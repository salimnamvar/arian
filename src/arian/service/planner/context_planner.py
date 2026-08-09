"""Context planner for task-aware file selection and chunking."""

from __future__ import annotations

from dataclasses import replace
import logging

from arian.domain.context.models import ContextChunk
from arian.domain.context.models import ContextPlan
from arian.domain.context.models import ContextTask
from arian.domain.context.models import FileFragment
from arian.domain.context.models import PlannedFile
from arian.domain.protocols import FileClassifierProtocol
from arian.domain.repository.models import RepositoryFile
from arian.domain.repository.models import Symbol
from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import FileRole
from arian.domain.shared.enums import SymbolKind
from arian.domain.shared.enums import TokenBudget
from arian.infrastructure.config import PlannerConfig
from arian.service.base import BaseServiceModule
from arian.service.classifier.file_classifier import FileClassifier
from arian.util.base import ModuleMetadata

logger = logging.getLogger(__name__)


class ContextPlanner(BaseServiceModule):
    """Plans context generation based on task type and token budget.

    Selects files, decides compression levels, and organizes chunks
    to stay within token budgets while maximizing relevance.

    Attributes:
        _classifier: File classifier for role detection (protocol).
        _config: Planner configuration (role ordering, task boosts).
    """

    def __init__(
        self,
        a_classifier: FileClassifierProtocol | None = None,
        a_config: PlannerConfig = PlannerConfig(),
    ) -> None:
        """Initialize planner.

        Args:
            a_classifier: Optional file classifier (defaults to new instance).
            a_config: Planner configuration (role ordering, task boosts).
        """
        super().__init__(
            a_metadata=ModuleMetadata(
                name="arian.service.planner",
                layer="service",
                capabilities=frozenset({"sync"}),
            )
        )
        self._classifier: FileClassifierProtocol = a_classifier if a_classifier is not None else FileClassifier()
        self._config: PlannerConfig = a_config

    def plan(
        self,
        a_files: list[RepositoryFile],
        a_task: ContextTask,
        a_budget: TokenBudget,
        a_query: str | None = None,
        a_symbols: dict[str, list[Symbol]] | None = None,
    ) -> ContextPlan:
        """Create a context plan for the given files and task.

        Args:
            a_files: Repository files to plan for.
            a_task: The context task type.
            a_budget: Token budget constraints.
            a_query: Optional query for relevance matching.
            a_symbols: Optional mapping of file path to extracted symbols.

        Returns:
            ContextPlan with chunks and metadata.
        """
        symbols: dict[str, list[Symbol]] = a_symbols if a_symbols is not None else {}
        planned: list[PlannedFile] = self._plan_files(a_files, a_task, a_query, symbols, a_budget)
        chunks: tuple[ContextChunk, ...] = self._plan_chunks(planned, a_budget)
        total_tokens: int = sum(c.token_count for c in chunks)
        total_files: int = sum(len(c.files) for c in chunks)

        result: ContextPlan = ContextPlan(
            chunks=chunks,
            total_tokens=total_tokens,
            total_files=total_files,
            task=a_task,
            query=a_query,
        )
        return result

    def _plan_files(
        self,
        a_files: list[RepositoryFile],
        a_task: ContextTask,
        a_query: str | None,  # noqa: ARG002 — reserved for future query matching
        a_symbols: dict[str, list[Symbol]],
        a_budget: TokenBudget,
    ) -> list[PlannedFile]:
        """Plan individual file representations.

        Args:
            a_files: Repository files to plan.
            a_task: The context task type.
            a_query: Optional query for relevance matching.
            a_symbols: Mapping of file path to extracted symbols.
            a_budget: Token budget constraints.

        Returns:
            List of PlannedFile sorted by importance.
        """
        planned: list[PlannedFile] = []
        for repo_file in a_files:
            role: FileRole
            importance: int
            role, importance, _ = self._classifier.classify(repo_file.path)

            importance = self._adjust_importance(importance, role, a_task)

            if (
                a_budget.per_chunk_target is not None
                and repo_file.tokens > a_budget.per_chunk_target
                and repo_file.path in a_symbols
            ):
                fragments: tuple[FileFragment, ...] = self._fragment_large_file(
                    repo_file,
                    a_symbols[repo_file.path],
                    importance,
                    a_budget,
                )
                for fragment in fragments:
                    planned.append(
                        PlannedFile(
                            path=repo_file.path,
                            role=role,
                            importance=importance,
                            compression=fragment.compression,
                            representation=f"fragment {fragment.fragment_index + 1}/{fragment.fragment_total}",
                            tokens=fragment.estimated_tokens,
                            language=repo_file.language,
                            is_fragment=True,
                            fragment_index=fragment.fragment_index,
                            fragment_total=fragment.fragment_total,
                            line_start=fragment.line_start,
                            line_end=fragment.line_end,
                        )
                    )
            else:
                planned.append(
                    PlannedFile(
                        path=repo_file.path,
                        role=role,
                        importance=importance,
                        compression=CompressionLevel.FULL,
                        representation=CompressionLevel.FULL.value,
                        tokens=repo_file.tokens,
                        language=repo_file.language,
                    )
                )

        planned.sort(key=lambda f: (f.importance, self._config.role_order.get(f.role, 10), f.path))
        result: list[PlannedFile] = self._fit_budget(planned, a_budget)
        return result

    def _adjust_importance(
        self,
        a_base_importance: int,
        a_role: FileRole,
        a_task: ContextTask,
    ) -> int:
        """Adjust importance based on task type.

        Args:
            a_base_importance: Base importance from classifier.
            a_role: File role.
            a_task: Context task type.

        Returns:
            Adjusted importance score.
        """
        boost_map: dict[FileRole, int] = self._config.task_file_boost.get(a_task, {})
        boost: int = boost_map.get(a_role, 0)
        result: int = max(0, a_base_importance + boost)
        return result

    def _fit_budget(
        self,
        a_planned: list[PlannedFile],
        a_budget: TokenBudget,
    ) -> list[PlannedFile]:
        """Resolve compression so planned files fit within the token budget.

        Without a budget every file stays at FULL. When a budget is set and
        the total would exceed it, files are selected greedily by importance:
        the most important files keep FULL content, the next best fit as
        SIGNATURES, and the rest are dropped.

        Args:
            a_planned: Planned files sorted by importance.
            a_budget: Token budget constraints.

        Returns:
            Planned files that fit within the budget (same importance order).
        """
        max_tokens: int | None = a_budget.max_tokens
        result: list[PlannedFile]
        if max_tokens is None:
            result = a_planned
        else:
            decisions = self._select_for_budget(a_planned, max_tokens)
            result = self._apply_decisions(a_planned, decisions)
            dropped_count: int = len(a_planned) - len(result)
            if dropped_count > 0:
                logger.warning(
                    "Dropped %d file(s) to fit within the %d-token budget",
                    dropped_count,
                    max_tokens,
                )
        return result

    def _select_for_budget(
        self,
        a_planned: list[PlannedFile],
        a_max_tokens: int,
    ) -> dict[int, tuple[CompressionLevel, int]]:
        """Choose a compression level per file to fit within a token budget.

        Files are processed in importance order: FULL when it fits, otherwise
        SIGNATURES, otherwise the file is dropped. The budget is never
        exceeded.

        Args:
            a_planned: Planned files sorted by importance.
            a_max_tokens: Maximum total tokens.

        Returns:
            Per-index mapping of the chosen compression level and token count.
        """
        decisions: dict[int, tuple[CompressionLevel, int]] = {}
        remaining_budget: int = a_max_tokens

        for index, planned_file in enumerate(a_planned):
            if planned_file.compression != CompressionLevel.FULL:
                if planned_file.tokens <= remaining_budget:
                    decisions[index] = (planned_file.compression, planned_file.tokens)
                    remaining_budget -= planned_file.tokens
                continue
            if planned_file.tokens <= remaining_budget:
                decisions[index] = (CompressionLevel.FULL, planned_file.tokens)
                remaining_budget -= planned_file.tokens
                continue
            signature_tokens: int = self._estimate_tokens(planned_file.tokens, CompressionLevel.SIGNATURES)
            if signature_tokens <= remaining_budget:
                decisions[index] = (CompressionLevel.SIGNATURES, signature_tokens)
                remaining_budget -= signature_tokens

        return decisions

    def _apply_decisions(
        self,
        a_planned: list[PlannedFile],
        a_decisions: dict[int, tuple[CompressionLevel, int]],
    ) -> list[PlannedFile]:
        """Emit planned files in original order, applying budget decisions.

        Args:
            a_planned: Planned files sorted by importance.
            a_decisions: Per-index compression level and token count.

        Returns:
            Planned files that fit within the budget, in original order.
        """
        result: list[PlannedFile] = []
        for index, planned_file in enumerate(a_planned):
            if index not in a_decisions:
                continue
            level, tokens = a_decisions[index]
            if level == planned_file.compression and tokens == planned_file.tokens:
                result.append(planned_file)
                continue
            result.append(
                replace(
                    planned_file,
                    compression=level,
                    representation=level.value,
                    tokens=tokens,
                )
            )
        return result

    def _estimate_tokens(self, a_original_tokens: int, a_level: CompressionLevel) -> int:
        """Estimate token count after compression.

        Args:
            a_original_tokens: Original token count.
            a_level: Compression level.

        Returns:
            Estimated token count.
        """
        ratio: float = self._config.compression_ratios.get(a_level, 1.0)
        result: int = max(1, int(a_original_tokens * ratio))
        return result

    def _fragment_large_file(
        self,
        a_file: RepositoryFile,
        a_symbols: list[Symbol],
        a_importance: int,
        a_budget: TokenBudget,  # noqa: ARG002 — reserved for future fragmentation logic
    ) -> tuple[FileFragment, ...]:
        """Fragment a large file into semantic segments.

        Creates fragments based on symbol boundaries (classes, methods)
        to preserve semantic meaning. Falls back to token-based splitting
        only when no semantic boundaries exist.

        Args:
            a_file: Repository file metadata.
            a_symbols: Extracted symbols for this file.
            a_importance: Importance score for this file.
            a_budget: Token budget constraints.

        Returns:
            Tuple of FileFragment objects.
        """
        symbol_boundaries: list[tuple[int, int, str | None, str | None]] = []
        for symbol in a_symbols:
            if symbol.kind == SymbolKind.CLASS:
                symbol_boundaries.append((symbol.line_start, symbol.line_end, symbol.name, None))
            elif symbol.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
                symbol_boundaries.append((symbol.line_start, symbol.line_end, None, symbol.name))

        symbol_boundaries.sort(key=lambda b: b[0])
        fragments: list[FileFragment] = []

        if symbol_boundaries:
            current_start: int = 0
            before_tokens: int = 0
            symbol_tokens: int = 0

            for boundary_start, boundary_end, class_name, function_name in symbol_boundaries:
                if boundary_start > current_start:
                    before_tokens = max(1, a_file.tokens // (len(symbol_boundaries) + 1))
                    fragments.append(
                        FileFragment(
                            file_path=a_file.path,
                            fragment_index=len(fragments),
                            fragment_total=len(symbol_boundaries) + 1,
                            line_start=current_start,
                            line_end=boundary_start,
                            compression=CompressionLevel.SIGNATURES,
                            importance=a_importance,
                            estimated_tokens=before_tokens,
                        )
                    )

                symbol_tokens = max(1, a_file.tokens // (len(symbol_boundaries) + 1))
                fragments.append(
                    FileFragment(
                        file_path=a_file.path,
                        fragment_index=len(fragments),
                        fragment_total=len(symbol_boundaries) + 1,
                        line_start=boundary_start,
                        line_end=boundary_end,
                        compression=CompressionLevel.SIGNATURES,
                        importance=a_importance,
                        estimated_tokens=symbol_tokens,
                        class_context=class_name,
                        function_context=function_name,
                    )
                )
                current_start = boundary_end

            final_tokens: int = max(
                1,
                a_file.tokens - before_tokens - symbol_tokens * len(symbol_boundaries),
            )
            fragments.append(
                FileFragment(
                    file_path=a_file.path,
                    fragment_index=len(fragments),
                    fragment_total=len(symbol_boundaries) + 1,
                    line_start=current_start,
                    line_end=None,
                    compression=CompressionLevel.SIGNATURES,
                    importance=a_importance,
                    estimated_tokens=final_tokens,
                )
            )
        else:
            fragments.append(
                FileFragment(
                    file_path=a_file.path,
                    fragment_index=0,
                    fragment_total=1,
                    line_start=0,
                    line_end=None,
                    compression=CompressionLevel.SIGNATURES,
                    importance=a_importance,
                    estimated_tokens=int(a_file.tokens * self._config.fragment_signature_ratio),
                )
            )

        total_fragments: int = len(fragments)
        result: tuple[FileFragment, ...] = tuple(
            FileFragment(
                file_path=f.file_path,
                fragment_index=f.fragment_index,
                fragment_total=total_fragments,
                line_start=f.line_start,
                line_end=f.line_end,
                compression=f.compression,
                importance=f.importance,
                estimated_tokens=f.estimated_tokens,
                class_context=f.class_context,
                function_context=f.function_context,
                imports_summary=f.imports_summary,
            )
            for f in fragments
        )
        return result

    def _plan_chunks(
        self,
        a_planned: list[PlannedFile],
        a_budget: TokenBudget,
    ) -> tuple[ContextChunk, ...]:
        """Organize planned files into token-aware chunks.

        Args:
            a_planned: Planned files sorted by importance.
            a_budget: Token budget constraints.

        Returns:
            Tuple of ContextChunk objects.
        """
        chunks: list[ContextChunk] = []
        current_files: list[PlannedFile] = []
        current_tokens: int = 0
        chunk_index: int = 0

        for planned_file in a_planned:
            if (
                a_budget.per_chunk_target is not None
                and current_tokens + planned_file.tokens > a_budget.per_chunk_target
                and current_files
            ):
                chunks.append(
                    ContextChunk(
                        files=tuple(current_files),
                        token_count=current_tokens,
                        chunk_index=chunk_index,
                    )
                )
                chunk_index += 1
                current_files = []
                current_tokens = 0

            current_files.append(planned_file)
            current_tokens += planned_file.tokens

        if current_files:
            chunks.append(
                ContextChunk(
                    files=tuple(current_files),
                    token_count=current_tokens,
                    chunk_index=chunk_index,
                )
            )

        result: tuple[ContextChunk, ...] = tuple(chunks)
        return result

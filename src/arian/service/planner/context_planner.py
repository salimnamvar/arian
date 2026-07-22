"""Context planner for task-aware file selection and chunking."""

from __future__ import annotations

import logging
from pathlib import Path

from arian.domain.context.models import ContextChunk
from arian.domain.context.models import ContextPlan
from arian.domain.context.models import ContextTask
from arian.domain.context.models import FileFragment
from arian.domain.context.models import PlannedFile
from arian.domain.repository.models import RepositoryFile
from arian.domain.repository.models import Symbol
from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import FileRole
from arian.domain.shared.enums import SymbolKind
from arian.domain.shared.enums import TokenBudget
from arian.service.classifier.file_classifier import CONFIG_NAMES
from arian.service.classifier.file_classifier import README_NAMES
from arian.service.classifier.file_classifier import FileClassifier

logger = logging.getLogger(__name__)

_ROLE_ORDER: dict[FileRole, int] = {
    FileRole.README: 0,
    FileRole.DOCUMENTATION: 1,
    FileRole.ENTRY_POINT: 2,
    FileRole.CONFIGURATION: 3,
    FileRole.DOMAIN: 4,
    FileRole.SERVICE: 5,
    FileRole.INFRASTRUCTURE: 6,
    FileRole.UTILITY: 7,
    FileRole.TEST: 8,
    FileRole.GENERATED: 9,
    FileRole.UNKNOWN: 10,
}

_TASK_FILE_BOOST: dict[ContextTask, dict[FileRole, int]] = {
    ContextTask.BUG_FIX: {
        FileRole.TEST: -3,
        FileRole.SERVICE: -2,
        FileRole.DOMAIN: -1,
    },
    ContextTask.FEATURE: {
        FileRole.DOMAIN: -2,
        FileRole.SERVICE: -1,
        FileRole.TEST: -1,
    },
    ContextTask.REVIEW: {
        FileRole.SERVICE: -2,
        FileRole.DOMAIN: -1,
    },
    ContextTask.ONBOARDING: {
        FileRole.README: -5,
        FileRole.CONFIGURATION: -1,
    },
    ContextTask.REFACTOR: {
        FileRole.SERVICE: -2,
        FileRole.INFRASTRUCTURE: -1,
    },
    ContextTask.DOCUMENT: {
        FileRole.README: -3,
        FileRole.DOMAIN: -1,
        FileRole.SERVICE: -1,
    },
    ContextTask.GENERAL: {},
}


class ContextPlanner:
    """Plans context generation based on task type and token budget.

    Selects files, decides compression levels, and organizes chunks
    to stay within token budgets while maximizing relevance.

    Attributes:
        _classifier: File classifier for role detection.
    """

    def __init__(self, a_classifier: FileClassifier | None = None) -> None:
        """Initialize planner.

        Args:
            a_classifier: Optional file classifier (defaults to new instance).
        """
        self._classifier: FileClassifier = a_classifier if a_classifier is not None else FileClassifier()

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
            compression: CompressionLevel
            role, importance, compression = self._classifier.classify(repo_file.path)

            importance = self._adjust_importance(importance, role, a_task)
            compression = self._decide_compression(compression, repo_file, a_task)

            representation: str = compression.value
            tokens: int = self._estimate_tokens(repo_file.tokens, compression)

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
                        compression=compression,
                        representation=representation,
                        tokens=tokens,
                        language=repo_file.language,
                    )
                )

        planned.sort(key=lambda f: (f.importance, _ROLE_ORDER.get(f.role, 10), f.path))
        return planned

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
        boost_map: dict[FileRole, int] = _TASK_FILE_BOOST.get(a_task, {})
        boost: int = boost_map.get(a_role, 0)
        result: int = max(0, a_base_importance + boost)
        return result

    def _decide_compression(
        self,
        a_default: CompressionLevel,
        a_file: RepositoryFile,
        a_task: ContextTask,
    ) -> CompressionLevel:
        """Decide compression level for a file.

        Args:
            a_default: Default compression from classifier.
            a_file: Repository file metadata.
            a_task: Context task type.

        Returns:
            Decided compression level.
        """
        result: CompressionLevel = a_default

        if a_file.tokens > 5000 and result == CompressionLevel.FULL:
            result = CompressionLevel.STRUCTURE
        elif a_file.tokens > 2000 and result == CompressionLevel.FULL:
            result = CompressionLevel.SIGNATURES

        if a_role_is_critical(a_file.path, a_task):
            result = CompressionLevel.FULL

        return result

    def _estimate_tokens(self, a_original_tokens: int, a_level: CompressionLevel) -> int:
        """Estimate token count after compression.

        Args:
            a_original_tokens: Original token count.
            a_level: Compression level.

        Returns:
            Estimated token count.
        """
        ratios: dict[CompressionLevel, float] = {
            CompressionLevel.FULL: 1.0,
            CompressionLevel.SIGNATURES: 0.3,
            CompressionLevel.STRUCTURE: 0.1,
            CompressionLevel.SUMMARY: 0.05,
            CompressionLevel.AUTO: 1.0,
        }
        ratio: float = ratios.get(a_level, 1.0)
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
                    estimated_tokens=int(a_file.tokens * 0.3),
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
        total_tokens: int = 0

        for planned_file in a_planned:
            if a_budget.max_tokens is not None and total_tokens + planned_file.tokens > a_budget.max_tokens:
                logger.warning(
                    "Token budget exceeded: %d + %d > %d. Stopping.",
                    total_tokens,
                    planned_file.tokens,
                    a_budget.max_tokens,
                )
                break

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
            total_tokens += planned_file.tokens

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


def a_role_is_critical(a_path: str, a_task: ContextTask) -> bool:
    """Check if a file is critical for the given task.

    Args:
        a_path: File path.
        a_task: Context task type.

    Returns:
        True if the file should always be included at full compression.
    """
    path_lower: str = a_path.lower()
    name: str = Path(path_lower).name
    result: bool = False

    if a_task == ContextTask.BUG_FIX:
        if "test" in path_lower or "spec" in path_lower:
            result = True
        if name in README_NAMES or name.startswith("readme"):
            result = True
    elif a_task == ContextTask.REVIEW:
        if name in README_NAMES or name.startswith("readme"):
            result = True
    elif a_task == ContextTask.ONBOARDING:
        if name in README_NAMES or name.startswith("readme"):
            result = True
        if name in CONFIG_NAMES:
            result = True

    return result

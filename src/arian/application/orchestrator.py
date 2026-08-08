"""Application class — use case orchestrator for context generation.

Follows CSR pattern: the controller delegates here; this layer orchestrates
services and repositories via protocols to fulfill the use case.
"""

from __future__ import annotations

from collections.abc import Callable
import logging
from pathlib import Path
import time

from arian.application.context import ContextRequest
from arian.application.context import ContextResult
from arian.application.validator import ContextRequestValidator
from arian.domain.context.models import BuildRequest
from arian.domain.context.models import ContextPlan
from arian.domain.context.models import ContextTask
from arian.domain.exceptions import InputError
from arian.domain.exceptions import ProcessingError
from arian.domain.exceptions import ProjectBaseError
from arian.domain.protocols import ContextBuilderProtocol
from arian.domain.repository.models import CollectionStats
from arian.domain.shared.enums import TokenBudget
from arian.domain.shared.output import OutputWriterProtocol
from arian.domain.shared.output import RendererProtocol
from arian.domain.shared.security import redact_secrets
from arian.domain.shared.security import sanitize_error_message
from arian.infrastructure.config import SecurityConfig

logger = logging.getLogger(__name__)


class Application:
    """Use case orchestrator — builds context from a repository.

    Responsibilities:
        1. Validate request and resolve output paths via injected ports.
        2. Delegate to ContextBuilderProtocol for plan, content, materialization.
        3. Delegate to RendererProtocol for final output.
        4. Redact secrets, write via OutputWriter, return ContextResult.

    Attributes:
        _builder: Context builder pipeline port.
        _renderer: Renderer port (protocol-based).
        _output: Output writer port (protocol-based).
        _validator: Request validator.
        _root: Repository root path (injected; no Path.cwd() in use-case code).
        _resolve_output: Output path resolver port.
        _security_config: Security configuration for secret redaction.
    """

    def __init__(
        self,
        a_builder: ContextBuilderProtocol,
        a_renderer: RendererProtocol,
        a_output: OutputWriterProtocol,
        a_resolve_output: Callable[[str], Path],
        a_security_config: SecurityConfig = SecurityConfig(),
        a_validator: ContextRequestValidator | None = None,
        a_root: Path | None = None,
    ) -> None:
        """Initialize the application.

        Args:
            a_builder: Context builder pipeline port.
            a_renderer: Renderer for output generation (protocol-based).
            a_output: Output writer port for persisting rendered content.
            a_resolve_output: Output path resolver port (injected by bootstrap).
            a_security_config: Security configuration (used by
                ``redact_secrets`` on every rendered chunk).
            a_validator: Request validator. Created with a_root if None.
            a_root: Repository root. Defaults to current working directory
                only when bootstrap does not inject one.
        """
        self._builder: ContextBuilderProtocol = a_builder
        self._renderer: RendererProtocol = a_renderer
        self._output: OutputWriterProtocol = a_output
        self._resolve_output: Callable[[str], Path] = a_resolve_output
        self._security_config: SecurityConfig = a_security_config
        self._root: Path = a_root if a_root is not None else Path.cwd()
        self._validator = a_validator or ContextRequestValidator(a_root=self._root)

    async def build_context(self, a_request: ContextRequest) -> ContextResult:
        """Execute the full context generation pipeline.

        Pipeline:
            1. Parse task, resolve paths.
            2. Build plan via ContextBuilder.
            3. Load content, materialize, render, redact.
            4. Write output file.
            5. Return ContextResult with stats and partial-failure info.

        Args:
            a_request: Input DTO from the controller.

        Returns:
            ContextResult with output path, statistics, skips, and warnings.

        Raises:
            InputError: If task name is invalid or input is bad.
            ProcessingError: If an OS-level error occurs during processing.
        """
        root: Path = self._root
        try:
            self._validator.validate(a_request)
            t_start: float = time.monotonic()
            task_enum: ContextTask = ContextTask(a_request.task)
            budget: TokenBudget = TokenBudget(max_tokens=a_request.budget)
            input_paths: list[Path] = [root / p for p in a_request.paths] if a_request.paths else [root]

            if a_request.group:
                result, skipped_files = await self._build_grouped(root, task_enum, budget, a_request)
            elif a_request.scope == "separate":
                result, skipped_files = await self._build_separate(root, task_enum, budget, a_request)
            else:
                result, skipped_files = await self._build_merged(root, task_enum, budget, input_paths, a_request)

            warnings: list[str] = []
            if skipped_files:
                warnings.append(f"Skipped {len(skipped_files)} file(s) during content load")

            elapsed: float = time.monotonic() - t_start
            return ContextResult(
                output_path=result.output_path,
                total_files=result.total_files,
                total_tokens=result.total_tokens,
                elapsed_seconds=elapsed,
                skipped_files=skipped_files,
                warnings=tuple(warnings),
            )
        except ProjectBaseError:
            raise
        except ValueError as e:
            sanitized = sanitize_error_message(str(e), str(root))
            raise InputError(sanitized) from e
        except OSError as e:
            sanitized = sanitize_error_message(str(e), str(root))
            raise ProcessingError(sanitized) from e

    async def _build_merged(
        self,
        a_root: Path,
        a_task: ContextTask,
        a_budget: TokenBudget,
        a_input_paths: list[Path],
        a_request: ContextRequest,
    ) -> tuple[ContextResult, tuple[str, ...]]:
        """Build a single merged context file.

        Args:
            a_root: Repository root path.
            a_task: Task type.
            a_budget: Token budget.
            a_input_paths: All input paths.
            a_request: Original request DTO.

        Returns:
            Tuple of ContextResult with stats and skipped file paths.
        """
        output_path: Path = self._resolve_output(a_request.output_path)
        # Only user-named paths are explicit. The implicit ``a_root``
        # default (when the user passes no paths) is NOT explicit, so
        # ``.gitignore`` rules still apply during a default scan.
        explicit_paths: frozenset[Path] = (
            frozenset(a_root / p for p in a_request.paths) if a_request.paths else frozenset()
        )
        plan: ContextPlan = await self._builder.build(
            BuildRequest(
                path=a_root,
                task=a_task,
                budget=a_budget,
                query=a_request.query,
                root=a_root,
                input_paths=a_input_paths if a_request.paths else None,
                explicit_paths=explicit_paths,
            )
        )
        return await self._materialize_render_write(
            a_plan=plan,
            a_root=a_root,
            a_request=a_request,
            a_scope="merged",
            a_output_path=output_path,
        )

    async def _build_separate(
        self,
        a_root: Path,
        a_task: ContextTask,
        a_budget: TokenBudget,
        a_request: ContextRequest,
    ) -> tuple[ContextResult, tuple[str, ...]]:
        """Build separate context files for each input path.

        Args:
            a_root: Repository root path.
            a_task: Task type.
            a_budget: Token budget.
            a_request: Original request DTO.

        Returns:
            Tuple of ContextResult with stats and accumulated skipped paths.
        """
        output_base: Path = self._resolve_output(a_request.output_path)
        total_files: int = 0
        total_tokens: int = 0
        last_output: Path = output_base
        all_skipped: list[str] = []

        input_paths: list[Path] = [a_root / p for p in a_request.paths] if a_request.paths else [a_root]
        for input_path in input_paths:
            plan: ContextPlan = await self._builder.build(
                BuildRequest(
                    path=input_path,
                    task=a_task,
                    budget=a_budget,
                    query=a_request.query,
                    root=a_root,
                    explicit_paths=frozenset({input_path}),
                )
            )
            input_name: str = str(input_path.relative_to(a_root)) if input_path != a_root else "."
            if input_path == a_root:
                sep_output = output_base.parent / "root_context.md"
            else:
                rel_name: Path = input_path.relative_to(a_root)
                sep_output = output_base.parent / f"{rel_name}_context.md"
            result, skipped = await self._materialize_render_write(
                a_plan=plan,
                a_root=a_root,
                a_request=a_request,
                a_scope="separate",
                a_output_path=sep_output,
                a_paths=[input_name],
            )
            all_skipped.extend(skipped)
            total_files += result.total_files
            total_tokens += result.total_tokens
            last_output = sep_output

        return (
            ContextResult(
                output_path=last_output,
                total_files=total_files,
                total_tokens=total_tokens,
                elapsed_seconds=0,
            ),
            tuple(all_skipped),
        )

    async def _build_grouped(
        self,
        a_root: Path,
        a_task: ContextTask,
        a_budget: TokenBudget,
        a_request: ContextRequest,
    ) -> tuple[ContextResult, tuple[str, ...]]:
        """Build context for each group of paths.

        Args:
            a_root: Repository root path.
            a_task: Task type.
            a_budget: Token budget.
            a_request: Original request DTO.

        Returns:
            Tuple of ContextResult with stats and accumulated skipped paths.
        """
        output_base: Path = self._resolve_output(a_request.output_path)
        total_files: int = 0
        total_tokens: int = 0
        last_output: Path = output_base
        all_skipped: list[str] = []

        for group_spec in a_request.group:
            group_paths: list[Path] = [a_root / p for p in group_spec]
            plan: ContextPlan = await self._builder.build(
                BuildRequest(
                    path=a_root,
                    task=a_task,
                    budget=a_budget,
                    query=a_request.query,
                    root=a_root,
                    input_paths=group_paths,
                    explicit_paths=frozenset(group_paths),
                )
            )
            group_names: list[str] = [p.name for p in group_paths]
            group_label: str = "_".join(group_names) if len(group_names) > 1 else group_names[0]
            group_output = output_base.parent / f"{group_label}_context.md"
            input_names: list[str] = [str(p.relative_to(a_root)) for p in group_paths]
            result, skipped = await self._materialize_render_write(
                a_plan=plan,
                a_root=a_root,
                a_request=a_request,
                a_scope="group",
                a_output_path=group_output,
                a_paths=input_names,
            )
            all_skipped.extend(skipped)
            total_files += result.total_files
            total_tokens += result.total_tokens
            last_output = group_output

        return (
            ContextResult(
                output_path=last_output,
                total_files=total_files,
                total_tokens=total_tokens,
                elapsed_seconds=0,
            ),
            tuple(all_skipped),
        )

    async def _materialize_render_write(
        self,
        a_plan: ContextPlan,
        a_root: Path,
        a_request: ContextRequest,
        a_scope: str,
        a_output_path: Path,
        a_paths: list[str] | None = None,
    ) -> tuple[ContextResult, tuple[str, ...]]:
        """Shared pipeline: metadata → load → materialize → redact → write.

        Args:
            a_plan: Planned context from the builder.
            a_root: Repository root path.
            a_request: Original request DTO.
            a_scope: Scope mode string (merged / separate / group).
            a_output_path: Destination path for this render.
            a_paths: Optional explicit path names for metadata.

        Returns:
            Tuple of ContextResult stats and skipped file paths.
        """
        stats: CollectionStats = self._builder.collection_stats
        plan: ContextPlan = self._with_metadata(
            a_plan,
            a_root,
            a_request,
            a_scope,
            a_paths=a_paths,
            a_stats=stats,
        )
        content, skipped_files = await self._builder.load_content(a_plan=plan, a_root=a_root)
        materialized = self._builder.materialize(plan, content)
        rendered: str = redact_secrets(
            self._renderer.render(materialized, plan),
            self._security_config,
        )
        self._output.write(str(a_output_path), rendered)
        logger.info(
            "Context generated: %d files, %d tokens, %d chunks, %d skipped",
            plan.total_files,
            plan.total_tokens,
            len(plan.chunks),
            len(skipped_files),
        )
        logger.info("Output: %s", a_output_path)
        return (
            ContextResult(
                output_path=a_output_path,
                total_files=plan.total_files,
                total_tokens=plan.total_tokens,
                elapsed_seconds=0,
            ),
            skipped_files,
        )

    @staticmethod
    def _with_metadata(
        a_plan: ContextPlan,
        a_root: Path,
        a_request: ContextRequest,
        a_scope: str,
        a_paths: list[str] | None = None,
        a_stats: CollectionStats | None = None,
    ) -> ContextPlan:
        """Return a new ContextPlan with metadata attached.

        Args:
            a_plan: Original plan.
            a_root: Repository root.
            a_request: Original request DTO.
            a_scope: Scope mode string.
            a_paths: Optional explicit path names.
            a_stats: Optional collection statistics.

        Returns:
            New ContextPlan with metadata dict.
        """
        paths: list[str] = (
            a_paths or [str(p) if p != a_root else "." for p in [a_root / p for p in a_request.paths]]
            if a_request.paths
            else ["."]
        )
        meta: dict[str, str | int | dict[str, str | int | None] | dict[str, int] | list[str]] = {
            "repository": a_root.name,
            "paths": paths,
            "budget": {"max": a_request.budget},
            "scope": a_scope,
        }
        if a_stats is not None:
            collection_block: dict[str, int] = {
                "total_scanned": a_stats.total_scanned,
                "collected": a_stats.collected,
                "skipped_binary": a_stats.skipped_binary,
                "skipped_size": a_stats.skipped_size,
                "skipped_gitignore": a_stats.skipped_gitignore,
                "skipped_permission": a_stats.skipped_permission,
                "skipped_error": a_stats.skipped_error,
                "skipped_by_extension": a_stats.skipped_by_extension,
                "unknown_language": a_stats.unknown_language,
            }
            meta["collection"] = collection_block
            meta["skipped_gitignore_by_pattern"] = dict(a_stats.skipped_gitignore_by_pattern)
        return ContextPlan(
            chunks=a_plan.chunks,
            total_tokens=a_plan.total_tokens,
            total_files=a_plan.total_files,
            task=a_plan.task,
            query=a_plan.query,
            metadata=meta,
            repository_files=a_plan.repository_files,
        )

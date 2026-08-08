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
from arian.domain.context.models import MaterializedChunk
from arian.domain.exceptions import ProjectBaseError
from arian.domain.protocols import ContextBuilderProtocol
from arian.domain.repository.models import CollectionStats
from arian.domain.repository.models import FileContent
from arian.domain.shared.enums import TokenBudget
from arian.domain.shared.output import OutputWriterProtocol
from arian.domain.shared.output import RendererProtocol
from arian.domain.shared.result import Result
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

    async def build_context(self, a_request: ContextRequest) -> Result[ContextResult]:
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
            Result[ContextResult] with is_success, value (ContextResult), and message.
        """
        root: Path = self._root
        result: Result[ContextResult] = Result[ContextResult].failure("uninitialized")
        b_continue: bool = True

        try:
            validation_result = self._validator.validate(a_request)
            if not validation_result.is_success:
                logger.debug("Validation failed: %s", validation_result.message)
                result = Result[ContextResult].failure(validation_result.message)
                b_continue = False

            if b_continue:
                t_start: float = time.monotonic()
                task_enum: ContextTask = ContextTask(a_request.task)
                budget: TokenBudget = TokenBudget(max_tokens=a_request.budget)
                input_paths: list[Path] = [root / p for p in a_request.paths] if a_request.paths else [root]

                build_result: Result[tuple[ContextResult, tuple[str, ...]]]
                if a_request.group:
                    build_result = await self._build_grouped(root, task_enum, budget, a_request)
                elif a_request.scope == "separate":
                    build_result = await self._build_separate(root, task_enum, budget, a_request)
                else:
                    build_result = await self._build_merged(root, task_enum, budget, input_paths, a_request)

                if not build_result.is_success:
                    result = Result[ContextResult].failure(build_result.message)
                    b_continue = False
                else:
                    build_data, skipped_files = build_result.success_value()
                    warnings: list[str] = []
                    if skipped_files:
                        warnings.append(f"Skipped {len(skipped_files)} file(s) during content load")

                    elapsed: float = time.monotonic() - t_start
                    result = Result[ContextResult].success(
                        ContextResult(
                            output_path=build_data.output_path,
                            total_files=build_data.total_files,
                            total_tokens=build_data.total_tokens,
                            elapsed_seconds=elapsed,
                            skipped_files=skipped_files,
                            warnings=tuple(warnings),
                        )
                    )
        except ProjectBaseError as exc:
            logger.exception("Context build aborted")
            result = Result[ContextResult].failure(exc.message)
        except ValueError as e:
            sanitized = sanitize_error_message(str(e), str(root))
            logger.exception("Invalid context request for %s: %s", root, sanitized)
            result = Result[ContextResult].failure(sanitized)
        except OSError as e:
            sanitized = sanitize_error_message(str(e), str(root))
            logger.exception("OS error while building context for %s: %s", root, sanitized)
            result = Result[ContextResult].failure(sanitized)

        return result

    async def _build_merged(
        self,
        a_root: Path,
        a_task: ContextTask,
        a_budget: TokenBudget,
        a_input_paths: list[Path],
        a_request: ContextRequest,
    ) -> Result[tuple[ContextResult, tuple[str, ...]]]:
        """Build a single merged context file.

        Args:
            a_root: Repository root path.
            a_task: Task type.
            a_budget: Token budget.
            a_input_paths: All input paths.
            a_request: Original request DTO.

        Returns:
            Result of tuple of ContextResult with stats and skipped file paths.
        """
        result: Result[tuple[ContextResult, tuple[str, ...]]] = Result.failure("uninitialized")
        b_continue: bool = True
        output_path: Path = self._resolve_output(a_request.output_path)
        explicit_paths: frozenset[Path] = (
            frozenset(a_root / p for p in a_request.paths) if a_request.paths else frozenset()
        )
        build_plan_result = await self._builder.build(
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
        if not build_plan_result.is_success or build_plan_result.value is None:
            result = Result.failure(build_plan_result.message)
            b_continue = False

        plan: ContextPlan = ContextPlan(chunks=(), total_tokens=0, total_files=0, task=a_task)
        if b_continue:
            plan = build_plan_result.success_value()

        if b_continue:
            materialize_result = await self._materialize_render_write(
                a_plan=plan,
                a_root=a_root,
                a_request=a_request,
                a_scope="merged",
                a_output_path=output_path,
            )
            result = materialize_result

        return result

    async def _build_separate(
        self,
        a_root: Path,
        a_task: ContextTask,
        a_budget: TokenBudget,
        a_request: ContextRequest,
    ) -> Result[tuple[ContextResult, tuple[str, ...]]]:
        """Build separate context files for each input path.

        Args:
            a_root: Repository root path.
            a_task: Task type.
            a_budget: Token budget.
            a_request: Original request DTO.

        Returns:
            Result of tuple of ContextResult with stats and accumulated skipped paths.
        """
        result: Result[tuple[ContextResult, tuple[str, ...]]] = Result.failure("uninitialized")
        b_continue: bool = True
        output_base: Path = self._resolve_output(a_request.output_path)
        total_files: int = 0
        total_tokens: int = 0
        last_output: Path = output_base
        all_skipped: list[str] = []

        input_paths: list[Path] = [a_root / p for p in a_request.paths] if a_request.paths else [a_root]
        for input_path in input_paths:
            if b_continue:
                build_plan_result = await self._builder.build(
                    BuildRequest(
                        path=input_path,
                        task=a_task,
                        budget=a_budget,
                        query=a_request.query,
                        root=a_root,
                        explicit_paths=frozenset({input_path}),
                    )
                )
                if not build_plan_result.is_success or build_plan_result.value is None:
                    result = Result.failure(build_plan_result.message)
                    b_continue = False
                else:
                    plan: ContextPlan = build_plan_result.success_value()
                    input_name: str = str(input_path.relative_to(a_root)) if input_path != a_root else "."
                    if input_path == a_root:
                        sep_output = output_base.parent / "root_context.md"
                    else:
                        rel_name: Path = input_path.relative_to(a_root)
                        sep_output = output_base.parent / f"{rel_name}_context.md"
                    materialize_result = await self._materialize_render_write(
                        a_plan=plan,
                        a_root=a_root,
                        a_request=a_request,
                        a_scope="separate",
                        a_output_path=sep_output,
                        a_paths=[input_name],
                    )
                    if not materialize_result.is_success:
                        result = materialize_result
                        b_continue = False
                    else:
                        res, skipped = materialize_result.success_value()
                        all_skipped.extend(skipped)
                        total_files += res.total_files
                        total_tokens += res.total_tokens
                        last_output = sep_output

        if b_continue:
            result = Result.success(
                (
                    ContextResult(
                        output_path=last_output,
                        total_files=total_files,
                        total_tokens=total_tokens,
                        elapsed_seconds=0,
                    ),
                    tuple(all_skipped),
                )
            )

        return result

    async def _build_grouped(
        self,
        a_root: Path,
        a_task: ContextTask,
        a_budget: TokenBudget,
        a_request: ContextRequest,
    ) -> Result[tuple[ContextResult, tuple[str, ...]]]:
        """Build context for each group of paths.

        Args:
            a_root: Repository root path.
            a_task: Task type.
            a_budget: Token budget.
            a_request: Original request DTO.

        Returns:
            Result of tuple of ContextResult with stats and accumulated skipped paths.
        """
        result: Result[tuple[ContextResult, tuple[str, ...]]] = Result.failure("uninitialized")
        b_continue: bool = True
        output_base: Path = self._resolve_output(a_request.output_path)
        total_files: int = 0
        total_tokens: int = 0
        last_output: Path = output_base
        all_skipped: list[str] = []

        for group_spec in a_request.group:
            if b_continue:
                group_paths: list[Path] = [a_root / p for p in group_spec]
                build_plan_result = await self._builder.build(
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
                if not build_plan_result.is_success or build_plan_result.value is None:
                    result = Result.failure(build_plan_result.message)
                    b_continue = False
                else:
                    plan: ContextPlan = build_plan_result.success_value()
                    group_names: list[str] = [p.name for p in group_paths]
                    group_label: str = "_".join(group_names) if len(group_names) > 1 else group_names[0]
                    group_output = output_base.parent / f"{group_label}_context.md"
                    input_names: list[str] = [str(p.relative_to(a_root)) for p in group_paths]
                    materialize_result = await self._materialize_render_write(
                        a_plan=plan,
                        a_root=a_root,
                        a_request=a_request,
                        a_scope="group",
                        a_output_path=group_output,
                        a_paths=input_names,
                    )
                    if not materialize_result.is_success:
                        result = materialize_result
                        b_continue = False
                    else:
                        res, skipped = materialize_result.success_value()
                        all_skipped.extend(skipped)
                        total_files += res.total_files
                        total_tokens += res.total_tokens
                        last_output = group_output

        if b_continue:
            result = Result.success(
                (
                    ContextResult(
                        output_path=last_output,
                        total_files=total_files,
                        total_tokens=total_tokens,
                        elapsed_seconds=0,
                    ),
                    tuple(all_skipped),
                )
            )

        return result

    async def _materialize_render_write(
        self,
        a_plan: ContextPlan,
        a_root: Path,
        a_request: ContextRequest,
        a_scope: str,
        a_output_path: Path,
        a_paths: list[str] | None = None,
    ) -> Result[tuple[ContextResult, tuple[str, ...]]]:
        """Shared pipeline: metadata → load → materialize → redact → write.

        Args:
            a_plan: Planned context from the builder.
            a_root: Repository root path.
            a_request: Original request DTO.
            a_scope: Scope mode string (merged / separate / group).
            a_output_path: Destination path for this render.
            a_paths: Optional explicit path names for metadata.

        Returns:
            Result of tuple of ContextResult stats and skipped file paths.
        """
        result: Result[tuple[ContextResult, tuple[str, ...]]] = Result.failure("uninitialized")
        b_continue: bool = True
        stats: CollectionStats = self._builder.collection_stats
        plan: ContextPlan = self._with_metadata(
            a_plan,
            a_root,
            a_request,
            a_scope,
            a_paths=a_paths,
            a_stats=stats,
        )
        content_load_result = await self._builder.load_content(a_plan=plan, a_root=a_root)
        if not content_load_result.is_success or content_load_result.value is None:
            result = Result.failure(content_load_result.message)
            b_continue = False

        content: dict[str, FileContent] = {}
        skipped_files: tuple[str, ...] = ()
        if b_continue:
            load_data = content_load_result.success_value()
            content = load_data.content
            skipped_files = load_data.skipped

        materialized: tuple[MaterializedChunk, ...] = ()
        if b_continue:
            materialize_result = self._builder.materialize(plan, content)
            if not materialize_result.is_success or materialize_result.value is None:
                result = Result.failure(materialize_result.message)
                b_continue = False
            else:
                materialized = materialize_result.success_value()

        rendered: str = ""
        if b_continue:
            render_result = self._renderer.render(materialized, plan)
            if not render_result.is_success or render_result.value is None:
                result = Result.failure(render_result.message)
                b_continue = False
            else:
                rendered = redact_secrets(
                    render_result.success_value(),
                    self._security_config,
                )

        if b_continue:
            write_result = self._output.write(str(a_output_path), rendered)
            if not write_result.is_success:
                result = Result.failure(write_result.message)
                b_continue = False

        if b_continue:
            logger.info(
                "Context generated: %d files, %d tokens, %d chunks, %d skipped",
                plan.total_files,
                plan.total_tokens,
                len(plan.chunks),
                len(skipped_files),
            )
            logger.info("Output: %s", a_output_path)
            result = Result.success(
                (
                    ContextResult(
                        output_path=a_output_path,
                        total_files=plan.total_files,
                        total_tokens=plan.total_tokens,
                        elapsed_seconds=0,
                    ),
                    skipped_files,
                )
            )

        return result

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

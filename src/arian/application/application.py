"""Application class — use case orchestrator for context generation.

Follows CSR pattern: the controller delegates here; this layer orchestrates
services and repositories to fulfill the use case.
"""

from __future__ import annotations

import logging
from pathlib import Path
import time

from arian.application.context import ContextRequest
from arian.application.context import ContextResult
from arian.domain.context.models import ContextPlan
from arian.domain.context.models import ContextTask
from arian.domain.exceptions import InputError
from arian.domain.exceptions import ProcessingError
from arian.domain.exceptions import ProjectBaseError
from arian.domain.shared.enums import TokenBudget
from arian.domain.shared.output import OutputWriterProtocol
from arian.infrastructure.output_path_resolver import resolve_output_path
from arian.renderer.markdown.renderer import MarkdownRenderer
from arian.service.builder.context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class Application:
    """Use case orchestrator — builds context from a repository.

    Responsibilities:
        1. Resolve input paths and output path.
        2. Delegate to ContextBuilder for plan, content, and materialization.
        3. Delegate to MarkdownRenderer for final output.
        4. Delegate to OutputWriter for persistence and return a ContextResult.

    Attributes:
        _builder: Context builder for the full pipeline.
        _renderer: Markdown renderer for final output.
        _output: Output writer (filesystem-agnostic protocol).
    """

    def __init__(
        self,
        a_builder: ContextBuilder,
        a_renderer: MarkdownRenderer,
        a_output: OutputWriterProtocol,
    ) -> None:
        """Initialize the application.

        Args:
            a_builder: Context builder for pipeline orchestration.
            a_renderer: Markdown renderer for output generation.
            a_output: Output writer port for persisting rendered content.
        """
        self._builder = a_builder
        self._renderer = a_renderer
        self._output = a_output

    async def build_context(self, a_request: ContextRequest) -> ContextResult:
        """Execute the full context generation pipeline.

        Pipeline:
            1. Parse task, resolve paths.
            2. Build plan via ContextBuilder.
            3. Load content, materialize, render.
            4. Write output file.
            5. Return ContextResult with stats.

        Args:
            a_request: Input DTO from the controller.

        Returns:
            ContextResult with output path and statistics.

        Raises:
            InputError: If task name is invalid or input is bad.
            ProcessingError: If an OS-level error occurs during processing.
        """
        try:
            t_start: float = time.monotonic()
            root: Path = Path.cwd()
            task_enum: ContextTask = ContextTask(a_request.task)
            budget: TokenBudget = TokenBudget(max_tokens=a_request.budget)
            input_paths: list[Path] = [root / p for p in a_request.paths] if a_request.paths else [root]

            if a_request.group:
                result = await self._build_grouped(root, task_enum, budget, a_request)
            elif a_request.scope == "separate":
                result = await self._build_separate(root, task_enum, budget, a_request)
            else:
                result = await self._build_merged(root, task_enum, budget, input_paths, a_request)

            elapsed: float = time.monotonic() - t_start
            return ContextResult(
                output_path=result.output_path,
                total_files=result.total_files,
                total_tokens=result.total_tokens,
                elapsed_seconds=elapsed,
            )
        except ProjectBaseError:
            raise
        except ValueError as e:
            raise InputError(str(e)) from e
        except OSError as e:
            raise ProcessingError(str(e)) from e

    async def _build_merged(
        self,
        a_root: Path,
        a_task: ContextTask,
        a_budget: TokenBudget,
        a_input_paths: list[Path],
        a_request: ContextRequest,
    ) -> ContextResult:
        """Build a single merged context file.

        Args:
            a_root: Repository root path.
            a_task: Task type.
            a_budget: Token budget.
            a_input_paths: All input paths.
            a_request: Original request DTO.

        Returns:
            ContextResult with stats and output path.
        """
        output_path: Path = resolve_output_path(a_request.output_path)
        plan: ContextPlan = await self._builder.build(
            a_path=a_root,
            a_task=a_task,
            a_budget=a_budget,
            a_query=a_request.query,
            a_root=a_root,
            a_input_paths=a_input_paths if a_request.paths else None,
        )
        plan = self._with_metadata(plan, a_root, a_request, "merged")
        content = await self._builder.load_content(a_plan=plan, a_root=a_root)
        materialized = self._builder.materialize(plan, content)
        rendered: str = self._renderer.render(materialized, plan)
        self._output.write(str(output_path), rendered)
        logger.info(
            "Context generated: %d files, %d tokens, %d chunks",
            plan.total_files,
            plan.total_tokens,
            len(plan.chunks),
        )
        logger.info("Output: %s", output_path)
        return ContextResult(
            output_path=output_path,
            total_files=plan.total_files,
            total_tokens=plan.total_tokens,
            elapsed_seconds=0,
        )

    async def _build_separate(
        self,
        a_root: Path,
        a_task: ContextTask,
        a_budget: TokenBudget,
        a_request: ContextRequest,
    ) -> ContextResult:
        """Build separate context files for each input path.

        Args:
            a_root: Repository root path.
            a_task: Task type.
            a_budget: Token budget.
            a_request: Original request DTO.

        Returns:
            ContextResult with stats and output path of last file.
        """
        output_base: Path = resolve_output_path(a_request.output_path)
        total_files: int = 0
        total_tokens: int = 0
        last_output: Path = output_base

        input_paths: list[Path] = [a_root / p for p in a_request.paths] if a_request.paths else [a_root]
        for input_path in input_paths:
            if not input_path.exists():
                msg = f"Path does not exist: {input_path}"
                raise ValueError(msg)
            plan: ContextPlan = await self._builder.build(
                a_path=input_path,
                a_task=a_task,
                a_budget=a_budget,
                a_query=a_request.query,
                a_root=a_root,
            )
            input_name: str = str(input_path.relative_to(a_root)) if input_path != a_root else "."
            plan = self._with_metadata(plan, a_root, a_request, "separate", [input_name])
            content = await self._builder.load_content(a_plan=plan, a_root=a_root)
            materialized = self._builder.materialize(plan, content)
            rendered: str = self._renderer.render(materialized, plan)
            if input_path == a_root:
                sep_output = output_base.parent / "root_context.md"
            else:
                rel_name: Path = input_path.relative_to(a_root)
                sep_output = output_base.parent / f"{rel_name}_context.md"
            self._output.write(str(sep_output), rendered)
            logger.info("Output: %s", sep_output)
            total_files += plan.total_files
            total_tokens += plan.total_tokens
            last_output = sep_output

        return ContextResult(
            output_path=last_output,
            total_files=total_files,
            total_tokens=total_tokens,
            elapsed_seconds=0,
        )

    async def _build_grouped(
        self,
        a_root: Path,
        a_task: ContextTask,
        a_budget: TokenBudget,
        a_request: ContextRequest,
    ) -> ContextResult:
        """Build context for each group of paths.

        Args:
            a_root: Repository root path.
            a_task: Task type.
            a_budget: Token budget.
            a_request: Original request DTO.

        Returns:
            ContextResult with stats and output path of last group.
        """
        output_base: Path = resolve_output_path(a_request.output_path)
        total_files: int = 0
        total_tokens: int = 0
        last_output: Path = output_base

        for group_spec in a_request.group:
            group_paths: list[Path] = [a_root / p for p in group_spec]
            plan: ContextPlan = await self._builder.build(
                a_path=a_root,
                a_task=a_task,
                a_budget=a_budget,
                a_query=a_request.query,
                a_root=a_root,
                a_input_paths=group_paths,
            )
            group_names: list[str] = [p.name for p in group_paths]
            group_label: str = "_".join(group_names) if len(group_names) > 1 else group_names[0]
            group_output = output_base.parent / f"{group_label}_context.md"
            input_names: list[str] = [str(p.relative_to(a_root)) for p in group_paths]
            plan = self._with_metadata(plan, a_root, a_request, "group", input_names)
            content = await self._builder.load_content(a_plan=plan, a_root=a_root)
            materialized = self._builder.materialize(plan, content)
            rendered: str = self._renderer.render(materialized, plan)
            self._output.write(str(group_output), rendered)
            logger.info("Output: %s", group_output)
            total_files += plan.total_files
            total_tokens += plan.total_tokens
            last_output = group_output

        return ContextResult(
            output_path=last_output,
            total_files=total_files,
            total_tokens=total_tokens,
            elapsed_seconds=0,
        )

    @staticmethod
    def _with_metadata(
        a_plan: ContextPlan,
        a_root: Path,
        a_request: ContextRequest,
        a_scope: str,
        a_paths: list[str] | None = None,
    ) -> ContextPlan:
        """Return a new ContextPlan with metadata attached.

        Args:
            a_plan: Original plan.
            a_root: Repository root.
            a_request: Original request DTO.
            a_scope: Scope mode string.
            a_paths: Optional explicit path names.

        Returns:
            New ContextPlan with metadata dict.
        """
        paths: list[str] = (
            a_paths or [str(p) if p != a_root else "." for p in [a_root / p for p in a_request.paths]]
            if a_request.paths
            else ["."]
        )
        return ContextPlan(
            chunks=a_plan.chunks,
            total_tokens=a_plan.total_tokens,
            total_files=a_plan.total_files,
            task=a_plan.task,
            query=a_plan.query,
            metadata={
                "repository": a_root.name,
                "paths": paths,
                "budget": {"max": a_request.budget},
                "scope": a_scope,
            },
            repository_files=a_plan.repository_files,
        )

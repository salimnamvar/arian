"""Typer CLI application for Arian."""

from __future__ import annotations

import asyncio
import logging
import logging.handlers
from pathlib import Path
import time

import typer

from arian.bootstrap.logging import configure_logging
from arian.domain.context.models import ContextPlan
from arian.domain.context.models import ContextTask
from arian.domain.shared.enums import TokenBudget
from arian.infrastructure.config import LoggingConfig
from arian.infrastructure.ignore.default_patterns import DEFAULT_EXCLUDES
from arian.infrastructure.output_path_resolver import resolve_output_path
from arian.renderer.markdown.renderer import MarkdownRenderer
from arian.repository.filesystem.collector import FileCollector
from arian.repository.index.memory_repository import MemoryRepositoryIndex
from arian.service.analyzer.python_analyzer import PythonAnalyzer
from arian.service.builder.context_builder import ContextBuilder
from arian.service.classifier.file_classifier import FileClassifier
from arian.service.context.materializer import ContextMaterializer
from arian.service.planner.context_planner import ContextPlanner

app: typer.Typer = typer.Typer(help="Repository intelligence and context planning engine.", add_completion=False)

logger: logging.Logger = logging.getLogger(__name__)


def _parse_budget(a_value: str | None) -> int | None:
    """Parse budget string into token count or None for unlimited.

    Args:
        a_value: Raw budget string from CLI. None, "none", or a positive integer.

    Returns:
        Parsed budget as int, or None for unlimited.

    Raises:
        typer.Exit: If value is not a valid number or is non-positive.
    """
    budget_value: int | None = None
    if a_value is not None:
        if a_value.lower() == "none":
            budget_value = None
        else:
            try:
                budget_value = int(a_value)
            except ValueError:
                logger.error("Invalid budget: %s. Must be a number or 'none'.", a_value)  # noqa: TRY400
                raise typer.Exit(code=1) from None
            if budget_value <= 0:
                logger.error("Budget must be > 0, got: %d", budget_value)
                raise typer.Exit(code=1) from None
    return budget_value


_DEFAULT_EXTENSIONS: frozenset[str] = frozenset({".py", ".md", ".txt", ".rst", ".toml", ".yaml", ".yml", ".json"})


def _run_separate(
    a_builder: ContextBuilder,
    a_input_paths: list[Path],
    a_task: ContextTask,
    a_budget: TokenBudget,
    a_query: str | None,
    a_root: Path,
    a_output_path: Path,
    a_scope: str,
) -> None:
    """Build and write separate context files for each path.

    Args:
        a_builder: Context builder instance.
        a_input_paths: Paths to process individually.
        a_task: Task type.
        a_budget: Token budget.
        a_query: Optional query.
        a_root: Repository root.
        a_output_path: Base output path.
        a_scope: Scope mode string.
    """
    for input_path in a_input_paths:
        if not input_path.exists():
            logger.error("Path does not exist: %s", input_path)
            raise typer.Exit(code=1) from None
        plan = asyncio.run(
            a_builder.build(a_path=input_path, a_task=a_task, a_budget=a_budget, a_query=a_query, a_root=a_root)
        )
        input_name: str = str(input_path.relative_to(a_root)) if input_path != a_root else "."
        plan = ContextPlan(
            chunks=plan.chunks,
            total_tokens=plan.total_tokens,
            total_files=plan.total_files,
            task=plan.task,
            query=plan.query,
            metadata={
                "repository": a_root.name,
                "paths": [input_name],
                "budget": {"max": a_budget.max_tokens},
                "scope": a_scope,
            },
            repository_files=plan.repository_files,
        )
        content_map = asyncio.run(a_builder.load_content(a_plan=plan, a_root=a_root))
        materialized = a_builder.materialize(plan, content_map)
        renderer: MarkdownRenderer = MarkdownRenderer()
        rendered: str = renderer.render(materialized, plan)
        if input_path == a_root:
            sep_output = a_output_path.parent / "root_context.md"
        else:
            rel_name: Path = input_path.relative_to(a_root)
            sep_output = a_output_path.parent / f"{rel_name}_context.md"
        sep_output.parent.mkdir(parents=True, exist_ok=True)
        sep_output.write_text(rendered, encoding="utf-8")
        logger.info("Output: %s", sep_output)


def _run_merged(
    a_builder: ContextBuilder,
    a_input_paths: list[Path],
    a_task: ContextTask,
    a_budget: TokenBudget,
    a_query: str | None,
    a_root: Path,
    a_output_path: Path,
    a_scope: str,
    a_paths_provided: bool,
) -> None:
    """Build and write a single merged context file.

    Args:
        a_builder: Context builder instance.
        a_input_paths: All input paths.
        a_task: Task type.
        a_budget: Token budget.
        a_query: Optional query.
        a_root: Repository root.
        a_output_path: Output file path.
        a_scope: Scope mode string.
        a_paths_provided: Whether user provided explicit paths.
    """
    plan = asyncio.run(
        a_builder.build(
            a_path=a_root,
            a_task=a_task,
            a_budget=a_budget,
            a_query=a_query,
            a_root=a_root,
            a_input_paths=a_input_paths if a_paths_provided else None,
        )
    )

    input_names = [str(p.relative_to(a_root)) if p != a_root else "." for p in a_input_paths]
    plan = ContextPlan(
        chunks=plan.chunks,
        total_tokens=plan.total_tokens,
        total_files=plan.total_files,
        task=plan.task,
        query=plan.query,
        metadata={
            "repository": a_root.name,
            "paths": input_names,
            "budget": {"max": a_budget.max_tokens},
            "scope": a_scope,
        },
        repository_files=plan.repository_files,
    )

    content_map = asyncio.run(a_builder.load_content(a_plan=plan, a_root=a_root))
    materialized = a_builder.materialize(plan, content_map)
    renderer_final: MarkdownRenderer = MarkdownRenderer()
    rendered_final: str = renderer_final.render(materialized, plan)
    a_output_path.parent.mkdir(parents=True, exist_ok=True)
    a_output_path.write_text(rendered_final, encoding="utf-8")

    logger.info(
        "Context generated: %d files, %d tokens, %d chunks",
        plan.total_files,
        plan.total_tokens,
        len(plan.chunks),
    )
    logger.info("Output: %s", a_output_path)


def _run_group(
    a_builder: ContextBuilder,
    a_group_paths: list[Path],
    a_task: ContextTask,
    a_budget: TokenBudget,
    a_query: str | None,
    a_root: Path,
    a_output_path: Path,
) -> None:
    """Build and write context for a single group of paths.

    Args:
        a_builder: Context builder instance.
        a_group_paths: Paths belonging to this group.
        a_task: Task type.
        a_budget: Token budget.
        a_query: Optional query.
        a_root: Repository root.
        a_output_path: Base output path.
    """
    plan = asyncio.run(
        a_builder.build(
            a_path=a_root,
            a_task=a_task,
            a_budget=a_budget,
            a_query=a_query,
            a_root=a_root,
            a_input_paths=a_group_paths,
        )
    )
    group_names: list[str] = [p.name for p in a_group_paths]
    group_label: str = "_".join(group_names) if len(group_names) > 1 else group_names[0]
    group_output = a_output_path.parent / f"{group_label}_context.md"
    group_output.parent.mkdir(parents=True, exist_ok=True)

    input_names = [str(p.relative_to(a_root)) for p in a_group_paths]
    plan = ContextPlan(
        chunks=plan.chunks,
        total_tokens=plan.total_tokens,
        total_files=plan.total_files,
        task=plan.task,
        query=plan.query,
        metadata={
            "repository": a_root.name,
            "paths": input_names,
            "budget": {"max": a_budget.max_tokens},
            "scope": "group",
        },
        repository_files=plan.repository_files,
    )

    content_map = asyncio.run(a_builder.load_content(a_plan=plan, a_root=a_root))
    materialized = a_builder.materialize(plan, content_map)
    renderer: MarkdownRenderer = MarkdownRenderer()
    rendered: str = renderer.render(materialized, plan)
    group_output.write_text(rendered, encoding="utf-8")
    logger.info("Output: %s", group_output)


@app.command()  # a-prefix-ignore: Typer CLI public names
def context(  # a-prefix-ignore: Typer CLI public names
    task: str = typer.Option(
        "general",
        "--task",
        case_sensitive=False,
        help="Task type: bug_fix, feature, review, onboarding, refactor, document, general",
    ),
    query: str | None = typer.Option(
        None, "--query", "-q", help="Query for relevance matching (reserved, not yet implemented)"
    ),
    output: str = typer.Option("~/.arian/output/context.md", "-o", "--output", help="Output file path"),
    budget: str | None = typer.Option(None, "--budget", help="Maximum tokens for context (default: unlimited)"),
    scope: str = typer.Option("merged", "--scope", help="Scope mode: merged (default) or separate"),
    group: list[str] | None = typer.Option(
        None,
        "--group",
        help="Group paths into one context file. Comma-separated. Repeatable: --group src/,lib/ --group docs/",
    ),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logging"),
    paths: list[str] = typer.Argument(default=None, help="Directories or files to include (default: cwd)"),
) -> None:
    """Generate task-aware context from a repository."""
    listener: logging.handlers.QueueListener | None = configure_logging(
        LoggingConfig(level="DEBUG" if verbose else "INFO")
    )

    try:
        t_start: float = time.monotonic()
        logger.info("Generating context for task=%s", task)

        try:
            task_enum: ContextTask = ContextTask(task.lower())
        except ValueError:
            msg = f"Invalid task: {task}. Valid tasks: {', '.join(t.value for t in ContextTask)}"
            logger.error(msg)  # noqa: TRY400
            raise typer.Exit(code=1) from None

        if scope not in ("merged", "separate"):
            msg = f"Invalid scope: {scope}. Valid scopes: merged, separate"
            logger.error(msg)
            raise typer.Exit(code=1) from None

        token_budget: TokenBudget = TokenBudget(max_tokens=_parse_budget(budget))
        root: Path = Path.cwd()
        output_path: Path = resolve_output_path(output)

        input_paths: list[Path] = [root / p for p in paths] if paths else [root]

        classifier: FileClassifier = FileClassifier()
        collector: FileCollector = FileCollector(
            a_extensions=_DEFAULT_EXTENSIONS,
            a_exclude=DEFAULT_EXCLUDES,
            a_classifier=classifier,
        )
        index: MemoryRepositoryIndex = MemoryRepositoryIndex()
        analyzer: PythonAnalyzer = PythonAnalyzer()
        planner: ContextPlanner = ContextPlanner(a_classifier=classifier)
        materializer: ContextMaterializer = ContextMaterializer(a_analyzer=analyzer)
        builder: ContextBuilder = ContextBuilder(
            a_collector=collector,
            a_index=index,
            a_planner=planner,
            a_materializer=materializer,
        )

        if group:
            if scope != "merged":
                logger.warning("--scope is ignored when --group is used")
            for group_spec in group:
                group_paths: list[Path] = [root / p.strip() for p in group_spec.split(",")]
                for gp in group_paths:
                    if not gp.exists():
                        logger.error("Path does not exist: %s", gp)
                        raise typer.Exit(code=1) from None
                _run_group(builder, group_paths, task_enum, token_budget, query, root, output_path)

        elif scope == "separate":
            _run_separate(builder, input_paths, task_enum, token_budget, query, root, output_path, scope)
        else:
            _run_merged(builder, input_paths, task_enum, token_budget, query, root, output_path, scope, bool(paths))

        elapsed: float = time.monotonic() - t_start
        logger.info("Completed in %.2fs", elapsed)
    finally:
        if listener is not None:
            listener.stop()

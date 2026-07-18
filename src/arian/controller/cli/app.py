"""Typer CLI application for Arian."""

from __future__ import annotations

import asyncio
import logging
import logging.handlers
from pathlib import Path

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

app: typer.Typer = typer.Typer(help="Repository intelligence and context planning engine.")

logger: logging.Logger = logging.getLogger(__name__)

_DEFAULT_EXTENSIONS: frozenset[str] = frozenset({".py", ".md", ".txt", ".rst", ".toml", ".yaml", ".yml", ".json"})


@app.command()  # a-prefix-ignore: Typer CLI public names
def context(  # a-prefix-ignore: Typer CLI public names
    task: str = typer.Option(
        "general",
        "--task",
        case_sensitive=False,
        help="Task type: bug_fix, feature, review, onboarding, refactor, document, general",
    ),
    query: str | None = typer.Option(None, "--query", "-q", help="Query for relevance matching"),
    output: str = typer.Option(".tmp", "-o", "--output", help="Output file path"),
    max_tokens: int = typer.Option(5000, "--max-tokens", help="Maximum tokens for context"),
    per_chunk: int = typer.Option(4000, "--per-chunk", help="Target tokens per chunk"),
    scope: str = typer.Option("merged", "--scope", help="Scope mode: merged (default) or separate"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logging"),
    async_logging: bool = typer.Option(False, "--async-logging", help="Enable async logging via queue"),
    paths: list[str] = typer.Argument(default=None, help="Directories or files to include (default: cwd)"),
) -> None:
    """Generate task-aware context from a repository."""
    listener: logging.handlers.QueueListener | None = configure_logging(
        LoggingConfig(level="DEBUG" if verbose else "INFO", async_logging=async_logging)
    )

    try:
        logger.info("Generating context for task=%s", task)

        try:
            task_enum: ContextTask = ContextTask(task.lower())
        except ValueError:
            msg = f"Invalid task: {task}. Valid tasks: {', '.join(t.value for t in ContextTask)}"
            logger.exception(msg)
            raise typer.Exit(code=1) from None

        if scope not in ("merged", "separate"):
            msg = f"Invalid scope: {scope}. Valid scopes: merged, separate"
            logger.error(msg)
            raise typer.Exit(code=1) from None

        budget: TokenBudget = TokenBudget(max_tokens=max_tokens, per_chunk_target=per_chunk)
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

        if scope == "separate":
            for input_path in input_paths:
                if not input_path.exists():
                    logger.error("Path does not exist: %s", input_path)
                    raise typer.Exit(code=1) from None
                plan = asyncio.run(
                    builder.build(
                        a_path=input_path,
                        a_task=task_enum,
                        a_budget=budget,
                        a_query=query,
                        a_root=root,
                    )
                )
                content_map = asyncio.run(builder.load_content(a_plan=plan, a_root=input_path))
                materialized = builder.materialize(plan, content_map)
                renderer: MarkdownRenderer = MarkdownRenderer()
                rendered: str = renderer.render(materialized, plan)
                rel_name = input_path.relative_to(root) if input_path != root else Path()
                sep_output = output_path.parent / f"{rel_name}_context.md"
                sep_output.parent.mkdir(parents=True, exist_ok=True)
                sep_output.write_text(rendered, encoding="utf-8")
                logger.info("Output: %s", sep_output)
        else:
            if not root.exists():
                logger.error("Path does not exist: %s", root)
                raise typer.Exit(code=1) from None
            plan = asyncio.run(
                builder.build(
                    a_path=root,
                    a_task=task_enum,
                    a_budget=budget,
                    a_query=query,
                    a_root=root,
                    a_input_paths=input_paths if paths else None,
                )
            )

            repo_name = root.name
            input_names = [str(p.relative_to(root)) if p != root else "." for p in input_paths]
            plan = ContextPlan(
                chunks=plan.chunks,
                total_tokens=plan.total_tokens,
                total_files=plan.total_files,
                task=plan.task,
                query=plan.query,
                metadata={
                    "repository": repo_name,
                    "paths": input_names,
                    "budget": {"max": budget.max_tokens, "per_chunk": budget.per_chunk_target},
                    "scope": scope,
                },
            )

            content_map = asyncio.run(builder.load_content(a_plan=plan, a_root=root))
            materialized = builder.materialize(plan, content_map)
            renderer_final: MarkdownRenderer = MarkdownRenderer()
            rendered_final: str = renderer_final.render(materialized, plan)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered_final, encoding="utf-8")

            logger.info(
                "Context generated: %d files, %d tokens, %d chunks",
                plan.total_files,
                plan.total_tokens,
                len(plan.chunks),
            )
            logger.info("Output: %s", output_path)
    finally:
        if listener is not None:
            listener.stop()

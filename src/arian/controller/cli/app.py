"""Typer CLI application for Arian."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import typer

from arian.bootstrap.logging import configure_logging
from arian.domain.context.models import ContextTask
from arian.domain.shared.enums import TokenBudget
from arian.infrastructure.config import LoggingConfig
from arian.infrastructure.output_path_resolver import resolve_output_path
from arian.renderers.markdown.renderer import MarkdownRenderer
from arian.repositories.filesystem.collector import FileCollector
from arian.repositories.index.memory_repository import MemoryRepositoryIndex
from arian.services.analyzer.python_analyzer import PythonAnalyzer
from arian.services.builder.context_builder import ContextBuilder
from arian.services.classifier.file_classifier import FileClassifier
from arian.services.planner.context_planner import ContextPlanner

app: typer.Typer = typer.Typer(help="Repository intelligence and context planning engine.")

logger: logging.Logger = logging.getLogger(__name__)

_DEFAULT_EXTENSIONS: frozenset[str] = frozenset({".py", ".md", ".txt", ".rst", ".toml", ".yaml", ".yml", ".json"})
_DEFAULT_EXCLUDE: frozenset[str] = frozenset(
    {"__pycache__", ".git", ".mypy_cache", ".pytest_cache", "node_modules", ".venv"}
)


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
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logging"),
) -> None:
    """Generate task-aware context from a repository."""
    configure_logging(LoggingConfig(level="DEBUG" if verbose else "INFO"))
    logger.info("Generating context for task=%s", task)

    try:
        task_enum: ContextTask = ContextTask(task.lower())
    except ValueError:
        msg = f"Invalid task: {task}. Valid tasks: {', '.join(t.value for t in ContextTask)}"
        logger.exception(msg)
        raise typer.Exit(code=1) from None

    budget: TokenBudget = TokenBudget(max_tokens=max_tokens, per_chunk_target=per_chunk)
    root: Path = Path.cwd()
    output_path: Path = resolve_output_path(output)

    collector: FileCollector = FileCollector(
        a_extensions=_DEFAULT_EXTENSIONS,
        a_exclude=_DEFAULT_EXCLUDE,
    )
    index: MemoryRepositoryIndex = MemoryRepositoryIndex()
    analyzer: PythonAnalyzer = PythonAnalyzer()
    classifier: FileClassifier = FileClassifier()
    planner: ContextPlanner = ContextPlanner(a_classifier=classifier)
    builder: ContextBuilder = ContextBuilder(
        a_collector=collector,
        a_index=index,
        a_analyzer=analyzer,
        a_planner=planner,
    )

    plan = asyncio.run(
        builder.build(
            a_path=root,
            a_task=task_enum,
            a_budget=budget,
            a_query=query,
        )
    )

    content_map = asyncio.run(builder.load_content(a_plan=plan, a_root=root))

    renderer: MarkdownRenderer = MarkdownRenderer()
    rendered: str = renderer.render(plan, content_map, a_root=root)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")

    logger.info(
        "Context generated: %d files, %d tokens, %d chunks",
        plan.total_files,
        plan.total_tokens,
        len(plan.chunks),
    )
    logger.info("Output: %s", output_path)

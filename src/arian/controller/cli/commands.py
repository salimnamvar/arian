"""Typer CLI controller for Arian.

Thin interface layer: parses CLI args → constructs ContextRequest →
delegates to Application → displays result. No service construction,
no pipeline logic, no output writing.
"""

from __future__ import annotations

import asyncio
import logging

import typer

from arian.application.context import ContextRequest
from arian.bootstrap.application import create_application
from arian.bootstrap.lifespan import lifespan
from arian.controller.cli.parsing import parse_budget
from arian.controller.cli.parsing import parse_groups
from arian.controller.cli.parsing import validate_request
from arian.infrastructure.config import ArianConfig
from arian.infrastructure.config import LoggingConfig

app: typer.Typer = typer.Typer(help="Repository intelligence and context planning engine.", add_completion=False)

logger: logging.Logger = logging.getLogger(__name__)


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
    logging_level: str = "DEBUG" if verbose else "INFO"
    config: ArianConfig = ArianConfig(logging=LoggingConfig(level=logging_level))

    with lifespan(config):
        request: ContextRequest = ContextRequest(
            task=task.lower(),
            budget=parse_budget(budget),
            output_path=output,
            scope=scope,
            group=parse_groups(group),
            query=query,
            paths=tuple(paths) if paths else (),
        )

        validate_request(request)

        logger.info("Generating context for task=%s", request.task)
        application = create_application(config)
        # Note: asyncio.run() is used here because the CLI is a sync entry point.
        # For ASGI (future MCP server), use async_lifespan instead.
        result = asyncio.run(application.build_context(request))

        logger.info(
            "Context generated: %d files, %d tokens in %.2fs",
            result.total_files,
            result.total_tokens,
            result.elapsed_seconds,
        )
        logger.info("Output: %s", result.output_path)
        if result.skipped_files:
            logger.warning("Skipped %d file(s) during content load", len(result.skipped_files))
            for skipped in result.skipped_files[:20]:
                logger.warning("  skipped: %s", skipped)
        for warning in result.warnings:
            logger.warning("%s", warning)

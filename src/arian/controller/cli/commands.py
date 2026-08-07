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
from arian.infrastructure.config import FileCollectorConfig
from arian.infrastructure.config import LoggingConfig

app: typer.Typer = typer.Typer(help="Repository intelligence and context planning engine.", add_completion=False)

logger: logging.Logger = logging.getLogger(__name__)


def _build_collector_config(
    a_from_env: ArianConfig,
    a_no_gitignore: bool,
    a_nested_gitignore: bool,
) -> FileCollectorConfig:
    """Build a ``FileCollectorConfig`` from env defaults + CLI overrides.

    Precedence: ``ARIAN_NO_GITIGNORE`` / ``ARIAN_NESTED_GITIGNORE`` env
    vars supply defaults; explicit ``--no-gitignore`` /
    ``--nested-gitignore`` flags override them.

    Args:
        a_from_env: Config loaded from environment variables.
        a_no_gitignore: Value of the ``--no-gitignore`` flag.
        a_nested_gitignore: Value of the ``--nested-gitignore`` flag.

    Returns:
        A new ``FileCollectorConfig`` reflecting the effective settings.
    """
    cfg: FileCollectorConfig = a_from_env.collector
    if a_no_gitignore:
        cfg = cfg.model_copy(update={"use_gitignore": False})
    if a_nested_gitignore:
        cfg = cfg.model_copy(update={"nested_gitignore": True})
    return cfg


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
    no_gitignore: bool = typer.Option(
        False,
        "--no-gitignore",
        help=(
            "Ignore all .gitignore rules for this invocation. Positional PATHS are "
            "always treated as explicit and bypass gitignore, regardless of this flag."
        ),
    ),
    nested_gitignore: bool = typer.Option(
        False,
        "--nested-gitignore",
        help=(
            "Also load .gitignore files from ancestor directories of the scan root. "
            "Off by default; mirrors git's behaviour for sub-trees."
        ),
    ),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logging"),
    paths: list[str] = typer.Argument(
        default=None,
        help=(
            "Directories or files to include (default: cwd). Any path passed here is "
            "treated as explicit and bypasses .gitignore rules — like 'git add -f'."
        ),
    ),
) -> None:
    """Generate task-aware context from a repository."""
    from_env: ArianConfig = ArianConfig.load_from_env()
    logging_level: str = "DEBUG" if verbose else from_env.logging.level
    collector_cfg: FileCollectorConfig = _build_collector_config(from_env, no_gitignore, nested_gitignore)
    config: ArianConfig = from_env.model_copy(
        update={
            "logging": LoggingConfig(level=logging_level, log_dir=from_env.logging.log_dir),
            "collector": collector_cfg,
        }
    )

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

        validate_request(request, a_config=config.controller)

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

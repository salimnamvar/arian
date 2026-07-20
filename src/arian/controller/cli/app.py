"""Typer CLI controller for Arian.

Thin interface layer: parses CLI args → constructs ContextRequest →
delegates to Application → displays result. No service construction,
no pipeline logic, no output writing.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import typer

from arian.application.context import ContextRequest
from arian.bootstrap.application import create_application
from arian.bootstrap.lifespan import lifespan
from arian.domain.context.models import ContextTask
from arian.infrastructure.config import ArianConfig
from arian.infrastructure.config import LoggingConfig

app: typer.Typer = typer.Typer(help="Repository intelligence and context planning engine.", add_completion=False)

logger: logging.Logger = logging.getLogger(__name__)

_VALID_SCOPES: frozenset[str] = frozenset({"merged", "separate"})


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


def _parse_groups(a_group: list[str] | None) -> tuple[tuple[str, ...], ...]:
    """Parse --group options into tuple of path-tuples.

    Args:
        a_group: Raw group strings from CLI (comma-separated paths).

    Returns:
        Tuple of path-tuples, one per group.
    """
    result: tuple[tuple[str, ...], ...] = ()
    if a_group:
        parsed: list[tuple[str, ...]] = []
        for group_spec in a_group:
            group_paths: tuple[str, ...] = tuple(p.strip() for p in group_spec.split(","))
            parsed.append(group_paths)
        result = tuple(parsed)
    return result


def _validate_request(a_request: ContextRequest) -> None:
    """Validate a ContextRequest before passing to Application.

    Args:
        a_request: Request DTO to validate.

    Raises:
        typer.Exit: If validation fails.
    """
    try:
        ContextTask(a_request.task)
    except ValueError:
        msg = f"Invalid task: {a_request.task}. Valid tasks: {', '.join(t.value for t in ContextTask)}"
        logger.error(msg)  # noqa: TRY400
        raise typer.Exit(code=1) from None

    if a_request.scope not in _VALID_SCOPES:
        msg = f"Invalid scope: {a_request.scope}. Valid scopes: merged, separate"
        logger.error(msg)
        raise typer.Exit(code=1) from None

    root: Path = Path.cwd()
    if a_request.group:
        for group_spec in a_request.group:
            for p in group_spec:
                gp: Path = root / p
                if not gp.exists():
                    logger.error("Path does not exist: %s", gp)
                    raise typer.Exit(code=1) from None


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
            budget=_parse_budget(budget),
            output_path=output,
            scope=scope,
            group=_parse_groups(group),
            query=query,
            paths=tuple(paths) if paths else (),
        )

        _validate_request(request)

        logger.info("Generating context for task=%s", request.task)
        application = create_application(config)
        result = asyncio.run(application.build_context(request))

        logger.info(
            "Context generated: %d files, %d tokens in %.2fs",
            result.total_files,
            result.total_tokens,
            result.elapsed_seconds,
        )
        logger.info("Output: %s", result.output_path)

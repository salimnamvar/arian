"""CLI parsing utilities — extracted from the controller.

Handles budget string parsing, group option parsing, and request validation.
These are CLI-specific concerns that do not belong in the command definition.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from arian.application.context import ContextRequest
from arian.domain.context.models import ContextTask

logger: logging.Logger = logging.getLogger(__name__)

_VALID_SCOPES: frozenset[str] = frozenset({"merged", "separate"})


def parse_budget(a_value: str | None) -> int | None:
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


def parse_groups(a_group: list[str] | None) -> tuple[tuple[str, ...], ...]:
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


def validate_request(a_request: ContextRequest) -> None:
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

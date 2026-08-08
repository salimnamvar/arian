"""CLI parsing utilities — extracted from the controller.

Handles budget string parsing and group option parsing. Business
validation of ``ContextRequest`` (paths, budget limits, scope) belongs
to the Application layer (``ContextRequestValidator``); the controller
only translates domain errors into CLI exit codes.
"""

from __future__ import annotations

import logging

import typer

from arian.application.context import ContextRequest
from arian.application.validator import ContextRequestValidator
from arian.domain.context.models import ContextTask
from arian.domain.shared.result import Result
from arian.infrastructure.config import ControllerConfig

logger: logging.Logger = logging.getLogger(__name__)


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


def validate_request(
    a_request: ContextRequest,
    a_config: ControllerConfig = ControllerConfig(),
    a_validator: ContextRequestValidator | None = None,
) -> Result[None]:
    """Validate a ContextRequest at the CLI boundary.

    Delegates business rules to ``ContextRequestValidator`` (application
    layer) and maps domain errors into a ``Result[None]``. Task name
    is still checked here so invalid enum values fail fast with a helpful
    list of valid values.

    Args:
        a_request: Request DTO to validate.
        a_config: Controller configuration (valid scopes) — used when
            no validator is injected.
        a_validator: Optional application validator. Built from
            ``a_config`` when omitted.

    Returns:
        Result[None] with is_success and message.
    """
    msg: str = ""
    result: Result[None] = Result[None].failure("uninitialized")
    b_continue: bool = True

    try:
        ContextTask(a_request.task)
    except ValueError:
        msg = f"Invalid task: {a_request.task}. Valid tasks: {', '.join(t.value for t in ContextTask)}"
        b_continue = False

    if b_continue:
        validator: ContextRequestValidator = a_validator or ContextRequestValidator(a_controller=a_config)
        result = validator.validate(a_request)

        if not result.is_success:
            logger.error("%s", result.message)

    if not b_continue:
        logger.error("%s", msg)
        result = Result[None].failure(msg)

    return result

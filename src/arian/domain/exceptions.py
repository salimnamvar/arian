"""Domain exceptions for Arian.

Provides structured exception hierarchy following errors.md patterns.
"""

from __future__ import annotations

from typing import Any


class ProjectBaseError(Exception):
    """Root base for all project exceptions.

    Never raise this class directly — always use a typed subclass.

    Attributes:
        message (str): Human-readable error description.
        resource_type (str | None): Resource type affected.
        resource_name (str | None): Resource identifier.
        details (list[dict[str, Any]]): Pre-built error detail objects.
    """

    reason: str = "UNKNOWN_ERROR"

    def __init__(
        self,
        a_message: str,
        a_resource_type: str | None = None,
        a_resource_name: str | None = None,
        a_details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.message = a_message
        self.resource_type = a_resource_type
        self.resource_name = a_resource_name
        self.details: list[dict[str, Any]] = list(a_details) if a_details else []
        super().__init__(a_message)


class ContextBuilderError(ProjectBaseError):
    """Base for context builder-specific errors."""

    reason = "CONTEXT_BUILDER_ERROR"


class InputNotFoundError(ContextBuilderError):
    """Input path does not exist."""

    reason = "INPUT_NOT_FOUND"


class NoDocumentsError(ContextBuilderError):
    """No documents collected from inputs."""

    reason = "NO_DOCUMENTS"

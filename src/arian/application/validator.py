"""Request validation — validates ContextRequest before pipeline execution."""

from __future__ import annotations

import logging
from pathlib import Path

from arian.application.context import ContextRequest
from arian.domain.exceptions import InputError
from arian.domain.shared.security import validate_input_path
from arian.infrastructure.config import ControllerConfig
from arian.infrastructure.config import DomainLimitsConfig
from arian.infrastructure.config import SecurityConfig

logger = logging.getLogger(__name__)


class ContextRequestValidator:
    """Validates ContextRequest fields before pipeline execution.

    Attributes:
        _root: Repository root (used to resolve relative paths).
        _limits: Domain-level numeric limits.
        _security: Security configuration (path-length, traversal).
        _controller: Controller-level validation tables.
    """

    def __init__(
        self,
        a_root: Path | None = None,
        a_limits: DomainLimitsConfig = DomainLimitsConfig(),
        a_security: SecurityConfig = SecurityConfig(),
        a_controller: ControllerConfig = ControllerConfig(),
    ) -> None:
        """Initialize the validator.

        Args:
            a_root: Repository root for relative-path resolution.
            a_limits: Domain-level numeric limits (max token budget).
            a_security: Security configuration (path-length cap).
            a_controller: Controller-level validation tables.
        """
        self._root: Path | None = a_root
        self._limits: DomainLimitsConfig = a_limits
        self._security: SecurityConfig = a_security
        self._controller: ControllerConfig = a_controller

    def validate(self, a_request: ContextRequest) -> None:
        """Validate a request. Raises InputError on failure.

        Args:
            a_request: Request to validate.

        Raises:
            InputError: If validation fails.
            SecurityError: If path traversal detected.
        """
        root: Path = self._root or Path.cwd()
        self._validate_paths(a_request.paths, root)
        for group_spec in a_request.group:
            self._validate_paths(group_spec, root)

        msg: str = ""
        if a_request.budget is not None and a_request.budget <= 0:
            msg = f"Budget must be positive, got: {a_request.budget}"
        elif a_request.budget is not None and a_request.budget > self._limits.max_token_budget:
            msg = f"Budget exceeds maximum ({self._limits.max_token_budget}), got: {a_request.budget}"
        elif a_request.scope not in self._controller.valid_scopes:
            msg = f"Invalid scope: {a_request.scope}. Valid scopes: {', '.join(sorted(self._controller.valid_scopes))}"

        if msg:
            logger.debug("Rejected context request: %s", msg)
            raise InputError(msg)

    def _validate_paths(self, a_paths: tuple[str, ...], a_root: Path) -> None:
        """Validate that each path exists and is not a traversal.

        Args:
            a_paths: Relative or absolute path strings.
            a_root: Repository root for relative resolution.

        Raises:
            InputError: If a path does not exist.
            SecurityError: If path traversal is detected.
        """
        msg: str = ""
        for path_str in a_paths:
            raw_path: Path = Path(path_str)
            full_path = raw_path if raw_path.is_absolute() else a_root / path_str
            if not full_path.exists():
                msg = f"Path does not exist: {path_str}"
                break
            if not raw_path.is_absolute():
                validate_input_path(full_path, a_root, self._security)

        if msg:
            logger.debug("Rejected path: %s", msg)
            raise InputError(msg)

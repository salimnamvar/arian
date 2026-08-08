"""Request validation — validates ContextRequest before pipeline execution."""

from __future__ import annotations

import logging
from pathlib import Path

from arian.application.context import ContextRequest
from arian.domain.shared.security import validate_input_path
from arian.infrastructure.config import ControllerConfig
from arian.infrastructure.config import DomainLimitsConfig
from arian.infrastructure.config import SecurityConfig

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of request validation.

    Attributes:
        is_success: Whether validation passed.
        message: Error message if validation failed.
    """

    def __init__(self, *, a_is_success: bool, a_message: str = "") -> None:
        self.is_success: bool = a_is_success
        self.message: str = a_message

    @staticmethod
    def success() -> ValidationResult:
        return ValidationResult(a_is_success=True)

    @staticmethod
    def failure(a_message: str) -> ValidationResult:
        return ValidationResult(a_is_success=False, a_message=a_message)


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

    def validate(self, a_request: ContextRequest) -> ValidationResult:
        """Validate a request. Returns ValidationResult instead of raising.

        Args:
            a_request: Request to validate.

        Returns:
            ValidationResult with is_success=True or error message.
        """
        root: Path = self._root or Path.cwd()
        result: ValidationResult = ValidationResult.success()

        path_result: ValidationResult = self._validate_paths(a_request.paths, root)
        if not path_result.is_success:
            result = path_result
        else:
            for group_spec in a_request.group:
                group_result: ValidationResult = self._validate_paths(group_spec, root)
                if not group_result.is_success:
                    result = group_result
                    break

        if result.is_success:
            msg: str = ""
            if a_request.budget is not None and a_request.budget <= 0:
                msg = f"Budget must be positive, got: {a_request.budget}"
            elif a_request.budget is not None and a_request.budget > self._limits.max_token_budget:
                msg = f"Budget exceeds maximum ({self._limits.max_token_budget}), got: {a_request.budget}"
            elif a_request.scope not in self._controller.valid_scopes:
                msg = f"Invalid scope: {a_request.scope}. Valid scopes: {', '.join(sorted(self._controller.valid_scopes))}"

            if msg:
                logger.debug("Rejected context request: %s", msg)
                result = ValidationResult.failure(msg)

        return result

    def _validate_paths(self, a_paths: tuple[str, ...], a_root: Path) -> ValidationResult:
        """Validate that each path exists and is not a traversal.

        Args:
            a_paths: Relative or absolute path strings.
            a_root: Repository root for relative resolution.

        Returns:
            ValidationResult with is_success=True or error message.
        """
        msg: str = ""
        for path_str in a_paths:
            raw_path: Path = Path(path_str)
            full_path = raw_path if raw_path.is_absolute() else a_root / path_str
            if not full_path.exists():
                msg = f"Path does not exist: {path_str}"
                break
            if not raw_path.is_absolute():
                try:
                    validate_input_path(full_path, a_root, self._security)
                except (ValueError, OSError) as exc:
                    msg = f"Path validation failed for {path_str}: {exc}"
                    break

        if msg:
            logger.debug("Rejected path: %s", msg)

        return ValidationResult.failure(msg) if msg else ValidationResult.success()

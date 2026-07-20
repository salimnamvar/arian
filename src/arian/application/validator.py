"""Request validation — validates ContextRequest before pipeline execution."""

from __future__ import annotations

from pathlib import Path

from arian.application.context import ContextRequest
from arian.domain.exceptions import InputError
from arian.domain.shared.security import validate_input_path


class ContextRequestValidator:
    """Validates ContextRequest fields before pipeline execution."""

    def __init__(self, a_root: Path | None = None) -> None:
        self._root: Path | None = a_root

    def validate(self, a_request: ContextRequest) -> None:
        """Validate a request. Raises InputError on failure.

        Args:
            a_request: Request to validate.

        Raises:
            InputError: If validation fails.
            SecurityError: If path traversal detected.
        """
        root: Path = self._root or Path.cwd()
        for path_str in a_request.paths:
            raw_path: Path = Path(path_str)
            full_path = raw_path if raw_path.is_absolute() else root / path_str
            if not full_path.exists():
                msg = f"Path does not exist: {path_str}"
                raise InputError(msg)
            if not raw_path.is_absolute():
                validate_input_path(full_path, root)

        if a_request.budget is not None and a_request.budget <= 0:
            msg = f"Budget must be positive, got: {a_request.budget}"
            raise InputError(msg)

        if a_request.scope not in ("merged", "separate"):
            msg = f"Invalid scope: {a_request.scope}"
            raise InputError(msg)

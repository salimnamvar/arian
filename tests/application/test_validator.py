"""Unit tests for ContextRequestValidator."""

from __future__ import annotations

from pathlib import Path

import pytest

from arian.application.context import ContextRequest
from arian.application.validator import ContextRequestValidator
from arian.domain.exceptions import InputError
from arian.domain.exceptions import SecurityError


class TestContextRequestValidator:
    """Tests for ContextRequestValidator.validate()."""

    def test_valid_request_passes(self, tmp_path: Path) -> None:
        """Verify a valid request passes validation."""
        (tmp_path / "src").mkdir()
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(paths=("src",), budget=5000, scope="merged")
        validator.validate(request)

    def test_nonexistent_path_raises(self, tmp_path: Path) -> None:
        """Verify missing path raises InputError."""
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(paths=("nonexistent",), scope="merged")
        with pytest.raises(InputError, match="Path does not exist"):
            validator.validate(request)

    def test_negative_budget_raises(self, tmp_path: Path) -> None:
        """Verify negative budget raises InputError."""
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(budget=-1, scope="merged")
        with pytest.raises(InputError, match="Budget must be positive"):
            validator.validate(request)

    def test_zero_budget_raises(self, tmp_path: Path) -> None:
        """Verify zero budget raises InputError."""
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(budget=0, scope="merged")
        with pytest.raises(InputError, match="Budget must be positive"):
            validator.validate(request)

    def test_none_budget_passes(self, tmp_path: Path) -> None:
        """Verify None budget (unlimited) passes validation."""
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(budget=None, scope="merged")
        validator.validate(request)

    def test_invalid_scope_raises(self, tmp_path: Path) -> None:
        """Verify invalid scope raises InputError."""
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(scope="group")
        with pytest.raises(InputError, match="Invalid scope"):
            validator.validate(request)

    def test_separate_scope_passes(self, tmp_path: Path) -> None:
        """Verify 'separate' scope passes validation."""
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(scope="separate")
        validator.validate(request)

    def test_path_traversal_nonexistent_raises_input(self, tmp_path: Path) -> None:
        """Verify traversal path that doesn't exist raises InputError first."""
        (tmp_path / "src").mkdir()
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(paths=("src/../../etc",), scope="merged")
        with pytest.raises(InputError, match="Path does not exist"):
            validator.validate(request)

    def test_symlink_escape_raises_security(self, tmp_path: Path) -> None:
        """Verify symlink pointing outside root raises SecurityError."""
        outside = tmp_path.parent / "outside_root"
        outside.mkdir(exist_ok=True)
        (outside / "secret.txt").write_text("secret")
        link = tmp_path / "sneaky"
        link.symlink_to(outside)
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(paths=("sneaky",), scope="merged")
        with pytest.raises(SecurityError):
            validator.validate(request)

    def test_default_root_is_none_lazy(self) -> None:
        """Verify default root is None (resolved lazily to cwd)."""
        validator = ContextRequestValidator()
        assert validator._root is None

    def test_empty_paths_and_no_budget_passes(self, tmp_path: Path) -> None:
        """Verify empty paths with no budget passes validation."""
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(paths=(), budget=None, scope="merged")
        validator.validate(request)

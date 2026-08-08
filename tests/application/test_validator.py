"""Unit tests for ContextRequestValidator."""

from __future__ import annotations

from pathlib import Path

from arian.application.context import ContextRequest
from arian.application.validator import ContextRequestValidator


class TestContextRequestValidator:
    """Tests for ContextRequestValidator.validate()."""

    def test_valid_request_passes(self, tmp_path: Path) -> None:
        """Verify a valid request passes validation."""
        (tmp_path / "src").mkdir()
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(paths=("src",), budget=5000, scope="merged")
        result = validator.validate(request)
        assert result.is_success is True

    def test_nonexistent_path_fails(self, tmp_path: Path) -> None:
        """Verify missing path returns failure."""
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(paths=("nonexistent",), scope="merged")
        result = validator.validate(request)
        assert result.is_success is False
        assert "Path does not exist" in result.message

    def test_negative_budget_fails(self, tmp_path: Path) -> None:
        """Verify negative budget returns failure."""
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(budget=-1, scope="merged")
        result = validator.validate(request)
        assert result.is_success is False
        assert "Budget must be positive" in result.message

    def test_zero_budget_fails(self, tmp_path: Path) -> None:
        """Verify zero budget returns failure."""
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(budget=0, scope="merged")
        result = validator.validate(request)
        assert result.is_success is False
        assert "Budget must be positive" in result.message

    def test_none_budget_passes(self, tmp_path: Path) -> None:
        """Verify None budget (unlimited) passes validation."""
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(budget=None, scope="merged")
        result = validator.validate(request)
        assert result.is_success is True

    def test_invalid_scope_fails(self, tmp_path: Path) -> None:
        """Verify invalid scope returns failure."""
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(scope="group")
        result = validator.validate(request)
        assert result.is_success is False
        assert "Invalid scope" in result.message

    def test_separate_scope_passes(self, tmp_path: Path) -> None:
        """Verify 'separate' scope passes validation."""
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(scope="separate")
        result = validator.validate(request)
        assert result.is_success is True

    def test_path_traversal_nonexistent_returns_failure(self, tmp_path: Path) -> None:
        """Verify traversal path that doesn't exist returns failure."""
        (tmp_path / "src").mkdir()
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(paths=("src/../../etc",), scope="merged")
        result = validator.validate(request)
        assert result.is_success is False
        assert "Path does not exist" in result.message

    def test_symlink_escape_returns_security_failure(self, tmp_path: Path) -> None:
        """Verify symlink pointing outside root returns failure."""
        outside = tmp_path.parent / "outside_root"
        outside.mkdir(exist_ok=True)
        (outside / "secret.txt").write_text("secret")
        link = tmp_path / "sneaky"
        link.symlink_to(outside)
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(paths=("sneaky",), scope="merged")
        result = validator.validate(request)
        assert result.is_success is False

    def test_default_root_is_none_lazy(self) -> None:
        """Verify default root is None (resolved lazily to cwd)."""
        validator = ContextRequestValidator()
        assert validator._root is None

    def test_empty_paths_and_no_budget_passes(self, tmp_path: Path) -> None:
        """Verify empty paths with no budget passes validation."""
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(paths=(), budget=None, scope="merged")
        result = validator.validate(request)
        assert result.is_success is True

    def test_budget_exceeding_max_fails(self, tmp_path: Path) -> None:
        """Verify budget exceeding MAX_TOKEN_BUDGET returns failure."""
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(budget=2_000_000, scope="merged")
        result = validator.validate(request)
        assert result.is_success is False
        assert "Budget exceeds maximum" in result.message

    def test_budget_at_max_passes(self, tmp_path: Path) -> None:
        """Verify budget exactly at MAX_TOKEN_BUDGET passes validation."""
        validator = ContextRequestValidator(a_root=tmp_path)
        request = ContextRequest(budget=1_000_000, scope="merged")
        result = validator.validate(request)
        assert result.is_success is True

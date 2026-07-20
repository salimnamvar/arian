"""Tests for error message sanitization."""

from __future__ import annotations

from arian.domain.shared.security import sanitize_error_message


class TestSanitizeErrorMessage:
    """Tests for sanitize_error_message()."""

    def test_no_root_returns_original(self) -> None:
        """Verify message is unchanged when no root is provided."""
        msg = "Error at /home/user/project/src/main.py"
        assert sanitize_error_message(msg) == msg

    def test_none_root_returns_original(self) -> None:
        """Verify message is unchanged when root is None."""
        msg = "Error at /home/user/project/src/main.py"
        assert sanitize_error_message(msg, a_root=None) == msg

    def test_root_replaced_with_repository(self) -> None:
        """Verify root path is replaced with <repository>."""
        msg = "Error at /home/user/project/src/main.py"
        result = sanitize_error_message(msg, a_root="/home/user/project")
        assert result == "Error at <repository>/src/main.py"
        assert "/home/user/project" not in result

    def test_multiple_occurrences_replaced(self) -> None:
        """Verify all occurrences of root are replaced."""
        msg = "File1: /home/proj/a.py, File2: /home/proj/b.py"
        result = sanitize_error_message(msg, a_root="/home/proj")
        assert result == "File1: <repository>/a.py, File2: <repository>/b.py"

    def test_empty_message(self) -> None:
        """Verify empty message is handled."""
        result = sanitize_error_message("", a_root="/home/proj")
        assert result == ""

    def test_root_not_in_message(self) -> None:
        """Verify no change when root is not present in message."""
        msg = "Some unrelated error"
        result = sanitize_error_message(msg, a_root="/home/proj")
        assert result == msg

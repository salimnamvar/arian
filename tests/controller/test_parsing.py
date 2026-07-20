"""Unit tests for CLI parsing utilities.

Tests for parse_budget, parse_groups, and validate_request extracted
from the controller into a dedicated parsing module.
"""

from __future__ import annotations

import pytest
import typer

from arian.application.context import ContextRequest
from arian.controller.cli.parsing import parse_budget
from arian.controller.cli.parsing import parse_groups
from arian.controller.cli.parsing import validate_request


class TestParseBudget:
    """Tests for the parse_budget utility."""

    def test_none_returns_none(self) -> None:
        """None input should return None (unlimited)."""
        assert parse_budget(None) is None

    def test_string_none_returns_none(self) -> None:
        """The string 'none' should return None (unlimited)."""
        assert parse_budget("none") is None
        assert parse_budget("None") is None
        assert parse_budget("NONE") is None

    def test_positive_integer_returns_int(self) -> None:
        """A positive integer string should return the int value."""
        assert parse_budget("1000") == 1000
        assert parse_budget("1") == 1

    def test_zero_exits(self) -> None:
        """A zero budget should cause typer.Exit."""
        with pytest.raises(typer.Exit):
            parse_budget("0")

    def test_negative_exits(self) -> None:
        """A negative budget should cause typer.Exit."""
        with pytest.raises(typer.Exit):
            parse_budget("-100")

    def test_non_numeric_exits(self) -> None:
        """A non-numeric string should cause typer.Exit."""
        with pytest.raises(typer.Exit):
            parse_budget("abc")

    def test_float_string_exits(self) -> None:
        """A float string should cause typer.Exit (not a valid int)."""
        with pytest.raises(typer.Exit):
            parse_budget("1.5")


class TestParseGroups:
    """Tests for the parse_groups utility."""

    def test_none_returns_empty_tuple(self) -> None:
        """None input should return an empty tuple."""
        assert parse_groups(None) == ()

    def test_empty_list_returns_empty_tuple(self) -> None:
        """An empty list should return an empty tuple."""
        assert parse_groups([]) == ()

    def test_single_group(self) -> None:
        """A single group string should produce one path-tuple."""
        result = parse_groups(["src/,lib/"])
        assert result == (("src/", "lib/"),)

    def test_multiple_groups(self) -> None:
        """Multiple group strings should produce multiple path-tuples."""
        result = parse_groups(["src/,lib/", "docs/"])
        assert result == (("src/", "lib/"), ("docs/",))

    def test_whitespace_stripped(self) -> None:
        """Paths should have surrounding whitespace stripped."""
        result = parse_groups([" src/ , lib/ "])
        assert result == (("src/", "lib/"),)

    def test_single_path_group(self) -> None:
        """A group with one path should produce a single-element tuple."""
        result = parse_groups(["src/"])
        assert result == (("src/",),)


class TestValidateRequest:
    """Tests for the validate_request utility."""

    def test_valid_request_passes(self) -> None:
        """A well-formed request should not raise."""
        request = ContextRequest(task="general", scope="merged")
        validate_request(request)

    def test_invalid_task_exits(self) -> None:
        """An invalid task name should cause typer.Exit."""
        request = ContextRequest(task="nonexistent_task")
        with pytest.raises(typer.Exit):
            validate_request(request)

    def test_invalid_scope_exits(self) -> None:
        """An invalid scope should cause typer.Exit."""
        request = ContextRequest(task="general", scope="bogus")
        with pytest.raises(typer.Exit):
            validate_request(request)

    def test_valid_scopes_accepted(self) -> None:
        """Both 'merged' and 'separate' scopes should be accepted."""
        for scope in ("merged", "separate"):
            request = ContextRequest(task="general", scope=scope)
            validate_request(request)

    def test_group_with_nonexistent_path_exits(self) -> None:
        """A group referencing a non-existent path should cause typer.Exit.

        Note: validate_request uses Path.cwd() as root, so this test
        verifies the validation logic exists without relying on cwd.
        """
        request = ContextRequest(
            task="general",
            scope="merged",
            group=(("this_path_definitely_does_not_exist_xyz123",),),
        )
        with pytest.raises(typer.Exit):
            validate_request(request)

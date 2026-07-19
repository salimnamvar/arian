"""Tests for output path resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from arian.infrastructure.output_path_resolver import resolve_output_path


def test_resolve_absolute_path() -> None:
    """Test resolving an absolute path."""
    result = resolve_output_path("/tmp/output.md")
    assert result == Path("/tmp/output.md")


def test_resolve_relative_path() -> None:
    """Test resolving a relative path."""
    result = resolve_output_path("output.md")
    assert result == Path.cwd() / "output.md"


def test_resolve_directory_appends_filename(tmp_path: Path) -> None:
    """Test that directory path gets context.md appended."""
    result = resolve_output_path(str(tmp_path))
    assert result == tmp_path / "context.md"


def test_resolve_dot_tmp_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that .tmp directory resolves to .tmp/context.md."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".tmp").mkdir()
    result = resolve_output_path(".tmp")
    assert result == tmp_path / ".tmp" / "context.md"
    assert not result.is_dir()

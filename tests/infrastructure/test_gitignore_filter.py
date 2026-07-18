"""Unit tests for gitignore filter."""

from __future__ import annotations

from pathlib import Path

from arian.infrastructure.gitignore_filter import PathFilter


def test_path_filter_include_by_default(tmp_path: Path) -> None:
    """Test that paths are included by default."""
    test_dir: Path = tmp_path / "included"
    test_dir.mkdir()

    pf = PathFilter(a_exclude=frozenset([".git"]))
    result: bool = pf.should_include(test_dir)
    assert result is True


def test_path_filter_excludes_directory(tmp_path: Path) -> None:
    """Test that excluded directories are filtered out."""
    excluded: Path = tmp_path / ".git"
    excluded.mkdir()

    pf = PathFilter(a_exclude=frozenset([".git"]))
    result: bool = pf.should_include(excluded)
    assert result is False


def test_path_filter_respects_gitignore(tmp_path: Path, monkeypatch) -> None:
    """Test that .gitignore patterns are respected."""
    gitignore: Path = tmp_path / ".gitignore"
    gitignore.write_text("*.log\nnode_modules/\n")

    # Monkeypatch Path.cwd() to return tmp_path
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    pf = PathFilter(a_exclude=frozenset([".git"]))

    # Files matching gitignore should be excluded
    log_file: Path = tmp_path / "test.log"
    log_file.touch()
    assert pf.should_include(log_file) is False

    # Files not matching gitignore should be included
    py_file: Path = tmp_path / "test.py"
    py_file.touch()
    assert pf.should_include(py_file) is True


def test_path_filter_no_gitignore(tmp_path: Path, monkeypatch) -> None:
    """Test that filter works when no .gitignore exists."""
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    pf = PathFilter(a_exclude=frozenset([".git"]), a_gitignore=True)
    test_file: Path = tmp_path / "test.py"
    test_file.touch()

    assert pf.should_include(test_file) is True


def test_path_filter_gitignore_disabled(tmp_path: Path, monkeypatch) -> None:
    """Test that gitignore check can be disabled."""
    gitignore: Path = tmp_path / ".gitignore"
    gitignore.write_text("*.log\n")

    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    pf = PathFilter(a_exclude=frozenset([".git"]), a_gitignore=False)
    log_file: Path = tmp_path / "test.log"
    log_file.touch()

    # Should include even though .gitignore says *.log
    assert pf.should_include(log_file) is True

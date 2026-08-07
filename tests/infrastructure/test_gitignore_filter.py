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


# ---------------------------------------------------------------------------
# Explicit-path override (RC-2)
# ---------------------------------------------------------------------------


def test_path_filter_explicit_path_bypasses_gitignore(tmp_path: Path, monkeypatch) -> None:
    """A path listed as explicit bypasses gitignore (``git add -f`` semantics)."""
    (tmp_path / ".gitignore").write_text("data/\n")
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    data_dir: Path = tmp_path / "data"
    data_dir.mkdir()
    data_file: Path = data_dir / "ct_x.yaml"
    data_file.touch()

    pf = PathFilter(
        a_exclude=frozenset([".git"]),
        a_explicit_paths=frozenset({data_dir}),
    )

    assert pf.should_include(data_file) is True
    # last_matched_pattern should be None because the file passed the explicit
    # override before the gitignore gate was evaluated.
    assert pf.last_matched_pattern is None


def test_path_filter_explicit_path_only_applies_to_subtree(tmp_path: Path, monkeypatch) -> None:
    """Explicit paths do not leak to siblings."""
    (tmp_path / ".gitignore").write_text("data/\n")
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    src_dir: Path = tmp_path / "src"
    src_dir.mkdir()
    data_dir: Path = tmp_path / "data"
    data_dir.mkdir()

    pf = PathFilter(
        a_exclude=frozenset([".git"]),
        a_explicit_paths=frozenset({src_dir}),
    )

    # src is explicit, data is not
    assert pf.should_include(src_dir / "ok.py") is True
    # data is still blocked by gitignore
    assert pf.should_include(data_dir / "ct_x.yaml") is False
    assert pf.last_matched_pattern == "data/"


def test_path_filter_set_explicit_paths_updates_filter(tmp_path: Path, monkeypatch) -> None:
    """``set_explicit_paths`` mutates the allow-list on a live filter."""
    (tmp_path / ".gitignore").write_text("data/\n")
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    data_dir: Path = tmp_path / "data"
    data_dir.mkdir()
    data_file: Path = data_dir / "ct_x.yaml"
    data_file.touch()

    pf = PathFilter(a_exclude=frozenset([".git"]))
    assert pf.should_include(data_file) is False

    pf.set_explicit_paths(frozenset({data_dir}))
    assert pf.should_include(data_file) is True


# ---------------------------------------------------------------------------
# Pattern capture (RC-5)
# ---------------------------------------------------------------------------


def test_path_filter_last_matched_pattern_is_set(tmp_path: Path, monkeypatch) -> None:
    """``last_matched_pattern`` is set to the offending gitignore pattern."""
    (tmp_path / ".gitignore").write_text("*.log\n!keep.log\nbuild/\n")
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    pf = PathFilter(a_exclude=frozenset([".git"]))
    pf.should_include(tmp_path / "spam.log")
    assert pf.last_matched_pattern == "*.log"

    pf.should_include(tmp_path / "build" / "out.bin")
    assert pf.last_matched_pattern == "build/"


def test_path_filter_last_matched_pattern_exclude_fallback(tmp_path: Path) -> None:
    """When the directory-name exclude fires, the pattern is ``<exclude>``."""
    pf = PathFilter(a_exclude=frozenset([".git"]))
    pf.should_include(Path("/tmp/.git/objects/abc"))
    assert pf.last_matched_pattern == "<exclude>"


def test_path_filter_last_matched_pattern_reset_on_include(tmp_path: Path, monkeypatch) -> None:
    """A subsequent include resets the captured pattern."""
    (tmp_path / ".gitignore").write_text("*.log\n")
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    pf = PathFilter(a_exclude=frozenset([".git"]))
    pf.should_include(tmp_path / "x.log")
    assert pf.last_matched_pattern == "*.log"

    pf.should_include(tmp_path / "x.py")
    assert pf.last_matched_pattern is None


# ---------------------------------------------------------------------------
# Negation patterns (RC-4)
# ---------------------------------------------------------------------------


def test_path_filter_supports_negation_pattern(tmp_path: Path, monkeypatch) -> None:
    """``!pattern`` re-includes a path that an earlier rule ignored."""
    (tmp_path / ".gitignore").write_text("*.log\n!keep.log\n")
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    pf = PathFilter(a_exclude=frozenset([".git"]))
    assert pf.should_include(tmp_path / "debug.log") is False
    assert pf.should_include(tmp_path / "keep.log") is True


# ---------------------------------------------------------------------------
# Nested .gitignore (RC-4)
# ---------------------------------------------------------------------------


def test_path_filter_nested_gitignore_loads_ancestor_rules(tmp_path: Path, monkeypatch) -> None:
    """When ``nested_gitignore`` is on, ancestor ``.gitignore`` files apply."""
    nested_dir: Path = tmp_path / "sub" / "deeper"
    nested_dir.mkdir(parents=True)
    (tmp_path / ".gitignore").write_text("root_only.log\n")
    (nested_dir / ".gitignore").write_text("deep_only.log\n")

    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    pf_default = PathFilter(a_exclude=frozenset([".git"]))
    pf_nested = PathFilter(a_exclude=frozenset([".git"]), a_nested_gitignore=True)

    # default: only the cwd .gitignore is honored
    assert pf_default.should_include(tmp_path / "root_only.log") is False
    assert pf_default.should_include(nested_dir / "deep_only.log") is True

    # nested: both files are honored
    assert pf_nested.should_include(tmp_path / "root_only.log") is False
    assert pf_nested.should_include(nested_dir / "deep_only.log") is False


# ---------------------------------------------------------------------------
# Path-outside-cwd no longer silently swallowed (RC-4)
# ---------------------------------------------------------------------------


def test_path_filter_path_outside_cwd_is_included(tmp_path: Path, monkeypatch) -> None:
    """A path outside CWD no longer silently bypasses gitignore — it is included."""
    (tmp_path / ".gitignore").write_text("*.log\n")
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    pf = PathFilter(a_exclude=frozenset([".git"]))
    # /etc is outside cwd but not under any excluded name — must be included.
    assert pf.should_include(Path("/etc/hostname")) is True

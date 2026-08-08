"""Tests for CollectionStats invariant and skip counts."""

from __future__ import annotations

from pathlib import Path

from arian.domain.repository.models import CollectionStats
from arian.infrastructure.gitignore_filter import GitignoreOptions
from arian.repository.filesystem.collector import FileCollector


def test_stats_initial_zero() -> None:
    """Fresh CollectionStats has all zeros."""
    stats = CollectionStats()
    assert stats.total_scanned == 0
    assert stats.collected == 0
    assert stats.skipped_binary == 0
    assert stats.skipped_size == 0
    assert stats.skipped_gitignore == 0
    assert stats.skipped_permission == 0
    assert stats.skipped_error == 0
    assert stats.skipped_by_extension == 0
    assert stats.unknown_language == 0
    assert stats.skipped_gitignore_by_pattern == {}


def test_stats_invariant_empty() -> None:
    """Empty stats satisfy invariant: 0 == 0 + sum(0)."""
    stats = CollectionStats()
    total_skipped = (
        stats.skipped_binary
        + stats.skipped_size
        + stats.skipped_gitignore
        + stats.skipped_permission
        + stats.skipped_error
        + stats.skipped_by_extension
    )
    assert stats.total_scanned == stats.collected + total_skipped


async def test_collector_collects_text_files(tmp_path: Path) -> None:
    """Collector picks up text files with no extension filter."""
    (tmp_path / "hello.py").write_text("print('hello')")
    (tmp_path / "data.json").write_text('{"key": "value"}')
    (tmp_path / "readme.md").write_text("# Hello")

    collector = FileCollector(a_extensions=None, a_exclude=frozenset())
    files = await collector.collect(tmp_path)

    assert len(files) == 3
    assert collector.stats.collected == 3
    assert collector.stats.total_scanned == 3


async def test_collector_skips_binary(tmp_path: Path) -> None:
    """Binary files are skipped and counted."""
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    (tmp_path / "hello.py").write_text("print('hello')")

    collector = FileCollector(a_extensions=None, a_exclude=frozenset())
    files = await collector.collect(tmp_path)

    assert len(files) == 1
    assert collector.stats.skipped_binary == 1
    assert collector.stats.collected == 1


async def test_collector_extension_narrowing(tmp_path: Path) -> None:
    """Extension filter skips non-matching files."""
    (tmp_path / "hello.py").write_text("print('hello')")
    (tmp_path / "data.json").write_text('{"key": "value"}')

    collector = FileCollector(a_extensions=frozenset({".py"}), a_exclude=frozenset())
    files = await collector.collect(tmp_path)

    assert len(files) == 1
    assert files[0].path == "hello.py"
    assert collector.stats.skipped_by_extension == 1


async def test_collector_extension_narrowing_with_dot_prefix(tmp_path: Path) -> None:
    """Extension filter requires dot-prefixed extensions."""
    (tmp_path / "hello.py").write_text("print('hello')")
    (tmp_path / "data.json").write_text('{"key": "value"}')

    collector = FileCollector(a_extensions=frozenset({".py"}), a_exclude=frozenset())
    files = await collector.collect(tmp_path)

    assert len(files) == 1
    assert files[0].path == "hello.py"


async def test_stats_invariant_after_collect(tmp_path: Path) -> None:
    """Stats satisfy invariant after collection."""
    (tmp_path / "hello.py").write_text("print('hello')")
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    collector = FileCollector(a_extensions=None, a_exclude=frozenset())
    await collector.collect(tmp_path)

    stats = collector.stats
    total_skipped = (
        stats.skipped_binary
        + stats.skipped_size
        + stats.skipped_gitignore
        + stats.skipped_permission
        + stats.skipped_error
        + stats.skipped_by_extension
    )
    assert stats.total_scanned == stats.collected + total_skipped


async def test_language_computed_once(tmp_path: Path) -> None:
    """Language is computed at collection time and stored in RepositoryFile."""
    (tmp_path / "hello.py").write_text("print('hello')")

    collector = FileCollector(a_extensions=None, a_exclude=frozenset())
    files = await collector.collect(tmp_path)

    assert len(files) == 1
    assert files[0].language == "python"


# ---------------------------------------------------------------------------
# Gitignore interaction (RC-2, RC-3, RC-4, RC-5)
# ---------------------------------------------------------------------------


async def test_collector_respects_gitignore(tmp_path: Path, monkeypatch) -> None:
    """Files matching ``.gitignore`` are skipped and tallied."""
    (tmp_path / ".gitignore").write_text("data/\n")
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    data_dir: Path = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "ct_x.yaml").write_text("kind: DataContract\n")
    (data_dir / "ct_y.yaml").write_text("kind: DataContract\n")
    (tmp_path / "readme.md").write_text("# hi\n")

    collector = FileCollector(a_extensions=None, a_exclude=frozenset())
    files = await collector.collect(tmp_path)

    # The .gitignore file is itself a text file and is collected. The
    # two yaml files in data/ are the ones the rule is meant to catch.
    paths = {f.path for f in files}
    assert "readme.md" in paths
    assert not any(p.startswith("data/") for p in paths)
    assert collector.stats.skipped_gitignore == 2
    assert collector.stats.skipped_gitignore_by_pattern == {"data/": 2}
    # Invariant: per-pattern tally sums to the integer counter
    assert sum(collector.stats.skipped_gitignore_by_pattern.values()) == collector.stats.skipped_gitignore


async def test_collector_use_gitignore_false_disables_filter(tmp_path: Path, monkeypatch) -> None:
    """``a_use_gitignore=False`` collects files in gitignored directories."""
    (tmp_path / ".gitignore").write_text("data/\n")
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    data_dir: Path = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "ct_x.yaml").write_text("kind: DataContract\n")

    collector = FileCollector(
        a_extensions=None,
        a_exclude=frozenset(),
        a_gitignore_options=GitignoreOptions(enabled=False),
    )
    files = await collector.collect(tmp_path)

    paths = {f.path for f in files}
    assert any(p.endswith("ct_x.yaml") for p in paths)
    assert collector.stats.skipped_gitignore == 0


async def test_collector_explicit_paths_bypass_gitignore(tmp_path: Path, monkeypatch) -> None:
    """``a_explicit_paths`` lets a CLI-named path bypass gitignore (git add -f)."""
    (tmp_path / ".gitignore").write_text("data/\n")
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    data_dir: Path = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "ct_x.yaml").write_text("kind: DataContract\n")
    (data_dir / "ct_y.yaml").write_text("kind: DataContract\n")

    collector = FileCollector(a_extensions=None, a_exclude=frozenset())
    files = await collector.collect(
        data_dir,
        a_root=tmp_path,
        a_explicit_paths=frozenset({data_dir}),
    )

    assert len(files) == 2
    assert collector.stats.skipped_gitignore == 0
    assert collector.stats.collected == 2


async def test_collector_explicit_paths_does_not_leak(tmp_path: Path, monkeypatch) -> None:
    """Explicit override only applies to the named subtree."""
    (tmp_path / ".gitignore").write_text("data/\n")
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    data_dir: Path = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "ct_x.yaml").write_text("kind: DataContract\n")
    secret_dir: Path = tmp_path / "secret"
    secret_dir.mkdir()
    (secret_dir / "x.yaml").write_text("kind: DataContract\n")

    # Only `data` is explicit; `secret` is not, but it isn't gitignored either,
    # so both should be collected. The point is that explicit doesn't filter
    # out other paths.
    collector = FileCollector(a_extensions=None, a_exclude=frozenset())
    files = await collector.collect(
        tmp_path,
        a_explicit_paths=frozenset({data_dir}),
    )

    paths = {f.path for f in files}
    assert "data/ct_x.yaml" in paths
    assert "secret/x.yaml" in paths


async def test_collector_explicit_path_dir_level_bypass(tmp_path: Path, monkeypatch) -> None:
    """Recursive scan into an explicit dir short-circuits the dir-level gate.

    The bug this guards against: ``_collect_directory`` previously checked
    ``should_include`` on the entry dir and skipped it before recursing,
    even when the dir was named explicitly. With the fix, an explicit dir
    passes through without ever being looked up in gitignore.
    """
    (tmp_path / ".gitignore").write_text("data/\n")
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    data_dir: Path = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "ct_x.yaml").write_text("kind: DataContract\n")

    # Build a collector with a normal use_gitignore=True; then call collect
    # with the explicit-path override.
    collector = FileCollector(a_extensions=None, a_exclude=frozenset())
    files = await collector.collect(
        data_dir,
        a_explicit_paths=frozenset({data_dir}),
    )

    # The dir was named by the user, so no file inside should be classified
    # as skipped_gitignore — even the dir-level recursion gate.
    assert collector.stats.skipped_gitignore == 0
    assert collector.stats.collected == 1
    assert files[0].path.endswith("ct_x.yaml")


async def test_collector_pattern_tally_attributes_each_file(tmp_path: Path, monkeypatch) -> None:
    """Different patterns are tracked separately in the tally."""
    (tmp_path / ".gitignore").write_text("*.log\nbuild/\n")
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    (tmp_path / "a.log").write_text("x")
    (tmp_path / "b.log").write_text("x")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "out.bin").write_text("x")
    (tmp_path / "ok.py").write_text("x")

    collector = FileCollector(a_extensions=None, a_exclude=frozenset())
    await collector.collect(tmp_path)

    assert collector.stats.skipped_gitignore == 3
    assert collector.stats.skipped_gitignore_by_pattern == {"*.log": 2, "build/": 1}


async def test_collector_dir_exclude_falls_back_to_exclude_placeholder(tmp_path: Path) -> None:
    """When the directory-name ``exclude`` set trips, the pattern is ``<exclude>``."""
    git_dir: Path = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")

    collector = FileCollector(a_extensions=None, a_exclude=frozenset({".git"}))
    files = await collector.collect(tmp_path)

    assert files == []
    assert collector.stats.skipped_gitignore == 0  # the dir was never recursed into
    # The "<exclude>" tally is only incremented when an individual file is
    # reached and its path-part matches the exclude set, which is not the
    # case here (the .git dir is rejected at the dir level, no file scan).
    assert collector.stats.skipped_gitignore_by_pattern == {}


async def test_collector_nested_gitignore(tmp_path: Path, monkeypatch) -> None:
    """``a_nested_gitignore=True`` walks ancestor ``.gitignore`` files."""
    nested: Path = tmp_path / "sub" / "deeper"
    nested.mkdir(parents=True)
    (tmp_path / ".gitignore").write_text("root.log\n")
    (nested / ".gitignore").write_text("deep.log\n")
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    (tmp_path / "root.log").write_text("x")
    (nested / "deep.log").write_text("x")

    collector_default = FileCollector(a_extensions=None, a_exclude=frozenset())
    await collector_default.collect(tmp_path)
    # Only the cwd .gitignore applies.
    assert collector_default.stats.skipped_gitignore == 1
    assert collector_default.stats.skipped_gitignore_by_pattern == {"root.log": 1}

    collector_nested = FileCollector(
        a_extensions=None,
        a_exclude=frozenset(),
        a_gitignore_options=GitignoreOptions(nested=True),
    )
    await collector_nested.collect(tmp_path)
    # Both .gitignore files apply.
    assert collector_nested.stats.skipped_gitignore == 2
    assert collector_nested.stats.skipped_gitignore_by_pattern == {"root.log": 1, "deep.log": 1}

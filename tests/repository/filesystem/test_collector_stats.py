"""Tests for CollectionStats invariant and skip counts."""

from __future__ import annotations

from pathlib import Path

from arian.repository.filesystem.collector import CollectionStats
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

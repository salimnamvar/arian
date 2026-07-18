"""Unit tests for repository layer."""

from __future__ import annotations

import pytest
from pathlib import Path

from arian.domain.exceptions import InputNotFoundError
from arian.domain.models import Document
from arian.repository.collector import FilesystemCollector
from arian.repository.writer import FileWriter


def test_filesystem_collector_single_file(tmp_path: Path) -> None:
    """Test collecting a single file."""
    test_file: Path = tmp_path / "test.py"
    test_file.write_text("print('hello')", encoding="utf-8")

    collector = FilesystemCollector(
        a_extensions=frozenset([".py"]),
        a_exclude=frozenset([".git"]),
        a_tokenizer=lambda s: len(s),
    )

    result: list[Document] = collector.collect([str(test_file)])
    assert len(result) == 1
    assert result[0].path == str(test_file)
    assert result[0].content == "print('hello')"
    assert result[0].tokens == len("print('hello')")
    assert result[0].language == "python"


def test_filesystem_collector_directory(tmp_path: Path) -> None:
    """Test collecting from a directory."""
    (tmp_path / "file1.py").write_text("content1", encoding="utf-8")
    (tmp_path / "file2.md").write_text("content2", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "internal.py").write_text("git_content", encoding="utf-8")

    collector = FilesystemCollector(
        a_extensions=frozenset([".py", ".md"]),
        a_exclude=frozenset([".git"]),
        a_tokenizer=lambda s: len(s),
    )

    result: list[Document] = collector.collect([str(tmp_path)])
    paths: list[str] = [d.path for d in result]
    assert len(result) == 2
    assert str(tmp_path / "file1.py") in paths
    assert str(tmp_path / "file2.md") in paths
    # git internal file should be excluded
    assert not any(".git" in p for p in paths)


def test_filesystem_collector_excluded_directory(tmp_path: Path) -> None:
    """Test that excluded directories are skipped."""
    excluded_dir: Path = tmp_path / "archived"
    excluded_dir.mkdir()
    (excluded_dir / "old.py").write_text("old code", encoding="utf-8")
    (tmp_path / "current.py").write_text("current code", encoding="utf-8")

    collector = FilesystemCollector(
        a_extensions=frozenset([".py"]),
        a_exclude=frozenset(["archived"]),
        a_tokenizer=lambda s: len(s),
    )

    result: list[Document] = collector.collect([str(tmp_path)])
    assert len(result) == 1
    assert result[0].path == str(tmp_path / "current.py")


def test_filesystem_collector_missing_path(tmp_path: Path) -> None:
    """Test that non-existent path raises InputNotFoundError."""
    collector = FilesystemCollector(
        a_extensions=frozenset([".py"]),
        a_exclude=frozenset([]),
        a_tokenizer=len,
    )

    with pytest.raises(InputNotFoundError) as exc_info:
        collector.collect([str(tmp_path / "nonexistent")])
    assert "nonexistent" in exc_info.value.message


def test_filesystem_collector_unsupported_extension(tmp_path: Path) -> None:
    """Test that unsupported extensions are skipped."""
    test_file: Path = tmp_path / "test.rs"
    test_file.write_text("rust code", encoding="utf-8")

    collector = FilesystemCollector(
        a_extensions=frozenset([".py"]),
        a_exclude=frozenset([]),
        a_tokenizer=len,
    )

    result: list[Document] = collector.collect([str(test_file)])
    assert len(result) == 0


def test_file_writer_single_file(tmp_path: Path) -> None:
    """Test writing to a single output file."""
    writer = FileWriter(a_base_path=tmp_path)
    output_path: Path = tmp_path / "output.md"

    result: Path = writer.write("content", output_path)
    assert result == output_path
    assert output_path.read_text(encoding="utf-8") == "content"


def test_file_writer_creates_parent_directories(tmp_path: Path) -> None:
    """Test that writer creates parent directories."""
    writer = FileWriter(a_base_path=tmp_path)
    output_path: Path = tmp_path / "subdir" / "nested" / "output.md"

    result: Path = writer.write("nested content", output_path)
    assert output_path.exists()
    assert result == output_path


def test_file_writer_numbered_files(tmp_path: Path) -> None:
    """Test writing numbered output files."""
    writer = FileWriter(a_base_path=tmp_path)
    base_path: Path = tmp_path / "merged.md"

    result: list[Path] = writer.write_numbered(["chunk1", "chunk2"], base_path)
    assert len(result) == 2
    assert result[0].name == "merged.1.md"
    assert result[1].name == "merged.2.md"
    assert (tmp_path / "merged.1.md").read_text() == "chunk1"
    assert (tmp_path / "merged.2.md").read_text() == "chunk2"


def test_file_writer_numbered_creates_parent_directories(tmp_path: Path) -> None:
    """Test that numbered writer creates parent directories."""
    writer = FileWriter(a_base_path=tmp_path)
    base_path: Path = tmp_path / "subdir" / "merged.md"

    result: list[Path] = writer.write_numbered(["content"], base_path)
    assert len(result) == 1
    assert base_path.parent.exists()


def test_file_writer_numbered_default_suffix(tmp_path: Path) -> None:
    """Test that numbered files get .md suffix when base has no suffix."""
    writer = FileWriter(a_base_path=tmp_path)
    base_path: Path = tmp_path / "output"

    result: list[Path] = writer.write_numbered(["content"], base_path)
    assert len(result) == 1
    assert result[0].name == "output.1.md"

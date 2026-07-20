"""Tests for atomic FileOutputWriter."""

from __future__ import annotations

from pathlib import Path

from arian.infrastructure.file_output_writer import FileOutputWriter


class TestFileOutputWriter:
    """Tests for atomic write semantics."""

    def test_writes_content(self, tmp_path: Path) -> None:
        """Verify content is written to the target path."""
        target = tmp_path / "out.md"
        writer = FileOutputWriter()
        writer.write(str(target), "hello world")
        assert target.read_text(encoding="utf-8") == "hello world"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Verify nested parent directories are created."""
        target = tmp_path / "a" / "b" / "out.md"
        writer = FileOutputWriter()
        writer.write(str(target), "nested")
        assert target.read_text(encoding="utf-8") == "nested"

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        """Verify existing files are replaced atomically."""
        target = tmp_path / "out.md"
        target.write_text("old", encoding="utf-8")
        writer = FileOutputWriter()
        writer.write(str(target), "new")
        assert target.read_text(encoding="utf-8") == "new"

    def test_no_temp_files_left_after_success(self, tmp_path: Path) -> None:
        """Verify temp files are cleaned up after a successful write."""
        target = tmp_path / "out.md"
        writer = FileOutputWriter()
        writer.write(str(target), "clean")
        temps = list(tmp_path.glob(".out.md.*.tmp"))
        assert temps == []

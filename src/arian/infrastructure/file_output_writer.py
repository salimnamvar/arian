"""File-based output writer — infrastructure adapter."""

from __future__ import annotations

from pathlib import Path


class FileOutputWriter:
    """Writes rendered content to files on disk."""

    def write(self, a_path: str, a_content: str) -> None:
        """Write rendered content to a file, creating parent directories.

        Args:
            a_path: Output file path.
            a_content: Rendered content string.
        """
        path = Path(a_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(a_content, encoding="utf-8")

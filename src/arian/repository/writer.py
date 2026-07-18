"""File writer for output files."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FileWriter:
    """Writes rendered content to output files.

    Implements WriterProtocol.
    """

    def __init__(self, a_base_path: Path) -> None:
        """Initialize writer.

        Args:
            a_base_path: Base output directory path.
        """
        self._base_path: Path = a_base_path

    def write(self, a_content: str, a_path: Path) -> Path:
        """Write content to single output file.

        Args:
            a_content: Content to write.
            a_path: Output file path.

        Returns:
            Path that was written.
        """
        a_path.parent.mkdir(parents=True, exist_ok=True)
        a_path.write_text(a_content, encoding="utf-8")
        logger.debug("Wrote %d bytes to %s", len(a_content), a_path)
        return a_path

    def write_numbered(self, a_chunks: list[str], a_base_path: Path) -> list[Path]:
        """Write numbered output files.

        Args:
            a_chunks: Content chunks to write.
            a_base_path: Base path for output files.

        Returns:
            List of written paths.
        """
        a_base_path.parent.mkdir(parents=True, exist_ok=True)
        stem: str = a_base_path.stem
        suffix: str = a_base_path.suffix or ".md"
        written: list[Path] = []

        for i, chunk in enumerate(a_chunks, start=1):
            out_path: Path = a_base_path.parent / f"{stem}.{i}{suffix}"
            out_path.write_text(chunk, encoding="utf-8")
            written.append(out_path)

        return written

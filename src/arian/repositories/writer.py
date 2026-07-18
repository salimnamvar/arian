"""File writer for output files."""

from __future__ import annotations

import asyncio
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

    async def write(self, a_content: str, a_path: Path) -> Path:
        """Write content to single output file.

        Args:
            a_content: Content to write.
            a_path: Output file path.

        Returns:
            Path that was written.
        """
        await asyncio.to_thread(a_path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(a_path.write_text, a_content, encoding="utf-8")
        logger.debug("Wrote %d bytes to %s", len(a_content), a_path)
        return a_path

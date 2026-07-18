"""Repository protocols for Arian.

Defines protocols (interfaces) for repository implementations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from arian.domain.models import Document


class CollectorProtocol(Protocol):
    """Collects documents from input paths.

    Protocol for document collection implementations.
    """

    def collect(self, a_inputs: list[str]) -> list[Document]:
        """Collect documents from input paths.

        Args:
            a_inputs: List of input paths (files or directories).

        Returns:
            List of collected documents.
        """
        ...


class WriterProtocol(Protocol):
    """Writes rendered content to output."""

    def write(self, a_content: str, a_path: Path) -> Path:
        """Write content to single output file.

        Args:
            a_content: Content to write.
            a_path: Output file path.

        Returns:
            Path that was written.
        """
        ...

    def write_numbered(self, a_chunks: list[str], a_base_path: Path) -> list[Path]:
        """Write numbered output files.

        Args:
            a_chunks: Content chunks to write.
            a_base_path: Base path for output files.

        Returns:
            List of written paths.
        """
        ...

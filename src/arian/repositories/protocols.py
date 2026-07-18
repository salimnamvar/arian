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

    async def collect(self, a_inputs: list[str]) -> list[Document]:
        """Collect documents from input paths.

        Args:
            a_inputs: List of input paths (files or directories).

        Returns:
            List of collected documents.
        """
        ...


class WriterProtocol(Protocol):
    """Writes rendered content to output."""

    async def write(self, a_content: str, a_path: Path) -> Path:
        """Write content to single output file.

        Args:
            a_content: Content to write.
            a_path: Output file path.

        Returns:
            Path that was written.
        """
        ...

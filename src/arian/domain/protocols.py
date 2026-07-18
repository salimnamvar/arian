"""Domain protocols for Arian."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from arian.domain.repository.models import Symbol
from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import FileRole


class LanguageAnalyzerProtocol(Protocol):
    """Language-specific code analysis interface.

    Implementations provide language-aware symbol extraction,
    import detection, public API extraction, and content compression.
    """

    def extract_symbols(self, a_content: str, a_path: Path) -> list[Symbol]:
        """Extract code symbols from source content.

        Args:
            a_content: Source code content.
            a_path: File path for context.

        Returns:
            List of extracted symbols.
        """
        ...

    def extract_imports(self, a_content: str) -> list[str]:
        """Extract import statements from source content.

        Args:
            a_content: Source code content.

        Returns:
            List of imported module paths.
        """
        ...

    def extract_public_api(self, a_content: str) -> str:
        """Extract public API surface from source content.

        Args:
            a_content: Source code content.

        Returns:
            String representation of the public API.
        """
        ...

    def compress(self, a_content: str, a_level: CompressionLevel) -> str:
        """Compress source content according to compression level.

        Args:
            a_content: Source code content.
            a_level: Desired compression level.

        Returns:
            Compressed content string.
        """
        ...

    def strip_comments(self, a_content: str) -> str:
        """Strip comments from source content.

        Args:
            a_content: Source code content.

        Returns:
            Content with comments removed.
        """
        ...


class FileClassifierProtocol(Protocol):
    """File classification interface.

    Implementations classify files by role and importance.
    """

    def classify(self, a_path: str) -> tuple[FileRole, int, CompressionLevel]:
        """Classify a file path into role, importance, and compression.

        Args:
            a_path: Relative file path.

        Returns:
            Tuple of (role, importance, compression_level).
        """
        ...

    def get_role(self, a_path: str) -> FileRole:
        """Get the file role for a path.

        Args:
            a_path: Relative file path.

        Returns:
            Detected file role.
        """
        ...

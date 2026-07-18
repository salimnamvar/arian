"""File classifier for role detection and importance scoring."""

from __future__ import annotations

from pathlib import Path

from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import FileRole

_README_NAMES: frozenset[str] = frozenset(
    {"readme", "readme.md", "readme.rst", "readme.txt", "contributing", "contributing.md"},
)
_ENTRY_NAMES: frozenset[str] = frozenset(
    {"main.py", "__main__.py", "app.py", "cli.py"},
)
_CONFIG_NAMES: frozenset[str] = frozenset(
    {
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "package.json",
        "tsconfig.json",
        "cargo.toml",
        "go.mod",
        "makefile",
        "dockerfile",
        ".env",
        ".env.example",
    },
)
_GENERATED_PARTS: frozenset[str] = frozenset(
    {"migrations", "generated", "__generated__", "vendor", "node_modules"},
)
_CONFIG_SUFFIXES: frozenset[str] = frozenset({".toml", ".yaml", ".yml", ".ini", ".cfg"})
_DOC_SUFFIXES: frozenset[str] = frozenset({".md", ".rst"})
_DOC_PARTS: frozenset[str] = frozenset({"docs", "doc"})
_TEST_PARTS: frozenset[str] = frozenset({"test", "tests", "testing"})
_UTIL_PARTS: frozenset[str] = frozenset({"util", "utils", "utility", "helpers", "common"})

_ROLE_IMPORTANCE: dict[FileRole, int] = {
    FileRole.README: 0,
    FileRole.DOCUMENTATION: 1,
    FileRole.ENTRY_POINT: 1,
    FileRole.CONFIGURATION: 2,
    FileRole.DOMAIN: 2,
    FileRole.SERVICE: 3,
    FileRole.INFRASTRUCTURE: 4,
    FileRole.UTILITY: 5,
    FileRole.UNKNOWN: 6,
    FileRole.TEST: 7,
    FileRole.GENERATED: 9,
}

_ROLE_COMPRESSION: dict[FileRole, CompressionLevel] = {
    FileRole.README: CompressionLevel.FULL,
    FileRole.DOCUMENTATION: CompressionLevel.FULL,
    FileRole.ENTRY_POINT: CompressionLevel.FULL,
    FileRole.CONFIGURATION: CompressionLevel.FULL,
    FileRole.DOMAIN: CompressionLevel.FULL,
    FileRole.SERVICE: CompressionLevel.FULL,
    FileRole.INFRASTRUCTURE: CompressionLevel.FULL,
    FileRole.UTILITY: CompressionLevel.SIGNATURES,
    FileRole.UNKNOWN: CompressionLevel.FULL,
    FileRole.TEST: CompressionLevel.SIGNATURES,
    FileRole.GENERATED: CompressionLevel.STRUCTURE,
}


class FileClassifier:
    """Classifies files by role and importance for context planning.

    Analyzes file paths and names to determine their role in the
    repository architecture and assigns importance scores.
    """

    def classify(self, a_path: str) -> tuple[FileRole, int, CompressionLevel]:
        """Classify a file path into role, importance, and compression.

        Args:
            a_path: Relative file path.

        Returns:
            Tuple of (role, importance, compression_level).
        """
        path: Path = Path(a_path)
        name_lower: str = path.name.lower()
        parts_lower: tuple[str, ...] = tuple(p.lower() for p in path.parts)
        suffix: str = path.suffix.lower()

        role: FileRole
        importance: int
        compression: CompressionLevel
        role, importance, compression = self._classify_parts(name_lower, parts_lower, suffix)

        return role, importance, compression

    def get_role(self, a_path: str) -> FileRole:
        """Get the file role for a path.

        Args:
            a_path: Relative file path.

        Returns:
            Detected file role.
        """
        role: FileRole
        _importance: int
        _compression: CompressionLevel
        role, _importance, _compression = self.classify(a_path)
        return role

    def get_importance(self, a_path: str) -> int:
        """Get the importance score for a path.

        Args:
            a_path: Relative file path.

        Returns:
            Importance score (0=highest, 100=lowest).
        """
        _role: FileRole
        importance: int
        _compression: CompressionLevel
        _role, importance, _compression = self.classify(a_path)
        return importance

    def _classify_parts(
        self,
        a_name: str,
        a_parts: tuple[str, ...],
        a_suffix: str,
    ) -> tuple[FileRole, int, CompressionLevel]:
        """Determine role, importance, and compression from path parts.

        Args:
            a_name: Lowercased file name.
            a_parts: Lowercased path parts.
            a_suffix: Lowercased file suffix.

        Returns:
            Tuple of (role, importance, compression).
        """
        result: tuple[FileRole, int, CompressionLevel]
        if a_name in _README_NAMES or a_name.startswith("readme"):
            result = (FileRole.README, 0, CompressionLevel.FULL)
        elif any(part in _DOC_PARTS for part in a_parts) or a_suffix in _DOC_SUFFIXES:
            result = (FileRole.DOCUMENTATION, 1, CompressionLevel.FULL)
        elif a_name in _ENTRY_NAMES:
            result = (FileRole.ENTRY_POINT, 1, CompressionLevel.FULL)
        elif a_name in _CONFIG_NAMES or a_suffix in _CONFIG_SUFFIXES:
            result = (FileRole.CONFIGURATION, 2, CompressionLevel.FULL)
        elif any(part in _GENERATED_PARTS for part in a_parts):
            result = (FileRole.GENERATED, 9, CompressionLevel.STRUCTURE)
        elif any(part in _TEST_PARTS for part in a_parts) or a_name.startswith("test_"):
            result = (FileRole.TEST, 7, CompressionLevel.SIGNATURES)
        else:
            result = self._classify_layer(a_parts)
        return result

    def _classify_layer(self, a_parts: tuple[str, ...]) -> tuple[FileRole, int, CompressionLevel]:
        """Classify architectural layer from path parts.

        Args:
            a_parts: Lowercased path parts.

        Returns:
            Tuple of (role, importance, compression).
        """
        result: tuple[FileRole, int, CompressionLevel]
        if "domain" in a_parts:
            result = (FileRole.DOMAIN, 2, CompressionLevel.FULL)
        elif "service" in a_parts or "services" in a_parts:
            result = (FileRole.SERVICE, 3, CompressionLevel.FULL)
        elif "infrastructure" in a_parts or "infra" in a_parts:
            result = (FileRole.INFRASTRUCTURE, 4, CompressionLevel.FULL)
        elif any(part in _UTIL_PARTS for part in a_parts):
            result = (FileRole.UTILITY, 5, CompressionLevel.SIGNATURES)
        else:
            result = (FileRole.UNKNOWN, 6, CompressionLevel.FULL)
        return result

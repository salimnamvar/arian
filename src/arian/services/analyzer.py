"""Context analyzer for file classification and importance ordering."""

from __future__ import annotations

from pathlib import Path

from arian.domain.enums import FileRole
from arian.domain.models import FULL
from arian.domain.models import SIGNATURES
from arian.domain.models import STRUCTURE_ONLY
from arian.domain.models import CompressionLevel
from arian.domain.models import Document
from arian.domain.models import FileClassification

_README_NAMES: frozenset[str] = frozenset(
    {"readme", "readme.md", "readme.rst", "readme.txt", "contributing", "contributing.md"},
)
_ENTRY_NAMES: frozenset[str] = frozenset(
    {"main.py", "__main__.py", "app.py", "cli.py", "__init__.py"},
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


class ContextAnalyzer:
    """Classifies files by role and importance for context engineering."""

    def classify_file(self, a_path: str) -> FileClassification:
        """Classify a file path into role, importance, and compression.

        Args:
            a_path: Filesystem path of the file.

        Returns:
            FileClassification with role, importance, and compression level.
        """
        path: Path = Path(a_path)
        name_lower: str = path.name.lower()
        parts_lower: tuple[str, ...] = tuple(p.lower() for p in path.parts)
        suffix: str = path.suffix.lower()

        role: FileRole
        importance: int
        compression: CompressionLevel
        role, importance, compression = self._classify_parts(name_lower, parts_lower, suffix)

        result: FileClassification = FileClassification(
            path=a_path,
            role=role,
            importance=importance,
            compression=compression,
        )
        return result

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
            result = (FileRole.README, 0, FULL)
        elif any(part in _DOC_PARTS for part in a_parts) or a_suffix in _DOC_SUFFIXES:
            result = (FileRole.DOCUMENTATION, 1, FULL)
        elif a_name in _ENTRY_NAMES:
            result = (FileRole.ENTRY_POINT, 1, FULL)
        elif a_name in _CONFIG_NAMES or a_suffix in _CONFIG_SUFFIXES:
            result = (FileRole.CONFIGURATION, 2, FULL)
        elif any(part in _GENERATED_PARTS for part in a_parts):
            result = (FileRole.GENERATED, 9, STRUCTURE_ONLY)
        elif any(part in _TEST_PARTS for part in a_parts) or a_name.startswith("test_"):
            result = (FileRole.TEST, 7, SIGNATURES)
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
            result = (FileRole.DOMAIN, 2, FULL)
        elif "service" in a_parts or "services" in a_parts:
            result = (FileRole.SERVICE, 3, FULL)
        elif "infrastructure" in a_parts or "infra" in a_parts:
            result = (FileRole.INFRASTRUCTURE, 4, FULL)
        elif any(part in _UTIL_PARTS for part in a_parts):
            result = (FileRole.UTILITY, 5, SIGNATURES)
        else:
            result = (FileRole.UNKNOWN, 6, FULL)
        return result

    def order_by_importance(self, a_documents: list[Document]) -> list[Document]:
        """Sort documents by importance then path.

        Args:
            a_documents: Documents to order.

        Returns:
            Documents ordered by increasing importance (README first).
        """
        scored: list[tuple[int, str, Document]] = []
        for doc in a_documents:
            classification: FileClassification = self.classify_file(doc.path)
            scored.append((classification.importance, doc.path, doc))
        scored.sort(key=lambda item: (item[0], item[1]))
        ordered: list[Document] = [item[2] for item in scored]
        return ordered

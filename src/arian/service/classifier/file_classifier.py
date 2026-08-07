"""File classifier for role detection and importance scoring."""

from __future__ import annotations

from pathlib import Path

from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import FileRole
from arian.infrastructure.config import ClassifierConfig


class FileClassifier:
    """Classifies files by role and importance for context planning.

    Analyzes file paths and names to determine their role in the
    repository architecture and assigns importance scores.

    Attributes:
        _config: Classification lookup tables.
    """

    def __init__(self, a_config: ClassifierConfig = ClassifierConfig()) -> None:
        """Initialize classifier.

        Args:
            a_config: Classification lookup tables (names, suffixes, parts).
        """
        self._config: ClassifierConfig = a_config

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
        role: FileRole = self._detect_role(a_name, a_parts, a_suffix)
        result: tuple[FileRole, int, CompressionLevel] = (
            role,
            self._config.role_importance[role],
            self._config.role_compression[role],
        )
        return result

    def _detect_role(
        self,
        a_name: str,
        a_parts: tuple[str, ...],
        a_suffix: str,
    ) -> FileRole:
        """Detect the architectural role of a path.

        Args:
            a_name: Lowercased file name.
            a_parts: Lowercased path parts.
            a_suffix: Lowercased file suffix.

        Returns:
            Detected file role.
        """
        result: FileRole
        if a_name in self._config.readme_names or a_name.startswith("readme"):
            result = FileRole.README
        elif a_name in self._config.basename_config:
            result = FileRole.CONFIGURATION
        elif any(part in self._config.doc_parts for part in a_parts) or a_suffix in self._config.doc_suffixes:
            result = FileRole.DOCUMENTATION
        elif a_name in self._config.entry_names:
            result = FileRole.ENTRY_POINT
        elif a_name in self._config.config_names or a_suffix in self._config.config_suffixes:
            result = FileRole.CONFIGURATION
        elif a_suffix in self._config.web_suffixes:
            result = FileRole.SERVICE
        elif any(part in self._config.generated_parts for part in a_parts):
            result = FileRole.GENERATED
        elif any(part in self._config.test_parts for part in a_parts) or a_name.startswith("test_"):
            result = FileRole.TEST
        else:
            result = self._classify_layer(a_parts)
        return result

    def _classify_layer(self, a_parts: tuple[str, ...]) -> FileRole:
        """Classify architectural layer from path parts.

        Args:
            a_parts: Lowercased path parts.

        Returns:
            Detected file role.
        """
        result: FileRole
        if "domain" in a_parts:
            result = FileRole.DOMAIN
        elif "service" in a_parts or "services" in a_parts:
            result = FileRole.SERVICE
        elif "infrastructure" in a_parts or "infra" in a_parts:
            result = FileRole.INFRASTRUCTURE
        elif any(part in self._config.util_parts for part in a_parts):
            result = FileRole.UTILITY
        else:
            result = FileRole.UNKNOWN
        return result

"""Tests for FileClassifier."""

from __future__ import annotations

from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import FileRole
from arian.services.classifier.file_classifier import FileClassifier


class TestFileClassifier:
    """Tests for FileClassifier."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.classifier = FileClassifier()

    def test_classify_readme(self) -> None:
        """Test classifying README files."""
        role, importance, compression = self.classifier.classify("README.md")
        assert role == FileRole.README
        assert importance == 0
        assert compression == CompressionLevel.FULL

    def test_classify_test_file(self) -> None:
        """Test classifying test files."""
        role, importance, compression = self.classifier.classify("tests/test_main.py")
        assert role == FileRole.TEST
        assert importance == 7
        assert compression == CompressionLevel.SIGNATURES

    def test_classify_domain_file(self) -> None:
        """Test classifying domain files."""
        role, importance, compression = self.classifier.classify("src/domain/models.py")
        assert role == FileRole.DOMAIN
        assert importance == 2
        assert compression == CompressionLevel.FULL

    def test_classify_service_file(self) -> None:
        """Test classifying service files."""
        role, importance, compression = self.classifier.classify("src/services/analyzer.py")
        assert role == FileRole.SERVICE
        assert importance == 3
        assert compression == CompressionLevel.FULL

    def test_classify_config_file(self) -> None:
        """Test classifying configuration files."""
        role, importance, compression = self.classifier.classify("pyproject.toml")
        assert role == FileRole.CONFIGURATION
        assert importance == 2
        assert compression == CompressionLevel.FULL

    def test_classify_entry_point(self) -> None:
        """Test classifying entry point files."""
        role, importance, compression = self.classifier.classify("src/main.py")
        assert role == FileRole.ENTRY_POINT
        assert importance == 1
        assert compression == CompressionLevel.FULL

    def test_classify_generated_file(self) -> None:
        """Test classifying generated files."""
        role, importance, compression = self.classifier.classify("src/migrations/001.py")
        assert role == FileRole.GENERATED
        assert importance == 9
        assert compression == CompressionLevel.STRUCTURE

    def test_get_role(self) -> None:
        """Test get_role helper."""
        role = self.classifier.get_role("README.md")
        assert role == FileRole.README

    def test_get_importance(self) -> None:
        """Test get_importance helper."""
        importance = self.classifier.get_importance("README.md")
        assert importance == 0

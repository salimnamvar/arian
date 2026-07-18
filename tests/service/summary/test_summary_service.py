"""Tests for SummaryService."""

from __future__ import annotations

from arian.domain.repository.models import Symbol
from arian.domain.shared.enums import FileRole
from arian.domain.shared.enums import SymbolKind
from arian.service.summary.summary_service import SummaryService


class TestSummaryService:
    """Tests for SummaryService."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.service = SummaryService()

    def test_empty_symbols(self) -> None:
        """Test summary with no symbols."""
        result = self.service.generate([], FileRole.DOMAIN)
        assert result == ""

    def test_with_imports(self) -> None:
        """Test summary with imports."""
        imports = ("from typing import List", "import os")
        result = self.service.generate([], FileRole.DOMAIN, a_imports=imports)
        assert "## Imports" in result
        assert "`from typing import List`" in result
        assert "`import os`" in result

    def test_with_classes(self) -> None:
        """Test summary with class symbols."""
        symbols = [
            Symbol(
                name="AuthService",
                kind=SymbolKind.CLASS,
                file_path="src/auth.py",
                signature="class AuthService",
                docstring="Handles authentication",
            ),
        ]
        result = self.service.generate(symbols, FileRole.SERVICE)
        assert "## Classes" in result
        assert "**AuthService**" in result
        assert "Handles authentication" in result

    def test_with_functions(self) -> None:
        """Test summary with function symbols."""
        symbols = [
            Symbol(
                name="validate_token",
                kind=SymbolKind.FUNCTION,
                file_path="src/auth.py",
                signature="def validate_token",
                docstring="Validates JWT token",
            ),
        ]
        result = self.service.generate(symbols, FileRole.SERVICE)
        assert "## Functions" in result
        assert "`validate_token`" in result
        assert "Validates JWT token" in result

    def test_with_methods(self) -> None:
        """Test summary with method symbols."""
        symbols = [
            Symbol(
                name="login",
                kind=SymbolKind.METHOD,
                file_path="src/auth.py",
                signature="def login(self)",
            ),
        ]
        result = self.service.generate(symbols, FileRole.SERVICE)
        assert "## Methods" in result
        assert "`login`" in result

    def test_deterministic_output(self) -> None:
        """Test that same inputs always produce same output."""
        symbols = [
            Symbol(
                name="Parser",
                kind=SymbolKind.CLASS,
                file_path="src/parser.py",
                signature="class Parser",
            ),
        ]
        result1 = self.service.generate(symbols, FileRole.DOMAIN)
        result2 = self.service.generate(symbols, FileRole.DOMAIN)
        assert result1 == result2

    def test_no_llm_calls(self) -> None:
        """Test that summary generation is purely deterministic."""
        symbols = [
            Symbol(
                name="Service",
                kind=SymbolKind.CLASS,
                file_path="src/service.py",
                signature="class Service",
                docstring="Main service",
            ),
            Symbol(
                name="process",
                kind=SymbolKind.FUNCTION,
                file_path="src/service.py",
                signature="def process",
            ),
        ]
        result = self.service.generate(symbols, FileRole.SERVICE)
        assert "## Classes" in result
        assert "## Functions" in result
        assert "**Service**" in result
        assert "`process`" in result

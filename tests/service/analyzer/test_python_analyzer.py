"""Tests for PythonAnalyzer."""

from __future__ import annotations

from pathlib import Path

from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import SymbolKind
from arian.service.analyzer.python_analyzer import PythonAnalyzer


class TestPythonAnalyzer:
    """Tests for PythonAnalyzer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.analyzer = PythonAnalyzer()

    def test_extract_symbols_from_class(self) -> None:
        """Test extracting class symbols."""
        content = '''
class MyClass:
    """A test class."""
    def method(self) -> None:
        pass
'''
        symbols = self.analyzer.extract_symbols(content, Path("test.py"))
        assert len(symbols) >= 1
        class_symbols = [s for s in symbols if s.kind == SymbolKind.CLASS]
        assert len(class_symbols) == 1
        assert class_symbols[0].name == "MyClass"
        assert class_symbols[0].docstring == "A test class."

    def test_extract_symbols_from_function(self) -> None:
        """Test extracting function symbols."""
        content = '''
def my_function(a_arg: str) -> int:
    """A test function."""
    return len(a_arg)
'''
        symbols = self.analyzer.extract_symbols(content, Path("test.py"))
        func_symbols = [s for s in symbols if s.kind == SymbolKind.FUNCTION]
        assert len(func_symbols) == 1
        assert func_symbols[0].name == "my_function"
        assert "a_arg" in func_symbols[0].signature

    def test_extract_symbols_from_method(self) -> None:
        """Test extracting method symbols."""
        content = """
class MyClass:
    def my_method(self, a_x: int) -> str:
        return str(a_x)
"""
        symbols = self.analyzer.extract_symbols(content, Path("test.py"))
        method_symbols = [s for s in symbols if s.kind == SymbolKind.METHOD]
        assert len(method_symbols) == 1
        assert method_symbols[0].name == "my_method"

    def test_extract_symbols_syntax_error(self) -> None:
        """Test extracting symbols from invalid Python."""
        content = "def broken(:"
        symbols = self.analyzer.extract_symbols(content, Path("test.py"))
        assert symbols == []

    def test_extract_imports(self) -> None:
        """Test extracting imports."""
        content = """
import os
from pathlib import Path
from typing import Any
import sys
"""
        imports = self.analyzer.extract_imports(content)
        assert "os" in imports
        assert "pathlib" in imports
        assert "typing" in imports
        assert "sys" in imports

    def test_extract_public_api(self) -> None:
        """Test extracting public API."""
        content = '''
class PublicClass:
    """Public class."""
    pass

def public_function() -> None:
    """Public function."""
    pass

def _private_function() -> None:
    pass
'''
        api = self.analyzer.extract_public_api(content)
        assert "PublicClass" in api
        assert "public_function" in api
        assert "_private_function" not in api

    def test_compress_full(self) -> None:
        """Test FULL compression returns original."""
        content = "def func(): pass"
        result = self.analyzer.compress(content, CompressionLevel.FULL)
        assert result == content

    def test_compress_structure(self) -> None:
        """Test STRUCTURE compression keeps only structure."""
        content = """
import os

class MyClass:
    def method(self) -> None:
        pass
"""
        result = self.analyzer.compress(content, CompressionLevel.STRUCTURE)
        assert "import os" in result
        assert "class MyClass" in result or "def method" in result

    def test_compress_summary(self) -> None:
        """Test SUMMARY compression generates summary."""
        content = '''
class MyClass:
    """A test class."""
    pass

def my_function() -> None:
    pass
'''
        result = self.analyzer.compress(content, CompressionLevel.SUMMARY)
        assert "Python module" in result
        assert "MyClass" in result

    def test_strip_comments(self) -> None:
        """Test stripping comments."""
        content = """# This is a comment
x = 1  # inline comment
y = 2
"""
        result = self.analyzer.strip_comments(content)
        assert "# This is a comment" not in result
        assert "x = 1" in result
        assert "y = 2" in result

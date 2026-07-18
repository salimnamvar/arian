"""Unit tests for context analyzer and content compressor."""

from __future__ import annotations

from arian.domain.enums import FileRole
from arian.domain.models import FULL
from arian.domain.models import SIGNATURES
from arian.domain.models import STRUCTURE_ONLY
from arian.domain.models import Document
from arian.services.analyzer import ContextAnalyzer
from arian.services.compressor import ContentCompressor


def test_classify_readme() -> None:
    """Test README classification."""
    analyzer = ContextAnalyzer()
    result = analyzer.classify_file("README.md")
    assert result.role == FileRole.README
    assert result.importance == 0
    assert result.compression == FULL


def test_classify_domain() -> None:
    """Test domain file classification."""
    analyzer = ContextAnalyzer()
    result = analyzer.classify_file("src/arian/domain/models.py")
    assert result.role == FileRole.DOMAIN
    assert result.importance == 2


def test_classify_test() -> None:
    """Test test file classification."""
    analyzer = ContextAnalyzer()
    result = analyzer.classify_file("tests/services/test_foo.py")
    assert result.role == FileRole.TEST
    assert result.compression == SIGNATURES


def test_classify_generated() -> None:
    """Test generated file classification."""
    analyzer = ContextAnalyzer()
    result = analyzer.classify_file("src/migrations/001_init.py")
    assert result.role == FileRole.GENERATED
    assert result.compression == STRUCTURE_ONLY


def test_order_by_importance() -> None:
    """Test documents ordered by importance."""
    analyzer = ContextAnalyzer()
    docs = [
        Document(path="tests/test_a.py", content="t", tokens=1),
        Document(path="README.md", content="r", tokens=1),
        Document(path="src/domain/x.py", content="d", tokens=1),
    ]
    ordered = analyzer.order_by_importance(docs)
    assert ordered[0].path == "README.md"
    assert ordered[-1].path == "tests/test_a.py"


def test_compress_strip_comments_python() -> None:
    """Test stripping Python comments."""
    compressor = ContentCompressor()
    content = "x = 1  # inline\n# full line\ny = 2\n"
    result = compressor.compress(content, "python", SIGNATURES)
    assert "# full line" not in result
    assert "y = 2" in result or "..." in result


def test_compress_full_keeps_everything() -> None:
    """Test full compression keeps content."""
    compressor = ContentCompressor()
    content = 'def foo():\n    """Doc."""\n    return 1\n'
    result = compressor.compress(content, "python", FULL)
    assert "return 1" in result
    assert "Doc" in result


def test_compress_signatures_strips_body() -> None:
    """Test signature compression strips implementation."""
    compressor = ContentCompressor()
    content = 'def foo(a_x: int) -> int:\n    """Add one."""\n    return a_x + 1\n'
    result = compressor.compress(content, "python", SIGNATURES)
    assert "def foo" in result
    assert "return a_x + 1" not in result
    assert "..." in result

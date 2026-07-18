"""Unit tests for domain models."""

from __future__ import annotations

from arian.domain.enums import OutputMode
from arian.domain.models import ContextConfig
from arian.domain.models import ContextResult
from arian.domain.models import Document


def test_document_defaults() -> None:
    """Test Document default values."""
    doc = Document(path="test.py")
    assert doc.content == ""
    assert doc.tokens == 0
    assert doc.language == ""


def test_document_immutability() -> None:
    """Test Document is frozen (immutable)."""
    doc = Document(path="test.py")
    try:
        doc.path = "other.py"  # type: ignore[misc]
    except AttributeError:
        pass  # Expected - frozen dataclass cannot be modified
    else:
        msg = "Should not be able to modify frozen dataclass"
        raise AssertionError(msg)


def test_document_ordering() -> None:
    """Test Document ordering by path."""
    doc1 = Document(path="a.py")
    doc2 = Document(path="b.py")
    assert doc1 < doc2


def test_context_config_defaults() -> None:
    """Test ContextConfig default max_tokens."""
    config = ContextConfig(
        inputs=("test.py",),
        extensions=frozenset([".py"]),
        exclude=frozenset([".git"]),
        mode=OutputMode.SEPARATE,
        output_path="output.md",
    )
    assert config.max_tokens is None


def test_context_result_defaults() -> None:
    """Test ContextResult default chunks value."""
    result = ContextResult(
        output_paths=("output.md",),
        total_files=5,
        total_tokens=100,
    )
    assert result.chunks == 1


def test_context_result_custom_chunks() -> None:
    """Test ContextResult custom chunks value."""
    result = ContextResult(
        output_paths=("output.md",),
        total_files=5,
        total_tokens=100,
        chunks=3,
    )
    assert result.chunks == 3

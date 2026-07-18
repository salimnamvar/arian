"""Unit tests for domain models."""

from __future__ import annotations

from arian.domain.enums import OutputMode
from arian.domain.models import ContextConfig
from arian.domain.models import ContextResult
from arian.domain.models import Document
from arian.domain.models import InputSpec


def test_document_defaults() -> None:
    """Test Document default values."""
    doc = Document(path="test.py")
    assert doc.content == ""
    assert doc.tokens == 0
    assert doc.language == ""
    assert doc.tag == ""


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
    """Test Document sorting by path."""
    doc1 = Document(path="b.py")
    doc2 = Document(path="a.py")
    result: list[Document] = sorted([doc1, doc2], key=lambda d: d.path)
    assert result[0].path == "a.py"
    assert result[1].path == "b.py"


def test_document_with_tag() -> None:
    """Test Document with tag field."""
    doc = Document(path="a.py", tag="core")
    assert doc.tag == "core"


def test_input_spec_defaults() -> None:
    """Test InputSpec default tag is empty."""
    spec = InputSpec(path="src/")
    assert spec.path == "src/"
    assert spec.tag == ""


def test_input_spec_with_tag() -> None:
    """Test InputSpec with tag."""
    spec = InputSpec(path="src/", tag="core")
    assert spec.path == "src/"
    assert spec.tag == "core"


def test_context_config_defaults() -> None:
    """Test ContextConfig default max_tokens."""
    config = ContextConfig(
        inputs=(InputSpec(path="test.py"),),
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

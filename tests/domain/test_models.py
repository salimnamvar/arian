"""Unit tests for domain models."""

from __future__ import annotations

from arian.domain.enums import OutputMode
from arian.domain.models import ContextConfig
from arian.domain.models import ContextResult
from arian.domain.models import Document


def test_base_entity_to_dict() -> None:
    """Test BaseEntity to_dict serialization."""
    doc = Document(path="test.py", content="print('hello')", tokens=10, language="python")
    result: dict[str, object] = doc.to_dict()
    assert result == {"path": "test.py", "content": "print('hello')", "tokens": 10, "language": "python"}


def test_base_entity_to_tuple() -> None:
    """Test BaseEntity to_tuple serialization."""
    doc = Document(path="test.py", content="print('hello')", tokens=10, language="python")
    result: tuple[object, ...] = doc.to_tuple()
    assert result == ("test.py", "print('hello')", 10, "python")


def test_base_entity_from_dict() -> None:
    """Test BaseEntity from_dict deserialization."""
    data: dict[str, object] = {
        "path": "test.py",
        "content": "print('hello')",
        "tokens": 10,
        "language": "python",
    }
    result: Document = Document.from_dict(data)
    assert result.path == "test.py"
    assert result.content == "print('hello')"
    assert result.tokens == 10
    assert result.language == "python"


def test_base_entity_from_tuple() -> None:
    """Test BaseEntity from_tuple deserialization."""
    data: tuple[object, ...] = ("test.py", "print('hello')", 10, "python")
    result: Document = Document.from_tuple(data)
    assert result.path == "test.py"
    assert result.content == "print('hello')"
    assert result.tokens == 10
    assert result.language == "python"


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
        inputs=["test.py"],
        extensions=frozenset([".py"]),
        exclude=frozenset([".git"]),
        mode=OutputMode.SEPARATE,
        output_path="output.md",
    )
    assert config.max_tokens is None


def test_context_result_defaults() -> None:
    """Test ContextResult default chunks value."""
    result = ContextResult(
        output_paths=["output.md"],
        total_files=5,
        total_tokens=100,
    )
    assert result.chunks == 1


def test_context_result_custom_chunks() -> None:
    """Test ContextResult custom chunks value."""
    result = ContextResult(
        output_paths=["output.md"],
        total_files=5,
        total_tokens=100,
        chunks=3,
    )
    assert result.chunks == 3


def test_context_config_to_dict() -> None:
    """Test ContextConfig to_dict serialization."""
    config = ContextConfig(
        inputs=["src/", "tests/"],
        extensions=frozenset([".py"]),
        exclude=frozenset([".git"]),
        mode=OutputMode.AGGREGATE,
        output_path="output/",
        max_tokens=5000,
    )
    result: dict[str, object] = config.to_dict()
    assert result["inputs"] == ["src/", "tests/"]
    assert result["mode"] == OutputMode.AGGREGATE
    assert result["max_tokens"] == 5000


def test_context_result_to_dict() -> None:
    """Test ContextResult to_dict serialization."""
    result = ContextResult(
        output_paths=["output.md"],
        total_files=5,
        total_tokens=100,
    )
    data: dict[str, object] = result.to_dict()
    assert data["output_paths"] == ["output.md"]
    assert data["total_files"] == 5
    assert data["total_tokens"] == 100
    assert data["chunks"] == 1

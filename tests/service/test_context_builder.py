"""Unit tests for service layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from arian.domain.enums import OutputMode
from arian.domain.exceptions import NoDocumentsError
from arian.domain.models import ContextConfig
from arian.domain.models import Document
from arian.service.context_builder import ContextBuilderService


class MockCollector:
    """Mock collector for testing."""

    def __init__(self, a_documents: list[Document]) -> None:
        """Initialize with documents to return."""
        self._documents = a_documents

    def collect(self, a_inputs: list[str]) -> list[Document]:
        """Return mock documents."""
        return self._documents


class MockWriter:
    """Mock writer for testing."""

    def __init__(self) -> None:
        """Initialize mock writer."""
        self.written: list[tuple[str, Path]] = []

    def write(self, a_content: str, a_path: Path) -> Path:
        """Record write operation."""
        self.written.append((a_content, a_path))
        return a_path


class MockRenderer:
    """Mock renderer for testing."""

    def __init__(self) -> None:
        """Initialize mock renderer."""
        self.rendered: list[list[Document]] = []

    def render(self, a_documents: list[Document]) -> str:
        """Return mock rendered content."""
        self.rendered.append(a_documents)
        return f"Rendered {len(a_documents)} documents"


def _make_service(
    a_mode: OutputMode,
    a_docs: list[Document],
    a_output: str = "output.md",
    a_max_tokens: int | None = None,
) -> tuple[ContextBuilderService, MockWriter, MockRenderer]:
    """Create a service with mock dependencies."""
    config = ContextConfig(
        inputs=("src/",),
        extensions=frozenset([".py"]),
        exclude=frozenset([".git"]),
        mode=a_mode,
        output_path=a_output,
        max_tokens=a_max_tokens,
    )
    writer = MockWriter()
    renderer = MockRenderer()
    service = ContextBuilderService(
        a_config=config,
        a_collector=MockCollector(a_docs),
        a_writer=writer,
        a_renderer=renderer,
    )
    return service, writer, renderer


def test_context_builder_service_aggregate_mode() -> None:
    """Test ContextBuilderService with aggregate mode."""
    docs = [
        Document(path="a.py", content="code", tokens=10, language="python"),
    ]
    service, _writer, _renderer = _make_service(OutputMode.AGGREGATE, docs)

    result = service.build()
    assert result.total_files == 1
    assert result.total_tokens == 10
    assert result.chunks == 1


def test_context_builder_service_separate_mode() -> None:
    """Test ContextBuilderService with separate mode."""
    docs = [
        Document(path="a.py", content="code", tokens=10, language="python"),
    ]
    service, _writer, _renderer = _make_service(OutputMode.SEPARATE, docs, a_output="output/")

    result = service.build()
    assert result.total_files == 1


def test_context_builder_service_with_max_tokens() -> None:
    """Test ContextBuilderService with token splitting."""
    docs = [
        Document(path="a.py", content="a", tokens=20),
        Document(path="b.py", content="b", tokens=20),
        Document(path="c.py", content="c", tokens=20),
    ]
    service, writer, _renderer = _make_service(
        OutputMode.AGGREGATE,
        docs,
        a_output="output/",
        a_max_tokens=50,
    )

    result = service.build()
    assert result.total_files == 3
    assert result.chunks == 2
    assert len(writer.written) == 2


def test_context_builder_service_no_documents() -> None:
    """Test ContextBuilderService raises NoDocumentsError when no docs collected."""
    service, _writer, _renderer = _make_service(OutputMode.AGGREGATE, [])

    with pytest.raises(NoDocumentsError) as exc_info:
        service.build()
    assert "No documents collected" in exc_info.value.message


def test_split_documents_no_limit() -> None:
    """Test splitting with no max_tokens limit."""
    docs = [
        Document(path="a.py", content="a", tokens=10),
        Document(path="b.py", content="b", tokens=20),
    ]
    service, _w, _r = _make_service(OutputMode.AGGREGATE, docs)
    result: list[list[Document]] = service._split_documents(docs, None)
    assert len(result) == 1
    assert len(result[0]) == 2


def test_split_documents_single_chunk() -> None:
    """Test splitting where all docs fit in one chunk."""
    docs = [
        Document(path="a.py", content="a", tokens=10),
        Document(path="b.py", content="b", tokens=20),
    ]
    service, _w, _r = _make_service(OutputMode.AGGREGATE, docs)
    result: list[list[Document]] = service._split_documents(docs, 100)
    assert len(result) == 1
    assert len(result[0]) == 2


def test_split_documents_multiple_chunks() -> None:
    """Test splitting into multiple chunks."""
    docs = [
        Document(path="a.py", content="a", tokens=50),
        Document(path="b.py", content="b", tokens=50),
        Document(path="c.py", content="c", tokens=50),
    ]
    service, _w, _r = _make_service(OutputMode.AGGREGATE, docs)
    result: list[list[Document]] = service._split_documents(docs, 100)
    assert len(result) == 2
    assert len(result[0]) == 2
    assert len(result[1]) == 1


def test_split_documents_respects_exact_limit() -> None:
    """Test splitting respects exact token limit."""
    docs = [
        Document(path="a.py", content="a", tokens=100),
        Document(path="b.py", content="b", tokens=50),
    ]
    service, _w, _r = _make_service(OutputMode.AGGREGATE, docs)
    result: list[list[Document]] = service._split_documents(docs, 100)
    assert len(result) == 2
    assert len(result[0]) == 1
    assert len(result[1]) == 1


def test_render_aggregate_single() -> None:
    """Test rendering single aggregate output."""
    docs = [Document(path="a.py", content="code", tokens=10, language="python")]
    service, writer, _r = _make_service(OutputMode.AGGREGATE, docs, a_output="output.md")

    result = service._render_aggregate_single(docs, Path("output.md"), 10)

    assert result.output_paths == ("output.md",)
    assert result.total_files == 1
    assert result.total_tokens == 10
    assert result.chunks == 1
    assert len(writer.written) == 1


def test_render_aggregate_split() -> None:
    """Test rendering split aggregate output."""
    chunks: list[list[Document]] = [
        [Document(path="a.py", content="a", tokens=50, language="python")],
        [Document(path="b.py", content="b", tokens=50, language="python")],
    ]
    service, writer, _r = _make_service(OutputMode.AGGREGATE, [], a_output="output/", a_max_tokens=100)

    result = service._render_aggregate_split(chunks, Path("output/"), 100)

    assert len(result.output_paths) == 2
    assert "merged.1.md" in result.output_paths[0]
    assert "merged.2.md" in result.output_paths[1]
    assert result.chunks == 2
    assert len(writer.written) == 2


def test_render_separate() -> None:
    """Test rendering separate output."""
    chunks: list[list[Document]] = [
        [Document(path="a.py", content="a", tokens=10, language="python")],
        [Document(path="b.md", content="b", tokens=10, language="markdown")],
    ]
    service, writer, _r = _make_service(OutputMode.SEPARATE, [], a_output="output/")

    result = service._render_separate(chunks, Path("output/"), 20)

    assert len(result.output_paths) == 2
    assert "a.md" in result.output_paths[0]
    assert "b.md" in result.output_paths[1]
    assert len(writer.written) == 2


def test_render_separate_skips_empty_chunks() -> None:
    """Test that separate mode skips empty chunks."""
    chunks: list[list[Document]] = [
        [Document(path="a.py", content="a", tokens=10, language="python")],
        [],
        [Document(path="b.md", content="b", tokens=10, language="markdown")],
    ]
    service, _w, _r = _make_service(OutputMode.SEPARATE, [], a_output="output/")

    result = service._render_separate(chunks, Path("output/"), 20)

    assert len(result.output_paths) == 2

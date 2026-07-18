"""Unit tests for pipeline layer."""

from __future__ import annotations

from pathlib import Path

from arian.domain.enums import OutputMode
from arian.domain.models import ContextResult
from arian.domain.models import Document
from arian.pipeline.renderer_pipeline import render_and_write
from arian.pipeline.renderer_pipeline import _render_aggregate_single
from arian.pipeline.renderer_pipeline import _render_aggregate_split
from arian.pipeline.renderer_pipeline import _render_separate
from arian.pipeline.splitter_pipeline import split_documents


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
        """Record render operation and return content."""
        self.rendered.append(a_documents)
        return f"Rendered {len(a_documents)} documents"


def test_split_documents_no_limit() -> None:
    """Test splitting with no max_tokens limit."""
    docs = [
        Document(path="a.py", content="a", tokens=10),
        Document(path="b.py", content="b", tokens=20),
    ]
    result: list[list[Document]] = split_documents(docs, None)
    assert len(result) == 1
    assert len(result[0]) == 2


def test_split_documents_single_chunk() -> None:
    """Test splitting where all docs fit in one chunk."""
    docs = [
        Document(path="a.py", content="a", tokens=10),
        Document(path="b.py", content="b", tokens=20),
    ]
    result: list[list[Document]] = split_documents(docs, 100)
    assert len(result) == 1
    assert len(result[0]) == 2


def test_split_documents_multiple_chunks() -> None:
    """Test splitting into multiple chunks."""
    docs = [
        Document(path="a.py", content="a", tokens=50),
        Document(path="b.py", content="b", tokens=50),
        Document(path="c.py", content="c", tokens=50),
    ]
    result: list[list[Document]] = split_documents(docs, 100)
    assert len(result) == 2
    # First chunk has a (50) + b (50) = 100, c (50) > 100 so starts new chunk
    assert len(result[0]) == 2
    assert len(result[1]) == 1


def test_split_documents_respects_exact_limit() -> None:
    """Test splitting respects exact token limit."""
    docs = [
        Document(path="a.py", content="a", tokens=100),
        Document(path="b.py", content="b", tokens=50),
    ]
    result: list[list[Document]] = split_documents(docs, 100)
    assert len(result) == 2
    assert len(result[0]) == 1
    assert len(result[1]) == 1


def test_render_aggregate_single() -> None:
    """Test rendering single aggregate output."""
    writer = MockWriter()
    renderer = MockRenderer()
    docs = [Document(path="a.py", content="code", tokens=10, language="python")]

    result: ContextResult = _render_aggregate_single(
        a_renderer=renderer,
        a_writer=writer,
        a_documents=docs,
        a_output_path=Path("output.md"),
        a_total_tokens=10,
    )

    assert result.output_paths == ("output.md",)
    assert result.total_files == 1
    assert result.total_tokens == 10
    assert result.chunks == 1


def test_render_aggregate_split() -> None:
    """Test rendering split aggregate output."""
    writer = MockWriter()
    renderer = MockRenderer()
    chunks: list[list[Document]] = [
        [Document(path="a.py", content="a", tokens=50, language="python")],
        [Document(path="b.py", content="b", tokens=50, language="python")],
    ]

    result: ContextResult = _render_aggregate_split(
        a_renderer=renderer,
        a_writer=writer,
        a_chunks=chunks,
        a_output_path=Path("output/"),
        a_total_tokens=100,
    )

    assert len(result.output_paths) == 2
    assert "merged.1.md" in result.output_paths[0]
    assert "merged.2.md" in result.output_paths[1]
    assert result.chunks == 2


def test_render_separate() -> None:
    """Test rendering separate output."""
    writer = MockWriter()
    renderer = MockRenderer()
    chunks: list[list[Document]] = [
        [Document(path="a.py", content="a", tokens=10, language="python")],
        [Document(path="b.md", content="b", tokens=10, language="markdown")],
    ]

    result: ContextResult = _render_separate(
        a_renderer=renderer,
        a_writer=writer,
        a_chunks=chunks,
        a_output_path=Path("output/"),
        a_total_tokens=20,
    )

    assert len(result.output_paths) == 2
    assert "a.md" in result.output_paths[0]
    assert "b.md" in result.output_paths[1]


def test_render_separate_skips_empty_chunks() -> None:
    """Test that separate mode skips empty chunks."""
    writer = MockWriter()
    renderer = MockRenderer()
    chunks: list[list[Document]] = [
        [Document(path="a.py", content="a", tokens=10, language="python")],
        [],  # Empty chunk should be skipped
        [Document(path="b.md", content="b", tokens=10, language="markdown")],
    ]

    result: ContextResult = _render_separate(
        a_renderer=renderer,
        a_writer=writer,
        a_chunks=chunks,
        a_output_path=Path("output/"),
        a_total_tokens=20,
    )

    assert len(result.output_paths) == 2


def test_render_and_write_aggregate_single() -> None:
    """Test render_and_write in aggregate single mode."""
    writer = MockWriter()
    renderer = MockRenderer()
    docs = [Document(path="a.py", content="code", tokens=10, language="python")]

    result: ContextResult = render_and_write(
        a_documents=docs,
        a_chunks=[docs],
        a_output_path=Path("output.md"),
        a_mode=OutputMode.AGGREGATE,
        a_max_tokens=None,
        a_renderer=renderer,
        a_writer=writer,
    )

    assert len(result.output_paths) == 1
    assert result.chunks == 1


def test_render_and_write_aggregate_split() -> None:
    """Test render_and_write in aggregate split mode."""
    writer = MockWriter()
    renderer = MockRenderer()
    chunks: list[list[Document]] = [
        [Document(path="a.py", content="a", tokens=50, language="python")],
        [Document(path="b.py", content="b", tokens=50, language="python")],
    ]

    result: ContextResult = render_and_write(
        a_documents=[
            Document(path="a.py", content="a", tokens=50, language="python"),
            Document(path="b.py", content="b", tokens=50, language="python"),
        ],
        a_chunks=chunks,
        a_output_path=Path("output/"),
        a_mode=OutputMode.AGGREGATE,
        a_max_tokens=100,
        a_renderer=renderer,
        a_writer=writer,
    )

    assert len(result.output_paths) == 2
    assert result.chunks == 2


def test_render_and_write_separate_mode() -> None:
    """Test render_and_write in separate mode."""
    writer = MockWriter()
    renderer = MockRenderer()
    # In separate mode, chunks are one per input
    chunks: list[list[Document]] = [
        [Document(path="a.py", content="a", tokens=10, language="python")],
        [Document(path="b.md", content="b", tokens=10, language="markdown")],
    ]

    result: ContextResult = render_and_write(
        a_documents=[
            Document(path="a.py", content="a", tokens=10, language="python"),
            Document(path="b.md", content="b", tokens=10, language="markdown"),
        ],
        a_chunks=chunks,
        a_output_path=Path("output/"),
        a_mode=OutputMode.SEPARATE,
        a_max_tokens=None,
        a_renderer=renderer,
        a_writer=writer,
    )

    assert len(result.output_paths) == 2

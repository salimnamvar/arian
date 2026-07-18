"""Unit tests for service layer."""

from __future__ import annotations

from pathlib import Path

from arian.domain.enums import OutputMode
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

    def write_numbered(self, a_chunks: list[str], a_base_path: Path) -> list[Path]:
        """Record numbered write operation."""
        result: list[Path] = []
        for i, chunk in enumerate(a_chunks, start=1):
            out_path: Path = a_base_path.parent / f"{a_base_path.stem}.{i}.md"
            self.written.append((chunk, out_path))
            result.append(out_path)
        return result


class MockRenderer:
    """Mock renderer for testing."""

    def render(self, a_documents: list[Document]) -> str:
        """Return mock rendered content."""
        return f"Rendered {len(a_documents)} documents"


def test_context_builder_service_aggregate_mode() -> None:
    """Test ContextBuilderService with aggregate mode."""
    config = ContextConfig(
        inputs=["src/"],
        extensions=frozenset([".py"]),
        exclude=frozenset([".git"]),
        mode=OutputMode.AGGREGATE,
        output_path="output.md",
    )
    docs = [
        Document(path="a.py", content="code", tokens=10, language="python"),
    ]
    collector = MockCollector(docs)
    writer = MockWriter()
    renderer = MockRenderer()

    service = ContextBuilderService(
        a_config=config,
        a_collector=collector,
        a_writer=writer,
        a_renderer=renderer,
        a_tokenizer=len,
    )

    result = service.build()
    assert result.total_files == 1
    assert result.total_tokens == 10
    assert result.chunks == 1


def test_context_builder_service_separate_mode() -> None:
    """Test ContextBuilderService with separate mode."""
    config = ContextConfig(
        inputs=["src/"],
        extensions=frozenset([".py"]),
        exclude=frozenset([".git"]),
        mode=OutputMode.SEPARATE,
        output_path="output/",
    )
    docs = [
        Document(path="a.py", content="code", tokens=10, language="python"),
    ]
    collector = MockCollector(docs)
    writer = MockWriter()
    renderer = MockRenderer()

    service = ContextBuilderService(
        a_config=config,
        a_collector=collector,
        a_writer=writer,
        a_renderer=renderer,
        a_tokenizer=len,
    )

    result = service.build()
    assert result.total_files == 1


def test_context_builder_service_with_max_tokens() -> None:
    """Test ContextBuilderService with token splitting."""
    config = ContextConfig(
        inputs=["src/"],
        extensions=frozenset([".py"]),
        exclude=frozenset([".git"]),
        mode=OutputMode.AGGREGATE,
        output_path="output/",
        max_tokens=50,
    )
    # Create docs that will be split
    docs = [
        Document(path="a.py", content="a", tokens=20),
        Document(path="b.py", content="b", tokens=20),
        Document(path="c.py", content="c", tokens=20),
    ]
    collector = MockCollector(docs)
    writer = MockWriter()
    renderer = MockRenderer()

    service = ContextBuilderService(
        a_config=config,
        a_collector=collector,
        a_writer=writer,
        a_renderer=renderer,
        a_tokenizer=len,
    )

    result = service.build()
    # With max_tokens=50, should split into chunks
    assert result.total_files == 3

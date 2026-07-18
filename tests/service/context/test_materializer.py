"""Tests for ContextMaterializer."""

from __future__ import annotations

from typing import Protocol

from arian.domain.context.models import ContextChunk
from arian.domain.context.models import ContextPlan
from arian.domain.context.models import ContextTask
from arian.domain.context.models import PlannedFile
from arian.domain.repository.models import FileContent
from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import FileRole
from arian.service.context.materializer import ContextMaterializer


class MockAnalyzer(Protocol):
    """Mock analyzer for testing."""

    def compress(self, a_content: str, a_level: CompressionLevel) -> str: ...


class MockLanguageAnalyzer:
    """Mock language analyzer for testing."""

    def compress(self, a_content: str, a_level: CompressionLevel) -> str:
        """Mock compression — returns content with level prefix."""
        if a_level == CompressionLevel.SIGNATURES:
            return f"[SIG] {a_content[:50]}..."
        if a_level == CompressionLevel.STRUCTURE:
            return f"[STRUCT] {a_content[:20]}..."
        if a_level == CompressionLevel.SUMMARY:
            return f"[SUM] {a_content[:10]}..."
        return a_content


class TestContextMaterializer:
    """Tests for ContextMaterializer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.analyzer = MockLanguageAnalyzer()
        self.materializer = ContextMaterializer(self.analyzer)

    def test_materialize_full_file(self) -> None:
        """Test materializing a full file."""
        plan = ContextPlan(
            chunks=(
                ContextChunk(
                    files=(
                        PlannedFile(
                            path="src/main.py",
                            role=FileRole.SERVICE,
                            importance=3,
                            compression=CompressionLevel.FULL,
                            representation="full",
                            tokens=100,
                        ),
                    ),
                    token_count=100,
                    chunk_index=0,
                ),
            ),
            total_tokens=100,
            total_files=1,
            task=ContextTask.GENERAL,
        )
        content = {"src/main.py": FileContent(path="src/main.py", content="def main(): pass", hash="abc")}
        chunks = self.materializer.materialize(plan, content)
        assert len(chunks) == 1
        assert len(chunks[0].entries) == 1
        assert chunks[0].entries[0].content == "def main(): pass"

    def test_materialize_compressed_file(self) -> None:
        """Test materializing a compressed file."""
        plan = ContextPlan(
            chunks=(
                ContextChunk(
                    files=(
                        PlannedFile(
                            path="src/service.py",
                            role=FileRole.SERVICE,
                            importance=3,
                            compression=CompressionLevel.SIGNATURES,
                            representation="signatures",
                            tokens=50,
                        ),
                    ),
                    token_count=50,
                    chunk_index=0,
                ),
            ),
            total_tokens=50,
            total_files=1,
            task=ContextTask.GENERAL,
        )
        content = {"src/service.py": FileContent(path="src/service.py", content="class Service: pass", hash="abc")}
        chunks = self.materializer.materialize(plan, content)
        assert len(chunks) == 1
        assert "[SIG]" in chunks[0].entries[0].content

    def test_materialize_fragment(self) -> None:
        """Test materializing a file fragment with line extraction."""
        plan = ContextPlan(
            chunks=(
                ContextChunk(
                    files=(
                        PlannedFile(
                            path="src/parser.py",
                            role=FileRole.DOMAIN,
                            importance=2,
                            compression=CompressionLevel.FULL,
                            representation="fragment 1/3",
                            tokens=200,
                            is_fragment=True,
                            fragment_index=0,
                            fragment_total=3,
                            line_start=10,
                            line_end=50,
                        ),
                    ),
                    token_count=200,
                    chunk_index=0,
                ),
            ),
            total_tokens=200,
            total_files=1,
            task=ContextTask.GENERAL,
        )
        lines = [f"line {i}" for i in range(100)]
        content = {"src/parser.py": FileContent(path="src/parser.py", content="\n".join(lines), hash="abc")}
        chunks = self.materializer.materialize(plan, content)
        assert len(chunks) == 1
        entry = chunks[0].entries[0]
        assert entry.is_fragment is True
        assert entry.fragment_index == 0
        assert entry.fragment_total == 3
        assert "line 10" in entry.content
        assert "line 49" in entry.content
        assert "line 50" not in entry.content

    def test_provenance_created(self) -> None:
        """Test that provenance is created for materialized entries."""
        plan = ContextPlan(
            chunks=(
                ContextChunk(
                    files=(
                        PlannedFile(
                            path="src/auth.py",
                            role=FileRole.SERVICE,
                            importance=1,
                            compression=CompressionLevel.FULL,
                            representation="full",
                            tokens=100,
                        ),
                    ),
                    token_count=100,
                    chunk_index=0,
                ),
            ),
            total_tokens=100,
            total_files=1,
            task=ContextTask.BUG_FIX,
        )
        content = {"src/auth.py": FileContent(path="src/auth.py", content="def auth(): pass", hash="abc")}
        chunks = self.materializer.materialize(plan, content)
        entry = chunks[0].entries[0]
        assert entry.provenance is not None
        assert entry.provenance.source_file == "src/auth.py"
        assert entry.provenance.compression_applied == CompressionLevel.FULL

    def test_provenance_for_fragment(self) -> None:
        """Test that provenance records correct line range for fragments."""
        plan = ContextPlan(
            chunks=(
                ContextChunk(
                    files=(
                        PlannedFile(
                            path="src/parser.py",
                            role=FileRole.DOMAIN,
                            importance=2,
                            compression=CompressionLevel.SIGNATURES,
                            representation="fragment 2/3",
                            tokens=150,
                            is_fragment=True,
                            fragment_index=1,
                            fragment_total=3,
                            line_start=100,
                            line_end=200,
                        ),
                    ),
                    token_count=150,
                    chunk_index=0,
                ),
            ),
            total_tokens=150,
            total_files=1,
            task=ContextTask.GENERAL,
        )
        content = {"src/parser.py": FileContent(path="src/parser.py", content="x\n" * 200, hash="abc")}
        chunks = self.materializer.materialize(plan, content)
        entry = chunks[0].entries[0]
        assert entry.provenance is not None
        assert entry.provenance.source_lines == (100, 200)

    def test_missing_content_handled(self) -> None:
        """Test that missing content is handled gracefully."""
        plan = ContextPlan(
            chunks=(
                ContextChunk(
                    files=(
                        PlannedFile(
                            path="src/missing.py",
                            role=FileRole.UNKNOWN,
                            importance=5,
                            compression=CompressionLevel.FULL,
                            representation="full",
                            tokens=100,
                        ),
                    ),
                    token_count=100,
                    chunk_index=0,
                ),
            ),
            total_tokens=100,
            total_files=1,
            task=ContextTask.GENERAL,
        )
        content: dict[str, FileContent] = {}
        chunks = self.materializer.materialize(plan, content)
        assert len(chunks) == 0

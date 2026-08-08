"""Tests for MarkdownRenderer."""

from __future__ import annotations

from arian.domain.context.models import ContextChunk
from arian.domain.context.models import ContextPlan
from arian.domain.context.models import ContextTask
from arian.domain.context.models import MaterializedChunk
from arian.domain.context.models import MaterializedEntry
from arian.domain.context.models import PlannedFile
from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import FileRole
from arian.infrastructure.output.markdown.renderer import MarkdownRenderer


class TestMarkdownRenderer:
    """Tests for MarkdownRenderer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.renderer = MarkdownRenderer()

    def test_render_empty_plan(self) -> None:
        """Test rendering an empty plan."""
        plan = ContextPlan(
            chunks=(),
            total_tokens=0,
            total_files=0,
            task=ContextTask.GENERAL,
        )
        result = self.renderer.render((), plan)
        assert result.is_success
        assert "Files: 0" in result.value
        assert "Tokens: 0" in result.value

    def test_render_with_files(self) -> None:
        """Test rendering with materialized files."""
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
            task=ContextTask.BUG_FIX,
        )
        chunks = (
            MaterializedChunk(
                entries=(
                    MaterializedEntry(
                        path="src/main.py",
                        role=FileRole.SERVICE,
                        importance=3,
                        compression=CompressionLevel.FULL,
                        content="def main(): pass",
                        tokens=100,
                    ),
                ),
                token_count=100,
                chunk_index=0,
            ),
        )
        result = self.renderer.render(chunks, plan)
        assert result.is_success
        assert "def main(): pass" in result.value
        assert "Files: 1" in result.value
        assert "bug_fix" in result.value

    def test_render_with_compressed_content(self) -> None:
        """Test rendering with compressed (signatures) content."""
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
            task=ContextTask.BUG_FIX,
        )
        chunks = (
            MaterializedChunk(
                entries=(
                    MaterializedEntry(
                        path="src/service.py",
                        role=FileRole.SERVICE,
                        importance=3,
                        compression=CompressionLevel.SIGNATURES,
                        content="class Service:\n    def method(self) -> None: ...",
                        tokens=50,
                    ),
                ),
                token_count=50,
                chunk_index=0,
            ),
        )
        result = self.renderer.render(chunks, plan)
        assert result.is_success
        assert "def method(self) -> None: ..." in result.value
        assert "SIGNATURES" in result.value

    def test_manifest_exists(self) -> None:
        """Test that YAML manifest is present in output."""
        plan = ContextPlan(
            chunks=(),
            total_tokens=0,
            total_files=0,
            task=ContextTask.GENERAL,
        )
        result = self.renderer.render((), plan)
        assert result.is_success
        assert "# Arian Context Manifest" in result.value
        assert "task: general" in result.value

    def test_fragment_labels_rendered(self) -> None:
        """Test that fragment labels are displayed."""
        plan = ContextPlan(
            chunks=(
                ContextChunk(
                    files=(
                        PlannedFile(
                            path="src/parser.py",
                            role=FileRole.DOMAIN,
                            importance=2,
                            compression=CompressionLevel.SIGNATURES,
                            representation="fragment 1/3",
                            tokens=200,
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
        chunks = (
            MaterializedChunk(
                entries=(
                    MaterializedEntry(
                        path="src/parser.py",
                        role=FileRole.DOMAIN,
                        importance=2,
                        compression=CompressionLevel.SIGNATURES,
                        content="class Parser: ...",
                        tokens=200,
                        is_fragment=True,
                        fragment_index=0,
                        fragment_total=3,
                    ),
                ),
                token_count=200,
                chunk_index=0,
            ),
        )
        result = self.renderer.render(chunks, plan)
        assert result.is_success
        assert "Fragment 1/3" in result.value

    def test_continuation_hints_rendered(self) -> None:
        """Test that continuation hints are displayed."""
        plan = ContextPlan(
            chunks=(
                ContextChunk(
                    files=(
                        PlannedFile(
                            path="src/parser.py",
                            role=FileRole.DOMAIN,
                            importance=2,
                            compression=CompressionLevel.SIGNATURES,
                            representation="fragment 1/3",
                            tokens=200,
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
        chunks = (
            MaterializedChunk(
                entries=(
                    MaterializedEntry(
                        path="src/parser.py",
                        role=FileRole.DOMAIN,
                        importance=2,
                        compression=CompressionLevel.SIGNATURES,
                        content="class Parser: ...",
                        tokens=200,
                        is_fragment=True,
                        fragment_index=0,
                        fragment_total=3,
                        continues_in_chunk=2,
                    ),
                ),
                token_count=200,
                chunk_index=0,
            ),
        )
        result = self.renderer.render(chunks, plan)
        assert result.is_success
        assert "Continues in Chunk 2" in result.value

    def test_no_provenance_in_markdown(self) -> None:
        """Test that provenance is not displayed in Markdown output."""
        from arian.domain.context.models import Provenance

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
        chunks = (
            MaterializedChunk(
                entries=(
                    MaterializedEntry(
                        path="src/auth.py",
                        role=FileRole.SERVICE,
                        importance=1,
                        compression=CompressionLevel.FULL,
                        content="def auth(): pass",
                        tokens=100,
                        provenance=Provenance(
                            source_file="src/auth.py",
                            source_lines=(0, 10),
                            compression_applied=CompressionLevel.FULL,
                        ),
                    ),
                ),
                token_count=100,
                chunk_index=0,
            ),
        )
        result = self.renderer.render(chunks, plan)
        assert result.is_success
        assert "source_file" not in result.value
        assert "source_lines" not in result.value

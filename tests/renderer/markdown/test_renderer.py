"""Tests for MarkdownRenderer."""

from __future__ import annotations

from arian.domain.context.models import ContextChunk
from arian.domain.context.models import ContextPlan
from arian.domain.context.models import ContextTask
from arian.domain.context.models import MaterializedChunk
from arian.domain.context.models import MaterializedFile
from arian.domain.context.models import PlannedFile
from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import FileRole
from arian.renderer.markdown.renderer import MarkdownRenderer


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
        assert "Files: 0" in result
        assert "Tokens: 0" in result

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
                files=(
                    MaterializedFile(
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
        assert "def main(): pass" in result
        assert "Files: 1" in result
        assert "bug_fix" in result

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
                files=(
                    MaterializedFile(
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
        assert "def method(self) -> None: ..." in result
        assert "SIGNATURES" in result

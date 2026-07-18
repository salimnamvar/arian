"""Tests for MarkdownRenderer."""

from __future__ import annotations

from pathlib import Path

from arian.domain.context.models import ContextChunk
from arian.domain.context.models import ContextPlan
from arian.domain.context.models import ContextTask
from arian.domain.context.models import PlannedFile
from arian.domain.repository.models import FileContent
from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import FileRole
from arian.renderers.markdown.renderer import MarkdownRenderer


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
        result = self.renderer.render(plan, {})
        assert "Files: 0" in result
        assert "Tokens: 0" in result

    def test_render_with_files(self) -> None:
        """Test rendering with files."""
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
        files = {
            "src/main.py": FileContent(
                path="src/main.py",
                content="def main(): pass",
                hash="abc",
            ),
        }
        result = self.renderer.render(plan, files)
        assert "def main(): pass" in result
        assert "Files: 1" in result
        assert "bug_fix" in result

    def test_render_with_root_path(self) -> None:
        """Test rendering with root path for relative display."""
        plan = ContextPlan(
            chunks=(
                ContextChunk(
                    files=(
                        PlannedFile(
                            path="/home/user/project/src/main.py",
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
        files = {
            "/home/user/project/src/main.py": FileContent(
                path="/home/user/project/src/main.py",
                content="x = 1",
                hash="abc",
            ),
        }
        result = self.renderer.render(plan, files, a_root=Path("/home/user/project"))
        assert "main.py" in result

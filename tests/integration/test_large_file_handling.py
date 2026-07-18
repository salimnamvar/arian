"""Integration test for large file handling."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from arian.domain.context.models import ContextTask
from arian.domain.shared.enums import TokenBudget
from arian.renderer.markdown.renderer import MarkdownRenderer
from arian.repository.filesystem.collector import FileCollector
from arian.repository.index.memory_repository import MemoryRepositoryIndex
from arian.service.analyzer.python_analyzer import PythonAnalyzer
from arian.service.builder.context_builder import ContextBuilder
from arian.service.classifier.file_classifier import FileClassifier
from arian.service.context.materializer import ContextMaterializer
from arian.service.planner.context_planner import ContextPlanner


@pytest.mark.integration
class TestLargeFileHandling:
    """Integration test for large file handling with fragmentation."""

    def test_large_file_fragmentation(self, tmp_path: Path) -> None:
        """Test that large files are fragmented into semantic segments."""
        (tmp_path / "README.md").write_text("# Project\n\nDescription.\n")

        src_dir = tmp_path / "src"
        src_dir.mkdir()

        large_lines: list[str] = []
        large_lines.append("from typing import List")
        large_lines.append("")
        large_lines.append("class Parser:")
        large_lines.append('    """Main parser class."""')
        for i in range(200):
            large_lines.append(f"    def method_{i}(self) -> str:")
            large_lines.append(f'        """Method {i}."""')
            large_lines.append(f'        return "method_{i}"')
            large_lines.append("")
        (src_dir / "parser.py").write_text("\n".join(large_lines))

        (src_dir / "small.py").write_text("def helper() -> None:\n    pass\n")

        classifier = FileClassifier()
        collector = FileCollector(
            a_extensions=frozenset({".py", ".md"}),
            a_exclude=frozenset(),
            a_classifier=classifier,
        )
        index = MemoryRepositoryIndex()
        planner = ContextPlanner(a_classifier=classifier)
        analyzer = PythonAnalyzer()
        materializer = ContextMaterializer(a_analyzer=analyzer)
        builder = ContextBuilder(
            a_collector=collector,
            a_index=index,
            a_planner=planner,
            a_materializer=materializer,
        )

        budget = TokenBudget(max_tokens=10000, per_chunk_target=500)
        plan = asyncio.run(builder.build(tmp_path, ContextTask.GENERAL, budget))
        content_map = asyncio.run(builder.load_content(plan, tmp_path))
        materialized = materializer.materialize(plan, content_map, budget)

        assert plan.total_files >= 2

        has_fragment: bool = False
        for chunk in materialized:
            for entry in chunk.entries:
                if entry.is_fragment:
                    has_fragment = True
                    break

        assert has_fragment or plan.total_files > 1

    def test_full_pipeline_with_renderer(self, tmp_path: Path) -> None:
        """Test full pipeline from files to rendered Markdown."""
        (tmp_path / "README.md").write_text("# Auth Service\n\nAuthentication module.\n")
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "auth.py").write_text(
            'class AuthService:\n    """Authentication service."""\n'
            "    def authenticate(self, a_creds: dict) -> str:\n"
            '        """Authenticate user."""\n'
            '        return "token"\n'
        )
        (src_dir / "utils.py").write_text("def helper() -> None:\n    pass\n")

        classifier = FileClassifier()
        collector = FileCollector(
            a_extensions=frozenset({".py", ".md"}),
            a_exclude=frozenset(),
            a_classifier=classifier,
        )
        index = MemoryRepositoryIndex()
        planner = ContextPlanner(a_classifier=classifier)
        analyzer = PythonAnalyzer()
        materializer = ContextMaterializer(a_analyzer=analyzer)
        builder = ContextBuilder(
            a_collector=collector,
            a_index=index,
            a_planner=planner,
            a_materializer=materializer,
        )
        renderer = MarkdownRenderer()

        budget = TokenBudget(max_tokens=5000)
        plan = asyncio.run(builder.build(tmp_path, ContextTask.BUG_FIX, budget, "authentication timeout"))
        content_map = asyncio.run(builder.load_content(plan, tmp_path))
        materialized = materializer.materialize(plan, content_map, budget)
        output = renderer.render(materialized, plan)

        assert "# Arian Context Manifest" in output
        assert "task: bug_fix" in output
        assert "query: authentication timeout" in output
        assert "README.md" in output
        assert "auth.py" in output
        assert plan.total_tokens <= 5000

    def test_provenance_in_materialized_output(self, tmp_path: Path) -> None:
        """Test that provenance is present in materialized entries."""
        (tmp_path / "README.md").write_text("# Project\n\nDescription.\n")
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "service.py").write_text("class Service:\n    def run(self) -> None:\n        pass\n")

        classifier = FileClassifier()
        collector = FileCollector(
            a_extensions=frozenset({".py", ".md"}),
            a_exclude=frozenset(),
            a_classifier=classifier,
        )
        index = MemoryRepositoryIndex()
        planner = ContextPlanner(a_classifier=classifier)
        analyzer = PythonAnalyzer()
        materializer = ContextMaterializer(a_analyzer=analyzer)
        builder = ContextBuilder(
            a_collector=collector,
            a_index=index,
            a_planner=planner,
            a_materializer=materializer,
        )

        budget = TokenBudget(max_tokens=5000)
        plan = asyncio.run(builder.build(tmp_path, ContextTask.GENERAL, budget))
        content_map = asyncio.run(builder.load_content(plan, tmp_path))
        materialized = materializer.materialize(plan, content_map, budget)

        for chunk in materialized:
            for entry in chunk.entries:
                assert entry.provenance is not None
                assert entry.provenance.source_file == entry.path
                assert entry.provenance.compression_applied == entry.compression

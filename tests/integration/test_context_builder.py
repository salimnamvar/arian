"""Integration tests for the full context building pipeline."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from arian.domain.context.models import ContextTask
from arian.domain.shared.enums import TokenBudget
from arian.repository.filesystem.collector import FileCollector
from arian.repository.index.memory_repository import MemoryRepositoryIndex
from arian.service.analyzer.python_analyzer import PythonAnalyzer
from arian.service.builder.context_builder import ContextBuilder
from arian.service.classifier.file_classifier import FileClassifier
from arian.service.context.materializer import ContextMaterializer
from arian.service.planner.context_planner import ContextPlanner


@pytest.mark.integration
class TestContextBuilderIntegration:
    """Integration tests for ContextBuilder."""

    def test_build_from_real_directory(self, tmp_path: Path) -> None:
        """Test building context from a real directory."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text('def main() -> None:\n    """Main entry point."""\n    pass\n')
        (src_dir / "utils.py").write_text('def helper() -> str:\n    """Helper function."""\n    return "help"\n')

        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_main.py").write_text("def test_main() -> None:\n    assert True\n")

        (tmp_path / "README.md").write_text("# My Project\n\nA test project.\n")

        classifier = FileClassifier()
        collector = FileCollector(
            a_extensions=frozenset({".py", ".md"}),
            a_exclude=frozenset({"__pycache__", ".git"}),
            a_classifier=classifier,
        )
        index = MemoryRepositoryIndex()
        planner = ContextPlanner(a_classifier=classifier)
        materializer = ContextMaterializer(a_analyzer=PythonAnalyzer())
        builder = ContextBuilder(
            a_collector=collector,
            a_index=index,
            a_planner=planner,
            a_materializer=materializer,
        )

        budget = TokenBudget(max_tokens=5000)
        plan = asyncio.run(
            builder.build(
                a_path=tmp_path,
                a_task=ContextTask.BUG_FIX,
                a_budget=budget,
                a_query="authentication timeout",
            )
        )

        assert plan.total_files >= 3
        assert plan.total_tokens > 0
        assert len(plan.chunks) >= 1

    def test_build_loads_content(self, tmp_path: Path) -> None:
        """Test that content loading works."""
        (tmp_path / "main.py").write_text("x = 1\n")

        classifier = FileClassifier()
        collector = FileCollector(
            a_extensions=frozenset({".py"}),
            a_exclude=frozenset(),
            a_classifier=classifier,
        )
        index = MemoryRepositoryIndex()
        planner = ContextPlanner(a_classifier=classifier)
        materializer = ContextMaterializer(a_analyzer=PythonAnalyzer())
        builder = ContextBuilder(
            a_collector=collector,
            a_index=index,
            a_planner=planner,
            a_materializer=materializer,
        )

        budget = TokenBudget(max_tokens=5000)
        plan = asyncio.run(
            builder.build(
                a_path=tmp_path,
                a_task=ContextTask.GENERAL,
                a_budget=budget,
            )
        )

        content_map, _skipped = asyncio.run(builder.load_content(a_plan=plan, a_root=tmp_path))
        assert len(content_map) >= 1

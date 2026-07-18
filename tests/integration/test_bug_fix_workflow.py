"""Integration test for the north-star bug-fix workflow."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from arian.domain.context.models import ContextTask
from arian.domain.shared.enums import TokenBudget
from arian.renderers.markdown.renderer import MarkdownRenderer
from arian.repositories.filesystem.collector import FileCollector
from arian.repositories.index.memory_repository import MemoryRepositoryIndex
from arian.services.analyzer.python_analyzer import PythonAnalyzer
from arian.services.builder.context_builder import ContextBuilder
from arian.services.classifier.file_classifier import FileClassifier
from arian.services.context.materializer import ContextMaterializer
from arian.services.planner.context_planner import ContextPlanner


@pytest.mark.integration
class TestBugFixWorkflow:
    """Integration test for the north-star bug fix workflow."""

    def test_bug_fix_context_includes_correct_files(self, tmp_path: Path) -> None:
        """Test that bug-fix context includes README, auth, tests with correct compression."""
        (tmp_path / "README.md").write_text("# Auth Service\n\nAuthentication module.\n")
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "auth.py").write_text(
            'class AuthService:\n    """Authentication service."""\n'
            "    def authenticate(self, a_creds: dict) -> str:\n"
            '        """Authenticate user."""\n'
            '        return "token"\n'
        )
        (src_dir / "models.py").write_text(
            'class Token:\n    """Auth token."""\n    def __init__(self) -> None:\n        self.value = \'\'\n'
        )
        (src_dir / "database.py").write_text(
            'class DB:\n    """Database connection."""\n    def query(self) -> list:\n        return []\n'
        )
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_auth.py").write_text("def test_auth() -> None:\n    assert True\n")

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

        assert "README.md" in output
        assert "auth.py" in output
        assert "test_auth.py" in output
        assert plan.total_tokens <= 5000
        assert len(plan.chunks) >= 1

    def test_onboarding_context_prioritizes_readme(self, tmp_path: Path) -> None:
        """Test that onboarding context puts README first."""
        (tmp_path / "README.md").write_text("# Project\n\nDescription.\n")
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "app.py").write_text("def main() -> None:\n    pass\n")

        classifier = FileClassifier()
        collector = FileCollector(
            a_extensions=frozenset({".py", ".md"}),
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
        plan = asyncio.run(builder.build(tmp_path, ContextTask.ONBOARDING, budget))

        first_file: str = plan.chunks[0].files[0].path if plan.chunks and plan.chunks[0].files else ""
        assert "README" in first_file

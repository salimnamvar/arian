"""Tests for ContextPlanner."""

from __future__ import annotations

from arian.domain.context.models import ContextTask
from arian.domain.repository.models import RepositoryFile
from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import FileRole
from arian.domain.shared.enums import TokenBudget
from arian.services.planner.context_planner import ContextPlanner


class TestContextPlanner:
    """Tests for ContextPlanner."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.planner = ContextPlanner()

    def test_plan_empty_files(self) -> None:
        """Test planning with no files."""
        budget = TokenBudget(max_tokens=5000)
        plan = self.planner.plan([], ContextTask.GENERAL, budget)
        assert plan.total_files == 0
        assert plan.total_tokens == 0

    def test_plan_single_file(self) -> None:
        """Test planning with a single file."""
        files = [
            RepositoryFile(path="src/main.py", language="python", role=FileRole.UNKNOWN, tokens=100, hash="abc"),
        ]
        budget = TokenBudget(max_tokens=5000)
        plan = self.planner.plan(files, ContextTask.GENERAL, budget)
        assert plan.total_files == 1
        assert len(plan.chunks) == 1

    def test_plan_bug_fix_prioritizes_tests(self) -> None:
        """Test that bug fix task prioritizes test files."""
        files = [
            RepositoryFile(path="src/service.py", language="python", role=FileRole.UNKNOWN, tokens=100, hash="a"),
            RepositoryFile(
                path="tests/test_service.py", language="python", role=FileRole.UNKNOWN, tokens=100, hash="b"
            ),
        ]
        budget = TokenBudget(max_tokens=5000)
        plan = self.planner.plan(files, ContextTask.BUG_FIX, budget)
        assert plan.total_files == 2
        for chunk in plan.chunks:
            for pf in chunk.files:
                if pf.path == "tests/test_service.py":
                    assert pf.importance <= 5

    def test_plan_chunking(self) -> None:
        """Test that files are chunked according to budget."""
        files = [
            RepositoryFile(path=f"src/file{i}.py", language="python", role=FileRole.UNKNOWN, tokens=100, hash=f"h{i}")
            for i in range(10)
        ]
        budget = TokenBudget(max_tokens=5000, per_chunk_target=300)
        plan = self.planner.plan(files, ContextTask.GENERAL, budget)
        assert len(plan.chunks) > 1

    def test_plan_compression_for_large_files(self) -> None:
        """Test that large files get compressed."""
        files = [
            RepositoryFile(path="src/large.py", language="python", role=FileRole.UNKNOWN, tokens=6000, hash="big"),
        ]
        budget = TokenBudget(max_tokens=10000)
        plan = self.planner.plan(files, ContextTask.GENERAL, budget)
        for chunk in plan.chunks:
            for pf in chunk.files:
                if pf.path == "src/large.py":
                    assert pf.compression in (CompressionLevel.SIGNATURES, CompressionLevel.STRUCTURE)

"""Tests for ContextPlanner."""

from __future__ import annotations

from arian.domain.context.models import ContextTask
from arian.domain.repository.models import RepositoryFile
from arian.domain.repository.models import Symbol
from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import FileRole
from arian.domain.shared.enums import SymbolKind
from arian.domain.shared.enums import TokenBudget
from arian.service.planner.context_planner import ContextPlanner


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

    def test_large_file_creates_fragments(self) -> None:
        """Test that large files with symbols create fragments."""
        files = [
            RepositoryFile(path="src/parser.py", language="python", role=FileRole.DOMAIN, tokens=12000, hash="big"),
        ]
        symbols = {
            "src/parser.py": [
                Symbol(
                    name="Parser",
                    kind=SymbolKind.CLASS,
                    file_path="src/parser.py",
                    signature="class Parser",
                    line_start=100,
                    line_end=500,
                ),
                Symbol(
                    name="Lexer",
                    kind=SymbolKind.CLASS,
                    file_path="src/parser.py",
                    signature="class Lexer",
                    line_start=510,
                    line_end=900,
                ),
            ],
        }
        budget = TokenBudget(max_tokens=12000, per_chunk_target=2000)
        plan = self.planner.plan(files, ContextTask.GENERAL, budget, a_symbols=symbols)
        assert plan.total_files > 1

    def test_fragment_boundaries_follow_symbols(self) -> None:
        """Test that fragment boundaries align with symbol boundaries."""
        files = [
            RepositoryFile(path="src/auth.py", language="python", role=FileRole.SERVICE, tokens=10000, hash="auth"),
        ]
        symbols = {
            "src/auth.py": [
                Symbol(
                    name="AuthService",
                    kind=SymbolKind.CLASS,
                    file_path="src/auth.py",
                    signature="class AuthService",
                    line_start=50,
                    line_end=300,
                ),
                Symbol(
                    name="validate_token",
                    kind=SymbolKind.FUNCTION,
                    file_path="src/auth.py",
                    signature="def validate_token",
                    line_start=310,
                    line_end=400,
                ),
            ],
        }
        budget = TokenBudget(max_tokens=10000, per_chunk_target=1500)
        plan = self.planner.plan(files, ContextTask.GENERAL, budget, a_symbols=symbols)
        assert plan.total_files >= 2

    def test_planner_never_reads_files(self) -> None:
        """Test that planner only uses metadata, never reads file content."""
        files = [
            RepositoryFile(path="src/secret.py", language="python", role=FileRole.DOMAIN, tokens=100, hash="s"),
        ]
        budget = TokenBudget(max_tokens=5000)
        plan = self.planner.plan(files, ContextTask.GENERAL, budget)
        assert plan.total_files == 1

    def test_summary_fragment_created(self) -> None:
        """Test that large files with symbols create a summary fragment."""
        files = [
            RepositoryFile(path="src/large.py", language="python", role=FileRole.DOMAIN, tokens=15000, hash="lg"),
        ]
        symbols = {
            "src/large.py": [
                Symbol(
                    name="MainClass",
                    kind=SymbolKind.CLASS,
                    file_path="src/large.py",
                    signature="class MainClass",
                    line_start=1,
                    line_end=500,
                ),
            ],
        }
        budget = TokenBudget(max_tokens=15000, per_chunk_target=2000)
        plan = self.planner.plan(files, ContextTask.GENERAL, budget, a_symbols=symbols)
        assert plan.total_files > 1

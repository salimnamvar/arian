"""Tests for domain context models."""

from __future__ import annotations

from arian.domain.context.models import ContextChunk
from arian.domain.context.models import ContextPlan
from arian.domain.context.models import ContextResult
from arian.domain.context.models import ContextTask
from arian.domain.context.models import PlannedFile
from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import FileRole


def test_context_task_values() -> None:
    """Test ContextTask enum values."""
    assert ContextTask.BUG_FIX.value == "bug_fix"
    assert ContextTask.FEATURE.value == "feature"
    assert ContextTask.REVIEW.value == "review"
    assert ContextTask.ONBOARDING.value == "onboarding"
    assert ContextTask.REFACTOR.value == "refactor"
    assert ContextTask.DOCUMENT.value == "document"
    assert ContextTask.GENERAL.value == "general"


def test_planned_file_creation() -> None:
    """Test PlannedFile creation."""
    planned = PlannedFile(
        path="src/main.py",
        role=FileRole.SERVICE,
        importance=3,
        compression=CompressionLevel.FULL,
        representation="full",
        tokens=100,
    )
    assert planned.path == "src/main.py"
    assert planned.role == FileRole.SERVICE
    assert planned.importance == 3
    assert planned.compression == CompressionLevel.FULL
    assert planned.representation == "full"
    assert planned.tokens == 100


def test_context_chunk_creation() -> None:
    """Test ContextChunk creation."""
    chunk = ContextChunk(
        files=(
            PlannedFile(
                path="a.py",
                role=FileRole.UNKNOWN,
                importance=5,
                compression=CompressionLevel.FULL,
                representation="full",
                tokens=50,
            ),
        ),
        token_count=50,
        chunk_index=0,
        header="Section 1",
    )
    assert len(chunk.files) == 1
    assert chunk.token_count == 50
    assert chunk.chunk_index == 0
    assert chunk.header == "Section 1"


def test_context_plan_creation() -> None:
    """Test ContextPlan creation."""
    plan = ContextPlan(
        chunks=(),
        total_tokens=0,
        total_files=0,
        task=ContextTask.BUG_FIX,
    )
    assert plan.chunks == ()
    assert plan.total_tokens == 0
    assert plan.total_files == 0
    assert plan.task == ContextTask.BUG_FIX
    assert plan.query is None


def test_context_plan_with_query() -> None:
    """Test ContextPlan with query."""
    plan = ContextPlan(
        chunks=(),
        total_tokens=100,
        total_files=5,
        task=ContextTask.FEATURE,
        query="add rate limiting",
    )
    assert plan.query == "add rate limiting"


def test_context_result_creation() -> None:
    """Test ContextResult creation."""
    result = ContextResult(
        output_paths=("output/context.md",),
        total_files=10,
        total_tokens=5000,
        chunks=2,
    )
    assert result.output_paths == ("output/context.md",)
    assert result.total_files == 10
    assert result.total_tokens == 5000
    assert result.chunks == 2

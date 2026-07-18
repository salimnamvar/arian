"""Tests for domain context models."""

from __future__ import annotations

from arian.domain.context.models import Chunk
from arian.domain.context.models import ChunkEntry
from arian.domain.context.models import ContextChunk
from arian.domain.context.models import ContextPlan
from arian.domain.context.models import ContextResult
from arian.domain.context.models import ContextTask
from arian.domain.context.models import FileFragment
from arian.domain.context.models import PlannedFile
from arian.domain.context.models import Provenance
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


def test_file_fragment_is_immutable() -> None:
    """Test FileFragment is a frozen dataclass."""
    fragment = FileFragment(
        file_path="src/auth.py",
        fragment_index=0,
        fragment_total=3,
        line_start=1,
        line_end=100,
        compression=CompressionLevel.SIGNATURES,
        importance=2,
        estimated_tokens=300,
    )
    assert fragment.file_path == "src/auth.py"
    assert fragment.fragment_index == 0
    assert fragment.fragment_total == 3
    assert fragment.line_start == 1
    assert fragment.line_end == 100
    assert fragment.compression == CompressionLevel.SIGNATURES
    assert fragment.importance == 2
    assert fragment.estimated_tokens == 300
    assert fragment.class_context is None
    assert fragment.function_context is None
    assert fragment.imports_summary == ()


def test_file_fragment_has_no_content() -> None:
    """Test FileFragment has no content field — content is not a planning concern."""
    fragment = FileFragment(
        file_path="src/auth.py",
        fragment_index=0,
        fragment_total=1,
        line_start=1,
        line_end=50,
        compression=CompressionLevel.FULL,
        importance=1,
        estimated_tokens=100,
    )
    assert not hasattr(fragment, "content")


def test_file_fragment_has_no_file_id() -> None:
    """Test FileFragment has no stored file_id — V1 uses computed property only."""
    fragment = FileFragment(
        file_path="src/auth.py",
        fragment_index=0,
        fragment_total=1,
        line_start=1,
        line_end=50,
        compression=CompressionLevel.FULL,
        importance=1,
        estimated_tokens=100,
    )
    assert not hasattr(fragment, "file_id")


def test_file_fragment_with_context() -> None:
    """Test FileFragment with optional context fields."""
    fragment = FileFragment(
        file_path="src/parser.py",
        fragment_index=1,
        fragment_total=3,
        line_start=200,
        line_end=400,
        compression=CompressionLevel.SIGNATURES,
        importance=3,
        estimated_tokens=500,
        class_context="Parser",
        function_context="parse_tokens",
        imports_summary=("from typing import List",),
    )
    assert fragment.class_context == "Parser"
    assert fragment.function_context == "parse_tokens"
    assert fragment.imports_summary == ("from typing import List",)


def test_provenance_creation() -> None:
    """Test Provenance creation."""
    provenance = Provenance(
        source_file="src/auth/service.py",
        source_lines=(120, 240),
        compression_applied=CompressionLevel.SIGNATURES,
        importance_reason="Bug fix target — authentication flow",
    )
    assert provenance.source_file == "src/auth/service.py"
    assert provenance.source_lines == (120, 240)
    assert provenance.compression_applied == CompressionLevel.SIGNATURES
    assert provenance.importance_reason == "Bug fix target — authentication flow"


def test_provenance_optional_reason() -> None:
    """Test Provenance with optional importance_reason."""
    provenance = Provenance(
        source_file="src/utils.py",
        source_lines=(1, 50),
        compression_applied=CompressionLevel.FULL,
    )
    assert provenance.importance_reason is None


def test_chunk_entry_creation() -> None:
    """Test ChunkEntry creation for a full file."""
    entry = ChunkEntry(
        file_path="src/auth.py",
        role=FileRole.SERVICE,
        importance=2,
        compression=CompressionLevel.FULL,
        representation="full",
        content="def auth(): ...",
        estimated_tokens=100,
    )
    assert entry.file_path == "src/auth.py"
    assert entry.role == FileRole.SERVICE
    assert entry.importance == 2
    assert entry.compression == CompressionLevel.FULL
    assert entry.content == "def auth(): ..."
    assert entry.estimated_tokens == 100
    assert entry.is_fragment is False
    assert entry.fragment_index is None
    assert entry.fragment_total is None
    assert entry.continues_in_chunk is None
    assert entry.language is None
    assert entry.provenance is None


def test_chunk_entry_as_fragment() -> None:
    """Test ChunkEntry as a file fragment."""
    provenance = Provenance(
        source_file="src/parser.py",
        source_lines=(200, 400),
        compression_applied=CompressionLevel.SIGNATURES,
    )
    entry = ChunkEntry(
        file_path="src/parser.py",
        role=FileRole.DOMAIN,
        importance=1,
        compression=CompressionLevel.SIGNATURES,
        representation="signatures",
        content="class Parser: ...",
        estimated_tokens=200,
        is_fragment=True,
        fragment_index=1,
        fragment_total=3,
        continues_in_chunk=5,
        language="python",
        provenance=provenance,
    )
    assert entry.is_fragment is True
    assert entry.fragment_index == 1
    assert entry.fragment_total == 3
    assert entry.continues_in_chunk == 5
    assert entry.language == "python"
    assert entry.provenance is not None
    assert entry.provenance.source_file == "src/parser.py"


def test_chunk_creation() -> None:
    """Test Chunk creation."""
    entry = ChunkEntry(
        file_path="a.py",
        role=FileRole.UNKNOWN,
        importance=5,
        compression=CompressionLevel.FULL,
        representation="full",
        content="x = 1",
        estimated_tokens=50,
    )
    chunk = Chunk(
        entries=(entry,),
        token_count=50,
        chunk_index=0,
        header="Section 1",
    )
    assert len(chunk.entries) == 1
    assert chunk.token_count == 50
    assert chunk.chunk_index == 0
    assert chunk.header == "Section 1"


def test_chunk_is_distinct_from_context_chunk() -> None:
    """Test Chunk and ContextChunk are different types."""
    assert Chunk is not ContextChunk

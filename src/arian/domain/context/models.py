"""Context domain models for Arian."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import ContextTask
from arian.domain.shared.enums import FileRole
from arian.domain.shared.enums import TokenBudget
from arian.domain.shared.result import Result


@dataclass(frozen=True)
class BuildRequest:
    """Per-call input to the context build pipeline.

    Grouping all build inputs into a single object keeps the public
    surface short and self-documenting, and makes it easy to add new
    optional fields without breaking existing callers.

    Attributes:
        path: Repository root path.
        task: The context task type.
        budget: Token budget constraints.
        query: Optional query for relevance matching.
        root: Root for computing relative paths. Defaults to ``path``.
        input_paths: Optional list of specific input paths to scan.
        explicit_paths: Paths whose contents always pass the
            ``.gitignore`` filter. Mirrors ``git add -f`` semantics.
    """

    path: Path
    task: ContextTask
    budget: TokenBudget
    query: str | None = None
    root: Path | None = None
    input_paths: list[Path] | None = None
    explicit_paths: frozenset[Path] = field(default_factory=frozenset[Path])


@dataclass(frozen=True)
class ContextPlan:
    """Output of the Context Planner — what to include and how.

    Attributes:
        chunks: Tuple of planned context chunks.
        total_tokens: Total token count across all chunks.
        total_files: Total number of files included in plan.
        task: The context task type.
        query: Optional query string for relevance matching.
        metadata: Optional metadata dict for manifest (repository, budget, scope, paths).
        repository_files: All collected file paths (for full directory tree).
    """

    chunks: tuple[ContextChunk, ...]
    total_tokens: int
    total_files: int
    task: ContextTask
    query: str | None = None
    metadata: dict[str, str | int | dict[str, str | int | None] | dict[str, int] | list[str]] | None = None
    repository_files: tuple[str, ...] = ()

    def validate(self) -> Result[None]:
        """Validate ContextPlan invariants.

        Returns:
            Result[None] with is_success and message.
        """
        seen_paths: set[str] = set()
        computed_tokens: int = 0
        msg: str = ""
        b_continue: bool = True

        for chunk in self.chunks:
            chunk_tokens: int = 0
            for planned_file in chunk.files:
                if planned_file.compression == CompressionLevel.AUTO:
                    msg = f"AUTO compression not resolved: {planned_file.path}"
                    b_continue = False
                    break
                chunk_tokens += planned_file.tokens
                if planned_file.path in seen_paths:
                    msg = f"Duplicate file in plan: {planned_file.path}"
                    b_continue = False
                    break
                seen_paths.add(planned_file.path)
            if not b_continue:
                break
            if chunk_tokens != chunk.token_count:
                msg = f"Chunk token count mismatch: {chunk_tokens} != {chunk.token_count}"
                b_continue = False
                break
            computed_tokens += chunk_tokens

        if b_continue and not msg and computed_tokens != self.total_tokens:
            msg = f"Total token count mismatch: {computed_tokens} != {self.total_tokens}"

        result: Result[None] = Result.success(None)
        if msg:
            result = Result.failure(msg)

        return result


@dataclass(frozen=True)
class ContextChunk:
    """A single chunk of context.

    Attributes:
        files: Tuple of planned files in this chunk.
        token_count: Token count for this chunk.
        chunk_index: Zero-based chunk index.
        header: Optional section header.
    """

    files: tuple[PlannedFile, ...]
    token_count: int
    chunk_index: int
    header: str = ""


@dataclass(frozen=True)
class PlannedFile:
    """A file with its planned representation.

    Attributes:
        path: Relative file path.
        role: File role.
        importance: Importance score (0=highest, 100=lowest).
        compression: Compression level to apply.
        representation: Human-readable representation name.
        tokens: Estimated token count at this compression level.
        language: Detected language identifier (computed once at collection).
        is_fragment: True if this is a file fragment (not a full file).
        fragment_index: Fragment position within the file (None for full files).
        fragment_total: Total fragments for this file (None for full files).
        line_start: First line number for fragments (None for full files).
        line_end: Last line number for fragments (None for full files).
    """

    path: str
    role: FileRole
    importance: int
    compression: CompressionLevel
    representation: str
    tokens: int
    language: str = ""
    is_fragment: bool = False
    fragment_index: int | None = None
    fragment_total: int | None = None
    line_start: int | None = None
    line_end: int | None = None


@dataclass(frozen=True)
class ContextResult:
    """Final output of the build process.

    Attributes:
        output_paths: Paths to generated output files.
        total_files: Total number of files included.
        total_tokens: Total token count.
        chunks: Number of chunks generated.
    """

    output_paths: tuple[str, ...]
    total_files: int
    total_tokens: int
    chunks: int


@dataclass(frozen=True)
class MaterializedEntry:
    """A materialized entry ready for rendering — full file or fragment.

    Attributes:
        path: Relative file path.
        role: File role.
        importance: Importance score.
        compression: Compression level applied.
        content: Compressed content string.
        tokens: Actual token count.
        is_fragment: True if this is a file fragment (not a full file).
        fragment_index: Fragment position within the file (None for full files).
        fragment_total: Total fragments for this file (None for full files).
        continues_in_chunk: Chunk index where the next fragment appears (None if last).
        language: Detected language identifier.
        provenance: Optional provenance metadata.
    """

    path: str
    role: FileRole
    importance: int
    compression: CompressionLevel
    content: str
    tokens: int
    is_fragment: bool = False
    fragment_index: int | None = None
    fragment_total: int | None = None
    continues_in_chunk: int | None = None
    language: str | None = None
    provenance: Provenance | None = None


# Backward compatibility alias
MaterializedFile = MaterializedEntry


@dataclass(frozen=True)
class MaterializedChunk:
    """A chunk with materialized content ready for rendering.

    Attributes:
        entries: Tuple of materialized entries in this chunk.
        token_count: Token count for this chunk.
        chunk_index: Zero-based chunk index.
        header: Optional section header.
    """

    entries: tuple[MaterializedEntry, ...]
    token_count: int
    chunk_index: int
    header: str = ""


@dataclass(frozen=True)
class FileFragment:
    """A fragment of a file created during planning for large file handling.

    A FileFragment is a planning artifact — created during context planning
    and destroyed after context generation. It is NOT a repository entity.

    Attributes:
        file_path: Relative file path of the originating file.
        fragment_index: Zero-based position within the file.
        fragment_total: Total number of fragments for this file.
        line_start: First line number (inclusive).
        line_end: Last line number (exclusive). None = read to end of file.
        compression: Compression level to apply to this fragment.
        importance: Importance score for this fragment.
        estimated_tokens: Estimated token count (not exact until materialized).
        class_context: Class name at the split point, if applicable.
        function_context: Function name at the split point, if applicable.
        imports_summary: Relevant imports for this fragment.
    """

    file_path: str
    fragment_index: int
    fragment_total: int
    line_start: int
    compression: CompressionLevel
    importance: int
    estimated_tokens: int
    line_end: int | None = None
    class_context: str | None = None
    function_context: str | None = None
    imports_summary: tuple[str, ...] = ()


@dataclass(frozen=True)
class Provenance:
    """Metadata tracing where content came from.

    Provenance is for debugging, validation, MCP jump-to-source,
    and future IDE integration. It is NOT exposed in Markdown output.

    Attributes:
        source_file: Relative file path of the originating file.
        source_lines: Tuple of (start_line, end_line) used after materialization.
        compression_applied: Compression level that was actually applied.
        importance_reason: Why this entry has this importance score.
    """

    source_file: str
    source_lines: tuple[int, int]
    compression_applied: CompressionLevel
    importance_reason: str | None = None


@dataclass(frozen=True)
class ChunkEntry:
    """A single entry within a chunk — either a full file or a fragment.

    Attributes:
        file_path: Relative file path.
        role: File role.
        importance: Importance score.
        compression: Compression level applied.
        representation: Human-readable representation name.
        content: Materialized content string.
        estimated_tokens: Estimated token count.
        is_fragment: True if this is a file fragment (not a full file).
        fragment_index: Fragment position within the file (None for full files).
        fragment_total: Total fragments for this file (None for full files).
        continues_in_chunk: Chunk index where the next fragment appears (None if last).
        language: Detected language identifier.
        provenance: Optional provenance metadata.
    """

    file_path: str
    role: FileRole
    importance: int
    compression: CompressionLevel
    representation: str
    content: str
    estimated_tokens: int
    is_fragment: bool = False
    fragment_index: int | None = None
    fragment_total: int | None = None
    continues_in_chunk: int | None = None
    language: str | None = None
    provenance: Provenance | None = None


@dataclass(frozen=True)
class Chunk:
    """A single chunk of context entries.

    Attributes:
        entries: Tuple of chunk entries in this chunk.
        token_count: Token count for this chunk.
        chunk_index: Zero-based chunk index.
        header: Optional section header.
    """

    entries: tuple[ChunkEntry, ...]
    token_count: int
    chunk_index: int
    header: str = ""

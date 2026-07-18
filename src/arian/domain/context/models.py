"""Context domain models for Arian."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import FileRole


class ContextTask(Enum):
    """Task type driving context generation.

    Attributes:
        BUG_FIX: Fixing a bug or issue.
        FEATURE: Implementing a new feature.
        REVIEW: Code review.
        ONBOARDING: New team member onboarding.
        REFACTOR: Code refactoring.
        DOCUMENT: Documentation generation.
        GENERAL: General purpose context.
    """

    BUG_FIX = "bug_fix"
    FEATURE = "feature"
    REVIEW = "review"
    ONBOARDING = "onboarding"
    REFACTOR = "refactor"
    DOCUMENT = "document"
    GENERAL = "general"


@dataclass(frozen=True)
class ContextPlan:
    """Output of the Context Planner — what to include and how.

    Attributes:
        chunks: Tuple of planned context chunks.
        total_tokens: Total token count across all chunks.
        total_files: Total number of files included.
        task: The context task type.
        query: Optional query string for relevance matching.
    """

    chunks: tuple[ContextChunk, ...]
    total_tokens: int
    total_files: int
    task: ContextTask
    query: str | None = None


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
    """

    path: str
    role: FileRole
    importance: int
    compression: CompressionLevel
    representation: str
    tokens: int


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

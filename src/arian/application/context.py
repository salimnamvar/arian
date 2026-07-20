"""Application-layer DTOs for context generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContextRequest:
    """Input DTO for context generation — constructed by the controller.

    Attributes:
        task: Task type string (e.g. "bug_fix", "feature").
        budget: Maximum token count, or None for unlimited.
        output_path: Output file path string (supports ~ expansion).
        scope: Scope mode — "merged", "separate", or "group".
        paths: Tuple of relative path strings to include.
        group: Tuple of path-tuples, one per group.
        query: Optional query string for relevance matching.
    """

    task: str = "general"
    budget: int | None = None
    output_path: str = "~/.arian/output/context.md"
    scope: str = "merged"
    paths: tuple[str, ...] = ()
    group: tuple[tuple[str, ...], ...] = ()
    query: str | None = None


@dataclass(frozen=True)
class ContextResult:
    """Output DTO for context generation — returned to the controller.

    Attributes:
        output_path: Resolved path to the generated output file.
        total_files: Number of files included in the context.
        total_tokens: Total token count of the context.
        elapsed_seconds: Wall-clock time for the entire operation.
        skipped_files: Files that failed to load.
        warnings: Non-fatal warnings.
    """

    output_path: Path
    total_files: int
    total_tokens: int
    elapsed_seconds: float
    skipped_files: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

"""Arian domain models.

Domain entities for the context builder application.

Classes:
    Document: A single document to include in context.
    ContextConfig: Configuration for context building.
    ContextResult: Result of context building operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any

from arian.domain.enums import OutputMode


@dataclass(frozen=True)
class Document:
    """A single document to include in context.

    Attributes:
        path (str): Source file path.
        content (str): File content.
        tokens (int): Token count of content.
        language (str): Detected language from extension.
    """

    path: str = field(metadata={"description": "Source file path"})
    content: str = field(default="", metadata={"description": "File content"})
    tokens: int = field(default=0, metadata={"description": "Token count of content"})
    language: str = field(default="", metadata={"description": "Detected language from extension"})

    def __lt__(self, other: Any) -> bool:
        """Compare documents by path for sorting."""
        if not isinstance(other, Document):
            return NotImplemented
        return self.path < other.path


@dataclass(frozen=True)
class ContextConfig:
    """Configuration for context building.

    Attributes:
        inputs (tuple[str, ...]): Input paths to process.
        extensions (frozenset[str]): File extensions to include.
        exclude (frozenset[str]): Directory names to exclude.
        mode (OutputMode): Output mode (separate or aggregate).
        output_path (str): Output file or directory path.
        max_tokens (int | None): Maximum tokens per chunk.
    """

    inputs: tuple[str, ...] = field(metadata={"description": "Input paths to process"})
    extensions: frozenset[str] = field(metadata={"description": "File extensions to include"})
    exclude: frozenset[str] = field(metadata={"description": "Directory names to exclude"})
    mode: OutputMode = field(metadata={"description": "Output mode (separate or aggregate)"})
    output_path: str = field(metadata={"description": "Output file or directory path"})
    max_tokens: int | None = field(default=None, metadata={"description": "Maximum tokens per chunk"})


@dataclass(frozen=True)
class ContextResult:
    """Result of context building operation.

    Attributes:
        output_paths (tuple[str, ...]): Paths to output files.
        total_files (int): Total number of files processed.
        total_tokens (int): Total token count across all files.
        chunks (int): Number of chunks if split.
    """

    output_paths: tuple[str, ...] = field(metadata={"description": "Paths to output files"})
    total_files: int = field(metadata={"description": "Total number of files processed"})
    total_tokens: int = field(metadata={"description": "Total token count across all files"})
    chunks: int = field(default=1, metadata={"description": "Number of chunks if split"})
"""Arian domain models.

Domain entities for the context builder application.

Classes:
    InputSpec: Tagged input path specification.
    Document: A single document to include in context.
    CompressionLevel: Controls content inclusion for a file.
    FileClassification: Classification of a file's role.
    PatternRule: Per-pattern compression override.
    ContextConfig: Configuration for context building.
    ContextResult: Result of context building operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from arian.domain.enums import FileRole
from arian.domain.enums import OutputMode


@dataclass(frozen=True)
class InputSpec:
    """Tagged input path specification.

    Attributes:
        path (str): Filesystem path (file or directory).
        tag (str): Optional grouping tag for output organization.
    """

    path: str = field(metadata={"description": "Filesystem path (file or directory)"})
    tag: str = field(default="", metadata={"description": "Optional grouping tag"})


@dataclass(frozen=True)
class Document:
    """A single document to include in context.

    Attributes:
        path (str): Source file path.
        content (str): File content.
        tokens (int): Token count of content.
        language (str): Detected language from extension.
        tag (str): Grouping tag from InputSpec.
    """

    path: str = field(metadata={"description": "Source file path"})
    content: str = field(default="", metadata={"description": "File content"})
    tokens: int = field(default=0, metadata={"description": "Token count of content"})
    language: str = field(default="", metadata={"description": "Detected language from extension"})
    tag: str = field(default="", metadata={"description": "Grouping tag from InputSpec"})


@dataclass(frozen=True)
class CompressionLevel:
    """Controls how much content to include for a file.

    Attributes:
        keep_comments (bool): Whether to keep code comments.
        keep_docstrings (bool): Whether to keep docstrings.
        keep_type_hints (bool): Whether to keep type hints.
        keep_implementation (bool): Whether to keep function/method bodies.
        keep_imports (bool): Whether to keep import statements.
    """

    keep_comments: bool = True
    keep_docstrings: bool = True
    keep_type_hints: bool = True
    keep_implementation: bool = True
    keep_imports: bool = True


FULL = CompressionLevel()
SIGNATURES = CompressionLevel(
    keep_comments=False,
    keep_docstrings=True,
    keep_implementation=False,
)
STRUCTURE_ONLY = CompressionLevel(
    keep_comments=False,
    keep_docstrings=False,
    keep_implementation=False,
    keep_imports=False,
)


@dataclass(frozen=True)
class FileClassification:
    """Classification of a file's role in the project.

    Attributes:
        path (str): File path that was classified.
        role (FileRole): Detected role.
        importance (int): Importance rank (0=highest, 10=lowest).
        compression (CompressionLevel): Recommended compression level.
    """

    path: str = field(metadata={"description": "File path that was classified"})
    role: FileRole = field(metadata={"description": "Detected file role"})
    importance: int = field(metadata={"description": "Importance rank (0=highest)"})
    compression: CompressionLevel = field(metadata={"description": "Recommended compression"})


@dataclass(frozen=True)
class PatternRule:
    """Per-pattern compression override.

    Attributes:
        pattern (str): Glob pattern to match file paths.
        compression (str): Compression mode name (full, compressed, structure_only).
    """

    pattern: str = field(metadata={"description": "Glob pattern to match file paths"})
    compression: str = field(metadata={"description": "Compression mode name"})


@dataclass(frozen=True)
class ContextConfig:
    """Configuration for context building.

    Attributes:
        inputs (tuple[InputSpec, ...]): Tagged input paths to process.
        extensions (frozenset[str]): File extensions to include.
        exclude (frozenset[str]): Directory names to exclude.
        mode (OutputMode): Output mode (separate or aggregate).
        output_path (str): Output file or directory path.
        max_tokens (int | None): Maximum tokens per chunk.
        compression (str): Compression strategy (full, auto, signatures, minimal).
        include_comments (bool | None): Override comment inclusion.
        include_docstrings (bool | None): Override docstring inclusion.
        include_imports (bool | None): Override import inclusion.
        include_line_numbers (bool): Whether to add line numbers to content.
        include_directory_structure (bool): Whether to include directory tree.
        include_file_summary (bool): Whether to include file summary header.
        include_token_counts (bool): Whether to report token counts.
        custom_instructions (str | None): Custom instructions for the LLM.
        sort_by_importance (bool): Whether to order files by importance.
        preserve_readme_in_chunks (bool): Whether to include README in every chunk.
        pattern_rules (tuple[PatternRule, ...]): Per-pattern compression overrides.
    """

    inputs: tuple[InputSpec, ...] = field(metadata={"description": "Tagged input paths to process"})
    extensions: frozenset[str] = field(metadata={"description": "File extensions to include"})
    exclude: frozenset[str] = field(metadata={"description": "Directory names to exclude"})
    mode: OutputMode = field(metadata={"description": "Output mode (separate or aggregate)"})
    output_path: str = field(metadata={"description": "Output file or directory path"})
    max_tokens: int | None = field(default=None, metadata={"description": "Maximum tokens per chunk"})
    compression: str = field(default="auto", metadata={"description": "Compression strategy"})
    include_comments: bool | None = field(default=None, metadata={"description": "Override comment inclusion"})
    include_docstrings: bool | None = field(default=None, metadata={"description": "Override docstring inclusion"})
    include_imports: bool | None = field(default=None, metadata={"description": "Override import inclusion"})
    include_line_numbers: bool = field(default=False, metadata={"description": "Add line numbers"})
    include_directory_structure: bool = field(default=True, metadata={"description": "Include directory tree"})
    include_file_summary: bool = field(default=True, metadata={"description": "Include file summary"})
    include_token_counts: bool = field(default=True, metadata={"description": "Report token counts"})
    custom_instructions: str | None = field(default=None, metadata={"description": "Custom LLM instructions"})
    sort_by_importance: bool = field(default=True, metadata={"description": "Order files by importance"})
    preserve_readme_in_chunks: bool = field(default=True, metadata={"description": "README in every chunk"})
    pattern_rules: tuple[PatternRule, ...] = field(
        default_factory=tuple,
        metadata={"description": "Per-pattern compression overrides"},
    )


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

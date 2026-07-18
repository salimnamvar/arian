"""Arian domain models.

Domain entities for the context builder application.

Classes:
    BaseEntity: Abstract base for domain dataclass entities.
    Document: A single document to include in context.
    ContextConfig: Configuration for context building.
    ContextResult: Result of context building operation.
"""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import astuple
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Self

from arian.domain.enums import OutputMode


@dataclass(order=True, frozen=True)
class BaseEntity:
    """Abstract base for domain dataclass entities.

    Provides shared serialization helpers. Subclasses define fields only.
    """

    def to_dict(self) -> dict[str, Any]:
        """Convert instance to a dictionary.

        Returns:
            Dict[str, Any]: All attributes as a dictionary.
        """
        result: dict[str, Any] = asdict(self)
        return result

    def to_tuple(self) -> tuple[Any, ...]:
        """Convert instance to a tuple.

        Returns:
            Tuple[Any, ...]: All field values in field-definition order.
        """
        result: tuple[Any, ...] = astuple(self)
        return result

    @classmethod
    def from_dict(cls, a_data: dict[str, Any]) -> Self:
        """Create instance from a dictionary.

        Args:
            a_data (Dict[str, Any]): Dictionary with keys matching the entity's field names.

        Returns:
            Self: An instance of the calling entity class.
        """
        result: Self = cls(**a_data)
        return result

    @classmethod
    def from_tuple(cls, a_data: tuple[Any, ...]) -> Self:
        """Create instance from a tuple.

        Args:
            a_data (Tuple[Any, ...]): Tuple of values matching the entity's field order.

        Returns:
            Self: An instance of the calling entity class.
        """
        result: Self = cls(*a_data)
        return result


@dataclass(order=True, frozen=True)
class Document(BaseEntity):
    """A single document to include in context.

    Attributes:
        path (str): Source file path.
        content (str): File content.
        tokens (int): Token count of content.
        language (str): Detected language from extension.
    """

    path: str = field(metadata={"description": "Source file path", "primary_key": True})
    content: str = field(default="", metadata={"description": "File content"})
    tokens: int = field(default=0, metadata={"description": "Token count of content"})
    language: str = field(default="", metadata={"description": "Detected language from extension"})


@dataclass(order=True, frozen=True)
class ContextConfig(BaseEntity):
    """Configuration for context building.

    Attributes:
        inputs (list[str]): Input paths to process.
        extensions (frozenset[str]): File extensions to include.
        exclude (frozenset[str]): Directory names to exclude.
        mode (OutputMode): Output mode (separate or aggregate).
        output_path (str): Output file or directory path.
        max_tokens (Optional[int]): Maximum tokens per chunk.
    """

    inputs: list[str] = field(metadata={"description": "Input paths to process"})
    extensions: frozenset[str] = field(metadata={"description": "File extensions to include"})
    exclude: frozenset[str] = field(metadata={"description": "Directory names to exclude"})
    mode: OutputMode = field(metadata={"description": "Output mode (separate or aggregate)"})
    output_path: str = field(metadata={"description": "Output file or directory path"})
    max_tokens: int | None = field(default=None, metadata={"description": "Maximum tokens per chunk"})


@dataclass(order=True, frozen=True)
class ContextResult(BaseEntity):
    """Result of context building operation.

    Attributes:
        output_paths (list[str]): Paths to output files.
        total_files (int): Total number of files processed.
        total_tokens (int): Total token count across all files.
        chunks (int): Number of chunks if split.
    """

    output_paths: list[str] = field(metadata={"description": "Paths to output files"})
    total_files: int = field(metadata={"description": "Total number of files processed"})
    total_tokens: int = field(metadata={"description": "Total token count across all files"})
    chunks: int = field(default=1, metadata={"description": "Number of chunks if split"})

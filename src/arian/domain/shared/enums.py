"""Shared domain enums and value objects for Arian."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FileRole(Enum):
    """Role a file plays in the repository."""

    README = "readme"
    ENTRY_POINT = "entry_point"
    CONFIGURATION = "configuration"
    DOMAIN = "domain"
    SERVICE = "service"
    INFRASTRUCTURE = "infrastructure"
    UTILITY = "utility"
    TEST = "test"
    GENERATED = "generated"
    DOCUMENTATION = "documentation"
    UNKNOWN = "unknown"


class SymbolKind(Enum):
    """Kind of extracted code symbol."""

    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"


class DependencyKind(Enum):
    """Kind of relationship between files."""

    IMPORT = "import"
    CALL = "call"
    INHERIT = "inherit"


class CompressionLevel(Enum):
    """How much content to include for a file."""

    FULL = "full"
    STRUCTURE = "structure"
    SIGNATURES = "signatures"
    SUMMARY = "summary"
    AUTO = "auto"


class ConcurrencyPolicy(Enum):
    """Controls how parallel operations are executed.

    Attributes:
        SEQUENTIAL: One file at a time (debugging).
        CONCURRENT: asyncio.gather (default).
        BOUNDED: asyncio.Semaphore-limited.
    """

    SEQUENTIAL = "sequential"
    CONCURRENT = "concurrent"
    BOUNDED = "bounded"


@dataclass(frozen=True)
class TokenBudget:
    """Token budget constraints for context planning.

    Attributes:
        max_tokens: Maximum total tokens. None = unlimited.
        per_chunk_target: Target tokens per chunk. None = auto.
    """

    max_tokens: int | None = None
    per_chunk_target: int | None = None

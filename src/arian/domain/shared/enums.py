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


@dataclass(frozen=True)
class TokenBudget:
    """Token budget constraints for context planning.

    Attributes:
        max_tokens: Maximum total tokens for the context.
        per_chunk_target: Target tokens per chunk.
        readme_reserve: Tokens reserved for README content.
    """

    max_tokens: int
    per_chunk_target: int = 4000
    readme_reserve: int = 500

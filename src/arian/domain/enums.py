"""Domain enums for Arian."""

from __future__ import annotations

from enum import Enum
from enum import auto


class OutputMode(Enum):
    """Output mode for context building.

    SEPARATE: One output file per input path.
    AGGREGATE: All inputs merged into single output (or split chunks if max_tokens set).
    """

    SEPARATE = auto()
    AGGREGATE = auto()


class FileRole(Enum):
    """What role a file plays in the project."""

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

"""Default ignore patterns for file collection."""

from __future__ import annotations

DEFAULT_EXCLUDES: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        "dist",
        "build",
        ".arian",
        ".tmp",
        ".mypy_cache",
        ".ruff_cache",
        "archived",
    }
)

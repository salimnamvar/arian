"""Output path resolution for Arian."""

from __future__ import annotations

from pathlib import Path


def resolve_output_path(a_output_path: str) -> Path:
    """Resolve output path relative to current working directory.

    If the path is an existing directory, appends 'context.md' to it.

    Args:
        a_output_path: Output path string (relative or absolute).

    Returns:
        Resolved Path object.
    """
    result: Path = Path(a_output_path).expanduser()
    if not result.is_absolute():
        result = Path.cwd() / result

    if result.is_dir():
        result = result / "context.md"

    return result

"""Output path resolution for Arian."""

from __future__ import annotations

from pathlib import Path


def resolve_output_path(a_output_path: str) -> Path:
    """Resolve output path relative to project root.

    Args:
        a_output_path: Output path string (relative or absolute).

    Returns:
        Resolved Path object.
    """
    result: Path = Path(a_output_path)
    if not result.is_absolute():
        result = Path(__file__).resolve().parents[3] / a_output_path
    return result

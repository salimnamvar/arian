"""Language detection for document rendering."""

from __future__ import annotations

from pathlib import Path


def detect_language(a_path: Path) -> str:
    """Detect language from file extension.

    Args:
        a_path: Path to detect language for.

    Returns:
        Detected language identifier or empty string.
    """
    lang_map: dict[str, str] = {
        ".py": "python",
        ".md": "markdown",
        ".txt": "",
        ".rst": "rst",
        ".puml": "puml",
    }
    result: str = lang_map.get(a_path.suffix, "")
    return result

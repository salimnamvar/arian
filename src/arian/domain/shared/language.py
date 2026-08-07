"""Language detection — domain concept.

Detects programming language from file extension, filename, shebang,
and modeline for rendering and analysis purposes.

This module exposes pure functions that take their configuration
explicitly via parameters. Lookup tables, thresholds, and other
tunable values live in :class:`arian.infrastructure.config.LanguageConfig`
— no module-level values are permitted here per the safe-coding
policy (no scattered constants in implementation files).
"""

from __future__ import annotations

from pathlib import Path

from arian.infrastructure.config import LanguageConfig


def lang_extensions(a_config: LanguageConfig) -> frozenset[str]:
    """Return the set of file extensions the config recognises.

    Args:
        a_config: Language configuration.

    Returns:
        Frozenset of every extension key in the config's ``lang_map``.
    """
    return frozenset(a_config.lang_map.keys())


def detect_language(a_path: Path, a_config: LanguageConfig) -> str:
    """Detect language using extension, filename, shebang, and modeline.

    Priority:
        1. Extension lookup in ``a_config.lang_map``
        2. Filename lookup in ``a_config.filename_map``
        3. Shebang detection (first line)
        4. Modeline detection (last 5 lines, ``ft=...``)
        5. Empty string (unknown)

    Args:
        a_path: Path to detect language for.
        a_config: Language configuration.

    Returns:
        Detected language identifier or empty string.
    """
    result: str = ""
    ext: str = a_path.suffix.lower()
    if a_config.lang_map.get(ext):
        result = a_config.lang_map[ext]
    else:
        name: str = a_path.name.lower()
        result = a_config.filename_map[name] if name in a_config.filename_map else _detect_by_content(a_path, a_config)

    return result


def _detect_by_content(a_path: Path, a_config: LanguageConfig) -> str:
    """Detect language by reading file content (shebang and modeline).

    Args:
        a_path: Path to read content from.
        a_config: Language configuration.

    Returns:
        Detected language identifier or empty string.
    """
    result: str = ""
    lang_map: dict[str, str] = a_config.lang_map

    try:
        with a_path.open("r", encoding="utf-8", errors="ignore") as fh:
            first_line: str = fh.readline(256)
            if first_line.startswith("#!"):
                parts: list[str] = first_line.split("/")
                tail: str = parts[-1].strip() if parts else ""
                tokens: list[str] = tail.split()
                interpreter: str = (
                    tokens[1]
                    if len(tokens) >= a_config.min_shebang_tokens_for_env and tokens[0] == "env"
                    else (tokens[0] if tokens else "")
                )
                if interpreter in a_config.shebang_map:
                    result = a_config.shebang_map[interpreter]
    except OSError:
        pass

    if not result:
        try:
            with a_path.open("r", encoding="utf-8", errors="ignore") as fh:
                lines: list[str] = fh.readlines()
                for line in lines[-5:]:
                    if "ft=" in line:
                        ft_value: str = line.split("ft=")[-1].split()[0]
                        if ft_value in lang_map.values():
                            result = ft_value
                            break
        except OSError:
            pass

    return result

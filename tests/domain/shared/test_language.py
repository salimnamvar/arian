"""Tests for language detection — extension, filename, shebang, modeline."""

from __future__ import annotations

from pathlib import Path

from arian.domain.shared.language import LANG_EXTENSIONS
from arian.domain.shared.language import _FILENAME_MAP
from arian.domain.shared.language import _LANG_MAP
from arian.domain.shared.language import detect_language


def test_extension_detection() -> None:
    """Known extensions return correct language."""
    assert detect_language(Path("main.py")) == "python"
    assert detect_language(Path("index.ts")) == "typescript"
    assert detect_language(Path("lib.rs")) == "rust"
    assert detect_language(Path("main.go")) == "go"
    assert detect_language(Path("style.css")) == "css"
    assert detect_language(Path("README.md")) == "markdown"


def test_extension_case_insensitive() -> None:
    """Extension detection is case-insensitive."""
    assert detect_language(Path("Main.PY")) == "python"
    assert detect_language(Path("index.TS")) == "typescript"
    assert detect_language(Path("STYLE.CSS")) == "css"


def test_new_extensions_detected() -> None:
    """Newly added extensions are detected."""
    assert detect_language(Path("template.jinja2")) == "jinja2"
    assert detect_language(Path("template.j2")) == "jinja2"
    assert detect_language(Path("schema.proto")) == "protobuf"
    assert detect_language(Path("schema.graphql")) == "graphql"
    assert detect_language(Path("infra.tf")) == "hcl"
    assert detect_language(Path("data.csv")) == "csv"
    assert detect_language(Path("debug.log")) == "log"
    assert detect_language(Path("change.diff")) == "diff"
    assert detect_language(Path("types.pyi")) == "python"


def test_filename_detection() -> None:
    """Filenames without extensions are detected."""
    assert detect_language(Path("Makefile")) == "make"
    assert detect_language(Path("Dockerfile")) == "dockerfile"
    assert detect_language(Path("CMakeLists.txt")) == "cmake"
    assert detect_language(Path("Justfile")) == "just"


def test_shebang_detection(tmp_path: Path) -> None:
    """Shebang in first line detects language."""
    script = tmp_path / "script"
    script.write_text("#!/usr/bin/env python3\nprint('hello')\n")
    assert detect_language(script) == "python"


def test_shebang_bash(tmp_path: Path) -> None:
    """Bash shebang detected."""
    script = tmp_path / "script.sh"
    script.write_text("#!/bin/bash\necho hello\n")
    assert detect_language(script) == "bash"


def test_modeline_detection(tmp_path: Path) -> None:
    """Vim modeline in last 5 lines detects language."""
    content = "# some code\nx = 1\n# vim: ft=python\n"
    script = tmp_path / "script.txt"
    script.write_text(content)
    assert detect_language(script) == "python"


def test_unknown_extension_returns_empty() -> None:
    """Unknown extension returns empty string."""
    assert detect_language(Path("file.xyz")) == ""
    assert detect_language(Path("file.unknown")) == ""


def test_lang_extensions_matches_lang_map() -> None:
    """LANG_EXTENSIONS is derived from _LANG_MAP keys."""
    assert frozenset(_LANG_MAP.keys()) == LANG_EXTENSIONS


def test_lang_extensions_all_dot_prefixed() -> None:
    """All LANG_EXTENSIONS start with a dot."""
    for ext in LANG_EXTENSIONS:
        assert ext.startswith("."), f"Extension {ext} is not dot-prefixed"


def test_lang_extensions_all_lowercase() -> None:
    """All LANG_EXTENSIONS are lowercase."""
    for ext in LANG_EXTENSIONS:
        assert ext == ext.lower(), f"Extension {ext} is not lowercase"


def test_filename_map_all_lowercase() -> None:
    """All FILENAME_MAP keys are lowercase."""
    for name in _FILENAME_MAP:
        assert name == name.lower(), f"Filename {name} is not lowercase"

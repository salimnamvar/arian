"""Tests for language detection — extension, filename, shebang, modeline."""

from __future__ import annotations

from pathlib import Path

from arian.domain.shared.language import detect_language
from arian.domain.shared.language import lang_extensions
from arian.infrastructure.config import LanguageConfig


def _config() -> LanguageConfig:
    """Default language configuration used by the tests."""
    return LanguageConfig()


def test_extension_detection() -> None:
    """Known extensions return correct language."""
    config = _config()
    assert detect_language(Path("main.py"), config) == "python"
    assert detect_language(Path("index.ts"), config) == "typescript"
    assert detect_language(Path("lib.rs"), config) == "rust"
    assert detect_language(Path("main.go"), config) == "go"
    assert detect_language(Path("style.css"), config) == "css"
    assert detect_language(Path("README.md"), config) == "markdown"


def test_extension_case_insensitive() -> None:
    """Extension detection is case-insensitive."""
    config = _config()
    assert detect_language(Path("Main.PY"), config) == "python"
    assert detect_language(Path("index.TS"), config) == "typescript"
    assert detect_language(Path("STYLE.CSS"), config) == "css"


def test_new_extensions_detected() -> None:
    """Newly added extensions are detected."""
    config = _config()
    assert detect_language(Path("template.jinja2"), config) == "jinja2"
    assert detect_language(Path("template.j2"), config) == "jinja2"
    assert detect_language(Path("schema.proto"), config) == "protobuf"
    assert detect_language(Path("schema.graphql"), config) == "graphql"
    assert detect_language(Path("infra.tf"), config) == "hcl"
    assert detect_language(Path("data.csv"), config) == "csv"
    assert detect_language(Path("debug.log"), config) == "log"
    assert detect_language(Path("change.diff"), config) == "diff"
    assert detect_language(Path("types.pyi"), config) == "python"


def test_filename_detection() -> None:
    """Filenames without extensions are detected."""
    config = _config()
    assert detect_language(Path("Makefile"), config) == "make"
    assert detect_language(Path("Dockerfile"), config) == "dockerfile"
    assert detect_language(Path("CMakeLists.txt"), config) == "cmake"
    assert detect_language(Path("Justfile"), config) == "just"


def test_shebang_detection(tmp_path: Path) -> None:
    """Shebang in first line detects language."""
    config = _config()
    script = tmp_path / "script"
    script.write_text("#!/usr/bin/env python3\nprint('hello')\n")
    assert detect_language(script, config) == "python"


def test_shebang_bash(tmp_path: Path) -> None:
    """Bash shebang detected."""
    config = _config()
    script = tmp_path / "script.sh"
    script.write_text("#!/bin/bash\necho hello\n")
    assert detect_language(script, config) == "bash"


def test_modeline_detection(tmp_path: Path) -> None:
    """Vim modeline in last 5 lines detects language."""
    config = _config()
    content = "# some code\nx = 1\n# vim: ft=python\n"
    script = tmp_path / "script.txt"
    script.write_text(content)
    assert detect_language(script, config) == "python"


def test_unknown_extension_returns_empty() -> None:
    """Unknown extension returns empty string."""
    config = _config()
    assert detect_language(Path("file.xyz"), config) == ""
    assert detect_language(Path("file.unknown"), config) == ""


def test_lang_extensions_matches_lang_map() -> None:
    """lang_extensions is derived from config lang_map keys."""
    config = _config()
    assert frozenset(config.lang_map.keys()) == lang_extensions(config)


def test_lang_extensions_all_dot_prefixed() -> None:
    """All lang_extensions start with a dot."""
    config = _config()
    for ext in lang_extensions(config):
        assert ext.startswith("."), f"Extension {ext} is not dot-prefixed"


def test_lang_extensions_all_lowercase() -> None:
    """All lang_extensions are lowercase."""
    config = _config()
    for ext in lang_extensions(config):
        assert ext == ext.lower(), f"Extension {ext} is not lowercase"


def test_filename_map_all_lowercase() -> None:
    """All filename_map keys are lowercase."""
    config = _config()
    for name in config.filename_map:
        assert name == name.lower(), f"Filename {name} is not lowercase"

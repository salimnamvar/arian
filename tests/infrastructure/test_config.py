"""Unit tests for infrastructure configuration."""

from __future__ import annotations

from arian.domain.enums import OutputMode
from arian.domain.models import InputSpec
from arian.infrastructure.config import ContextBuilderSettings
from arian.infrastructure.config import parse_input_spec


def test_context_builder_settings_defaults() -> None:
    """Test default settings values."""
    settings = ContextBuilderSettings()
    assert settings.output == ".tmp"
    assert settings.mode == OutputMode.SEPARATE
    assert ".py" in settings.extensions
    assert ".git" in settings.exclude
    assert settings.max_tokens is None


def test_context_builder_settings_custom_values() -> None:
    """Test custom settings values."""
    settings = ContextBuilderSettings(
        inputs=["src/", "tests/"],
        output="output.md",
        mode=OutputMode.AGGREGATE,
        exclude=["node_modules"],
        extensions=[".py"],
        max_tokens=5000,
    )
    assert settings.inputs == ["src/", "tests/"]
    assert settings.output == "output.md"
    assert settings.mode == OutputMode.AGGREGATE
    assert settings.exclude == ["node_modules"]
    assert settings.extensions == [".py"]
    assert settings.max_tokens == 5000


def test_context_builder_settings_to_domain() -> None:
    """Test converting settings to domain config."""
    settings = ContextBuilderSettings(
        inputs=["src/"],
        output="output.md",
        mode=OutputMode.AGGREGATE,
        max_tokens=5000,
    )
    config = settings.to_domain()

    assert config.inputs == (InputSpec(path="src/", tag=""),)
    assert config.output_path == "output.md"
    assert config.mode == OutputMode.AGGREGATE
    assert config.max_tokens == 5000
    assert isinstance(config.extensions, frozenset)
    assert isinstance(config.exclude, frozenset)


def test_context_builder_settings_to_domain_tagged() -> None:
    """Test converting tagged input strings to InputSpec."""
    settings = ContextBuilderSettings(
        inputs=["src/:core", "tests/:tests"],
        output="output.md",
        mode=OutputMode.AGGREGATE,
    )
    config = settings.to_domain()

    assert config.inputs == (
        InputSpec(path="src/", tag="core"),
        InputSpec(path="tests/", tag="tests"),
    )


def test_parse_input_spec_plain() -> None:
    """Test parsing plain path without tag."""
    spec = parse_input_spec("src/")
    assert spec == InputSpec(path="src/", tag="")


def test_parse_input_spec_tagged() -> None:
    """Test parsing path:tag syntax."""
    spec = parse_input_spec("src/:core")
    assert spec == InputSpec(path="src/", tag="core")


def test_parse_input_spec_windows_drive_safe() -> None:
    """Test that single-letter drive prefixes are not treated as tags."""
    spec = parse_input_spec("C:foo")
    assert spec.path == "C:foo"
    assert spec.tag == ""

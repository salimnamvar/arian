"""Unit tests for infrastructure configuration."""

from __future__ import annotations

from arian.domain.enums import OutputMode
from arian.infrastructure.config import ContextBuilderSettings


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

    assert config.inputs == ("src/",)
    assert config.output_path == "output.md"
    assert config.mode == OutputMode.AGGREGATE
    assert config.max_tokens == 5000
    assert isinstance(config.extensions, frozenset)
    assert isinstance(config.exclude, frozenset)

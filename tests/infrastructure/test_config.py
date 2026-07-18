"""Unit tests for infrastructure configuration."""

from __future__ import annotations

import pytest

from arian.infrastructure.config import LoggingConfig


def test_logging_config_defaults() -> None:
    """Test default logging config values."""
    config = LoggingConfig()
    assert config.level == "INFO"


def test_logging_config_custom_level() -> None:
    """Test custom logging level."""
    config = LoggingConfig(level="DEBUG")
    assert config.level == "DEBUG"


def test_logging_config_lowercase_level() -> None:
    """Test that lowercase level is normalized to uppercase."""
    config = LoggingConfig(level="warning")
    assert config.level == "WARNING"


def test_logging_config_invalid_level() -> None:
    """Test that invalid level raises ValueError."""
    with pytest.raises(ValueError, match="Invalid logging level"):
        LoggingConfig(level="INVALID")


def test_logging_config_non_string_level() -> None:
    """Test that non-string level raises TypeError."""
    with pytest.raises(TypeError, match="Logging level must be a string"):
        LoggingConfig(level=123)  # type: ignore[arg-type]

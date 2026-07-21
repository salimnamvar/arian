"""Unit tests for infrastructure configuration."""

from __future__ import annotations

import pytest

from arian.infrastructure.config import ArianConfig
from arian.infrastructure.config import FileCollectorConfig
from arian.infrastructure.config import LoggingConfig


# ---------------------------------------------------------------------------
# LoggingConfig
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# FileCollectorConfig
# ---------------------------------------------------------------------------


def test_file_collector_config_defaults() -> None:
    """Test default file collector config values."""
    config = FileCollectorConfig()
    assert ".py" in config.extensions
    assert ".sql" in config.extensions
    assert ".git" in config.exclude


# ---------------------------------------------------------------------------
# ArianConfig.load() — no singleton
# ---------------------------------------------------------------------------


def test_load_returns_fresh_instances() -> None:
    """load() must return distinct instances, not a cached singleton."""
    first = ArianConfig.load()
    second = ArianConfig.load()
    assert first is not second
    assert first == second


def test_load_defaults_match_explicit() -> None:
    """load() defaults match explicit construction."""
    loaded = ArianConfig.load()
    explicit = ArianConfig()
    assert loaded == explicit


# ---------------------------------------------------------------------------
# ArianConfig.load_from_dict()
# ---------------------------------------------------------------------------


def test_load_from_dict_empty() -> None:
    """load_from_dict with empty dict returns defaults."""
    config = ArianConfig.load_from_dict({})
    assert config == ArianConfig()


def test_load_from_dict_logging() -> None:
    """load_from_dict overrides logging level."""
    config = ArianConfig.load_from_dict({"logging": {"level": "DEBUG"}})
    assert config.logging.level == "DEBUG"


def test_load_from_dict_collector() -> None:
    """load_from_dict overrides collector extensions."""
    config = ArianConfig.load_from_dict(
        {"collector": {"extensions": [".py", ".ts"]}},
    )
    assert config.collector.extensions == frozenset({".py", ".ts"})


def test_load_from_dict_frozen() -> None:
    """load_from_dict result is frozen (immutable)."""
    config = ArianConfig.load_from_dict({})
    with pytest.raises(Exception):
        config.logging = LoggingConfig(level="ERROR")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ArianConfig.load_from_env()
# ---------------------------------------------------------------------------


def test_load_from_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_from_env with no env vars returns defaults."""
    monkeypatch.delenv("ARIAN_LOG_LEVEL", raising=False)
    monkeypatch.delenv("ARIAN_LOG_DIR", raising=False)
    monkeypatch.delenv("ARIAN_EXTENSIONS", raising=False)
    monkeypatch.delenv("ARIAN_EXCLUDE", raising=False)
    config = ArianConfig.load_from_env()
    assert config.logging.level == "INFO"


def test_load_from_env_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_from_env reads ARIAN_LOG_LEVEL."""
    monkeypatch.setenv("ARIAN_LOG_LEVEL", "DEBUG")
    monkeypatch.delenv("ARIAN_LOG_DIR", raising=False)
    monkeypatch.delenv("ARIAN_EXTENSIONS", raising=False)
    monkeypatch.delenv("ARIAN_EXCLUDE", raising=False)
    config = ArianConfig.load_from_env()
    assert config.logging.level == "DEBUG"


def test_load_from_env_extensions(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_from_env reads ARIAN_EXTENSIONS."""
    monkeypatch.delenv("ARIAN_LOG_LEVEL", raising=False)
    monkeypatch.delenv("ARIAN_LOG_DIR", raising=False)
    monkeypatch.setenv("ARIAN_EXTENSIONS", ".py, .ts, .js")
    monkeypatch.delenv("ARIAN_EXCLUDE", raising=False)
    config = ArianConfig.load_from_env()
    assert config.collector.extensions == frozenset({".py", ".ts", ".js"})


def test_load_from_env_exclude(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_from_env reads ARIAN_EXCLUDE."""
    monkeypatch.delenv("ARIAN_LOG_LEVEL", raising=False)
    monkeypatch.delenv("ARIAN_LOG_DIR", raising=False)
    monkeypatch.delenv("ARIAN_EXTENSIONS", raising=False)
    monkeypatch.setenv("ARIAN_EXCLUDE", "vendor, tmp")
    config = ArianConfig.load_from_env()
    assert "vendor" in config.collector.exclude
    assert "tmp" in config.collector.exclude


def test_load_from_env_frozen() -> None:
    """load_from_env result is frozen (immutable)."""
    config = ArianConfig.load_from_env()
    with pytest.raises(Exception):
        config.logging = LoggingConfig(level="ERROR")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ArianConfig.load_with_precedence()
# ---------------------------------------------------------------------------


def test_load_with_precedence_no_env() -> None:
    """load_with_precedence with empty env returns defaults."""
    config = ArianConfig.load_with_precedence(a_env={})
    assert config == ArianConfig()


def test_load_with_precedence_log_level() -> None:
    """load_with_precedence overrides log level from env dict."""
    config = ArianConfig.load_with_precedence(a_env={"ARIAN_LOG_LEVEL": "DEBUG"})
    assert config.logging.level == "DEBUG"


def test_load_with_precedence_log_level_case() -> None:
    """load_with_precedence normalizes log level case from env dict."""
    config = ArianConfig.load_with_precedence(a_env={"ARIAN_LOG_LEVEL": "warning"})
    assert config.logging.level == "WARNING"


def test_load_with_precedence_log_dir() -> None:
    """load_with_precedence overrides log dir from env dict."""
    config = ArianConfig.load_with_precedence(a_env={"ARIAN_LOG_DIR": "/tmp/arian-test"})
    assert config.logging.level == "INFO"
    assert config.logging.log_dir is not None


def test_load_with_precedence_ignores_unrelated_env() -> None:
    """load_with_precedence ignores env vars it does not recognize."""
    config = ArianConfig.load_with_precedence(a_env={"UNRELATED_VAR": "value"})
    assert config == ArianConfig()


def test_load_with_precedence_frozen() -> None:
    """load_with_precedence result is frozen (immutable)."""
    config = ArianConfig.load_with_precedence(a_env={})
    with pytest.raises(Exception):
        config.logging = LoggingConfig(level="ERROR")  # type: ignore[misc]

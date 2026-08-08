"""Unit tests for bootstrap validator."""

from __future__ import annotations

from pathlib import Path

import pytest

from arian.bootstrap.validator import StartupValidator
from arian.infrastructure.config import ArianConfig
from arian.infrastructure.config import LoggingConfig


class TestStartupValidator:
    """Tests for StartupValidator.validate()."""

    def test_valid_config_passes(self, tmp_path: Path) -> None:
        config = ArianConfig()
        validator = StartupValidator()
        result = validator.validate(config, a_root=tmp_path)
        assert result.is_success

    def test_invalid_log_level_fails(self, tmp_path: Path) -> None:
        bad_logging = LoggingConfig.model_construct(level="BOGUS")
        config = ArianConfig.model_construct(logging=bad_logging)
        validator = StartupValidator()
        result = validator.validate(config, a_root=tmp_path)
        assert result.is_failure
        assert "Invalid log level" in result.message

    def test_nonexistent_root_fails(self) -> None:
        config = ArianConfig()
        validator = StartupValidator()
        result = validator.validate(config, a_root=Path("/nonexistent/path/abc123"))
        assert result.is_failure
        assert "Root path does not exist" in result.message

    def test_valid_debug_level(self, tmp_path: Path) -> None:
        config = ArianConfig.load_from_dict({"logging": {"level": "DEBUG"}})
        validator = StartupValidator()
        result = validator.validate(config, a_root=tmp_path)
        assert result.is_success

    def test_valid_critical_level(self, tmp_path: Path) -> None:
        config = ArianConfig.load_from_dict({"logging": {"level": "CRITICAL"}})
        validator = StartupValidator()
        result = validator.validate(config, a_root=tmp_path)
        assert result.is_success

    def test_default_root_uses_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        config = ArianConfig()
        validator = StartupValidator()
        result = validator.validate(config)
        assert result.is_success

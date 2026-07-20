"""Unit tests for bootstrap validator."""

from __future__ import annotations

from pathlib import Path

import pytest

from arian.bootstrap.validator import StartupValidator
from arian.domain.exceptions import ConfigurationError
from arian.infrastructure.config import ArianConfig
from arian.infrastructure.config import LoggingConfig


class TestStartupValidator:
    """Tests for StartupValidator.validate()."""

    def test_valid_config_passes(self, tmp_path: Path) -> None:
        config = ArianConfig()
        validator = StartupValidator()
        validator.validate(config, a_root=tmp_path)

    def test_invalid_log_level_raises(self, tmp_path: Path) -> None:
        bad_logging = LoggingConfig.model_construct(level="BOGUS")
        config = ArianConfig.model_construct(logging=bad_logging)
        validator = StartupValidator()
        with pytest.raises(ConfigurationError, match="Invalid log level"):
            validator.validate(config, a_root=tmp_path)

    def test_nonexistent_root_raises(self) -> None:
        config = ArianConfig()
        validator = StartupValidator()
        with pytest.raises(ConfigurationError, match="Root path does not exist"):
            validator.validate(config, a_root=Path("/nonexistent/path/abc123"))

    def test_valid_debug_level(self, tmp_path: Path) -> None:
        config = ArianConfig.load_from_dict({"logging": {"level": "DEBUG"}})
        validator = StartupValidator()
        validator.validate(config, a_root=tmp_path)

    def test_valid_critical_level(self, tmp_path: Path) -> None:
        config = ArianConfig.load_from_dict({"logging": {"level": "CRITICAL"}})
        validator = StartupValidator()
        validator.validate(config, a_root=tmp_path)

    def test_default_root_uses_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        config = ArianConfig()
        validator = StartupValidator()
        validator.validate(config)

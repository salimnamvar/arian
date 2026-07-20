"""Startup validation — checks required resources exist."""

from __future__ import annotations

import logging
from pathlib import Path

from arian.domain.exceptions import ConfigurationError
from arian.infrastructure.config import ArianConfig

_VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class StartupValidator:
    """Validates application configuration and resources at startup."""

    def validate(self, a_config: ArianConfig, a_root: Path | None = None) -> None:
        """Validate config and required resources.

        Args:
            a_config: Application configuration.
            a_root: Repository root path. Uses cwd if None.

        Raises:
            ConfigurationError: If config is invalid.
        """
        root: Path = a_root or Path.cwd()
        if not root.exists():
            msg = f"Root path does not exist: {root}"
            raise ConfigurationError(msg)
        if a_config.logging.level not in _VALID_LOG_LEVELS:
            msg = f"Invalid log level: {a_config.logging.level}"
            raise ConfigurationError(msg)

        logger = logging.getLogger(__name__)
        logger.debug("Startup validation passed for root=%s", root)

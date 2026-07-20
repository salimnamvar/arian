"""Infrastructure configuration for Arian.

Pydantic-settings based configuration loaded from CLI args or environment.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

_DEFAULT_EXTENSIONS: frozenset[str] = frozenset(
    {".py", ".md", ".txt", ".rst", ".toml", ".yaml", ".yml", ".json"},
)


class LoggingConfig(BaseModel):
    """Logging configuration — level, transport, and file output.

    Attributes:
        level: Application logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        async_logging: Enable async logging via QueueHandler → QueueListener.
        log_dir: Directory for log files. None disables file logging.
        max_bytes: Maximum log file size in bytes before rotation.
        backup_count: Number of rotated log files to keep.
    """

    model_config = ConfigDict(frozen=True)

    level: str = Field(default="INFO", description="Application logging level.")
    async_logging: bool = Field(default=False, description="Enable async logging via queue.")
    log_dir: Path | None = Field(
        default=Path("~/.arian/logs"),
        description="Directory for log files. None disables file logging.",
    )
    max_bytes: int = Field(default=10 * 1024 * 1024, description="Max log file size before rotation (bytes).")
    backup_count: int = Field(default=5, description="Number of rotated log files to keep.")

    @field_validator("level", mode="before")
    @classmethod
    def _validate_level(cls, a_value: Any) -> str:
        """Normalize and validate logging level against stdlib names.

        Args:
            a_value: Raw level value from CLI or environment.

        Returns:
            Uppercase validated level string.

        Raises:
            TypeError: If level is not a string.
            ValueError: If level is not a valid stdlib logging level name.
        """
        if not isinstance(a_value, str):
            msg = "Logging level must be a string"
            raise TypeError(msg)
        level: str = a_value.upper()
        if level not in logging.getLevelNamesMapping():
            msg = f"Invalid logging level: {a_value}"
            raise ValueError(msg)
        return level


class FileCollectorConfig(BaseModel):
    """File collector configuration — extensions and exclusions.

    Attributes:
        extensions: File extensions to include.
        exclude: Directory names to exclude from scanning.
    """

    model_config = ConfigDict(frozen=True)

    extensions: frozenset[str] = Field(
        default=_DEFAULT_EXTENSIONS,
        description="File extensions to include.",
    )
    exclude: frozenset[str] = Field(
        default=frozenset(
            {
                ".git",
                ".venv",
                "__pycache__",
                ".pytest_cache",
                "node_modules",
                "dist",
                "build",
                ".arian",
                ".tmp",
                ".mypy_cache",
                ".ruff_cache",
                "archived",
            }
        ),
        description="Directory names to exclude.",
    )


class ArianConfig(BaseModel):
    """Root configuration for Arian — hierarchical, frozen, injectable.

    Attributes:
        logging: Logging configuration.
        collector: File collector configuration.
    """

    model_config = ConfigDict(frozen=True)

    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    collector: FileCollectorConfig = Field(default_factory=FileCollectorConfig)

    @staticmethod
    def load() -> ArianConfig:
        """Create a fresh ArianConfig with default values.

        Returns:
            New ArianConfig instance.
        """
        return ArianConfig()

    @classmethod
    def load_from_env(cls) -> ArianConfig:
        """Create ArianConfig from environment variables.

        Environment variables:
            ARIAN_LOG_LEVEL: Logging level (default: INFO).
            ARIAN_LOG_DIR: Log directory path (default: ~/.arian/logs).
            ARIAN_EXTENSIONS: Comma-separated file extensions (default: standard set).
            ARIAN_EXCLUDE: Comma-separated directory names to exclude.

        Returns:
            ArianConfig populated from environment variables.
        """
        log_level: str = os.environ.get("ARIAN_LOG_LEVEL", "INFO")
        log_dir_raw: str | None = os.environ.get("ARIAN_LOG_DIR")
        log_dir: Path | None = Path(log_dir_raw) if log_dir_raw else Path("~/.arian/logs")

        logging_cfg = LoggingConfig(level=log_level, log_dir=log_dir)

        collector_kwargs: dict[str, Any] = {}
        extensions_raw: str | None = os.environ.get("ARIAN_EXTENSIONS")
        if extensions_raw:
            collector_kwargs["extensions"] = frozenset(ext.strip() for ext in extensions_raw.split(",") if ext.strip())

        exclude_raw: str | None = os.environ.get("ARIAN_EXCLUDE")
        if exclude_raw:
            collector_kwargs["exclude"] = frozenset(name.strip() for name in exclude_raw.split(",") if name.strip())

        collector_cfg = FileCollectorConfig(**collector_kwargs)
        return cls(logging=logging_cfg, collector=collector_cfg)

    @classmethod
    def load_from_dict(cls, a_data: dict[str, Any]) -> ArianConfig:
        """Create ArianConfig from a dictionary — useful for testing.

        Args:
            a_data: Dictionary with optional 'logging' and 'collector' keys.

        Returns:
            ArianConfig populated from the provided dictionary.
        """
        return cls.model_validate(a_data)

    @classmethod
    def load_with_precedence(cls, a_env: dict[str, str] | None = None) -> ArianConfig:
        """Load config with precedence: defaults < env < CLI.

        Precedence order:
            1. Built-in defaults (class fields)
            2. Environment variables (ARIAN_LOG_LEVEL, etc.)
            3. CLI args (future — not yet implemented)

        Args:
            a_env: Optional environment dict (for testing). Uses os.environ if None.

        Returns:
            ArianConfig with values resolved by precedence.
        """
        cfg = cls.load()
        env = a_env if a_env is not None else dict(os.environ)
        if "ARIAN_LOG_LEVEL" in env:
            level: str = env["ARIAN_LOG_LEVEL"].upper()
            cfg = cfg.model_copy(
                update={"logging": cfg.logging.model_copy(update={"level": level})}
            )
        if "ARIAN_LOG_DIR" in env:
            raw: str = env["ARIAN_LOG_DIR"]
            log_dir: Path | None = Path(raw) if raw else None
            cfg = cfg.model_copy(
                update={"logging": cfg.logging.model_copy(update={"log_dir": log_dir})}
            )
        return cfg

"""Infrastructure configuration for Arian.

Pydantic-settings based configuration loaded from CLI args or environment.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator


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

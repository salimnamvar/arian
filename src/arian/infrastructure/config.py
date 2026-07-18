"""Infrastructure configuration for Arian.

Pydantic-settings based configuration loaded from CLI args or environment.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from arian.domain.enums import OutputMode
from arian.domain.models import ContextConfig


class LoggingConfig(BaseModel):
    """Logging configuration — level only, validated and normalized.

    Attributes:
        level: Application logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """

    model_config = ConfigDict(frozen=True)

    level: str = Field(default="INFO", description="Application logging level.")

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


DEFAULT_EXCLUDE: list[str] = [
    "archived",
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
]


class ContextBuilderSettings(BaseSettings):
    """Settings for context builder via CLI or environment.

    Attributes:
        inputs (List[str]): Input paths to process.
        output (str): Output path or directory.
        mode (OutputMode): Output mode (separate or aggregate).
        exclude (List[str]): Directory names to exclude.
        extensions (List[str]): File extensions to include.
        max_tokens (Optional[int]): Maximum tokens per chunk.
    """

    model_config = SettingsConfigDict(env_prefix="CB_")

    inputs: list[str] = Field(default_factory=list)
    output: str = Field(default=".tmp")
    mode: OutputMode = Field(default=OutputMode.SEPARATE)
    exclude: list[str] = Field(default_factory=lambda: list(DEFAULT_EXCLUDE))
    extensions: list[str] = Field(default=[".py", ".md", ".txt", ".rst", ".puml"])
    max_tokens: int | None = Field(default=None)

    def to_domain(self) -> ContextConfig:
        """Convert to domain configuration.

        Returns:
            ContextConfig: Immutable domain config.
        """
        result: ContextConfig = ContextConfig(
            inputs=tuple(self.inputs),
            extensions=frozenset(self.extensions),
            exclude=frozenset(self.exclude),
            mode=self.mode,
            output_path=self.output,
            max_tokens=self.max_tokens,
        )
        return result

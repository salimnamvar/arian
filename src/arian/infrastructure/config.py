"""Infrastructure configuration for Arian.

Pydantic-settings based configuration loaded from CLI args or environment.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from arian.domain.enums import OutputMode
from arian.domain.models import ContextConfig


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
    exclude: list[str] = Field(
        default=["archived", "__pycache__", ".git", ".mypy_cache", ".pytest_cache", "node_modules"]
    )
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

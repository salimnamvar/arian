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
from arian.domain.models import InputSpec
from arian.domain.models import PatternRule


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


def parse_input_spec(a_raw: str) -> InputSpec:
    """Parse a raw input string into an InputSpec.

    Supports ``path:tag`` syntax (e.g. ``src/:core``). Plain paths yield an
    empty tag.

    Args:
        a_raw: Raw CLI or config input string.

    Returns:
        Parsed InputSpec with path and optional tag.
    """
    result: InputSpec
    if ":" in a_raw:
        path_part: str
        tag_part: str
        path_part, tag_part = a_raw.rsplit(":", 1)
        if path_part and not (len(path_part) == 1 and path_part.isalpha()):
            result = InputSpec(path=path_part, tag=tag_part)
        else:
            result = InputSpec(path=a_raw, tag="")
    else:
        result = InputSpec(path=a_raw, tag="")
    return result


class ContextBuilderSettings(BaseSettings):
    """Settings for context builder via CLI or environment.

    Attributes:
        inputs (List[str]): Input paths to process (optionally path:tag).
        output (str): Output path or directory.
        mode (OutputMode): Output mode (separate or aggregate).
        exclude (List[str]): Directory names to exclude.
        extensions (List[str]): File extensions to include.
        max_tokens (Optional[int]): Maximum tokens per chunk.
        compression (str): Compression strategy.
        include_comments (Optional[bool]): Override comment inclusion.
        include_docstrings (Optional[bool]): Override docstring inclusion.
        include_imports (Optional[bool]): Override import inclusion.
        include_line_numbers (bool): Whether to add line numbers.
        include_directory_structure (bool): Whether to include directory tree.
        include_file_summary (bool): Whether to include file summary.
        include_token_counts (bool): Whether to report token counts.
        custom_instructions (Optional[str]): Custom LLM instructions.
        sort_by_importance (bool): Whether to order files by importance.
        preserve_readme_in_chunks (bool): Whether to include README in every chunk.
    """

    model_config = SettingsConfigDict(env_prefix="CB_")

    inputs: list[str] = Field(default_factory=list)
    output: str = Field(default=".tmp")
    mode: OutputMode = Field(default=OutputMode.SEPARATE)
    exclude: list[str] = Field(default_factory=lambda: list(DEFAULT_EXCLUDE))
    extensions: list[str] = Field(default=[".py", ".md", ".txt", ".rst", ".puml"])
    max_tokens: int | None = Field(default=None)
    compression: str = Field(default="auto")
    include_comments: bool | None = Field(default=None)
    include_docstrings: bool | None = Field(default=None)
    include_imports: bool | None = Field(default=None)
    include_line_numbers: bool = Field(default=False)
    include_directory_structure: bool = Field(default=True)
    include_file_summary: bool = Field(default=True)
    include_token_counts: bool = Field(default=True)
    custom_instructions: str | None = Field(default=None)
    sort_by_importance: bool = Field(default=True)
    preserve_readme_in_chunks: bool = Field(default=True)
    pattern_rules: list[PatternRule] = Field(default=[])

    def to_domain(self) -> ContextConfig:
        """Convert to domain configuration.

        Parses tagged input strings (``path:tag``) into InputSpec values.

        Returns:
            ContextConfig: Immutable domain config.
        """
        parsed_inputs: tuple[InputSpec, ...] = tuple(parse_input_spec(raw) for raw in self.inputs)
        result: ContextConfig = ContextConfig(
            inputs=parsed_inputs,
            extensions=frozenset(self.extensions),
            exclude=frozenset(self.exclude),
            mode=self.mode,
            output_path=self.output,
            max_tokens=self.max_tokens,
            compression=self.compression,
            include_comments=self.include_comments,
            include_docstrings=self.include_docstrings,
            include_imports=self.include_imports,
            include_line_numbers=self.include_line_numbers,
            include_directory_structure=self.include_directory_structure,
            include_file_summary=self.include_file_summary,
            include_token_counts=self.include_token_counts,
            custom_instructions=self.custom_instructions,
            sort_by_importance=self.sort_by_importance,
            preserve_readme_in_chunks=self.preserve_readme_in_chunks,
            pattern_rules=tuple(self.pattern_rules),
        )
        return result

"""Markdown renderer using Jinja2 templates."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape

from arian.domain.context.models import ContextPlan
from arian.domain.context.models import MaterializedChunk

logger = logging.getLogger(__name__)

_TEMPLATE_DIR: Path = Path(__file__).parent.parent.parent / "templates"


class MarkdownRenderer:
    """Renders materialized chunks as Markdown output.

    Uses Jinja2 templates for flexible output formatting.
    Receives only MaterializedChunks — never raw repository state.

    Attributes:
        _environment: Jinja2 template environment.
        _template: Loaded Jinja2 template.
    """

    def __init__(self) -> None:
        """Initialize renderer with template environment."""
        self._environment: Environment = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=select_autoescape(),
        )
        self._template = self._environment.get_template("document.md.jinja2")

    def render(
        self,
        a_chunks: tuple[MaterializedChunk, ...],
        a_plan: ContextPlan,
    ) -> str:
        """Render materialized chunks to Markdown.

        Args:
            a_chunks: Materialized chunks with compressed content.
            a_plan: Original context plan for metadata.

        Returns:
            Rendered Markdown string.
        """
        chunks_data: list[dict[str, object]] = []
        total_files: int = 0

        for chunk in a_chunks:
            files_data: list[dict[str, object]] = []
            for mat_file in chunk.files:
                lang: str = ""
                if mat_file.path.endswith(".py"):
                    lang = "python"
                elif mat_file.path.endswith(".md"):
                    lang = "markdown"

                files_data.append(
                    {
                        "path": mat_file.path,
                        "representation": mat_file.compression.value,
                        "content": mat_file.content,
                        "language": lang,
                    }
                )
                total_files += 1

            chunks_data.append(
                {
                    "header": chunk.header,
                    "files": files_data,
                }
            )

        directory_structure: str = self._build_directory_structure(a_chunks)
        file_summary: str = self._build_file_summary(a_plan, total_files)

        result: str = self._template.render(
            directory_structure=directory_structure,
            file_summary=file_summary,
            custom_instructions="",
            chunks=chunks_data,
            total_files=total_files,
            total_tokens=a_plan.total_tokens,
        )
        logger.debug("Rendered materialized chunks to markdown (%d tokens)", a_plan.total_tokens)
        return result

    def _build_directory_structure(
        self,
        a_chunks: tuple[MaterializedChunk, ...],
    ) -> str:
        """Build a directory tree string from materialized chunks.

        Args:
            a_chunks: Materialized chunks.

        Returns:
            Multi-line directory tree string.
        """
        paths: list[str] = []
        for chunk in a_chunks:
            for mat_file in chunk.files:
                paths.append(mat_file.path)

        lines: list[str] = []
        for path in sorted(set(paths)):
            depth: int = len(Path(path).parts) - 1
            indent: str = "  " * max(depth, 0)
            name: str = Path(path).name
            lines.append(f"{indent}{name}")

        result: str = "\n".join(lines)
        return result

    def _build_file_summary(self, a_plan: ContextPlan, a_total_files: int) -> str:
        """Build a file summary with token counts.

        Args:
            a_plan: Context plan for metadata.
            a_total_files: Total file count.

        Returns:
            Multi-line summary string.
        """
        lines: list[str] = [
            f"Files: {a_total_files}",
            f"Tokens: {a_plan.total_tokens}",
            f"Chunks: {len(a_plan.chunks)}",
            f"Task: {a_plan.task.value}",
        ]
        if a_plan.query:
            lines.append(f"Query: {a_plan.query}")

        result: str = "\n".join(lines)
        return result

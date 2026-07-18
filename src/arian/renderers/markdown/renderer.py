"""Markdown renderer using Jinja2 templates."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape

from arian.domain.context.models import ContextPlan
from arian.domain.repository.models import FileContent

logger = logging.getLogger(__name__)

_TEMPLATE_DIR: Path = Path(__file__).parent.parent.parent / "templates"


class MarkdownRenderer:
    """Renders context plans as Markdown output.

    Uses Jinja2 templates for flexible output formatting.

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
        a_plan: ContextPlan,
        a_files: dict[str, FileContent],
        a_root: Path | None = None,
    ) -> str:
        """Render a context plan to Markdown.

        Args:
            a_plan: Context plan with chunks and metadata.
            a_files: Mapping of file path to FileContent.
            a_root: Optional root path for relative path display.

        Returns:
            Rendered Markdown string.
        """
        chunks_data: list[dict[str, object]] = []
        total_files: int = 0

        for chunk in a_plan.chunks:
            files_data: list[dict[str, object]] = []
            for planned_file in chunk.files:
                content_obj: FileContent | None = a_files.get(planned_file.path)
                content_str: str = content_obj.content if content_obj is not None else ""
                lang: str = ""
                if content_obj is not None and planned_file.path.endswith(".py"):
                    lang = "python"
                elif content_obj is not None and planned_file.path.endswith(".md"):
                    lang = "markdown"

                display_path: str = planned_file.path
                if a_root is not None:
                    try:
                        display_path = str(Path(planned_file.path).relative_to(a_root))
                    except ValueError:
                        display_path = planned_file.path

                files_data.append(
                    {
                        "path": display_path,
                        "representation": planned_file.representation,
                        "content": content_str,
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

        directory_structure: str = self._build_directory_structure(a_plan, a_root)
        file_summary: str = self._build_file_summary(a_plan)

        result: str = self._template.render(
            directory_structure=directory_structure,
            file_summary=file_summary,
            custom_instructions="",
            chunks=chunks_data,
            total_files=total_files,
            total_tokens=a_plan.total_tokens,
        )
        logger.debug("Rendered context plan to markdown (%d tokens)", a_plan.total_tokens)
        return result

    def _build_directory_structure(
        self,
        a_plan: ContextPlan,
        a_root: Path | None,
    ) -> str:
        """Build a directory tree string from the plan.

        Args:
            a_plan: Context plan.
            a_root: Optional root path.

        Returns:
            Multi-line directory tree string.
        """
        paths: list[str] = []
        for chunk in a_plan.chunks:
            for planned_file in chunk.files:
                paths.append(planned_file.path)

        lines: list[str] = []
        for path in sorted(set(paths)):
            display: str = path
            if a_root is not None:
                try:
                    display = str(Path(path).relative_to(a_root))
                except ValueError:
                    display = path

            depth: int = len(Path(display).parts) - 1
            indent: str = "  " * max(depth, 0)
            name: str = Path(display).name
            lines.append(f"{indent}{name}")

        result: str = "\n".join(lines)
        return result

    def _build_file_summary(self, a_plan: ContextPlan) -> str:
        """Build a file summary with token counts.

        Args:
            a_plan: Context plan.

        Returns:
            Multi-line summary string.
        """
        lines: list[str] = [
            f"Files: {a_plan.total_files}",
            f"Tokens: {a_plan.total_tokens}",
            f"Chunks: {len(a_plan.chunks)}",
            f"Task: {a_plan.task.value}",
        ]
        if a_plan.query:
            lines.append(f"Query: {a_plan.query}")

        result: str = "\n".join(lines)
        return result

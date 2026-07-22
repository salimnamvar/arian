"""Markdown renderer using Jinja2 templates."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape

from arian.domain.context.models import ContextPlan
from arian.domain.context.models import MaterializedChunk
from arian.infrastructure.output.protocols import RendererProtocol

logger = logging.getLogger(__name__)

_TEMPLATE_DIR: Path = Path(__file__).parent.parent.parent.parent / "template"


class MarkdownRenderer(RendererProtocol):
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
            for entry in chunk.entries:
                lang: str = entry.language or ""

                file_data: dict[str, object] = {
                    "path": entry.path,
                    "representation": entry.compression.value,
                    "content": entry.content,
                    "language": lang,
                    "is_fragment": entry.is_fragment,
                    "fragment_label": "",
                    "continuation_hint": "",
                }

                if entry.is_fragment and entry.fragment_index is not None and entry.fragment_total is not None:
                    file_data["fragment_label"] = f"Fragment {entry.fragment_index + 1}/{entry.fragment_total}"

                if entry.continues_in_chunk is not None:
                    file_data["continuation_hint"] = f"Continues in Chunk {entry.continues_in_chunk}"

                files_data.append(file_data)
                total_files += 1

            chunks_data.append(
                {
                    "header": chunk.header,
                    "files": files_data,
                }
            )

        directory_structure: str = self._build_directory_structure(a_plan.repository_files)
        manifest: str = self._build_manifest(a_plan, total_files)

        result: str = self._template.render(
            manifest=manifest,
            directory_structure=directory_structure,
            chunks=chunks_data,
            total_files=total_files,
            total_tokens=a_plan.total_tokens,
        )
        logger.debug("Rendered materialized chunks to markdown (%d tokens)", a_plan.total_tokens)
        return result

    def _build_directory_structure(
        self,
        a_repository_files: tuple[str, ...],
    ) -> str:
        """Build a directory tree string from all repository files.

        Renders proper hierarchy with directory nodes and Unicode box-drawing
        characters for visual clarity. Uses the full file list, not just
        materialized files, so the tree shows the complete repository structure.

        Args:
            a_repository_files: All collected file paths from the repository.

        Returns:
            Multi-line directory tree string.
        """
        paths: set[str] = set(a_repository_files)

        dirs: set[str] = set()
        for path in paths:
            parent = Path(path).parent
            while parent != Path():
                dirs.add(str(parent))
                parent = parent.parent

        all_entries: set[str] = paths | dirs
        lines: list[str] = []

        for entry_path in sorted(all_entries):
            depth = len(Path(entry_path).parts)
            indent = "│   " * (depth - 1) + "├── "
            name = Path(entry_path).name
            if entry_path in dirs:
                name += "/"
            lines.append(f"{indent}{name}")

        result: str = "\n".join(lines)
        return result

    def _build_manifest(self, a_plan: ContextPlan, a_total_files: int) -> str:
        """Build a YAML manifest for the context.

        Args:
            a_plan: Context plan for metadata.
            a_total_files: Total file count in plan (after budget enforcement).

        Returns:
            YAML manifest string.
        """
        meta: dict[str, str | int | dict[str, str | int | None] | list[str]] = (
            a_plan.metadata if a_plan.metadata is not None else {}
        )
        collected_count: int = len(a_plan.repository_files)
        lines: list[str] = [
            "# Arian Context Manifest",
        ]
        if "repository" in meta:
            lines.append("repository: " + str(meta["repository"]))
        if "paths" in meta:
            raw_paths = meta["paths"]
            if isinstance(raw_paths, list):
                lines.append("paths:")
                for p in raw_paths:
                    lines.append("  - " + str(p))
        lines.append("task: " + a_plan.task.value)
        if a_plan.query:
            lines.append("query: " + a_plan.query)
        if "budget" in meta:
            raw_budget = meta["budget"]
            if isinstance(raw_budget, dict):
                lines.append("budget:")
                for key in raw_budget:
                    lines.append(f"  {key}: {raw_budget[key]}")
        lines.append("collected: " + str(collected_count))
        lines.append("files: " + str(a_total_files))
        lines.append("chunks: " + str(len(a_plan.chunks)))
        lines.append("tokens: " + str(a_plan.total_tokens))
        if "scope" in meta:
            lines.append("scope: " + str(meta["scope"]))

        result: str = "\n".join(lines)
        return result

"""Markdown renderer using Jinja2 templates."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Template

from arian.domain.models import Document

logger = logging.getLogger(__name__)

MARKDOWN_TEMPLATE = Template(
    """\
{% if directory_structure %}
# Repository Structure

```
{{ directory_structure }}
```

{% endif %}
{% if file_summary %}
# File Summary

{{ file_summary }}

{% endif %}
{% if custom_instructions %}
# Instructions

{{ custom_instructions }}

{% endif %}
{% for doc in documents %}
--- SOURCE: {{ doc.path }}{% if include_token_counts %} ({{ doc.tokens }} tokens){% endif %} ---

{% if doc.language %}
```{{ doc.language }}
{{ doc.content }}
```
{% else %}
{{ doc.content }}
{% endif %}

{% endfor %}"""
)


class MarkdownRenderer:
    """Render documents as markdown with optional context headers.

    Attributes:
        _include_directory_structure: Whether to include directory tree.
        _include_file_summary: Whether to include file summary.
        _include_token_counts: Whether to show per-file token counts.
        _include_line_numbers: Whether to prefix content lines with numbers.
        _custom_instructions: Optional custom instructions block.
    """

    def __init__(
        self,
        a_include_directory_structure: bool = True,
        a_include_file_summary: bool = True,
        a_include_token_counts: bool = True,
        a_include_line_numbers: bool = False,
        a_custom_instructions: str | None = None,
    ) -> None:
        """Initialize renderer options.

        Args:
            a_include_directory_structure: Include directory tree header.
            a_include_file_summary: Include file summary header.
            a_include_token_counts: Include token counts in headers.
            a_include_line_numbers: Prefix content lines with numbers.
            a_custom_instructions: Custom instructions for the LLM.
        """
        self._include_directory_structure = a_include_directory_structure
        self._include_file_summary = a_include_file_summary
        self._include_token_counts = a_include_token_counts
        self._include_line_numbers = a_include_line_numbers
        self._custom_instructions = a_custom_instructions

    def render(self, a_documents: list[Document]) -> str:
        """Render documents to markdown.

        Args:
            a_documents: Documents to render.

        Returns:
            Rendered markdown content.
        """
        docs: list[Document] = a_documents
        if self._include_line_numbers:
            docs = [self._with_line_numbers(doc) for doc in a_documents]

        directory_structure: str = ""
        if self._include_directory_structure and a_documents:
            directory_structure = self._build_directory_structure(a_documents)

        file_summary: str = ""
        if self._include_file_summary and a_documents:
            file_summary = self._build_file_summary(a_documents)

        result: str = MARKDOWN_TEMPLATE.render(
            documents=docs,
            directory_structure=directory_structure,
            file_summary=file_summary,
            custom_instructions=self._custom_instructions or "",
            include_token_counts=self._include_token_counts,
        )
        logger.debug("Rendered %d documents to markdown", len(a_documents))
        return result

    def _with_line_numbers(self, a_document: Document) -> Document:
        """Return a document copy with line numbers prefixed to content.

        Args:
            a_document: Source document.

        Returns:
            Document with numbered content lines.
        """
        lines: list[str] = a_document.content.splitlines()
        numbered: list[str] = [f"{i:>4}| {line}" for i, line in enumerate(lines, start=1)]
        content: str = "\n".join(numbered)
        if a_document.content.endswith("\n"):
            content += "\n"
        result: Document = Document(
            path=a_document.path,
            content=content,
            tokens=a_document.tokens,
            language=a_document.language,
            tag=a_document.tag,
        )
        return result

    def _build_directory_structure(self, a_documents: list[Document]) -> str:
        """Build a simple directory tree from document paths.

        Args:
            a_documents: Documents to include in the tree.

        Returns:
            Multi-line directory tree string.
        """
        paths: list[Path] = sorted(Path(doc.path) for doc in a_documents)
        lines: list[str] = []
        for path in paths:
            token_map: dict[str, int] = {doc.path: doc.tokens for doc in a_documents}
            tokens: int = token_map.get(str(path), 0)
            depth: int = len(path.parts) - 1
            indent: str = "  " * max(depth, 0)
            if self._include_token_counts:
                lines.append(f"{indent}{path.name}  ({tokens} tokens)")
            else:
                lines.append(f"{indent}{path.name}")
        result: str = "\n".join(lines)
        return result

    def _build_file_summary(self, a_documents: list[Document]) -> str:
        """Build a file summary with token counts.

        Args:
            a_documents: Documents to summarize.

        Returns:
            Multi-line summary string.
        """
        total_tokens: int = sum(doc.tokens for doc in a_documents)
        lines: list[str] = [
            f"Files processed: {len(a_documents)}",
            f"Total tokens: {total_tokens}",
            "",
        ]
        for doc in a_documents:
            if self._include_token_counts:
                lines.append(f"- {doc.path} ({doc.tokens} tokens)")
            else:
                lines.append(f"- {doc.path}")
        result: str = "\n".join(lines)
        return result

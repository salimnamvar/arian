"""Markdown renderer using Jinja2 templates."""

from __future__ import annotations

from jinja2 import Template

from arian.domain.models import Document

MARKDOWN_TEMPLATE = Template(
    """\
{% for doc in documents %}
--- SOURCE: {{ doc.path }} ---

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
    """Render documents as markdown."""

    def render(self, a_documents: list[Document]) -> str:
        """Render documents to markdown.

        Args:
            a_documents: Documents to render.

        Returns:
            Rendered markdown content.
        """
        result: str = MARKDOWN_TEMPLATE.render(documents=a_documents)
        return result

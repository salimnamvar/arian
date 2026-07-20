"""Output layer for Arian — presentation adapters."""

from arian.infrastructure.output.markdown.renderer import MarkdownRenderer
from arian.infrastructure.output.protocols import RendererProtocol

__all__ = [
    "MarkdownRenderer",
    "RendererProtocol",
]

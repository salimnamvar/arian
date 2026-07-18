"""Renderer layer for Arian.

Provides document rendering implementations and language detection.
"""

from arian.renderer.language import detect_language
from arian.renderer.markdown import MarkdownRenderer
from arian.renderer.protocols import RendererProtocol

__all__ = ["MarkdownRenderer", "RendererProtocol", "detect_language"]

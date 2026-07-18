"""Renderer protocols for Arian.

Defines protocols (interfaces) for renderer implementations.
"""

from __future__ import annotations

from typing import Protocol

from arian.domain.models import Document


class RendererProtocol(Protocol):
    """Renders documents to output format.

    Protocol for renderer implementations.
    """

    def render(self, a_documents: list[Document]) -> str:
        """Render documents to output format.

        Args:
            a_documents: Documents to render.

        Returns:
            Rendered content as string.
        """
        ...

"""Output rendering protocols."""

from __future__ import annotations

from typing import Protocol

from arian.domain.context.models import ContextPlan
from arian.domain.context.models import MaterializedChunk


class RendererProtocol(Protocol):
    """Protocol for rendering materialized chunks to output format."""

    def render(self, a_chunks: tuple[MaterializedChunk, ...], a_plan: ContextPlan) -> str: ...

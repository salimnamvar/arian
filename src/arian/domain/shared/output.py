"""Output ports — save and render contracts for the application layer."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Protocol

from arian.domain.shared.result import Result

if TYPE_CHECKING:
    from arian.domain.context.models import ContextPlan
    from arian.domain.context.models import MaterializedChunk


class OutputWriterProtocol(Protocol):
    """Output port — writes rendered content to the target destination.

    The Application layer depends on this protocol, not on filesystem
    implementation.
    """

    def save(self, a_path: str, a_content: str) -> Result[None]:
        """Write rendered content to the output destination.

        Args:
            a_path: Output file path.
            a_content: Rendered content string.

        Returns:
            Result[None] with is_success and message.
        """
        ...


class RendererProtocol(Protocol):
    """Output port — renders materialized chunks to a text format.

    Infrastructure adapters (Markdown, etc.) implement this; Application
    depends only on the protocol (CSR).
    """

    def render(
        self,
        a_chunks: tuple[MaterializedChunk, ...],
        a_plan: ContextPlan,
    ) -> Result[str]:
        """Render materialized chunks according to the plan.

        Args:
            a_chunks: Materialized content chunks.
            a_plan: Context plan with metadata for the output header.

        Returns:
            Result[str] with is_success, value (rendered string), and message.
        """
        ...

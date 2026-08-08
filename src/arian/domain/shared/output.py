"""Output ports — write and render contracts for the application layer."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Protocol

if TYPE_CHECKING:
    from arian.domain.context.models import ContextPlan
    from arian.domain.context.models import MaterializedChunk


class WriteResult:
    """Result of the write() operation.

    Attributes:
        is_success: Whether the operation succeeded.
        message: Error message if failed, empty string if successful.
    """

    def __init__(
        self,
        *,
        a_is_success: bool,
        a_message: str = "",
    ) -> None:
        self.is_success: bool = a_is_success
        self.message: str = a_message

    @staticmethod
    def success() -> WriteResult:
        return WriteResult(a_is_success=True)

    @staticmethod
    def failure(a_message: str) -> WriteResult:
        return WriteResult(a_is_success=False, a_message=a_message)


class OutputWriterProtocol(Protocol):
    """Output port — writes rendered content to the target destination.

    The Application layer depends on this protocol, not on filesystem
    implementation.
    """

    def write(self, a_path: str, a_content: str) -> WriteResult:
        """Write rendered content to the output destination.

        Args:
            a_path: Output file path.
            a_content: Rendered content string.

        Returns:
            WriteResult with is_success and message.
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
    ) -> RenderResult:
        """Render materialized chunks according to the plan.

        Args:
            a_chunks: Materialized content chunks.
            a_plan: Context plan with metadata for the output header.

        Returns:
            RenderResult with is_success, value (rendered string), and message.
        """
        ...


class RenderResult:
    """Result of the render() operation.

    Attributes:
        is_success: Whether the operation succeeded.
        value: Rendered string if successful, None otherwise.
        message: Error message if failed, empty string if successful.
    """

    def __init__(
        self,
        *,
        a_is_success: bool,
        a_value: str | None = None,
        a_message: str = "",
    ) -> None:
        self.is_success: bool = a_is_success
        self.value: str | None = a_value
        self.message: str = a_message

    @staticmethod
    def success(a_value: str) -> RenderResult:
        return RenderResult(a_is_success=True, a_value=a_value)

    @staticmethod
    def failure(a_message: str) -> RenderResult:
        return RenderResult(a_is_success=False, a_message=a_message)

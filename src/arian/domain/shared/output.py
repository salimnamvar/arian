"""Output port for writing rendered content."""

from __future__ import annotations

from typing import Protocol


class OutputWriterProtocol(Protocol):
    """Output port — writes rendered content to the target destination.

    The Application layer depends on this protocol, not on filesystem
    implementation.
    """

    def write(self, a_path: str, a_content: str) -> None:
        """Write rendered content to the output destination.

        Args:
            a_path: Output file path.
            a_content: Rendered content string.
        """
        ...

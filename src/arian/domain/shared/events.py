"""Simple event hooks and pipeline extension points."""

from __future__ import annotations

from typing import Protocol


class PipelineProgressProtocol(Protocol):
    """Hook for reporting pipeline progress."""

    def on_stage_start(self, a_stage: str, a_total: int) -> None:
        """Called when a pipeline stage begins.

        Args:
            a_stage: Name of the pipeline stage.
            a_total: Total number of items expected in this stage.
        """
        ...

    def on_stage_progress(self, a_stage: str, a_current: int, a_total: int) -> None:
        """Report progress within a pipeline stage.

        Args:
            a_stage: Name of the current pipeline stage.
            a_current: Current item index (0-based).
            a_total: Total number of items in the stage.
        """
        ...

    def on_stage_complete(self, a_stage: str) -> None:
        """Called when a pipeline stage completes successfully.

        Args:
            a_stage: Name of the pipeline stage that completed.
        """
        ...

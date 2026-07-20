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


class PipelineStageProtocol(Protocol):
    """Extension point for adding or replacing a pipeline stage.

    The default pipeline is composed via constructor-injected collaborators
    on ContextBuilder (collector, planner, materializer). To extend:

      1. Implement this protocol (or inject a new collaborator service).
      2. Wire the implementation in bootstrap ``create_application()``.
      3. Invoke it from ContextBuilder at the appropriate lifecycle point.

    The default pipeline (collect → plan → load → materialize → render → write)
    is the expected production configuration. Composability is for advanced
    use and tests only.
    """

    @property
    def name(self) -> str:
        """Stable stage identifier used in progress and error reporting."""
        ...


class ProgressHook(Protocol):
    """Hook for reporting pipeline progress."""

    def on_progress(self, a_stage: str, a_current: int, a_total: int) -> None:
        """Report progress for a pipeline stage.

        Args:
            a_stage: Name of the current pipeline stage.
            a_current: Current item index (0-based).
            a_total: Total number of items in the stage.
        """
        ...


class ErrorHook(Protocol):
    """Hook for reporting errors during processing."""

    def on_error(self, a_stage: str, a_error: Exception) -> None:
        """Report an error that occurred during a pipeline stage.

        Args:
            a_stage: Name of the pipeline stage where the error occurred.
            a_error: The exception that was raised.
        """
        ...

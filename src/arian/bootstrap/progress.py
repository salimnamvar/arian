"""Logging-based pipeline progress reporter."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class LoggingProgressReporter:
    """Reports pipeline stage progress via the standard logging system.

    Implements PipelineProgressProtocol for composition-root injection.
    """

    def on_stage_start(self, a_stage: str, a_total: int) -> None:
        """Log stage start.

        Args:
            a_stage: Stage name.
            a_total: Expected work units.
        """
        logger.info("Pipeline stage start: %s (items=%d)", a_stage, a_total)

    def on_stage_progress(self, a_stage: str, a_current: int, a_total: int) -> None:
        """Log stage progress at debug level.

        Args:
            a_stage: Stage name.
            a_current: Current progress index.
            a_total: Total work units.
        """
        logger.debug("Pipeline stage progress: %s %d/%d", a_stage, a_current, a_total)

    def on_stage_complete(self, a_stage: str) -> None:
        """Log stage completion.

        Args:
            a_stage: Stage name.
        """
        logger.info("Pipeline stage complete: %s", a_stage)

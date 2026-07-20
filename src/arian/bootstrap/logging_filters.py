"""Logging filters for structured context."""

from __future__ import annotations

import logging
import uuid


class RunContextFilter(logging.Filter):
    """Adds run_id to all log records for correlation."""

    def __init__(self) -> None:
        super().__init__()
        self.run_id: str = str(uuid.uuid4())[:8]

    def filter(self, record: logging.LogRecord) -> bool:  # a-prefix-ignore: stdlib Filter.signature
        """Attach run_id to log record for cross-log correlation.

        Args:
            record: Log record to filter.

        Returns:
            Always True — admits all records.
        """
        record.run_id = self.run_id  # type: ignore[attr-defined]
        return True

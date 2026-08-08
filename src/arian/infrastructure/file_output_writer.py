"""File-based output writer — infrastructure adapter with atomic writes."""

from __future__ import annotations

import contextlib
import logging
import os
from pathlib import Path
import tempfile

from arian.infrastructure.retry import retry_sync_with_backoff

logger = logging.getLogger(__name__)


class FileOutputWriter:
    """Writes rendered content to files on disk using atomic rename.

    Strategy: write to a temporary file in the same directory, then
    ``os.replace`` onto the target path. This prevents partial output
    if the process crashes mid-write. Transient OS errors are retried.
    """

    def write(self, a_path: str, a_content: str) -> None:
        """Atomically write rendered content to a file.

        Contract: raises on invalid input or on failure, and returns
        ``None`` only after the content is durably on disk. Inputs are
        verified up front (non-empty path and content) so a bad call
        fails fast instead of producing an empty or misplaced file.

        Args:
            a_path: Output file path.
            a_content: Rendered content string.

        Raises:
            ValueError: If ``a_path`` or ``a_content`` is empty.
            OSError: On filesystem failure.
        """
        msg: str = ""
        if not a_path or not a_path.strip():
            msg = "Output path must be a non-empty string"
        elif not a_content:
            msg = "Output content must not be empty"

        if msg:
            logger.error("%s", msg)
            raise ValueError(msg)

        path = Path(a_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        retry_sync_with_backoff(
            self._write_atomic,
            path,
            a_content,
            a_max_retries=3,
            a_base_delay=0.05,
            a_exceptions=(OSError,),
        )

    @staticmethod
    def _write_atomic(a_path: Path, a_content: str) -> None:
        """Perform a single atomic write attempt.

        Logs the per-attempt failure at debug level before re-raising so
        the transient attempts are visible; the final failure after all
        retries is logged at error level by ``retry_sync_with_backoff``.

        Args:
            a_path: Destination path.
            a_content: Content to write.

        Raises:
            OSError: On filesystem failure.
        """
        fd: int
        tmp_name: str
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{a_path.name}.",
            suffix=".tmp",
            dir=str(a_path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(a_content)
                handle.flush()
                os.fsync(handle.fileno())
            Path(tmp_name).replace(a_path)
            logger.debug("Atomically wrote %d bytes to %s", len(a_content), a_path)
        except Exception:
            logger.debug("Atomic write to %s failed", a_path)
            with contextlib.suppress(OSError):
                Path(tmp_name).unlink(missing_ok=True)
            raise

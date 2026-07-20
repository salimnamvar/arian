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

        Creates parent directories as needed. Writes to a same-directory
        temp file first, then renames into place. Uses
        ``retry_sync_with_backoff`` for transient filesystem errors.

        Args:
            a_path: Output file path.
            a_content: Rendered content string.
        """
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
            with contextlib.suppress(OSError):
                Path(tmp_name).unlink(missing_ok=True)
            raise

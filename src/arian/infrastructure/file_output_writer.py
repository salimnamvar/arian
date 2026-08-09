"""File-based output writer — infrastructure adapter with atomic writes."""

from __future__ import annotations

import contextlib
import logging
import os
from pathlib import Path
import tempfile

from arian.domain.shared.result import Result
from arian.infrastructure.base import BaseInfrastructureModule
from arian.infrastructure.retry import retry_sync_with_backoff
from arian.util.base import ModuleMetadata

logger = logging.getLogger(__name__)


class FileOutputWriter(BaseInfrastructureModule):
    """Writes rendered content to files on disk using atomic rename.

    Strategy: write to a temporary file in the same directory, then
    ``os.replace`` onto the target path. This prevents partial output
    if the process crashes mid-write. Transient OS errors are retried.
    """

    def __init__(self) -> None:
        """Initialize file output writer."""
        super().__init__(
            a_metadata=ModuleMetadata(
                name="arian.infrastructure.file_output_writer",
                layer="infrastructure",
                capabilities=frozenset({"sync"}),
            )
        )

    def write(self, a_path: str, a_content: str) -> Result[None]:
        """Atomically write rendered content to a file.

        Contract: returns Result[None] with is_success and message.
        Inputs are verified up front (non-empty path and content) so
        a bad call fails fast instead of producing an empty or misplaced file.

        Args:
            a_path: Output file path.
            a_content: Rendered content string.

        Returns:
            Result[None] with is_success and message.
        """
        result: Result[None] = Result[None].failure("uninitialized")
        b_continue: bool = True

        if not a_path or not a_path.strip():
            msg = "Output path must be a non-empty string"
            logger.error("%s", msg)
            result = Result[None].failure(msg)
            b_continue = False
        elif not a_content:
            msg = "Output content must not be empty"
            logger.error("%s", msg)
            result = Result[None].failure(msg)
            b_continue = False

        path: Path = Path(a_path) if b_continue else Path("x")

        if b_continue:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                msg = f"Failed to create output directory: {path.parent}"
                logger.exception("%s", msg)
                result = Result[None].failure(msg)
                b_continue = False

        if b_continue:
            retry_result = retry_sync_with_backoff(
                self._write_atomic,
                path,
                a_content,
                a_max_retries=3,
                a_base_delay=0.05,
                a_exceptions=(OSError,),
            )
            if retry_result.is_success:
                result = Result[None].success()
            else:
                msg = f"Failed to write output file: {a_path}"
                logger.error("%s", retry_result.message)
                result = Result[None].failure(msg)
                b_continue = False

        return result

    @staticmethod
    def _write_atomic(a_path: Path, a_content: str) -> None:
        """Perform a single atomic write attempt.

        Logs the per-attempt failure at debug level before re-raising so
        the transient attempts are visible.

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

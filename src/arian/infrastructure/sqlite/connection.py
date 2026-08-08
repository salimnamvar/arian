"""SQLite connection management."""

from __future__ import annotations

import logging
from pathlib import Path
import sqlite3

from arian.domain.shared.result import Result

logger = logging.getLogger(__name__)


def get_connection(a_db_path: Path) -> Result[sqlite3.Connection]:
    """Get a SQLite connection to the specified database.

    Creates the parent directory if it doesn't exist.

    Args:
        a_db_path: Path to the SQLite database file.

    Returns:
        Result[sqlite3.Connection] with connection or error message.
    """
    result: Result[sqlite3.Connection] = Result[sqlite3.Connection].failure("uninitialized")
    b_continue: bool = True

    if not a_db_path:
        result = Result[sqlite3.Connection].failure("a_db_path must be non-empty")
        b_continue = False

    if b_continue:
        try:
            a_db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            msg = f"Failed to create database directory: {a_db_path.parent}"
            logger.exception("%s", msg)
            result = Result[sqlite3.Connection].failure(msg)
            b_continue = False

    if b_continue:
        try:
            conn = sqlite3.connect(str(a_db_path))
            result = Result[sqlite3.Connection].success(conn)
        except sqlite3.Error:
            msg = f"Failed to connect to database: {a_db_path}"
            logger.exception("%s", msg)
            result = Result[sqlite3.Connection].failure(msg)

    return result

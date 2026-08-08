"""SQLite connection management."""

from __future__ import annotations

import logging
from pathlib import Path
import sqlite3

logger = logging.getLogger(__name__)


class ConnectionResult:
    """Result of database connection attempt.

    Attributes:
        is_success: Whether connection succeeded.
        connection: SQLite connection if successful, None otherwise.
        message: Error message if failed.
    """

    def __init__(
        self,
        *,
        a_is_success: bool,
        a_connection: sqlite3.Connection | None = None,
        a_message: str = "",
    ) -> None:
        self.is_success: bool = a_is_success
        self.connection: sqlite3.Connection | None = a_connection
        self.message: str = a_message

    @staticmethod
    def success(a_connection: sqlite3.Connection) -> ConnectionResult:
        return ConnectionResult(a_is_success=True, a_connection=a_connection)

    @staticmethod
    def failure(a_message: str) -> ConnectionResult:
        return ConnectionResult(a_is_success=False, a_message=a_message)


def get_connection(a_db_path: Path) -> ConnectionResult:
    """Get a SQLite connection to the specified database.

    Creates the parent directory if it doesn't exist.

    Args:
        a_db_path: Path to the SQLite database file.

    Returns:
        ConnectionResult with connection or error message.
    """
    result: ConnectionResult = ConnectionResult.failure("uninitialized")
    b_continue: bool = True

    if not a_db_path:
        result = ConnectionResult.failure("a_db_path must be non-empty")
        b_continue = False

    if b_continue:
        try:
            a_db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            msg = f"Failed to create database directory: {a_db_path.parent}"
            logger.exception("%s", msg)
            result = ConnectionResult.failure(msg)
            b_continue = False

    if b_continue:
        try:
            conn = sqlite3.connect(str(a_db_path))
            result = ConnectionResult.success(conn)
        except sqlite3.Error:
            msg = f"Failed to connect to database: {a_db_path}"
            logger.exception("%s", msg)
            result = ConnectionResult.failure(msg)

    return result

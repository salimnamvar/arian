"""SQLite connection management."""

from __future__ import annotations

from pathlib import Path
import sqlite3


def get_connection(a_db_path: Path) -> sqlite3.Connection:
    """Get a SQLite connection to the specified database.

    Creates the parent directory if it doesn't exist.

    Args:
        a_db_path: Path to the SQLite database file.

    Returns:
        Active SQLite connection.
    """
    a_db_path.parent.mkdir(parents=True, exist_ok=True)
    result: sqlite3.Connection = sqlite3.connect(str(a_db_path))
    return result

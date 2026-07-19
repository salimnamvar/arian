"""SQLite-backed repository index for persistent storage."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import sqlite3
from typing import Any

from arian.domain.repository.models import Dependency
from arian.domain.repository.models import Module
from arian.domain.repository.models import Repository
from arian.domain.repository.models import RepositoryFile
from arian.domain.repository.models import Symbol
from arian.domain.shared.enums import DependencyKind
from arian.domain.shared.enums import FileRole
from arian.domain.shared.enums import SymbolKind

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    language TEXT NOT NULL,
    role TEXT NOT NULL,
    tokens INTEGER NOT NULL,
    hash TEXT NOT NULL,
    size_bytes INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS symbols (
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    file_path TEXT NOT NULL,
    signature TEXT NOT NULL,
    docstring TEXT DEFAULT '',
    line_start INTEGER DEFAULT 0,
    line_end INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS dependencies (
    source_path TEXT NOT NULL,
    target_path TEXT NOT NULL,
    kind TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS modules (
    name TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    files TEXT DEFAULT '[]'
);
"""


class SQLiteRepositoryIndex:
    """SQLite-backed implementation of RepositoryIndexProtocol.

    Stores repository metadata in a SQLite database for persistence
    across runs.

    Attributes:
        _db_path: Path to the SQLite database file.
        _connection: Active database connection.
    """

    def __init__(self, a_db_path: Path) -> None:
        """Initialize SQLite index.

        Args:
            a_db_path: Path to the SQLite database file.
        """
        self._db_path: Path = a_db_path
        self._connection: sqlite3.Connection | None = None

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create the database connection.

        Returns:
            Active SQLite connection.
        """
        if self._connection is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(str(self._db_path))
            self._connection.executescript(_SCHEMA_SQL)
        return self._connection

    async def save_repository(self, a_repo: Repository) -> None:
        """Save a repository by storing its files.

        Args:
            a_repo: Repository to store.
        """
        for repo_file in a_repo.files:
            await self.save_file(repo_file)

    async def save_file(self, a_file: RepositoryFile) -> None:
        """Save a file metadata entry.

        Args:
            a_file: File metadata to store.
        """
        conn: sqlite3.Connection = self._get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO files (path, language, role, tokens, hash, size_bytes) VALUES (?, ?, ?, ?, ?, ?)",
            (a_file.path, a_file.language, a_file.role.value, a_file.tokens, a_file.hash, a_file.size_bytes),
        )
        conn.commit()

    async def get_file(self, a_path: str) -> RepositoryFile | None:
        """Retrieve a file by path.

        Args:
            a_path: File path to look up.

        Returns:
            RepositoryFile if found, None otherwise.
        """
        conn: sqlite3.Connection = self._get_connection()
        cursor: sqlite3.Cursor = conn.execute(
            "SELECT path, language, role, tokens, hash, size_bytes FROM files WHERE path = ?",
            (a_path,),
        )
        row: tuple[Any, ...] | None = cursor.fetchone()
        result: RepositoryFile | None = None
        if row is not None:
            result = RepositoryFile(
                path=row[0],
                language=row[1],
                role=FileRole(row[2]),
                tokens=row[3],
                hash=row[4],
                size_bytes=row[5],
            )
        return result

    async def list_files(self) -> list[RepositoryFile]:
        """List all indexed files.

        Returns:
            List of all stored file metadata.
        """
        conn: sqlite3.Connection = self._get_connection()
        cursor: sqlite3.Cursor = conn.execute(
            "SELECT path, language, role, tokens, hash, size_bytes FROM files",
        )
        result: list[RepositoryFile] = [
            RepositoryFile(
                path=row[0],
                language=row[1],
                role=FileRole(row[2]),
                tokens=row[3],
                hash=row[4],
                size_bytes=row[5],
            )
            for row in cursor.fetchall()
        ]
        return result

    async def save_symbol(self, a_symbol: Symbol) -> None:
        """Save an extracted symbol.

        Args:
            a_symbol: Symbol to store.
        """
        conn: sqlite3.Connection = self._get_connection()
        conn.execute(
            "INSERT INTO symbols (name, kind, file_path, signature, docstring, line_start, line_end) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                a_symbol.name,
                a_symbol.kind.value,
                a_symbol.file_path,
                a_symbol.signature,
                a_symbol.docstring,
                a_symbol.line_start,
                a_symbol.line_end,
            ),
        )
        conn.commit()

    async def find_symbols(self, a_name: str) -> list[Symbol]:
        """Find symbols by name.

        Args:
            a_name: Symbol name to search for.

        Returns:
            List of matching symbols.
        """
        conn: sqlite3.Connection = self._get_connection()
        cursor: sqlite3.Cursor = conn.execute(
            "SELECT name, kind, file_path, signature, docstring, line_start, line_end FROM symbols WHERE name = ?",
            (a_name,),
        )
        result: list[Symbol] = [
            Symbol(
                name=row[0],
                kind=SymbolKind(row[1]),
                file_path=row[2],
                signature=row[3],
                docstring=row[4],
                line_start=row[5],
                line_end=row[6],
            )
            for row in cursor.fetchall()
        ]
        return result

    async def save_dependency(self, a_dep: Dependency) -> None:
        """Save a dependency relationship.

        Args:
            a_dep: Dependency to store.
        """
        conn: sqlite3.Connection = self._get_connection()
        conn.execute(
            "INSERT INTO dependencies (source_path, target_path, kind) VALUES (?, ?, ?)",
            (a_dep.source_path, a_dep.target_path, a_dep.kind.value),
        )
        conn.commit()

    async def get_dependencies(self, a_path: str) -> list[Dependency]:
        """Get dependencies for a file.

        Args:
            a_path: File path to get dependencies for.

        Returns:
            List of dependencies involving this file.
        """
        conn: sqlite3.Connection = self._get_connection()
        cursor: sqlite3.Cursor = conn.execute(
            "SELECT source_path, target_path, kind FROM dependencies WHERE source_path = ? OR target_path = ?",
            (a_path, a_path),
        )
        result: list[Dependency] = [
            Dependency(
                source_path=row[0],
                target_path=row[1],
                kind=DependencyKind(row[2]),
            )
            for row in cursor.fetchall()
        ]
        return result

    async def save_module(self, a_module: Module) -> None:
        """Save a module grouping.

        Args:
            a_module: Module to store.
        """
        conn: sqlite3.Connection = self._get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO modules (name, path, files) VALUES (?, ?, ?)",
            (a_module.name, a_module.path, json.dumps(list(a_module.files))),
        )
        conn.commit()

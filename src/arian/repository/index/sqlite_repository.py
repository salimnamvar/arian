"""SQLite-backed repository index for persistent storage."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import sqlite3
from typing import Any

from arian.domain.exceptions import DatabaseConnectionError
from arian.domain.exceptions import RepositoryIndexError
from arian.domain.repository.models import Dependency
from arian.domain.repository.models import Module
from arian.domain.repository.models import Repository
from arian.domain.repository.models import RepositoryFile
from arian.domain.repository.models import Symbol
from arian.domain.shared.enums import DependencyKind
from arian.domain.shared.enums import FileRole
from arian.domain.shared.enums import SymbolKind
from arian.infrastructure.config import RepositoryConfig
from arian.repository.base import BaseRepositoryModule
from arian.util.base import ModuleMetadata

logger = logging.getLogger(__name__)


class SQLiteRepositoryIndex(BaseRepositoryModule):
    """SQLite-backed implementation of RepositoryIndexProtocol.

    Stores repository metadata in a SQLite database for persistence
    across runs.

    Safe-coding contract: every SQLite failure is logged locally and
    translated into a typed domain exception — ``DatabaseConnectionError`` for
    connection failures, ``RepositoryIndexError`` for read/write failures. Raw
    ``sqlite3.Error`` never escapes this adapter.

    Attributes:
        _db_path: Path to the SQLite database file.
        _connection: Active database connection.
        _config: Repository configuration (schema DDL).
    """

    def __init__(self, a_db_path: Path, a_config: RepositoryConfig = RepositoryConfig()) -> None:
        """Initialize SQLite index.

        Args:
            a_db_path: Path to the SQLite database file.
            a_config: Repository configuration (schema DDL).
        """
        super().__init__(
            a_metadata=ModuleMetadata(
                name="arian.repository.sqlite",
                layer="repository",
                capabilities=frozenset({"async"}),
            )
        )
        self._db_path: Path = a_db_path
        self._connection: sqlite3.Connection | None = None
        self._config: RepositoryConfig = a_config

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create the database connection.

        Returns:
            Active SQLite connection.

        Raises:
            DatabaseConnectionError: If the database cannot be opened or the
                schema cannot be applied.
        """
        if self._connection is None:
            try:
                self._db_path.parent.mkdir(parents=True, exist_ok=True)
                self._connection = sqlite3.connect(str(self._db_path))
                self._connection.executescript(self._config.schema_sql)
            except sqlite3.Error as e:
                msg = f"Cannot open SQLite database at {self._db_path}"
                logger.exception(msg)
                raise DatabaseConnectionError(msg, a_cause=e) from e
        return self._connection

    def _execute_write(self, a_sql: str, a_params: tuple[object, ...]) -> None:
        """Run a write statement and commit, translating failures.

        Args:
            a_sql: SQL statement to execute.
            a_params: Bound parameters for the statement.

        Raises:
            RepositoryIndexError: If the write or commit fails.
        """
        try:
            conn: sqlite3.Connection = self._get_connection()
            conn.execute(a_sql, a_params)
            conn.commit()
        except sqlite3.Error as e:
            msg = f"SQLite write failed: {a_sql}"
            logger.exception(msg)
            raise RepositoryIndexError(msg, a_cause=e) from e

    def _fetch_rows(self, a_sql: str, a_params: tuple[object, ...]) -> list[tuple[Any, ...]]:
        """Run a query and return all rows, translating failures.

        Args:
            a_sql: SQL statement to execute.
            a_params: Bound parameters for the statement.

        Returns:
            Rows returned by the query.

        Raises:
            RepositoryIndexError: If the query fails.
        """
        result: list[tuple[Any, ...]]
        try:
            conn: sqlite3.Connection = self._get_connection()
            cursor: sqlite3.Cursor = conn.execute(a_sql, a_params)
            result = cursor.fetchall()
        except sqlite3.Error as e:
            msg = f"SQLite read failed: {a_sql}"
            logger.exception(msg)
            raise RepositoryIndexError(msg, a_cause=e) from e
        return result

    @staticmethod
    def _map_row_to_file(a_row: tuple[Any, ...]) -> RepositoryFile:
        """Map a files-table row to a domain model.

        Args:
            a_row: SQL row (path, language, role, tokens, hash, size_bytes).

        Returns:
            RepositoryFile domain entity.
        """
        return RepositoryFile(
            path=a_row[0],
            language=a_row[1],
            role=FileRole(a_row[2]),
            tokens=a_row[3],
            hash=a_row[4],
            size_bytes=a_row[5],
        )

    @staticmethod
    def _map_row_to_symbol(a_row: tuple[Any, ...]) -> Symbol:
        """Map a symbols-table row to a domain model.

        Args:
            a_row: SQL row (name, kind, file_path, signature, docstring, line_start, line_end).

        Returns:
            Symbol domain entity.
        """
        return Symbol(
            name=a_row[0],
            kind=SymbolKind(a_row[1]),
            file_path=a_row[2],
            signature=a_row[3],
            docstring=a_row[4],
            line_start=a_row[5],
            line_end=a_row[6],
        )

    @staticmethod
    def _map_row_to_dependency(a_row: tuple[Any, ...]) -> Dependency:
        """Map a dependencies-table row to a domain model.

        Args:
            a_row: SQL row (source_path, target_path, kind).

        Returns:
            Dependency domain entity.
        """
        return Dependency(
            source_path=a_row[0],
            target_path=a_row[1],
            kind=DependencyKind(a_row[2]),
        )

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
        self._execute_write(
            "INSERT OR REPLACE INTO files (path, language, role, tokens, hash, size_bytes) VALUES (?, ?, ?, ?, ?, ?)",
            (a_file.path, a_file.language, a_file.role.value, a_file.tokens, a_file.hash, a_file.size_bytes),
        )

    async def load(self, a_path: str) -> RepositoryFile | None:
        """Retrieve a file by path.

        Args:
            a_path: File path to look up.

        Returns:
            RepositoryFile if found, None otherwise.
        """
        rows: list[tuple[Any, ...]] = self._fetch_rows(
            "SELECT path, language, role, tokens, hash, size_bytes FROM files WHERE path = ?",
            (a_path,),
        )
        result: RepositoryFile | None = self._map_row_to_file(rows[0]) if rows else None
        return result

    async def load_all(self) -> list[RepositoryFile]:
        """List all indexed files.

        Returns:
            List of all stored file metadata.
        """
        rows: list[tuple[Any, ...]] = self._fetch_rows(
            "SELECT path, language, role, tokens, hash, size_bytes FROM files",
            (),
        )
        result: list[RepositoryFile] = [self._map_row_to_file(row) for row in rows]
        return result

    async def save_symbol(self, a_symbol: Symbol) -> None:
        """Save an extracted symbol.

        Args:
            a_symbol: Symbol to store.
        """
        self._execute_write(
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

    async def find(self, a_name: str) -> list[Symbol]:
        """Find symbols by name.

        Args:
            a_name: Symbol name to search for.

        Returns:
            List of matching symbols.
        """
        rows: list[tuple[Any, ...]] = self._fetch_rows(
            "SELECT name, kind, file_path, signature, docstring, line_start, line_end FROM symbols WHERE name = ?",
            (a_name,),
        )
        result: list[Symbol] = [self._map_row_to_symbol(row) for row in rows]
        return result

    async def save_dependency(self, a_dep: Dependency) -> None:
        """Save a dependency relationship.

        Args:
            a_dep: Dependency to store.
        """
        self._execute_write(
            "INSERT INTO dependencies (source_path, target_path, kind) VALUES (?, ?, ?)",
            (a_dep.source_path, a_dep.target_path, a_dep.kind.value),
        )

    async def load_dependencies(self, a_path: str) -> list[Dependency]:
        """Get dependencies for a file.

        Args:
            a_path: File path to get dependencies for.

        Returns:
            List of dependencies involving this file.
        """
        rows: list[tuple[Any, ...]] = self._fetch_rows(
            "SELECT source_path, target_path, kind FROM dependencies WHERE source_path = ? OR target_path = ?",
            (a_path, a_path),
        )
        result: list[Dependency] = [self._map_row_to_dependency(row) for row in rows]
        return result

    async def save_module(self, a_module: Module) -> None:
        """Save a module grouping.

        Args:
            a_module: Module to store.
        """
        self._execute_write(
            "INSERT OR REPLACE INTO modules (name, path, files) VALUES (?, ?, ?)",
            (a_module.name, a_module.path, json.dumps(list(a_module.files))),
        )

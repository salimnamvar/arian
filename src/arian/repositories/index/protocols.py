"""Repository index protocol and implementations."""

from __future__ import annotations

from typing import Protocol

from arian.domain.repository.models import Dependency
from arian.domain.repository.models import Module
from arian.domain.repository.models import Repository
from arian.domain.repository.models import RepositoryFile
from arian.domain.repository.models import Symbol


class RepositoryIndexProtocol(Protocol):
    """Indexed knowledge of the repository.

    Provides async storage and retrieval of repository metadata,
    symbols, dependencies, and modules.
    """

    async def save_repository(self, a_repo: Repository) -> None:
        """Save a repository representation.

        Args:
            a_repo: Repository to store.
        """
        ...

    async def save_file(self, a_file: RepositoryFile) -> None:
        """Save a file metadata entry.

        Args:
            a_file: File metadata to store.
        """
        ...

    async def get_file(self, a_path: str) -> RepositoryFile | None:
        """Retrieve a file by path.

        Args:
            a_path: File path to look up.

        Returns:
            RepositoryFile if found, None otherwise.
        """
        ...

    async def list_files(self) -> list[RepositoryFile]:
        """List all indexed files.

        Returns:
            List of all stored file metadata.
        """
        ...

    async def save_symbol(self, a_symbol: Symbol) -> None:
        """Save an extracted symbol.

        Args:
            a_symbol: Symbol to store.
        """
        ...

    async def find_symbols(self, a_name: str) -> list[Symbol]:
        """Find symbols by name.

        Args:
            a_name: Symbol name to search for.

        Returns:
            List of matching symbols.
        """
        ...

    async def save_dependency(self, a_dep: Dependency) -> None:
        """Save a dependency relationship.

        Args:
            a_dep: Dependency to store.
        """
        ...

    async def get_dependencies(self, a_path: str) -> list[Dependency]:
        """Get dependencies for a file.

        Args:
            a_path: File path to get dependencies for.

        Returns:
            List of dependencies involving this file.
        """
        ...

    async def save_module(self, a_module: Module) -> None:
        """Save a module grouping.

        Args:
            a_module: Module to store.
        """
        ...

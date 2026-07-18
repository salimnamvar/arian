"""In-memory repository index for testing and lightweight use."""

from __future__ import annotations

from arian.domain.repository.models import Dependency
from arian.domain.repository.models import Module
from arian.domain.repository.models import Repository
from arian.domain.repository.models import RepositoryFile
from arian.domain.repository.models import Symbol


class MemoryRepositoryIndex:
    """In-memory implementation of RepositoryIndexProtocol.

    Stores all data in dictionaries. Suitable for testing and
    scenarios where persistence is not required.

    Attributes:
        _files: File metadata indexed by path.
        _symbols: Symbols indexed by name.
        _dependencies: Dependencies indexed by source path.
        _modules: Modules indexed by name.
    """

    def __init__(self) -> None:
        """Initialize empty index."""
        self._files: dict[str, RepositoryFile] = {}
        self._symbols: dict[str, list[Symbol]] = {}
        self._dependencies: dict[str, list[Dependency]] = {}
        self._modules: dict[str, Module] = {}

    async def save_repository(self, a_repo: Repository) -> None:
        """Save a repository by storing its files.

        Args:
            a_repo: Repository to store.
        """
        for repo_file in a_repo.files:
            self._files[repo_file.path] = repo_file

    async def save_file(self, a_file: RepositoryFile) -> None:
        """Save a file metadata entry.

        Args:
            a_file: File metadata to store.
        """
        self._files[a_file.path] = a_file

    async def get_file(self, a_path: str) -> RepositoryFile | None:
        """Retrieve a file by path.

        Args:
            a_path: File path to look up.

        Returns:
            RepositoryFile if found, None otherwise.
        """
        result: RepositoryFile | None = self._files.get(a_path)
        return result

    async def list_files(self) -> list[RepositoryFile]:
        """List all indexed files.

        Returns:
            List of all stored file metadata.
        """
        result: list[RepositoryFile] = list(self._files.values())
        return result

    async def save_symbol(self, a_symbol: Symbol) -> None:
        """Save an extracted symbol.

        Args:
            a_symbol: Symbol to store.
        """
        self._symbols.setdefault(a_symbol.name, []).append(a_symbol)

    async def find_symbols(self, a_name: str) -> list[Symbol]:
        """Find symbols by name.

        Args:
            a_name: Symbol name to search for.

        Returns:
            List of matching symbols.
        """
        result: list[Symbol] = self._symbols.get(a_name, [])
        return result

    async def save_dependency(self, a_dep: Dependency) -> None:
        """Save a dependency relationship.

        Args:
            a_dep: Dependency to store.
        """
        self._dependencies.setdefault(a_dep.source_path, []).append(a_dep)

    async def get_dependencies(self, a_path: str) -> list[Dependency]:
        """Get dependencies for a file.

        Args:
            a_path: File path to get dependencies for.

        Returns:
            List of dependencies involving this file.
        """
        result: list[Dependency] = self._dependencies.get(a_path, [])
        return result

    async def save_module(self, a_module: Module) -> None:
        """Save a module grouping.

        Args:
            a_module: Module to store.
        """
        self._modules[a_module.name] = a_module

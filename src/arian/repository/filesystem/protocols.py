"""File collection protocol — abstraction over filesystem scanning."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from arian.domain.repository.models import CollectionStats
from arian.domain.repository.models import RepositoryFile


class PathFilterProtocol(Protocol):
    """Protocol for filtering paths using gitignore patterns."""

    last_matched_pattern: str | None

    def set_explicit_paths(self, a_paths: frozenset[Path]) -> None:
        """Replace the explicit-path allow-list.

        Args:
            a_paths: New set of paths that always pass the filter.
        """
        ...

    def should_include(self, a_path: Path) -> bool:
        """Check if path should be included.

        Args:
            a_path: Path to check.

        Returns:
            True if path should be included.
        """
        ...


class FileCollectorProtocol(Protocol):
    """Protocol for collecting files from a directory."""

    async def collect(
        self,
        a_path: Path,
        *,
        a_root: Path | None = None,
        a_explicit_paths: frozenset[Path] = frozenset(),
    ) -> list[RepositoryFile]: ...

    @property
    def stats(self) -> CollectionStats: ...

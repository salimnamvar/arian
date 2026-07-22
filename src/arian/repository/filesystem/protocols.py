"""File collection protocol — abstraction over filesystem scanning."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from arian.domain.repository.models import RepositoryFile
from arian.repository.filesystem.collector import CollectionStats


class FileCollectorProtocol(Protocol):
    """Protocol for collecting files from a directory."""

    async def collect(self, a_path: Path, *, a_root: Path | None = None) -> list[RepositoryFile]: ...

    @property
    def stats(self) -> CollectionStats: ...

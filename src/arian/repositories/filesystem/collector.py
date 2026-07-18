"""Async file collector for repository scanning."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path

from arian.domain.repository.models import RepositoryFile
from arian.domain.shared.enums import FileRole
from arian.infrastructure.gitignore_filter import PathFilter
from arian.infrastructure.language import detect_language
from arian.infrastructure.tokenizer import count_tokens

logger = logging.getLogger(__name__)


class FileCollector:
    """Collects repository files from the filesystem.

    Scans directories recursively, respects .gitignore patterns,
    and produces RepositoryFile metadata without loading content.

    Attributes:
        _extensions: File extensions to include.
        _filter: Path filter for gitignore and exclusion patterns.
    """

    def __init__(
        self,
        a_extensions: frozenset[str],
        a_exclude: frozenset[str],
    ) -> None:
        """Initialize collector.

        Args:
            a_extensions: File extensions to include (e.g. {".py", ".md"}).
            a_exclude: Directory names to exclude.
        """
        self._extensions: frozenset[str] = a_extensions
        self._filter: PathFilter = PathFilter(a_exclude)

    async def collect(self, a_path: Path) -> list[RepositoryFile]:
        """Collect file metadata from a directory path.

        Args:
            a_path: Root directory to scan.

        Returns:
            List of RepositoryFile metadata objects.
        """
        files: list[RepositoryFile] = []
        emitted: set[Path] = set()
        await self._collect_directory(a_path, files, emitted)
        logger.debug("Collected %d files from %s", len(files), a_path)
        return files

    async def _collect_directory(
        self,
        a_directory: Path,
        a_files: list[RepositoryFile],
        a_emitted: set[Path],
    ) -> None:
        """Recursively collect files from a directory.

        Args:
            a_directory: Directory to scan.
            a_files: Accumulator for collected files.
            a_emitted: Set of already-emitted paths for deduplication.
        """
        entries: list[Path]

        try:
            entries = await asyncio.to_thread(
                lambda: sorted(a_directory.iterdir(), key=lambda p: (p.is_dir(), p.name)),
            )
        except OSError:
            logger.warning("Cannot read directory: %s", a_directory)
            entries = []

        for entry in entries:
            if entry.is_dir():
                if self._filter.should_include(entry):
                    await self._collect_directory(entry, a_files, a_emitted)
            elif entry.is_file():
                repo_file: RepositoryFile | None = await self._collect_file(entry, a_emitted)
                if repo_file is not None:
                    a_files.append(repo_file)

    async def _collect_file(
        self,
        a_path: Path,
        a_emitted: set[Path],
    ) -> RepositoryFile | None:
        """Collect metadata for a single file.

        Args:
            a_path: Path to the file.
            a_emitted: Set of already-emitted paths for deduplication.

        Returns:
            RepositoryFile if collected, None if skipped.
        """
        result: RepositoryFile | None = None

        if a_path.suffix not in self._extensions:
            logger.debug("Skipping %s (extension not in filter)", a_path)
        elif a_path.resolve() in a_emitted:
            logger.debug("Skipping %s (duplicate)", a_path)
        else:
            try:
                content: str = await asyncio.to_thread(
                    a_path.read_text,
                    encoding="utf-8",
                    errors="ignore",
                )
                a_emitted.add(a_path.resolve())
                tokens: int = await asyncio.to_thread(count_tokens, content)
                language: str = detect_language(a_path)
                content_hash: str = await asyncio.to_thread(
                    lambda: hashlib.sha256(content.encode()).hexdigest()[:16],
                )
                result = RepositoryFile(
                    path=str(a_path),
                    language=language,
                    role=FileRole.UNKNOWN,
                    tokens=tokens,
                    hash=content_hash,
                )
            except OSError:
                logger.warning("Skipping %s (read error)", a_path)

        return result

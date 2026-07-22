"""Async file collector for repository scanning."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from pathlib import Path

from arian.domain.protocols import FileClassifierProtocol
from arian.domain.repository.models import RepositoryFile
from arian.domain.shared.constants import MAX_FILE_SIZE_BYTES
from arian.domain.shared.enums import FileRole
from arian.domain.shared.language import detect_language
from arian.domain.shared.security import is_binary
from arian.domain.shared.tokenizer import estimate_tokens_from_size
from arian.infrastructure.gitignore_filter import PathFilter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CollectionStats:
    """Transparent collection statistics.

    Invariant: total_scanned == collected + sum(all skipped_*).

    Attributes:
        total_scanned: Total files encountered during traversal.
        collected: Files that passed all gates.
        skipped_binary: Files skipped because they are binary.
        skipped_size: Files skipped because they exceed max_file_size.
        skipped_gitignore: Files skipped by gitignore/exclude patterns.
        skipped_permission: Files skipped due to permission errors.
        skipped_error: Files skipped due to OS errors.
        skipped_by_extension: Files skipped by extension narrowing filter.
        unknown_language: Collected files with empty language string.
    """

    total_scanned: int = 0
    collected: int = 0
    skipped_binary: int = 0
    skipped_size: int = 0
    skipped_gitignore: int = 0
    skipped_permission: int = 0
    skipped_error: int = 0
    skipped_by_extension: int = 0
    unknown_language: int = 0


class FileCollector:
    """Collects repository files from the filesystem.

    Scans directories recursively, respects .gitignore patterns,
    and produces RepositoryFile metadata without loading content.

    Collection gate (in order):
        1. Binary check (is_binary on first 8KB)
        2. Size check (max_file_size)
        3. Gitignore/exclude check
        4. Extension narrowing (only if extensions is set)
        5. Language detection (computed once)

    Attributes:
        _extensions: File extensions to include. None means all text files.
        _max_file_size: Maximum file size in bytes.
        _filter: Path filter for gitignore and exclusion patterns.
        _classifier: File classifier for role detection.
    """

    def __init__(
        self,
        a_extensions: frozenset[str] | None,
        a_exclude: frozenset[str],
        a_classifier: FileClassifierProtocol | None = None,
        a_max_file_size: int = MAX_FILE_SIZE_BYTES,
    ) -> None:
        """Initialize collector.

        Args:
            a_extensions: File extensions to include. None means all text files.
            a_exclude: Directory names to exclude.
            a_classifier: Optional file classifier for role detection.
            a_max_file_size: Maximum file size in bytes.
        """
        self._extensions: frozenset[str] | None = a_extensions
        self._max_file_size: int = a_max_file_size
        self._filter: PathFilter = PathFilter(a_exclude)
        self._classifier: FileClassifierProtocol | None = a_classifier
        self._stats: CollectionStats = CollectionStats()

    @property
    def stats(self) -> CollectionStats:
        """Return collection statistics after collect() completes."""
        return self._stats

    async def collect(
        self,
        a_path: Path,
        a_root: Path | None = None,
    ) -> list[RepositoryFile]:
        """Collect file metadata from a path.

        Supports both individual files and directories. For directories,
        scans recursively. For files, collects metadata directly.

        Args:
            a_path: File or directory to scan.
            a_root: Root for computing relative paths. Defaults to a_path.

        Returns:
            List of RepositoryFile metadata objects.
        """
        root: Path = a_root if a_root is not None else a_path
        files: list[RepositoryFile] = []
        emitted: set[Path] = set()
        self._stats = CollectionStats()
        if a_path.is_file():
            repo_file: RepositoryFile | None = await self._collect_file(a_path, emitted, root)
            if repo_file is not None:
                files.append(repo_file)
        else:
            await self._collect_directory(a_path, files, emitted, root)
        logger.debug(
            "Collected %d files from %s (scanned=%d, binary=%d, size=%d, gitignore=%d, extension=%d)",
            len(files),
            a_path,
            self._stats.total_scanned,
            self._stats.skipped_binary,
            self._stats.skipped_size,
            self._stats.skipped_gitignore,
            self._stats.skipped_by_extension,
        )
        return files

    async def _collect_directory(
        self,
        a_directory: Path,
        a_files: list[RepositoryFile],
        a_emitted: set[Path],
        a_root: Path,
    ) -> None:
        """Recursively collect files from a directory.

        Args:
            a_directory: Directory to scan.
            a_files: Accumulator for collected files.
            a_emitted: Set of already-emitted paths for deduplication.
            a_root: Root for computing relative paths.
        """
        entries: list[Path]

        try:
            entries = await asyncio.to_thread(
                lambda: sorted(a_directory.iterdir(), key=lambda p: (p.is_dir(), p.name)),
            )
        except PermissionError:
            logger.debug("Skipping (permission denied): %s", a_directory)
            entries = []
        except OSError:
            logger.warning("Cannot read directory: %s", a_directory)
            entries = []

        for entry in entries:
            if entry.is_dir():
                if self._filter.should_include(entry):
                    await self._collect_directory(entry, a_files, a_emitted, a_root)
            elif entry.is_file():
                repo_file: RepositoryFile | None = await self._collect_file(entry, a_emitted, a_root)
                if repo_file is not None:
                    a_files.append(repo_file)

    async def _collect_file(
        self,
        a_path: Path,
        a_emitted: set[Path],
        a_root: Path,
    ) -> RepositoryFile | None:
        """Collect metadata for a single file without reading content.

        Gate order: binary → size → gitignore → extension → collect.

        Args:
            a_path: Path to the file.
            a_emitted: Set of already-emitted paths for deduplication.
            a_root: Root for computing relative paths.

        Returns:
            RepositoryFile if collected, None if skipped.
        """
        result: RepositoryFile | None = None
        self._stats = CollectionStats(
            total_scanned=self._stats.total_scanned + 1,
            collected=self._stats.collected,
            skipped_binary=self._stats.skipped_binary,
            skipped_size=self._stats.skipped_size,
            skipped_gitignore=self._stats.skipped_gitignore,
            skipped_permission=self._stats.skipped_permission,
            skipped_error=self._stats.skipped_error,
            skipped_by_extension=self._stats.skipped_by_extension,
            unknown_language=self._stats.unknown_language,
        )

        if a_path.resolve() in a_emitted:
            logger.debug("Skipping %s (duplicate)", a_path)
            self._stats = CollectionStats(
                total_scanned=self._stats.total_scanned,
                collected=self._stats.collected,
                skipped_binary=self._stats.skipped_binary,
                skipped_size=self._stats.skipped_size,
                skipped_gitignore=self._stats.skipped_gitignore + 1,
                skipped_permission=self._stats.skipped_permission,
                skipped_error=self._stats.skipped_error,
                skipped_by_extension=self._stats.skipped_by_extension,
                unknown_language=self._stats.unknown_language,
            )
        else:
            result = await self._try_collect(a_path, a_emitted, a_root)

        return result

    async def _try_collect(
        self,
        a_path: Path,
        a_emitted: set[Path],
        a_root: Path,
    ) -> RepositoryFile | None:
        """Attempt to collect a file through all gates.

        Args:
            a_path: Path to the file.
            a_emitted: Set of already-emitted paths for deduplication.
            a_root: Root for computing relative paths.

        Returns:
            RepositoryFile if collected, None if skipped.
        """
        result: RepositoryFile | None = None
        collected: bool = False

        try:
            content_head: bytes = await asyncio.to_thread(
                lambda: a_path.read_bytes()[:8192],
            )
            if is_binary(content_head):
                self._stats = CollectionStats(
                    total_scanned=self._stats.total_scanned,
                    collected=self._stats.collected,
                    skipped_binary=self._stats.skipped_binary + 1,
                    skipped_size=self._stats.skipped_size,
                    skipped_gitignore=self._stats.skipped_gitignore,
                    skipped_permission=self._stats.skipped_permission,
                    skipped_error=self._stats.skipped_error,
                    skipped_by_extension=self._stats.skipped_by_extension,
                    unknown_language=self._stats.unknown_language,
                )
            else:
                stat_result = await asyncio.to_thread(a_path.stat)
                size_bytes: int = stat_result.st_size
                if size_bytes > self._max_file_size:
                    self._stats = CollectionStats(
                        total_scanned=self._stats.total_scanned,
                        collected=self._stats.collected,
                        skipped_binary=self._stats.skipped_binary,
                        skipped_size=self._stats.skipped_size + 1,
                        skipped_gitignore=self._stats.skipped_gitignore,
                        skipped_permission=self._stats.skipped_permission,
                        skipped_error=self._stats.skipped_error,
                        skipped_by_extension=self._stats.skipped_by_extension,
                        unknown_language=self._stats.unknown_language,
                    )
                elif not self._filter.should_include(a_path):
                    self._stats = CollectionStats(
                        total_scanned=self._stats.total_scanned,
                        collected=self._stats.collected,
                        skipped_binary=self._stats.skipped_binary,
                        skipped_size=self._stats.skipped_size,
                        skipped_gitignore=self._stats.skipped_gitignore + 1,
                        skipped_permission=self._stats.skipped_permission,
                        skipped_error=self._stats.skipped_error,
                        skipped_by_extension=self._stats.skipped_by_extension,
                        unknown_language=self._stats.unknown_language,
                    )
                elif self._extensions is not None and a_path.suffix.lower() not in self._extensions:
                    self._stats = CollectionStats(
                        total_scanned=self._stats.total_scanned,
                        collected=self._stats.collected,
                        skipped_binary=self._stats.skipped_binary,
                        skipped_size=self._stats.skipped_size,
                        skipped_gitignore=self._stats.skipped_gitignore,
                        skipped_permission=self._stats.skipped_permission,
                        skipped_error=self._stats.skipped_error,
                        skipped_by_extension=self._stats.skipped_by_extension + 1,
                        unknown_language=self._stats.unknown_language,
                    )
                else:
                    a_emitted.add(a_path.resolve())
                    language: str = detect_language(a_path)
                    tokens: int = estimate_tokens_from_size(size_bytes)
                    role: FileRole = FileRole.UNKNOWN
                    if self._classifier is not None:
                        role = self._classifier.get_role(str(a_path))
                    rel_path: str = str(a_path.relative_to(a_root))
                    result = RepositoryFile(
                        path=rel_path,
                        language=language,
                        role=role,
                        tokens=tokens,
                        hash="",
                        size_bytes=size_bytes,
                    )
                    collected = True
                    self._stats = CollectionStats(
                        total_scanned=self._stats.total_scanned,
                        collected=self._stats.collected + 1,
                        skipped_binary=self._stats.skipped_binary,
                        skipped_size=self._stats.skipped_size,
                        skipped_gitignore=self._stats.skipped_gitignore,
                        skipped_permission=self._stats.skipped_permission,
                        skipped_error=self._stats.skipped_error,
                        skipped_by_extension=self._stats.skipped_by_extension,
                        unknown_language=self._stats.unknown_language + (1 if not language else 0),
                    )
        except PermissionError:
            logger.debug("Skipping %s (permission denied)", a_path)
            self._stats = CollectionStats(
                total_scanned=self._stats.total_scanned,
                collected=self._stats.collected,
                skipped_binary=self._stats.skipped_binary,
                skipped_size=self._stats.skipped_size,
                skipped_gitignore=self._stats.skipped_gitignore,
                skipped_permission=self._stats.skipped_permission + 1,
                skipped_error=self._stats.skipped_error,
                skipped_by_extension=self._stats.skipped_by_extension,
                unknown_language=self._stats.unknown_language,
            )
        except OSError:
            logger.warning("Skipping %s (stat/read error)", a_path)
            self._stats = CollectionStats(
                total_scanned=self._stats.total_scanned,
                collected=self._stats.collected,
                skipped_binary=self._stats.skipped_binary,
                skipped_size=self._stats.skipped_size,
                skipped_gitignore=self._stats.skipped_gitignore,
                skipped_permission=self._stats.skipped_permission,
                skipped_error=self._stats.skipped_error + 1,
                skipped_by_extension=self._stats.skipped_by_extension,
                unknown_language=self._stats.unknown_language,
            )

        if not collected:
            result = None

        return result

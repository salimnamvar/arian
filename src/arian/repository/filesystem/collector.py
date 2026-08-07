"""Async file collector for repository scanning."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
import logging
from pathlib import Path

from arian.domain.protocols import FileClassifierProtocol
from arian.domain.repository.models import RepositoryFile
from arian.domain.shared.enums import FileRole
from arian.domain.shared.language import detect_language
from arian.domain.shared.security import is_binary
from arian.domain.shared.tokenizer import estimate_tokens_from_size
from arian.infrastructure.config import LanguageConfig
from arian.infrastructure.gitignore_filter import GitignoreOptions
from arian.infrastructure.gitignore_filter import PathFilter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CollectionStats:
    """Transparent collection statistics.

    Invariant: ``total_scanned == collected + sum(all skipped_*)``
    AND ``sum(skipped_gitignore_by_pattern.values()) == skipped_gitignore``.

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
        skipped_gitignore_by_pattern: Map of gitignore pattern to the
            number of files it rejected. Aggregates to
            ``skipped_gitignore`` and is surfaced in the manifest so
            users can see *which* rule caused the skip.
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
    skipped_gitignore_by_pattern: dict[str, int] = field(default_factory=dict[str, int])


class FileCollector:
    """Collects repository files from the filesystem.

    Scans directories recursively, respects .gitignore patterns,
    and produces RepositoryFile metadata without loading content.

    Collection gate (in order):
        1. Binary check (is_binary on first 8KB)
        2. Size check (max_file_size)
        3. Gitignore/exclude check (with explicit-path override)
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
        a_max_file_size: int = 10 * 1024 * 1024,
        a_gitignore_options: GitignoreOptions = GitignoreOptions(),
        a_language_config: LanguageConfig = LanguageConfig(),
    ) -> None:
        """Initialize collector.

        Args:
            a_extensions: File extensions to include. None means all text files.
            a_exclude: Directory names to exclude.
            a_classifier: Optional file classifier for role detection.
            a_max_file_size: Maximum file size in bytes.
            a_gitignore_options: Static gitignore layer configuration
                passed through to the underlying :class:`PathFilter`.
            a_language_config: Language detection lookup tables.
        """
        self._extensions: frozenset[str] | None = a_extensions
        self._max_file_size: int = a_max_file_size
        self._language_config: LanguageConfig = a_language_config
        self._filter: PathFilter = PathFilter(a_exclude, a_gitignore_options)
        self._classifier: FileClassifierProtocol | None = a_classifier
        self._stats: CollectionStats = CollectionStats()

    @property
    def stats(self) -> CollectionStats:
        """Return collection statistics after collect() completes."""
        return self._stats

    def _bump(self, **changes: object) -> CollectionStats:
        """Return a new ``CollectionStats`` with the given fields changed.

        ``skipped_gitignore_by_pattern`` is the only mutable field on
        ``CollectionStats``; callers pass a new dict to replace it
        wholesale.
        """
        return replace(self._stats, **changes)

    def _record_gitignore_skip(self) -> CollectionStats:
        """Increment ``skipped_gitignore`` and attribute to a pattern.

        Uses ``PathFilter.last_matched_pattern`` (set by the last
        ``should_include`` call) to credit the offending rule. Falls
        back to ``"<exclude>"`` when the path was rejected by the
        directory-name set.
        """
        pattern: str = self._filter.last_matched_pattern or "<exclude>"
        tally: dict[str, int] = dict(self._stats.skipped_gitignore_by_pattern)
        tally[pattern] = tally.get(pattern, 0) + 1
        return self._bump(
            skipped_gitignore=self._stats.skipped_gitignore + 1,
            skipped_gitignore_by_pattern=tally,
        )

    async def collect(
        self,
        a_path: Path,
        a_root: Path | None = None,
        a_explicit_paths: frozenset[Path] = frozenset(),
    ) -> list[RepositoryFile]:
        """Collect file metadata from a path.

        Supports both individual files and directories. For directories,
        scans recursively. For files, collects metadata directly.

        Args:
            a_path: File or directory to scan.
            a_root: Root for computing relative paths. Defaults to a_path.
            a_explicit_paths: Paths (or subtrees) that always pass the
                gitignore gate for this call, mirroring ``git add -f``.
                When non-empty, any path that lives beneath one of
                these roots bypasses the ``.gitignore`` filter.

        Returns:
            List of RepositoryFile metadata objects.
        """
        self._filter.set_explicit_paths(a_explicit_paths)
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
        self._stats = self._bump(total_scanned=self._stats.total_scanned + 1)

        if a_path.resolve() in a_emitted:
            logger.debug("Skipping %s (duplicate)", a_path)
            self._stats = self._record_gitignore_skip()
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
                self._stats = self._bump(skipped_binary=self._stats.skipped_binary + 1)
            else:
                stat_result = await asyncio.to_thread(a_path.stat)
                size_bytes: int = stat_result.st_size
                if size_bytes > self._max_file_size:
                    self._stats = self._bump(skipped_size=self._stats.skipped_size + 1)
                elif not self._filter.should_include(a_path):
                    self._stats = self._record_gitignore_skip()
                elif self._extensions is not None and a_path.suffix.lower() not in self._extensions:
                    self._stats = self._bump(skipped_by_extension=self._stats.skipped_by_extension + 1)
                else:
                    a_emitted.add(a_path.resolve())
                    language: str = detect_language(a_path, self._language_config)
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
                    self._stats = self._bump(
                        collected=self._stats.collected + 1,
                        unknown_language=self._stats.unknown_language + (1 if not language else 0),
                    )
        except PermissionError:
            logger.debug("Skipping %s (permission denied)", a_path)
            self._stats = self._bump(skipped_permission=self._stats.skipped_permission + 1)
        except OSError:
            logger.warning("Skipping %s (stat/read error)", a_path)
            self._stats = self._bump(skipped_error=self._stats.skipped_error + 1)

        if not collected:
            result = None

        return result

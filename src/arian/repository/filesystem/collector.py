"""Async file collector for repository scanning."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from arian.domain.protocols import FileClassifierProtocol
from arian.domain.repository.models import RepositoryFile
from arian.domain.shared.enums import FileRole
from arian.domain.shared.language import detect_language
from arian.domain.shared.tokenizer import estimate_tokens_from_size
from arian.infrastructure.gitignore_filter import PathFilter

logger = logging.getLogger(__name__)


class FileCollector:
    """Collects repository files from the filesystem.

    Scans directories recursively, respects .gitignore patterns,
    and produces RepositoryFile metadata without loading content.

    Attributes:
        _extensions: File extensions to include.
        _filter: Path filter for gitignore and exclusion patterns.
        _classifier: File classifier for role detection.
    """

    def __init__(
        self,
        a_extensions: frozenset[str],
        a_exclude: frozenset[str],
        a_classifier: FileClassifierProtocol | None = None,
    ) -> None:
        """Initialize collector.

        Args:
            a_extensions: File extensions to include (e.g. {".py", ".md"}).
            a_exclude: Directory names to exclude.
            a_classifier: Optional file classifier for role detection.
        """
        self._extensions: frozenset[str] = a_extensions
        self._filter: PathFilter = PathFilter(a_exclude)
        self._classifier: FileClassifierProtocol | None = a_classifier

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
        if a_path.is_file():
            repo_file: RepositoryFile | None = await self._collect_file(a_path, emitted, root)
            if repo_file is not None:
                files.append(repo_file)
        else:
            await self._collect_directory(a_path, files, emitted, root)
        logger.debug("Collected %d files from %s", len(files), a_path)
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

        Uses stat() for file size and heuristic token estimation.
        Content is loaded later by ContextBuilder.load_content().

        Args:
            a_path: Path to the file.
            a_emitted: Set of already-emitted paths for deduplication.
            a_root: Root for computing relative paths.

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
                stat_result = await asyncio.to_thread(a_path.stat)
                size_bytes: int = stat_result.st_size
                a_emitted.add(a_path.resolve())
                tokens: int = estimate_tokens_from_size(size_bytes)
                language: str = detect_language(a_path)
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
            except OSError:
                logger.warning("Skipping %s (stat error)", a_path)

        return result

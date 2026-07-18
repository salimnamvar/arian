"""Filesystem collector for document collection.

Collects documents from the filesystem respecting filters and token counting.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
from pathlib import Path

from arian.domain.exceptions import InputNotFoundError
from arian.domain.models import Document
from arian.domain.models import InputSpec
from arian.infrastructure.gitignore_filter import PathFilter
from arian.infrastructure.language import detect_language

logger = logging.getLogger(__name__)


class FilesystemCollector:
    """Collects documents from filesystem paths.

    Attributes:
        _extensions (frozenset[str]): File extensions to include.
        _filter (PathFilter): Path filter instance.
    """

    def __init__(
        self,
        a_extensions: frozenset[str],
        a_exclude: frozenset[str],
        a_tokenizer: Callable[[str], int],
    ) -> None:
        """Initialize collector.

        Args:
            a_extensions: File extensions to include.
            a_exclude: Directory names to exclude.
            a_tokenizer: Token counting function.
        """
        self._extensions = a_extensions
        self._filter = PathFilter(a_exclude)
        self._tokenizer = a_tokenizer

    async def collect(self, a_inputs: list[InputSpec]) -> list[Document]:
        """Collect documents from input specifications.

        Args:
            a_inputs: List of input specifications (paths and tags).

        Returns:
            List[Document]: Collected documents.

        Raises:
            InputNotFoundError: If an input path does not exist.
        """
        documents: list[Document] = []
        emitted: set[Path] = set()

        logger.debug("Collecting from %d input(s)", len(a_inputs))

        for spec in a_inputs:
            path: Path = Path(spec.path)
            if path.is_file():
                doc: Document | None = await self._collect_file(path, emitted, spec.tag)
                if doc:
                    documents.append(doc)
            elif path.is_dir():
                dir_docs: list[Document] = await self._collect_directory(path, emitted, spec.tag)
                documents.extend(dir_docs)
            else:
                msg = f"Input path not found: {spec.path}"
                logger.warning("Input path not found: %s", spec.path)
                raise InputNotFoundError(
                    msg,
                    a_resource_name=spec.path,
                )

        logger.debug("Collected %d documents", len(documents))
        return documents

    async def _collect_file(
        self,
        a_path: Path,
        a_emitted: set[Path],
        a_tag: str,
    ) -> Document | None:
        """Collect single file.

        Args:
            a_path: Path to file.
            a_emitted: Set of already emitted paths (for dedup).
            a_tag: Grouping tag from InputSpec.

        Returns:
            Document if collected, None otherwise.
        """
        result: Document | None = None

        if a_path.suffix not in self._extensions:
            logger.debug("Skipping %s (extension not in filter)", a_path)
        elif a_path.resolve() in a_emitted:
            logger.debug("Skipping %s (duplicate)", a_path)
        else:
            try:
                content: str = await asyncio.to_thread(a_path.read_text, encoding="utf-8", errors="ignore")
                a_emitted.add(a_path.resolve())
                tokens: int = await asyncio.to_thread(self._tokenizer, content)
                result = Document(
                    path=str(a_path),
                    content=content,
                    tokens=tokens,
                    language=detect_language(a_path),
                    tag=a_tag,
                )
            except OSError:
                logger.warning("Skipping %s (read error)", a_path)

        return result

    async def _collect_directory(
        self,
        a_directory: Path,
        a_emitted: set[Path],
        a_tag: str,
    ) -> list[Document]:
        """Recursively collect from directory.

        Args:
            a_directory: Directory to collect from.
            a_emitted: Set of already emitted paths (for dedup).
            a_tag: Grouping tag from InputSpec.

        Returns:
            List[Document]: Collected documents.
        """
        documents: list[Document] = []
        entries: list[Path] | None = None

        try:
            entries = await asyncio.to_thread(
                lambda: sorted(a_directory.iterdir(), key=lambda p: (p.is_dir(), p.name)),
            )
        except OSError:
            logger.warning("Cannot read directory: %s", a_directory)
            entries = None

        if entries is not None:
            readme_files: list[Path] = [e for e in entries if e.is_file() and e.name.lower().startswith("readme")]
            common_dirs: list[Path] = [e for e in entries if e.is_dir() and e.name == "common"]
            other_files: list[Path] = [
                e
                for e in entries
                if e.is_file() and not e.name.lower().startswith("readme") and e.suffix in self._extensions
            ]
            other_dirs: list[Path] = [e for e in entries if e.is_dir() and e.name != "common"]

            for f in readme_files:
                doc = await self._collect_file(f, a_emitted, a_tag)
                if doc:
                    documents.append(doc)
            for d in common_dirs:
                documents.extend(await self._collect_directory(d, a_emitted, a_tag))
            for f in other_files:
                doc = await self._collect_file(f, a_emitted, a_tag)
                if doc:
                    documents.append(doc)
            for d in other_dirs:
                if self._filter.should_include(d):
                    documents.extend(await self._collect_directory(d, a_emitted, a_tag))

        return documents

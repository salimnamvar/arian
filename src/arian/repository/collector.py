"""Filesystem collector for document collection.

Collects documents from the filesystem respecting filters and token counting.
"""

from __future__ import annotations

from collections.abc import Callable
import logging
from pathlib import Path

from arian.domain.exceptions import InputNotFoundError
from arian.domain.models import Document
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

    def collect(self, a_inputs: list[str]) -> list[Document]:
        """Collect documents from input paths.

        Args:
            a_inputs: List of input paths (files or directories).

        Returns:
            List[Document]: Collected documents.

        Raises:
            InputNotFoundError: If an input path does not exist.
        """
        documents: list[Document] = []
        emitted: set[Path] = set()

        logger.debug("Collecting from %d input(s)", len(a_inputs))

        for path_str in a_inputs:
            path: Path = Path(path_str)
            if path.is_file():
                doc: Document | None = self._collect_file(path, emitted)
                if doc:
                    documents.append(doc)
            elif path.is_dir():
                documents.extend(self._collect_directory(path, emitted))
            else:
                msg = f"Input path not found: {path_str}"
                logger.warning("Input path not found: %s", path_str)
                raise InputNotFoundError(
                    msg,
                    a_resource_name=path_str,
                )

        logger.debug("Collected %d documents", len(documents))
        return documents

    def _collect_file(self, a_path: Path, a_emitted: set[Path]) -> Document | None:
        """Collect single file.

        Args:
            a_path: Path to file.
            a_emitted: Set of already emitted paths (for dedup).

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
                content: str = a_path.read_text(encoding="utf-8", errors="ignore")
                a_emitted.add(a_path.resolve())
                result = Document(
                    path=str(a_path),
                    content=content,
                    tokens=self._tokenizer(content),
                    language=detect_language(a_path),
                )
            except OSError:
                logger.warning("Skipping %s (read error)", a_path)

        return result

    def _collect_directory(self, a_directory: Path, a_emitted: set[Path]) -> list[Document]:
        """Recursively collect from directory.

        Args:
            a_directory: Directory to collect from.
            a_emitted: Set of already emitted paths (for dedup).

        Returns:
            List[Document]: Collected documents.
        """
        documents: list[Document] = []
        entries: list[Path] | None = None

        try:
            entries = sorted(a_directory.iterdir(), key=lambda p: (p.is_dir(), p.name))
        except OSError:
            logger.warning("Cannot read directory: %s", a_directory)
            entries = None

        if entries is not None:
            # Process: readme files, common dirs, other files, other dirs
            readme_files: list[Path] = [e for e in entries if e.is_file() and e.name.lower().startswith("readme")]
            common_dirs: list[Path] = [e for e in entries if e.is_dir() and e.name == "common"]
            other_files: list[Path] = [
                e
                for e in entries
                if e.is_file() and not e.name.lower().startswith("readme") and e.suffix in self._extensions
            ]
            other_dirs: list[Path] = [e for e in entries if e.is_dir() and e.name != "common"]

            for f in readme_files:
                if doc := self._collect_file(f, a_emitted):
                    documents.append(doc)
            for d in common_dirs:
                documents.extend(self._collect_directory(d, a_emitted))
            for f in other_files:
                if doc := self._collect_file(f, a_emitted):
                    documents.append(doc)
            for d in other_dirs:
                if self._filter.should_include(d):
                    documents.extend(self._collect_directory(d, a_emitted))

        return documents

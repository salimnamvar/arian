"""Filesystem collector for document collection.

Collects documents from the filesystem respecting filters and token counting.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from arian.domain.exceptions import InputNotFoundError
from arian.domain.models import Document
from arian.infrastructure.gitignore_filter import PathFilter
from arian.renderer.language import detect_language


class FilesystemCollector:
    """Collects documents from filesystem paths.

    Attributes:
        _extensions (frozenset[str]): File extensions to include.
        _filter (PathFilter): Path filter instance.
        _emitted (set[Path]): Set of already emitted paths.
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
        self._emitted: set[Path] = set()
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
        self._emitted.clear()
        documents: list[Document] = []

        for path_str in a_inputs:
            path: Path = Path(path_str)
            if path.is_file():
                doc: Document | None = self._collect_file(path)
                if doc:
                    documents.append(doc)
            elif path.is_dir():
                documents.extend(self._collect_directory(path))
            else:
                msg = f"Input path not found: {path_str}"
                raise InputNotFoundError(
                    msg,
                    a_resource_name=path_str,
                )

        return documents

    def _collect_file(self, a_path: Path) -> Document | None:
        """Collect single file.

        Args:
            a_path: Path to file.

        Returns:
            Document if collected, None otherwise.
        """
        if a_path.suffix not in self._extensions:
            return None

        resolved: Path = a_path.resolve()
        if resolved in self._emitted:
            return None

        try:
            content: str = a_path.read_text(encoding="utf-8", errors="ignore")
            self._emitted.add(resolved)
            return Document(
                path=str(a_path),
                content=content,
                tokens=self._tokenizer(content),
                language=detect_language(a_path),
            )
        except OSError:
            return None

    def _collect_directory(self, a_directory: Path) -> list[Document]:
        """Recursively collect from directory.

        Args:
            a_directory: Directory to collect from.

        Returns:
            List[Document]: Collected documents.
        """
        documents: list[Document] = []
        entries: list[Path]

        try:
            entries = sorted(a_directory.iterdir(), key=lambda p: (p.is_dir(), p.name))
        except OSError:
            return documents

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
            if doc := self._collect_file(f):
                documents.append(doc)
        for d in common_dirs:
            documents.extend(self._collect_directory(d))
        for f in other_files:
            if doc := self._collect_file(f):
                documents.append(doc)
        for d in other_dirs:
            if self._filter.should_include(d):
                documents.extend(self._collect_directory(d))

        return documents

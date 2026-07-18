"""Repository domain models for Arian."""

from __future__ import annotations

from dataclasses import dataclass

from arian.domain.shared.enums import DependencyKind
from arian.domain.shared.enums import FileRole
from arian.domain.shared.enums import SymbolKind


@dataclass(frozen=True)
class Repository:
    """Top-level repository representation.

    Attributes:
        path: Root path of the repository.
        name: Repository name.
        files: Tuple of repository files.
        modules: Tuple of logical modules.
    """

    path: str
    name: str
    files: tuple[RepositoryFile, ...] = ()
    modules: tuple[Module, ...] = ()


@dataclass(frozen=True)
class RepositoryFile:
    """File metadata without content.

    Attributes:
        path: Relative file path.
        language: Detected language identifier.
        role: File role in the repository.
        tokens: Token count of the file content.
        hash: Content hash for cache invalidation.
    """

    path: str
    language: str
    role: FileRole
    tokens: int
    hash: str


@dataclass(frozen=True)
class FileContent:
    """File content loaded separately from metadata.

    Attributes:
        path: Relative file path.
        content: Raw file content.
        hash: Content hash matching the RepositoryFile.
    """

    path: str
    content: str
    hash: str


@dataclass(frozen=True)
class Module:
    """Logical grouping of files.

    Attributes:
        name: Module name.
        path: Module root path.
        files: Tuple of file paths belonging to this module.
    """

    name: str
    path: str
    files: tuple[str, ...] = ()


@dataclass(frozen=True)
class Symbol:
    """Extracted code symbol.

    Attributes:
        name: Symbol name.
        kind: Symbol kind (class, function, method).
        file_path: File containing this symbol.
        signature: Full signature string.
        docstring: Associated docstring.
        line_start: Starting line number.
        line_end: Ending line number.
    """

    name: str
    kind: SymbolKind
    file_path: str
    signature: str
    docstring: str = ""
    line_start: int = 0
    line_end: int = 0


@dataclass(frozen=True)
class Dependency:
    """Relationship between files.

    Attributes:
        source_path: Source file path.
        target_path: Target file path.
        kind: Dependency kind (import, call, inherit).
    """

    source_path: str
    target_path: str
    kind: DependencyKind

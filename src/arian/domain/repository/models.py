"""Repository domain models for Arian."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

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
        tokens: Estimated token count (heuristic, not exact).
        hash: Content hash for cache invalidation. Empty string until content is loaded.
        size_bytes: File size in bytes from stat().
    """

    path: str
    language: str
    role: FileRole
    tokens: int
    hash: str
    size_bytes: int = 0


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


@dataclass(frozen=True)
class CollectionStats:
    """Transparent collection statistics (domain value object).

    Lives in the domain so Application and Service layers can depend on
    the type without importing repository implementations (CSR).

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
            number of files it rejected.
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

"""Path filtering using pathspec for .gitignore support."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pathspec


class PathFilter:
    """Filter paths using gitignore patterns.

    Attributes:
        _exclude (frozenset[str]): Directory names to exclude.
        _gitignore_patterns (Any | None): Loaded gitignore patterns.
    """

    def __init__(self, a_exclude: frozenset[str], a_gitignore: bool = True) -> None:
        """Initialize path filter.

        Args:
            a_exclude: Directory names to exclude.
            a_gitignore: Whether to respect .gitignore files.
        """
        self._exclude = a_exclude
        self._gitignore_patterns: Any | None = self._load_gitignore() if a_gitignore else None

    def _load_gitignore(self) -> Any | None:
        """Load .gitignore patterns if present.

        Returns:
            Any | None: Loaded patterns or None.
        """
        gitignore_path: Path = Path.cwd() / ".gitignore"
        result: Any | None = None
        if gitignore_path.exists():
            content: str = gitignore_path.read_text()
            result = pathspec.PathSpec.from_lines("gitignore", content.splitlines())
        return result

    def should_include(self, a_path: Path) -> bool:
        """Check if path should be included.

        Args:
            a_path: Path to check.

        Returns:
            bool: True if path should be included.
        """
        include: bool = True

        # Check excluded directories
        if any(part in self._exclude for part in a_path.parts):
            include = False
        elif self._gitignore_patterns:
            try:
                relative: str = str(a_path.relative_to(Path.cwd()))
                if self._gitignore_patterns.match_file(relative):
                    include = False
            except ValueError:
                pass

        return include

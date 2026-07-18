"""Path filtering using pathspec for .gitignore support."""

from __future__ import annotations

from pathlib import Path

import pathspec


class PathFilter:
    """Filter paths using gitignore patterns.

    Attributes:
        _exclude (FrozenSet[str]): Directory names to exclude.
        _gitignore_patterns (Optional[pathspec.PathSpec]): Loaded gitignore patterns.
    """

    def __init__(self, a_exclude: frozenset[str], a_gitignore: bool = True) -> None:
        """Initialize path filter.

        Args:
            a_exclude: Directory names to exclude.
            a_gitignore: Whether to respect .gitignore files.
        """
        self._exclude = a_exclude
        self._gitignore_patterns: pathspec.PathSpec | None = self._load_gitignore() if a_gitignore else None

    def _load_gitignore(self) -> pathspec.PathSpec | None:
        """Load .gitignore patterns if present.

        Returns:
            Optional[pathspec.PathSpec]: Loaded patterns or None.
        """
        gitignore_path: Path = Path.cwd() / ".gitignore"
        content: str
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            result: pathspec.PathSpec | None = pathspec.PathSpec.from_lines("gitwildmatch", content.splitlines())
            return result
        return None

    def should_include(self, a_path: Path) -> bool:
        """Check if path should be included.

        Args:
            a_path: Path to check.

        Returns:
            bool: True if path should be included.
        """
        # Check excluded directories
        if any(part in self._exclude for part in a_path.parts):
            return False

        # Check gitignore
        if self._gitignore_patterns:
            try:
                relative: str = str(a_path.relative_to(Path.cwd()))
                if self._gitignore_patterns.match_file(relative):
                    return False
            except ValueError:
                pass

        return True

"""Path filter protocol — domain interface for path filtering decisions.

Implementations decide which filesystem paths to include or exclude
during repository scanning. The filtering strategy (gitignore, patterns,
etc.) is an infrastructure concern; the decision interface is domain.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class PathFilterProtocol(Protocol):
    """Protocol for path inclusion decisions.

    Implementations check whether a given path should be included
    in repository scanning based on exclusion rules and patterns.
    """

    def should_include(self, a_path: Path) -> bool:
        """Check if path should be included in scanning.

        Args:
            a_path: Path to evaluate.

        Returns:
            True if path should be included.
        """
        ...

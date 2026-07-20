"""Language detection for document rendering.

Re-exports from domain.shared.language for backward compatibility.
"""

from __future__ import annotations

from arian.domain.shared.language import detect_language

__all__ = ["detect_language"]

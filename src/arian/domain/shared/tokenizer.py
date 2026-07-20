"""Tokenizer protocol and utilities — domain interface for token counting.

Token counting is a domain concern (budget enforcement), but the
tiktoken implementation is an infrastructure detail. This protocol
defines the interface that the domain depends on.
"""

from __future__ import annotations

from typing import Protocol


def estimate_tokens_from_size(a_size_bytes: int) -> int:
    """Estimate token count from file size without reading content.

    Heuristic: ~4 characters per token for code. Uses conservative
    overestimate to ensure budget enforcement is safe.

    Args:
        a_size_bytes: File size in bytes.

    Returns:
        Estimated token count (minimum 1).
    """
    return max(1, a_size_bytes // 4)


class TokenizerProtocol(Protocol):
    """Protocol for counting tokens in text."""

    def count_tokens(self, a_text: str, a_model: str = "gpt-4") -> int:
        """Count tokens in text.

        Args:
            a_text: Text to count tokens for.
            a_model: Model name for tokenizer selection.

        Returns:
            Token count.
        """
        ...

"""Tokenizer protocol — domain interface for token counting.

Token counting is a domain concern (budget enforcement), but the
tiktoken implementation is an infrastructure detail. This protocol
defines the interface that the domain depends on.
"""

from __future__ import annotations

from typing import Protocol


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

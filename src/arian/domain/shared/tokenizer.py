"""Tokenizer utilities — domain interface for token counting.

Token counting is a domain concern (budget enforcement), but the
tiktoken implementation is an infrastructure detail.
"""

from __future__ import annotations


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

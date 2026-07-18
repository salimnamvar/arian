"""Token counting using tiktoken."""

from __future__ import annotations

from functools import lru_cache

import tiktoken


@lru_cache(maxsize=8)
def _get_encoding(a_model: str) -> tiktoken.Encoding:
    """Get encoding for a model, cached for performance.

    Args:
        a_model: Model name for tokenizer.

    Returns:
        tiktoken.Encoding: The encoding instance.
    """
    encoding: tiktoken.Encoding
    try:
        encoding = tiktoken.encoding_for_model(a_model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return encoding


def count_tokens(a_text: str, a_model: str = "gpt-4") -> int:
    """Count tokens in text using tiktoken.

    Args:
        a_text (str): Text to count tokens for.
        a_model (str): Model name for tokenizer.

    Returns:
        int: Token count.
    """
    enc: tiktoken.Encoding = _get_encoding(a_model)
    return len(enc.encode(a_text))

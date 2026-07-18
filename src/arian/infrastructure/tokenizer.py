"""Token counting using tiktoken."""

from __future__ import annotations

import tiktoken


def count_tokens(a_text: str, a_model: str = "gpt-4") -> int:
    """Count tokens in text using tiktoken.

    Args:
        a_text (str): Text to count tokens for.
        a_model (str): Model name for tokenizer.

    Returns:
        int: Token count.
    """
    enc: tiktoken.Encoding
    try:
        enc = tiktoken.encoding_for_model(a_model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(a_text))

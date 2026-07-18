"""Splitter pipeline for Arian.

Splits documents into chunks respecting token limits.
"""

from __future__ import annotations

from arian.domain.models import Document


def split_documents(
    a_documents: list[Document],
    a_max_tokens: int | None,
) -> list[list[Document]]:
    """Split documents into chunks respecting token limit.

    Args:
        a_documents: Documents to split.
        a_max_tokens: Maximum tokens per chunk.

    Returns:
        List of document chunks.
    """
    chunks: list[list[Document]]
    if a_max_tokens is None:
        chunks = [a_documents]
    else:
        chunks = []
        current_chunk: list[Document] = []
        current_tokens: int = 0

        for doc in a_documents:
            if current_tokens + doc.tokens > a_max_tokens and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [doc]
                current_tokens = doc.tokens
            else:
                current_chunk.append(doc)
                current_tokens += doc.tokens

        if current_chunk:
            chunks.append(current_chunk)

    return chunks

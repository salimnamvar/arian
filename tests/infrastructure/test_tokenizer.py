"""Unit tests for infrastructure layer."""

from __future__ import annotations

from arian.infrastructure.tokenizer import count_tokens


def test_count_tokens_basic() -> None:
    """Test basic token counting."""
    result: int = count_tokens("hello world")
    assert result > 0


def test_count_tokens_empty_string() -> None:
    """Test token counting empty string."""
    result: int = count_tokens("")
    assert result == 0


def test_count_tokens_nonexistent_model() -> None:
    """Test token counting with nonexistent model falls back to cl100k_base."""
    # Should not raise, uses fallback encoding
    result: int = count_tokens("hello world", a_model="nonexistent-model")
    assert result > 0


def test_count_tokens_gpt4_model() -> None:
    """Test token counting with GPT-4 model."""
    result: int = count_tokens("hello world", a_model="gpt-4")
    assert result > 0

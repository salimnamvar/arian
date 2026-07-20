"""Tests for domain shared constants."""

from __future__ import annotations

from arian.domain.shared.constants import DEFAULT_MAX_CONCURRENT_LOADS
from arian.domain.shared.constants import MAX_COLLECTED_FILES
from arian.domain.shared.constants import MAX_FILE_SIZE_BYTES
from arian.domain.shared.constants import MAX_TOKEN_BUDGET


def test_max_file_size_is_10mb() -> None:
    """Verify MAX_FILE_SIZE_BYTES is 10MB."""
    assert MAX_FILE_SIZE_BYTES == 10 * 1024 * 1024


def test_max_collected_files_limit() -> None:
    """Verify MAX_COLLECTED_FILES is a reasonable limit."""
    assert MAX_COLLECTED_FILES == 10_000
    assert MAX_COLLECTED_FILES > 0


def test_max_token_budget_limit() -> None:
    """Verify MAX_TOKEN_BUDGET is a reasonable limit."""
    assert MAX_TOKEN_BUDGET == 1_000_000
    assert MAX_TOKEN_BUDGET > 0


def test_default_max_concurrent_loads() -> None:
    """Verify default concurrent load limit is positive and bounded."""
    assert DEFAULT_MAX_CONCURRENT_LOADS == 10
    assert DEFAULT_MAX_CONCURRENT_LOADS > 0

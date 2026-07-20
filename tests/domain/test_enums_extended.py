"""Unit tests for ConcurrencyPolicy enum."""

from __future__ import annotations

from arian.domain.shared.enums import ConcurrencyPolicy


class TestConcurrencyPolicy:
    """Tests for ConcurrencyPolicy enum."""

    def test_sequential_value(self) -> None:
        """Verify SEQUENTIAL has correct value."""
        assert ConcurrencyPolicy.SEQUENTIAL.value == "sequential"

    def test_concurrent_value(self) -> None:
        """Verify CONCURRENT has correct value."""
        assert ConcurrencyPolicy.CONCURRENT.value == "concurrent"

    def test_bounded_value(self) -> None:
        """Verify BOUNDED has correct value."""
        assert ConcurrencyPolicy.BOUNDED.value == "bounded"

    def test_all_members_present(self) -> None:
        """Verify all expected members exist."""
        members = list(ConcurrencyPolicy)
        assert len(members) == 3
        assert ConcurrencyPolicy.SEQUENTIAL in members
        assert ConcurrencyPolicy.CONCURRENT in members
        assert ConcurrencyPolicy.BOUNDED in members

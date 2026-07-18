"""Tests for domain enums."""

from arian.domain.enums import OutputMode


def test_output_mode_values() -> None:
    assert OutputMode.SEPARATE is not OutputMode.AGGREGATE


def test_output_mode_is_enum() -> None:
    assert len(OutputMode) == 2
    assert set(OutputMode) == {OutputMode.SEPARATE, OutputMode.AGGREGATE}

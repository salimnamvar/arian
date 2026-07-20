"""Unit tests for logging filters."""

from __future__ import annotations

import logging

from arian.bootstrap.logging_filters import RunContextFilter


class TestRunContextFilter:
    """Tests for RunContextFilter."""

    def test_run_id_is_8_chars(self) -> None:
        f = RunContextFilter()
        assert len(f.run_id) == 8

    def test_run_id_is_hex(self) -> None:
        f = RunContextFilter()
        int(f.run_id, 16)

    def test_filter_attaches_run_id(self) -> None:
        f = RunContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test",
            args=None,
            exc_info=None,
        )
        result = f.filter(record)
        assert result is True
        assert record.run_id == f.run_id  # type: ignore[attr-defined]

    def test_same_run_id_across_records(self) -> None:
        f = RunContextFilter()
        r1 = logging.LogRecord("t", logging.INFO, "", 0, "m", None, None)
        r2 = logging.LogRecord("t", logging.INFO, "", 0, "m", None, None)
        f.filter(r1)
        f.filter(r2)
        assert r1.run_id == r2.run_id  # type: ignore[attr-defined]

    def test_different_filters_get_different_ids(self) -> None:
        f1 = RunContextFilter()
        f2 = RunContextFilter()
        assert f1.run_id != f2.run_id

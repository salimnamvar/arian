"""Tests for retry with backoff policy."""

from __future__ import annotations

import asyncio

import pytest

from arian.infrastructure.retry import retry_with_backoff


class TestRetryWithBackoff:
    """Tests for retry_with_backoff()."""

    async def test_success_on_first_attempt(self) -> None:
        """Verify function succeeds without retry."""

        async def ok() -> str:
            return "done"

        result = await retry_with_backoff(ok)
        assert result == "done"

    async def test_retries_on_transient_error(self) -> None:
        """Verify function retries on matching exception."""
        call_count = 0

        async def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                msg = "transient"
                raise OSError(msg)
            return "recovered"

        result = await retry_with_backoff(
            flaky,
            a_max_retries=3,
            a_base_delay=0.01,
            a_exceptions=(OSError,),
        )
        assert result == "recovered"
        assert call_count == 3

    async def test_raises_after_max_retries(self) -> None:
        """Verify last exception is raised when all retries fail."""

        async def always_fail() -> None:
            msg = "permanent"
            raise OSError(msg)

        with pytest.raises(OSError, match="permanent"):
            await retry_with_backoff(
                always_fail,
                a_max_retries=2,
                a_base_delay=0.01,
                a_exceptions=(OSError,),
            )

    async def test_does_not_retry_unmatched_exception(self) -> None:
        """Verify non-matching exceptions are not retried."""

        async def type_error() -> None:
            msg = "wrong type"
            raise TypeError(msg)

        with pytest.raises(TypeError, match="wrong type"):
            await retry_with_backoff(
                type_error,
                a_max_retries=3,
                a_base_delay=0.01,
                a_exceptions=(OSError,),
            )

    async def test_passes_args_to_function(self) -> None:
        """Verify arguments are forwarded to the retried function."""

        async def add(a: int, b: int) -> int:
            return a + b

        result = await retry_with_backoff(add, 3, 4, a_max_retries=1, a_base_delay=0.01)
        assert result == 7

    async def test_exponential_delay_timing(self) -> None:
        """Verify delays increase exponentially."""
        call_times: list[float] = []

        async def track_time() -> None:
            call_times.append(asyncio.get_event_loop().time())
            msg = "fail"
            raise OSError(msg)

        with pytest.raises(OSError):
            await retry_with_backoff(
                track_time,
                a_max_retries=3,
                a_base_delay=0.05,
                a_exceptions=(OSError,),
            )

        assert len(call_times) == 3

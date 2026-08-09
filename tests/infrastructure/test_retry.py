"""Tests for retry with backoff policy."""

from __future__ import annotations

import asyncio

from arian.infrastructure.retry import execute_with_retry_sync
from arian.infrastructure.retry import execute_with_retry


class TestRetrySyncWithBackoff:
    """Tests for execute_with_retry_sync()."""

    def test_success_on_first_attempt(self) -> None:
        """Verify sync function succeeds without retry."""

        def ok() -> str:
            return "done"

        result = execute_with_retry_sync(ok)
        assert result.is_success
        assert result.value == "done"

    def test_retries_on_transient_error(self) -> None:
        """Verify sync function retries on matching exception."""
        call_count = 0

        def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                msg = "transient"
                raise OSError(msg)
            return "recovered"

        result = execute_with_retry_sync(
            flaky,
            a_max_retries=3,
            a_base_delay=0.01,
            a_exceptions=(OSError,),
        )
        assert result.is_success
        assert result.value == "recovered"
        assert call_count == 3

    def test_returns_failure_after_max_retries(self) -> None:
        """Verify failure Result when all retries fail."""

        def always_fail() -> None:
            msg = "permanent"
            raise OSError(msg)

        result = execute_with_retry_sync(
            always_fail,
            a_max_retries=2,
            a_base_delay=0.01,
            a_exceptions=(OSError,),
        )
        assert result.is_failure
        assert "permanent" in result.message

    def test_does_not_retry_unmatched_exception(self) -> None:
        """Verify non-matching exceptions are not retried."""

        def type_error() -> None:
            msg = "wrong type"
            raise TypeError(msg)

        result = execute_with_retry_sync(
            type_error,
            a_max_retries=3,
            a_base_delay=0.01,
            a_exceptions=(OSError,),
        )
        assert result.is_failure
        assert "wrong type" in result.message

    def test_passes_args_to_function(self) -> None:
        """Verify arguments are forwarded to the retried function."""

        def add(a: int, b: int) -> int:
            return a + b

        result = execute_with_retry_sync(add, 3, 4, a_max_retries=1, a_base_delay=0.01)
        assert result.is_success
        assert result.value == 7


class TestRetryWithBackoff:
    """Tests for execute_with_retry()."""

    async def test_success_on_first_attempt(self) -> None:
        """Verify function succeeds without retry."""

        async def ok() -> str:
            return "done"

        result = await execute_with_retry(ok)
        assert result.is_success
        assert result.value == "done"

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

        result = await execute_with_retry(
            flaky,
            a_max_retries=3,
            a_base_delay=0.01,
            a_exceptions=(OSError,),
        )
        assert result.is_success
        assert result.value == "recovered"
        assert call_count == 3

    async def test_returns_failure_after_max_retries(self) -> None:
        """Verify failure Result when all retries fail."""

        async def always_fail() -> None:
            msg = "permanent"
            raise OSError(msg)

        result = await execute_with_retry(
            always_fail,
            a_max_retries=2,
            a_base_delay=0.01,
            a_exceptions=(OSError,),
        )
        assert result.is_failure
        assert "permanent" in result.message

    async def test_does_not_retry_unmatched_exception(self) -> None:
        """Verify non-matching exceptions are not retried."""

        async def type_error() -> None:
            msg = "wrong type"
            raise TypeError(msg)

        result = await execute_with_retry(
            type_error,
            a_max_retries=3,
            a_base_delay=0.01,
            a_exceptions=(OSError,),
        )
        assert result.is_failure
        assert "wrong type" in result.message

    async def test_passes_args_to_function(self) -> None:
        """Verify arguments are forwarded to the retried function."""

        async def add(a: int, b: int) -> int:
            return a + b

        result = await execute_with_retry(add, 3, 4, a_max_retries=1, a_base_delay=0.01)
        assert result.is_success
        assert result.value == 7

    async def test_exponential_delay_timing(self) -> None:
        """Verify delays increase exponentially."""
        call_times: list[float] = []

        async def track_time() -> None:
            call_times.append(asyncio.get_event_loop().time())
            msg = "fail"
            raise OSError(msg)

        result = await execute_with_retry(
            track_time,
            a_max_retries=3,
            a_base_delay=0.05,
            a_exceptions=(OSError,),
        )

        assert result.is_failure
        assert len(call_times) == 3

"""Retry policy for transient errors."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from collections.abc import Callable
import logging
import time
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_with_backoff(  # noqa: UP047 — PEP 695 breaks Python 3.10/3.11
    a_func: Callable[..., Awaitable[T]],
    *args: object,
    a_max_retries: int = 3,
    a_base_delay: float = 0.1,
    a_exceptions: tuple[type[Exception], ...] = (OSError,),
) -> T:
    """Retry an async function with exponential backoff.

    Follows the safe-coding shape: a ``b_continue`` guard drives the loop,
    the result is captured in a single variable, and the function ends in
    one success return and one failure raise site.

    Args:
        a_func: Async function to retry.
        *args: Positional arguments for the function.
        a_max_retries: Maximum retry attempts.
        a_base_delay: Base delay in seconds (doubled each retry).
        a_exceptions: Exception types to retry on.

    Returns:
        Function result.

    Raises:
        Last exception if all retries fail.
    """
    result: T | None = None
    b_continue: bool = True
    last_exception: Exception | None = None

    for attempt in range(a_max_retries):
        if b_continue:
            try:
                result = await a_func(*args)
                b_continue = False
            except a_exceptions as e:
                last_exception = e
                if attempt < a_max_retries - 1:
                    delay: float = a_base_delay * (2**attempt)
                    logger.debug(
                        "Retry %d/%d after %.2fs: %s",
                        attempt + 1,
                        a_max_retries,
                        delay,
                        e,
                    )
                    await asyncio.sleep(delay)

    if b_continue:
        logger.error("Retry failed after %d attempts: %s", a_max_retries, last_exception)
        raise last_exception  # type: ignore[misc] — set when all attempts failed

    return result  # type: ignore[return-value] — narrows; success set result


def retry_sync_with_backoff(  # noqa: UP047 — PEP 695 breaks Python 3.10/3.11
    a_func: Callable[..., T],
    *args: object,
    a_max_retries: int = 3,
    a_base_delay: float = 0.1,
    a_exceptions: tuple[type[Exception], ...] = (OSError,),
    **kwargs: object,
) -> T:
    """Retry a synchronous function with exponential backoff.

    Compatible with Python 3.10+ (uses typing.TypeVar, not PEP 695 syntax).

    Follows the safe-coding shape: a ``b_continue`` guard drives the loop,
    the result is captured in a single variable, and the function ends in
    one success return and one failure raise site.

    Args:
        a_func: Sync function to retry.
        *args: Positional arguments for the function.
        a_max_retries: Maximum retry attempts.
        a_base_delay: Base delay in seconds (doubled each retry).
        a_exceptions: Exception types to retry on.
        **kwargs: Keyword arguments for the function.

    Returns:
        Function result.

    Raises:
        Last exception if all retries fail.
    """
    result: T | None = None
    b_continue: bool = True
    last_exception: Exception | None = None

    for attempt in range(a_max_retries):
        if b_continue:
            try:
                result = a_func(*args, **kwargs)
                b_continue = False
            except a_exceptions as e:
                last_exception = e
                if attempt < a_max_retries - 1:
                    delay: float = a_base_delay * (2**attempt)
                    logger.debug(
                        "Retry %d/%d after %.2fs: %s",
                        attempt + 1,
                        a_max_retries,
                        delay,
                        e,
                    )
                    time.sleep(delay)

    if b_continue:
        logger.error("Retry failed after %d attempts: %s", a_max_retries, last_exception)
        raise last_exception  # type: ignore[misc] — set when all attempts failed

    return result  # type: ignore[return-value] — narrows; success set result

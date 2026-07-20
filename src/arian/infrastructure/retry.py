"""Retry policy for transient errors."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
import time
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_with_backoff(
    a_func: object,
    *args: object,
    a_max_retries: int = 3,
    a_base_delay: float = 0.1,
    a_exceptions: tuple[type[Exception], ...] = (OSError,),
) -> object:
    """Retry an async function with exponential backoff.

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
    last_exception: Exception | None = None
    for attempt in range(a_max_retries):
        try:
            return await a_func(*args)  # type: ignore[misc]
        except a_exceptions as e:
            last_exception = e
            if attempt < a_max_retries - 1:
                delay = a_base_delay * (2**attempt)
                logger.debug(
                    "Retry %d/%d after %.2fs: %s",
                    attempt + 1,
                    a_max_retries,
                    delay,
                    e,
                )
                await asyncio.sleep(delay)
    if last_exception is None:
        msg = "retry_with_backoff failed without capturing an exception"
        raise RuntimeError(msg)
    raise last_exception


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
    last_exception: Exception | None = None
    for attempt in range(a_max_retries):
        try:
            return a_func(*args, **kwargs)
        except a_exceptions as e:
            last_exception = e
            if attempt < a_max_retries - 1:
                delay = a_base_delay * (2**attempt)
                logger.debug(
                    "Retry %d/%d after %.2fs: %s",
                    attempt + 1,
                    a_max_retries,
                    delay,
                    e,
                )
                time.sleep(delay)
    if last_exception is None:
        msg = "retry_sync_with_backoff failed without capturing an exception"
        raise RuntimeError(msg)
    raise last_exception

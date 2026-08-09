"""Retry policy for transient errors."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from collections.abc import Callable
import logging
import time
from typing import TypeVar

from arian.domain.shared.result import Result

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def execute_with_retry(  # noqa: UP047 — PEP 695 breaks Python 3.10/3.11  # a-prefix-ignore: generic variadic pass-through
    a_func: Callable[..., Awaitable[T]],
    *args: object,
    a_max_retries: int = 3,
    a_base_delay: float = 0.1,
    a_exceptions: tuple[type[Exception], ...] = (OSError,),
) -> Result[T]:
    """Retry an async function with exponential backoff.

    Follows the safe-coding shape: a ``b_continue`` guard drives the loop,
    the result is captured in a single variable, and the function returns
    exactly once with a Result[T].

    Args:
        a_func: Async function to retry.
        *args: Positional arguments for the function.
        a_max_retries: Maximum retry attempts.
        a_base_delay: Base delay in seconds (doubled each retry).
        a_exceptions: Exception types to retry on.

    Returns:
        Result[T] with the function result or failure message.
    """
    result: Result[T] = Result.failure("uninitialized")
    b_continue: bool = True
    last_exception: Exception | None = None

    for attempt in range(a_max_retries):
        if b_continue:
            try:
                value: T = await a_func(*args)
                result = Result.success(value)
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
            except asyncio.CancelledError:
                result = Result.failure("Operation cancelled")
                b_continue = False
            except Exception as e:
                last_exception = e
                logger.exception("Unexpected error during retry")
                result = Result.failure(f"Unexpected error: {e}")
                b_continue = False

    if b_continue:
        msg = f"Retry failed after {a_max_retries} attempts: {last_exception}"
        logger.error("%s", msg)
        result = Result.failure(msg)

    return result


def execute_with_retry_sync(  # noqa: UP047 — PEP 695 breaks Python 3.10/3.11  # a-prefix-ignore: generic variadic pass-through
    a_func: Callable[..., T],
    *args: object,
    a_max_retries: int = 3,
    a_base_delay: float = 0.1,
    a_exceptions: tuple[type[Exception], ...] = (OSError,),
    **kwargs: object,
) -> Result[T]:
    """Retry a synchronous function with exponential backoff.

    Compatible with Python 3.10+ (uses typing.TypeVar, not PEP 695 syntax).

    Follows the safe-coding shape: a ``b_continue`` guard drives the loop,
    the result is captured in a single variable, and the function returns
    exactly once with a Result[T].

    Args:
        a_func: Sync function to retry.
        *args: Positional arguments for the function.
        a_max_retries: Maximum retry attempts.
        a_base_delay: Base delay in seconds (doubled each retry).
        a_exceptions: Exception types to retry on.
        **kwargs: Keyword arguments for the function.

    Returns:
        Result[T] with the function result or failure message.
    """
    result: Result[T] = Result.failure("uninitialized")
    b_continue: bool = True
    last_exception: Exception | None = None

    for attempt in range(a_max_retries):
        if b_continue:
            try:
                value: T = a_func(*args, **kwargs)
                result = Result.success(value)
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
            except Exception as e:
                last_exception = e
                logger.exception("Unexpected error during retry")
                result = Result.failure(f"Unexpected error: {e}")
                b_continue = False

    if b_continue:
        msg = f"Retry failed after {a_max_retries} attempts: {last_exception}"
        logger.error("%s", msg)
        result = Result.failure(msg)

    return result

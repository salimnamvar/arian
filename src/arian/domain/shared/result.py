"""Generic Result type for safe-coding compliance.

Every function SHALL return a typed Result[T] with is_success, value, and message.
This eliminates the need for per-operation Result classes (DRY principle).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class Result[T]:
    """Immutable structured result returned by all functions.

    Result[T] carries either a success value or a failure message.
    Success results have is_success == True.
    Failure results have is_success == False and value == None.

    Attributes:
        value: The success value, or None on failure.
        message: Human-readable message (error details on failure).
    """

    def __init__(
        self,
        *,
        a_is_success: bool,
        a_value: T | None = None,
        a_message: str = "",
    ) -> None:
        self.is_success: bool = a_is_success
        self.value: T | None = a_value
        self.message: str = a_message

    @property
    def is_failure(self) -> bool:
        """Return whether the operation failed."""
        return not self.is_success

    def __bool__(self) -> bool:
        """True when the result represents success."""
        return self.is_success

    def map[U](self, a_fn: Callable[[T], U]) -> Result[U]:
        """Transform the success value, preserving failure unchanged."""
        result: Result[U] = Result.failure(self.message)
        if self.is_success:
            result = Result.success(a_fn(self.value), self.message)  # type: ignore[arg-type]
        return result

    def flat_map[U](self, a_fn: Callable[[T], Result[U]]) -> Result[U]:
        """Chain a function that itself returns a Result."""
        result: Result[U] = Result.failure(self.message)
        if self.is_success:
            result = a_fn(self.value)  # type: ignore[arg-type]
        return result

    def unwrap(self) -> T | None:
        """Return the success value, or None on failure."""
        result: T | None = None
        if self.is_success:
            result = self.value
        return result

    def success_value(self) -> T:
        """Return the success value, asserting the result is successful.

        Raises:
            AssertionError: If the result is a failure or value is None.
        """
        assert self.is_success, f"Expected success but got failure: {self.message}"  # noqa: S101 — internal invariant
        assert self.value is not None, "Success result has None value"  # noqa: S101 — internal invariant
        return self.value

    def unwrap_or(self, a_default: T) -> T:
        """Return the success value, or a_default on failure."""
        result: T = a_default
        if self.is_success:
            result = self.value  # type: ignore[assignment]
        return result

    @staticmethod
    def success[U](a_value: U | None = None, a_message: str = "Success") -> Result[U]:
        """Create a successful result with a value."""
        return Result(a_is_success=True, a_value=a_value, a_message=a_message)

    @staticmethod
    def failure(a_message: str) -> Result[Any]:
        """Create a failure result with no value."""
        return Result(a_is_success=False, a_value=None, a_message=a_message)

    @staticmethod
    def uninitialized() -> Result[Any]:
        """Create an uninitialized sentinel result."""
        return Result(a_is_success=False, a_value=None, a_message="UNINITIALIZED")

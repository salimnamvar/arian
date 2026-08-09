"""Generic function protocol and execution mode contracts.

Defines typed structural contracts for callable operations with explicit
input/output types and sync/async execution mode. Layer-neutral.
"""

from __future__ import annotations

import enum
from typing import Protocol
from typing import TypeVar
from typing import runtime_checkable

_InputT = TypeVar("_InputT")
_OutputT = TypeVar("_OutputT")


class ExecutionMode(enum.Enum):
    """Describes how a callable operation executes.

    Attributes:
        SYNC: Synchronous blocking execution.
        ASYNC: Native async/await execution.
    """

    SYNC = "sync"
    ASYNC = "async"


class ConcurrencyMode(enum.Enum):
    """Describes concurrency behavior of a callable operation.

    Attributes:
        SINGLE_THREADED: No concurrency; runs in the calling context.
        THREAD_SAFE: Safe to call from multiple threads.
        PROCESS_SAFE: Safe to call across process boundaries.
    """

    SINGLE_THREADED = "single_threaded"
    THREAD_SAFE = "thread_safe"
    PROCESS_SAFE = "process_safe"


@runtime_checkable
class SyncFunctionProtocol(Protocol[_InputT, _OutputT]):
    """Typed structural contract for a synchronous callable operation.

    Captures the real callable shape with typed input and output.
    Layer-specific protocols may narrow this with additional constraints.
    """

    @property
    def execution_mode(self) -> ExecutionMode:
        """Whether this function executes synchronously or asynchronously."""
        ...

    @property
    def concurrency_mode(self) -> ConcurrencyMode:
        """Concurrency safety classification."""
        ...

    @property
    def is_idempotent(self) -> bool:
        """Whether repeated calls with the same input produce the same result."""
        ...

    def __call__(self, a_input: _InputT) -> _OutputT:
        """Execute the function with a typed input and return a typed output."""
        ...


@runtime_checkable
class AsyncFunctionProtocol(Protocol[_InputT, _OutputT]):
    """Typed structural contract for an asynchronous callable operation.

    Captures the real callable shape with typed input and output.
    Layer-specific protocols may narrow this with additional constraints.
    """

    @property
    def execution_mode(self) -> ExecutionMode:
        """Whether this function executes synchronously or asynchronously."""
        ...

    @property
    def concurrency_mode(self) -> ConcurrencyMode:
        """Concurrency safety classification."""
        ...

    @property
    def is_idempotent(self) -> bool:
        """Whether repeated calls with the same input produce the same result."""
        ...

    async def __call__(self, a_input: _InputT) -> _OutputT:
        """Execute the function with a typed input and return a typed output."""
        ...

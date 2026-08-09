"""Generic function protocol and execution mode contracts.

Defines the structural contract for callable operations, their typed
input/output, and sync/async execution mode. Remains generic and
layer-neutral.
"""

from __future__ import annotations

import enum
from typing import Any
from typing import Protocol
from typing import runtime_checkable


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
class FunctionProtocol(Protocol):
    """Generic structural contract for a callable operation.

    A function protocol captures:
    - input validation responsibility
    - return type (direct for infallible, Result[T] for fallible)
    - sync or async execution mode
    - side effects and resource ownership
    - timeout, retry, cancellation, idempotency behavior
    - concurrency safety and re-entrancy

    This protocol is generic and layer-neutral. Layer-specific protocols
    may narrow it with additional constraints.
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

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the function. Subclass or protocol narrowing defines the signature."""
        ...

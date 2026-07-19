"""Application lifespan — startup/shutdown lifecycle orchestration.

Provides both sync and async context managers:
- Sync (for CLI): ``with lifespan(config): ...``
- Async (for future ASGI): ``async with async_lifespan(app): ...``
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from collections.abc import Generator
from contextlib import asynccontextmanager
from contextlib import contextmanager
import logging
import logging.handlers

from arian.bootstrap.logging import configure_logging
from arian.infrastructure.config import ArianConfig

_logger = logging.getLogger(__name__)


@contextmanager
def lifespan(a_config: ArianConfig) -> Generator[None]:
    """Sync lifespan for CLI: configure logging on startup, stop listener on shutdown.

    Args:
        a_config: Application configuration.

    Yields:
        None — application is alive during yield.
    """
    listener: logging.handlers.QueueListener | None = configure_logging(a_config.logging)
    _logger.debug("Logging configured at level %s", a_config.logging.level.upper())
    _logger.info("Arian starting")
    try:
        yield
    finally:
        _logger.info("Arian stopped")
        if listener is not None:
            listener.stop()


@asynccontextmanager
async def async_lifespan(a_config: ArianConfig) -> AsyncGenerator[None]:
    """Async lifespan for future ASGI use: configure logging on startup, stop listener on shutdown.

    Args:
        a_config: Application configuration.

    Yields:
        None — application is alive during yield.
    """
    listener: logging.handlers.QueueListener | None = configure_logging(a_config.logging)
    _logger.debug("Logging configured at level %s", a_config.logging.level.upper())
    _logger.info("Arian starting")
    try:
        yield
    finally:
        _logger.info("Arian stopped")
        if listener is not None:
            listener.stop()

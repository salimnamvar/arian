"""Bootstrap layer for Arian — composition root (factory, lifecycle, logging)."""

from arian.bootstrap.application import create_application
from arian.bootstrap.lifespan import async_lifespan
from arian.bootstrap.lifespan import lifespan
from arian.bootstrap.logging import configure_logging

__all__ = [
    "async_lifespan",
    "configure_logging",
    "create_application",
    "lifespan",
]

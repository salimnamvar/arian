"""Filesystem repository for Arian."""

from arian.repository.filesystem.collector import FileCollector
from arian.repository.filesystem.protocols import FileCollectorProtocol

__all__ = [
    "FileCollector",
    "FileCollectorProtocol",
]

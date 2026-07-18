"""Domain layer for Arian.

Provides domain entities, enums, and exceptions.
"""

from arian.domain.enums import OutputMode
from arian.domain.exceptions import ContextBuilderError
from arian.domain.exceptions import InputNotFoundError
from arian.domain.exceptions import NoDocumentsError
from arian.domain.exceptions import ProjectBaseError
from arian.domain.models import ContextConfig
from arian.domain.models import ContextResult
from arian.domain.models import Document

__all__ = [
    "ContextBuilderError",
    "ContextConfig",
    "ContextResult",
    "Document",
    "InputNotFoundError",
    "NoDocumentsError",
    "OutputMode",
    "ProjectBaseError",
]

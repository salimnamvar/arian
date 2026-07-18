"""Domain layer for Arian.

Provides domain entities, enums, and exceptions.
"""

from arian.domain.enums import FileRole
from arian.domain.enums import OutputMode
from arian.domain.exceptions import ContextBuilderError
from arian.domain.exceptions import InputNotFoundError
from arian.domain.exceptions import NoDocumentsError
from arian.domain.exceptions import ProjectBaseError
from arian.domain.models import FULL
from arian.domain.models import SIGNATURES
from arian.domain.models import STRUCTURE_ONLY
from arian.domain.models import CompressionLevel
from arian.domain.models import ContextConfig
from arian.domain.models import ContextResult
from arian.domain.models import Document
from arian.domain.models import FileClassification
from arian.domain.models import InputSpec
from arian.domain.models import PatternRule

__all__ = [
    "FULL",
    "SIGNATURES",
    "STRUCTURE_ONLY",
    "CompressionLevel",
    "ContextBuilderError",
    "ContextConfig",
    "ContextResult",
    "Document",
    "FileClassification",
    "FileRole",
    "InputNotFoundError",
    "InputSpec",
    "NoDocumentsError",
    "OutputMode",
    "PatternRule",
    "ProjectBaseError",
]

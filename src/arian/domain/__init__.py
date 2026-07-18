"""Domain layer for Arian.

Provides domain entities, enums, and exceptions.
Zero external dependencies — only stdlib imports.
"""

from arian.domain.context import ContextChunk
from arian.domain.context import ContextPlan
from arian.domain.context import ContextResult
from arian.domain.context import ContextTask
from arian.domain.context import PlannedFile
from arian.domain.exceptions import ContextBuilderError
from arian.domain.exceptions import InputNotFoundError
from arian.domain.exceptions import NoDocumentsError
from arian.domain.exceptions import ProjectBaseError
from arian.domain.protocols import LanguageAnalyzerProtocol
from arian.domain.repository import Dependency
from arian.domain.repository import FileContent
from arian.domain.repository import Module
from arian.domain.repository import Repository
from arian.domain.repository import RepositoryFile
from arian.domain.repository import Symbol
from arian.domain.shared import CompressionLevel
from arian.domain.shared import DependencyKind
from arian.domain.shared import FileRole
from arian.domain.shared import SymbolKind
from arian.domain.shared import TokenBudget

__all__ = [
    "CompressionLevel",
    "ContextBuilderError",
    "ContextChunk",
    "ContextPlan",
    "ContextResult",
    "ContextTask",
    "Dependency",
    "DependencyKind",
    "FileContent",
    "FileRole",
    "InputNotFoundError",
    "LanguageAnalyzerProtocol",
    "Module",
    "NoDocumentsError",
    "PlannedFile",
    "ProjectBaseError",
    "Repository",
    "RepositoryFile",
    "Symbol",
    "SymbolKind",
    "TokenBudget",
]

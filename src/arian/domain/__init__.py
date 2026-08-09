"""Domain layer for Arian.

Provides domain entities, enums, and exceptions.
Zero external dependencies — only stdlib imports.
"""

from arian.domain.base import BaseDomainModule
from arian.domain.context import BuildRequest
from arian.domain.context import ContextChunk
from arian.domain.context import ContextPlan
from arian.domain.context import ContextResult
from arian.domain.context import ContextTask
from arian.domain.context import PlannedFile
from arian.domain.exceptions import AnalysisError
from arian.domain.exceptions import BinaryFileError
from arian.domain.exceptions import CancellationError
from arian.domain.exceptions import ClassificationError
from arian.domain.exceptions import CollectionError
from arian.domain.exceptions import ConfigurationError
from arian.domain.exceptions import ContextBuilderError
from arian.domain.exceptions import DatabaseConnectionError
from arian.domain.exceptions import ExternalServiceError
from arian.domain.exceptions import GitError
from arian.domain.exceptions import InputError
from arian.domain.exceptions import InputNotFoundError
from arian.domain.exceptions import InvalidTaskError
from arian.domain.exceptions import MaterializationError
from arian.domain.exceptions import NoDocumentsError
from arian.domain.exceptions import PartialResultError
from arian.domain.exceptions import PathTraversalError
from arian.domain.exceptions import PlanningError
from arian.domain.exceptions import ProcessingError
from arian.domain.exceptions import ProjectBaseError
from arian.domain.exceptions import RenderingError
from arian.domain.exceptions import RepositoryError
from arian.domain.exceptions import ResourceError
from arian.domain.exceptions import SecurityError
from arian.domain.exceptions import SymlinkLoopError
from arian.domain.exceptions import TokenizationError
from arian.domain.exceptions import ValidationError
from arian.domain.protocols import ContextBuilderProtocol
from arian.domain.protocols import ContextMaterializerProtocol
from arian.domain.protocols import ContextPlannerProtocol
from arian.domain.protocols import FileClassifierProtocol
from arian.domain.protocols import LanguageAnalyzerProtocol
from arian.domain.repository import CollectionStats
from arian.domain.repository import Dependency
from arian.domain.repository import FileContent
from arian.domain.repository import Module
from arian.domain.repository import Repository
from arian.domain.repository import RepositoryFile
from arian.domain.repository import Symbol
from arian.domain.shared import CompressionLevel
from arian.domain.shared import ConcurrencyPolicy
from arian.domain.shared import DependencyKind
from arian.domain.shared import EnvironmentSecretProvider
from arian.domain.shared import FileRole
from arian.domain.shared import OutputWriterProtocol
from arian.domain.shared import RendererProtocol
from arian.domain.shared import SecretProvider
from arian.domain.shared import SymbolKind
from arian.domain.shared import TokenBudget
from arian.domain.shared import detect_language
from arian.domain.shared import is_binary
from arian.domain.shared import lang_extensions
from arian.domain.shared import redact_secrets
from arian.domain.shared import validate_input_path

__all__ = [
    "AnalysisError",
    "BaseDomainModule",
    "BinaryFileError",
    "BuildRequest",
    "CancellationError",
    "ClassificationError",
    "CollectionError",
    "CollectionStats",
    "CompressionLevel",
    "ConcurrencyPolicy",
    "ConfigurationError",
    "ContextBuilderError",
    "ContextBuilderProtocol",
    "ContextChunk",
    "ContextMaterializerProtocol",
    "ContextPlan",
    "ContextPlannerProtocol",
    "ContextResult",
    "ContextTask",
    "DatabaseConnectionError",
    "Dependency",
    "DependencyKind",
    "EnvironmentSecretProvider",
    "ExternalServiceError",
    "FileClassifierProtocol",
    "FileContent",
    "FileRole",
    "GitError",
    "InputError",
    "InputNotFoundError",
    "InvalidTaskError",
    "LanguageAnalyzerProtocol",
    "MaterializationError",
    "Module",
    "NoDocumentsError",
    "OutputWriterProtocol",
    "PartialResultError",
    "PathTraversalError",
    "PlannedFile",
    "PlanningError",
    "ProcessingError",
    "ProjectBaseError",
    "RendererProtocol",
    "RenderingError",
    "Repository",
    "RepositoryError",
    "RepositoryFile",
    "ResourceError",
    "SecretProvider",
    "SecurityError",
    "Symbol",
    "SymbolKind",
    "SymlinkLoopError",
    "TokenBudget",
    "TokenizationError",
    "ValidationError",
    "detect_language",
    "is_binary",
    "lang_extensions",
    "redact_secrets",
    "validate_input_path",
]

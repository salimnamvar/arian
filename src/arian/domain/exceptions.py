"""Domain exceptions for Arian.

Provides structured exception hierarchy following errors.md patterns.
Each exception carries reason, exit_code, and recoverable metadata
for programmatic handling by the CLI and orchestration layers.
"""

from __future__ import annotations


class ProjectBaseError(Exception):
    """Root base for all project exceptions.

    Never raise this class directly — always use a typed subclass.

    Attributes:
        message: Human-readable error description.
        reason: Machine-readable reason code (UPPER_SNAKE_CASE).
        exit_code: Exit code for process termination.
        recoverable: Whether the error can be retried.
    """

    reason: str = "UNKNOWN_ERROR"
    exit_code: int = 2
    recoverable: bool = False

    def __init__(
        self,
        a_message: str,
        *,
        a_cause: BaseException | None = None,
    ) -> None:
        self.message = a_message
        super().__init__(a_message)
        if a_cause is not None:
            self.__cause__ = a_cause


class ConfigurationError(ProjectBaseError):
    """Invalid config, missing required fields."""

    reason = "CONFIGURATION_ERROR"
    exit_code = 1
    recoverable = False


class InputError(ProjectBaseError):
    """Bad user input."""

    reason = "INPUT_ERROR"
    exit_code = 1
    recoverable = False


class InputNotFoundError(InputError):
    """Input path does not exist."""

    reason = "INPUT_NOT_FOUND"
    exit_code = 1
    recoverable = False


class InvalidTaskError(InputError):
    """Unknown task type."""

    reason = "INVALID_TASK"
    exit_code = 1
    recoverable = False


class ValidationError(InputError):
    """Request validation failed."""

    reason = "VALIDATION_ERROR"
    exit_code = 1
    recoverable = False


class ProcessingError(ProjectBaseError):
    """Pipeline processing failures."""

    reason = "PROCESSING_ERROR"
    exit_code = 2
    recoverable = True


class ContextBuilderError(ProcessingError):
    """Context build failures."""

    reason = "CONTEXT_BUILDER_ERROR"
    exit_code = 2
    recoverable = True


class PlanningError(ContextBuilderError):
    """Plan generation failures."""

    reason = "PLANNING_ERROR"
    exit_code = 2
    recoverable = True


class MaterializationError(ContextBuilderError):
    """Content materialization failures."""

    reason = "MATERIALIZATION_ERROR"
    exit_code = 2
    recoverable = True


class RenderingError(ContextBuilderError):
    """Output rendering failures."""

    reason = "RENDERING_ERROR"
    exit_code = 2
    recoverable = True


class ClassificationError(ProcessingError):
    """File classification failures."""

    reason = "CLASSIFICATION_ERROR"
    exit_code = 2
    recoverable = True


class AnalysisError(ProcessingError):
    """Code analysis failures."""

    reason = "ANALYSIS_ERROR"
    exit_code = 2
    recoverable = True


class TokenizationError(ProcessingError):
    """Token counting failures."""

    reason = "TOKENIZATION_ERROR"
    exit_code = 2
    recoverable = True


class RepositoryError(ProjectBaseError):
    """Data access failures."""

    reason = "REPOSITORY_ERROR"
    exit_code = 2
    recoverable = True


class CollectionError(RepositoryError):
    """File collection failures."""

    reason = "COLLECTION_ERROR"
    exit_code = 2
    recoverable = True


class IndexError(RepositoryError):
    """Index read/write failures."""

    reason = "INDEX_ERROR"
    exit_code = 2
    recoverable = True


class ConnectionError(RepositoryError):
    """Database connection failures."""

    reason = "CONNECTION_ERROR"
    exit_code = 3
    recoverable = True


class SecurityError(ProjectBaseError):
    """Security violations."""

    reason = "SECURITY_ERROR"
    exit_code = 1
    recoverable = False


class PathTraversalError(SecurityError):
    """Path escape attempt."""

    reason = "PATH_TRAVERSAL"
    exit_code = 1
    recoverable = False


class SymlinkLoopError(SecurityError):
    """Symlink loop detected."""

    reason = "SYMLINK_LOOP"
    exit_code = 1
    recoverable = False


class BinaryFileError(SecurityError):
    """Binary file encountered."""

    reason = "BINARY_FILE"
    exit_code = 1
    recoverable = False


class ResourceError(ProjectBaseError):
    """Resource limitations."""

    reason = "RESOURCE_ERROR"
    exit_code = 3
    recoverable = False


class FileNotFoundError(ResourceError):
    """Required resource missing."""

    reason = "FILE_NOT_FOUND"
    exit_code = 3
    recoverable = False


class MemoryError(ResourceError):
    """Out of memory."""

    reason = "MEMORY_ERROR"
    exit_code = 3
    recoverable = False


class TimeoutError(ResourceError):
    """Operation timed out."""

    reason = "TIMEOUT_ERROR"
    exit_code = 3
    recoverable = True


class CancellationError(ProjectBaseError):
    """User or system cancellation."""

    reason = "CANCELLATION_ERROR"
    exit_code = 130
    recoverable = False


class ExternalServiceError(ProjectBaseError):
    """External service failures."""

    reason = "EXTERNAL_SERVICE_ERROR"
    exit_code = 3
    recoverable = True


class GitError(ExternalServiceError):
    """Git operation failures."""

    reason = "GIT_ERROR"
    exit_code = 3
    recoverable = True


class PartialResultError(ProjectBaseError):
    """Some files failed, partial output available."""

    reason = "PARTIAL_RESULT"
    exit_code = 2
    recoverable = False


class NoDocumentsError(ContextBuilderError):
    """No documents collected from inputs."""

    reason = "NO_DOCUMENTS"

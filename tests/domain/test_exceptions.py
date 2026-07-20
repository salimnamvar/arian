"""Unit tests for domain exceptions."""

from __future__ import annotations

import pytest

from arian.domain.exceptions import AnalysisError
from arian.domain.exceptions import BinaryFileError
from arian.domain.exceptions import CancellationError
from arian.domain.exceptions import ClassificationError
from arian.domain.exceptions import CollectionError
from arian.domain.exceptions import ConfigurationError
from arian.domain.exceptions import ConnectionError
from arian.domain.exceptions import ContextBuilderError
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


class TestProjectBaseError:
    """Tests for the root exception class."""

    def test_default_attributes(self) -> None:
        exc = ProjectBaseError("Test message")
        assert exc.message == "Test message"
        assert exc.reason == "UNKNOWN_ERROR"
        assert exc.exit_code == 2
        assert exc.recoverable is False

    def test_cause_chaining(self) -> None:
        cause = ValueError("root cause")
        exc = ProjectBaseError("wrapper", a_cause=cause)
        assert exc.__cause__ is cause

    def test_no_cause(self) -> None:
        exc = ProjectBaseError("no cause")
        assert exc.__cause__ is None

    def test_is_exception(self) -> None:
        exc = ProjectBaseError("test")
        assert isinstance(exc, Exception)

    def test_str_representation(self) -> None:
        exc = ProjectBaseError("test message")
        assert "test message" in str(exc)


class TestConfigurationError:
    def test_attributes(self) -> None:
        exc = ConfigurationError("bad config")
        assert exc.reason == "CONFIGURATION_ERROR"
        assert exc.exit_code == 1
        assert exc.recoverable is False

    def test_inheritance(self) -> None:
        exc = ConfigurationError("bad config")
        assert isinstance(exc, ProjectBaseError)


class TestInputError:
    def test_attributes(self) -> None:
        exc = InputError("bad input")
        assert exc.reason == "INPUT_ERROR"
        assert exc.exit_code == 1
        assert exc.recoverable is False

    def test_inheritance(self) -> None:
        exc = InputError("bad input")
        assert isinstance(exc, ProjectBaseError)


class TestInputNotFoundError:
    def test_attributes(self) -> None:
        exc = InputNotFoundError("not found")
        assert exc.reason == "INPUT_NOT_FOUND"
        assert exc.exit_code == 1
        assert exc.recoverable is False

    def test_inheritance(self) -> None:
        exc = InputNotFoundError("not found")
        assert isinstance(exc, InputError)
        assert isinstance(exc, ProjectBaseError)

    def test_backward_compat(self) -> None:
        with pytest.raises(InputNotFoundError):
            raise InputNotFoundError("missing")


class TestInvalidTaskError:
    def test_attributes(self) -> None:
        exc = InvalidTaskError("unknown task")
        assert exc.reason == "INVALID_TASK"
        assert exc.exit_code == 1
        assert exc.recoverable is False

    def test_inheritance(self) -> None:
        exc = InvalidTaskError("unknown task")
        assert isinstance(exc, InputError)


class TestValidationError:
    def test_attributes(self) -> None:
        exc = ValidationError("validation failed")
        assert exc.reason == "VALIDATION_ERROR"
        assert exc.exit_code == 1
        assert exc.recoverable is False

    def test_inheritance(self) -> None:
        exc = ValidationError("validation failed")
        assert isinstance(exc, InputError)


class TestProcessingError:
    def test_attributes(self) -> None:
        exc = ProcessingError("processing failed")
        assert exc.reason == "PROCESSING_ERROR"
        assert exc.exit_code == 2
        assert exc.recoverable is True

    def test_inheritance(self) -> None:
        exc = ProcessingError("processing failed")
        assert isinstance(exc, ProjectBaseError)


class TestContextBuilderError:
    def test_attributes(self) -> None:
        exc = ContextBuilderError("builder failed")
        assert exc.reason == "CONTEXT_BUILDER_ERROR"
        assert exc.exit_code == 2
        assert exc.recoverable is True

    def test_inheritance(self) -> None:
        exc = ContextBuilderError("builder failed")
        assert isinstance(exc, ProcessingError)
        assert isinstance(exc, ProjectBaseError)

    def test_backward_compat(self) -> None:
        with pytest.raises(ContextBuilderError):
            raise ContextBuilderError("test")


class TestPlanningError:
    def test_attributes(self) -> None:
        exc = PlanningError("plan failed")
        assert exc.reason == "PLANNING_ERROR"
        assert exc.exit_code == 2
        assert exc.recoverable is True

    def test_inheritance(self) -> None:
        exc = PlanningError("plan failed")
        assert isinstance(exc, ContextBuilderError)
        assert isinstance(exc, ProcessingError)


class TestMaterializationError:
    def test_attributes(self) -> None:
        exc = MaterializationError("materialize failed")
        assert exc.reason == "MATERIALIZATION_ERROR"
        assert exc.exit_code == 2
        assert exc.recoverable is True

    def test_inheritance(self) -> None:
        exc = MaterializationError("materialize failed")
        assert isinstance(exc, ContextBuilderError)


class TestRenderingError:
    def test_attributes(self) -> None:
        exc = RenderingError("render failed")
        assert exc.reason == "RENDERING_ERROR"
        assert exc.exit_code == 2
        assert exc.recoverable is True

    def test_inheritance(self) -> None:
        exc = RenderingError("render failed")
        assert isinstance(exc, ContextBuilderError)


class TestClassificationError:
    def test_attributes(self) -> None:
        exc = ClassificationError("classify failed")
        assert exc.reason == "CLASSIFICATION_ERROR"
        assert exc.exit_code == 2
        assert exc.recoverable is True

    def test_inheritance(self) -> None:
        exc = ClassificationError("classify failed")
        assert isinstance(exc, ProcessingError)


class TestAnalysisError:
    def test_attributes(self) -> None:
        exc = AnalysisError("analysis failed")
        assert exc.reason == "ANALYSIS_ERROR"
        assert exc.exit_code == 2
        assert exc.recoverable is True

    def test_inheritance(self) -> None:
        exc = AnalysisError("analysis failed")
        assert isinstance(exc, ProcessingError)


class TestTokenizationError:
    def test_attributes(self) -> None:
        exc = TokenizationError("tokenize failed")
        assert exc.reason == "TOKENIZATION_ERROR"
        assert exc.exit_code == 2
        assert exc.recoverable is True

    def test_inheritance(self) -> None:
        exc = TokenizationError("tokenize failed")
        assert isinstance(exc, ProcessingError)


class TestRepositoryError:
    def test_attributes(self) -> None:
        exc = RepositoryError("repo error")
        assert exc.reason == "REPOSITORY_ERROR"
        assert exc.exit_code == 2
        assert exc.recoverable is True

    def test_inheritance(self) -> None:
        exc = RepositoryError("repo error")
        assert isinstance(exc, ProjectBaseError)


class TestCollectionError:
    def test_attributes(self) -> None:
        exc = CollectionError("collect failed")
        assert exc.reason == "COLLECTION_ERROR"
        assert exc.exit_code == 2
        assert exc.recoverable is True

    def test_inheritance(self) -> None:
        exc = CollectionError("collect failed")
        assert isinstance(exc, RepositoryError)


class TestIndexError:
    def test_attributes(self) -> None:
        from arian.domain.exceptions import IndexError

        exc = IndexError("index failed")
        assert exc.reason == "INDEX_ERROR"
        assert exc.exit_code == 2
        assert exc.recoverable is True

    def test_inheritance(self) -> None:
        from arian.domain.exceptions import IndexError

        exc = IndexError("index failed")
        assert isinstance(exc, RepositoryError)


class TestConnectionError:
    def test_attributes(self) -> None:
        exc = ConnectionError("conn failed")
        assert exc.reason == "CONNECTION_ERROR"
        assert exc.exit_code == 3
        assert exc.recoverable is True

    def test_inheritance(self) -> None:
        exc = ConnectionError("conn failed")
        assert isinstance(exc, RepositoryError)


class TestSecurityError:
    def test_attributes(self) -> None:
        exc = SecurityError("security violation")
        assert exc.reason == "SECURITY_ERROR"
        assert exc.exit_code == 1
        assert exc.recoverable is False

    def test_inheritance(self) -> None:
        exc = SecurityError("security violation")
        assert isinstance(exc, ProjectBaseError)


class TestPathTraversalError:
    def test_attributes(self) -> None:
        exc = PathTraversalError("traversal")
        assert exc.reason == "PATH_TRAVERSAL"
        assert exc.exit_code == 1
        assert exc.recoverable is False

    def test_inheritance(self) -> None:
        exc = PathTraversalError("traversal")
        assert isinstance(exc, SecurityError)


class TestSymlinkLoopError:
    def test_attributes(self) -> None:
        exc = SymlinkLoopError("symlink loop")
        assert exc.reason == "SYMLINK_LOOP"
        assert exc.exit_code == 1
        assert exc.recoverable is False

    def test_inheritance(self) -> None:
        exc = SymlinkLoopError("symlink loop")
        assert isinstance(exc, SecurityError)


class TestBinaryFileError:
    def test_attributes(self) -> None:
        exc = BinaryFileError("binary file")
        assert exc.reason == "BINARY_FILE"
        assert exc.exit_code == 1
        assert exc.recoverable is False

    def test_inheritance(self) -> None:
        exc = BinaryFileError("binary file")
        assert isinstance(exc, SecurityError)


class TestResourceError:
    def test_attributes(self) -> None:
        exc = ResourceError("resource error")
        assert exc.reason == "RESOURCE_ERROR"
        assert exc.exit_code == 3
        assert exc.recoverable is False

    def test_inheritance(self) -> None:
        exc = ResourceError("resource error")
        assert isinstance(exc, ProjectBaseError)


class TestFileNotFoundError:
    def test_attributes(self) -> None:
        from arian.domain.exceptions import FileNotFoundError

        exc = FileNotFoundError("file missing")
        assert exc.reason == "FILE_NOT_FOUND"
        assert exc.exit_code == 3
        assert exc.recoverable is False

    def test_inheritance(self) -> None:
        from arian.domain.exceptions import FileNotFoundError

        exc = FileNotFoundError("file missing")
        assert isinstance(exc, ResourceError)


class TestMemoryError:
    def test_attributes(self) -> None:
        from arian.domain.exceptions import MemoryError

        exc = MemoryError("out of memory")
        assert exc.reason == "MEMORY_ERROR"
        assert exc.exit_code == 3
        assert exc.recoverable is False

    def test_inheritance(self) -> None:
        from arian.domain.exceptions import MemoryError

        exc = MemoryError("out of memory")
        assert isinstance(exc, ResourceError)


class TestTimeoutError:
    def test_attributes(self) -> None:
        from arian.domain.exceptions import TimeoutError

        exc = TimeoutError("timed out")
        assert exc.reason == "TIMEOUT_ERROR"
        assert exc.exit_code == 3
        assert exc.recoverable is True

    def test_inheritance(self) -> None:
        from arian.domain.exceptions import TimeoutError

        exc = TimeoutError("timed out")
        assert isinstance(exc, ResourceError)


class TestCancellationError:
    def test_attributes(self) -> None:
        exc = CancellationError("cancelled")
        assert exc.reason == "CANCELLATION_ERROR"
        assert exc.exit_code == 130
        assert exc.recoverable is False

    def test_inheritance(self) -> None:
        exc = CancellationError("cancelled")
        assert isinstance(exc, ProjectBaseError)


class TestExternalServiceError:
    def test_attributes(self) -> None:
        exc = ExternalServiceError("external failed")
        assert exc.reason == "EXTERNAL_SERVICE_ERROR"
        assert exc.exit_code == 3
        assert exc.recoverable is True

    def test_inheritance(self) -> None:
        exc = ExternalServiceError("external failed")
        assert isinstance(exc, ProjectBaseError)


class TestGitError:
    def test_attributes(self) -> None:
        exc = GitError("git failed")
        assert exc.reason == "GIT_ERROR"
        assert exc.exit_code == 3
        assert exc.recoverable is True

    def test_inheritance(self) -> None:
        exc = GitError("git failed")
        assert isinstance(exc, ExternalServiceError)
        assert isinstance(exc, ProjectBaseError)


class TestPartialResultError:
    def test_attributes(self) -> None:
        exc = PartialResultError("partial output")
        assert exc.reason == "PARTIAL_RESULT"
        assert exc.exit_code == 2
        assert exc.recoverable is False

    def test_inheritance(self) -> None:
        exc = PartialResultError("partial output")
        assert isinstance(exc, ProjectBaseError)


class TestNoDocumentsError:
    def test_attributes(self) -> None:
        exc = NoDocumentsError("no docs")
        assert exc.reason == "NO_DOCUMENTS"

    def test_inheritance(self) -> None:
        exc = NoDocumentsError("no docs")
        assert isinstance(exc, ContextBuilderError)
        assert isinstance(exc, ProjectBaseError)

    def test_backward_compat(self) -> None:
        with pytest.raises(NoDocumentsError):
            raise NoDocumentsError("test")


class TestExceptionRaiseCatch:
    """Verify all exceptions can be raised and caught."""

    @pytest.mark.parametrize(
        "exc_class",
        [
            ConfigurationError,
            InputError,
            InputNotFoundError,
            InvalidTaskError,
            ValidationError,
            ProcessingError,
            ContextBuilderError,
            PlanningError,
            MaterializationError,
            RenderingError,
            ClassificationError,
            AnalysisError,
            TokenizationError,
            RepositoryError,
            CollectionError,
            SecurityError,
            PathTraversalError,
            SymlinkLoopError,
            BinaryFileError,
            ResourceError,
            CancellationError,
            ExternalServiceError,
            GitError,
            PartialResultError,
            NoDocumentsError,
        ],
    )
    def test_raise_and_catch(self, exc_class: type[ProjectBaseError]) -> None:
        with pytest.raises(exc_class, match="test"):
            raise exc_class("test")

    @pytest.mark.parametrize(
        "exc_class",
        [
            ConfigurationError,
            InputError,
            ProcessingError,
            ContextBuilderError,
            RepositoryError,
            SecurityError,
            ResourceError,
            ExternalServiceError,
        ],
    )
    def test_cause_chaining(self, exc_class: type[ProjectBaseError]) -> None:
        cause = RuntimeError("underlying")
        exc = exc_class("wrapper", a_cause=cause)
        assert exc.__cause__ is cause

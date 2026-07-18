"""Unit tests for domain exceptions."""

from __future__ import annotations

import pytest

from arian.domain.exceptions import ContextBuilderError
from arian.domain.exceptions import InputNotFoundError
from arian.domain.exceptions import NoDocumentsError
from arian.domain.exceptions import ProjectBaseError


def test_project_base_error_defaults() -> None:
    """Test ProjectBaseError default values."""
    exc = ProjectBaseError("Test message")
    assert exc.message == "Test message"
    assert exc.resource_type is None
    assert exc.resource_name is None
    assert exc.details == []


def test_project_base_error_with_context() -> None:
    """Test ProjectBaseError with structured context."""
    exc = ProjectBaseError(
        "Test error",
        a_resource_type="document",
        a_resource_name="test.py",
    )
    assert exc.resource_type == "document"
    assert exc.resource_name == "test.py"


def test_project_base_error_with_details() -> None:
    """Test ProjectBaseError with error details."""
    details: list[dict[str, str]] = [{"key": "value"}]
    exc = ProjectBaseError("Test error", a_details=details)
    assert exc.details == details


def test_input_not_found_error() -> None:
    """Test InputNotFoundError reason code."""
    exc = InputNotFoundError("Input not found", a_resource_name="/missing/path")
    assert exc.reason == "INPUT_NOT_FOUND"
    assert exc.resource_name == "/missing/path"


def test_no_documents_error() -> None:
    """Test NoDocumentsError reason code."""
    exc = NoDocumentsError("No documents found")
    assert exc.reason == "NO_DOCUMENTS"


def test_context_builder_error_inheritance() -> None:
    """Test ContextBuilderError inheritance chain."""
    exc = ContextBuilderError("Builder error")
    assert isinstance(exc, ContextBuilderError)
    assert isinstance(exc, ProjectBaseError)


def test_exception_can_be_raised() -> None:
    """Test exceptions can be raised and caught."""
    message = "Not found"
    with pytest.raises(InputNotFoundError) as exc_info:
        raise InputNotFoundError(message)
    assert message in str(exc_info.value)

"""Tests for domain repository models."""

from __future__ import annotations

from arian.domain.repository.models import Dependency
from arian.domain.repository.models import FileContent
from arian.domain.repository.models import Module
from arian.domain.repository.models import Repository
from arian.domain.repository.models import RepositoryFile
from arian.domain.repository.models import Symbol
from arian.domain.shared.enums import DependencyKind
from arian.domain.shared.enums import FileRole
from arian.domain.shared.enums import SymbolKind


def test_repository_file_creation() -> None:
    """Test RepositoryFile creation."""
    repo_file = RepositoryFile(
        path="src/main.py",
        language="python",
        role=FileRole.ENTRY_POINT,
        tokens=100,
        hash="abc123",
    )
    assert repo_file.path == "src/main.py"
    assert repo_file.language == "python"
    assert repo_file.role == FileRole.ENTRY_POINT
    assert repo_file.tokens == 100
    assert repo_file.hash == "abc123"


def test_repository_file_immutable() -> None:
    """Test RepositoryFile is frozen."""
    repo_file = RepositoryFile(
        path="test.py",
        language="python",
        role=FileRole.UNKNOWN,
        tokens=0,
        hash="",
    )
    try:
        repo_file.path = "other.py"  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        msg = "Should not be able to modify frozen dataclass"
        raise AssertionError(msg)


def test_file_content_creation() -> None:
    """Test FileContent creation."""
    content = FileContent(
        path="src/main.py",
        content="print('hello')",
        hash="abc123",
    )
    assert content.path == "src/main.py"
    assert content.content == "print('hello')"
    assert content.hash == "abc123"


def test_symbol_creation() -> None:
    """Test Symbol creation."""
    symbol = Symbol(
        name="MyClass",
        kind=SymbolKind.CLASS,
        file_path="src/models.py",
        signature="class MyClass:",
        docstring="A test class.",
        line_start=10,
        line_end=20,
    )
    assert symbol.name == "MyClass"
    assert symbol.kind == SymbolKind.CLASS
    assert symbol.file_path == "src/models.py"
    assert symbol.signature == "class MyClass:"
    assert symbol.docstring == "A test class."
    assert symbol.line_start == 10
    assert symbol.line_end == 20


def test_symbol_defaults() -> None:
    """Test Symbol default values."""
    symbol = Symbol(
        name="func",
        kind=SymbolKind.FUNCTION,
        file_path="test.py",
        signature="def func(): ...",
    )
    assert symbol.docstring == ""
    assert symbol.line_start == 0
    assert symbol.line_end == 0


def test_dependency_creation() -> None:
    """Test Dependency creation."""
    dep = Dependency(
        source_path="src/main.py",
        target_path="src/utils.py",
        kind=DependencyKind.IMPORT,
    )
    assert dep.source_path == "src/main.py"
    assert dep.target_path == "src/utils.py"
    assert dep.kind == DependencyKind.IMPORT


def test_module_creation() -> None:
    """Test Module creation."""
    module = Module(
        name="core",
        path="src/core",
        files=("src/core/main.py", "src/core/utils.py"),
    )
    assert module.name == "core"
    assert module.path == "src/core"
    assert len(module.files) == 2


def test_repository_creation() -> None:
    """Test Repository creation."""
    repo = Repository(
        path="/home/user/project",
        name="my-project",
    )
    assert repo.path == "/home/user/project"
    assert repo.name == "my-project"
    assert repo.files == ()
    assert repo.modules == ()

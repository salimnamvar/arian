"""Tests for repository implementations."""

from __future__ import annotations

from arian.domain.repository.models import Dependency
from arian.domain.repository.models import Module
from arian.domain.repository.models import Repository
from arian.domain.repository.models import RepositoryFile
from arian.domain.repository.models import Symbol
from arian.domain.shared.enums import DependencyKind
from arian.domain.shared.enums import FileRole
from arian.domain.shared.enums import SymbolKind
from arian.repository.index.memory_repository import MemoryRepositoryIndex


class TestMemoryRepositoryIndex:
    """Tests for MemoryRepositoryIndex."""

    async def test_save_and_get_file(self) -> None:
        """Test saving and retrieving a file."""
        index = MemoryRepositoryIndex()
        repo_file = RepositoryFile(
            path="src/main.py",
            language="python",
            role=FileRole.ENTRY_POINT,
            tokens=100,
            hash="abc123",
        )

        await index.save_file(repo_file)
        result = await index.get_file("src/main.py")

        assert result is not None
        assert result.path == "src/main.py"
        assert result.language == "python"
        assert result.tokens == 100

    async def test_get_nonexistent_file(self) -> None:
        """Test retrieving a non-existent file."""
        index = MemoryRepositoryIndex()
        result = await index.get_file("nonexistent.py")
        assert result is None

    async def test_list_files(self) -> None:
        """Test listing all files."""
        index = MemoryRepositoryIndex()
        files = [
            RepositoryFile(path="a.py", language="python", role=FileRole.UNKNOWN, tokens=10, hash="a"),
            RepositoryFile(path="b.py", language="python", role=FileRole.UNKNOWN, tokens=20, hash="b"),
        ]

        for f in files:
            await index.save_file(f)

        result = await index.list_files()
        assert len(result) == 2

    async def test_save_and_find_symbols(self) -> None:
        """Test saving and finding symbols."""
        index = MemoryRepositoryIndex()
        symbol = Symbol(
            name="MyClass",
            kind=SymbolKind.CLASS,
            file_path="src/models.py",
            signature="class MyClass:",
        )

        await index.save_symbol(symbol)
        result = await index.find_symbols("MyClass")

        assert len(result) == 1
        assert result[0].name == "MyClass"
        assert result[0].kind == SymbolKind.CLASS

    async def test_find_nonexistent_symbols(self) -> None:
        """Test finding non-existent symbols."""
        index = MemoryRepositoryIndex()
        result = await index.find_symbols("Nonexistent")
        assert result == []

    async def test_save_and_get_dependencies(self) -> None:
        """Test saving and retrieving dependencies."""
        index = MemoryRepositoryIndex()
        dep = Dependency(
            source_path="src/main.py",
            target_path="src/utils.py",
            kind=DependencyKind.IMPORT,
        )

        await index.save_dependency(dep)
        result = await index.get_dependencies("src/main.py")

        assert len(result) == 1
        assert result[0].source_path == "src/main.py"
        assert result[0].target_path == "src/utils.py"

    async def test_get_dependencies_nonexistent(self) -> None:
        """Test getting dependencies for non-existent file."""
        index = MemoryRepositoryIndex()
        result = await index.get_dependencies("nonexistent.py")
        assert result == []

    async def test_save_and_get_module(self) -> None:
        """Test saving and retrieving a module."""
        index = MemoryRepositoryIndex()
        module = Module(
            name="core",
            path="src/core",
            files=("src/core/main.py",),
        )

        await index.save_module(module)
        assert "core" in index._modules

    async def test_save_repository(self) -> None:
        """Test saving a repository."""
        index = MemoryRepositoryIndex()
        repo = Repository(
            path="/home/user/project",
            name="my-project",
            files=(
                RepositoryFile(path="a.py", language="python", role=FileRole.UNKNOWN, tokens=10, hash="a"),
                RepositoryFile(path="b.py", language="python", role=FileRole.UNKNOWN, tokens=20, hash="b"),
            ),
        )

        await index.save_repository(repo)
        result = await index.list_files()
        assert len(result) == 2

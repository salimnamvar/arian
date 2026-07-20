"""Contract tests — verify Memory and SQLite implementations behave identically."""

from __future__ import annotations

import asyncio
import contextlib
import tempfile
from pathlib import Path
from collections.abc import Generator

from arian.domain.repository.models import Dependency
from arian.domain.repository.models import Module
from arian.domain.repository.models import Repository
from arian.domain.repository.models import RepositoryFile
from arian.domain.repository.models import Symbol
from arian.domain.shared.enums import DependencyKind
from arian.domain.shared.enums import FileRole
from arian.domain.shared.enums import SymbolKind
from arian.repository.index.memory_repository import MemoryRepositoryIndex
from arian.repository.index.sqlite_repository import SQLiteRepositoryIndex

_IMPLS = ("memory", "sqlite")


@contextlib.contextmanager
def _make_repository(a_impl: str) -> Generator:
    """Create a repository index with proper cleanup."""
    if a_impl == "memory":
        yield MemoryRepositoryIndex()
        return
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = SQLiteRepositoryIndex(a_db_path=Path(tmpdir) / "contract.db")
        yield repo
        if repo._connection is not None:
            repo._connection.close()


class TestRepositoryContract:
    """Shared contract tests for all RepositoryIndex implementations."""

    def test_save_and_get_file(self) -> None:
        """Saving a file then retrieving by path returns identical metadata."""
        for impl in _IMPLS:
            with _make_repository(impl) as repo:
                file = RepositoryFile(
                    path="src/main.py",
                    language="python",
                    role=FileRole.ENTRY_POINT,
                    tokens=100,
                    hash="abc123",
                    size_bytes=500,
                )
                asyncio.run(repo.save_file(file))
                result = asyncio.run(repo.get_file("src/main.py"))
                assert result is not None, f"[{impl}] file not found"
                assert result.path == "src/main.py", f"[{impl}] wrong path"
                assert result.language == "python", f"[{impl}] wrong language"
                assert result.tokens == 100, f"[{impl}] wrong tokens"
                assert result.hash == "abc123", f"[{impl}] wrong hash"
                assert result.size_bytes == 500, f"[{impl}] wrong size_bytes"

    def test_get_nonexistent_file(self) -> None:
        """Retrieving a non-existent path returns None."""
        for impl in _IMPLS:
            with _make_repository(impl) as repo:
                result = asyncio.run(repo.get_file("nonexistent.py"))
                assert result is None, f"[{impl}] expected None"

    def test_list_files(self) -> None:
        """Listing files after saving returns all stored entries."""
        for impl in _IMPLS:
            with _make_repository(impl) as repo:
                files = [
                    RepositoryFile(path="a.py", language="python", role=FileRole.UTILITY, tokens=10, hash="a"),
                    RepositoryFile(path="b.py", language="python", role=FileRole.UTILITY, tokens=20, hash="b"),
                ]
                for f in files:
                    asyncio.run(repo.save_file(f))
                result = asyncio.run(repo.list_files())
                assert len(result) == 2, f"[{impl}] expected 2 files, got {len(result)}"

    def test_list_files_empty(self) -> None:
        """Listing files on a fresh index returns empty list."""
        for impl in _IMPLS:
            with _make_repository(impl) as repo:
                result = asyncio.run(repo.list_files())
                assert result == [], f"[{impl}] expected empty list"

    def test_save_file_overwrites(self) -> None:
        """Saving the same path twice keeps the latest version."""
        for impl in _IMPLS:
            with _make_repository(impl) as repo:
                v1 = RepositoryFile(path="a.py", language="python", role=FileRole.UTILITY, tokens=10, hash="h1")
                v2 = RepositoryFile(path="a.py", language="python", role=FileRole.UTILITY, tokens=20, hash="h2")
                asyncio.run(repo.save_file(v1))
                asyncio.run(repo.save_file(v2))
                result = asyncio.run(repo.get_file("a.py"))
                assert result is not None, f"[{impl}] file missing"
                assert result.hash == "h2", f"[{impl}] expected overwrite"
                assert result.tokens == 20, f"[{impl}] expected updated tokens"

    def test_save_and_find_symbol(self) -> None:
        """Saving a symbol then finding by name returns it."""
        for impl in _IMPLS:
            with _make_repository(impl) as repo:
                symbol = Symbol(
                    name="MyClass",
                    kind=SymbolKind.CLASS,
                    file_path="src/models.py",
                    signature="class MyClass:",
                    docstring="A test class.",
                    line_start=10,
                    line_end=25,
                )
                asyncio.run(repo.save_symbol(symbol))
                result = asyncio.run(repo.find_symbols("MyClass"))
                assert len(result) == 1, f"[{impl}] expected 1 symbol"
                assert result[0].name == "MyClass", f"[{impl}] wrong name"
                assert result[0].kind == SymbolKind.CLASS, f"[{impl}] wrong kind"
                assert result[0].file_path == "src/models.py", f"[{impl}] wrong file_path"
                assert result[0].signature == "class MyClass:", f"[{impl}] wrong signature"

    def test_find_nonexistent_symbol(self) -> None:
        """Finding a symbol that was never saved returns empty list."""
        for impl in _IMPLS:
            with _make_repository(impl) as repo:
                result = asyncio.run(repo.find_symbols("Nonexistent"))
                assert result == [], f"[{impl}] expected empty list"

    def test_find_multiple_symbols_same_name(self) -> None:
        """Multiple symbols with the same name are all returned."""
        for impl in _IMPLS:
            with _make_repository(impl) as repo:
                s1 = Symbol(name="foo", kind=SymbolKind.FUNCTION, file_path="a.py", signature="def foo():")
                s2 = Symbol(name="foo", kind=SymbolKind.FUNCTION, file_path="b.py", signature="def foo():")
                asyncio.run(repo.save_symbol(s1))
                asyncio.run(repo.save_symbol(s2))
                result = asyncio.run(repo.find_symbols("foo"))
                assert len(result) == 2, f"[{impl}] expected 2 symbols"

    def test_save_and_get_dependency(self) -> None:
        """Saving a dependency then querying by source path returns it."""
        for impl in _IMPLS:
            with _make_repository(impl) as repo:
                dep = Dependency(
                    source_path="src/main.py",
                    target_path="src/utils.py",
                    kind=DependencyKind.IMPORT,
                )
                asyncio.run(repo.save_dependency(dep))
                result = asyncio.run(repo.get_dependencies("src/main.py"))
                assert len(result) == 1, f"[{impl}] expected 1 dep"
                assert result[0].source_path == "src/main.py", f"[{impl}] wrong source"
                assert result[0].target_path == "src/utils.py", f"[{impl}] wrong target"
                assert result[0].kind == DependencyKind.IMPORT, f"[{impl}] wrong kind"

    def test_get_dependencies_nonexistent(self) -> None:
        """Querying dependencies for an unknown path returns empty list."""
        for impl in _IMPLS:
            with _make_repository(impl) as repo:
                result = asyncio.run(repo.get_dependencies("nonexistent.py"))
                assert result == [], f"[{impl}] expected empty list"

    def test_save_module_no_crash(self) -> None:
        """Saving a module succeeds without raising."""
        for impl in _IMPLS:
            with _make_repository(impl) as repo:
                module = Module(name="core", path="src/core", files=("src/core/main.py", "src/core/utils.py"))
                asyncio.run(repo.save_module(module))

    def test_save_repository(self) -> None:
        """Saving a repository stores all its files."""
        for impl in _IMPLS:
            with _make_repository(impl) as repo:
                repository = Repository(
                    path="/home/user/project",
                    name="my-project",
                    files=(
                        RepositoryFile(path="a.py", language="python", role=FileRole.UTILITY, tokens=10, hash="a"),
                        RepositoryFile(path="b.py", language="python", role=FileRole.UTILITY, tokens=20, hash="b"),
                    ),
                )
                asyncio.run(repo.save_repository(repository))
                result = asyncio.run(repo.list_files())
                assert len(result) == 2, f"[{impl}] expected 2 files from repo"

    def test_save_repository_empty(self) -> None:
        """Saving a repository with no files results in empty index."""
        for impl in _IMPLS:
            with _make_repository(impl) as repo:
                repository = Repository(path="/empty", name="empty")
                asyncio.run(repo.save_repository(repository))
                result = asyncio.run(repo.list_files())
                assert result == [], f"[{impl}] expected empty"

"""Unit tests for application layer DTOs and Application class."""

from __future__ import annotations

import os
from pathlib import Path
from typing import NamedTuple

from arian.application.orchestrator import Application
from arian.application.context import ContextRequest
from arian.application.context import ContextResult
from arian.bootstrap.application import create_application
from arian.infrastructure.config import ArianConfig


class _WriteCall(NamedTuple):
    path: str
    content: str


class _StubOutputWriter:
    """In-memory output writer for testing."""

    def __init__(self) -> None:
        self.calls: list[_WriteCall] = []

    def write(self, a_path: str, a_content: str) -> None:
        self.calls.append(_WriteCall(path=a_path, content=a_content))


class TestContextRequest:
    """Tests for ContextRequest DTO."""

    def test_defaults(self) -> None:
        """Verify default values."""
        req = ContextRequest()
        assert req.task == "general"
        assert req.budget is None
        assert req.output_path == "~/.arian/output/context.md"
        assert req.scope == "merged"
        assert req.paths == ()
        assert req.group == ()
        assert req.query is None

    def test_custom_values(self) -> None:
        """Verify custom values are stored."""
        req = ContextRequest(
            task="bug_fix",
            budget=5000,
            output_path="/tmp/out.md",
            scope="separate",
            paths=("src/", "lib/"),
            group=(("src/", "lib/"),),
            query="auth",
        )
        assert req.task == "bug_fix"
        assert req.budget == 5000
        assert req.paths == ("src/", "lib/")
        assert req.group == (("src/", "lib/"),)

    def test_frozen(self) -> None:
        """Verify DTO is immutable."""
        req = ContextRequest()
        import pytest

        with pytest.raises(AttributeError):
            req.task = "feature"  # type: ignore[misc]


class TestContextResult:
    """Tests for ContextResult DTO."""

    def test_creation(self) -> None:
        """Verify ContextResult stores values."""
        result = ContextResult(
            output_path=Path("/tmp/context.md"),
            total_files=10,
            total_tokens=5000,
            elapsed_seconds=1.23,
        )
        assert result.output_path == Path("/tmp/context.md")
        assert result.total_files == 10
        assert result.total_tokens == 5000
        assert result.elapsed_seconds == 1.23

    def test_frozen(self) -> None:
        """Verify DTO is immutable."""
        result = ContextResult(
            output_path=Path("/tmp/context.md"),
            total_files=10,
            total_tokens=5000,
            elapsed_seconds=1.0,
        )
        import pytest

        with pytest.raises(AttributeError):
            result.total_files = 20  # type: ignore[misc]


class TestCreateApplication:
    """Tests for bootstrap factory."""

    def test_create_default(self) -> None:
        """Verify factory creates a wired Application with defaults."""
        app = create_application()
        assert isinstance(app, Application)

    def test_create_with_config(self) -> None:
        """Verify factory accepts custom config."""
        config = ArianConfig()
        app = create_application(config)
        assert isinstance(app, Application)


class TestApplicationBuildContext:
    """Integration tests for Application.build_context."""

    async def test_build_empty_directory(self, tmp_path: Path) -> None:
        """Verify building context for empty directory produces zero files."""
        app = create_application()
        request = ContextRequest(
            paths=(str(tmp_path),),
            output_path=str(tmp_path / "out.md"),
        )
        result = await app.build_context(request)
        assert result.total_files == 0
        assert result.total_tokens == 0
        assert result.output_path.exists()

    async def test_build_with_files(self, tmp_path: Path) -> None:
        """Verify building context with files produces output."""
        (tmp_path / "hello.py").write_text("def hello():\n    return 'world'\n")

        original_cwd: Path = Path.cwd()
        try:
            os.chdir(tmp_path)
            # Composition root captures cwd; create after chdir.
            app = create_application()
            request = ContextRequest(
                paths=("hello.py",),
                output_path=str(tmp_path / "out.md"),
            )
            result = await app.build_context(request)
        finally:
            os.chdir(original_cwd)

        assert result.total_files >= 1
        assert result.total_tokens > 0
        assert result.elapsed_seconds > 0
        assert result.output_path.exists()
        content = result.output_path.read_text()
        assert "hello.py" in content

    async def test_build_returns_elapsed_time(self, tmp_path: Path) -> None:
        """Verify elapsed_seconds is positive."""
        app = create_application()
        request = ContextRequest(
            paths=(str(tmp_path),),
            output_path=str(tmp_path / "out.md"),
        )
        result = await app.build_context(request)
        assert result.elapsed_seconds >= 0

    async def test_output_writer_called_with_correct_args(self, tmp_path: Path) -> None:
        """Verify OutputWriterProtocol.write receives correct path and content."""
        (tmp_path / "hello.py").write_text("def hello():\n    return 'world'\n")
        stub = _StubOutputWriter()

        original_cwd: Path = Path.cwd()
        try:
            os.chdir(tmp_path)
            wired = create_application()
            app = Application(
                a_builder=wired._builder,
                a_renderer=wired._renderer,
                a_output=stub,
                a_root=tmp_path,
            )
            request = ContextRequest(
                paths=("hello.py",),
                output_path=str(tmp_path / "out.md"),
            )
            await app.build_context(request)
        finally:
            os.chdir(original_cwd)

        assert len(stub.calls) == 1
        call = stub.calls[0]
        assert call.path == str(tmp_path / "out.md")
        assert "hello.py" in call.content
        assert len(call.content) > 0

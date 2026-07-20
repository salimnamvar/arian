"""Tests for domain shared event hook protocols."""

from __future__ import annotations

from arian.domain.shared.events import ErrorHook
from arian.domain.shared.events import ProgressHook


def test_progress_hook_is_protocol() -> None:
    """Test ProgressHook is a Protocol."""
    from typing import Protocol

    assert issubclass(ProgressHook, Protocol)


def test_error_hook_is_protocol() -> None:
    """Test ErrorHook is a Protocol."""
    from typing import Protocol

    assert issubclass(ErrorHook, Protocol)


def test_progress_hook_structural_subtyping() -> None:
    """Test a concrete class satisfies ProgressHook via structural subtyping."""

    class Collector:
        """Stub progress collector."""

        def __init__(self) -> None:
            self.calls: list[tuple[str, int, int]] = []

        def on_progress(self, a_stage: str, a_current: int, a_total: int) -> None:
            self.calls.append((a_stage, a_current, a_total))

    collector: ProgressHook = Collector()
    collector.on_progress("chunking", 2, 10)

    assert collector.calls == [("chunking", 2, 10)]


def test_error_hook_structural_subtyping() -> None:
    """Test a concrete class satisfies ErrorHook via structural subtyping."""

    class Recorder:
        """Stub error recorder."""

        def __init__(self) -> None:
            self.errors: list[tuple[str, Exception]] = []

        def on_error(self, a_stage: str, a_error: Exception) -> None:
            self.errors.append((a_stage, a_error))

    recorder: ErrorHook = Recorder()
    exc = ValueError("bad input")
    recorder.on_error("parsing", exc)

    assert recorder.errors == [("parsing", exc)]


def test_progress_hook_def() -> None:
    """Test a plain function satisfies ProgressHook."""
    calls: list[tuple[str, int, int]] = []

    def hook(a_stage: str, a_current: int, a_total: int) -> None:
        calls.append((a_stage, a_current, a_total))

    hook("render", 0, 5)
    assert calls == [("render", 0, 5)]


def test_error_hook_def() -> None:
    """Test a plain function satisfies ErrorHook."""
    calls: list[tuple[str, Exception]] = []

    def hook(a_stage: str, a_error: Exception) -> None:
        calls.append((a_stage, a_error))

    exc = RuntimeError("timeout")
    hook("network", exc)
    assert calls == [("network", exc)]


def test_progress_hook_multiple_calls() -> None:
    """Test a collector accumulates multiple progress calls."""

    class Collector:
        """Stub progress collector."""

        def __init__(self) -> None:
            self.calls: list[tuple[str, int, int]] = []

        def on_progress(self, a_stage: str, a_current: int, a_total: int) -> None:
            self.calls.append((a_stage, a_current, a_total))

    hook: ProgressHook = Collector()
    hook.on_progress("scan", 0, 3)
    hook.on_progress("scan", 1, 3)
    hook.on_progress("scan", 2, 3)

    assert len(hook.calls) == 3


def test_error_hook_multiple_calls() -> None:
    """Test a recorder accumulates multiple error calls."""

    class Recorder:
        """Stub error recorder."""

        def __init__(self) -> None:
            self.errors: list[tuple[str, Exception]] = []

        def on_error(self, a_stage: str, a_error: Exception) -> None:
            self.errors.append((a_stage, a_error))

    hook: ErrorHook = Recorder()
    hook.on_error("a", ValueError("v1"))
    hook.on_error("b", RuntimeError("v2"))

    assert len(hook.errors) == 2

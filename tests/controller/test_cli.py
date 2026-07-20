"""CLI integration tests for the arian command.

Verifies end-to-end CLI behavior: help text, option parsing, error handling,
and output defaults after the budget/async-logging refactoring.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(a_text: str) -> str:
    """Remove ANSI escape sequences from terminal output."""
    return _ANSI_RE.sub("", a_text)


def _run_cli(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    """Run the arian CLI as a subprocess and return the result.

    Args:
        *args: Arguments passed after ``python -m arian``.
        cwd: Optional working directory for the subprocess.

    Returns:
        CompletedProcess with captured stdout and stderr (ANSI stripped).
    """
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    env["FORCE_COLOR"] = "0"
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "arian", *args],
        capture_output=True,
        check=False,
        text=True,
        cwd=cwd,
        timeout=30,
        env=env,
    )
    return subprocess.CompletedProcess(
        args=result.args,
        returncode=result.returncode,
        stdout=_strip_ansi(result.stdout),
        stderr=_strip_ansi(result.stderr),
    )


@pytest.mark.integration
class TestCliHelp:
    """Tests for ``arian --help`` top-level help output."""

    def test_cli_help(self) -> None:
        """Verify ``arian --help`` exits cleanly and mentions key terms."""
        result = _run_cli("--help")

        assert result.returncode == 0
        assert "arian" in result.stdout.lower()
        assert "context" in result.stdout.lower()


@pytest.mark.integration
class TestCliContextHelp:
    """Tests for ``arian context --help`` option presence and defaults."""

    def test_cli_context_help(self) -> None:
        """Verify help text contains new options and omits removed ones.

        After the refactoring, ``--budget`` replaced ``--max-tokens``/``--per-chunk``,
        and ``--async-logging`` was removed entirely.
        """
        result = _run_cli("context", "--help")

        assert result.returncode == 0
        output = result.stdout

        # New options present
        assert "--budget" in output
        assert "--query" in output
        assert "reserved" in output.lower()
        assert "--output" in output
        assert "~/.arian/output/context.md" in output

        # Removed options absent
        assert "--max-tokens" not in output
        assert "--per-chunk" not in output
        assert "--async-logging" not in output


@pytest.mark.integration
class TestCliContextMissingPaths:
    """Tests for ``arian context`` invoked without explicit paths."""

    def test_cli_context_missing_paths(self, tmp_path: str) -> None:
        """Verify ``arian context`` with no arguments and empty dir exits cleanly.

        When no paths are provided the CLI defaults to the current working
        directory.  An empty directory should produce zero files without crashing.
        """
        result = _run_cli(cwd=tmp_path)

        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "0 files" in combined or "0 tokens" in combined


@pytest.mark.integration
class TestCliContextInvalidBudget:
    """Tests for ``--budget`` rejecting non-numeric input."""

    def test_cli_context_invalid_budget(self, tmp_path: str) -> None:
        """Verify a non-numeric budget string causes a non-zero exit."""
        (tmp_path / "dummy.txt").write_text("hello\n")
        result = _run_cli("--budget", "abc", "dummy.txt", cwd=tmp_path)

        assert result.returncode != 0


@pytest.mark.integration
class TestCliContextBudgetNone:
    """Tests for ``--budget none`` being treated as unlimited."""

    def test_cli_context_budget_none(self, tmp_path: str) -> None:
        """Verify ``--budget none`` does not crash on budget parsing.

        The parser should translate ``none`` to unlimited and continue
        normally (possibly producing an empty context if no files match).
        """
        (tmp_path / "dummy.txt").write_text("hello\n")
        result = _run_cli("--budget", "none", "dummy.txt", cwd=tmp_path)

        # Should not fail due to budget parsing
        assert "Invalid budget" not in result.stderr


@pytest.mark.integration
class TestCliVersion:
    """Tests for version-related CLI behavior."""

    def test_cli_version(self) -> None:
        """Verify ``arian --version`` is handled gracefully.

        The CLI does not currently expose a ``--version`` flag.
        This test asserts that Typer rejects the unknown option with a
        non-zero exit code and a helpful error message.
        """
        result = _run_cli("--version")

        assert result.returncode != 0
        assert "no such option" in result.stderr.lower() or "error" in result.stderr.lower()

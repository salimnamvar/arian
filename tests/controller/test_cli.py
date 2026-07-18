"""Integration tests for CLI controller."""

from __future__ import annotations

from typer.testing import CliRunner

from arian.controller.cli import app


def test_cli_help() -> None:
    """Test CLI help command."""
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Build context" in result.output


def test_cli_build_command() -> None:
    """Test CLI build command with valid input."""
    runner = CliRunner()
    # Filter out command name from args (click quirk for variadic args)
    result = runner.invoke(app, ["build", "src/arian", "-o", "/tmp/arian_cli_test"])
    # Output goes to stderr via logging, check exit code and output content
    assert result.exit_code == 0
    assert "Build complete" in result.output or "Collected" in result.output


def test_cli_build_with_explicit_inputs() -> None:
    """Test CLI build command filters command name from inputs."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "build",
            "src/arian",
            "-o",
            "/tmp/arian_cli_test2",
            "--mode",
            "aggregate",
        ],
    )
    # Should succeed because we filter out the 'build' command name
    assert "Build complete" in result.output or "Collected" in result.output or result.exit_code == 0

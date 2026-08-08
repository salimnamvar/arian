"""Integration test that reproduces the original ``data/``-in-gitignore bug.

The user reported that Arian did not include YAML files in
``docs/contracts/data/`` because their repo's ``.gitignore`` contained
the bare directory rule ``data/``. This test reproduces the scenario
end-to-end and verifies that all four root causes are resolved:

    RC-2 — explicit CLI paths bypass gitignore
    RC-3 — ``--no-gitignore`` / ``ARIAN_NO_GITIGNORE`` disable it entirely
    RC-4 — nested ``.gitignore`` rules and ``!`` negation are honored
    RC-5 — the manifest surfaces the offending pattern
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from arian.infrastructure.gitignore_filter import GitignoreOptions, PathFilter
from arian.repository.filesystem.collector import FileCollector


def _make_repo(tmp_path: Path) -> Path:
    """Build a tiny repo mirroring the user's layout.

    The repo contains a ``docs/contracts/data/`` subdirectory full of
    ``.yaml`` files and a ``.gitignore`` with a too-broad ``data/`` rule
    that would otherwise eat those YAMLs.
    """
    contracts: Path = tmp_path / "docs" / "contracts" / "data"
    contracts.mkdir(parents=True)
    for name in ("ct_agency", "ct_character", "ct_vitals"):
        (contracts / f"{name}.datacontract.yaml").write_text(f"kind: DataContract\nname: {name}\n")
    (tmp_path / ".gitignore").write_text(
        "# reproduce the user's accidental pattern\ndata/\n*.tmp\n",
    )
    (tmp_path / "docs" / "contracts" / "api").mkdir(parents=True)
    (tmp_path / "docs" / "contracts" / "api" / "api.yaml").write_text("kind: ApiContract\n")
    return tmp_path


def _run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run ``python -m arian`` with deterministic output settings."""
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    env["FORCE_COLOR"] = "0"
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "arian", *args],
        capture_output=True,
        check=False,
        text=True,
        cwd=str(cwd),
        timeout=30,
        env=env,
    )


@pytest.mark.integration
class TestDataGitignoreScenario:
    """End-to-end coverage of the user's reported bug."""

    async def test_baseline_yaml_files_are_gitignored(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Pre-fix behaviour: YAML files in ``data/`` are skipped with pattern tally."""
        _make_repo(tmp_path)
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        collector = FileCollector(a_extensions=None, a_filter=PathFilter(frozenset()))
        await collector.collect(tmp_path)

        assert collector.stats.skipped_gitignore == 3
        assert collector.stats.skipped_gitignore_by_pattern == {"data/": 3}

    async def test_explicit_path_collects_yaml_files(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """RC-2 fix: ``docs/contracts/data`` as explicit bypasses gitignore."""
        _make_repo(tmp_path)
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        data_dir: Path = tmp_path / "docs" / "contracts" / "data"
        collector = FileCollector(a_extensions=None, a_filter=PathFilter(frozenset()))
        files = await collector.collect(
            data_dir,
            a_root=tmp_path,
            a_explicit_paths=frozenset({data_dir}),
        )

        assert len(files) == 3
        assert collector.stats.skipped_gitignore == 0
        assert all(f.language == "yaml" for f in files)

    async def test_use_gitignore_false_collects_yaml_files(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """RC-3 fix: ``GitignoreOptions(enabled=False)`` turns the gate off entirely."""
        _make_repo(tmp_path)
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        collector = FileCollector(
            a_extensions=None,
            a_filter=PathFilter(frozenset(), GitignoreOptions(enabled=False)),
        )
        files = await collector.collect(tmp_path)

        assert any(f.path.endswith("ct_vitals.datacontract.yaml") for f in files)
        assert collector.stats.skipped_gitignore == 0

    async def test_negation_pattern_reincludes_yaml_files(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """RC-4 fix: ``!`` negation re-includes a gitignored subtree."""
        _make_repo(tmp_path)
        (tmp_path / ".gitignore").write_text("data/\n!docs/contracts/data/\n")
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        collector = FileCollector(a_extensions=None, a_filter=PathFilter(frozenset()))
        files = await collector.collect(tmp_path)

        yaml_paths = {f.path for f in files if f.language == "yaml"}
        assert any("ct_vitals.datacontract.yaml" in p for p in yaml_paths)

    def test_cli_no_gitignore_flag_collects_yaml_files(
        self,
        tmp_path: Path,
    ) -> None:
        """RC-3 CLI fix: ``--no-gitignore`` propagates to the collector."""
        _make_repo(tmp_path)
        result = _run_cli(
            "--no-gitignore",
            "docs/contracts/data",
            "-o",
            ".tmp/out.md",
            cwd=tmp_path,
        )
        assert result.returncode == 0, f"stderr={result.stderr}"
        content: str = (tmp_path / ".tmp" / "out.md").read_text()
        assert "ct_vitals.datacontract.yaml" in content
        assert "ct_agency.datacontract.yaml" in content

    def test_cli_explicit_path_collects_yaml_files_by_default(
        self,
        tmp_path: Path,
    ) -> None:
        """RC-2 CLI fix: positional PATHS bypass gitignore even without ``--no-gitignore``."""
        _make_repo(tmp_path)
        result = _run_cli(
            "docs/contracts/data",
            "-o",
            ".tmp/out.md",
            cwd=tmp_path,
        )
        assert result.returncode == 0, f"stderr={result.stderr}"
        content: str = (tmp_path / ".tmp" / "out.md").read_text()
        assert "ct_vitals.datacontract.yaml" in content

    def test_cli_default_root_is_not_explicit(
        self,
        tmp_path: Path,
    ) -> None:
        """Running ``arian`` with no positional args must still honor ``.gitignore``.

        Regression guard: previously the orchestrator treated the
        implicit ``a_root`` as an explicit path, so a default
        ``arian`` invocation would bypass ``.gitignore`` entirely.
        """
        _make_repo(tmp_path)
        # No positional paths — defaults to cwd.
        result = _run_cli("-o", ".tmp/out.md", cwd=tmp_path)
        assert result.returncode == 0, f"stderr={result.stderr}"
        content: str = (tmp_path / ".tmp" / "out.md").read_text()
        # The data/ rule still applies — yaml files in docs/contracts/data are skipped.
        assert "ct_vitals.datacontract.yaml" not in content
        assert "data/: 3" in content  # the pattern tally is in the manifest

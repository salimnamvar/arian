"""Git repository analyzer."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class GitAnalyzer:
    """Analyzes git repository metadata.

    Provides async methods to extract git-specific information
    like branch, commit history, and changed files.
    """

    async def get_branch(self, a_path: Path) -> str:
        """Get the current git branch name.

        Args:
            a_path: Repository root path.

        Returns:
            Branch name or empty string if not a git repo.
        """
        result: str = ""
        try:
            process: asyncio.subprocess.Process = await asyncio.create_subprocess_exec(
                "git",
                "rev-parse",
                "--abbrev-ref",
                "HEAD",
                cwd=str(a_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout: bytes
            _stderr: bytes
            stdout, _stderr = await process.communicate()
            if process.returncode == 0:
                result = stdout.decode().strip()
        except (OSError, TimeoutError):
            logger.debug("Cannot get git branch for %s", a_path)
        return result

    async def get_changed_files(self, a_path: Path) -> list[str]:
        """Get list of changed files since last commit.

        Args:
            a_path: Repository root path.

        Returns:
            List of changed file paths.
        """
        result: list[str] = []
        try:
            process: asyncio.subprocess.Process = await asyncio.create_subprocess_exec(
                "git",
                "diff",
                "--name-only",
                "HEAD~1",
                cwd=str(a_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout: bytes
            _stderr: bytes
            stdout, _stderr = await process.communicate()
            if process.returncode == 0:
                result = [f for f in stdout.decode().strip().splitlines() if f]
        except (OSError, TimeoutError):
            logger.debug("Cannot get git changes for %s", a_path)
        return result

"""Context builder for assembling final context output."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path

from arian.domain.context.models import ContextPlan
from arian.domain.context.models import ContextTask
from arian.domain.repository.models import FileContent
from arian.domain.repository.models import RepositoryFile
from arian.domain.shared.enums import TokenBudget
from arian.repositories.filesystem.collector import FileCollector
from arian.repositories.index.protocols import RepositoryIndexProtocol
from arian.services.analyzer.python_analyzer import PythonAnalyzer
from arian.services.planner.context_planner import ContextPlanner

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds context by collecting, analyzing, planning, and loading content.

    Orchestrates the full pipeline from repository scanning to
    context output generation.

    Attributes:
        _collector: File collector for repository scanning.
        _index: Repository index for metadata storage.
        _analyzer: Python analyzer for symbol extraction.
        _planner: Context planner for file selection.
    """

    def __init__(
        self,
        a_collector: FileCollector,
        a_index: RepositoryIndexProtocol,
        a_analyzer: PythonAnalyzer | None = None,
        a_planner: ContextPlanner | None = None,
    ) -> None:
        """Initialize context builder.

        Args:
            a_collector: File collector for repository scanning.
            a_index: Repository index for metadata storage.
            a_analyzer: Optional Python analyzer (defaults to new instance).
            a_planner: Optional context planner (defaults to new instance).
        """
        self._collector: FileCollector = a_collector
        self._index: RepositoryIndexProtocol = a_index
        self._analyzer: PythonAnalyzer = a_analyzer if a_analyzer is not None else PythonAnalyzer()
        self._planner: ContextPlanner = a_planner if a_planner is not None else ContextPlanner()

    async def build(
        self,
        a_path: Path,
        a_task: ContextTask,
        a_budget: TokenBudget,
        a_query: str | None = None,
    ) -> ContextPlan:
        """Build a context plan from a repository path.

        Pipeline: collect files -> store metadata -> plan context.

        Args:
            a_path: Repository root path.
            a_task: The context task type.
            a_budget: Token budget constraints.
            a_query: Optional query for relevance matching.

        Returns:
            ContextPlan with chunks and metadata.
        """
        logger.info("Building context for task=%s, path=%s", a_task.value, a_path)

        files: list[RepositoryFile] = await self._collector.collect(a_path)
        logger.debug("Collected %d files", len(files))

        for repo_file in files:
            await self._index.save_file(repo_file)

        plan: ContextPlan = self._planner.plan(files, a_task, a_budget, a_query)
        logger.info(
            "Planned %d files in %d chunks (%d tokens)",
            plan.total_files,
            len(plan.chunks),
            plan.total_tokens,
        )

        return plan

    async def load_content(
        self,
        a_plan: ContextPlan,
        a_root: Path,
    ) -> dict[str, FileContent]:
        """Load file content for all files in the plan.

        Args:
            a_plan: Context plan with file references.
            a_root: Repository root path.

        Returns:
            Mapping of file path to FileContent.
        """
        content_map: dict[str, FileContent] = {}
        load_tasks: list[asyncio.Task[FileContent | None]] = []

        for chunk in a_plan.chunks:
            for planned_file in chunk.files:
                if planned_file.path not in content_map:
                    load_tasks.append(
                        asyncio.create_task(self._load_single(a_root / planned_file.path)),
                    )

        results: list[FileContent | None] = list(await asyncio.gather(*load_tasks))
        for content in results:
            if content is not None:
                content_map[content.path] = content

        logger.debug("Loaded content for %d files", len(content_map))
        return content_map

    async def _load_single(self, a_path: Path) -> FileContent | None:
        """Load content from a single file.

        Args:
            a_path: Full path to the file.

        Returns:
            FileContent if successful, None on error.
        """
        result: FileContent | None = None
        try:
            content: str = await asyncio.to_thread(
                a_path.read_text,
                encoding="utf-8",
                errors="ignore",
            )
            content_hash: str = await asyncio.to_thread(
                lambda: hashlib.sha256(content.encode()).hexdigest()[:16],
            )
            result = FileContent(
                path=str(a_path),
                content=content,
                hash=content_hash,
            )
        except OSError:
            logger.warning("Cannot read file: %s", a_path)
        return result

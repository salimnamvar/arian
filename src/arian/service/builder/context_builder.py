"""Context builder for assembling final context output."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path

from arian.domain.context.models import ContextPlan
from arian.domain.context.models import ContextTask
from arian.domain.context.models import MaterializedChunk
from arian.domain.exceptions import ContextBuilderError
from arian.domain.exceptions import InputError
from arian.domain.repository.models import FileContent
from arian.domain.repository.models import RepositoryFile
from arian.domain.shared.constants import DEFAULT_MAX_CONCURRENT_LOADS
from arian.domain.shared.constants import MAX_COLLECTED_FILES
from arian.domain.shared.enums import ConcurrencyPolicy
from arian.domain.shared.enums import TokenBudget
from arian.domain.shared.events import PipelineProgressProtocol
from arian.domain.shared.security import is_binary
from arian.domain.shared.security import redact_secrets
from arian.repository.filesystem.protocols import FileCollectorProtocol
from arian.repository.index.protocols import RepositoryIndexProtocol
from arian.service.context.materializer import ContextMaterializer
from arian.service.planner.context_planner import ContextPlanner

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds context by collecting, analyzing, planning, materializing, and rendering.

    Pipeline: collect -> plan -> load -> materialize -> render -> write.

    Extension points (see PipelineStageProtocol):
      Each stage is a constructor-injected collaborator. To add or replace a
      stage:
        1. Create a service implementing the desired logic.
        2. Inject it via the constructor (or extend this class).
        3. Call it from ``build()``, ``load_content()``, or ``materialize()``.
        4. Optionally attach a PipelineProgressProtocol for visibility.

    Pipeline Stages:
      - Collect: Scans the repository for files matching configured patterns.
      - Plan: Selects and prioritizes files based on task and budget.
      - Load: Reads file content from disk for planned files.
      - Materialize: Applies compression and formatting to produce chunks.

    Attributes:
        _collector: File collector for repository scanning.
        _index: Repository index for metadata storage.
        _planner: Context planner for file selection.
        _materializer: Context materializer for compression.
        _progress: Optional progress reporter for pipeline stages.
        _concurrency: How parallel file loads are executed.
        _max_concurrent: Semaphore limit when policy is BOUNDED.
    """

    def __init__(
        self,
        a_collector: FileCollectorProtocol,
        a_index: RepositoryIndexProtocol,
        a_planner: ContextPlanner,
        a_materializer: ContextMaterializer,
        a_progress: PipelineProgressProtocol | None = None,
        a_concurrency: ConcurrencyPolicy = ConcurrencyPolicy.BOUNDED,
        a_max_concurrent: int = DEFAULT_MAX_CONCURRENT_LOADS,
    ) -> None:
        """Initialize context builder.

        Args:
            a_collector: File collector protocol for repository scanning.
            a_index: Repository index for metadata storage.
            a_planner: Context planner for file selection.
            a_materializer: Context materializer for compression.
            a_progress: Optional progress reporter for pipeline stages.
            a_concurrency: Parallelism policy for content loading.
            a_max_concurrent: Max concurrent reads when policy is BOUNDED.
        """
        self._collector: FileCollectorProtocol = a_collector
        self._index: RepositoryIndexProtocol = a_index
        self._planner: ContextPlanner = a_planner
        self._materializer: ContextMaterializer = a_materializer
        self._progress: PipelineProgressProtocol | None = a_progress
        self._concurrency: ConcurrencyPolicy = a_concurrency
        self._max_concurrent: int = a_max_concurrent

    async def build(
        self,
        a_path: Path,
        a_task: ContextTask,
        a_budget: TokenBudget,
        a_query: str | None = None,
        a_root: Path | None = None,
        a_input_paths: list[Path] | None = None,
    ) -> ContextPlan:
        """Build a context plan from a repository path.

        Pipeline: collect files -> store metadata -> plan context.

        Args:
            a_path: Repository root path.
            a_task: The context task type.
            a_budget: Token budget constraints.
            a_query: Optional query for relevance matching.
            a_root: Root for computing relative paths. Defaults to a_path.
            a_input_paths: Optional list of specific input paths to scan.

        Returns:
            ContextPlan with chunks and metadata.
        """
        logger.info("Building context for task=%s, path=%s", a_task.value, a_path)

        root: Path = a_root if a_root is not None else a_path
        files: list[RepositoryFile] = []
        seen: set[str] = set()
        sources: list[Path] = a_input_paths if a_input_paths is not None else [a_path]

        try:
            await self._collect_files(sources, root, files, seen)
        except Exception as e:
            msg = f"File collection failed for {a_path}: {e}"
            raise ContextBuilderError(msg, a_cause=e) from e

        logger.debug("Collected %d files", len(files))
        self._notify_complete("collect")

        if len(files) > MAX_COLLECTED_FILES:
            msg = f"Too many files collected ({len(files)}), limit is {MAX_COLLECTED_FILES}"
            raise InputError(msg)

        self._notify_start("plan", 1)
        for repo_file in files:
            await self._index.save_file(repo_file)

        try:
            plan: ContextPlan = self._planner.plan(files, a_task, a_budget, a_query)
            plan.validate()
        except Exception as e:
            msg = f"Context planning failed: {e}"
            raise ContextBuilderError(msg, a_cause=e) from e

        all_paths: tuple[str, ...] = tuple(f.path for f in files)
        plan = ContextPlan(
            chunks=plan.chunks,
            total_tokens=plan.total_tokens,
            total_files=plan.total_files,
            task=plan.task,
            query=plan.query,
            metadata=plan.metadata,
            repository_files=all_paths,
        )

        logger.info(
            "Planned %d files in %d chunks (%d tokens) from %d collected",
            plan.total_files,
            len(plan.chunks),
            plan.total_tokens,
            len(all_paths),
        )
        self._notify_complete("plan")

        return plan

    async def load_content(
        self,
        a_plan: ContextPlan,
        a_root: Path,
    ) -> tuple[dict[str, FileContent], tuple[str, ...]]:
        """Load file content for all files in the plan.

        Honours ConcurrencyPolicy for parallel reads. Skips binary files and
        unreadable paths; secrets in content are redacted at load time.

        Args:
            a_plan: Context plan with file references.
            a_root: Repository root path.

        Returns:
            Tuple of content mapping and list of skipped file paths.
        """
        content_map: dict[str, FileContent] = {}
        skipped: list[str] = []
        paths: list[tuple[Path, str]] = []

        seen_paths: set[str] = set()
        for chunk in a_plan.chunks:
            for planned_file in chunk.files:
                if planned_file.path not in seen_paths:
                    paths.append((a_root / planned_file.path, planned_file.path))
                    seen_paths.add(planned_file.path)

        self._notify_start("load", len(paths))
        results = await self._load_all(paths)
        for i, (result, rel_path) in enumerate(zip(results, (p[1] for p in paths), strict=True)):
            if result is not None:
                content_map[result.path] = result
            else:
                skipped.append(rel_path)
            self._notify_progress("load", i + 1, len(results))

        logger.debug(
            "Loaded content for %d files, skipped %d",
            len(content_map),
            len(skipped),
        )
        self._notify_complete("load")
        return content_map, tuple(skipped)

    def materialize(
        self,
        a_plan: ContextPlan,
        a_content: dict[str, FileContent],
    ) -> tuple[MaterializedChunk, ...]:
        """Materialize a context plan with compressed content.

        Args:
            a_plan: Context plan with compression decisions.
            a_content: Mapping of file path to FileContent.

        Returns:
            Tuple of MaterializedChunk with compressed content.
        """
        self._notify_start("materialize", len(a_plan.chunks))
        result: tuple[MaterializedChunk, ...] = self._materializer.materialize(a_plan, a_content)
        self._notify_complete("materialize")
        logger.debug("Materialized %d chunks", len(result))
        return result

    async def _load_all(
        self,
        a_paths: list[tuple[Path, str]],
    ) -> list[FileContent | None]:
        """Load all paths according to the configured concurrency policy.

        Args:
            a_paths: List of (absolute_path, relative_path) pairs.

        Returns:
            List of FileContent or None aligned with a_paths.
        """
        results: list[FileContent | None] = []
        if a_paths:
            if self._concurrency == ConcurrencyPolicy.SEQUENTIAL:
                for abs_path, rel_path in a_paths:
                    results.append(await self._load_single(abs_path, rel_path))
            elif self._concurrency == ConcurrencyPolicy.BOUNDED:
                semaphore = asyncio.Semaphore(self._max_concurrent)
                results = list(
                    await asyncio.gather(
                        *(self._load_single_bounded(p, r, semaphore) for p, r in a_paths),
                    ),
                )
            else:
                # CONCURRENT — unbounded gather
                results = list(
                    await asyncio.gather(*(self._load_single(p, r) for p, r in a_paths)),
                )
        return results

    async def _load_single_bounded(
        self,
        a_path: Path,
        a_rel_path: str,
        a_semaphore: asyncio.Semaphore,
    ) -> FileContent | None:
        """Load a single file under a concurrency semaphore.

        Args:
            a_path: Full path to the file.
            a_rel_path: Relative path for the content map key.
            a_semaphore: Shared concurrency limiter.

        Returns:
            FileContent if successful, None on skip/error.
        """
        async with a_semaphore:
            return await self._load_single(a_path, a_rel_path)

    async def _load_single(self, a_path: Path, a_rel_path: str) -> FileContent | None:
        """Load content from a single file with retry, binary check, and redaction.

        Transient ``OSError`` is retried with exponential backoff (3 attempts).
        Binary files and permanent read failures are skipped (returned as None).

        Args:
            a_path: Full path to the file.
            a_rel_path: Relative path for the content map key.

        Returns:
            FileContent if successful, None on error or binary content.
        """
        result: FileContent | None = None
        raw: bytes | None = None
        last_error: OSError | None = None
        for attempt in range(3):
            try:
                raw = await asyncio.to_thread(a_path.read_bytes)
                last_error = None
                break
            except OSError as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(0.05 * (2**attempt))

        if last_error is not None or raw is None:
            logger.warning("Cannot read file: %s", a_path)
        elif is_binary(raw):
            logger.warning("Skipping binary file: %s", a_path)
        else:
            content: str = redact_secrets(raw.decode("utf-8", errors="ignore"))
            content_hash: str = await asyncio.to_thread(
                lambda: hashlib.sha256(content.encode()).hexdigest()[:16],
            )
            result = FileContent(
                path=a_rel_path,
                content=content,
                hash=content_hash,
            )
        return result

    async def _collect_files(
        self,
        a_sources: list[Path],
        a_root: Path,
        a_files: list[RepositoryFile],
        a_seen: set[str],
    ) -> None:
        """Collect files from all sources with progress reporting.

        Args:
            a_sources: List of source paths to collect from.
            a_root: Root path for relative path computation.
            a_files: Output list to append collected files to.
            a_seen: Set of already-seen paths to avoid duplicates.
        """
        self._notify_start("collect", len(a_sources))
        for i, source in enumerate(a_sources):
            collected = await self._collector.collect(source, a_root=a_root)
            for f in collected:
                if f.path not in a_seen:
                    a_files.append(f)
                    a_seen.add(f.path)
            self._notify_progress("collect", i + 1, len(a_sources))

    def _notify_start(self, a_stage: str, a_total: int) -> None:
        """Notify progress hook of stage start, if present.

        Args:
            a_stage: Stage name.
            a_total: Total work units in the stage.
        """
        if self._progress:
            self._progress.on_stage_start(a_stage, a_total)

    def _notify_progress(self, a_stage: str, a_current: int, a_total: int) -> None:
        """Notify progress hook of stage progress, if present.

        Args:
            a_stage: Stage name.
            a_current: Current progress index.
            a_total: Total work units in the stage.
        """
        if self._progress:
            self._progress.on_stage_progress(a_stage, a_current, a_total)

    def _notify_complete(self, a_stage: str) -> None:
        """Notify progress hook of stage completion, if present.

        Args:
            a_stage: Stage name.
        """
        if self._progress:
            self._progress.on_stage_complete(a_stage)

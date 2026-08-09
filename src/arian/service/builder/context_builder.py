"""Context builder for assembling final context output."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from dataclasses import field
import hashlib
import logging
from pathlib import Path

from arian.domain.context.models import BuildRequest
from arian.domain.context.models import ContextPlan
from arian.domain.context.models import ContextTask
from arian.domain.context.models import MaterializedChunk
from arian.domain.protocols import ContentLoadData
from arian.domain.protocols import ContextMaterializerProtocol
from arian.domain.protocols import ContextPlannerProtocol
from arian.domain.repository.models import CollectionStats
from arian.domain.repository.models import FileContent
from arian.domain.repository.models import RepositoryFile
from arian.domain.shared.enums import ConcurrencyPolicy
from arian.domain.shared.enums import TokenBudget
from arian.domain.shared.events import PipelineProgressProtocol
from arian.domain.shared.result import Result
from arian.domain.shared.security import is_binary
from arian.domain.shared.security import redact_secrets
from arian.domain.shared.security import sanitize_error_message
from arian.infrastructure.config import DomainLimitsConfig
from arian.infrastructure.config import RetryConfig
from arian.infrastructure.config import SecurityConfig
from arian.repository.filesystem.protocols import FileCollectorProtocol
from arian.repository.index.protocols import RepositoryIndexProtocol
from arian.service.base import BaseServiceModule
from arian.util.base import ModuleMetadata

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContextBuilderOptions:
    """Optional collaborators and concurrency knobs for :class:`ContextBuilder`.

    Grouping these into a single object keeps the constructor's
    argument list short and prevents the public surface from drifting
    when new tuning knobs are added.

    Attributes:
        progress: Optional progress reporter. ``None`` disables
            progress notifications.
        concurrency: Parallelism policy for content loading.
        max_concurrent: Max concurrent reads when the policy is
            :attr:`ConcurrencyPolicy.BOUNDED`.
        max_collected_files: Hard cap on files the planner accepts
            in a single collection pass.
        retry: File-read retry policy.
        security: Security configuration (used by ``redact_secrets``).
    """

    progress: PipelineProgressProtocol | None = None
    concurrency: ConcurrencyPolicy = ConcurrencyPolicy.BOUNDED
    max_concurrent: int = DomainLimitsConfig().default_max_concurrent_loads
    max_collected_files: int = DomainLimitsConfig().max_collected_files
    retry: RetryConfig = field(default_factory=RetryConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)


class ContextBuilder(BaseServiceModule):
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
        _options: Concurrency / security / retry options.
    """

    def __init__(
        self,
        a_collector: FileCollectorProtocol,
        a_index: RepositoryIndexProtocol,
        a_planner: ContextPlannerProtocol,
        a_materializer: ContextMaterializerProtocol,
        a_options: ContextBuilderOptions = ContextBuilderOptions(),
    ) -> None:
        """Initialize context builder.

        Args:
            a_collector: File collector protocol for repository scanning.
            a_index: Repository index for metadata storage.
            a_planner: Context planner for file selection (protocol).
            a_materializer: Context materializer for compression (protocol).
            a_options: Concurrency / progress / retry options. See
                :class:`ContextBuilderOptions`.
        """
        super().__init__(
            a_metadata=ModuleMetadata(
                name="arian.service.builder",
                layer="service",
                capabilities=frozenset({"async", "sync"}),
            )
        )
        self._collector: FileCollectorProtocol = a_collector
        self._index: RepositoryIndexProtocol = a_index
        self._planner: ContextPlannerProtocol = a_planner
        self._materializer: ContextMaterializerProtocol = a_materializer
        self._options: ContextBuilderOptions = a_options
        self._collection_stats: CollectionStats = CollectionStats()

    @property
    def collection_stats(self) -> CollectionStats:
        """Return collection statistics from the last build() call."""
        return self._collection_stats

    async def build(
        self,
        a_request: BuildRequest,
    ) -> Result[ContextPlan]:
        """Build a context plan from a :class:`BuildRequest`.

        Pipeline: collect files -> store metadata -> plan context.

        Args:
            a_request: Input describing the scan, including the
                repository root, the task, the budget, optional
                per-call input paths, and the explicit-path allow-list.

        Returns:
            Result[ContextPlan] with is_success, value (ContextPlan), and message.
        """
        a_path: Path = a_request.path
        a_task: ContextTask = a_request.task
        a_budget: TokenBudget = a_request.budget
        a_query: str | None = a_request.query
        a_root: Path = a_request.root if a_request.root is not None else a_path
        a_input_paths: list[Path] | None = a_request.input_paths
        a_explicit_paths: frozenset[Path] = a_request.explicit_paths

        logger.info("Building context for task=%s, path=%s", a_task.value, a_path)

        root: Path = a_root
        files: list[RepositoryFile] = []
        seen: set[str] = set()
        sources: list[Path] = a_input_paths if a_input_paths is not None else [a_path]
        result: Result[ContextPlan] = Result.failure("uninitialized")
        plan: ContextPlan = ContextPlan(chunks=(), total_tokens=0, total_files=0, task=a_task)
        b_continue: bool = True

        try:
            await self._collect_files(sources, root, files, seen, a_explicit_paths)
        except Exception as e:
            sanitized: str = sanitize_error_message(str(e), str(root))
            logger.exception("File collection failed for %s: %s", a_path, sanitized)
            msg: str = f"File collection failed for {a_path}: {sanitized}"
            result = Result.failure(msg)
            b_continue = False

        if b_continue:
            logger.debug("Collected %d files", len(files))
            self._notify_complete("collect")

            if len(files) > self._options.max_collected_files:
                msg = f"Too many files collected ({len(files)}), limit is {self._options.max_collected_files}"
                logger.error("%s", msg)
                result = Result.failure(msg)
                b_continue = False

        if b_continue:
            self._notify_start("plan", 1)
            try:
                for repo_file in files:
                    await self._index.save_file(repo_file)
                plan: ContextPlan = self._planner.plan(files, a_task, a_budget, a_query)
            except Exception as e:
                sanitized = sanitize_error_message(str(e), str(root))
                logger.exception("Planning failed: %s", sanitized)
                msg = f"Planning failed: {sanitized}"
                result = Result.failure(msg)
                b_continue = False

            if b_continue:
                validation_result = plan.validate()
                if not validation_result.is_success:
                    msg = f"Plan validation failed: {validation_result.message}"
                    logger.error("%s", msg)
                    result = Result.failure(msg)
                    b_continue = False

        if b_continue:
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
            result = Result.success(plan)

        return result

    async def load_content(
        self,
        a_plan: ContextPlan,
        a_root: Path,
    ) -> Result[ContentLoadData]:
        """Load file content for all files in the plan.

        Honours ConcurrencyPolicy for parallel reads. Skips binary files and
        unreadable paths; secrets in content are redacted at load time.

        Args:
            a_plan: Context plan with file references.
            a_root: Repository root path.

        Returns:
            Result[ContentLoadData] with is_success, content mapping, skipped paths, and message.
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
        for i, (load_result, rel_path) in enumerate(zip(results, (p[1] for p in paths), strict=True)):
            if load_result is not None:
                content_map[load_result.path] = load_result
            else:
                skipped.append(rel_path)
            self._notify_progress("load", i + 1, len(results))

        logger.debug(
            "Loaded content for %d files, skipped %d",
            len(content_map),
            len(skipped),
        )
        self._notify_complete("load")
        return Result.success(ContentLoadData(content=content_map, skipped=tuple(skipped)))

    def materialize(
        self,
        a_plan: ContextPlan,
        a_content: dict[str, FileContent],
    ) -> Result[tuple[MaterializedChunk, ...]]:
        """Materialize a context plan with compressed content.

        Args:
            a_plan: Context plan with compression decisions.
            a_content: Mapping of file path to FileContent.

        Returns:
            Result[tuple[MaterializedChunk, ...]] with is_success, value (MaterializedChunk tuple), and message.
        """
        self._notify_start("materialize", len(a_plan.chunks))
        materialized: tuple[MaterializedChunk, ...] = self._materializer.materialize(a_plan, a_content)
        self._notify_complete("materialize")
        logger.debug("Materialized %d chunks", len(materialized))
        return Result.success(materialized)

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
            if self._options.concurrency == ConcurrencyPolicy.SEQUENTIAL:
                for abs_path, rel_path in a_paths:
                    results.append(await self._load_single(abs_path, rel_path))
            elif self._options.concurrency == ConcurrencyPolicy.BOUNDED:
                semaphore = asyncio.Semaphore(self._options.max_concurrent)
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

        Transient ``OSError`` is retried with exponential backoff.
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
        retry: RetryConfig = self._options.retry
        for attempt in range(retry.attempts):
            try:
                raw = await asyncio.to_thread(a_path.read_bytes)
                last_error = None
                break
            except OSError as exc:
                last_error = exc
                if attempt < retry.attempts - 1:
                    await asyncio.sleep(retry.backoff_base_seconds * (retry.backoff_exponent_base**attempt))

        if last_error is not None or raw is None:
            logger.warning("Cannot read file: %s", a_path)
        elif is_binary(raw):
            logger.warning("Skipping binary file: %s", a_path)
        else:
            content: str = redact_secrets(raw.decode("utf-8", errors="ignore"), self._options.security)
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
        a_explicit_paths: frozenset[Path] = frozenset(),
    ) -> None:
        """Collect files from all sources with progress reporting.

        Args:
            a_sources: List of source paths to collect from.
            a_root: Root path for relative path computation.
            a_files: Output list to append collected files to.
            a_seen: Set of already-seen paths to avoid duplicates.
            a_explicit_paths: Paths whose contents always pass the
                ``.gitignore`` filter.
        """
        self._notify_start("collect", len(a_sources))
        for i, source in enumerate(a_sources):
            collected = await self._collector.collect(
                source,
                a_root=a_root,
                a_explicit_paths=a_explicit_paths,
            )
            self._collection_stats = self._collector.stats
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
        if self._options.progress:
            self._options.progress.on_stage_start(a_stage, a_total)

    def _notify_progress(self, a_stage: str, a_current: int, a_total: int) -> None:
        """Notify progress hook of stage progress, if present.

        Args:
            a_stage: Stage name.
            a_current: Current progress index.
            a_total: Total work units in the stage.
        """
        if self._options.progress:
            self._options.progress.on_stage_progress(a_stage, a_current, a_total)

    def _notify_complete(self, a_stage: str) -> None:
        """Notify progress hook of stage completion, if present.

        Args:
            a_stage: Stage name.
        """
        if self._options.progress:
            self._options.progress.on_stage_complete(a_stage)

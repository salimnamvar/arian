"""Context planner for task-aware file selection and chunking."""

from __future__ import annotations

import logging

from arian.domain.context.models import ContextChunk
from arian.domain.context.models import ContextPlan
from arian.domain.context.models import ContextTask
from arian.domain.context.models import PlannedFile
from arian.domain.repository.models import RepositoryFile
from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import FileRole
from arian.domain.shared.enums import TokenBudget
from arian.services.classifier.file_classifier import FileClassifier

logger = logging.getLogger(__name__)

_TASK_FILE_BOOST: dict[ContextTask, dict[FileRole, int]] = {
    ContextTask.BUG_FIX: {
        FileRole.TEST: -3,
        FileRole.SERVICE: -2,
        FileRole.DOMAIN: -1,
    },
    ContextTask.FEATURE: {
        FileRole.DOMAIN: -2,
        FileRole.SERVICE: -1,
        FileRole.TEST: -1,
    },
    ContextTask.REVIEW: {
        FileRole.SERVICE: -2,
        FileRole.DOMAIN: -1,
    },
    ContextTask.ONBOARDING: {
        FileRole.README: -5,
        FileRole.CONFIGURATION: -1,
    },
    ContextTask.REFACTOR: {
        FileRole.SERVICE: -2,
        FileRole.INFRASTRUCTURE: -1,
    },
    ContextTask.DOCUMENT: {
        FileRole.README: -3,
        FileRole.DOMAIN: -1,
        FileRole.SERVICE: -1,
    },
    ContextTask.GENERAL: {},
}


class ContextPlanner:
    """Plans context generation based on task type and token budget.

    Selects files, decides compression levels, and organizes chunks
    to stay within token budgets while maximizing relevance.

    Attributes:
        _classifier: File classifier for role detection.
    """

    def __init__(self, a_classifier: FileClassifier | None = None) -> None:
        """Initialize planner.

        Args:
            a_classifier: Optional file classifier (defaults to new instance).
        """
        self._classifier: FileClassifier = a_classifier if a_classifier is not None else FileClassifier()

    def plan(
        self,
        a_files: list[RepositoryFile],
        a_task: ContextTask,
        a_budget: TokenBudget,
        a_query: str | None = None,
    ) -> ContextPlan:
        """Create a context plan for the given files and task.

        Args:
            a_files: Repository files to plan for.
            a_task: The context task type.
            a_budget: Token budget constraints.
            a_query: Optional query for relevance matching.

        Returns:
            ContextPlan with chunks and metadata.
        """
        planned: list[PlannedFile] = self._plan_files(a_files, a_task, a_query)
        chunks: tuple[ContextChunk, ...] = self._plan_chunks(planned, a_budget)
        total_tokens: int = sum(c.token_count for c in chunks)

        result: ContextPlan = ContextPlan(
            chunks=chunks,
            total_tokens=total_tokens,
            total_files=len(planned),
            task=a_task,
            query=a_query,
        )
        return result

    def _plan_files(
        self,
        a_files: list[RepositoryFile],
        a_task: ContextTask,
        a_query: str | None,  # noqa: ARG002 — reserved for future query matching
    ) -> list[PlannedFile]:
        """Plan individual file representations.

        Args:
            a_files: Repository files to plan.
            a_task: The context task type.
            a_query: Optional query for relevance matching.

        Returns:
            List of PlannedFile sorted by importance.
        """
        planned: list[PlannedFile] = []
        for repo_file in a_files:
            role: FileRole
            importance: int
            compression: CompressionLevel
            role, importance, compression = self._classifier.classify(repo_file.path)

            importance = self._adjust_importance(importance, role, a_task)
            compression = self._decide_compression(compression, repo_file, a_task)

            representation: str = compression.value
            tokens: int = self._estimate_tokens(repo_file.tokens, compression)

            planned.append(
                PlannedFile(
                    path=repo_file.path,
                    role=role,
                    importance=importance,
                    compression=compression,
                    representation=representation,
                    tokens=tokens,
                )
            )

        planned.sort(key=lambda f: (f.importance, f.path))
        return planned

    def _adjust_importance(
        self,
        a_base_importance: int,
        a_role: FileRole,
        a_task: ContextTask,
    ) -> int:
        """Adjust importance based on task type.

        Args:
            a_base_importance: Base importance from classifier.
            a_role: File role.
            a_task: Context task type.

        Returns:
            Adjusted importance score.
        """
        boost_map: dict[FileRole, int] = _TASK_FILE_BOOST.get(a_task, {})
        boost: int = boost_map.get(a_role, 0)
        result: int = max(0, a_base_importance + boost)
        return result

    def _decide_compression(
        self,
        a_default: CompressionLevel,
        a_file: RepositoryFile,
        a_task: ContextTask,
    ) -> CompressionLevel:
        """Decide compression level for a file.

        Args:
            a_default: Default compression from classifier.
            a_file: Repository file metadata.
            a_task: Context task type.

        Returns:
            Decided compression level.
        """
        result: CompressionLevel = a_default

        if (a_file.tokens > 5000 or a_file.tokens > 2000) and result == CompressionLevel.FULL:
            result = CompressionLevel.SIGNATURES

        if a_role_is_critical(a_file.path, a_task):
            result = CompressionLevel.FULL

        return result

    def _estimate_tokens(self, a_original_tokens: int, a_level: CompressionLevel) -> int:
        """Estimate token count after compression.

        Args:
            a_original_tokens: Original token count.
            a_level: Compression level.

        Returns:
            Estimated token count.
        """
        ratios: dict[CompressionLevel, float] = {
            CompressionLevel.FULL: 1.0,
            CompressionLevel.SIGNATURES: 0.3,
            CompressionLevel.STRUCTURE: 0.1,
            CompressionLevel.SUMMARY: 0.05,
            CompressionLevel.AUTO: 1.0,
        }
        ratio: float = ratios.get(a_level, 1.0)
        result: int = max(1, int(a_original_tokens * ratio))
        return result

    def _plan_chunks(
        self,
        a_planned: list[PlannedFile],
        a_budget: TokenBudget,
    ) -> tuple[ContextChunk, ...]:
        """Organize planned files into token-aware chunks.

        Args:
            a_planned: Planned files sorted by importance.
            a_budget: Token budget constraints.

        Returns:
            Tuple of ContextChunk objects.
        """
        chunks: list[ContextChunk] = []
        current_files: list[PlannedFile] = []
        current_tokens: int = 0
        chunk_index: int = 0

        for planned_file in a_planned:
            if current_tokens + planned_file.tokens > a_budget.per_chunk_target and current_files:
                chunks.append(
                    ContextChunk(
                        files=tuple(current_files),
                        token_count=current_tokens,
                        chunk_index=chunk_index,
                    )
                )
                chunk_index += 1
                current_files = []
                current_tokens = 0

            current_files.append(planned_file)
            current_tokens += planned_file.tokens

        if current_files:
            chunks.append(
                ContextChunk(
                    files=tuple(current_files),
                    token_count=current_tokens,
                    chunk_index=chunk_index,
                )
            )

        result: tuple[ContextChunk, ...] = tuple(chunks)
        return result


def a_role_is_critical(a_path: str, a_task: ContextTask) -> bool:
    """Check if a file is critical for the given task.

    Args:
        a_path: File path.
        a_task: Context task type.

    Returns:
        True if the file should always be included at full compression.
    """
    path_lower: str = a_path.lower()
    result: bool = False

    if a_task == ContextTask.BUG_FIX:
        if "test" in path_lower or "spec" in path_lower:
            result = True
        if path_lower.endswith("readme.md"):
            result = True
    elif a_task == ContextTask.REVIEW:
        if path_lower.endswith("readme.md"):
            result = True
    elif a_task == ContextTask.ONBOARDING:
        if path_lower.endswith("readme.md"):
            result = True
        if "pyproject.toml" in path_lower or "setup.py" in path_lower:
            result = True

    return result

"""Domain protocols for Arian.

Cross-layer contracts live here so Application and Service depend on
abstractions, not concrete implementations (CSR).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from arian.domain.context.models import BuildRequest
from arian.domain.context.models import ContextPlan
from arian.domain.context.models import ContextTask
from arian.domain.context.models import MaterializedChunk
from arian.domain.repository.models import CollectionStats
from arian.domain.repository.models import FileContent
from arian.domain.repository.models import RepositoryFile
from arian.domain.repository.models import Symbol
from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import FileRole
from arian.domain.shared.enums import TokenBudget


class LanguageAnalyzerProtocol(Protocol):
    """Language-specific code analysis interface.

    Implementations provide language-aware symbol extraction,
    import detection, public API extraction, and content compression.
    """

    def extract_symbols(self, a_content: str, a_path: Path) -> list[Symbol]:
        """Extract code symbols from source content.

        Args:
            a_content: Source code content.
            a_path: File path for context.

        Returns:
            List of extracted symbols.
        """
        ...

    def extract_imports(self, a_content: str) -> list[str]:
        """Extract import statements from source content.

        Args:
            a_content: Source code content.

        Returns:
            List of imported module paths.
        """
        ...

    def extract_public_api(self, a_content: str) -> str:
        """Extract public API surface from source content.

        Args:
            a_content: Source code content.

        Returns:
            String representation of the public API.
        """
        ...

    def compress(self, a_content: str, a_level: CompressionLevel) -> str:
        """Compress source content according to compression level.

        Args:
            a_content: Source code content.
            a_level: Desired compression level.

        Returns:
            Compressed content string.
        """
        ...

    def strip_comments(self, a_content: str) -> str:
        """Strip comments from source content.

        Args:
            a_content: Source code content.

        Returns:
            Content with comments removed.
        """
        ...


class FileClassifierProtocol(Protocol):
    """File classification interface.

    Implementations classify files by role and importance.
    """

    def classify(self, a_path: str) -> tuple[FileRole, int, CompressionLevel]:
        """Classify a file path into role, importance, and compression.

        Args:
            a_path: Relative file path.

        Returns:
            Tuple of (role, importance, compression_level).
        """
        ...

    def get_role(self, a_path: str) -> FileRole:
        """Get the file role for a path.

        Args:
            a_path: Relative file path.

        Returns:
            Detected file role.
        """
        ...


class ContextPlannerProtocol(Protocol):
    """Plans which files to include and how to compress them."""

    def plan(
        self,
        a_files: list[RepositoryFile],
        a_task: ContextTask,
        a_budget: TokenBudget,
        a_query: str | None = None,
        a_symbols: dict[str, list[Symbol]] | None = None,
    ) -> ContextPlan:
        """Create a context plan for the given files and task.

        Args:
            a_files: Repository files to plan for.
            a_task: The context task type.
            a_budget: Token budget constraints.
            a_query: Optional query for relevance matching.
            a_symbols: Optional mapping of file path to extracted symbols.

        Returns:
            ContextPlan with chunks and metadata.
        """
        ...


class ContextMaterializerProtocol(Protocol):
    """Applies plan compression decisions to loaded file content."""

    def materialize(
        self,
        a_plan: ContextPlan,
        a_content: dict[str, FileContent],
    ) -> tuple[MaterializedChunk, ...]:
        """Apply compression levels from plan to actual file content.

        Args:
            a_plan: Context plan with compression decisions.
            a_content: Mapping of file path to FileContent.

        Returns:
            Tuple of MaterializedChunk with compressed content.
        """
        ...


class ContextBuilderProtocol(Protocol):
    """Full collect → plan → load → materialize pipeline port.

    Application depends on this protocol; bootstrap wires the concrete
    ContextBuilder.
    """

    @property
    def collection_stats(self) -> CollectionStats:
        """Return collection statistics from the last build() call."""
        ...

    async def build(self, a_request: BuildRequest) -> ContextPlan:
        """Build a context plan from a build request value object.

        Args:
            a_request: Build request (path, task, budget, filters).

        Returns:
            ContextPlan with chunks and metadata.
        """
        ...

    async def load_content(
        self,
        a_plan: ContextPlan,
        a_root: Path,
    ) -> tuple[dict[str, FileContent], tuple[str, ...]]:
        """Load file content for all files in the plan.

        Args:
            a_plan: Context plan with file references.
            a_root: Repository root path.

        Returns:
            Tuple of content mapping and skipped file paths.
        """
        ...

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
        ...

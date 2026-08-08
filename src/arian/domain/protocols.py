"""Domain protocols for Arian.

Cross-layer contracts live here so Application and Service depend on
abstractions, not concrete implementations (CSR).
"""

from __future__ import annotations

from dataclasses import dataclass
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
from arian.domain.shared.result import Result


class LanguageAnalyzerProtocol(Protocol):
    """Language-specific code analysis interface."""

    def extract_symbols(self, a_content: str, a_path: Path) -> list[Symbol]: ...

    def extract_imports(self, a_content: str) -> list[str]: ...

    def extract_public_api(self, a_content: str) -> str: ...

    def compress(self, a_content: str, a_level: CompressionLevel) -> str: ...

    def strip_comments(self, a_content: str) -> str: ...


class FileClassifierProtocol(Protocol):
    """File classification interface."""

    def classify(self, a_path: str) -> tuple[FileRole, int, CompressionLevel]: ...

    def get_role(self, a_path: str) -> FileRole: ...


class ContextPlannerProtocol(Protocol):
    """Plans which files to include and how to compress them."""

    def plan(
        self,
        a_files: list[RepositoryFile],
        a_task: ContextTask,
        a_budget: TokenBudget,
        a_query: str | None = None,
        a_symbols: dict[str, list[Symbol]] | None = None,
    ) -> ContextPlan: ...


class ContextMaterializerProtocol(Protocol):
    """Applies plan compression decisions to loaded file content."""

    def materialize(
        self,
        a_plan: ContextPlan,
        a_content: dict[str, FileContent],
    ) -> tuple[MaterializedChunk, ...]: ...


@dataclass(frozen=True)
class ContentLoadData:
    """Data returned by load_content() on success."""

    content: dict[str, FileContent]
    skipped: tuple[str, ...]


class ContextBuilderProtocol(Protocol):
    """Full collect -> plan -> load -> materialize pipeline port."""

    @property
    def collection_stats(self) -> CollectionStats:
        """Return collection statistics from the last build() call."""
        ...

    async def build(self, a_request: BuildRequest) -> Result[ContextPlan]:
        """Build a context plan from a build request value object."""
        ...

    async def load_content(
        self,
        a_plan: ContextPlan,
        a_root: Path,
    ) -> Result[ContentLoadData]:
        """Load file content for all files in the plan."""
        ...

    def materialize(
        self,
        a_plan: ContextPlan,
        a_content: dict[str, FileContent],
    ) -> Result[tuple[MaterializedChunk, ...]]:
        """Materialize a context plan with compressed content."""
        ...

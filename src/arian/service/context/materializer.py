"""Context materializer — applies compression decisions from ContextPlan."""

from __future__ import annotations

import logging
from typing import Protocol

from arian.domain.context.models import ContextPlan
from arian.domain.context.models import MaterializedChunk
from arian.domain.context.models import MaterializedFile
from arian.domain.repository.models import FileContent
from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import TokenBudget

logger = logging.getLogger(__name__)


class LanguageAnalyzerProtocol(Protocol):
    """Protocol for language-specific content compression."""

    def compress(self, a_content: str, a_level: CompressionLevel) -> str: ...


class ContextMaterializer:
    """Applies ContextPlan decisions to produce materialized content.

    Takes a ContextPlan (what to include) and FileContent (actual content),
    and produces MaterializedChunks with compressed content ready for rendering.

    Attributes:
        _analyzer: Language analyzer for content compression.
    """

    def __init__(self, a_analyzer: LanguageAnalyzerProtocol) -> None:
        """Initialize materializer.

        Args:
            a_analyzer: Language analyzer for content compression.
        """
        self._analyzer: LanguageAnalyzerProtocol = a_analyzer

    def materialize(
        self,
        a_plan: ContextPlan,
        a_content: dict[str, FileContent],
        a_budget: TokenBudget | None = None,  # noqa: ARG002 — reserved for overflow handling
    ) -> tuple[MaterializedChunk, ...]:
        """Apply compression levels from plan to actual file content.

        Args:
            a_plan: Context plan with compression decisions.
            a_content: Mapping of file path to FileContent.
            a_budget: Optional token budget for overflow handling.

        Returns:
            Tuple of MaterializedChunk with compressed content.
        """
        materialized_chunks: list[MaterializedChunk] = []
        overflow_files: list[MaterializedFile] = []

        for chunk in a_plan.chunks:
            materialized_files: list[MaterializedFile] = []
            chunk_tokens: int = 0

            for planned_file in chunk.files:
                content_obj: FileContent | None = a_content.get(planned_file.path)
                if content_obj is None:
                    logger.warning("No content for planned file: %s", planned_file.path)
                    continue

                compressed_content: str = self._compress(content_obj.content, planned_file.compression)

                materialized_files.append(
                    MaterializedFile(
                        path=planned_file.path,
                        role=planned_file.role,
                        importance=planned_file.importance,
                        compression=planned_file.compression,
                        content=compressed_content,
                        tokens=planned_file.tokens,
                        is_overflow=False,
                    )
                )
                chunk_tokens += planned_file.tokens

            if materialized_files:
                materialized_chunks.append(
                    MaterializedChunk(
                        files=tuple(materialized_files),
                        token_count=chunk_tokens,
                        chunk_index=chunk.chunk_index,
                        header=chunk.header,
                    )
                )

        for i, overflow_file in enumerate(overflow_files):
            materialized_chunks.append(
                MaterializedChunk(
                    files=(overflow_file,),
                    token_count=overflow_file.tokens,
                    chunk_index=len(materialized_chunks) + i,
                    header="Overflow",
                )
            )

        return tuple(materialized_chunks)

    def _compress(self, a_content: str, a_level: CompressionLevel) -> str:
        """Compress content according to level.

        Args:
            a_content: Raw content.
            a_level: Compression level.

        Returns:
            Compressed content string.
        """
        result: str
        if a_level == CompressionLevel.FULL:
            result = a_content
        elif a_level == CompressionLevel.SIGNATURES:
            result = self._analyzer.compress(a_content, CompressionLevel.SIGNATURES)
        elif a_level == CompressionLevel.STRUCTURE:
            result = self._analyzer.compress(a_content, CompressionLevel.STRUCTURE)
        elif a_level == CompressionLevel.SUMMARY:
            result = self._analyzer.compress(a_content, CompressionLevel.SUMMARY)
        else:
            result = a_content
        return result

"""Context materializer — applies compression decisions from ContextPlan."""

from __future__ import annotations

import logging
from typing import Protocol

from arian.domain.context.models import ContextPlan
from arian.domain.context.models import MaterializedChunk
from arian.domain.context.models import MaterializedFile
from arian.domain.repository.models import FileContent
from arian.domain.shared.enums import CompressionLevel

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
    ) -> tuple[MaterializedChunk, ...]:
        """Apply compression levels from plan to actual file content.

        Args:
            a_plan: Context plan with compression decisions.
            a_content: Mapping of file path to FileContent.

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

                compressed_content: str
                is_overflow: bool = False

                if planned_file.compression == CompressionLevel.FULL:
                    compressed_content = content_obj.content
                elif planned_file.compression == CompressionLevel.SUMMARY:
                    compressed_content = self._analyzer.compress(content_obj.content, CompressionLevel.SUMMARY)
                elif planned_file.compression == CompressionLevel.SIGNATURES:
                    compressed_content = self._analyzer.compress(content_obj.content, CompressionLevel.SIGNATURES)
                elif planned_file.compression == CompressionLevel.STRUCTURE:
                    compressed_content = self._analyzer.compress(content_obj.content, CompressionLevel.STRUCTURE)
                else:
                    compressed_content = content_obj.content

                materialized_files.append(
                    MaterializedFile(
                        path=planned_file.path,
                        role=planned_file.role,
                        importance=planned_file.importance,
                        compression=planned_file.compression,
                        content=compressed_content,
                        tokens=planned_file.tokens,
                        is_overflow=is_overflow,
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

        materialized_chunks.extend(
            MaterializedChunk(
                files=(overflow_file,),
                token_count=overflow_file.tokens,
                chunk_index=len(materialized_chunks) + i,
                header="Overflow",
            )
            for i, overflow_file in enumerate(overflow_files)
        )

        return tuple(materialized_chunks)

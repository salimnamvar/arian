"""Context materializer — applies compression decisions from ContextPlan."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from arian.domain.context.models import ContextPlan
from arian.domain.context.models import MaterializedChunk
from arian.domain.context.models import MaterializedEntry
from arian.domain.context.models import Provenance
from arian.domain.repository.models import FileContent
from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.language import detect_language

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

        for chunk in a_plan.chunks:
            materialized_entries: list[MaterializedEntry] = []
            chunk_tokens: int = 0

            for planned_file in chunk.files:
                content_obj: FileContent | None = a_content.get(planned_file.path)
                if content_obj is None:
                    logger.warning("No content for planned file: %s", planned_file.path)
                    continue

                raw_content: str = self._extract_content(
                    content_obj.content,
                    planned_file.line_start,
                    planned_file.line_end,
                )
                compressed_content: str = self._compress(raw_content, planned_file.compression)

                provenance: Provenance = Provenance(
                    source_file=planned_file.path,
                    source_lines=(
                        planned_file.line_start if planned_file.line_start is not None else 0,
                        planned_file.line_end
                        if planned_file.line_end is not None
                        else len(content_obj.content.splitlines()),
                    ),
                    compression_applied=planned_file.compression,
                )

                materialized_entries.append(
                    MaterializedEntry(
                        path=planned_file.path,
                        role=planned_file.role,
                        importance=planned_file.importance,
                        compression=planned_file.compression,
                        content=compressed_content,
                        tokens=planned_file.tokens,
                        is_fragment=planned_file.is_fragment,
                        fragment_index=planned_file.fragment_index,
                        fragment_total=planned_file.fragment_total,
                        language=detect_language(Path(planned_file.path)),
                        provenance=provenance,
                    )
                )
                chunk_tokens += planned_file.tokens

            if materialized_entries:
                materialized_chunks.append(
                    MaterializedChunk(
                        entries=tuple(materialized_entries),
                        token_count=chunk_tokens,
                        chunk_index=chunk.chunk_index,
                        header=chunk.header,
                    )
                )

        self._populate_continuation_hints(materialized_chunks)
        return tuple(materialized_chunks)

    def _populate_continuation_hints(
        self,
        a_chunks: list[MaterializedChunk],
    ) -> None:
        """Populate continues_in_chunk for cross-chunk fragment relationships.

        Modifies chunks in-place, setting continues_in_chunk for each
        fragment that has a next fragment in a later chunk.

        Args:
            a_chunks: List of materialized chunks to update.
        """
        fragment_locations: dict[str, list[int]] = {}
        for i, chunk in enumerate(a_chunks):
            for entry in chunk.entries:
                if entry.is_fragment:
                    fragment_locations.setdefault(entry.path, []).append(i)

        for path, chunk_indices in fragment_locations.items():
            if len(chunk_indices) < 2:
                continue
            for pos, chunk_idx in enumerate(chunk_indices):
                if pos < len(chunk_indices) - 1:
                    next_chunk_idx = chunk_indices[pos + 1]
                    chunk = a_chunks[chunk_idx]
                    updated_entries: list[MaterializedEntry] = []
                    for entry in chunk.entries:
                        if entry.is_fragment and entry.path == path and entry.continues_in_chunk is None:
                            updated_entries.append(
                                MaterializedEntry(
                                    path=entry.path,
                                    role=entry.role,
                                    importance=entry.importance,
                                    compression=entry.compression,
                                    content=entry.content,
                                    tokens=entry.tokens,
                                    is_fragment=entry.is_fragment,
                                    fragment_index=entry.fragment_index,
                                    fragment_total=entry.fragment_total,
                                    continues_in_chunk=next_chunk_idx,
                                    language=entry.language,
                                    provenance=entry.provenance,
                                )
                            )
                        else:
                            updated_entries.append(entry)
                    a_chunks[chunk_idx] = MaterializedChunk(
                        entries=tuple(updated_entries),
                        token_count=chunk.token_count,
                        chunk_index=chunk.chunk_index,
                        header=chunk.header,
                    )

    def _extract_content(
        self,
        a_content: str,
        a_line_start: int | None,
        a_line_end: int | None,
    ) -> str:
        """Extract content for a line range.

        Args:
            a_content: Full file content.
            a_line_start: First line number (inclusive, 0-based). None for full file.
            a_line_end: Last line number (exclusive, 0-based). None for full file.

        Returns:
            Extracted content string.
        """
        result: str = a_content
        if a_line_start is not None and a_line_end is not None:
            lines: list[str] = a_content.splitlines(keepends=True)
            start: int = max(0, a_line_start)
            end: int = min(len(lines), a_line_end)
            result = "".join(lines[start:end])
        return result

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

"""Service layer for Arian.

Orchestrates the context building pipeline with dependency injection.
"""

from __future__ import annotations

import logging
from pathlib import Path

from arian.domain.enums import OutputMode
from arian.domain.exceptions import NoDocumentsError
from arian.domain.models import ContextConfig
from arian.domain.models import ContextResult
from arian.domain.models import Document
from arian.renderers.protocols import RendererProtocol
from arian.repositories.protocols import CollectorProtocol
from arian.repositories.protocols import WriterProtocol

logger = logging.getLogger(__name__)


class ContextBuilderService:
    """Main orchestration service for building LLM context.

    Attributes:
        _config (ContextConfig): Configuration.
        _collector (CollectorProtocol): Document collector.
        _writer (WriterProtocol): Output writer.
        _renderer (RendererProtocol): Content renderer.
    """

    def __init__(
        self,
        a_config: ContextConfig,
        a_collector: CollectorProtocol,
        a_writer: WriterProtocol,
        a_renderer: RendererProtocol,
    ) -> None:
        """Initialize service with injected dependencies.

        Args:
            a_config: Configuration.
            a_collector: Document collector.
            a_writer: Output writer.
            a_renderer: Content renderer.
        """
        self._config: ContextConfig = a_config
        self._collector: CollectorProtocol = a_collector
        self._writer: WriterProtocol = a_writer
        self._renderer: RendererProtocol = a_renderer

    def build(self) -> ContextResult:
        """Build context and write output.

        Returns:
            ContextResult: Result of the operation.

        Raises:
            NoDocumentsError: If no documents were collected from inputs.
        """
        documents: list[Document] = self._collector.collect(list(self._config.inputs))

        if not documents:
            logger.warning("No documents collected from inputs")
            msg = "No documents collected from inputs"
            raise NoDocumentsError(
                msg,
                a_resource_type="input_path",
                a_resource_name=", ".join(self._config.inputs),
            )

        documents = sorted(documents, key=lambda d: d.path)

        total_tokens: int = sum(d.tokens for d in documents)
        logger.info("Collected %d documents (%d tokens)", len(documents), total_tokens)

        chunks: list[list[Document]]
        if self._config.mode == OutputMode.AGGREGATE and self._config.max_tokens is not None:
            chunks = self._split_documents(documents, self._config.max_tokens)
        else:
            chunks = [documents]

        logger.debug("Split into %d chunk(s)", len(chunks))

        out_path: Path = Path(self._config.output_path)

        result: ContextResult = self._render_and_write(
            a_documents=documents,
            a_chunks=chunks,
            a_output_path=out_path,
        )
        return result

    def _split_documents(
        self,
        a_documents: list[Document],
        a_max_tokens: int | None,
    ) -> list[list[Document]]:
        """Split documents into chunks respecting token limit.

        Args:
            a_documents: Documents to split.
            a_max_tokens: Maximum tokens per chunk.

        Returns:
            List of document chunks.
        """
        chunks: list[list[Document]]
        if a_max_tokens is None:
            chunks = [a_documents]
        else:
            chunks = []
            current_chunk: list[Document] = []
            current_tokens: int = 0

            for doc in a_documents:
                if current_tokens + doc.tokens > a_max_tokens and current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = [doc]
                    current_tokens = doc.tokens
                else:
                    current_chunk.append(doc)
                    current_tokens += doc.tokens

            if current_chunk:
                chunks.append(current_chunk)

        logger.debug(
            "Split %d documents into %d chunk(s) (max %s tokens)",
            len(a_documents),
            len(chunks),
            a_max_tokens,
        )

        return chunks

    def _render_and_write(
        self,
        a_documents: list[Document],
        a_chunks: list[list[Document]],
        a_output_path: Path,
    ) -> ContextResult:
        """Render documents and write to output files.

        Args:
            a_documents: All collected documents.
            a_chunks: Document chunks.
            a_output_path: Output path.

        Returns:
            ContextResult with output information.
        """
        total_tokens: int = sum(d.tokens for d in a_documents)

        logger.debug("Rendering %d documents, %d chunk(s)", len(a_documents), len(a_chunks))

        result: ContextResult
        if self._config.mode == OutputMode.AGGREGATE and self._config.max_tokens is None:
            result = self._render_aggregate_single(a_documents, a_output_path, total_tokens)
        elif self._config.mode == OutputMode.AGGREGATE and self._config.max_tokens is not None:
            result = self._render_aggregate_split(a_chunks, a_output_path, total_tokens)
        else:
            result = self._render_separate(a_chunks, a_output_path, total_tokens)

        return result

    def _render_aggregate_single(
        self,
        a_documents: list[Document],
        a_output_path: Path,
        a_total_tokens: int,
    ) -> ContextResult:
        """Write single aggregated output.

        Args:
            a_documents: All documents to render.
            a_output_path: Output path.
            a_total_tokens: Total token count.

        Returns:
            ContextResult.
        """
        content: str = self._renderer.render(a_documents)
        output_path: Path = a_output_path
        if output_path.suffix != ".md":
            output_path = output_path / "merged.md"

        written: Path = self._writer.write(content, output_path)
        logger.debug("Wrote %s", written)

        result: ContextResult = ContextResult(
            output_paths=(str(written),),
            total_files=len(a_documents),
            total_tokens=a_total_tokens,
        )
        return result

    def _render_aggregate_split(
        self,
        a_chunks: list[list[Document]],
        a_output_path: Path,
        a_total_tokens: int,
    ) -> ContextResult:
        """Write aggregated output split by tokens.

        Args:
            a_chunks: Document chunks.
            a_output_path: Output directory.
            a_total_tokens: Total token count.

        Returns:
            ContextResult.
        """
        output_paths: list[str] = []

        for i, chunk in enumerate(a_chunks, start=1):
            content: str = self._renderer.render(chunk)
            numbered_path: Path = a_output_path / f"merged.{i}.md"
            self._writer.write(content, numbered_path)
            logger.debug("Wrote chunk %d to %s", i, numbered_path)
            output_paths.append(str(numbered_path))

        result: ContextResult = ContextResult(
            output_paths=tuple(output_paths),
            total_files=sum(len(c) for c in a_chunks),
            total_tokens=a_total_tokens,
            chunks=len(a_chunks),
        )
        return result

    def _render_separate(
        self,
        a_chunks: list[list[Document]],
        a_output_path: Path,
        a_total_tokens: int,
    ) -> ContextResult:
        """Write separate mode output (one file per input).

        Args:
            a_chunks: Document chunks (one per input).
            a_output_path: Output directory.
            a_total_tokens: Total token count.

        Returns:
            ContextResult.
        """
        output_paths: list[str] = []

        for chunk in a_chunks:
            if not chunk:
                continue
            first_doc: Document = chunk[0]
            stem: str = Path(first_doc.path).stem or Path(first_doc.path).name
            content: str = self._renderer.render(chunk)
            out_path: Path = a_output_path / f"{stem}.md"
            self._writer.write(content, out_path)
            logger.debug("Wrote %s", out_path)
            output_paths.append(str(out_path))

        result: ContextResult = ContextResult(
            output_paths=tuple(output_paths),
            total_files=sum(len(c) for c in a_chunks),
            total_tokens=a_total_tokens,
        )
        return result

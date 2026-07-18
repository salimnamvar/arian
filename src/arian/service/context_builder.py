"""Service layer for Arian.

Orchestrates the context building pipeline with dependency injection.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from arian.domain.enums import OutputMode
from arian.domain.exceptions import NoDocumentsError
from arian.domain.models import ContextConfig
from arian.domain.models import ContextResult
from arian.domain.models import Document
from arian.pipeline.renderer_pipeline import render_and_write
from arian.pipeline.splitter_pipeline import split_documents
from arian.renderer.protocols import RendererProtocol
from arian.repository.protocols import CollectorProtocol
from arian.repository.protocols import WriterProtocol


class ContextBuilderService:
    """Main orchestration service for building LLM context.

    Attributes:
        _config (ContextConfig): Configuration.
    """

    def __init__(
        self,
        a_config: ContextConfig,
        a_collector: CollectorProtocol,
        a_writer: WriterProtocol,
        a_renderer: RendererProtocol,
        a_tokenizer: Callable[[str], int],
    ) -> None:
        """Initialize service with injected dependencies.

        Args:
            a_config: Configuration.
            a_collector: Document collector.
            a_writer: Output writer.
            a_renderer: Content renderer.
            a_tokenizer: Token counting function.
        """
        self._config: ContextConfig = a_config
        self._collector: CollectorProtocol = a_collector
        self._writer: WriterProtocol = a_writer
        self._renderer: RendererProtocol = a_renderer
        self._tokenizer: Callable[[str], int] = a_tokenizer

    def build(self) -> ContextResult:
        """Build context and write output.

        Returns:
            ContextResult: Result of the operation.

        Raises:
            NoDocumentsError: If no documents were collected from inputs.
        """
        # Collect documents
        documents: list[Document] = self._collector.collect(self._config.inputs)

        # Check for empty results
        if not documents:
            msg = "No documents collected from inputs"
            raise NoDocumentsError(
                msg,
                a_resource_type="input_path",
                a_resource_name=", ".join(self._config.inputs),
            )

        # Order documents
        documents = sorted(documents, key=lambda d: d.path)

        # Determine chunks based on mode
        chunks: list[list[Document]]
        if self._config.mode == OutputMode.AGGREGATE and self._config.max_tokens is not None:
            chunks = split_documents(documents, self._config.max_tokens)
        else:
            chunks = [documents]

        # Output path resolved by controller
        out_path: Path = Path(self._config.output_path)

        # Render and write
        result: ContextResult = render_and_write(
            a_documents=documents,
            a_chunks=chunks,
            a_output_path=out_path,
            a_mode=self._config.mode,
            a_max_tokens=self._config.max_tokens,
            a_renderer=self._renderer,
            a_writer=self._writer,
        )

        return result

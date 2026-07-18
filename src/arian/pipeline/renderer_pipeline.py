"""Renderer pipeline for Arian.

Renders documents and writes output files.
"""

from __future__ import annotations

import logging
from pathlib import Path

from arian.domain.models import ContextResult
from arian.domain.models import Document
from arian.domain.models import OutputMode
from arian.renderer.protocols import RendererProtocol
from arian.repository.protocols import WriterProtocol

logger = logging.getLogger(__name__)


def render_and_write(
    a_documents: list[Document],
    a_chunks: list[list[Document]],
    a_output_path: Path,
    a_mode: OutputMode,
    a_max_tokens: int | None,
    a_renderer: RendererProtocol,
    a_writer: WriterProtocol,
) -> ContextResult:
    """Render documents and write to output files.

    Args:
        a_documents: All collected documents.
        a_chunks: Document chunks.
        a_output_path: Output path.
        a_mode: Output mode.
        a_max_tokens: Token limit.
        a_renderer: Renderer instance (injected).
        a_writer: Writer instance (injected).

    Returns:
        ContextResult with output information.
    """
    total_tokens: int = sum(d.tokens for d in a_documents)

    logger.debug("Rendering %d documents, %d chunk(s)", len(a_documents), len(a_chunks))

    result: ContextResult
    if a_mode == OutputMode.AGGREGATE and a_max_tokens is None:
        result = _render_aggregate_single(a_renderer, a_writer, a_documents, a_output_path, total_tokens)
    elif a_mode == OutputMode.AGGREGATE and a_max_tokens is not None:
        result = _render_aggregate_split(a_renderer, a_writer, a_chunks, a_output_path, total_tokens)
    else:
        # SEPARATE mode - a_chunks contains one list per input
        result = _render_separate(a_renderer, a_writer, a_chunks, a_output_path, total_tokens)

    return result


def _render_aggregate_single(
    a_renderer: RendererProtocol,
    a_writer: WriterProtocol,
    a_documents: list[Document],
    a_output_path: Path,
    a_total_tokens: int,
) -> ContextResult:
    """Write single aggregated output.

    Args:
        a_renderer: Renderer instance.
        a_writer: Writer instance.
        a_documents: All documents to render.
        a_output_path: Output path.
        a_total_tokens: Total token count.

    Returns:
        ContextResult.
    """
    content: str = a_renderer.render(a_documents)

    if a_output_path.suffix != ".md":
        a_output_path = a_output_path / "merged.md"

    written: Path = a_writer.write(content, a_output_path)
    logger.debug("Wrote %s", written)

    result: ContextResult = ContextResult(
        output_paths=(str(written),),
        total_files=len(a_documents),
        total_tokens=a_total_tokens,
    )
    return result


def _render_aggregate_split(
    a_renderer: RendererProtocol,
    a_writer: WriterProtocol,
    a_chunks: list[list[Document]],
    a_output_path: Path,
    a_total_tokens: int,
) -> ContextResult:
    """Write aggregated output split by tokens.

    Args:
        a_renderer: Renderer instance.
        a_writer: Writer instance.
        a_chunks: Document chunks.
        a_output_path: Output directory.
        a_total_tokens: Total token count.

    Returns:
        ContextResult.
    """
    output_paths: list[str] = []

    for i, chunk in enumerate(a_chunks, start=1):
        content: str = a_renderer.render(chunk)
        numbered_path: Path = a_output_path / f"merged.{i}.md"
        a_writer.write(content, numbered_path)
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
    a_renderer: RendererProtocol,
    a_writer: WriterProtocol,
    a_chunks: list[list[Document]],
    a_output_path: Path,
    a_total_tokens: int,
) -> ContextResult:
    """Write separate mode output (one file per input).

    Args:
        a_renderer: Renderer instance.
        a_writer: Writer instance.
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
        # Use the path of the first document in the chunk
        first_doc: Document = chunk[0]
        stem: str = Path(first_doc.path).stem or Path(first_doc.path).name
        content: str = a_renderer.render(chunk)
        out_path: Path = a_output_path / f"{stem}.md"
        a_writer.write(content, out_path)
        logger.debug("Wrote %s", out_path)
        output_paths.append(str(out_path))

    result: ContextResult = ContextResult(
        output_paths=tuple(output_paths),
        total_files=sum(len(c) for c in a_chunks),
        total_tokens=a_total_tokens,
    )
    return result

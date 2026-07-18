"""Service layer for Arian.

Orchestrates the context building pipeline with dependency injection.
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
from pathlib import Path

from arian.domain.enums import FileRole
from arian.domain.enums import OutputMode
from arian.domain.exceptions import NoDocumentsError
from arian.domain.models import FULL
from arian.domain.models import SIGNATURES
from arian.domain.models import STRUCTURE_ONLY
from arian.domain.models import CompressionLevel
from arian.domain.models import ContextConfig
from arian.domain.models import ContextResult
from arian.domain.models import Document
from arian.domain.models import FileClassification
from arian.domain.models import InputSpec
from arian.domain.models import PatternRule
from arian.infrastructure.tokenizer import count_tokens
from arian.renderers.protocols import RendererProtocol
from arian.repositories.protocols import CollectorProtocol
from arian.repositories.protocols import WriterProtocol
from arian.services.analyzer import ContextAnalyzer
from arian.services.compressor import ContentCompressor

logger = logging.getLogger(__name__)


class ContextBuilderService:
    """Main orchestration service for building LLM context.

    Attributes:
        _config (ContextConfig): Configuration.
        _collector (CollectorProtocol): Document collector.
        _writer (WriterProtocol): Output writer.
        _renderer (RendererProtocol): Content renderer.
        _analyzer (ContextAnalyzer): File classifier.
        _compressor (ContentCompressor): Content compressor.
    """

    def __init__(
        self,
        a_config: ContextConfig,
        a_collector: CollectorProtocol,
        a_writer: WriterProtocol,
        a_renderer: RendererProtocol,
        a_analyzer: ContextAnalyzer | None = None,
        a_compressor: ContentCompressor | None = None,
    ) -> None:
        """Initialize service with injected dependencies.

        Args:
            a_config: Configuration.
            a_collector: Document collector.
            a_writer: Output writer.
            a_renderer: Content renderer.
            a_analyzer: Optional file classifier (defaults to ContextAnalyzer).
            a_compressor: Optional content compressor.
        """
        self._config: ContextConfig = a_config
        self._collector: CollectorProtocol = a_collector
        self._writer: WriterProtocol = a_writer
        self._renderer: RendererProtocol = a_renderer
        self._analyzer: ContextAnalyzer = a_analyzer if a_analyzer is not None else ContextAnalyzer()
        self._compressor: ContentCompressor = (
            a_compressor if a_compressor is not None else ContentCompressor(a_tokenizer=count_tokens)
        )

    def build(self) -> ContextResult:
        """Build context and write output (synchronous wrapper).

        Returns:
            ContextResult: Result of the operation.

        Raises:
            NoDocumentsError: If no documents were collected from inputs.
        """
        result: ContextResult = asyncio.run(self.build_async())
        return result

    async def build_async(self) -> ContextResult:
        """Build context and write output asynchronously.

        Pipeline: collect → classify → compress → order → chunk → render/write.

        Returns:
            ContextResult: Result of the operation.

        Raises:
            NoDocumentsError: If no documents were collected from inputs.
        """
        documents: list[Document] = await self._collector.collect(list(self._config.inputs))

        if not documents:
            logger.warning("No documents collected from inputs")
            input_names: str = ", ".join(spec.path for spec in self._config.inputs)
            msg = "No documents collected from inputs"
            raise NoDocumentsError(
                msg,
                a_resource_type="input_path",
                a_resource_name=input_names,
            )

        documents = self._tag_documents(documents, self._config.inputs)
        documents = self._apply_context_engineering(documents)
        tagged_groups: dict[str, list[Document]] = self._group_by_tag(documents)

        total_tokens: int = sum(d.tokens for d in documents)
        logger.info("Collected %d documents (%d tokens)", len(documents), total_tokens)

        out_path: Path = Path(self._config.output_path)
        result: ContextResult = await self._build_per_tag(tagged_groups, out_path)
        return result

    def _apply_context_engineering(self, a_documents: list[Document]) -> list[Document]:
        """Classify, compress, and order documents.

        Args:
            a_documents: Collected documents.

        Returns:
            Processed documents ready for chunking.
        """
        processed: list[Document] = []
        for doc in a_documents:
            classification: FileClassification = self._analyzer.classify_file(doc.path)
            level: CompressionLevel = self._resolve_compression(doc.path, classification)
            content: str = self._compressor.compress(doc.content, doc.language, level)
            tokens: int = count_tokens(content) if content != doc.content else doc.tokens
            processed.append(
                Document(
                    path=doc.path,
                    content=content,
                    tokens=tokens,
                    language=doc.language,
                    tag=doc.tag,
                ),
            )

        result: list[Document]
        if self._config.sort_by_importance:
            result = self._analyzer.order_by_importance(processed)
        else:
            result = sorted(processed, key=lambda d: d.path)
        return result

    def _resolve_compression(
        self,
        a_path: str,
        a_classification: FileClassification,
    ) -> CompressionLevel:
        """Resolve effective compression level for a file.

        Args:
            a_path: File path.
            a_classification: Analyzer classification for the file.

        Returns:
            Effective CompressionLevel after config and pattern overrides.
        """
        level: CompressionLevel
        mode: str = self._config.compression

        if mode == "full":
            level = FULL
        elif mode == "signatures":
            level = SIGNATURES
        elif mode == "minimal":
            level = STRUCTURE_ONLY
        else:
            # auto — use classification recommendation
            level = a_classification.compression

        for rule in self._config.pattern_rules:
            if self._matches_pattern(a_path, rule):
                level = self._level_from_name(rule.compression)

        level = self._apply_include_overrides(level)
        return level

    def _matches_pattern(self, a_path: str, a_rule: PatternRule) -> bool:
        """Check whether a path matches a pattern rule.

        Args:
            a_path: File path.
            a_rule: Pattern rule to apply.

        Returns:
            True if the path matches the rule pattern.
        """
        result: bool = fnmatch.fnmatch(a_path, a_rule.pattern) or fnmatch.fnmatch(
            Path(a_path).name,
            a_rule.pattern,
        )
        return result

    def _level_from_name(self, a_name: str) -> CompressionLevel:
        """Map a compression name string to a CompressionLevel preset.

        Args:
            a_name: Compression mode name.

        Returns:
            Matching CompressionLevel preset.
        """
        mapping: dict[str, CompressionLevel] = {
            "full": FULL,
            "compressed": SIGNATURES,
            "signatures": SIGNATURES,
            "structure_only": STRUCTURE_ONLY,
            "minimal": STRUCTURE_ONLY,
        }
        result: CompressionLevel = mapping.get(a_name, FULL)
        return result

    def _apply_include_overrides(self, a_level: CompressionLevel) -> CompressionLevel:
        """Apply CLI include_* overrides to a compression level.

        Args:
            a_level: Base compression level.

        Returns:
            CompressionLevel with overrides applied.
        """
        keep_comments: bool = a_level.keep_comments
        keep_docstrings: bool = a_level.keep_docstrings
        keep_imports: bool = a_level.keep_imports

        if self._config.include_comments is not None:
            keep_comments = self._config.include_comments
        if self._config.include_docstrings is not None:
            keep_docstrings = self._config.include_docstrings
        if self._config.include_imports is not None:
            keep_imports = self._config.include_imports

        result: CompressionLevel = CompressionLevel(
            keep_comments=keep_comments,
            keep_docstrings=keep_docstrings,
            keep_type_hints=a_level.keep_type_hints,
            keep_implementation=a_level.keep_implementation,
            keep_imports=keep_imports,
        )
        return result

    def _tag_documents(
        self,
        a_documents: list[Document],
        a_inputs: tuple[InputSpec, ...],
    ) -> list[Document]:
        """Match each document to its InputSpec by path prefix and apply tags.

        Longer matching prefixes win so nested inputs are preferred.

        Args:
            a_documents: Collected documents.
            a_inputs: Input specifications used for collection.

        Returns:
            Documents with tags applied from matching InputSpecs.
        """
        sorted_specs: list[InputSpec] = sorted(
            a_inputs,
            key=lambda s: len(str(Path(s.path).resolve())),
            reverse=True,
        )
        tagged: list[Document] = []
        for doc in a_documents:
            doc_path: str = str(Path(doc.path).resolve())
            matched_tag: str = doc.tag
            for spec in sorted_specs:
                spec_path: str = str(Path(spec.path).resolve())
                if doc_path == spec_path or doc_path.startswith(spec_path.rstrip("/") + "/"):
                    matched_tag = spec.tag
                    break
            if matched_tag != doc.tag:
                tagged.append(
                    Document(
                        path=doc.path,
                        content=doc.content,
                        tokens=doc.tokens,
                        language=doc.language,
                        tag=matched_tag,
                    ),
                )
            else:
                tagged.append(doc)
        return tagged

    def _group_by_tag(self, a_documents: list[Document]) -> dict[str, list[Document]]:
        """Group documents by their tag.

        Args:
            a_documents: Documents to group.

        Returns:
            Mapping of tag to documents in that group.
        """
        groups: dict[str, list[Document]] = {}
        for doc in a_documents:
            groups.setdefault(doc.tag, []).append(doc)
        return groups

    async def _build_per_tag(
        self,
        a_groups: dict[str, list[Document]],
        a_output_path: Path,
    ) -> ContextResult:
        """Build output for each tag group.

        Args:
            a_groups: Documents grouped by tag.
            a_output_path: Base output path.

        Returns:
            Merged ContextResult across all tag groups.
        """
        results: list[ContextResult] = []
        for tag in sorted(a_groups.keys()):
            docs: list[Document] = a_groups[tag]
            if self._config.sort_by_importance:
                docs = self._analyzer.order_by_importance(docs)
            else:
                docs = sorted(docs, key=lambda d: d.path)
            tag_result: ContextResult = await self._build_single_tag(tag, docs, a_output_path)
            results.append(tag_result)

        all_paths: list[str] = []
        total_files: int = 0
        total_tokens: int = 0
        total_chunks: int = 0
        for r in results:
            all_paths.extend(r.output_paths)
            total_files += r.total_files
            total_tokens += r.total_tokens
            total_chunks += r.chunks

        merged: ContextResult = ContextResult(
            output_paths=tuple(all_paths),
            total_files=total_files,
            total_tokens=total_tokens,
            chunks=max(total_chunks, 1),
        )
        return merged

    async def _build_single_tag(
        self,
        a_tag: str,
        a_docs: list[Document],
        a_output_path: Path,
    ) -> ContextResult:
        """Build output for a single tag group.

        Args:
            a_tag: Tag name (empty string for untagged).
            a_docs: Documents in this tag group.
            a_output_path: Base output path.

        Returns:
            ContextResult for this tag group.
        """
        chunks: list[list[Document]]
        if self._config.mode == OutputMode.AGGREGATE and self._config.max_tokens is not None:
            chunks = self._split_documents(a_docs, self._config.max_tokens)
        else:
            chunks = [a_docs]

        logger.debug("Tag %r: %d docs, %d chunk(s)", a_tag, len(a_docs), len(chunks))

        result: ContextResult = await self._render_and_write(
            a_documents=a_docs,
            a_chunks=chunks,
            a_output_path=a_output_path,
            a_tag=a_tag,
        )
        return result

    def _split_documents(
        self,
        a_documents: list[Document],
        a_max_tokens: int | None,
    ) -> list[list[Document]]:
        """Split documents into chunks respecting token limit.

        When ``preserve_readme_in_chunks`` is enabled, README documents are
        prepended to every chunk.

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
            readme_docs: list[Document] = []
            other_docs: list[Document] = []
            if self._config.preserve_readme_in_chunks:
                for doc in a_documents:
                    role: FileRole = self._analyzer.classify_file(doc.path).role
                    if role == FileRole.README:
                        readme_docs.append(doc)
                    else:
                        other_docs.append(doc)
            else:
                other_docs = list(a_documents)

            readme_tokens: int = sum(d.tokens for d in readme_docs)
            chunks = []
            current_chunk: list[Document] = list(readme_docs)
            current_tokens: int = readme_tokens

            for doc in other_docs:
                if current_tokens + doc.tokens > a_max_tokens and current_tokens > readme_tokens:
                    chunks.append(current_chunk)
                    current_chunk = [*readme_docs, doc]
                    current_tokens = readme_tokens + doc.tokens
                else:
                    current_chunk.append(doc)
                    current_tokens += doc.tokens

            if current_chunk and (len(current_chunk) > len(readme_docs) or not chunks):
                chunks.append(current_chunk)

            if not chunks:
                chunks = [list(a_documents)]

        logger.debug(
            "Split %d documents into %d chunk(s) (max %s tokens)",
            len(a_documents),
            len(chunks),
            a_max_tokens,
        )

        return chunks

    def _make_output_path(self, a_base: Path, a_tag: str, a_index: int | None = None) -> Path:
        """Build an output path including optional tag and chunk index.

        Args:
            a_base: Base output path from config.
            a_tag: Tag name (empty for untagged).
            a_index: Optional 1-based chunk index for split outputs.

        Returns:
            Resolved output file path.
        """
        result: Path
        if a_base.suffix == ".md" and a_index is None and not a_tag:
            result = a_base
        else:
            directory: Path = a_base if a_base.suffix != ".md" else a_base.parent
            parts: list[str] = ["merged"]
            if a_tag:
                parts.append(a_tag)
            if a_index is not None:
                parts.append(str(a_index))
            result = directory / (".".join(parts) + ".md")
        return result

    async def _render_and_write(
        self,
        a_documents: list[Document],
        a_chunks: list[list[Document]],
        a_output_path: Path,
        a_tag: str = "",
    ) -> ContextResult:
        """Render documents and write to output files.

        Args:
            a_documents: All collected documents.
            a_chunks: Document chunks.
            a_output_path: Output path.
            a_tag: Tag for this group (affects output naming).

        Returns:
            ContextResult with output information.
        """
        total_tokens: int = sum(d.tokens for d in a_documents)

        logger.debug("Rendering %d documents, %d chunk(s)", len(a_documents), len(a_chunks))

        result: ContextResult
        if self._config.mode == OutputMode.AGGREGATE and self._config.max_tokens is None:
            result = await self._render_aggregate_single(a_documents, a_output_path, total_tokens, a_tag)
        elif self._config.mode == OutputMode.AGGREGATE and self._config.max_tokens is not None:
            result = await self._render_aggregate_split(a_chunks, a_output_path, total_tokens, a_tag)
        else:
            result = await self._render_separate(a_chunks, a_output_path, total_tokens, a_tag)

        return result

    async def _render_aggregate_single(
        self,
        a_documents: list[Document],
        a_output_path: Path,
        a_total_tokens: int,
        a_tag: str = "",
    ) -> ContextResult:
        """Write single aggregated output.

        Args:
            a_documents: All documents to render.
            a_output_path: Output path.
            a_total_tokens: Total token count.
            a_tag: Tag for this group.

        Returns:
            ContextResult.
        """
        content: str = self._renderer.render(a_documents)
        output_path: Path = self._make_output_path(a_output_path, a_tag)

        written: Path = await self._writer.write(content, output_path)
        logger.debug("Wrote %s", written)

        result: ContextResult = ContextResult(
            output_paths=(str(written),),
            total_files=len(a_documents),
            total_tokens=a_total_tokens,
        )
        return result

    async def _render_aggregate_split(
        self,
        a_chunks: list[list[Document]],
        a_output_path: Path,
        a_total_tokens: int,
        a_tag: str = "",
    ) -> ContextResult:
        """Write aggregated output split by tokens.

        Args:
            a_chunks: Document chunks.
            a_output_path: Output directory.
            a_total_tokens: Total token count.
            a_tag: Tag for this group.

        Returns:
            ContextResult.
        """
        write_tasks: list[asyncio.Task[Path]] = []
        for i, chunk in enumerate(a_chunks, start=1):
            content: str = self._renderer.render(chunk)
            numbered_path: Path = self._make_output_path(a_output_path, a_tag, a_index=i)
            write_tasks.append(asyncio.create_task(self._writer.write(content, numbered_path)))

        written_paths: list[Path] = list(await asyncio.gather(*write_tasks))
        for numbered_path in written_paths:
            logger.debug("Wrote chunk to %s", numbered_path)

        result: ContextResult = ContextResult(
            output_paths=tuple(str(p) for p in written_paths),
            total_files=sum(len(c) for c in a_chunks),
            total_tokens=a_total_tokens,
            chunks=len(a_chunks),
        )
        return result

    async def _render_separate(
        self,
        a_chunks: list[list[Document]],
        a_output_path: Path,
        a_total_tokens: int,
        a_tag: str = "",
    ) -> ContextResult:
        """Write separate mode output (one file per input group).

        Args:
            a_chunks: Document chunks (one per input).
            a_output_path: Output directory.
            a_total_tokens: Total token count.
            a_tag: Tag for this group.

        Returns:
            ContextResult.
        """
        write_coros: list[asyncio.Task[Path]] = []

        for chunk in a_chunks:
            if not chunk:
                continue
            first_doc: Document = chunk[0]
            if a_tag:
                stem: str = a_tag
            else:
                stem = Path(first_doc.path).stem or Path(first_doc.path).name
            content: str = self._renderer.render(chunk)
            directory: Path = a_output_path if a_output_path.suffix != ".md" else a_output_path.parent
            out_path: Path = directory / f"{stem}.md"
            write_coros.append(asyncio.create_task(self._writer.write(content, out_path)))

        written_paths: list[Path] = list(await asyncio.gather(*write_coros)) if write_coros else []
        for out_path in written_paths:
            logger.debug("Wrote %s", out_path)

        result: ContextResult = ContextResult(
            output_paths=tuple(str(p) for p in written_paths),
            total_files=sum(len(c) for c in a_chunks),
            total_tokens=a_total_tokens,
        )
        return result

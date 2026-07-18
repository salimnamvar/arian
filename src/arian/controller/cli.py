"""CLI controller for Arian."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import typer

from arian.bootstrap.logging import configure_logging
from arian.domain.enums import OutputMode
from arian.domain.exceptions import ProjectBaseError
from arian.domain.models import ContextConfig
from arian.infrastructure.config import DEFAULT_EXCLUDE
from arian.infrastructure.config import ContextBuilderSettings
from arian.infrastructure.config import LoggingConfig
from arian.infrastructure.output_path_resolver import resolve_output_path
from arian.infrastructure.tokenizer import count_tokens
from arian.renderers.markdown import MarkdownRenderer
from arian.repositories.collector import FilesystemCollector
from arian.repositories.writer import FileWriter
from arian.services.context_builder import ContextBuilderService

app = typer.Typer(help="Build LLM context from source files.")

logger = logging.getLogger(__name__)


@app.command()  # a-prefix-ignore: Typer CLI public names (not internal call args)
def build(  # a-prefix-ignore: Typer CLI public names (not internal call args)
    inputs: list[str] = typer.Argument(
        default_factory=lambda: ContextBuilderSettings().inputs,
        help='Input paths (optionally path:tag, e.g. "src/:core").',
    ),
    output: str = typer.Option(".tmp", "-o", "--output", help="Output location"),
    mode: str = typer.Option("separate", "--mode", case_sensitive=False, help="separate or aggregate"),
    exclude: list[str] = typer.Option(DEFAULT_EXCLUDE, "--exclude", help="Directories to exclude"),
    extensions: list[str] = typer.Option(
        [".py", ".md", ".txt", ".rst", ".puml"],
        "--extensions",
        help="File extensions to include",
    ),
    max_tokens: int | None = typer.Option(None, "--max-tokens", help="Max tokens per chunk"),
    compression: str = typer.Option(
        "auto",
        "--compression",
        help="Compression level: full, auto, signatures, minimal",
    ),
    no_comments: bool = typer.Option(False, "--no-comments", help="Strip code comments"),
    no_docstrings: bool = typer.Option(False, "--no-docstrings", help="Strip docstrings"),
    no_imports: bool = typer.Option(False, "--no-imports", help="Strip import statements"),
    no_directory_tree: bool = typer.Option(False, "--no-directory-tree", help="Skip directory structure"),
    no_file_summary: bool = typer.Option(False, "--no-file-summary", help="Skip file summary"),
    line_numbers: bool = typer.Option(False, "--line-numbers", help="Add line numbers to content"),
    instruction: str | None = typer.Option(None, "--instruction", help="Custom instructions for the LLM"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logging"),
) -> None:
    """Build context for LLM consumption."""
    configure_logging(LoggingConfig(level="DEBUG" if verbose else "INFO"))
    logger.info("Building context")

    # Filter out command name from variadic positional args (click quirk)
    a_inputs: list[str] = [p for p in inputs if p != "build"]

    try:
        settings = ContextBuilderSettings(
            inputs=a_inputs,
            output=output,
            mode=OutputMode.AGGREGATE if mode == "aggregate" else OutputMode.SEPARATE,
            exclude=exclude,
            extensions=extensions,
            max_tokens=max_tokens,
            compression=compression,
            include_comments=False if no_comments else None,
            include_docstrings=False if no_docstrings else None,
            include_imports=False if no_imports else None,
            include_line_numbers=line_numbers,
            include_directory_structure=not no_directory_tree,
            include_file_summary=not no_file_summary,
            custom_instructions=instruction,
        )

        resolved_path: Path = resolve_output_path(settings.output)
        base_config: ContextConfig = settings.to_domain()
        domain_config: ContextConfig = ContextConfig(
            inputs=base_config.inputs,
            extensions=base_config.extensions,
            exclude=base_config.exclude,
            mode=base_config.mode,
            output_path=str(resolved_path),
            max_tokens=base_config.max_tokens,
            compression=base_config.compression,
            include_comments=base_config.include_comments,
            include_docstrings=base_config.include_docstrings,
            include_imports=base_config.include_imports,
            include_line_numbers=base_config.include_line_numbers,
            include_directory_structure=base_config.include_directory_structure,
            include_file_summary=base_config.include_file_summary,
            include_token_counts=base_config.include_token_counts,
            custom_instructions=base_config.custom_instructions,
            sort_by_importance=base_config.sort_by_importance,
            preserve_readme_in_chunks=base_config.preserve_readme_in_chunks,
            pattern_rules=base_config.pattern_rules,
        )

        collector = FilesystemCollector(
            a_extensions=domain_config.extensions,
            a_exclude=domain_config.exclude,
            a_tokenizer=count_tokens,
        )
        writer = FileWriter(a_base_path=resolved_path)
        renderer = MarkdownRenderer(
            a_include_directory_structure=domain_config.include_directory_structure,
            a_include_file_summary=domain_config.include_file_summary,
            a_include_token_counts=domain_config.include_token_counts,
            a_include_line_numbers=domain_config.include_line_numbers,
            a_custom_instructions=domain_config.custom_instructions,
        )

        service = ContextBuilderService(
            a_config=domain_config,
            a_collector=collector,
            a_writer=writer,
            a_renderer=renderer,
        )
        result = asyncio.run(service.build_async())

        logger.info(
            "Build complete: %d files, %d tokens, %d chunk(s)",
            result.total_files,
            result.total_tokens,
            result.chunks,
        )
        for path in result.output_paths:
            logger.info("Output: %s", path)

    except ProjectBaseError as exc:
        logger.error("%s: %s", exc.reason, exc.message)  # noqa: TRY400 — clean CLI message
        raise typer.Exit(code=1) from exc
    except OSError as exc:
        logger.error("Filesystem error: %s", exc)  # noqa: TRY400 — clean CLI message
        raise typer.Exit(code=1) from exc

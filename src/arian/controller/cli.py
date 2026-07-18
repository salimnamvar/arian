"""CLI controller for Arian."""

from __future__ import annotations

from pathlib import Path

import typer

from arian.domain.enums import OutputMode
from arian.domain.models import ContextConfig
from arian.infrastructure.config import ContextBuilderSettings
from arian.infrastructure.output_path_resolver import resolve_output_path
from arian.infrastructure.tokenizer import count_tokens
from arian.renderer.markdown import MarkdownRenderer
from arian.repository.collector import FilesystemCollector
from arian.repository.writer import FileWriter
from arian.services.context_builder import ContextBuilderService

app = typer.Typer(help="Build LLM context from source files.")


@app.command()
def build(  # a-prefix-ignore: Typer CLI public names (not internal call args)
    inputs: list[str] = typer.Argument(
        default_factory=lambda: ContextBuilderSettings().inputs,
        help="Input paths to include.",
    ),
    output: str = typer.Option(".tmp", "-o", "--output", help="Output location"),
    mode: str = typer.Option("separate", "--mode", case_sensitive=False, help="separate or aggregate"),
    exclude: list[str] = typer.Option(
        ["archived", "__pycache__", ".git", ".mypy_cache", ".pytest_cache", "node_modules"],
        "--exclude",
        help="Directories to exclude",
    ),
    extensions: list[str] = typer.Option(
        [".py", ".md", ".txt", ".rst", ".puml"],
        "--extensions",
        help="File extensions to include",
    ),
    max_tokens: int | None = typer.Option(None, "--max-tokens", help="Max tokens per chunk"),
) -> None:
    """Build context for LLM consumption."""
    # Filter out command name from variadic positional args (click quirk)
    a_inputs: list[str] = [p for p in inputs if p != "build"]

    settings = ContextBuilderSettings(
        inputs=a_inputs,
        output=output,
        mode=OutputMode.AGGREGATE if mode == "aggregate" else OutputMode.SEPARATE,
        exclude=exclude,
        extensions=extensions,
        max_tokens=max_tokens,
    )

    # Convert to domain config and resolve output path
    resolved_path: Path = resolve_output_path(settings.output)
    domain_config: ContextConfig = ContextConfig(
        inputs=tuple(settings.inputs),
        extensions=frozenset(settings.extensions),
        exclude=frozenset(settings.exclude),
        mode=settings.mode,
        output_path=str(resolved_path),
        max_tokens=settings.max_tokens,
    )

    # Wire dependencies
    collector = FilesystemCollector(
        a_extensions=domain_config.extensions,
        a_exclude=domain_config.exclude,
        a_tokenizer=count_tokens,
    )
    writer = FileWriter(a_base_path=resolved_path)
    renderer = MarkdownRenderer()

    # Create service with injected dependencies
    service = ContextBuilderService(
        a_config=domain_config,
        a_collector=collector,
        a_writer=writer,
        a_renderer=renderer,
    )
    result = service.build()

    if result.chunks > 1:
        typer.echo(f"Split into {result.chunks} chunks: {', '.join(result.output_paths)}")
    else:
        typer.echo(f"Wrote {len(result.output_paths)} file(s): {', '.join(result.output_paths)}")

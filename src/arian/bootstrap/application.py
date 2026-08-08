"""Application factory — wires all layers together.

This is the single composition root. All dependency injection happens here.
No service, repository, or infrastructure object is created outside this module.
"""

from __future__ import annotations

from pathlib import Path

from arian.application.orchestrator import Application
from arian.application.validator import ContextRequestValidator
from arian.bootstrap.progress import LoggingProgressReporter
from arian.infrastructure.config import ArianConfig
from arian.infrastructure.file_output_writer import FileOutputWriter
from arian.infrastructure.gitignore_filter import GitignoreOptions
from arian.infrastructure.output.markdown.renderer import MarkdownRenderer
from arian.infrastructure.output_path_resolver import resolve_output_path
from arian.repository.filesystem.collector import FileCollector
from arian.repository.index.memory_repository import MemoryRepositoryIndex
from arian.service.analyzer.python_analyzer import PythonAnalyzer
from arian.service.builder.context_builder import ContextBuilder
from arian.service.builder.context_builder import ContextBuilderOptions
from arian.service.classifier.file_classifier import FileClassifier
from arian.service.context.materializer import ContextMaterializer
from arian.service.planner.context_planner import ContextPlanner


def create_application(a_config: ArianConfig | None = None) -> Application:
    """Create and wire the Application instance.

    Follows tenas pattern: single composition root, manual constructor injection.

    Args:
        a_config: Application configuration. Uses defaults if None.

    Returns:
        Wired Application instance ready to execute use cases.
    """
    cfg: ArianConfig = a_config or ArianConfig.load()
    root: Path = Path.cwd()

    classifier: FileClassifier = FileClassifier(a_config=cfg.classifier)
    collector: FileCollector = FileCollector(
        a_extensions=cfg.collector.extensions,
        a_exclude=cfg.collector.exclude,
        a_classifier=classifier,
        a_max_file_size=cfg.collector.max_file_size,
        a_gitignore_options=GitignoreOptions(
            enabled=cfg.collector.use_gitignore,
            nested=cfg.collector.nested_gitignore,
        ),
        a_language_config=cfg.language,
    )
    index: MemoryRepositoryIndex = MemoryRepositoryIndex()
    analyzer: PythonAnalyzer = PythonAnalyzer(a_config=cfg.analyzer)
    planner: ContextPlanner = ContextPlanner(a_classifier=classifier, a_config=cfg.planner)
    materializer: ContextMaterializer = ContextMaterializer(
        a_analyzer=analyzer,
        a_config=cfg.materializer,
    )
    progress = LoggingProgressReporter()
    builder: ContextBuilder = ContextBuilder(
        a_collector=collector,
        a_index=index,
        a_planner=planner,
        a_materializer=materializer,
        a_options=ContextBuilderOptions(
            progress=progress,
            max_concurrent=cfg.limits.default_max_concurrent_loads,
            max_collected_files=cfg.limits.max_collected_files,
            retry=cfg.retry,
            security=cfg.security,
        ),
    )
    renderer: MarkdownRenderer = MarkdownRenderer(a_config=cfg.renderer)
    output: FileOutputWriter = FileOutputWriter()
    validator = ContextRequestValidator(
        a_root=root,
        a_limits=cfg.limits,
        a_security=cfg.security,
        a_controller=cfg.controller,
    )

    return Application(
        a_builder=builder,
        a_renderer=renderer,
        a_output=output,
        a_resolve_output=resolve_output_path,
        a_security_config=cfg.security,
        a_validator=validator,
        a_root=root,
    )

"""Application factory — wires all layers together.

This is the single composition root. All dependency injection happens here.
No service, repository, or infrastructure object is created outside this module.
"""

from __future__ import annotations

from arian.application.application import Application
from arian.infrastructure.config import ArianConfig
from arian.infrastructure.file_output_writer import FileOutputWriter
from arian.infrastructure.output.markdown.renderer import MarkdownRenderer
from arian.repository.filesystem.collector import FileCollector
from arian.repository.index.memory_repository import MemoryRepositoryIndex
from arian.service.analyzer.python_analyzer import PythonAnalyzer
from arian.service.builder.context_builder import ContextBuilder
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

    classifier: FileClassifier = FileClassifier()
    collector: FileCollector = FileCollector(
        a_extensions=cfg.collector.extensions,
        a_exclude=cfg.collector.exclude,
        a_classifier=classifier,
    )
    index: MemoryRepositoryIndex = MemoryRepositoryIndex()
    analyzer: PythonAnalyzer = PythonAnalyzer()
    planner: ContextPlanner = ContextPlanner(a_classifier=classifier)
    materializer: ContextMaterializer = ContextMaterializer(a_analyzer=analyzer)
    builder: ContextBuilder = ContextBuilder(
        a_collector=collector,
        a_index=index,
        a_planner=planner,
        a_materializer=materializer,
    )
    renderer: MarkdownRenderer = MarkdownRenderer()

    output: FileOutputWriter = FileOutputWriter()

    return Application(a_builder=builder, a_renderer=renderer, a_output=output)

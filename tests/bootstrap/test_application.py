"""Integration tests for the bootstrap composition root."""

from __future__ import annotations

from arian.application.application import Application
from arian.bootstrap.application import create_application
from arian.infrastructure.config import ArianConfig


class TestCreateApplication:
    """Test that create_application wires all dependencies correctly."""

    def test_create_default(self) -> None:
        app = create_application()
        assert isinstance(app, Application)

    def test_create_with_custom_config(self) -> None:
        config = ArianConfig()
        app = create_application(config)
        assert isinstance(app, Application)

    def test_all_services_wired(self) -> None:
        app = create_application()
        assert hasattr(app, "_builder")
        assert hasattr(app, "_renderer")
        assert hasattr(app, "_output")
        assert app._builder is not None
        assert app._renderer is not None
        assert app._output is not None

    def test_builder_has_all_services(self) -> None:
        app = create_application()
        builder = app._builder
        assert hasattr(builder, "_collector")
        assert hasattr(builder, "_index")
        assert hasattr(builder, "_planner")
        assert hasattr(builder, "_materializer")

    def test_collector_has_config(self) -> None:
        app = create_application()
        collector = app._builder._collector
        assert hasattr(collector, "_extensions")
        assert hasattr(collector, "_filter")

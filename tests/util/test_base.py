"""Contract tests for arian.util base module and layer base modules.

Verifies metadata, lifecycle, capability introspection, deterministic
close, and invalid transitions for all base modules.
"""

from __future__ import annotations

import pytest

from arian.application.base import BaseApplicationModule
from arian.bootstrap.base import BaseBootstrapModule
from arian.controller.base import BaseControllerModule
from arian.domain.base import BaseDomainModule
from arian.infrastructure.base import BaseInfrastructureModule
from arian.repository.base import BaseRepositoryModule
from arian.service.base import BaseServiceModule
from arian.template.base import BaseTemplateModule
from arian.util.base import BaseModule, ModuleMetadata, ModuleState
from arian.util.protocol import ConcurrencyMode, ExecutionMode, FunctionProtocol


# ---------------------------------------------------------------------------
# BaseModule — metadata and identity
# ---------------------------------------------------------------------------


class TestBaseModuleMetadata:
    """Verify BaseModule stores and exposes metadata correctly."""

    def test_metadata_identity(self) -> None:
        metadata = ModuleMetadata(name="test.mod", layer="test", version="1.0.0")
        module = BaseModule(a_metadata=metadata)
        assert module.name == "test.mod"
        assert module.layer == "test"
        assert module.metadata.version == "1.0.0"

    def test_default_metadata_values(self) -> None:
        metadata = ModuleMetadata(name="x", layer="y")
        assert metadata.version == "0.1.0"
        assert metadata.capabilities == frozenset()

    def test_capabilities_declared(self) -> None:
        metadata = ModuleMetadata(name="m", layer="l", capabilities=frozenset({"sync", "async"}))
        module = BaseModule(a_metadata=metadata)
        assert module.has_capability("sync")
        assert module.has_capability("async")
        assert not module.has_capability("process")


# ---------------------------------------------------------------------------
# BaseModule — lifecycle state machine
# ---------------------------------------------------------------------------


class TestBaseModuleLifecycle:
    """Verify deterministic lifecycle transitions."""

    def test_initial_state_is_created(self) -> None:
        module = BaseModule(a_metadata=ModuleMetadata(name="m", layer="l"))
        assert module.state is ModuleState.CREATED

    def test_activate_transitions_to_ready(self) -> None:
        module = BaseModule(a_metadata=ModuleMetadata(name="m", layer="l"))
        module.activate()
        assert module.state is ModuleState.READY

    def test_close_transitions_to_closed(self) -> None:
        module = BaseModule(a_metadata=ModuleMetadata(name="m", layer="l"))
        module.activate()
        module.close()
        assert module.state is ModuleState.CLOSED

    def test_close_is_idempotent(self) -> None:
        module = BaseModule(a_metadata=ModuleMetadata(name="m", layer="l"))
        module.activate()
        module.close()
        module.close()
        assert module.state is ModuleState.CLOSED

    def test_fail_transitions_to_failed(self) -> None:
        module = BaseModule(a_metadata=ModuleMetadata(name="m", layer="l"))
        module.activate()
        module.fail()
        assert module.state is ModuleState.FAILED

    def test_fail_from_created(self) -> None:
        module = BaseModule(a_metadata=ModuleMetadata(name="m", layer="l"))
        module.fail()
        assert module.state is ModuleState.FAILED

    def test_activate_when_ready_raises(self) -> None:
        module = BaseModule(a_metadata=ModuleMetadata(name="m", layer="l"))
        module.activate()
        with pytest.raises(RuntimeError, match="Cannot activate"):
            module.activate()

    def test_close_when_created_raises(self) -> None:
        module = BaseModule(a_metadata=ModuleMetadata(name="m", layer="l"))
        with pytest.raises(RuntimeError, match="Cannot close"):
            module.close()

    def test_close_when_failed_raises(self) -> None:
        module = BaseModule(a_metadata=ModuleMetadata(name="m", layer="l"))
        module.activate()
        module.fail()
        with pytest.raises(RuntimeError, match="Cannot close"):
            module.close()

    def test_fail_when_closed_is_noop(self) -> None:
        module = BaseModule(a_metadata=ModuleMetadata(name="m", layer="l"))
        module.activate()
        module.close()
        module.fail()
        assert module.state is ModuleState.CLOSED


# ---------------------------------------------------------------------------
# BaseModule — runtime capabilities
# ---------------------------------------------------------------------------


class TestBaseModuleCapabilities:
    """Verify runtime capability registration."""

    def test_set_and_get_capability(self) -> None:
        module = BaseModule(a_metadata=ModuleMetadata(name="m", layer="l"))
        module.set_capability("db", "sqlite:///:memory:")
        assert module.get_capability("db") == "sqlite:///:memory:"

    def test_get_missing_capability_returns_none(self) -> None:
        module = BaseModule(a_metadata=ModuleMetadata(name="m", layer="l"))
        assert module.get_capability("missing") is None


# ---------------------------------------------------------------------------
# Layer base modules — metadata defaults
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cls", "expected_layer"),
    [
        (BaseDomainModule, "domain"),
        (BaseApplicationModule, "application"),
        (BaseServiceModule, "service"),
        (BaseRepositoryModule, "repository"),
        (BaseInfrastructureModule, "infrastructure"),
        (BaseControllerModule, "controller"),
        (BaseBootstrapModule, "bootstrap"),
        (BaseTemplateModule, "template"),
    ],
)
class TestLayerBaseModules:
    """Verify each layer base module has correct default metadata."""

    def test_layer_property(self, cls: type[BaseModule], expected_layer: str) -> None:
        module = cls()
        assert module.layer == expected_layer

    def test_initial_state(self, cls: type[BaseModule], expected_layer: str) -> None:
        module = cls()
        assert module.state is ModuleState.CREATED
        assert module.name.startswith(f"arian.{expected_layer}.")

    def test_lifecycle_transitions(self, cls: type[BaseModule], expected_layer: str) -> None:
        module = cls()
        module.activate()
        assert module.state is ModuleState.READY
        module.close()
        assert module.state is ModuleState.CLOSED


# ---------------------------------------------------------------------------
# FunctionProtocol — structural subtyping
# ---------------------------------------------------------------------------


class TestFunctionProtocol:
    """Verify FunctionProtocol structural subtyping."""

    def test_sync_function_satisfies_protocol(self) -> None:
        class Adder:
            @property
            def execution_mode(self) -> ExecutionMode:
                return ExecutionMode.SYNC

            @property
            def concurrency_mode(self) -> ConcurrencyMode:
                return ConcurrencyMode.SINGLE_THREADED

            @property
            def is_idempotent(self) -> bool:
                return True

            def __call__(self, a: int, b: int) -> int:
                return a + b

        func: FunctionProtocol = Adder()
        assert func.execution_mode is ExecutionMode.SYNC
        assert func.concurrency_mode is ConcurrencyMode.SINGLE_THREADED
        assert func.is_idempotent
        assert isinstance(func, FunctionProtocol)

    def test_async_function_satisfies_protocol(self) -> None:
        class AsyncFetcher:
            @property
            def execution_mode(self) -> ExecutionMode:
                return ExecutionMode.ASYNC

            @property
            def concurrency_mode(self) -> ConcurrencyMode:
                return ConcurrencyMode.THREAD_SAFE

            @property
            def is_idempotent(self) -> bool:
                return False

            def __call__(self, a_url: str) -> str:
                return f"fetched:{a_url}"

        func: FunctionProtocol = AsyncFetcher()
        assert func.execution_mode is ExecutionMode.ASYNC
        assert not func.is_idempotent


# ---------------------------------------------------------------------------
# Enums — value checks
# ---------------------------------------------------------------------------


class TestEnums:
    """Verify enum values are as expected."""

    def test_execution_mode_values(self) -> None:
        assert ExecutionMode.SYNC.value == "sync"
        assert ExecutionMode.ASYNC.value == "async"

    def test_concurrency_mode_values(self) -> None:
        assert ConcurrencyMode.SINGLE_THREADED.value == "single_threaded"
        assert ConcurrencyMode.THREAD_SAFE.value == "thread_safe"
        assert ConcurrencyMode.PROCESS_SAFE.value == "process_safe"

    def test_module_state_values(self) -> None:
        assert ModuleState.CREATED.value == "created"
        assert ModuleState.READY.value == "ready"
        assert ModuleState.CLOSING.value == "closing"
        assert ModuleState.CLOSED.value == "closed"
        assert ModuleState.FAILED.value == "failed"

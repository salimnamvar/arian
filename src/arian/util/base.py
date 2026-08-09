"""Base module with immutable identity metadata and deterministic lifecycle.

This is the lowest-level building block for all Arian modules.
It provides metadata, lifecycle state, and capability introspection
without owning application services, global registries, or business logic.
"""

from __future__ import annotations

from dataclasses import dataclass
import enum
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ModuleState(enum.Enum):
    """Lifecycle states for a module.

    Transitions are explicit and testable:
        CREATED -> READY -> CLOSING -> CLOSED
        CREATED -> READY -> FAILED
        CLOSING -> FAILED
    """

    CREATED = "created"
    READY = "ready"
    CLOSING = "closing"
    CLOSED = "closed"
    FAILED = "failed"


@dataclass(frozen=True)
class ModuleMetadata:
    """Immutable value object containing canonical module identity.

    Attributes:
        name: Canonical module name (e.g. 'arian.domain', 'arian.service.analyzer').
        layer: Architectural layer the module belongs to.
        version: Semantic version string.
        capabilities: Declared execution capabilities (e.g. 'sync', 'async').
    """

    name: str
    layer: str
    version: str = "0.1.0"
    capabilities: frozenset[str] = frozenset()


class BaseModule:
    """Immutable identity metadata, lifecycle state, and capability introspection.

    BaseModule is a convention and lifecycle boundary. It must not become
    a god object or a place for business logic.

    Use composition for optional capabilities. Do not add abstract methods
    that every layer must implement merely to satisfy inheritance.

    Attributes:
        metadata: Frozen module identity metadata.
        state: Current lifecycle state.
    """

    def __init__(self, a_metadata: ModuleMetadata) -> None:
        self._metadata = a_metadata
        self._state = ModuleState.CREATED
        self._capabilities: dict[str, Any] = {}

    @property
    def metadata(self) -> ModuleMetadata:
        """Return the module identity metadata."""
        return self._metadata

    @property
    def state(self) -> ModuleState:
        """Return the current lifecycle state."""
        return self._state

    @property
    def name(self) -> str:
        """Return the canonical module name."""
        return self._metadata.name

    @property
    def layer(self) -> str:
        """Return the architectural layer."""
        return self._metadata.layer

    def has_capability(self, a_capability: str) -> bool:
        """Check whether the module declares a given capability."""
        return a_capability in self._metadata.capabilities

    def set_capability(self, a_key: str, a_value: Any) -> None:
        """Register a runtime capability value.

        Args:
            a_key: Capability identifier.
            a_value: Capability value or handler.
        """
        self._capabilities[a_key] = a_value

    def get_capability(self, a_key: str) -> Any:
        """Retrieve a runtime capability value.

        Args:
            a_key: Capability identifier.

        Returns:
            The capability value, or None if not registered.
        """
        return self._capabilities.get(a_key)

    def activate(self) -> None:
        """Transition from CREATED to READY.

        Raises:
            RuntimeError: If the module is not in CREATED state.
        """
        if self._state is not ModuleState.CREATED:
            msg = f"Cannot activate module '{self.name}': current state is {self._state.value}"
            raise RuntimeError(msg)
        self._state = ModuleState.READY
        logger.debug("Module '%s' activated", self.name)

    def close(self) -> None:
        """Transition from READY to CLOSING then CLOSED.

        Idempotent: calling close() on an already-closed module is a no-op.

        Raises:
            RuntimeError: If the module is in CREATED or FAILED state.
        """
        if self._state is ModuleState.CREATED:
            msg = f"Cannot close module '{self.name}': module was never activated"
            raise RuntimeError(msg)
        if self._state is ModuleState.FAILED:
            msg = f"Cannot close module '{self.name}': module is in FAILED state"
            raise RuntimeError(msg)
        if self._state is ModuleState.CLOSED:
            return
        self._state = ModuleState.CLOSING
        self._on_close()
        self._state = ModuleState.CLOSED
        logger.debug("Module '%s' closed", self.name)

    def fail(self) -> None:
        """Transition to FAILED state from any non-CLOSED state.

        Idempotent: calling fail() on an already-failed or closed module
        is a no-op.
        """
        if self._state is not ModuleState.CLOSED:
            self._state = ModuleState.FAILED
            logger.debug("Module '%s' marked as failed", self.name)

    def _on_close(self) -> None:
        """Override point for subclass cleanup logic.

        Default implementation does nothing. Subclasses may override
        to release resources, close connections, or flush buffers.
        """

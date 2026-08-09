"""Controller layer base module.

Transport metadata and result-to-transport mapping boundary.
Must not do: validate business rules or construct adapters.
"""

from __future__ import annotations

from arian.util.base import BaseModule
from arian.util.base import ModuleMetadata


class BaseControllerModule(BaseModule):
    """Thin marker subclass for controller modules.

    Provides identity metadata and lifecycle for transport boundary modules.
    """

    def __init__(self, a_metadata: ModuleMetadata | None = None) -> None:
        metadata = a_metadata or ModuleMetadata(
            name=f"arian.controller.{type(self).__name__}",
            layer="controller",
        )
        super().__init__(a_metadata=metadata)

"""Application layer base module.

Use-case lifecycle and injected port inventory.
Must not do: construct services, repositories, or infrastructure.
"""

from __future__ import annotations

from arian.util.base import BaseModule
from arian.util.base import ModuleMetadata


class BaseApplicationModule(BaseModule):
    """Thin marker subclass for application modules.

    Provides identity metadata and lifecycle for use-case orchestration.
    """

    def __init__(self, a_metadata: ModuleMetadata | None = None) -> None:
        metadata = a_metadata or ModuleMetadata(
            name=f"arian.application.{type(self).__name__}",
            layer="application",
        )
        super().__init__(a_metadata=metadata)

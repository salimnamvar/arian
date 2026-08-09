"""Infrastructure layer base module.

External-resource ownership, timeout, retry, and cleanup contract.
Must not do: orchestrate use cases.
"""

from __future__ import annotations

from arian.util.base import BaseModule
from arian.util.base import ModuleMetadata


class BaseInfrastructureModule(BaseModule):
    """Thin marker subclass for infrastructure modules.

    Provides identity metadata and lifecycle for external resource adapters.
    """

    def __init__(self, a_metadata: ModuleMetadata | None = None) -> None:
        metadata = a_metadata or ModuleMetadata(
            name=f"arian.infrastructure.{type(self).__name__}",
            layer="infrastructure",
        )
        super().__init__(a_metadata=metadata)

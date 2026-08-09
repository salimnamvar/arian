"""Repository layer base module.

Persistence adapter identity and transaction/resource contract.
Must not do: know application or controller concerns.
"""

from __future__ import annotations

from arian.util.base import BaseModule
from arian.util.base import ModuleMetadata


class BaseRepositoryModule(BaseModule):
    """Thin marker subclass for repository modules.

    Provides identity metadata and lifecycle for persistence adapters.
    """

    def __init__(self, a_metadata: ModuleMetadata | None = None) -> None:
        metadata = a_metadata or ModuleMetadata(
            name=f"arian.repository.{type(self).__name__}",
            layer="repository",
        )
        super().__init__(a_metadata=metadata)

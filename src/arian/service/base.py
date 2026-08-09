"""Service layer base module.

Domain workflow identity and collaborator declarations.
Must not do: import application, controller, or infrastructure.
"""

from __future__ import annotations

from arian.util.base import BaseModule
from arian.util.base import ModuleMetadata


class BaseServiceModule(BaseModule):
    """Thin marker subclass for service modules.

    Provides identity metadata and lifecycle for domain workflow services.
    """

    def __init__(self, a_metadata: ModuleMetadata | None = None) -> None:
        metadata = a_metadata or ModuleMetadata(
            name=f"arian.service.{type(self).__name__}",
            layer="service",
        )
        super().__init__(a_metadata=metadata)

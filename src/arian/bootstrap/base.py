"""Bootstrap layer base module.

Composition-root lifecycle and graph validation.
Must not do: contain business workflows.
"""

from __future__ import annotations

from arian.util.base import BaseModule
from arian.util.base import ModuleMetadata


class BaseBootstrapModule(BaseModule):
    """Thin marker subclass for bootstrap modules.

    Provides identity metadata and lifecycle for the composition root.
    """

    def __init__(self, a_metadata: ModuleMetadata | None = None) -> None:
        metadata = a_metadata or ModuleMetadata(
            name=f"arian.bootstrap.{type(self).__name__}",
            layer="bootstrap",
        )
        super().__init__(a_metadata=metadata)

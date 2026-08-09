"""Template layer base module.

Rendering/template identity and renderer contract.
Must not do: contain business or persistence logic.
"""

from __future__ import annotations

from arian.util.base import BaseModule
from arian.util.base import ModuleMetadata


class BaseTemplateModule(BaseModule):
    """Thin marker subclass for template modules.

    Provides identity metadata and lifecycle for rendering templates.
    """

    def __init__(self, a_metadata: ModuleMetadata | None = None) -> None:
        metadata = a_metadata or ModuleMetadata(
            name=f"arian.template.{type(self).__name__}",
            layer="template",
        )
        super().__init__(a_metadata=metadata)

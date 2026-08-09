"""Domain layer base module.

Pure model/port identity and invariant declarations.
Must not do: I/O, logging setup, adapters, outer imports.
"""

from __future__ import annotations

from arian.util.base import BaseModule
from arian.util.base import ModuleMetadata


class BaseDomainModule(BaseModule):
    """Thin marker subclass for domain modules.

    Provides identity metadata and lifecycle for domain objects.
    Domain modules that are pure value objects or pure functions
    do not need to inherit this class.
    """

    def __init__(self, a_metadata: ModuleMetadata | None = None) -> None:
        metadata = a_metadata or ModuleMetadata(
            name=f"arian.domain.{type(self).__name__}",
            layer="domain",
        )
        super().__init__(a_metadata=metadata)

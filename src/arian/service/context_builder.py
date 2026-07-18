"""Service layer for Arian.

Provides the main orchestration service.
"""

# Re-export from services/ for backwards compatibility
from arian.services.context_builder import ContextBuilderService

__all__ = ["ContextBuilderService"]

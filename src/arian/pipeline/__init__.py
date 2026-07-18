"""Pipeline layer for Arian.

Orchestrates data flow through collection, splitting, and rendering stages.
"""

from arian.pipeline.renderer_pipeline import render_and_write
from arian.pipeline.splitter_pipeline import split_documents

__all__ = ["render_and_write", "split_documents"]

"""Tests for domain shared event hook protocols."""

from __future__ import annotations

from arian.domain.shared.events import PipelineProgressProtocol


def test_pipeline_progress_protocol() -> None:
    """Test PipelineProgressProtocol structural subtyping."""

    class Reporter:
        def __init__(self) -> None:
            self.stages: list[str] = []

        def on_stage_start(self, a_stage: str, a_total: int) -> None:
            self.stages.append(f"start:{a_stage}:{a_total}")

        def on_stage_progress(self, a_stage: str, a_current: int, a_total: int) -> None:
            self.stages.append(f"progress:{a_stage}:{a_current}/{a_total}")

        def on_stage_complete(self, a_stage: str) -> None:
            self.stages.append(f"complete:{a_stage}")

    reporter: PipelineProgressProtocol = Reporter()
    reporter.on_stage_start("load", 3)
    reporter.on_stage_progress("load", 1, 3)
    reporter.on_stage_complete("load")
    assert reporter.stages == ["start:load:3", "progress:load:1/3", "complete:load"]

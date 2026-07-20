"""Tests for lazy content loading."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from arian.domain.context.models import ContextTask
from arian.domain.shared.enums import TokenBudget
from arian.domain.shared.tokenizer import estimate_tokens_from_size
from arian.repository.filesystem.collector import FileCollector
from arian.repository.index.memory_repository import MemoryRepositoryIndex
from arian.service.analyzer.python_analyzer import PythonAnalyzer
from arian.service.builder.context_builder import ContextBuilder
from arian.service.classifier.file_classifier import FileClassifier
from arian.service.context.materializer import ContextMaterializer
from arian.service.planner.context_planner import ContextPlanner


class TestEstimateTokensFromSize:
    """Tests for estimate_tokens_from_size heuristic."""

    def test_empty_file(self) -> None:
        assert estimate_tokens_from_size(0) == 1

    def test_one_byte(self) -> None:
        assert estimate_tokens_from_size(1) == 1

    def test_four_bytes(self) -> None:
        assert estimate_tokens_from_size(4) == 1

    def test_eight_bytes(self) -> None:
        assert estimate_tokens_from_size(8) == 2

    def test_large_file(self) -> None:
        assert estimate_tokens_from_size(10000) == 2500

    def test_non_multiple_of_four(self) -> None:
        assert estimate_tokens_from_size(10) == 2


class TestCollectorLazyLoading:
    """Tests that collector does not read file content."""

    async def test_collect_uses_stat_not_read(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("def main(): pass")

        collector = FileCollector(
            a_extensions=frozenset({".py"}),
            a_exclude=frozenset(),
        )

        with patch.object(Path, "read_text", side_effect=Exception("should not be called")):
            files = await collector.collect(tmp_path)

        assert len(files) == 1
        assert files[0].hash == ""
        assert files[0].size_bytes > 0

    async def test_collect_sets_size_bytes(self, tmp_path: Path) -> None:
        content = "x = 1\n"
        (tmp_path / "test.py").write_text(content)

        collector = FileCollector(
            a_extensions=frozenset({".py"}),
            a_exclude=frozenset(),
        )
        files = await collector.collect(tmp_path)

        assert len(files) == 1
        assert files[0].size_bytes == len(content.encode("utf-8"))

    async def test_collect_estimates_tokens(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("x = 1\n")

        collector = FileCollector(
            a_extensions=frozenset({".py"}),
            a_exclude=frozenset(),
        )
        files = await collector.collect(tmp_path)

        assert len(files) == 1
        assert files[0].tokens == max(1, files[0].size_bytes // 4)


class TestEmptyFileCollection:
    """Tests for empty file handling."""

    async def test_empty_file_collected(self, tmp_path: Path) -> None:
        (tmp_path / "empty.py").write_text("")

        collector = FileCollector(
            a_extensions=frozenset({".py"}),
            a_exclude=frozenset(),
        )
        files = await collector.collect(tmp_path)

        assert len(files) == 1
        assert files[0].size_bytes == 0
        assert files[0].tokens == 1


class TestHashLifecycle:
    """Tests for hash field lifecycle: empty during collection, filled after load_content."""

    async def test_hash_empty_after_build(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("x = 1\n")

        classifier = FileClassifier()
        collector = FileCollector(
            a_extensions=frozenset({".py"}),
            a_exclude=frozenset(),
            a_classifier=classifier,
        )
        index = MemoryRepositoryIndex()
        planner = ContextPlanner(a_classifier=classifier)
        materializer = ContextMaterializer(a_analyzer=PythonAnalyzer())
        builder = ContextBuilder(
            a_collector=collector,
            a_index=index,
            a_planner=planner,
            a_materializer=materializer,
        )

        budget = TokenBudget(max_tokens=5000)
        await builder.build(a_path=tmp_path, a_task=ContextTask.GENERAL, a_budget=budget)

        stored_files = await index.list_files()
        for f in stored_files:
            assert f.hash == ""

    async def test_hash_populated_after_load_content(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("x = 1\n")

        classifier = FileClassifier()
        collector = FileCollector(
            a_extensions=frozenset({".py"}),
            a_exclude=frozenset(),
            a_classifier=classifier,
        )
        index = MemoryRepositoryIndex()
        planner = ContextPlanner(a_classifier=classifier)
        materializer = ContextMaterializer(a_analyzer=PythonAnalyzer())
        builder = ContextBuilder(
            a_collector=collector,
            a_index=index,
            a_planner=planner,
            a_materializer=materializer,
        )

        budget = TokenBudget(max_tokens=5000)
        plan = await builder.build(a_path=tmp_path, a_task=ContextTask.GENERAL, a_budget=budget)
        content_map, _skipped = await builder.load_content(a_plan=plan, a_root=tmp_path)

        for _path, content in content_map.items():
            assert content.hash != ""
            assert len(content.hash) == 16


class TestSingleReadVerification:
    """Tests that files are read exactly once during load_content."""

    async def test_single_read_per_file(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("x = 1\n")

        classifier = FileClassifier()
        collector = FileCollector(
            a_extensions=frozenset({".py"}),
            a_exclude=frozenset(),
            a_classifier=classifier,
        )
        index = MemoryRepositoryIndex()
        planner = ContextPlanner(a_classifier=classifier)
        materializer = ContextMaterializer(a_analyzer=PythonAnalyzer())
        builder = ContextBuilder(
            a_collector=collector,
            a_index=index,
            a_planner=planner,
            a_materializer=materializer,
        )

        budget = TokenBudget(max_tokens=5000)
        plan = await builder.build(a_path=tmp_path, a_task=ContextTask.GENERAL, a_budget=budget)

        read_count = 0
        original_read_text = Path.read_text

        def counting_read_text(self: Path, *args: object, **kwargs: object) -> str:
            nonlocal read_count
            read_count += 1
            return original_read_text(self, *args, **kwargs)

        with patch.object(Path, "read_text", counting_read_text):
            content_map, _skipped = await builder.load_content(a_plan=plan, a_root=tmp_path)

        assert read_count == len(content_map)


class TestBinaryFileSkipping:
    """Tests that binary files are skipped by extension filter."""

    async def test_binary_not_collected(self, tmp_path: Path) -> None:
        (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n")
        (tmp_path / "main.py").write_text("x = 1\n")

        collector = FileCollector(
            a_extensions=frozenset({".py"}),
            a_exclude=frozenset(),
        )
        files = await collector.collect(tmp_path)

        assert len(files) == 1
        assert files[0].path == "main.py"


class TestSymlinkDeduplication:
    """Tests that symlinks are deduplicated."""

    async def test_symlink_deduplicated(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("x = 1\n")
        (tmp_path / "link.py").symlink_to(tmp_path / "main.py")

        collector = FileCollector(
            a_extensions=frozenset({".py"}),
            a_exclude=frozenset(),
        )
        files = await collector.collect(tmp_path)

        assert len(files) == 1

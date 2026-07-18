"""Unit tests for renderer layer."""

from __future__ import annotations

from pathlib import Path

from arian.domain.models import Document
from arian.infrastructure.language import detect_language
from arian.renderers.markdown import MarkdownRenderer


def test_markdown_renderer_render_empty() -> None:
    """Test rendering empty document list."""
    renderer = MarkdownRenderer(
        a_include_directory_structure=False,
        a_include_file_summary=False,
        a_include_token_counts=False,
    )
    result: str = renderer.render([])
    assert result.strip() == ""


def test_markdown_renderer_render_single_document() -> None:
    """Test rendering single document with language."""
    renderer = MarkdownRenderer(
        a_include_directory_structure=False,
        a_include_file_summary=False,
        a_include_token_counts=False,
    )
    doc = Document(path="test.py", content="print('hello')", tokens=10, language="python")
    result: str = renderer.render([doc])

    assert "--- SOURCE: test.py ---" in result
    assert "```python" in result
    assert "print('hello')" in result
    assert "```" in result


def test_markdown_renderer_render_with_headers() -> None:
    """Test rendering includes directory structure and summary."""
    renderer = MarkdownRenderer()
    doc = Document(path="test.py", content="print('hello')", tokens=10, language="python")
    result: str = renderer.render([doc])

    assert "# Repository Structure" in result
    assert "# File Summary" in result
    assert "test.py" in result
    assert "10 tokens" in result
    assert "--- SOURCE: test.py (10 tokens) ---" in result


def test_markdown_renderer_custom_instructions() -> None:
    """Test rendering injects custom instructions."""
    renderer = MarkdownRenderer(
        a_include_directory_structure=False,
        a_include_file_summary=False,
        a_include_token_counts=False,
        a_custom_instructions="Focus on security",
    )
    doc = Document(path="a.py", content="x = 1", tokens=3, language="python")
    result: str = renderer.render([doc])

    assert "# Instructions" in result
    assert "Focus on security" in result


def test_markdown_renderer_line_numbers() -> None:
    """Test rendering with line numbers."""
    renderer = MarkdownRenderer(
        a_include_directory_structure=False,
        a_include_file_summary=False,
        a_include_token_counts=False,
        a_include_line_numbers=True,
    )
    doc = Document(path="a.py", content="x = 1\ny = 2", tokens=5, language="python")
    result: str = renderer.render([doc])

    assert "   1| x = 1" in result
    assert "   2| y = 2" in result


def test_markdown_renderer_render_multiple_documents() -> None:
    """Test rendering multiple documents."""
    renderer = MarkdownRenderer(
        a_include_directory_structure=False,
        a_include_file_summary=False,
        a_include_token_counts=False,
    )
    docs = [
        Document(path="a.py", content="code a", tokens=5, language="python"),
        Document(path="b.md", content="markdown b", tokens=5, language="markdown"),
    ]
    result: str = renderer.render(docs)

    assert "--- SOURCE: a.py ---" in result
    assert "--- SOURCE: b.md ---" in result
    assert "```python" in result
    assert "```markdown" in result


def test_markdown_renderer_render_no_language() -> None:
    """Test rendering document without language."""
    renderer = MarkdownRenderer(
        a_include_directory_structure=False,
        a_include_file_summary=False,
        a_include_token_counts=False,
    )
    doc = Document(path="notes.txt", content="plain text", tokens=10, language="")
    result: str = renderer.render([doc])

    assert "--- SOURCE: notes.txt ---" in result
    assert "plain text" in result
    assert "```" not in result


def test_detect_language_py() -> None:
    """Test language detection for Python files."""
    result: str = detect_language(Path("test.py"))
    assert result == "python"


def test_detect_language_md() -> None:
    """Test language detection for Markdown files."""
    result: str = detect_language(Path("README.md"))
    assert result == "markdown"


def test_detect_language_txt() -> None:
    """Test language detection for text files."""
    result: str = detect_language(Path("notes.txt"))
    assert result == ""


def test_detect_language_rst() -> None:
    """Test language detection for RST files."""
    result: str = detect_language(Path("docs.rst"))
    assert result == "rst"


def test_detect_language_puml() -> None:
    """Test language detection for PlantUML files."""
    result: str = detect_language(Path("diagram.puml"))
    assert result == "puml"


def test_detect_language_unknown() -> None:
    """Test language detection for unknown extensions."""
    result: str = detect_language(Path("file.unknown_ext"))
    assert result == ""


def test_detect_language_rust() -> None:
    """Test language detection for Rust files."""
    result: str = detect_language(Path("lib.rs"))
    assert result == "rust"

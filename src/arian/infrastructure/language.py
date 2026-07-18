"""Language detection for document rendering."""

from __future__ import annotations

from pathlib import Path


def detect_language(a_path: Path) -> str:
    """Detect language from file extension.

    Args:
        a_path: Path to detect language for.

    Returns:
        Detected language identifier or empty string.
    """
    lang_map: dict[str, str] = {
        ".py": "python",
        ".pyx": "python",
        ".pyw": "python",
        ".js": "javascript",
        ".jsx": "jsx",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".c": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".hxx": "cpp",
        ".cs": "csharp",
        ".rb": "ruby",
        ".php": "php",
        ".phtml": "php",
        ".swift": "swift",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".fish": "fish",
        ".sql": "sql",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        ".md": "markdown",
        ".markdown": "markdown",
        ".rst": "rst",
        ".txt": "",
        ".json": "json",
        ".jsonl": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".xml": "xml",
        ".svg": "svg",
        ".puml": "puml",
        ".plantuml": "puml",
        ".dockerfile": "dockerfile",
        ".mk": "makefile",
        ".makefile": "makefile",
        ".ini": "ini",
        ".cfg": "ini",
        ".env": "dotenv",
        ".gradle": "gradle",
        ".scala": "scala",
        ".r": "r",
        ".rmd": "r",
        ".lua": "lua",
        ".vim": "vim",
        ".svelte": "svelte",
        ".vue": "vue",
        ".astro": "astro",
    }
    result: str = lang_map.get(a_path.suffix.lower(), "")
    return result

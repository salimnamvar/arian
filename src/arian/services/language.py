"""Language detection for document services.

Maps file extensions to language identifiers for syntax highlighting.
"""

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
        # Python
        ".py": "python",
        ".pyx": "python",
        ".pyw": "python",
        # JavaScript/TypeScript
        ".js": "javascript",
        ".jsx": "jsx",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".mjs": "javascript",
        ".cjs": "javascript",
        # Go
        ".go": "go",
        # Rust
        ".rs": "rust",
        # Java/Kotlin
        ".java": "java",
        ".kt": "kotlin",
        ".kts": "kotlin",
        # C/C++
        ".c": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".hxx": "cpp",
        # C#
        ".cs": "csharp",
        # Ruby
        ".rb": "ruby",
        # PHP
        ".php": "php",
        ".phtml": "php",
        # Swift
        ".swift": "swift",
        # Shell
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".fish": "fish",
        # SQL
        ".sql": "sql",
        # HTML/CSS
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        # Markup/Structured
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
        # Documentation
        ".puml": "puml",
        ".plantuml": "puml",
        # Docker
        ".dockerfile": "dockerfile",
        # Make
        ".mk": "makefile",
        ".makefile": "makefile",
        # Config
        ".ini": "ini",
        ".cfg": "ini",
        ".env": "dotenv",
        # Other
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
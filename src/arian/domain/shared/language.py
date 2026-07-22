"""Language detection — domain concept moved from infrastructure.

Detects programming language from file extension, filename, shebang,
and modeline for rendering and analysis purposes.
"""

from __future__ import annotations

from pathlib import Path

_LANG_MAP: dict[str, str] = {
    ".py": "python",
    ".pyx": "python",
    ".pyw": "python",
    ".pyi": "python",
    ".ipynb": "python",
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
    ".jinja2": "jinja2",
    ".j2": "jinja2",
    ".jinja": "jinja2",
    ".mustache": "mustache",
    ".hbs": "handlebars",
    ".tmpl": "template",
    ".tpl": "template",
    ".proto": "protobuf",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".tf": "hcl",
    ".hcl": "hcl",
    ".csv": "csv",
    ".tsv": "tsv",
    ".log": "log",
    ".diff": "diff",
    ".patch": "diff",
}

LANG_EXTENSIONS: frozenset[str] = frozenset(_LANG_MAP.keys())

_FILENAME_MAP: dict[str, str] = {
    "makefile": "make",
    "dockerfile": "dockerfile",
    "cmakelists.txt": "cmake",
    "gemfile": "ruby",
    "rakefile": "ruby",
    "justfile": "just",
}

_SHEBANG_MAP: dict[str, str] = {
    "python": "python",
    "python3": "python",
    "node": "javascript",
    "ruby": "ruby",
    "bash": "bash",
    "sh": "sh",
    "zsh": "zsh",
    "fish": "fish",
    "perl": "perl",
    "lua": "lua",
    "php": "php",
    "r": "r",
    "scala": "scala",
    "go": "go",
    "rust": "rust",
}


def detect_language(a_path: Path) -> str:
    """Detect language using extension, filename, shebang, and modeline.

    Priority:
        1. Extension lookup in ``_LANG_MAP``
        2. Filename lookup in ``_FILENAME_MAP``
        3. Shebang detection (first line)
        4. Modeline detection (last 5 lines, ``ft=...``)
        5. Empty string (unknown)

    Args:
        a_path: Path to detect language for.

    Returns:
        Detected language identifier or empty string.
    """
    result: str = ""

    ext: str = a_path.suffix.lower()
    if _LANG_MAP.get(ext):
        result = _LANG_MAP[ext]
    else:
        name: str = a_path.name.lower()
        result = _FILENAME_MAP[name] if name in _FILENAME_MAP else _detect_by_content(a_path)

    return result


def _detect_by_content(a_path: Path) -> str:
    """Detect language by reading file content (shebang and modeline).

    Args:
        a_path: Path to read content from.

    Returns:
        Detected language identifier or empty string.
    """
    result: str = ""

    try:
        with a_path.open("r", encoding="utf-8", errors="ignore") as fh:
            first_line: str = fh.readline(256)
            if first_line.startswith("#!"):
                parts: list[str] = first_line.split("/")
                tail: str = parts[-1].strip() if parts else ""
                tokens: list[str] = tail.split()
                interpreter: str = (
                    tokens[1] if len(tokens) >= 2 and tokens[0] == "env" else (tokens[0] if tokens else "")
                )
                if interpreter in _SHEBANG_MAP:
                    result = _SHEBANG_MAP[interpreter]
    except OSError:
        pass

    if not result:
        try:
            with a_path.open("r", encoding="utf-8", errors="ignore") as fh:
                lines: list[str] = fh.readlines()
                for line in lines[-5:]:
                    if "ft=" in line:
                        ft_value: str = line.split("ft=")[-1].split()[0]
                        if ft_value in _LANG_MAP.values():
                            result = ft_value
                            break
        except OSError:
            pass

    return result

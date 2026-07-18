"""Content compressor with language-aware stripping."""

from __future__ import annotations

from collections.abc import Callable
import re

from arian.domain.models import CompressionLevel

_HASH_COMMENT_LANGS: frozenset[str] = frozenset({"python", "ruby", "bash", "shell", "yaml", "toml", "r"})
_SLASH_COMMENT_LANGS: frozenset[str] = frozenset(
    {"javascript", "typescript", "jsx", "tsx", "java", "c", "cpp", "csharp", "go", "rust", "kotlin", "swift"},
)
_DEF_PATTERN = re.compile(
    r"^(\s*)(async\s+)?(def|class|async\s+def)\s+\w+.*?:\s*(?:#.*)?$",
)
_IMPORT_PATTERN = re.compile(r"^\s*(from\s+\S+\s+import|import\s+)")
_DOCSTRING_START = re.compile(r'^\s*[rRuUbBfF]*("""|\'\'\')')


class ContentCompressor:
    """Applies compression levels to source content."""

    def __init__(self, a_tokenizer: Callable[[str], int] | None = None) -> None:
        """Initialize compressor.

        Args:
            a_tokenizer: Optional token counting function for post-compress metrics.
        """
        self._tokenizer = a_tokenizer

    def compress(
        self,
        a_content: str,
        a_language: str,
        a_compression_level: CompressionLevel,
    ) -> str:
        """Compress content according to the given level.

        Args:
            a_content: Original file content.
            a_language: Detected language identifier.
            a_compression_level: Compression controls.

        Returns:
            Compressed content string.
        """
        content: str = a_content
        level: CompressionLevel = a_compression_level

        if not level.keep_comments:
            content = self._strip_comments(content, a_language)

        if not level.keep_docstrings and a_language == "python":
            content = self._strip_docstrings(content)

        if not level.keep_imports:
            content = self._strip_imports(content, a_language)

        if not level.keep_implementation and a_language == "python":
            content = self._strip_implementation(content)

        collapsed: str = self._collapse_blank_lines(content)
        return collapsed

    def _strip_comments(self, a_content: str, a_language: str) -> str:
        """Strip line comments for the given language.

        Args:
            a_content: Source content.
            a_language: Language identifier.

        Returns:
            Content with comments removed.
        """
        lines: list[str] = a_content.splitlines()
        kept: list[str] = []
        lang: str = a_language.lower()

        for line in lines:
            stripped: str = line.lstrip()
            if lang in _HASH_COMMENT_LANGS and stripped.startswith("#"):
                continue
            if lang in _SLASH_COMMENT_LANGS and stripped.startswith(("//", "/*")):
                continue
            if lang in _HASH_COMMENT_LANGS and "#" in line and not self._is_inside_string_heuristic(line):
                hash_idx: int = line.find("#")
                code_part: str = line[:hash_idx].rstrip()
                if code_part:
                    kept.append(code_part)
                continue
            kept.append(line)

        joined: str = "\n".join(kept)
        return joined

    def _is_inside_string_heuristic(self, a_line: str) -> bool:
        """Heuristic: treat # after an odd quote count as inside a string.

        Args:
            a_line: Source line.

        Returns:
            True if # likely appears inside a string literal.
        """
        before_hash: str = a_line.split("#", 1)[0]
        single: int = before_hash.count("'") - before_hash.count("\\'")
        double: int = before_hash.count('"') - before_hash.count('\\"')
        result: bool = (single % 2 == 1) or (double % 2 == 1)
        return result

    def _strip_docstrings(self, a_content: str) -> str:
        """Strip Python triple-quoted docstrings.

        Args:
            a_content: Python source content.

        Returns:
            Content without docstrings.
        """
        result: str = re.sub(
            r'(?m)^[ \t]*[rRuUbBfF]?("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')\s*\n?',
            "",
            a_content,
        )
        return result

    def _strip_imports(self, a_content: str, a_language: str) -> str:
        """Strip import statements.

        Args:
            a_content: Source content.
            a_language: Language identifier.

        Returns:
            Content without imports.
        """
        lines: list[str] = a_content.splitlines()
        kept: list[str] = []
        lang: str = a_language.lower()

        for line in lines:
            if lang == "python" and _IMPORT_PATTERN.match(line):
                continue
            if lang in _SLASH_COMMENT_LANGS and re.match(r"^\s*import\s+", line):
                continue
            kept.append(line)

        result: str = "\n".join(kept)
        return result

    def _strip_implementation(self, a_content: str) -> str:
        """Replace Python function/method bodies with ellipsis.

        Args:
            a_content: Python source content.

        Returns:
            Content with implementations replaced by ``...``.
        """
        lines: list[str] = a_content.splitlines()
        result_lines: list[str] = []
        i: int = 0
        n: int = len(lines)

        while i < n:
            line: str = lines[i]
            match = _DEF_PATTERN.match(line)
            if match:
                result_lines.append(line.rstrip())
                indent: str = match.group(1)
                body_indent_len: int = len(indent) + 4
                i += 1
                # Skip docstring immediately after def/class
                if i < n and _DOCSTRING_START.match(lines[i]):
                    quote: str = '"""' if '"""' in lines[i] else "'''"
                    if lines[i].count(quote) >= 2:
                        result_lines.append(lines[i])
                        i += 1
                    else:
                        result_lines.append(lines[i])
                        i += 1
                        while i < n and quote not in lines[i]:
                            result_lines.append(lines[i])
                            i += 1
                        if i < n:
                            result_lines.append(lines[i])
                            i += 1
                # Skip body lines that are more indented
                while i < n:
                    body_line: str = lines[i]
                    if body_line.strip() == "":
                        i += 1
                        continue
                    leading: int = len(body_line) - len(body_line.lstrip())
                    if leading >= body_indent_len:
                        i += 1
                        continue
                    break
                result_lines.append(f"{indent}    ...")
            else:
                result_lines.append(line)
                i += 1

        result: str = "\n".join(result_lines)
        return result

    def _collapse_blank_lines(self, a_content: str) -> str:
        """Collapse runs of blank lines to a single blank line.

        Args:
            a_content: Source content.

        Returns:
            Content with collapsed blank lines.
        """
        result: str = re.sub(r"\n{3,}", "\n\n", a_content)
        return result.strip() + ("\n" if a_content.endswith("\n") else "")

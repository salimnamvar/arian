"""Python language analyzer using stdlib ast."""

from __future__ import annotations

import ast
from pathlib import Path
import re

from arian.domain.repository.models import Symbol
from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import SymbolKind

_DEF_PATTERN = re.compile(
    r"^(\s*)(async\s+)?(def|class|async\s+def)\s+\w+.*?:\s*(?:#.*)?$",
)
_IMPORT_PATTERN = re.compile(r"^\s*(from\s+\S+\s+import|import\s+)")
_DOCSTRING_START = re.compile(r'^\s*[rRuUbBfF]*("""|\'\'\')')


class PythonAnalyzer:
    """Python-specific code analyzer using stdlib ast.

    Extracts symbols, imports, and public API from Python source code.
    Provides content compression at various levels.
    """

    def extract_symbols(self, a_content: str, a_path: Path) -> list[Symbol]:
        """Extract class, function, and method symbols from Python source.

        Args:
            a_content: Python source code.
            a_path: File path for context.

        Returns:
            List of extracted Symbol objects.
        """
        symbols: list[Symbol] = []
        tree: ast.Module | None = None
        try:
            tree = ast.parse(a_content)
        except SyntaxError:
            tree = None

        if tree is not None:
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    symbols.append(self._make_class_symbol(node, a_path))
                    for item in ast.iter_child_nodes(node):
                        if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                            symbols.append(self._make_method_symbol(item, a_path, node.name))
                elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    symbols.append(self._make_function_symbol(node, a_path))

        return symbols

    def extract_imports(self, a_content: str) -> list[str]:
        """Extract import statements from Python source.

        Args:
            a_content: Python source code.

        Returns:
            List of imported module paths.
        """
        imports: list[str] = []
        for line in a_content.splitlines():
            stripped: str = line.strip()
            if stripped.startswith("import "):
                cleaned: str = (
                    stripped.split(";", maxsplit=1)[0].split("#", maxsplit=1)[0].removeprefix("import ").strip()
                )
                if cleaned:
                    imports.append(cleaned.split(",", maxsplit=1)[0].strip())
            elif stripped.startswith("from "):
                from_part: str = (
                    stripped.split(";", maxsplit=1)[0].split("#", maxsplit=1)[0].removeprefix("from ").strip()
                )
                if " import " in from_part:
                    imports.append(from_part.split(" import ", maxsplit=1)[0].strip())
        return imports

    def extract_public_api(self, a_content: str) -> str:
        """Extract public API surface (classes, functions, their signatures).

        Args:
            a_content: Python source code.

        Returns:
            String representation of the public API.
        """
        symbols: list[Symbol] = self.extract_symbols(a_content, Path("<api>"))
        lines: list[str] = []
        for symbol in symbols:
            if not symbol.name.startswith("_"):
                lines.append(symbol.signature)
                if symbol.docstring:
                    doc_lines: list[str] = symbol.docstring.strip().splitlines()
                    for doc_line in doc_lines[:2]:
                        lines.append(f"    {doc_line.strip()}")
                lines.append("")
        result: str = "\n".join(lines).strip()
        return result

    def compress(self, a_content: str, a_level: CompressionLevel) -> str:
        """Compress Python source according to the compression level.

        Args:
            a_content: Python source code.
            a_level: Desired compression level.

        Returns:
            Compressed content string.
        """
        result: str
        if a_level == CompressionLevel.FULL:
            result = a_content
        elif a_level == CompressionLevel.SIGNATURES:
            result = self._compress_signatures(a_content)
        elif a_level == CompressionLevel.STRUCTURE:
            result = self._compress_structure(a_content)
        elif a_level == CompressionLevel.SUMMARY:
            result = self._compress_summary(a_content)
        else:
            result = a_content
        return result

    def strip_comments(self, a_content: str) -> str:
        """Strip Python comments from source content.

        Args:
            a_content: Python source code.

        Returns:
            Content with comments removed.
        """
        lines: list[str] = a_content.splitlines()
        kept: list[str] = []
        for line in lines:
            stripped: str = line.lstrip()
            if stripped.startswith("#"):
                continue
            if "#" in line and not self._is_inside_string_heuristic(line):
                hash_idx: int = line.find("#")
                code_part: str = line[:hash_idx].rstrip()
                if code_part:
                    kept.append(code_part)
                continue
            kept.append(line)
        result: str = "\n".join(kept)
        return result

    def _compress_signatures(self, a_content: str) -> str:
        """Keep signatures and docstrings, strip implementations.

        Args:
            a_content: Python source code.

        Returns:
            Content with implementations replaced by ellipsis.
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

    def _compress_structure(self, a_content: str) -> str:
        """Keep only class/method/function names and dependencies.

        Args:
            a_content: Python source code.

        Returns:
            Content with only structural elements.
        """
        lines: list[str] = a_content.splitlines()
        result_lines: list[str] = []
        for line in lines:
            stripped: str = line.strip()
            if _DEF_PATTERN.match(stripped) or _IMPORT_PATTERN.match(stripped) or stripped.startswith("class "):
                result_lines.append(line)
        result: str = "\n".join(result_lines)
        return result

    def _compress_summary(self, a_content: str) -> str:
        """Generate a summary of the file's purpose.

        Args:
            a_content: Python source code.

        Returns:
            Summary string with key classes and functions.
        """
        symbols: list[Symbol] = self.extract_symbols(a_content, Path("<summary>"))
        lines: list[str] = ["Python module.", ""]
        classes: list[Symbol] = [s for s in symbols if s.kind == SymbolKind.CLASS]
        functions: list[Symbol] = [s for s in symbols if s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD)]

        if classes:
            lines.append("Classes:")
            for cls in classes:
                lines.append(f"  {cls.name}")
        if functions:
            lines.append("Functions:")
            for func in functions:
                if not func.name.startswith("_"):
                    lines.append(f"  {func.name}()")

        imports: list[str] = self.extract_imports(a_content)
        if imports:
            lines.append("")
            lines.append("Key imports: " + ", ".join(imports[:5]))

        result: str = "\n".join(lines)
        return result

    def _make_class_symbol(self, a_node: ast.ClassDef, a_path: Path) -> Symbol:
        """Create a Symbol from a class AST node.

        Args:
            a_node: Class AST node.
            a_path: File path.

        Returns:
            Symbol representing the class.
        """
        base_names: list[str] = []
        for base in a_node.bases:
            if isinstance(base, ast.Name):
                base_names.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_names.append(f"{ast.dump(base.value)}.{base.attr}")

        sig: str = f"class {a_node.name}"
        if base_names:
            sig += f"({', '.join(base_names)})"
        sig += ":"
        docstring: str = ast.get_docstring(a_node) or ""
        result: Symbol = Symbol(
            name=a_node.name,
            kind=SymbolKind.CLASS,
            file_path=str(a_path),
            signature=sig,
            docstring=docstring,
            line_start=a_node.lineno,
            line_end=a_node.end_lineno or a_node.lineno,
        )
        return result

    def _make_function_symbol(
        self,
        a_node: ast.FunctionDef | ast.AsyncFunctionDef,
        a_path: Path,
    ) -> Symbol:
        """Create a Symbol from a function AST node.

        Args:
            a_node: Function AST node.
            a_path: File path.

        Returns:
            Symbol representing the function.
        """
        prefix: str = "async def" if isinstance(a_node, ast.AsyncFunctionDef) else "def"
        args: list[str] = self._extract_args(a_node.args)
        sig: str = f"{prefix} {a_node.name}({', '.join(args)})"
        return_type: str = self._extract_return_type(a_node)
        if return_type:
            sig += f" -> {return_type}"
        sig += ":"
        docstring: str = ast.get_docstring(a_node) or ""
        result: Symbol = Symbol(
            name=a_node.name,
            kind=SymbolKind.FUNCTION,
            file_path=str(a_path),
            signature=sig,
            docstring=docstring,
            line_start=a_node.lineno,
            line_end=a_node.end_lineno or a_node.lineno,
        )
        return result

    def _make_method_symbol(
        self,
        a_node: ast.FunctionDef | ast.AsyncFunctionDef,
        a_path: Path,
        a_class_name: str,  # noqa: ARG002 — used for future method grouping
    ) -> Symbol:
        """Create a Symbol from a method AST node.

        Args:
            a_node: Method AST node.
            a_path: File path.
            a_class_name: Name of the containing class.

        Returns:
            Symbol representing the method.
        """
        prefix: str = "async def" if isinstance(a_node, ast.AsyncFunctionDef) else "def"
        args: list[str] = self._extract_args(a_node.args)
        sig: str = f"{prefix} {a_node.name}({', '.join(args)})"
        return_type: str = self._extract_return_type(a_node)
        if return_type:
            sig += f" -> {return_type}"
        sig += ":"
        docstring: str = ast.get_docstring(a_node) or ""
        result: Symbol = Symbol(
            name=a_node.name,
            kind=SymbolKind.METHOD,
            file_path=str(a_path),
            signature=sig,
            docstring=docstring,
            line_start=a_node.lineno,
            line_end=a_node.end_lineno or a_node.lineno,
        )
        return result

    def _extract_args(self, a_args: ast.arguments) -> list[str]:
        """Extract argument names from AST arguments node.

        Args:
            a_args: AST arguments node.

        Returns:
            List of argument strings.
        """
        args: list[str] = []
        for arg in a_args.args:
            ann: str = self._extract_annotation(arg.annotation) if arg.annotation else ""
            if ann:
                args.append(f"{arg.arg}: {ann}")
            else:
                args.append(arg.arg)
        if a_args.vararg:
            args.append(f"*{a_args.vararg.arg}")
        for arg in a_args.kwonlyargs:
            ann_k: str = self._extract_annotation(arg.annotation) if arg.annotation else ""
            if ann_k:
                args.append(f"{arg.arg}: {ann_k}")
            else:
                args.append(arg.arg)
        if a_args.kwarg:
            args.append(f"**{a_args.kwarg.arg}")
        return args

    def _extract_return_type(self, a_node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Extract return type annotation from function node.

        Args:
            a_node: Function AST node.

        Returns:
            Return type string or empty string.
        """
        result: str = ""
        if a_node.returns:
            result = self._extract_annotation(a_node.returns)
        return result

    def _extract_annotation(self, a_annotation: ast.expr) -> str:
        """Extract type annotation string from AST expression.

        Args:
            a_annotation: AST expression node.

        Returns:
            Type annotation string.
        """
        result: str = ast.dump(a_annotation)
        if isinstance(a_annotation, ast.Name):
            result = a_annotation.id
        elif isinstance(a_annotation, ast.Attribute):
            result = f"{self._extract_annotation(a_annotation.value)}.{a_annotation.attr}"
        elif isinstance(a_annotation, ast.Subscript):
            base: str = self._extract_annotation(a_annotation.value)
            inner: str = self._extract_annotation(a_annotation.slice)
            result = f"{base}[{inner}]"
        elif isinstance(a_annotation, ast.Tuple):
            elements: list[str] = [self._extract_annotation(e) for e in a_annotation.elts]
            result = ", ".join(elements)
        elif isinstance(a_annotation, ast.Constant):
            result = repr(a_annotation.value)
        return result

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

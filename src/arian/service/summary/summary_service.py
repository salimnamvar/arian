"""Deterministic summary service for file summarization."""

from __future__ import annotations

from arian.domain.repository.models import Symbol
from arian.domain.shared.enums import FileRole
from arian.domain.shared.enums import SymbolKind


class SummaryService:
    """Generates deterministic file summaries from extracted symbols.

    Produces structured summaries without LLM calls. For Python files,
    summaries are built from AST-extracted symbols (classes, functions,
    protocols, constants, decorators, inheritance, exports, public API).

    This service is stateless and deterministic — same inputs always
    produce the same output.
    """

    def generate(
        self,
        a_symbols: list[Symbol],
        a_file_role: FileRole,  # noqa: ARG002 — reserved for future role-specific formatting
        a_imports: tuple[str, ...] = (),
    ) -> str:
        """Generate a deterministic summary from symbols and imports.

        Args:
            a_symbols: Extracted code symbols for the file.
            a_file_role: Role of the file in the repository.
            a_imports: Tuple of import statements.

        Returns:
            Formatted summary string.
        """
        sections: list[str] = []

        if a_imports:
            sections.append(self._format_imports(a_imports))

        classes: list[Symbol] = [s for s in a_symbols if s.kind == SymbolKind.CLASS]
        if classes:
            sections.append(self._format_classes(classes))

        functions: list[Symbol] = [s for s in a_symbols if s.kind == SymbolKind.FUNCTION]
        if functions:
            sections.append(self._format_functions(functions))

        methods: list[Symbol] = [s for s in a_symbols if s.kind == SymbolKind.METHOD]
        if methods:
            sections.append(self._format_methods(methods))

        result: str = "\n\n".join(sections)
        return result

    def _format_imports(self, a_imports: tuple[str, ...]) -> str:
        """Format imports section.

        Args:
            a_imports: Tuple of import statements.

        Returns:
            Formatted imports string.
        """
        lines: list[str] = ["## Imports", ""]
        for imp in a_imports:
            lines.append(f"- `{imp}`")
        return "\n".join(lines)

    def _format_classes(self, a_classes: list[Symbol]) -> str:
        """Format classes section.

        Args:
            a_classes: List of class symbols.

        Returns:
            Formatted classes string.
        """
        lines: list[str] = ["## Classes", ""]
        for cls in a_classes:
            doc: str = f" — {cls.docstring}" if cls.docstring else ""
            lines.append(f"- **{cls.name}**{doc}")
        return "\n".join(lines)

    def _format_functions(self, a_functions: list[Symbol]) -> str:
        """Format functions section.

        Args:
            a_functions: List of function symbols.

        Returns:
            Formatted functions string.
        """
        lines: list[str] = ["## Functions", ""]
        for func in a_functions:
            doc: str = f" — {func.docstring}" if func.docstring else ""
            lines.append(f"- `{func.name}`{doc}")
        return "\n".join(lines)

    def _format_methods(self, a_methods: list[Symbol]) -> str:
        """Format methods section.

        Args:
            a_methods: List of method symbols.

        Returns:
            Formatted methods string.
        """
        lines: list[str] = ["## Methods", ""]
        for method in a_methods:
            doc: str = f" — {method.docstring}" if method.docstring else ""
            lines.append(f"- `{method.name}`{doc}")
        return "\n".join(lines)

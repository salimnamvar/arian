"""Tests for domain shared enums and models."""

from __future__ import annotations

from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import DependencyKind
from arian.domain.shared.enums import FileRole
from arian.domain.shared.enums import SymbolKind
from arian.domain.shared.enums import TokenBudget


def test_file_role_values() -> None:
    """Test FileRole enum values."""
    assert FileRole.README.value == "readme"
    assert FileRole.TEST.value == "test"
    assert FileRole.DOMAIN.value == "domain"


def test_symbol_kind_values() -> None:
    """Test SymbolKind enum values."""
    assert SymbolKind.CLASS.value == "class"
    assert SymbolKind.FUNCTION.value == "function"
    assert SymbolKind.METHOD.value == "method"


def test_dependency_kind_values() -> None:
    """Test DependencyKind enum values."""
    assert DependencyKind.IMPORT.value == "import"
    assert DependencyKind.CALL.value == "call"
    assert DependencyKind.INHERIT.value == "inherit"


def test_compression_level_values() -> None:
    """Test CompressionLevel enum values."""
    assert CompressionLevel.FULL.value == "full"
    assert CompressionLevel.SIGNATURES.value == "signatures"
    assert CompressionLevel.STRUCTURE.value == "structure"
    assert CompressionLevel.SUMMARY.value == "summary"
    assert CompressionLevel.AUTO.value == "auto"


def test_token_budget_defaults() -> None:
    """Test TokenBudget default values."""
    budget = TokenBudget(max_tokens=5000)
    assert budget.max_tokens == 5000
    assert budget.per_chunk_target is None


def test_token_budget_unlimited() -> None:
    """Test TokenBudget unlimited defaults."""
    budget = TokenBudget()
    assert budget.max_tokens is None
    assert budget.per_chunk_target is None


def test_token_budget_custom() -> None:
    """Test TokenBudget custom values."""
    budget = TokenBudget(max_tokens=10000, per_chunk_target=2000)
    assert budget.max_tokens == 10000
    assert budget.per_chunk_target == 2000


def test_token_budget_immutable() -> None:
    """Test TokenBudget is frozen."""
    budget = TokenBudget(max_tokens=5000)
    try:
        budget.max_tokens = 10000  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        msg = "Should not be able to modify frozen dataclass"
        raise AssertionError(msg)

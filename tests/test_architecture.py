"""Architecture tests — enforce Clean Architecture layer boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src" / "arian"

LAYER_MAP = {
    "domain": SRC / "domain",
    "application": SRC / "application",
    "service": SRC / "service",
    "repository": SRC / "repository",
    "infrastructure": SRC / "infrastructure",
    "controller": SRC / "controller",
    "bootstrap": SRC / "bootstrap",
}

FORBIDDEN: dict[str, set[str]] = {
    "domain": {"application", "service", "repository", "infrastructure", "controller", "bootstrap"},
    "infrastructure": {"application", "service", "repository", "controller", "bootstrap"},
    "service": {"application", "infrastructure", "controller", "bootstrap"},
    "repository": {"application", "service", "controller", "bootstrap"},
    "application": {"controller", "bootstrap"},
    "controller": {"service", "repository"},
}


def _get_layer(file_path: Path) -> str | None:
    for layer, layer_path in LAYER_MAP.items():
        try:
            file_path.relative_to(layer_path)
        except ValueError:
            continue
        else:
            return layer
    return None


def _get_imports(file_path: Path) -> list[str]:
    tree = ast.parse(file_path.read_text())
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imports.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
    return imports


def _import_to_layer(module: str) -> str | None:
    for layer in LAYER_MAP:
        if module.startswith(f"arian.{layer}.") or module == f"arian.{layer}":
            return layer
    return None


@pytest.mark.parametrize(("layer", "forbidden"), sorted(FORBIDDEN.items()))
def test_layer_boundaries(layer: str, forbidden: set[str]) -> None:
    layer_path = LAYER_MAP[layer]
    violations: list[str] = []

    for py_file in sorted(layer_path.rglob("*.py")):
        if py_file.name == "__pycache__":
            continue
        for import_module in _get_imports(py_file):
            imported_layer = _import_to_layer(import_module)
            if imported_layer in forbidden:
                rel = py_file.relative_to(SRC)
                violations.append(f"  {rel}: imports {import_module} (layer: {imported_layer})")

    assert not violations, f"Layer '{layer}' has forbidden imports:\n" + "\n".join(violations)


def test_domain_layer_is_pure() -> None:
    domain_path = LAYER_MAP["domain"]
    violations: list[str] = []

    for py_file in sorted(domain_path.rglob("*.py")):
        if py_file.name == "__pycache__":
            continue
        for import_module in _get_imports(py_file):
            if import_module.startswith("arian.") and not import_module.startswith("arian.domain."):
                rel = py_file.relative_to(SRC)
                violations.append(f"  {rel}: imports {import_module}")

    assert not violations, "Domain layer must be pure (no imports from other layers):\n" + "\n".join(violations)


def test_no_circular_layer_imports() -> None:
    dep_graph: dict[str, set[str]] = {layer: set() for layer in LAYER_MAP}

    for layer, layer_path in LAYER_MAP.items():
        for py_file in layer_path.rglob("*.py"):
            if py_file.name == "__pycache__":
                continue
            for import_module in _get_imports(py_file):
                imported_layer = _import_to_layer(import_module)
                if imported_layer and imported_layer != layer:
                    dep_graph[layer].add(imported_layer)

    cycles: list[str] = []
    for layer, deps in dep_graph.items():
        for dep in deps:
            if layer in dep_graph.get(dep, set()):
                cycles.append(f"  {layer} <-> {dep}")

    assert not cycles, "Circular layer dependencies detected:\n" + "\n".join(sorted(cycles))


def test_bootstrap_imports_everything() -> None:
    bootstrap_path = LAYER_MAP["bootstrap"]
    imported_layers: set[str] = set()

    for py_file in sorted(bootstrap_path.rglob("*.py")):
        if py_file.name == "__pycache__":
            continue
        for import_module in _get_imports(py_file):
            imported_layer = _import_to_layer(import_module)
            if imported_layer and imported_layer != "bootstrap":
                imported_layers.add(imported_layer)

    expected_layers = {"domain", "application", "service", "repository", "infrastructure"}
    missing = expected_layers - imported_layers
    assert not missing, f"Bootstrap (composition root) should import from all layers, missing: {missing}"


def test_no_absolute_imports() -> None:
    violations: list[str] = []

    for layer_path in LAYER_MAP.values():
        for py_file in sorted(layer_path.rglob("*.py")):
            if py_file.name == "__pycache__":
                continue
            for import_module in _get_imports(py_file):
                if import_module.startswith(("src.arian", "tests.")):
                    rel = py_file.relative_to(SRC)
                    violations.append(f"  {rel}: absolute project import {import_module}")

    assert not violations, "No absolute project path imports allowed:\n" + "\n".join(violations)

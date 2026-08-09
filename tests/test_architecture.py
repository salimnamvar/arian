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
    # Application may use service (use-case orchestration) and config, but not
    # infrastructure adapters, repository implementations, controller, or bootstrap.
    "application": {"controller", "bootstrap", "infrastructure", "repository"},
    # Controller may reach application + bootstrap composition root only.
    "controller": {"service", "repository", "infrastructure"},
}

# ``arian.infrastructure.config`` is a cross-cutting, data-only module
# (Pydantic models, no behaviour). Per the CSR rule "all constants live
# in the configuration section", every layer is allowed to depend on it,
# and it may depend on ``arian.domain`` enums. It is exempt from the
# boundary and cycle checks below.
CONFIG_MODULE = "arian.infrastructure.config"
UTIL_MODULE = "arian.util"


def _is_exempt_import(module: str) -> bool:
    """Return True if *module* is a shared config or utility module."""
    if module == CONFIG_MODULE or module.startswith(f"{CONFIG_MODULE}."):
        return True
    return module == UTIL_MODULE or module.startswith(f"{UTIL_MODULE}.")


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
            if _is_exempt_import(import_module):
                continue
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
            if _is_exempt_import(import_module):
                continue
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
                if _is_exempt_import(import_module):
                    continue
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


def test_util_has_no_layer_imports() -> None:
    """Verify arian.util imports only stdlib — no Arian layer dependencies.

    Self-referential imports within arian.util are allowed.
    """
    util_path = SRC / "util"
    violations: list[str] = []

    for py_file in sorted(util_path.rglob("*.py")):
        if py_file.name == "__pycache__":
            continue
        for import_module in _get_imports(py_file):
            if import_module.startswith("arian.") and not import_module.startswith("arian.util."):
                rel = py_file.relative_to(SRC)
                violations.append(f"  {rel}: imports {import_module}")

    assert not violations, "arian.util must not import any Arian layer:\n" + "\n".join(violations)


def test_all_layers_have_base_modules() -> None:
    """Verify every architectural layer has a base.py module."""
    missing: list[str] = []
    for layer, layer_path in LAYER_MAP.items():
        base_file = layer_path / "base.py"
        if not base_file.exists():
            missing.append(layer)
    assert not missing, f"Layers missing base.py: {missing}"


def test_no_duplicate_protocol_names() -> None:
    """Verify no two Protocol classes share the same name across the codebase."""
    protocol_names: dict[str, list[str]] = {}

    for py_file in sorted(SRC.rglob("*.py")):
        if py_file.name == "__pycache__":
            continue
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = ""
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = base.attr
                    if base_name == "Protocol":
                        rel = py_file.relative_to(SRC)
                        protocol_names.setdefault(node.name, []).append(str(rel))

    duplicates = {name: files for name, files in protocol_names.items() if len(files) > 1}
    assert not duplicates, "Duplicate protocol names found:\n" + "\n".join(
        f"  {name}: {files}" for name, files in sorted(duplicates.items())
    )


# Classes that are exempt from inheriting Base<Layer>Module.
# These are pure value objects, protocols, enums, exceptions, or framework subclasses.
_EXEMPT_CLASSES: set[str] = {
    # util
    "BaseModule",
    "ModuleMetadata",
    "ModuleState",
    "ExecutionMode",
    "ConcurrencyMode",
    "SyncFunctionProtocol",
    "AsyncFunctionProtocol",
    # domain — value objects, enums, exceptions, protocols
    "BuildRequest",
    "ContextPlan",
    "ContextChunk",
    "PlannedFile",
    "ContextResult",
    "MaterializedEntry",
    "MaterializedChunk",
    "FileFragment",
    "Provenance",
    "Repository",
    "RepositoryFile",
    "FileContent",
    "Module",
    "Symbol",
    "Dependency",
    "CollectionStats",
    "TokenBudget",
    "SafePath",
    "ContentLoadData",
    "FileRole",
    "SymbolKind",
    "DependencyKind",
    "CompressionLevel",
    "ConcurrencyPolicy",
    "ContextTask",
    "Result",
    "ProjectBaseError",
    "ConfigurationError",
    "InputError",
    "InputNotFoundError",
    "InvalidTaskError",
    "ValidationError",
    "ProcessingError",
    "ContextBuilderError",
    "PlanningError",
    "MaterializationError",
    "RenderingError",
    "ClassificationError",
    "AnalysisError",
    "TokenizationError",
    "RepositoryError",
    "CollectionError",
    "RepositoryIndexError",
    "DatabaseConnectionError",
    "SecurityError",
    "PathTraversalError",
    "SymlinkLoopError",
    "BinaryFileError",
    "ResourceError",
    "ResourceNotFoundError",
    "OutOfMemoryError",
    "OperationTimeoutError",
    "CancellationError",
    "ExternalServiceError",
    "GitError",
    "PartialResultError",
    "NoDocumentsError",
    # domain — protocols
    "LanguageAnalyzerProtocol",
    "FileClassifierProtocol",
    "ContextPlannerProtocol",
    "ContextMaterializerProtocol",
    "ContextBuilderProtocol",
    "OutputWriterProtocol",
    "RendererProtocol",
    "PipelineProgressProtocol",
    "SecretProvider",
    # repository — protocols
    "RepositoryIndexProtocol",
    "PathFilterProtocol",
    "FileCollectorProtocol",
    # infrastructure — config value objects
    "ArianConfig",
    "LoggingConfig",
    "FileCollectorConfig",
    "DomainLimitsConfig",
    "LanguageConfig",
    "SecurityConfig",
    "BootstrapConfig",
    "RepositoryConfig",
    "RendererConfig",
    "ControllerConfig",
    "RetryConfig",
    "GitConfig",
    "AnalyzerConfig",
    "ClassifierConfig",
    "MaterializerConfig",
    "PlannerConfig",
    "GitignoreOptions",
    # application — value objects
    "ContextRequest",
    # service — value objects
    "ContextBuilderOptions",
    # infrastructure — Pydantic BaseModel subclasses (config)
    "BaseModel",
    # bootstrap — framework subclasses
    "RunContextFilter",
    "IsoUtcFormatter",
    "ResourceFilter",
    "DiagnosticLevelFilter",
    "LoggingProgressReporter",
    "StartupValidator",
    # stateless adapters (no lifecycle, no resources)
    "EnvironmentSecretProvider",
    "PathFilter",
    "MemoryRepositoryIndex",
    # template — no concrete classes
}

# Base class names that indicate proper adoption
_BASE_NAMES = {
    "BaseDomainModule",
    "BaseApplicationModule",
    "BaseServiceModule",
    "BaseRepositoryModule",
    "BaseInfrastructureModule",
    "BaseControllerModule",
    "BaseBootstrapModule",
    "BaseTemplateModule",
    "BaseModule",
}


def _get_base_names(node: ast.ClassDef) -> list[str]:
    """Extract base class names from a class definition."""
    names: list[str] = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
    return names


def test_all_concrete_classes_adopt_base_or_are_exempt() -> None:
    """Verify every concrete class either inherits a Base<Layer>Module or is exempt.

    This prevents marker-class theater: production classes must either
    adopt the contract or be classified as value objects, protocols,
    enums, exceptions, or framework subclasses.
    """
    violations: list[str] = []

    for py_file in sorted(SRC.rglob("*.py")):
        if py_file.name == "__pycache__":
            continue
        if "/base.py" in str(py_file):
            continue
        try:
            tree = ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            class_name = node.name
            if class_name in _EXEMPT_CLASSES:
                continue
            bases = _get_base_names(node)
            has_base = any(b in _BASE_NAMES for b in bases)
            if not has_base:
                rel = py_file.relative_to(SRC)
                violations.append(f"  {rel}:{node.lineno} class {class_name} (bases: {bases})")

    assert not violations, "Concrete classes missing Base<Layer>Module adoption:\n" + "\n".join(violations)

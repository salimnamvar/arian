# Architecture Refactoring: CSR Bootstrap + Application Layer

> **Status:** Draft
> **Date:** 2026-07-19
> **Branch:** `feature/architecture-refactoring`
> **Reference:** `/home/salim/prj/aidirs/tenas/code/tenas_infrastructure/services/model_management/`

## 1. Problem Statement

The current `controller/cli/app.py` (331 lines) violates CSR by mixing interface parsing, service construction, pipeline orchestration, and output writing into a single function. There is no application layer — the controller directly calls services. The bootstrap layer only configures logging; there is no application factory or lifecycle management.

### Current Violations

| Violation | Location | Impact |
|-----------|----------|--------|
| Controller constructs 7 services inline | `app.py:297-311` | Tight coupling, no testability |
| Controller orchestrates the pipeline | `app.py:314-327` | Business logic in interface layer |
| Controller handles output writing | `_run_merged`, `_run_separate`, `_run_group` | I/O in interface layer |
| No application factory | `app.py:context()` creates everything | No single composition root |
| No lifecycle management | `try/finally` for logging | No structured startup/shutdown |
| No global config singleton | `LoggingConfig()` created inline | No env-driven config |
| CLI mixes 3 output strategies | `_run_merged`, `_run_separate`, `_run_group` | 3 near-identical 40-line functions |

## 2. Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     BOOTSTRAP LAYER                         │
│  application.py ─ create_application() → Application       │
│  lifespan.py    ─ async context manager (startup/shutdown)  │
│  logging.py     ─ configure_logging() (unchanged)          │
└──────────────────────────┬──────────────────────────────────┘
                           │ wires
┌──────────────────────────▼──────────────────────────────────┐
│                  CONTROLLER LAYER                           │
│  cli/app.py ─ Typer command: parse input → call app        │
│  (thin interface: input parsing, output routing only)       │
└──────────────────────────┬──────────────────────────────────┘
                           │ delegates to
┌──────────────────────────▼──────────────────────────────────┐
│                  APPLICATION LAYER (new)                    │
│  application.py ─ Application class: orchestrates use case  │
│  context.py     ─ ContextRequest / ContextResult DTOs       │
│  (single responsibility: context generation use case)       │
└───────┬──────────────────────────────────┬──────────────────┘
        │ calls                            │ calls
┌───────▼──────┐                 ┌──────────▼──────────┐
│ SERVICE LAYER│                 │  REPOSITORY LAYER   │
│ builder/     │                 │  filesystem/collector│
│ planner/     │                 │  index/memory        │
│ classifier/  │                 └─────────────────────┘
│ analyzer/    │
│ materializer/│
│ summary/     │
└──────────────┘
```

### Layer Responsibilities

| Layer | Responsibility | Knows About |
|-------|---------------|-------------|
| **Bootstrap** | Application factory, lifecycle, logging wiring | Application, Config |
| **Controller** | Input parsing (CLI args → DTOs), output display | Application, DTOs |
| **Application** | Use case orchestration, output writing | Services, Repository, DTOs |
| **Service** | Business logic (classify, plan, compress, render) | Domain models |
| **Repository** | Data access (filesystem, index) | Domain models |
| **Domain** | Entities, value objects, enums, protocols | Nothing |

## 3. Detailed Design

### 3.1 Configuration Layer (`infrastructure/config.py`)

**Change:** Add `ArianConfig` root config with `@lru_cache` singleton.

```python
class FileCollectorConfig(BaseModel):
    extensions: frozenset[str] = _DEFAULT_EXTENSIONS
    exclude: frozenset[str] = DEFAULT_EXCLUDES

class ContextBuilderConfig(BaseModel):
    default_output: str = "~/.arian/output/context.md"

class ArianConfig(BaseModel):
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    collector: FileCollectorConfig = Field(default_factory=FileCollectorConfig)
    builder: ContextBuilderConfig = Field(default_factory=ContextBuilderConfig)

    @staticmethod
    @lru_cache(maxsize=1)
    def load() -> "ArianConfig":
        return ArianConfig()
```

**Rationale:** Follows tenas `ServiceConfig.get()` singleton pattern. All config is hierarchical, frozen, and env-driven.

### 3.2 Bootstrap Layer

#### `bootstrap/application.py` (new)

```python
def create_application(a_config: ArianConfig | None = None) -> Application:
    cfg = a_config or ArianConfig.load()
    # Wire repositories
    collector = FileCollector(cfg.collector.extensions, cfg.collector.exclude)
    index = MemoryRepositoryIndex()
    # Wire services
    classifier = FileClassifier()
    analyzer = PythonAnalyzer()
    planner = ContextPlanner(a_classifier=classifier)
    materializer = ContextMaterializer(a_analyzer=analyzer)
    builder = ContextBuilder(collector, index, planner, materializer)
    renderer = MarkdownRenderer()
    return Application(builder, renderer, cfg)
```

**Rationale:** Single composition root. All DI happens here. No service is created outside bootstrap.

#### `bootstrap/lifespan.py` (new)

```python
@asynccontextmanager
async def lifespan(a_config: ArianConfig) -> AsyncGenerator[None]:
    listener = configure_logging(a_config.logging)
    logger.info("Arian starting")
    try:
        yield
    finally:
        logger.info("Arian stopped")
        if listener is not None:
            listener.stop()
```

**Rationale:** Follows tenas lifespan pattern. Even for CLI, this provides structured startup/shutdown. The `configure_logging` call moves out of the controller.

### 3.3 Application Layer (new)

#### `application/application.py`

```python
class Application:
    """Use case orchestrator — builds context from a repository."""

    def __init__(self, a_builder, a_renderer, a_config):
        self._builder = a_builder
        self._renderer = a_renderer
        self._config = a_config

    async def build_context(self, a_request: ContextRequest) -> ContextResult:
        """Execute the full context generation pipeline."""
        t_start = time.monotonic()
        root = Path.cwd()
        input_paths = [root / p for p in a_request.paths] if a_request.paths else [root]
        token_budget = TokenBudget(max_tokens=a_request.budget)

        plan = await self._build_plan(root, a_request.task, token_budget, input_paths)
        content = await self._builder.load_content(plan, root)
        materialized = self._builder.materialize(plan, content)
        rendered = self._renderer.render(materialized, plan)

        output = self._resolve_output(a_request.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")

        return ContextResult(
            output_path=output,
            total_files=plan.total_files,
            total_tokens=plan.total_tokens,
            elapsed_seconds=time.monotonic() - t_start,
        )
```

**Rationale:** The Application owns the use case. The controller only calls `build_context(request)`. The Application handles plan building, content loading, materialization, rendering, and file writing.

#### `application/context.py`

```python
@dataclass(frozen=True)
class ContextRequest:
    task: str = "general"
    budget: int | None = None
    output_path: str = "~/.arian/output/context.md"
    scope: str = "merged"
    paths: tuple[str, ...] = ()
    group: tuple[tuple[str, ...], ...] = ()

@dataclass(frozen=True)
class ContextResult:
    output_path: Path
    total_files: int
    total_tokens: int
    elapsed_seconds: float
```

**Rationale:** DTOs isolate the controller from internal domain models. The controller constructs a `ContextRequest`; the Application returns a `ContextResult`. No domain leakage.

### 3.4 Controller Layer (refactored)

#### `controller/cli/app.py` (slimmed down)

```python
@app.command()
def context(task, query, output, budget, scope, group, verbose, paths):
    """Generate task-aware context from a repository."""
    config = ArianConfig.load()
    with lifespan(config):
        app_instance = create_application(config)
        request = ContextRequest(
            task=task,
            budget=_parse_budget(budget),
            output_path=output,
            scope=scope,
            group=_parse_groups(group),
            paths=tuple(paths) if paths else (),
        )
        result = asyncio.run(app_instance.build_context(request))
        logger.info(
            "Context generated: %d files, %d tokens in %.2fs",
            result.total_files,
            result.total_tokens,
            result.elapsed_seconds,
        )
        logger.info("Output: %s", result.output_path)
```

**Rationale:** The controller becomes thin: parse CLI args → construct request → call application → display result. No service construction, no pipeline logic, no output writing.

### 3.5 Eliminated Code

| Removed | Replacement | Lines Saved |
|---------|-------------|-------------|
| `_run_separate()` | `Application.build_context()` handles scope internally | ~35 |
| `_run_merged()` | Same | ~40 |
| `_run_group()` | Same | ~35 |
| Service construction in `context()` | `create_application()` | ~15 |
| `configure_logging()` in `context()` | `lifespan()` context manager | ~3 |
| Inline output path writing | `Application._write_output()` | ~5 |

**Total estimated reduction:** ~130 lines from `app.py` (331 → ~200).

### 3.6 Output Strategy Consolidation

The three output strategies (`_run_merged`, `_run_separate`, `_run_group`) differ only in:
1. How `input_paths` are determined
2. How the output filename is computed
3. Whether multiple plans are built

These are consolidated into `Application.build_context()` with a single `_resolve_plan()` method:

```python
async def _resolve_plan(self, root, task, budget, request):
    if request.scope == "separate":
        return await self._build_separate(root, task, budget, request)
    if request.group:
        return await self._build_grouped(root, task, budget, request)
    return await self._build_merged(root, task, budget, request)
```

## 4. Files Changed

| File | Action | Description |
|------|--------|-------------|
| `bootstrap/application.py` | **Create** | Application factory |
| `bootstrap/lifespan.py` | **Create** | Lifecycle context manager |
| `application/__init__.py` | **Create** | Package init |
| `application/application.py` | **Create** | Application class |
| `application/context.py` | **Create** | ContextRequest/ContextResult DTOs |
| `infrastructure/config.py` | **Modify** | Add `ArianConfig` root config |
| `controller/cli/app.py` | **Modify** | Slim to interface-only (remove ~130 lines) |
| `domain/context/models.py` | **Modify** | Add `scope` field to `ContextResult` |
| `tests/controller/test_cli.py` | **Modify** | Update for new architecture |
| `tests/application/` | **Create** | Application layer tests |

## 5. Migration Steps

1. Create `application/` package with `ContextRequest`, `ContextResult`, and `Application`
2. Add `ArianConfig` to `infrastructure/config.py`
3. Create `bootstrap/application.py` (factory) and `bootstrap/lifespan.py` (lifecycle)
4. Refactor `controller/cli/app.py` to use `Application` (thin controller)
5. Consolidate `_run_merged`, `_run_separate`, `_run_group` into `Application`
6. Update tests
7. Run full test suite + pre-commit hooks

## 6. Design Principles Applied

| Principle | Application |
|-----------|------------|
| **CSR** | Controller parses, Application orchestrates, Repository stores |
| **SRP** | Each layer has exactly one responsibility |
| **DIP** | Application depends on protocols, not concrete implementations |
| **OCP** | New output strategies added to Application, not Controller |
| **DRY** | Three output functions consolidated into one pipeline |
| **KISS** | Controller is now ~70 lines (was ~330) |
| **SPR** | Configuration, lifecycle, and business logic are separated |

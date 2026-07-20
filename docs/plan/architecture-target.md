# Arian — Target Architecture Plan

> **Status:** Vision document — incremental implementation roadmap
> **Date:** 2026-07-19
> **Principles:** CSR, Clean Architecture, DRY, OOP, KISS, SPR, SOLID

---

## 1. Design Philosophy

Arian follows **Clean Architecture** with **CSR layering** (Controller → Service → Repository).
Every layer has a single responsibility. Dependencies point inward only.

```
Domain ← Repository ← Service ← Application ← Controller
   ↑                                                ↓
   └──────────── Bootstrap (wires everything) ──────┘
```

### Core Rules

| Rule | Enforcement |
|------|------------|
| **Domain has zero external deps** | Only stdlib. No pydantic, no typer, no jinja2 |
| **Dependencies point inward** | Controller → Application → Service → Repository → Domain |
| **Each layer owns its models** | Domain entities, Application DTOs, Controller schemas |
| **Protocols over concrete types** | All service boundaries use `Protocol` |
| **Single composition root** | All DI in `bootstrap/application.py` |
| **No mutable globals** | All state in frozen dataclasses or injected instances |
| **Single return per function** | Enforced by pre-commit hook |
| **`a_` prefix on all args** | Convention across the entire codebase |

---

## 2. Layer Architecture

### 2.1 Domain Layer (`domain/`)

> **Owns:** Entities, value objects, enums, protocols, exceptions.
> **Knows about:** Nothing (stdlib only).
> **Modified:** Rarely — only when business rules change.

```
domain/
├── context/
│   ├── models.py          # ContextPlan, ContextChunk, PlannedFile, ContextTask
│   └── exceptions.py      # ContextValidationError, ContextPlanError
├── repository/
│   ├── models.py          # RepositoryFile, FileContent, Symbol, Module, Dependency
│   └── exceptions.py      # FileAccessError, DuplicateFileError
├── shared/
│   ├── enums.py           # FileRole, CompressionLevel, SymbolKind, TokenBudget
│   └── value_objects.py   # FilePath (validated), TokenCount (bounded)
├── exceptions.py          # ProjectBaseError → DomainError → RepositoryError → ServiceError
└── protocols.py           # LanguageAnalyzerProtocol, FileClassifierProtocol
```

#### Target Exception Hierarchy

```
ProjectBaseError (domain/exceptions.py)
├── DomainError
│   ├── InvalidTaskError
│   ├── InvalidBudgetError
│   └── ContextValidationError
├── RepositoryError
│   ├── FileAccessError
│   ├── DirectoryReadError
│   └── DuplicateFileError
├── ServiceError
│   ├── PlanningError
│   ├── MaterializationError
│   └── RenderError
└── ApplicationError
    ├── OutputPathError
    └── PipelineError
```

Each exception carries: `reason` (machine code), `message` (human), `resource_type`, `resource_name`, `details`.

#### Target Value Objects

```python
# domain/shared/value_objects.py
@dataclass(frozen=True)
class FilePath:
    """Validated relative file path — must not escape root."""
    value: str

    def __post_init__(self) -> None:
        if ".." in self.value or self.value.startswith("/"):
            raise DomainError("Path must be relative and must not escape root")

@dataclass(frozen=True)
class TokenCount:
    """Bounded token count — always >= 0."""
    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise DomainError("Token count must be >= 0")
```

### 2.2 Repository Layer (`repository/`)

> **Owns:** Data access — filesystem scanning, index storage, content loading.
> **Knows about:** Domain models only.
> **Modified:** When storage mechanism changes (memory → sqlite → git).

```
repository/
├── filesystem/
│   ├── collector.py       # FileCollector — recursive scanner with gitignore
│   └── reader.py          # FileContentReader — async content loading + hashing
├── index/
│   ├── protocols.py       # RepositoryIndexProtocol
│   ├── memory_repository.py   # In-memory (testing)
│   └── sqlite_repository.py   # Persistent (production)
```

#### Target Collector Responsibilities

The collector should be split into two concerns:
1. **Scanning** — walk directories, respect gitignore, produce `RepositoryFile` metadata
2. **Reading** — load file content, compute hashes, produce `FileContent`

Currently both live in `collector.py`. Target: split `reader.py` out.

#### Target Index Protocol

```python
class RepositoryIndexProtocol(Protocol):
    async def save_file(self, a_file: RepositoryFile) -> None: ...
    async def get_file(self, a_path: str) -> RepositoryFile | None: ...
    async def list_files(self) -> list[RepositoryFile]: ...
    async def save_symbol(self, a_symbol: Symbol) -> None: ...
    async def find_symbols(self, a_path: str) -> list[Symbol]: ...
    async def save_module(self, a_module: Module) -> None: ...
```

### 2.3 Service Layer (`service/`)

> **Owns:** Business logic — classification, planning, analysis, materialization, rendering.
> **Knows about:** Domain models, Repository protocols.
> **Modified:** When business rules change.

```
service/
├── analyzer/
│   ├── protocols.py       # LanguageAnalyzerProtocol (already in domain)
│   └── python_analyzer.py # Python-specific AST analysis
├── classifier/
│   └── file_classifier.py # Role detection from path patterns
├── planner/
│   └── context_planner.py # Task-aware file selection + compression
├── materializer/
│   └── context_materializer.py  # Apply compression, track provenance
├── builder/
│   └── context_builder.py # Orchestrator: collect → plan → materialize
├── renderer/
│   └── markdown_renderer.py  # Jinja2 template rendering
└── summary/
    └── summary_service.py # Deterministic file summaries
```

#### Target Service Responsibilities

| Service | Responsibility | Input → Output |
|---------|---------------|----------------|
| `FileClassifier` | Detect role, importance, compression from path | `str` → `(FileRole, int, CompressionLevel)` |
| `ContextPlanner` | Select files by task, fragment large files, chunk by budget | `list[RepositoryFile], ContextTask, TokenBudget` → `ContextPlan` |
| `PythonAnalyzer` | Extract symbols, compress content via AST | `str, CompressionLevel` → `str` |
| `ContextMaterializer` | Apply compression decisions to actual content | `ContextPlan, dict[str, FileContent]` → `tuple[MaterializedChunk]` |
| `MarkdownRenderer` | Render Markdown from materialized chunks | `tuple[MaterializedChunk], ContextPlan` → `str` |
| `SummaryService` | Generate deterministic file summaries | `list[Symbol], FileRole` → `str` |

#### Target ContextBuilder (Orchestrator)

The `ContextBuilder` should be a pure orchestrator — no business logic, only delegation:

```python
class ContextBuilder:
    """Pipeline orchestrator: collect → index → plan → materialize."""

    async def build(self, ...) -> ContextPlan:
        files = await self._collector.collect(...)
        for f in files:
            await self._index.save_file(f)
        return self._planner.plan(files, task, budget)

    async def load_content(self, plan, root) -> dict[str, FileContent]:
        ...

    def materialize(self, plan, content) -> tuple[MaterializedChunk]:
        return self._materializer.materialize(plan, content)
```

### 2.4 Application Layer (`application/`)

> **Owns:** Use case orchestration — the single "build context" use case.
> **Knows about:** Service layer, Domain DTOs.
> **Modified:** When the use case workflow changes.

```
application/
├── __init__.py           # Re-exports Application, ContextRequest, ContextResult
├── application.py        # Application class — use case orchestrator
└── context.py            # ContextRequest (input DTO), ContextResult (output DTO)
```

#### Target Application Responsibilities

1. Parse `ContextRequest` → resolve paths → validate inputs
2. Delegate to `ContextBuilder` for pipeline execution
3. Delegate to `MarkdownRenderer` for output generation
4. Write output file
5. Return `ContextResult` with statistics

```python
class Application:
    async def build_context(self, a_request: ContextRequest) -> ContextResult:
        root = Path.cwd()
        task = ContextTask(a_request.task)
        budget = TokenBudget(max_tokens=a_request.budget)
        paths = self._resolve_paths(root, a_request.paths)

        plan = await self._builder.build(root, task, budget, paths)
        content = await self._builder.load_content(plan, root)
        materialized = self._builder.materialize(plan, content)
        rendered = self._renderer.render(materialized, plan)

        output = self._write_output(a_request.output_path, rendered)
        return ContextResult(output, plan.total_files, plan.total_tokens, elapsed)
```

#### Target DTOs

```python
@dataclass(frozen=True)
class ContextRequest:
    task: str = "general"
    budget: int | None = None
    output_path: str = "~/.arian/output/context.md"
    scope: str = "merged"
    paths: tuple[str, ...] = ()
    group: tuple[tuple[str, ...], ...] = ()
    query: str | None = None

@dataclass(frozen=True)
class ContextResult:
    output_path: Path
    total_files: int
    total_tokens: int
    elapsed_seconds: float
```

### 2.5 Controller Layer (`controller/`)

> **Owns:** Interface concerns — input parsing, output display, error presentation.
> **Knows about:** Application layer only.
> **Modified:** When the interface changes (CLI args, output format).

```
controller/
├── __init__.py
└── cli/
    ├── __init__.py       # Re-exports Typer app
    ├── app.py            # Typer command: parse → validate → call Application → display
    ├── parser.py         # Input parsing helpers (budget, groups, paths)
    └── schema.py         # CLI-specific types if needed
```

#### Target Controller Responsibilities

1. **Parse** CLI args into a `ContextRequest`
2. **Validate** task name, scope, path existence
3. **Call** `Application.build_context(request)`
4. **Display** result (log output path, stats)
5. **Handle** errors (catch exceptions → log + exit code)

The controller should be **under 100 lines**. Currently 157 — target is to extract `_parse_budget` and `_parse_groups` into `parser.py`.

### 2.6 Bootstrap Layer (`bootstrap/`)

> **Owns:** Composition root — application factory, lifecycle, logging.
> **Knows about:** All layers (it wires them).
> **Modified:** When the DI graph changes.

```
bootstrap/
├── __init__.py           # Re-exports create_application, lifespan, configure_logging
├── application.py        # create_application() — single composition root
├── lifespan.py           # Sync + async lifespan context managers
└── logging.py            # configure_logging() — stdlib dictConfig wiring
```

#### Target Factory

```python
def create_application(a_config: ArianConfig | None = None) -> Application:
    cfg = a_config or ArianConfig.load()

    classifier = FileClassifier()
    collector = FileCollector(cfg.collector.extensions, cfg.collector.exclude, classifier)
    index = MemoryRepositoryIndex()
    analyzer = PythonAnalyzer()
    planner = ContextPlanner(a_classifier=classifier)
    materializer = ContextMaterializer(a_analyzer=analyzer)
    builder = ContextBuilder(collector, index, planner, materializer)
    renderer = MarkdownRenderer()

    return Application(builder, renderer)
```

### 2.7 Infrastructure Layer (`infrastructure/`)

> **Owns:** Cross-cutting utilities — config, language detection, tokenization, git, sqlite.
> **Knows about:** Domain models (minimal).
> **Modified:** When infrastructure tools change.

```
infrastructure/
├── config.py             # ArianConfig, LoggingConfig, FileCollectorConfig
├── language.py           # detect_language() — extension-to-language mapping
├── output_path_resolver.py  # resolve_output_path() — expanduser + CWD
├── gitignore_filter.py   # PathFilter — .gitignore + exclusion patterns
├── tokenizer/
│   └── tokenizer.py      # count_tokens() — tiktoken wrapper
├── git/
│   └── analyzer.py       # GitAnalyzer — branch name, changed files
├── sqlite/
│   └── connection.py     # SQLite connection management
└── ignore/
    └── default_patterns.py  # DEFAULT_EXCLUDES — standard directory exclusions
```

---

## 3. Data Flow

### 3.1 Request Lifecycle

```
User runs:  arian src/ --task bug_fix --budget 5000

1. controller/cli/app.py
   ├─ Parses CLI args
   ├─ Constructs ContextRequest DTO
   ├─ Validates (task, scope, paths exist)
   └─ Calls Application.build_context(request)

2. application/application.py
   ├─ Resolves paths relative to CWD
   ├─ Creates ContextTask enum + TokenBudget
   └─ Delegates to Application pipeline

3. application/pipeline
   ├─ ContextBuilder.build()        → ContextPlan
   │   ├─ FileCollector.collect()   → list[RepositoryFile]
   │   ├─ Index.save_file()         → stored
   │   └─ ContextPlanner.plan()     → ContextPlan (chunks + compression)
   ├─ ContextBuilder.load_content() → dict[str, FileContent]
   ├─ ContextBuilder.materialize()  → tuple[MaterializedChunk]
   └─ MarkdownRenderer.render()     → str (Markdown)

4. application/application.py
   ├─ Writes output file
   └─ Returns ContextResult

5. controller/cli/app.py
   └─ Logs result + output path
```

### 3.2 Compression Pipeline

```
RepositoryFile (metadata only, no content)
  ↓
ContextPlanner (decides compression per file)
  ↓
PlannedFile (path + role + importance + compression + token estimate)
  ↓
ContextPlan (chunks of PlannedFiles)
  ↓
ContextMaterializer (applies compression to actual content)
  ↓
MaterializedChunk (compressed content + provenance)
  ↓
MarkdownRenderer (Jinja2 template → final Markdown)
```

### 3.3 Compression Levels

| Level | When Applied | Content Kept |
|-------|-------------|--------------|
| `FULL` | Small high-priority files | Complete content |
| `SIGNATURES` | Medium files | Class/function signatures + docstrings |
| `STRUCTURE` | Large files (>5000 tokens) | File outline (class/function names only) |
| `SUMMARY` | Very large files | Brief summary from SummaryService |

---

## 4. Configuration Architecture

### 4.1 Config Hierarchy

```python
ArianConfig (root, @lru_cache singleton)
├── logging: LoggingConfig
│   ├── level: str = "INFO"
│   ├── async_logging: bool = False
│   ├── log_dir: Path | None = "~/.arian/logs"
│   ├── max_bytes: int = 10MB
│   └── backup_count: int = 5
└── collector: FileCollectorConfig
    ├── extensions: frozenset[str] = {".py", ".md", ...}
    └── exclude: frozenset[str] = {".git", ".venv", ...}
```

### 4.2 Config Loading Flow

```
ArianConfig.load()
  → @lru_cache (singleton, called once)
  → ArianConfig() with defaults
  → CLI overrides via LoggingConfig(level="DEBUG")
  → Passed to create_application(config)
  → Passed to lifespan(config)
```

### 4.3 Environment Variables (Future)

```
ARIAN_LOGGING__LEVEL=DEBUG
ARIAN_COLLECTOR__EXCLUDE=.git,.venv
ARIAN_BUILDER__DEFAULT_OUTPUT=/tmp/context.md
```

---

## 5. Testing Architecture

### 5.1 Test Pyramid

```
         ╱╲
        ╱  ╲        Integration tests (15%)
       ╱    ╲       - test_cli.py (end-to-end subprocess)
      ╱──────╲      - test_context_builder.py
     ╱        ╲     - test_bug_fix_workflow.py
    ╱  Unit    ╲    Unit tests (85%)
   ╱   tests    ╲   - test_file_classifier.py
  ╱              ╲  - test_context_planner.py
 ╱────────────────╲ - test_python_analyzer.py
                   - test_materializer.py
                   - test_application.py
                   - test_config.py
```

### 5.2 Test Conventions

| Convention | Rule |
|------------|------|
| File naming | `test_<module>.py` matches `src/arian/<module>.py` |
| Class naming | `Test<ClassName>` (no `Test` prefix on the module) |
| Method naming | `test_<behavior>` — descriptive, no `test_1` or `test_basic` |
| Fixtures | `tmp_path` for filesystem, no shared mutable state |
| Assertions | One concept per assertion, descriptive messages |
| Integration tests | Marked with `@pytest.mark.integration` |
| Async tests | Use `asyncio.run()` in sync test methods |

### 5.3 Test Coverage Targets

| Layer | Target | Current |
|-------|--------|---------|
| Domain | 100% | ~95% |
| Service | 95% | ~90% |
| Application | 90% | 0% (new) |
| Controller | 80% | ~70% |
| Bootstrap | 80% | 0% (new) |

---

## 6. Error Handling Architecture

### 6.1 Layer-Bounded Exceptions

Each layer has its own exception branch. Exceptions never cross layer boundaries upward — they are caught and re-raised as the current layer's exception type.

```
Domain exceptions    → raised by domain logic
Repository exceptions → raised by data access (caught by Service)
Service exceptions   → raised by business logic (caught by Application)
Application exceptions → raised by use case (caught by Controller)
Controller exceptions → caught, logged, exit code
```

### 6.2 Error Presentation

```python
# Controller catches all exceptions and presents them cleanly
try:
    result = asyncio.run(application.build_context(request))
except DomainError as e:
    logger.error("Invalid request: %s", e.message)
    raise typer.Exit(code=1) from None
except RepositoryError as e:
    logger.error("File access error: %s", e.message)
    raise typer.Exit(code=1) from None
except ServiceError as e:
    logger.error("Processing error: %s", e.message)
    raise typer.Exit(code=1) from None
except Exception:
    logger.exception("Unexpected error")
    raise typer.Exit(code=1) from None
```

### 6.3 Error Codes (Reason Strings)

```python
# Domain
"INVALID_TASK"
"INVALID_BUDGET"
"CONTEXT_VALIDATION_FAILED"

# Repository
"FILE_ACCESS_ERROR"
"DIRECTORY_READ_ERROR"
"DUPLICATE_FILE"
"STAT_ERROR"

# Service
"PLANNING_ERROR"
"MATERIALIZATION_ERROR"
"RENDER_ERROR"
"COMPRESSION_FAILED"

# Application
"OUTPUT_PATH_ERROR"
"PIPELINE_ERROR"
"PATH_NOT_FOUND"
```

---

## 7. File Structure Target

```
src/arian/
├── __init__.py                  # Package init (re-exports app)
├── __main__.py                  # python -m arian entry
├── main.py                      # main() → app()
├── py.typed                     # PEP 561 marker
│
├── bootstrap/                   # COMPOSITION ROOT
│   ├── __init__.py
│   ├── application.py           # create_application() factory
│   ├── lifespan.py              # sync + async lifespan
│   └── logging.py               # configure_logging()
│
├── application/                 # USE CASE LAYER
│   ├── __init__.py
│   ├── application.py           # Application class
│   └── context.py               # ContextRequest, ContextResult DTOs
│
├── controller/                  # INTERFACE LAYER
│   ├── __init__.py
│   └── cli/
│       ├── __init__.py
│       ├── app.py               # Typer command (thin)
│       ├── parser.py            # Input parsing helpers
│       └── schema.py            # CLI-specific types
│
├── domain/                      # BUSINESS RULES (zero deps)
│   ├── __init__.py
│   ├── exceptions.py            # Full exception hierarchy
│   ├── protocols.py             # Structural typing protocols
│   ├── context/
│   │   ├── __init__.py
│   │   ├── models.py            # ContextPlan, ContextChunk, etc.
│   │   └── exceptions.py        # Context-specific errors
│   ├── repository/
│   │   ├── __init__.py
│   │   ├── models.py            # RepositoryFile, FileContent, Symbol
│   │   └── exceptions.py        # Repository-specific errors
│   └── shared/
│       ├── __init__.py
│       ├── enums.py             # FileRole, CompressionLevel, etc.
│       └── value_objects.py     # FilePath, TokenCount (validated)
│
├── infrastructure/              # CROSS-CUTTING UTILITIES
│   ├── __init__.py
│   ├── config.py                # ArianConfig, LoggingConfig, etc.
│   ├── language.py              # detect_language()
│   ├── output_path_resolver.py  # resolve_output_path()
│   ├── gitignore_filter.py      # PathFilter
│   ├── tokenizer/
│   │   ├── __init__.py
│   │   └── tokenizer.py         # count_tokens()
│   ├── git/
│   │   ├── __init__.py
│   │   └── analyzer.py          # GitAnalyzer
│   ├── sqlite/
│   │   ├── __init__.py
│   │   └── connection.py        # SQLite connection
│   └── ignore/
│       ├── __init__.py
│       └── default_patterns.py  # DEFAULT_EXCLUDES
│
├── repository/                  # DATA ACCESS
│   ├── __init__.py
│   ├── filesystem/
│   │   ├── __init__.py
│   │   ├── collector.py         # FileCollector (scanning)
│   │   └── reader.py            # FileContentReader (loading) [FUTURE]
│   └── index/
│       ├── __init__.py
│       ├── protocols.py         # RepositoryIndexProtocol
│       ├── memory_repository.py # In-memory (testing)
│       └── sqlite_repository.py # Persistent (production)
│
├── service/                     # BUSINESS LOGIC
│   ├── __init__.py
│   ├── analyzer/
│   │   ├── __init__.py
│   │   └── python_analyzer.py   # Python AST analysis
│   ├── classifier/
│   │   ├── __init__.py
│   │   └── file_classifier.py   # Role detection
│   ├── planner/
│   │   ├── __init__.py
│   │   └── context_planner.py   # File selection + chunking
│   ├── materializer/
│   │   ├── __init__.py
│   │   └── context_materializer.py  # Compression application
│   ├── renderer/
│   │   ├── __init__.py
│   │   └── markdown_renderer.py # Jinja2 rendering
│   └── summary/
│       ├── __init__.py
│       └── summary_service.py   # File summaries
│
└── template/                    # JINJA2 TEMPLATES
    ├── __init__.py
    └── document.md.jinja2
```

---

## 8. Implementation Roadmap

### Phase 1: Current State ✅

- [x] Bootstrap: `logging.py`, `application.py`, `lifespan.py`
- [x] Application: `Application` class, `ContextRequest`, `ContextResult`
- [x] Controller: thin CLI (157 lines)
- [x] Config: `ArianConfig` with `@lru_cache` singleton
- [x] 152 tests passing
- [x] Pre-commit hooks: ruff, pyright, pylint, custom checks

### Phase 2: Refine Current Architecture

- [ ] Extract `_parse_budget`, `_parse_groups` to `controller/cli/parser.py`
- [ ] Add `ArianConfig` env-var support (`ARIAN_*` prefix)
- [ ] Enrich exception hierarchy with `DomainError`, `RepositoryError`, `ServiceError` branches
- [ ] Add `value_objects.py` — `FilePath`, `TokenCount` validated types
- [ ] Split `FileCollector` scanning from content loading → `reader.py`
- [ ] Move `MarkdownRenderer` from `renderer/` to `service/renderer/`
- [ ] Add Application-layer tests with mocked services
- [ ] Add bootstrap integration tests

### Phase 3: Production Hardening

- [ ] SQLite index as default (replace memory index)
- [ ] Git integration: `GitAnalyzer` for branch-aware context
- [ ] Progress reporting: callback protocol for long operations
- [ ] Config file support: `~/.arian/config.toml`
- [ ] Output formats: JSON, YAML (not just Markdown)
- [ ] Parallel file collection: `asyncio.gather` for large repos

### Phase 4: Advanced Features

- [ ] MCP server: expose context generation as a tool
- [ ] LLM integration: auto-summarize using external API
- [ ] Caching: skip unchanged files (hash-based)
- [ ] Incremental: only regenerate changed files
- [ ] Multi-repo: cross-repository context

---

## 9. Design Patterns Reference

| Pattern | Where Applied |
|---------|--------------|
| **Factory** | `create_application()` in bootstrap |
| **Singleton** | `ArianConfig.load()` via `@lru_cache` |
| **Strategy** | `CompressionLevel` selection per file role |
| **Pipeline** | collect → plan → materialize → render |
| **DTO** | `ContextRequest`, `ContextResult` |
| **Protocol** | `LanguageAnalyzerProtocol`, `FileClassifierProtocol`, `RepositoryIndexProtocol` |
| **Context Manager** | `lifespan()` for startup/shutdown |
| **Template Method** | `ContextBuilder.build()` orchestrates fixed pipeline |
| **Value Object** | `FilePath`, `TokenCount`, `TokenBudget` |
| **Repository** | `MemoryRepositoryIndex`, `SQLiteRepositoryIndex` |

---

## 10. Conventions Checklist

- [ ] All args prefixed with `a_`
- [ ] Single return per function
- [ ] No mutable globals
- [ ] No in-function imports
- [ ] Google style docstrings
- [ ] Frozen dataclasses for domain models
- [ ] `noqa: TRY400` for intentional `logger.error` in except blocks
- [ ] Conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`)
- [ ] GitFlow: feature → PR → develop → release → main → tag
- [ ] Pre-commit: ruff, pyright, pylint, custom hooks

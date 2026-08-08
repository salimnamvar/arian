# Arian Feature Proposal: Code Graph & Dependency-Aware Context Generation

**Date:** 2026-07-28  
**Status:** Proposal  
**Author:** Salim Namvar  

---

## 1. Problem Statement

Current Arian generates context by collecting files, classifying them by role, and applying task-aware compression. But it lacks **structural awareness** of how code relates to each other:

- When a developer asks for context about `src/payments/processor.py`, Arian returns that file and similar-role files — but not its **callers**, **callees**, or **import dependencies**.
- There is no concept of **blast radius**: changing this module affects what else?
- There is no **persistent graph** per repository. Every run re-analyzes from scratch.
- Competitors (Sigmap, TLDR, CodeGraph, LLM-Context-Manager) already offer call graphs, dependency tracking, and knowledge graphs.

## 2. Proposed Solution

Treat each repository as a **directed graph** of code entities (files, classes, functions). Enable **task-aware graph traversal** to generate context that is structurally complete — not just a bag of relevant files.

### Core Capability

Given a target module/file, Arian can generate context at multiple scopes:

| Scope | What gets included |
|-------|-------------------|
| `MODULE` | The target module only |
| `DEPENDENCIES` | Direct import dependencies |
| `CALLEES` | Modules/functions called by the target |
| `CALLERS` | Modules/functions that call the target |
| `WHOLE_REPO` | Full repo + all transitive relationships |

This is **unique** — no competitor combines graph traversal with task-aware context generation.

## 3. Competitive Analysis

| Competitor | Graph Feature | Depth | Task-Aware | Persistent |
|---|---|---|---|---|
| **Sigmap** | Blast radius, `get_impact`, `get_method_impact`, callee signatures | Tree-sitter (33 langs) | ❌ | ❌ |
| **TLDR** (archived) | 5-layer: call graph, data flow, program dependence | Tree-sitter + AST | ❌ | ❌ |
| **CodeGraph** | Semantic graph: functions, classes, imports, call chains (42 MCP tools) | 38 langs | ❌ | ❌ |
| **LLM-Context-Manager** | Knowledge graph navigation, blast radius, call chain tracing | Tree-sitter (8 langs) | ❌ | ❌ |
| **Octocode** | LSP semantics, AST patterns, local + GitHub search | Multi-lang | ❌ | ❌ |
| **Code Review Graph** | Persistent code intelligence graph for MCP/CLI | Local-first | ❌ | ✅ |
| **MegaMemory** | Persistent project knowledge graph, semantic search | In-process embeddings | ❌ | ✅ |
| **Arian (proposed)** | Task-aware graph traversal, Python-AST-deep, SQLite-backed | Python first, then tree-sitter | ✅ | ✅ |

### Gap Arian Can Fill

No competitor combines:
1. **Task-aware** file selection/compression (Arian's existing differentiator)
2. **Graph-aware** context generation (callers, callees, dependencies, blast radius)
3. **Persistent per-repo graph** stored in SQLite
4. **Partial/whole context** from the same graph model

## 4. Proposed Architecture

### Layer Placement (Clean Architecture)

```
src/arian/
+-- domain/
|   +-- graph/
|       +-- models.py          # RepositoryGraph, GraphNode, GraphEdge, SymbolBinding, GraphScope
|       +-- protocols.py       # GraphBuilderProtocol, GraphQueryProtocol, GraphPersistenceProtocol
|       +-- traversal.py       # TaskAwareTraversal — turns graph queries into ContextPlan
|       +-- exceptions.py      # GraphError, CyclicDependencyError, UnresolvedSymbolError
+-- service/
|   +-- graph/
|       +-- python_graph_builder.py   # AST-based call graph + import resolution
|       +-- context_graph.py          # Partial/whole graph generation per module
|       +-- graph_indexer.py          # Index graph into Repository (SQLite)
+-- infrastructure/
    +-- graph/
        +-- sqlite_graph_repository.py  # Persistent graph storage in SQLite
```

### Dependency Rules

| Layer | May Import From |
|-------|----------------|
| `domain/graph/` | `domain/` only (stdlib + existing domain models) |
| `service/graph/` | `domain/graph/`, `service/` (classifier, analyzer, planner) |
| `infrastructure/graph/` | `domain/graph/` (implements protocols) |

No layer imports from `controller/` or `infrastructure/` non-graph modules.

## 5. Domain Models

### GraphNode

```python
@dataclass(frozen=True)
class GraphNode:
    node_id: str              # file_path or qualified_symbol_id (e.g. "src/payments/processor.py::Processor.process")
    kind: NodeKind            # FILE, CLASS, FUNCTION, METHOD
    file_path: str            # Owning file
    line_start: int
    line_end: int
    symbols: tuple[Symbol, ...] = ()
    metadata: dict[str, str | int] = field(default_factory=dict)
```

### GraphEdge

```python
@dataclass(frozen=True)
class GraphEdge:
    source: str               # Caller / importer
    target: str               # Callee / imported module
    kind: DependencyKind      # CALL, IMPORT, INHERIT
    line: int = 0
    confidence: float = 1.0   # 1.0 = certain, <1.0 = heuristic (for non-Python langs)
```

### RepositoryGraph

```python
@dataclass(frozen=True)
class RepositoryGraph:
    repo_path: str
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    modules: tuple[Module, ...]      # Reuse existing Module model
    generated_at: str
    language: str = "python"
```

### GraphScope (Enum)

```python
class GraphScope(Enum):
    MODULE = "module"            # Target module only
    DEPENDENCIES = "dependencies" # Direct imports
    CALLEES = "callees"          # What the target calls
    CALLERS = "callers"          # What calls the target
    WHOLE_REPO = "whole_repo"    # Full repo + all transitive relationships
```

### NodeKind (Enum)

```python
class NodeKind(Enum):
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
```

## 6. Service Layer

### PythonGraphBuilder

Responsible for extracting the graph from Python source using stdlib `ast`:

```python
class PythonGraphBuilder:
    def build(self, repo_files: list[RepositoryFile], symbols: dict[str, list[Symbol]]) -> RepositoryGraph:
        """
        Returns RepositoryGraph with:
        - One FILE node per repository file
        - CLASS/METHOD/FUNCTION nodes per symbol
        - IMPORT edges from import statements
        - CALL edges from function/method call analysis
        - INHERIT edges from class bases
        """
```

**Extraction strategy:**
1. **FILE → FILE edges**: Parse `import` / `from X import Y` statements → `IMPORT` edges
2. **CLASS → CLASS edges**: Parse `class Foo(Bar)` → `INHERIT` edges  
3. **FUNCTION/METHOD → FUNCTION/METHOD edges**: Walk function bodies for `ast.Call` nodes → `CALL` edges
4. **FILE → SYMBOL edges**: Each symbol gets a `CONTAINS` edge from its file node

**Call graph limitations (honest):**
- Python AST can resolve direct calls within the same file.
- Cross-file call resolution requires import resolution + symbol matching.
- Dynamic dispatch (`self.method()`, `getattr()`, decorators) is best-effort.
- This is still deeper than tree-sitter-only competitors for Python.

### ContextGraph

Responsible for turning graph queries into `ContextPlan`:

```python
class ContextGraph:
    def __init__(self, graph: RepositoryGraph, planner: ContextPlanner):
        self._graph = graph
        self._planner = planner

    def generate(
        self,
        target: str,                    # file path or symbol id
        scope: GraphScope,
        task: ContextTask,
        budget: TokenBudget,
    ) -> ContextPlan:
        """
        1. Resolve target to node(s)
        2. Traverse graph based on scope:
           - MODULE: neighbors at distance 0 (same file)
           - DEPENDENCIES: outgoing IMPORT edges
           - CALLEES: outgoing CALL edges (transitive)
           - CALLERS: incoming CALL edges (transitive)
           - WHOLE_REPO: all nodes, ranked by distance from target
        3. Convert selected nodes to PlannedFile list
        4. Delegate to ContextPlanner for chunking/budget enforcement
        """
```

### GraphIndexer

Responsible for persisting the graph in SQLite:

```python
class GraphIndexer:
    def __init__(self, repo_path: str, connection: sqlite3.Connection):
        self._repo_path = repo_path
        self._connection = connection

    def index(self, graph: RepositoryGraph) -> None:
        """Upsert nodes and edges into SQLite."""

    def load(self, repo_path: str) -> RepositoryGraph | None:
        """Load cached graph from SQLite if it exists and is fresh."""

    def is_stale(self, repo_path: str, current_hash: str) -> bool:
        """Check if cached graph is outdated based on repo hash."""
```

## 7. Infrastructure

### SQLiteGraphRepository

Implements `GraphPersistenceProtocol`:

```python
class SQLiteGraphRepository:
    def __init__(self, db_path: Path):
        self._db_path = db_path

    def save(self, graph: RepositoryGraph) -> None:
        """Atomic write: temp file + rename."""

    def load(self, repo_path: str) -> RepositoryGraph | None:
        """Load graph by repo_path."""

    def invalidate(self, repo_path: str) -> None:
        """Remove cached graph (e.g., after file changes)."""
```

**Schema:**

```sql
CREATE TABLE repo_graphs (
    repo_path TEXT PRIMARY KEY,
    language TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    graph_json TEXT NOT NULL
);

CREATE TABLE graph_nodes (
    node_id TEXT PRIMARY KEY,
    repo_path TEXT NOT NULL,
    kind TEXT NOT NULL,
    file_path TEXT NOT NULL,
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    metadata TEXT
);

CREATE TABLE graph_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_path TEXT NOT NULL,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    kind TEXT NOT NULL,
    line INTEGER DEFAULT 0,
    confidence REAL DEFAULT 1.0
);

CREATE INDEX idx_edges_source ON graph_edges(repo_path, source);
CREATE INDEX idx_edges_target ON graph_edges(repo_path, target);
```

## 8. Integration with Existing Pipeline

The graph feature plugs into the existing `ContextBuilder` pipeline as an **optional stage**:

```
Pipeline:
  Collect → [Build Graph] → Index → Plan → Materialize → Render
                           ↑
                    optional stage
                    enabled when:
                    - user passes --graph
                    - task benefits from graph (bug_fix, review, refactor)
                    - SQLite cache exists
```

### CLI Integration

```bash
# Existing:
arian src/ --task bug_fix

# New:
arian src/payments/processor.py --task bug_fix --graph callers
arian src/ --task refactor --graph whole_repo
arian src/ --task review --graph dependencies
```

### MCP Tool Integration (Phase 2)

```typescript
// Tool: get_module_context
{
  "name": "get_module_context",
  "description": "Get context for a module with graph-aware scope",
  "inputSchema": {
    "type": "object",
    "properties": {
      "modulePath": {"type": "string"},
      "scope": {"type": "string", "enum": ["module", "dependencies", "callees", "callers", "whole_repo"]},
      "task": {"type": "string", "enum": ["bug_fix", "feature", "review", "refactor", "general"]},
      "budget": {"type": "number", "default": 32000}
    }
  }
}

// Tool: get_blast_radius
{
  "name": "get_blast_radius",
  "description": "Get all modules affected by changes to target",
  "inputSchema": {
    "type": "object",
    "properties": {
      "modulePath": {"type": "string"},
      "maxDepth": {"type": "number", "default": 3}
    }
  }
}
```

## 9. Example Scenarios

### Scenario 1: Bug Fix Context

**Input:**
```bash
arian src/payments/processor.py --task bug_fix --graph callers
```

**Output Context Plan:**
```
1. src/payments/processor.py (FULL)          ← target
2. src/payments/__init__.py (SIGNATURES)     ← module entry
3. src/payments/exceptions.py (SIGNATURES)   ← dependency
4. src/api/endpoints.py (SIGNATURES)          ← caller (imports processor)
5. src/cli/commands.py (SIGNATURES)           ← caller (calls process())
6. tests/payments/test_processor.py (FULL)    ← critical for bug_fix
```

### Scenario 2: Refactor Blast Radius

**Input:**
```bash
arian src/payments/ --task refactor --graph whole_repo
```

**Output:** All files ranked by graph distance from `src/payments/`. Files with no incoming edges (unused) are deprioritized. Circular dependencies are flagged.

### Scenario 3: Onboarding to a Module

**Input:**
```bash
arian src/auth/ --task onboarding --graph dependencies
```

**Output:** The `auth` module + its direct dependencies, giving a new developer the mental model of what the module touches.

## 10. Implementation Phases

### Phase 1: Graph Extraction (30 days)

| Task | Effort | Priority |
|------|--------|----------|
| `domain/graph/models.py` — all models + enums | 2 days | CRITICAL |
| `service/graph/python_graph_builder.py` — AST extraction (imports, calls, inheritance) | 5 days | CRITICAL |
| `infrastructure/graph/sqlite_graph_repository.py` — persistence | 3 days | CRITICAL |
| `service/graph/graph_indexer.py` — upsert/load/invalidate | 2 days | CRITICAL |
| Tests: graph builder, SQLite repo, integration | 3 days | CRITICAL |

**Deliverable:** Arian can build and persist a Python call/import graph per repo.

### Phase 2: Graph-Aware Context (90 days)

| Task | Effort | Priority |
|------|--------|----------|
| `domain/graph/traversal.py` — `TaskAwareTraversal` | 4 days | CRITICAL |
| `service/graph/context_graph.py` — scope-based context generation | 4 days | CRITICAL |
| CLI integration: `--graph` flag + scope selection | 2 days | HIGH |
| MCP tools: `get_module_context`, `get_blast_radius` | 3 days | HIGH |
| Tests: traversal, context generation, MCP tools | 3 days | HIGH |

**Deliverable:** `arian --graph callers src/payments/processor.py --task bug_fix` works end-to-end.

### Phase 3: Multi-Language Graph (180 days)

| Task | Effort | Priority |
|------|--------|----------|
| Tree-sitter graph builders (TypeScript, Go, Rust) | 8 days | MEDIUM |
| Language-agnostic graph query layer | 3 days | MEDIUM |
| Graph visualization / export (JSON, DOT) | 2 days | LOW |

**Deliverable:** Graph support beyond Python.

## 11. Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Graph lives in domain layer** | Graph is a core business concept, not an implementation detail. Competitors who bolted graphs on as an afterthought have messy architectures. |
| **SQLite for persistence** | Arian already uses SQLite for repository indexing. Reusing the same pattern avoids new dependencies. |
| **AST-first for Python, tree-sitter later** | Arian's Python AST is already deeper than tree-sitter for Python. Adding tree-sitter later for other languages matches the existing roadmap. |
| **Graph is optional pipeline stage** | Not every run needs graph analysis. Keep it opt-in to avoid performance regression for existing users. |
| **Scope enum instead of free-form queries** | Prevents misuse, keeps the API simple, and makes MCP tool schemas clean. |
| **Confidence score on edges** | For non-Python languages or heuristic analysis, edges can be marked uncertain. This supports future multi-language expansion. |

## 12. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Python call graph is incomplete (dynamic dispatch, decorators) | High | Medium | Document limitations. Best-effort for dynamic patterns. Focus on static calls which are the majority. |
| Graph build is slow for large repos | Medium | Medium | Cache in SQLite. Incremental updates (only rebuild changed files). Parallel file processing. |
| Graph adds complexity to existing pipeline | Medium | High | Keep it an optional stage. No changes to existing non-graph flow. |
| Circular dependencies confuse ranking | Low | Low | Detect and flag. Deprioritize in ranking. |
| Memory usage for large graphs | Medium | Medium | Streaming builder. Never load all files into memory simultaneously. |

## 13. Success Metrics

| Metric | Target |
|--------|--------|
| Graph build time (medium repo, <500 files) | <5 seconds |
| Graph build time (large repo, 500+ files) | <30 seconds |
| Cache hit rate (repeated runs on same repo) | >90% |
| Call graph completeness (static calls) | >85% of direct calls resolved |
| Context quality improvement (task-aware vs non-graph) | >20% better relevance score |

## 14. Relationship to Existing Arian Features

| Existing Feature | Graph Feature Relationship |
|------------------|---------------------------|
| `PythonAnalyzer` | Feeds symbol data into `PythonGraphBuilder` |
| `ContextPlanner` | Consumes graph-ranked files via `ContextGraph` |
| `FileClassifier` | Graph edges supplement role-based classification |
| `RepositoryIndex` (SQLite) | Graph stored alongside existing index, same connection |
| `Dependency` / `DependencyKind` enums | Reused directly in graph edges |
| `Symbol` model | Used as graph node payloads |

## 15. Open Questions

1. **Incremental graph updates**: Should Arian track file-level hashes and only rebuild changed portions? Or rebuild the whole graph each time?
2. **Cross-language edges**: When Arian adds TypeScript support, how should cross-language edges (e.g., Python calling a TS API via HTTP) be represented?
3. **Graph freshness policy**: How long is a cached graph valid? Should Arian invalidate on `git pull`, file mtime change, or config change?
4. **MCP tool surface**: Should `get_module_context` be a single tool with a `scope` parameter, or separate tools for each scope?

---

*This proposal complements the existing competitor analysis and implementation roadmap in `.tmp/COMPETITOR/`.*

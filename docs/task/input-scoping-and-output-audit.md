# Task: Input Scoping System + Output Audit

**Date:** 2026-07-19
**Status:** DESIGN — ready for coder implementation
**Priority:** HIGH — blocks real-world usage

---

## Part 1: Output Audit

Audited file: `/home/salim/prj/salim/selma/.tmp/context.md`

### Issue 1: Directory Structure Broken

**Current output:**
```
              extensions.json
              launch.json
              settings.json
              tasks.json
            README.md
                README.md
```

**Problem:** No hierarchy visible. Files appear flat with random indentation. The `_build_directory_structure()` method in `renderer.py` uses `Path.parts` depth but doesn't connect parent directories to children.

**Expected:**
```
selma/
├── .vscode/
│   ├── extensions.json
│   └── settings.json
├── README.md
├── docs/
│   └── README.md
└── src/
    └── selma/
        └── __init__.py
```

**Root cause:** `_build_directory_structure()` only renders files, not directories. Missing directory nodes in the tree.

### Issue 2: Absolute Paths in File Headers

**Current output:**
```
─── /home/salim/prj/salim/selma/README.md (FULL) ───
```

**Problem:** Absolute paths leak host-specific information into context. LLM doesn't need `/home/salim/prj/salim/selma/` prefix.

**Expected:**
```
─── README.md (FULL) ───
```

**Root cause:** `PlannedFile.path` stores absolute path from `FileCollector`. Should store relative path from repository root.

### Issue 3: Token Budget Not Enforced (CRITICAL)

**Current output:** 72193 tokens even with `--max-tokens 1000`.

**Problem:** `TokenBudget.max_tokens` is accepted but **never enforced anywhere in the pipeline**. Only `per_chunk_target` is used for per-chunk bin-packing. Total budget is completely ignored.

**Verified:**
```bash
arian --max-tokens 1000
# → Planned 153 files in 19 chunks (72193 tokens)   ← 72x over budget
```

**Root cause:** `ContextPlanner._plan_chunks()` only checks `per_chunk_target`. No code path reads `max_tokens`.

**Fix required:**
1. `_plan_chunks()` must stop adding files when total exceeds `max_tokens`
2. Files beyond budget should be dropped with warning
3. Manifest should show `budget: {max: N, per_chunk: N}`
4. Output should never exceed `max_tokens`

### Issue 4: No Input Scoping

**Current:** Always scans entire CWD. No way to limit scope.

**Problem:** User cannot:
- Generate context for only `src/` directory
- Generate context for multiple specific directories
- Aggregate contexts from separate directories
- Nest directories with different treatment

### Issue 5: Manifest Missing Repository Name

**Current manifest:**
```yaml
task: general
files: 153
chunks: 19
tokens: 72193
```

**Expected:**
```yaml
repository: selma
task: general
files: 153
chunks: 19
tokens: 72193
```

### Issue 6: Continuation Hints Not Appearing

**Implementation exists** (`continues_in_chunk` on `MaterializedEntry`) but never populated. The `ContextMaterializer` doesn't track cross-chunk fragment relationships.

### Issue 7: Summary Section Minimal

**Current:**
```
## Summary
Files: 153
Tokens: 72193
```

**Expected:**
```
## Summary
Files: 153
Tokens: 72193
Chunks: 19
Task: general
Query: —
Budget: 5000 tokens
```

---

## Part 2: Input Scoping Design

### User Stories

| ID | Story | Priority |
|----|-------|----------|
| US-01 | User runs `arian` in repo root → scans entire repo | P0 |
| US-02 | User runs `arian src/` → scans only `src/` directory | P0 |
| US-03 | User runs `arian src/ lib/` → scans both directories, merged context | P0 |
| US-04 | User runs `arian "src/,lib/"` → same as US-03 (comma-separated) | P1 |
| US-05 | User runs `arian src/ --scope单独` → each directory gets separate context file | P1 |
| US-06 | User runs `arian (src/,lib/)` → `src/` and `lib/` treated as one logical unit | P2 |
| US-07 | User runs `arian src/ --max-tokens 10000` → scoped + budget | P0 |

### CLI Design

```
arian [OPTIONS] [PATHS...]

Arguments:
  PATHS    Directories or files to include (default: current directory)

Options:
  --task          Task type (default: general)
  --query, -q     Query for relevance matching
  --output, -o    Output path (default: .tmp)
  --max-tokens    Maximum tokens (default: 5000)
  --per-chunk     Target tokens per chunk (default: 4000)
  --scope         Scope mode: merged (default) | separate
  --verbose, -v   Debug logging
```

### Scope Modes

#### Mode 1: Merged (default)

```bash
arian src/ lib/
```

Behavior:
- Collect files from `src/` and `lib/`
- Treat as single repository
- Single context.md output
- Paths relative to CWD

Output structure:
```
# Arian Context Manifest
repository: merged
paths: [src/, lib/]
task: general
...

# Repository Structure
src/
  ├── __init__.py
  └── service.py
lib/
  ├── __init__.py
  └── utils.py

─── src/service.py (FULL) ───
...
─── lib/utils.py (SIGNATURES) ───
...
```

#### Mode 2: Separate

```bash
arian src/ lib/ --scope separate
```

Behavior:
- Collect files from `src/` and `lib/`
- Generate separate context for each
- Output: `src/context.md`, `lib/context.md`

Output structure:
```
.src/context.md
.lib/context.md
```

Each file has its own manifest with `paths: [src/]` or `paths: [lib/]`.

#### Mode 3: Grouped (future)

```bash
arian (src/,lib/) core/
```

Behavior:
- `src/` and `lib/` treated as one group → one context
- `core/` treated as separate group → one context
- Parentheses define grouping

### Path Resolution Rules

1. **Relative paths** → resolved from CWD
2. **Absolute paths** → used as-is
3. **Glob patterns** → expanded (future)
4. **Missing paths** → error with message
5. **Files mixed with directories** → files included, directories scanned

### Internal Model Changes

#### New: `InputSpec`

```python
@dataclass(frozen=True)
class InputSpec:
    """Specification for a single input path."""

    path: str              # relative or absolute path
    is_group: bool = False # True if part of a parenthesized group
    group_id: str | None = None  # group identifier for grouped mode
```

#### Updated: `ContextBuilder.build()`

```python
async def build(
    self,
    a_inputs: list[InputSpec],  # changed from a_path: Path
    a_task: ContextTask,
    a_budget: TokenBudget,
    a_query: str | None = None,
    a_scope: str = "merged",  # "merged" or "separate"
) -> list[ContextPlan]:  # changed from ContextPlan
```

#### Updated: `FileCollector.collect()`

```python
async def collect(
    self,
    a_paths: list[Path],  # changed from a_path: Path
) -> list[RepositoryFile]:
```

### Manifest Updates

```yaml
# Arian Context Manifest
repository: selma
paths:                          # NEW — input paths
  - src/
  - lib/
task: general
query: null
budget:
  max: 5000
  per_chunk: 4000
files: 153
chunks: 19
tokens: 72193
scope: merged                   # NEW — scope mode
```

### File Path Handling

All internal paths stored as **relative to CWD** (or relative to input root for scoped runs).

```python
# Bad (current)
path = "/home/salim/prj/salim/selma/src/auth.py"

# Good (proposed)
path = "src/auth.py"
```

The `FileCollector` should strip the input root prefix from paths.

### Token Budget Enforcement

```python
# In ContextPlanner._plan_chunks()
if current_tokens + file.tokens > a_budget.per_chunk_target and current_files:
    # start new chunk

# NEW: enforce total budget
if total_tokens + file.tokens > a_budget.max_tokens:
    logger.warning("Token budget exceeded: %d > %d", total_tokens, a_budget.max_tokens)
    break  # stop adding files
```

### Continuation Hints

The `ContextMaterializer` needs to track which chunks contain fragments of the same file:

```python
# After materializing all chunks
fragment_locations: dict[str, list[int]] = {}  # file_path → [chunk_indices]
for i, chunk in enumerate(materialized_chunks):
    for entry in chunk.entries:
        if entry.is_fragment:
            fragment_locations.setdefault(entry.path, []).append(i)

# Set continues_in_chunk
for i, chunk in enumerate(materialized_chunks):
    entries = list(chunk.entries)
    for j, entry in enumerate(entries):
        if entry.is_fragment and entry.path in fragment_locations:
            chunks_with_fragments = fragment_locations[entry.path]
            current_pos = chunks_with_fragments.index(i)
            if current_pos < len(chunks_with_fragments) - 1:
                entries[j] = replace(entry, continues_in_chunk=chunks_with_fragments[current_pos + 1])
    materialized_chunks[i] = replace(chunk, entries=tuple(entries))
```

---

## Implementation Order

| Phase | Task | Depends on |
|-------|------|------------|
| 1 | Fix directory tree rendering | — |
| 2 | Fix relative paths (strip input root) | — |
| 3 | Add `--input` positional argument | — |
| 4 | Add `--scope` option (merged/separate) | Phase 3 |
| 5 | Enforce `max_tokens` budget | — |
| 6 | Populate continuation hints | — |
| 7 | Update manifest with repository, paths, scope | Phase 3 |
| 8 | Add `InputSpec` domain model | Phase 3 |
| 9 | Update `ContextBuilder` for multi-path | Phase 8 |
| 10 | Tests for all new behavior | All phases |

---

## Acceptance Criteria

- [ ] `arian src/` generates context for only `src/` directory
- [ ] `arian src/ lib/` generates merged context from both
- [ ] `arian src/ lib/ --scope separate` generates separate files
- [ ] All paths in output are relative (no absolute paths)
- [ ] Directory tree shows proper hierarchy with directories and files
- [ ] Token budget is enforced (total ≤ max_tokens)
- [ ] Continuation hints appear for cross-chunk fragments
- [ ] Manifest includes repository name, paths, scope, budget
- [ ] 120+ tests pass
- [ ] Lint clean

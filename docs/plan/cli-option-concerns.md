# Arian CLI — Option Concern Analysis

**Date:** 2026-07-19
**Status:** DRAFT — awaiting review

---

## 1. The Pipeline

Arian processes input through a pipeline. Each option controls a specific stage:

```
INPUT → FILTER → STRATEGY → BUDGET → STRUCTURE → OUTPUT
  │        │         │          │         │          │
  │        │         │          │         │          └─ --output
  │        │         │          │         └─ --scope, --group
  │        │         │          └─ --budget
  │        │         └─ --task, --query
  │        └─ --extensions, --exclude
  └─ paths
```

---

## 2. Option Definitions — Single Responsibility

### `paths` — INPUT SELECTION

**Job:** Which files and directories to scan.

**Scope:** The starting point. Determines what enters the pipeline.

**Current behavior:**
- `arian` → scan CWD
- `arian docs/` → scan `docs/` directory
- `arian README.md` → scan single file (BROKEN — silently dropped)
- `arian src/ tests/` → scan multiple paths

**Concern boundary:** Ends at collection. Once files are collected, `paths` has no further effect.

**Bug:** Individual files silently dropped (`collector.py:79`).

---

### `--extensions` — INPUT FILTERING

**Job:** Which file types to include.

**Scope:** Filters during collection. Applied to each file's extension.

**Current behavior:** Hardcoded to `{".py", ".md", ".txt", ".rst", ".toml", ".yaml", ".yml", ".json"}`.

**Proposed:** `--extensions py,md,yaml` — user adds to defaults.

**Concern boundary:** Applied during `FileCollector.collect()`. Once files are filtered, this has no further effect.

**Interaction with `paths`:** Independent. `paths` selects directories, `--extensions` filters file types within those directories.

---

### `--exclude` — INPUT FILTERING

**Job:** Which directories to skip.

**Scope:** Filters during collection. Applied to directory traversal.

**Current behavior:** Hardcoded to 12 patterns (`.git`, `.venv`, `__pycache__`, etc.).

**Proposed:** `--exclude vendor,third_party` — user adds to defaults.

**Concern boundary:** Applied during `FileCollector._collect_directory()`. Once directories are excluded, this has no further effect.

**Interaction with `paths`:** Independent. `paths` selects starting directories, `--exclude` skips subdirectories within them.

---

### `--task` — CONTENT STRATEGY

**Job:** How to prioritize and compress files based on what the user is doing.

**Scope:** Affects two things:
1. **Importance scoring** — which files matter more for this task
2. **Compression decisions** — how much detail to include per file

**Current behavior:**
- `bug_fix` → boosts tests, services, domain files
- `feature` → boosts domain, services, tests
- `review` → boosts services, domain
- `onboarding` → boosts README, config, pyproject.toml
- `refactor` → boosts services, infrastructure
- `document` → boosts README, domain, services
- `general` → no boost (all equal)

**Concern boundary:** Applied during `ContextPlanner._plan_files()`. Affects importance scores and compression levels. Does NOT filter files (all files still considered).

**Interaction with `--query`:** Both affect content selection, but differently:
- `--task` adjusts importance/compression for ALL files (global strategy)
- `--query` should filter by relevance (selective inclusion)

**Interaction with `--budget`:** `--task` determines which files are prioritized when budget is limited. Higher importance = included first.

---

### `--query` / `-q` — CONTENT FILTERING

**Job:** Filter files by relevance to a natural language query.

**Scope:** Selective inclusion. Only files matching the query should be included.

**Current behavior:** DEAD — value flows through pipeline but is explicitly ignored at `context_planner.py:125`.

**Proposed behavior:** When set, files are scored by relevance to the query. Only files above a relevance threshold are included. This is a separate concern from `--task`:
- `--task` = "I'm doing a bug fix, so prioritize tests"
- `--query` = "I'm fixing the auth module, so only include auth-related files"

**Concern boundary:** Applied during planning. Should filter or re-rank files based on query text.

**Interaction with `--task`:** Complementary. `--task` sets global strategy, `--query` narrows scope. Both affect which files are included, but at different levels.

**Interaction with `--budget`:** `--query` reduces the file set before budget is applied. Fewer files = less budget pressure.

---

### `--budget` — SIZE CONSTRAINT

**Job:** Limit total tokens in the output.

**Scope:** Caps the output size. When set, files are included by importance until budget is exhausted.

**Current behavior:** `--max-tokens 5000` — default too low, silently drops files.

**Proposed behavior:** `--budget 10000` or `--budget none` (unlimited, the default).

**Concern boundary:** Applied during `ContextPlanner._plan_chunks()`. Files beyond budget are dropped with a clear warning.

**Interaction with `--task`:** `--task` determines priority order. `--budget` determines cutoff point.

**Interaction with `--query`:** `--query` reduces file set before budget applied.

**Interaction with `--scope`/`--group`:** `--budget` applies per-output-file in separate/group modes. Each output file gets its own budget.

**Why remove `--per-chunk`:** Chunk size is an internal implementation detail. The planner decides chunk boundaries based on file sizes and semantic boundaries. Users care about total output size, not chunk size.

---

### `--scope` — OUTPUT STRUCTURE

**Job:** How to organize the output files.

**Scope:** Controls the mapping from input paths to output files.

**Current behavior:**
- `merged` → one output file for all paths (default)
- `separate` → one output file per input path

**Concern boundary:** Determines which `_run_*` function is called. Does NOT affect content selection or planning.

**Interaction with `--group`:** `--group` overrides `--scope`. When `--group` is present, `--scope` is ignored (should warn).

**Interaction with `--budget`:** In `separate` mode, each output file gets the full budget. In `merged` mode, the budget is shared.

---

### `--group` — OUTPUT STRUCTURE (CUSTOM)

**Job:** Custom grouping of paths into output files.

**Scope:** User defines which paths go together.

**Current behavior:** `--group src/,lib/ --group docs/` → two output files: `src__lib_context.md` and `docs_context.md`.

**Concern boundary:** Same level as `--scope`. Determines output file organization.

**Interaction with `--scope`:** `--group` is a more granular version of `--scope separate`. When both are present, `--group` wins.

**Interaction with `--budget`:** Each group gets its own budget allocation.

---

### `--output` / `-o` — OUTPUT DESTINATION

**Job:** Where to write the output file(s).

**Scope:** Filesystem path for output.

**Current behavior:** Default `.tmp` → `{cwd}/.tmp/context.md`. In separate/group modes, only the parent directory is used.

**Proposed behavior:** Default `~/.arian/output/context.md`.

**Concern boundary:** Pure I/O. Does not affect content, planning, or structure.

**Interaction with `--scope`/`--group`:** In merged mode, exact path is used. In separate/group modes, parent directory is used as output directory.

---

### `--verbose` / `-v` — VISIBILITY

**Job:** Show debug information during execution.

**Scope:** Logging output only. Does not affect generated context.

**Current behavior:** Switches logger from INFO to DEBUG.

**Concern boundary:** Pure logging. Zero effect on output content.

**Interaction with other options:** None. Purely orthogonal.

---

## 3. Concern Overlaps — Current Problems

### Problem 1: `--scope` and `--group` overlap

Both control output structure. `--group` is just a more granular `--scope separate`.

**Current behavior:** `--group` silently overrides `--scope`. No warning.

**Fix:** When both are present, log warning. Consider making them mutually exclusive.

---

### Problem 2: `--task` affects two things

`--task` controls both importance scoring AND compression decisions. These are separate concerns:
- Importance = "which files matter" (selection)
- Compression = "how much detail" (representation)

**Current behavior:** Both adjusted by same `--task` value.

**Fix:** Acceptable as-is. The task type legitimately affects both. A bug fix needs tests at full compression, while onboarding needs README at full compression. The coupling is intentional.

---

### Problem 3: `--budget` interacts with everything

`--budget` limits total output. But it also implicitly affects:
- Which files are included (budget cutoff)
- How files are compressed (larger budget = less compression needed)
- How chunks are split (budget determines chunk boundaries)

**Current behavior:** Budget applied after all other decisions. Files silently dropped.

**Fix:** With unlimited default, budget only applies when user explicitly sets it. Clear warning when files are excluded.

---

### Problem 4: `--query` is dead

`--query` should filter by relevance but does nothing. Users who pass it get false expectations.

**Fix:** Mark as reserved. Implement in separate feature.

---

## 4. Clean Separation — Proposed Design

### Layer 1: Input (what to scan)

| Option | Job | Boundary |
|--------|-----|----------|
| `paths` | Starting directories/files | Collection |
| `--extensions` | File type filter | Collection |
| `--exclude` | Directory skip filter | Collection |

### Layer 2: Strategy (how to prioritize)

| Option | Job | Boundary |
|--------|-----|----------|
| `--task` | Importance + compression strategy | Planning |
| `--query` | Relevance filter (reserved) | Planning |

### Layer 3: Constraint (how much to include)

| Option | Job | Boundary |
|--------|-----|----------|
| `--budget` | Total token limit | Planning |

### Layer 4: Structure (how to organize output)

| Option | Job | Boundary |
|--------|-----|----------|
| `--scope` | Merged vs separate | Output |
| `--group` | Custom path grouping | Output |

### Layer 5: Destination (where to write)

| Option | Job | Boundary |
|--------|-----|----------|
| `--output` | Output file/directory path | I/O |

### Layer 6: Visibility (what to show)

| Option | Job | Boundary |
|--------|-----|----------|
| `--verbose` | Debug logging | Logging |

---

## 5. Interaction Matrix

| | `paths` | `--extensions` | `--exclude` | `--task` | `--query` | `--budget` | `--scope` | `--group` | `--output` | `--verbose` |
|---|---|---|---|---|---|---|---|---|---|---|
| `paths` | — | Independent | Independent | Independent | Independent | Independent | Independent | Independent | Independent | Independent |
| `--extensions` | | — | Independent | Independent | Independent | Independent | Independent | Independent | Independent | Independent |
| `--exclude` | | | — | Independent | Independent | Independent | Independent | Independent | Independent | Independent |
| `--task` | | | | — | Complementary | Priority order | Independent | Independent | Independent | Independent |
| `--query` | | | | | — | Reduces set | Independent | Independent | Independent | Independent |
| `--budget` | | | | | | — | Per-file in separate | Per-file in group | Independent | Independent |
| `--scope` | | | | | | | — | Overrides | Parent dir used | Independent |
| `--group` | | | | | | | | — | Parent dir used | Independent |
| `--output` | | | | | | | | | — | Independent |
| `--verbose` | | | | | | | | | | — |

---

## 6. Option Jobs — Summary

| Option | One-line job | Layer |
|--------|-------------|-------|
| `paths` | "Scan these directories/files" | Input |
| `--extensions` | "Only include these file types" | Input |
| `--exclude` | "Skip these directories" | Input |
| `--task` | "I'm doing X, so prioritize accordingly" | Strategy |
| `--query` | "Only include files relevant to this" | Strategy |
| `--budget` | "Don't exceed this many tokens" | Constraint |
| `--scope` | "One file for everything, or one per path" | Structure |
| `--group` | "Group these paths into one output file" | Structure |
| `--output` | "Write output here" | Destination |
| `--verbose` | "Show me what's happening" | Visibility |

---

## 7. What Needs to Change

### Remove
- `--per-chunk` — internal concern, not user knob
- `--async-logging` — internal design principle
- `--install-completion` / `--show-completion` — Typer auto-generated

### Rename
- `--max-tokens` → `--budget` — clearer, simpler

### Add
- `--extensions` — configurable file types
- `--exclude` — configurable directory exclusions

### Fix defaults
- `--budget` → `None` (unlimited) — no more silent file dropping
- `--output` → `~/.arian/output/context.md` — centralized
- Logging → `~/.arian/logs/` — centralized

### Fix bugs
- `paths` — handle individual files
- `--scope separate` — fix hidden file
- `--scope` + `--group` — warn on conflict
- `--query` — mark as reserved
- Separate mode — add manifest metadata

# Fix CLI Arguments — Design & Implementation Plan

**Date:** 2026-07-19
**Status:** DRAFT — awaiting review
**Branch:** `feature/fix-cli-arguments`
**Priority:** HIGH (user-facing bugs)

---

## 1. Problem Statement

Arian is an LLM input provider. Its API must work reliably, not be mocked. When running `arian docs/` on a 35-file documentation directory, arian produced output with only **5 of 35 files** — 30 files silently dropped due to a hardcoded 5000-token default budget. The manifest shows `collected: 35, files: 5` with no user-facing warning.

### Evidence of failure

```
$ arian docs/
WARNING: Token budget exceeded: 4206 + 1063 > 5000. Stopping.
INFO: Planned 5 files in 2 chunks (4206 tokens) from 35 collected
INFO: Context generated: 5 files, 4206 tokens, 2 chunks
```

Output: 5 files (1 markdown + 4 YAML schemas). 30 files silently excluded.

### Root causes

1. `--max-tokens` defaults to 5000 — too low for any real repository
2. `--per-chunk` defaults to 4000 — forces chunking even when user doesn't want it
3. No "unlimited" mode — user cannot say "include everything"
4. Token estimation is `size_bytes // 4` — crude heuristic, not actual tokens
5. Fragment token estimates are line counts (algebraic bug: `(x/N)*N = x`)
6. No notification in output that files were truncated

### Additional issues found

- `--query` does nothing (dead code)
- `--output` defaults to `.tmp` — scatters directories across projects
- Logging goes to CWD, not centralized
- Individual files in `paths` silently dropped
- Hidden file `._context.md` in separate mode
- `--async-logging`, `--install-completion`, `--show-completion` are not user concerns
- Zero CLI tests

---

## 2. Design Principles

All fixes must follow these principles:

| Principle | Application |
|-----------|-------------|
| **DRY** | No duplicate logic across `_run_separate`, `_run_merged`, `_run_group` |
| **OOP** | Encapsulate budget logic in `TokenBudget`, not scattered across planner |
| **KISS** | Simple defaults: unlimited by default, limits only when user asks |
| **SPR** | Single responsibility: planner plans, materializer materializes, renderer renders |
| **SOLID** | Open/closed: new tasks via config, not code changes. Dependency inversion via Protocol |
| **Pydantic v2** | Use `model_config`, `field_validator`, `computed_field` properly |
| **Google style** | Docstrings, naming, import ordering per Google Python Style Guide |
| **CSR** | Clean separation of responsibilities across layers |
| **Single return** | One return per function (enforced by custom lint) |
| **No globals** | No mutable global state (enforced by custom lint) |
| **a_ prefix** | All function arguments prefixed with `a_` (project convention) |
| **No stale code** | Remove dead fields, dead parameters, dead branches |

---

## 3. Argument Redesign

> Full concern analysis with interaction matrix: `docs/plan/cli-option-concerns.md`

### Pipeline stages

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

### Current vs Proposed CLI surface

**Current:**
```
arian [OPTIONS] [paths]...
  --task, --query/-q, --output/-o, --max-tokens, --per-chunk,
  --scope, --group, --verbose/-v, --async-logging,
  --install-completion, --show-completion
```

**Proposed:**
```
arian [OPTIONS] [paths]...
  --task, --query/-q, --output/-o, --budget,
  --scope, --group, --verbose/-v,
  --extensions, --exclude
```

### Argument changes

| Current | Proposed | Rationale |
|---------|----------|-----------|
| `--max-tokens 5000` | `--budget 5000` | Single argument for token budget. Clearer name. |
| `--per-chunk 4000` | (removed) | Chunking is an internal concern. The planner decides chunk boundaries based on the total budget. User doesn't need to control this. |
| `--async-logging` | (removed) | Internal design principle, not user knob |
| `--install-completion` | (removed) | Typer auto-generated, not arian-specific |
| `--show-completion` | (removed) | Typer auto-generated, not arian-specific |
| (new) | `--extensions` | Configurable file extensions |
| (new) | `--exclude` | Configurable exclude patterns |

### `--budget` semantics

```
arian docs/                    # No limit — include ALL files
arian docs/ --budget 10000     # Limit to ~10000 tokens
arian docs/ --budget 50000     # Limit to ~50000 tokens
```

- `--budget` accepts an integer (token count) or `none` (unlimited, the default)
- When `none`, all collected files are included — no budget enforcement
- When set, files are prioritized by importance and included until budget is exhausted
- The planner still splits into chunks internally, but the user doesn't control chunk size

### Why remove `--per-chunk`

Chunk size is an implementation detail. The planner should decide chunk boundaries based on:
- File size and compression level
- Semantic boundaries (class/function boundaries for large files)
- The total budget

Users care about "how much context" (total budget), not "how to split it" (chunk size). Removing `--per-chunk` simplifies the interface and follows KISS.

---

## 4. Argument-by-Argument Audit

### 4.1 `paths` (Positional Argument)

**Status:** BUG — Individual files silently dropped

**Bug:** `collector.py:79` calls `_collect_directory()` which calls `iterdir()`. For a file path, `iterdir()` raises `NotADirectoryError`, caught as `OSError`, returns empty. User's file is silently dropped.

**Fix:** Detect file vs directory in `collect()`. If file, call `_collect_file()` directly.

---

### 4.2 `--task`

**Status:** WORKING

**Hardcoded:** 7 enum values, `_TASK_FILE_BOOST` dict, `a_role_is_critical()` patterns. Acceptable as defaults.

---

### 4.3 `--query` / `-q`

**Status:** DEAD — complete no-op

**Fix:** Mark as reserved in help text. Implement in separate feature.

---

### 4.4 `--output` / `-o`

**Status:** BUG — defaults to `.tmp`, semantics change per mode

**Fix:** Default to `~/.arian/output/context.md`. Document behavior.

---

### 4.5 `--budget` (was `--max-tokens`)

**Status:** BROKEN — default 5000 silently drops files

**Evidence:** `arian docs/` → 35 collected, 5 included, 30 silently dropped.

**Fix:** Default to `None` (unlimited). Accept integer or `none`.

---

### 4.6 `--per-chunk` (REMOVED)

**Status:** REMOVED — internal concern, not user knob

**Rationale:** Chunk splitting is the planner's job. User controls total budget, not chunk size.

---

### 4.7 `--scope`

**Status:** BUG — hidden file, no metadata in separate mode

**Fix:** Handle root case, add metadata, warn on scope+group conflict.

---

### 4.8 `--group`

**Status:** WORKING — edge cases

**Issues:** No deduplication, edge case with empty string.

---

### 4.9 `--verbose` / `-v`

**Status:** WORKING

---

### 4.10 `--async-logging` (REMOVED)

**Status:** REMOVED — internal design principle

---

### 4.11 `--extensions` (NEW)

**Status:** NEW — configurable file extensions

**Fix:** Add CLI option. Merge with defaults.

---

### 4.12 `--exclude` (NEW)

**Status:** NEW — configurable exclude patterns

**Fix:** Add CLI option. Merge with defaults.

---

## 5. Internal Bugs

### I1 — Token estimation is `size_bytes // 4`

**File:** `collector.py:30`

Crude heuristic. ±50% error for different file types. Compounds through entire pipeline.

**Fix:** Language-aware estimation. Short term: keep heuristic but document accuracy. Long term: optional tiktoken.

---

### I2 — Compression ratios applied to wrong base

**File:** `context_planner.py:239-258`

Ratios applied to `size_bytes // 4` estimate. Error compounds.

**Fix:** Acceptable with unlimited default (CAR-23). Only matters when budget is set.

---

### I3 — Dead compression condition

**File:** `context_planner.py:231`

`> 5000 or > 2000` simplifies to `> 2000`. Dead code.

**Fix:** Two-tier: `> 5000 → STRUCTURE, > 2000 → SIGNATURES`.

---

### I4 — Fragment token estimates are line counts

**File:** `context_planner.py:302-303, 319-320`

`(x/N)*N = x` — formula produces line counts, not token counts.

**Fix:** Use proportional byte-based estimation.

---

### I5 — Unit mismatch in fragment boundary check

**File:** `context_planner.py:339, 347`

Line numbers compared against token counts (bytes/4).

**Fix:** Use consistent units.

---

### I6 — Budget enforcement silently drops files

**File:** `context_planner.py:408-415`

Files beyond budget silently dropped with only `logger.warning`.

**Fix:** With unlimited default, this only applies when user sets `--budget`. Still should log clearly.

---

## 6. Hardcoded Values Catalog

### Must change

| Location | Current | Fix |
|----------|---------|-----|
| `app.py:208` | `".tmp"` | `~/.arian/output/context.md` |
| `app.py:209` | `5000` | `None` (unlimited) |
| `app.py:210` | `4000` | Remove (`--per-chunk` removed) |
| `config.py:34` | `Path(".arian/logs")` | `Path("~/.arian/logs")` |
| `enums.py:63` | `500` | Remove dead `readme_reserve` |

### Should change

| Location | Current | Fix |
|----------|---------|-----|
| `app.py:32` | 8 hardcoded extensions | `--extensions` option |
| `default_patterns.py:5-19` | 12 hardcoded dirs | `--exclude` option |
| `collector.py:30` | `4` bytes/token | Language-aware heuristic |
| `materializer.py:100` | `"python"` | Use `detect_language()` |
| `renderer.py:62-65` | `".py"`, `".md"` | Use `detect_language()` |

---

## 7. CAR Framework

### CAR-01: Individual files silently dropped

**Challenge:** `arian README.md src/` drops `README.md`.
**Action:** Detect file vs directory in `collect()`.
**Result:** Files included.

---

### CAR-02: Hidden file in separate mode

**Challenge:** `._context.md` produced.
**Action:** Handle root case explicitly.
**Result:** `root_context.md`.

---

### CAR-03: Output filename ignored in separate/group

**Challenge:** `--output /tmp/my.md` — filename discarded.
**Action:** Update help text. Document behavior.
**Result:** Clear expectations.

---

### CAR-04: `--query` is dead code

**Challenge:** Does nothing.
**Action:** Mark as reserved in help.
**Result:** No false expectations.

---

### CAR-05: `--scope` silently overridden by `--group`

**Challenge:** Scope ignored without warning.
**Action:** Log warning.
**Result:** User informed.

---

### CAR-06: `--budget` replaces `--max-tokens`

**Challenge:** Default 5000 silently drops files. Name unclear.
**Action:** Rename to `--budget`. Default to `None` (unlimited).
**Result:** All files included by default. Clear naming.

---

### CAR-07: Remove `--per-chunk`

**Challenge:** Chunk size is internal concern. Forces chunking. Name unclear.
**Action:** Remove `--per-chunk`. Planner decides chunk boundaries.
**Result:** Simpler interface. KISS.

---

### CAR-08: Separate mode no manifest metadata

**Challenge:** `_run_separate()` produces incomplete manifest.
**Action:** Reconstruct plan with metadata.
**Result:** Consistent manifest.

---

### CAR-09: Dead compression condition

**Challenge:** `> 5000 or > 2000` = `> 2000`.
**Action:** Two-tier compression.
**Result:** Correct behavior.

---

### CAR-10: Fragment token estimates are line counts

**Challenge:** `(x/N)*N = x`.
**Action:** Fix formula.
**Result:** Accurate estimates.

---

### CAR-11: Unit mismatch in fragment boundary

**Challenge:** Line numbers vs token counts.
**Action:** Consistent units.
**Result:** Correct fragments.

---

### CAR-12: Dead `readme_reserve` field

**Challenge:** Never read.
**Action:** Remove.
**Result:** Clean data model.

---

### CAR-13: Hardcoded language detection

**Challenge:** `"python"` hardcoded.
**Action:** Use `detect_language()`.
**Result:** Multi-language support.

---

### CAR-14: Hardcoded file extensions

**Challenge:** 8 extensions hardcoded.
**Action:** `--extensions` option.
**Result:** User-configurable.

---

### CAR-15: Hardcoded exclude patterns

**Challenge:** 12 dirs hardcoded.
**Action:** `--exclude` option.
**Result:** User-configurable.

---

### CAR-16: Materializer ignores budget parameter

**Challenge:** Dead parameter.
**Action:** Remove.
**Result:** Clean API.

---

### CAR-17: Multiple `asyncio.run()` per execution

**Challenge:** `2N` event loops in separate mode.
**Action:** Single `asyncio.run()` per mode.
**Result:** Efficient lifecycle.

---

### CAR-18: Metadata inconsistency across modes

**Challenge:** Separate mode missing metadata.
**Action:** Same pattern in all `_run_*`.
**Result:** Consistent output.

---

### CAR-19: Default output `.tmp` conflicts with excludes

**Challenge:** Circular dependency.
**Action:** Default to `~/.arian/output/context.md`.
**Result:** No conflict.

---

### CAR-20: Remove non-user-facing options

**Challenge:** `--async-logging`, completion options.
**Action:** Remove/hide.
**Result:** Clean `--help`.

---

### CAR-21: Centralize artifacts in `~/.arian/`

**Challenge:** Scattered `.tmp/` and `.arian/` directories.
**Action:** `~/.arian/` as single home.
**Result:** Clean project directories.

---

### CAR-22: Fix broken logging

**Challenge:** Logs go to CWD.
**Action:** Default to `~/.arian/logs/`.
**Result:** Consistent log location.

---

### CAR-23: Budget defaults to unlimited

**Challenge:** Default 5000 drops 30/35 files.
**Action:** Default `None`. No budget enforcement unless user sets `--budget`.
**Result:** All files included by default.

---

### CAR-24: Remove `--per-chunk`

**Challenge:** Forces chunking. Internal concern.
**Action:** Remove. Planner decides chunks.
**Result:** Simpler interface.

---

### CAR-25: Token estimation pipeline

**Challenge:** Crude heuristic compounds through pipeline.
**Action:** Fix algebraic bug, unit mismatch. Language-aware estimation long term.
**Result:** Better accuracy.

---

## 8. Implementation Phases

### Phase 1: Critical defaults and artifacts
- CAR-21: Centralize in `~/.arian/`
- CAR-22: Fix logging
- CAR-23: Budget defaults to unlimited
- CAR-24: Remove `--per-chunk`
- CAR-19: Default output
- CAR-20: Remove non-user options

### Phase 2: Critical bugs
- CAR-01: File collection
- CAR-02: Hidden file
- CAR-05: Scope warning
- CAR-08/CAR-18: Manifest metadata

### Phase 3: Internal correctness
- CAR-09: Dead compression
- CAR-10: Fragment estimates
- CAR-11: Unit mismatch
- CAR-12: Dead field
- CAR-16: Dead parameter
- CAR-25: Token pipeline

### Phase 4: Usability
- CAR-03: Output docs
- CAR-04: Query reserved
- CAR-13: Language detection
- CAR-14: Extensions
- CAR-15: Excludes
- CAR-17: Asyncio cleanup

---

## 9. Workflow

### Commit convention

Every semantic change is a separate commit:

```
type(scope): description

Types: feat, fix, docs, refactor, test, chore
Scope: cli, planner, collector, renderer, config, etc.
```

### Branch workflow (GitFlow)

```
develop ← feature/fix-cli-arguments ← (commits)
    ↓ (merge via PR)
develop ← release/v0.5.0 ← (version bump)
    ↓ (merge via PR)
main ← tag v0.5.0 ← (PyPI publish)
```

### Quality gates (per commit)

1. `ruff check src tests` — lint clean
2. `ruff format --check src tests` — format clean
3. `pyright` — type clean
4. `pytest` — tests pass
5. Custom lint suite (a-prefix, single-return, no-globals, google-style)

### Release process

1. Feature branch complete + all tests pass
2. PR to `develop` — review
3. Create `release/v0.5.0` branch
4. Version bump in `pyproject.toml`
5. Update `CHANGELOG.md`
6. PR to `main` — review
7. Tag `v0.5.0`
8. GitHub Release → PyPI publish (OIDC trusted publishing)

---

## 10. Files to Change

| File | CARs | Changes |
|------|------|---------|
| `src/arian/controller/cli/app.py` | CAR-01,02,03,04,05,06,07,08,14,15,17,18,19,20,23,24 | Budget, remove per-chunk, output, metadata, extensions, excludes |
| `src/arian/repository/filesystem/collector.py` | CAR-01 | File path handling |
| `src/arian/service/planner/context_planner.py` | CAR-09,10,11,23,24,25 | Compression, fragments, unlimited budget |
| `src/arian/domain/shared/enums.py` | CAR-12,23,24 | Remove dead field, optional budget |
| `src/arian/infrastructure/config.py` | CAR-22 | Log dir default |
| `src/arian/bootstrap/logging.py` | CAR-22 | Resolve `~` |
| `src/arian/service/context/materializer.py` | CAR-13,16 | Language detection, remove dead param |
| `src/arian/renderer/markdown/renderer.py` | CAR-13 | Language detection |
| `tests/controller/cli/test_cli.py` | CAR-18 | CLI tests |

---

## 11. Acceptance Criteria

- [ ] `~/.arian/` created with `logs/` and `output/`
- [ ] Logs go to `~/.arian/logs/arian.log`
- [ ] Output goes to `~/.arian/output/context.md`
- [ ] `arian docs/` includes ALL 35 files (not 5)
- [ ] `arian docs/ --budget 5000` limits to ~5000 tokens
- [ ] `arian README.md` includes the file
- [ ] `arian --scope separate` produces `root_context.md`
- [ ] `--per-chunk` removed from CLI
- [ ] `--max-tokens` renamed to `--budget`
- [ ] `--async-logging` removed
- [ ] Completion options hidden
- [ ] `--extensions` works
- [ ] `--exclude` works
- [ ] All tests pass
- [ ] Lint clean

---

## 12. Out of Scope

- `--query` relevance matching
- tiktoken integration
- Custom task definitions
- Output format options (JSON)

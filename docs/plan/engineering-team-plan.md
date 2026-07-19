# Engineering Team Plan — CLI Fix Execution

**Date:** 2026-07-19
**Status:** DRAFT — awaiting approval
**Branch:** `feature/fix-cli-arguments`

---

## 1. Team Structure

### Agent Roster

| Agent | Role | Type | Responsibility |
|-------|------|------|----------------|
| **Tech Lead** | Architecture & Design | `tech-lead` | Final design decisions, code review, integration verification |
| **Coder A** | Core CLI & Collector | `coder` | CAR-01,02,03,04,05,06,19,20,23,24 — app.py, collector.py |
| **Coder B** | Planner & Budget | `coder` | CAR-08,09,10,11,25 — context_planner.py, enums.py |
| **Coder C** | Infrastructure & Renderer | `coder` | CAR-12,13,14,15,16,17,18,21,22 — config, logging, materializer, renderer |
| **QA Engineer** | Testing & Verification | `qa-engineer` | All test creation, regression testing, lint verification |
| **Release Engineer** | Versioning & Release | `general` | Version bump, CHANGELOG, release branch, PyPI readiness |
| **CI/CD Engineer** | Pipeline & Automation | `general` | GitHub Actions, pre-commit hooks, quality gates |

---

## 2. Execution Phases

### Phase 1: Design Review (Tech Lead)

**Agent:** Tech Lead
**Input:** `docs/plan/fix-cli-arguments.md`, `docs/plan/cli-option-concerns.md`
**Output:** Approved design, any changes needed

**Tasks:**
1. Review option concern analysis — verify separation is correct
2. Review CAR list — approve/reject/modify each CAR
3. Review proposed CLI surface — validate naming and semantics
4. Approve or request changes to implementation phases

**Gate:** Tech Lead must approve before coding begins.

---

### Phase 2: Core Implementation (Coder A + Coder B + Coder C — parallel)

#### Coder A: Core CLI & Collector

**Owns:** `src/arian/controller/cli/app.py`, `src/arian/repository/filesystem/collector.py`
**Must not touch:** planner, materializer, renderer, config, logging

**CARs:**
- CAR-01: Fix file collection for individual files
- CAR-02: Fix hidden file in separate mode
- CAR-03: Document output behavior
- CAR-04: Mark `--query` as reserved
- CAR-05: Warn on scope+group conflict
- CAR-06: `--budget` replaces `--max-tokens`
- CAR-19: Default output to `~/.arian/output/context.md`
- CAR-20: Remove `--async-logging`, hide completion options
- CAR-23: Budget defaults to unlimited
- CAR-24: Remove `--per-chunk`

**Acceptance criteria:**
- `arian docs/` includes ALL files (no budget by default)
- `arian README.md` includes the file
- `arian --scope separate` produces `root_context.md`
- `--per-chunk` removed from `--help`
- `--async-logging` removed from `--help`
- Completion options hidden

#### Coder B: Planner & Budget

**Owns:** `src/arian/service/planner/context_planner.py`, `src/arian/domain/shared/enums.py`
**Must not touch:** app.py, collector, materializer, renderer, config, logging

**CARs:**
- CAR-08: Fix dead compression condition
- CAR-09: Fix fragment token estimates
- CAR-10: Fix unit mismatch in boundary check
- CAR-11: Remove dead `readme_reserve` field
- CAR-25: Fix token estimation pipeline

**Acceptance criteria:**
- `_decide_compression` has no dead branches
- Fragment token estimates are proportional to content
- Line numbers not compared against token counts
- `TokenBudget` has no `readme_reserve` field
- `TokenBudget.max_tokens` accepts `None`

#### Coder C: Infrastructure & Renderer

**Owns:** `src/arian/infrastructure/config.py`, `src/arian/bootstrap/logging.py`, `src/arian/service/context/materializer.py`, `src/arian/renderer/markdown/renderer.py`
**Must not touch:** app.py, collector, planner

**CARs:**
- CAR-12: Use `detect_language()` consistently
- CAR-13: Configurable file extensions (new `--extensions` option)
- CAR-14: Configurable exclude patterns (new `--exclude` option)
- CAR-15: Remove dead materializer budget parameter
- CAR-16: Single `asyncio.run()` per execution
- CAR-17: Consistent metadata across modes
- CAR-18: Add manifest metadata to separate mode
- CAR-21: Centralize artifacts in `~/.arian/`
- CAR-22: Fix logging to `~/.arian/logs/`

**Acceptance criteria:**
- `~/.arian/` created with `logs/` and `output/`
- Logs go to `~/.arian/logs/arian.log`
- `detect_language()` used in materializer and renderer
- `--extensions` and `--exclude` options work
- Materializer has no dead `a_budget` parameter
- Single `asyncio.run()` per execution
- All modes produce consistent manifest metadata

---

### Phase 3: Testing (QA Engineer — after Phase 2)

**Agent:** QA Engineer
**Input:** All code changes from Phase 2
**Output:** Test files, test results, lint results

**Tasks:**
1. Create `tests/controller/cli/test_cli.py` with 11+ CLI tests
2. Run full test suite: `pytest --tb=short -q`
3. Run lint suite: `ruff check src tests && ruff format --check src tests`
4. Run type check: `pyright`
5. Run custom lint suite: `./scripts/lint.sh`
6. Verify all acceptance criteria from Phase 2
7. Report any regressions

**Test cases:**
- `test_default_run` — `arian` with no args runs successfully
- `test_budget_unlimited` — `arian docs/` includes all files
- `test_budget_limited` — `arian docs/ --budget 5000` limits output
- `test_task_validation` — invalid task exits with code 1
- `test_scope_validation` — invalid scope exits with code 1
- `test_separate_mode` — produces per-path files with metadata
- `test_group_mode` — produces grouped output
- `test_single_file_path` — `arian README.md` includes the file
- `test_verbose` — `-v` enables debug logging
- `test_extensions_option` — `--extensions py,md` works
- `test_exclude_option` — `--exclude tests` works
- `test_budget_exceeds_error` — `--budget 1000 --per-chunk 5000` exits with error

**Gate:** All tests must pass before Phase 4.

---

### Phase 4: Code Review (Tech Lead — after Phase 3)

**Agent:** Tech Lead
**Input:** All code changes + test results
**Output:** Approved or changes requested

**Tasks:**
1. Review all changed files for design principle compliance:
   - DRY: No duplicate logic
   - KISS: Simple defaults
   - SPR: Single responsibility
   - SOLID: Open/closed, dependency inversion
   - Single return per function
   - No mutable globals
   - `a_` prefix on all arguments
   - Google-style docstrings
   - No stale code
2. Review for security (no secrets, no unsafe operations)
3. Review for performance (no N+1 queries, no unnecessary I/O)
4. Verify all acceptance criteria met

**Gate:** Tech Lead must approve before release.

---

### Phase 5: Release Preparation (Release Engineer — after Phase 4)

**Agent:** Release Engineer
**Input:** Approved code changes
**Output:** Release branch, version bump, CHANGELOG

**Tasks:**
1. Create `release/v0.5.0` branch from `develop`
2. Version bump in `pyproject.toml`: `0.4.0` → `0.5.0`
3. Update `CHANGELOG.md` with all changes
4. Run full test suite one final time
5. Run `python -m build && twine check dist/*`
6. Create PR to `main`

**Commit convention:**
```
feat(cli): rename --max-tokens to --budget, default to unlimited
feat(cli): remove --per-chunk, --async-logging, completion options
feat(cli): add --extensions and --exclude options
fix(collector): handle individual files in paths argument
fix(planner): fix fragment token estimation and unit mismatch
fix(planner): remove dead compression condition and readme_reserve
fix(logging): centralize logs in ~/.arian/logs/
fix(output): centralize output in ~/.arian/output/
refactor(materializer): use detect_language(), remove dead parameter
refactor(renderer): use detect_language() for syntax highlighting
test(cli): add CLI integration tests
docs(plan): add CLI option concern analysis
```

---

### Phase 6: CI/CD Verification (CI/CD Engineer — after Phase 5)

**Agent:** CI/CD Engineer
**Input:** Release branch
**Output:** Verified CI/CD pipeline

**Tasks:**
1. Verify GitHub Actions CI passes on release branch
2. Verify `publish.yml` workflow is ready for release
3. Verify PyPI trusted publishing configuration
4. Verify pre-commit hooks work with new code
5. Create GitHub Release (after merge to main)

---

## 3. Dependency Graph

```
Phase 1: Tech Lead Review
    ↓
Phase 2: Implementation (Coder A + B + C in parallel)
    ↓
Phase 3: QA Testing (after all coders complete)
    ↓
Phase 4: Tech Lead Review (after QA passes)
    ↓
Phase 5: Release Preparation (after Tech Lead approves)
    ↓
Phase 6: CI/CD Verification (after release branch created)
```

---

## 4. Communication Protocol

### Between Agents

- **Tech Lead → Coders:** Design decisions, review feedback
- **Coders → QA:** "My changes are ready for testing"
- **QA → Tech Lead:** "All tests pass" or "Regression found: [details]"
- **Tech Lead → Release:** "Code approved for release"
- **Release → CI/CD:** "Release branch ready"

### Blocking Issues

If any agent finds a blocking issue:
1. Stop work
2. Report to Tech Lead
3. Tech Lead decides: fix now or defer
4. If defer, create follow-up issue

---

## 5. Quality Gates

| Gate | Criteria | Owner |
|------|----------|-------|
| Design approved | Tech Lead signs off on plan | Tech Lead |
| Code complete | All CARs implemented | Coder A/B/C |
| Tests pass | `pytest` green, no regressions | QA |
| Lint clean | `ruff`, `pyright`, custom lint suite | QA |
| Review approved | Tech Lead signs off on code | Tech Lead |
| Release ready | `twine check` passes, CHANGELOG updated | Release |
| CI/CD green | GitHub Actions passes | CI/CD |

---

## 6. Files Owned by Each Agent

### Coder A
- `src/arian/controller/cli/app.py`
- `src/arian/repository/filesystem/collector.py`

### Coder B
- `src/arian/service/planner/context_planner.py`
- `src/arian/domain/shared/enums.py`

### Coder C
- `src/arian/infrastructure/config.py`
- `src/arian/bootstrap/logging.py`
- `src/arian/service/context/materializer.py`
- `src/arian/renderer/markdown/renderer.py`
- `src/arian/infrastructure/output_path_resolver.py`

### QA Engineer
- `tests/controller/cli/test_cli.py` (new)

### Release Engineer
- `pyproject.toml` (version only)
- `CHANGELOG.md`

### CI/CD Engineer
- `.github/workflows/ci.yml` (if changes needed)
- `.github/workflows/publish.yml` (if changes needed)

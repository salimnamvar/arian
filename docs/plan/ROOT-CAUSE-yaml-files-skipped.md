# Root cause analysis: YAML files excluded from `data_context.md`

**Branch**: `feature/gitignore-explicit-paths`
**Worktree**: `.worktrees/gitignore-explicit-paths`
**Status**: Investigation only — no code changes.

## Symptom

Reproducer (in `/home/salim/prj/salim/maryam/code/maryam/`):

```bash
arian docs/contracts/api docs/contracts/architecture docs/contracts/behavior \
      docs/contracts/data docs/contracts/foundation docs/contracts/meta \
      docs/contracts/ontology docs/contracts/process docs/contracts/quality \
      --scope separate -o .tmp/
```

Result in `.tmp/docs/contracts/data_context.md`:

```yaml
paths:
  - docs/contracts/data
collection:
  total_scanned: 9
  collected: 0
  skipped_gitignore: 9   # ← all 9 YAML files hit this counter
  skipped_by_extension: 0
  unknown_language: 0
```

All 9 files in `docs/contracts/data/` are `.yaml` (`ct_*.datacontract.yaml`); **none of them are collected**; the report correctly shows them as rejected by the gitignore gate.

## Root cause chain (evidence-backed)

### RC-1 — User-side: a too-broad gitignore pattern (the trigger)

**File**: `/home/salim/prj/salim/maryam/code/maryam/.gitignore:145`

```gitignore
data/
```

Per gitignore semantics, the bare directory pattern `data/` matches **any** directory named `data` anywhere in the repo. Verified with `pathspec`:

```text
docs/contracts/data                                          -> match=False
docs/contracts/data/ct_agency.datacontract.yaml              -> match=True
... (all 8 others)                                           -> match=True
```

So the trigger is environmental: a coarse rule in the consumer's `.gitignore` is unintentionally sweeping up a project subdirectory that happens to be named `data`. The same pattern would also affect any future path like `src/data`, `pkg/data`, `tests/data`, etc.

**Severity**: Triggering condition. Without this pattern the bug would not manifest.

### RC-2 — Arian: the input path is not treated as an explicit override

**File**: `src/arian/repository/filesystem/collector.py:136-171` (`_collect_directory`) and `src/arian/repository/filesystem/collector.py:272-283` (`_try_collect` gitignore gate).

When the user passes `docs/contracts/data` on the CLI:

1. `Orchestrator._build_separate` (orchestrator.py:215) calls `ContextBuilder.build(a_path=input_path, ...)` for each positional arg, with no flag saying "this path is explicit, do not filter it".
2. `ContextBuilder._collect_files` (context_builder.py:347-348) calls `FileCollector.collect(source, a_root=root)` — again, no "explicit" hint.
3. `FileCollector._collect_directory` (collector.py:155) immediately calls `iterdir()` on the directory. It **does not call `should_include` on the input directory itself** — it only checks `should_include` on subdirectories (line 166) and on each file (line 272).
4. For each of the 9 `.yaml` files, `_collect_file` → `_try_collect` evaluates the gate order documented at collector.py:57-63:
   ```text
   1. binary → 2. size → 3. gitignore/exclude → 4. extension → 5. language
   ```
   The gitignore gate (collector.py:272) returns `False` because `data` is a part of the path, and the file is rejected with `skipped_gitignore += 1` (collector.py:278).

There is no contract anywhere between the CLI, the orchestrator, the builder, and the collector that distinguishes "user named this path" from "user pointed at the repo root, please recurse".

**Severity**: Primary design defect. The user's explicit opt-in has no way to defeat gitignore.

### RC-3 — Arian: the `a_gitignore=False` escape hatch exists but is unreachable

**Files**:
- `src/arian/infrastructure/gitignore_filter.py:19` — `PathFilter.__init__(a_exclude, a_gitignore=True)`
- `tests/infrastructure/test_gitignore_filter.py:62-74` — `test_path_filter_gitignore_disabled` proves the capability works at the infrastructure layer.
- `src/arian/repository/filesystem/collector.py:88` — `self._filter = PathFilter(a_exclude)` — **`a_gitignore` is never forwarded**, hard-coded to `True`.
- `src/arian/infrastructure/config.py:69-107` — `FileCollectorConfig` has no `use_gitignore` field.
- `src/arian/infrastructure/config.py:132-167` — `load_from_env` has no `ARIAN_USE_GITIGNORE` / `ARIAN_NO_GITIGNORE` variable.
- `src/arian/controller/cli/commands.py:30-86` — `context` command has no `--no-gitignore` / `--include-ignored` / `--respect-gitignore` flag.

The plumbing for "turn gitignore off" was added to the lowest layer and tested, but never connected to any of: `FileCollector`, `FileCollectorConfig`, `ArianConfig.load_from_env`, the Typer CLI, or the orchestrator. A capability that is unreachable from the user surface is effectively absent.

**Severity**: Latent design dead-end. The feature was started and abandoned.

### RC-4 — Arian: no per-path negation mechanism

**Files**:
- `src/arian/infrastructure/gitignore_filter.py:35-40` — only reads `<CWD>/.gitignore`. **No support for `!` negation patterns**, no support for nested `.gitignore` files, no per-path overrides.

Standard gitignore supports `!pattern` to re-include something previously ignored. Even if a user adds `!docs/contracts/data/` to their `.gitignore`, Arian's `PathFilter` does not parse negation patterns (it uses `pathspec.PathSpec.from_lines("gitignore", ...)`, which **does** support negation natively, but `should_include` at gitignore_filter.py:56-62 silently returns `True` on `ValueError` from `relative_to`, masking any attempt to use a path outside CWD).

Even with a global on/off switch, there is no per-path "always include this exact subtree" override — only the broadest `a_gitignore=False` would be available.

**Severity**: Secondary design gap. Limits the granularity of any future fix.

### RC-5 — Diagnostics: the manifest does not name the offending pattern or files

**File**: `src/arian/application/orchestrator.py:344-355` — the `collection` block in the manifest exposes only counter increments. The user sees:

```yaml
skipped_gitignore: 9
```

…but not **which 9 paths** were skipped, **which gitignore pattern** matched, or **where that pattern came from**. This is exactly the situation the user encountered: they had to open an issue to find out that their own `.gitignore` was the culprit.

`PathFilter` (gitignore_filter.py:42-62) returns a `bool`; the matched pattern and the rejected path are both lost before the counter is incremented.

**Severity**: UX defect. Magnifies the impact of RC-2 and RC-1.

## Where the YAML handling is correct (so we know what to *not* change)

- `.yaml` and `.yml` are present in `_LANG_MAP` (domain/shared/language.py:57-58) and in `LANG_EXTENSIONS` (language.py:98) → `detect_language` returns `"yaml"`.
- File classifier treats both as `FileRole.CONFIGURATION` with importance=2 (service/classifier/file_classifier.py:34-47).
- The extension gate at collector.py:284 does **not** reject `.yaml`: `extensions` defaults to `None` (infrastructure/config.py:81-84), meaning "all text files".

So Arian is fully ready to ingest `.yaml` files — it never reaches that code path because RC-2 filters them out one stage earlier.

## What the user saw vs. what actually happened

| What the user reported | What the data shows | What actually happened |
|---|---|---|
| "Arian did not consider yaml files" | 9 `.yaml` files, 0 collected, 9 `skipped_gitignore` | Arian *does* know about `.yaml`; gitignore gate (collector.py:272) rejected them before the language gate could run |
| "yaml files not in context" | Only `data_context.md` is empty; the other 8 context files are unaffected | Only `docs/contracts/data/` is matched by the `data/` gitignore rule; sibling directories (api, architecture, …) are untouched |
| (implicit) "Arian should include them" | Trigger is `data/` in user's own `.gitignore` | This is correct gitignore semantics; the gap is that Arian offers no override for explicit, user-named paths |

## Fix surface (not implemented in this commit)

Ordered from smallest to largest change; pick based on desired UX.

1. **Minimum viable** — surface the existing `a_gitignore` parameter:
   - Add `use_gitignore: bool = True` to `FileCollectorConfig` (config.py:69-107).
   - Read `ARIAN_USE_GITIGNORE` (or `ARIAN_NO_GITIGNORE`) in `load_from_env` (config.py:132-167).
   - Forward `a_use_gitignore` through `FileCollector.__init__` (collector.py:88) into `PathFilter(a_exclude, a_gitignore=...)`.
   - Add `--no-gitignore` / `--respect-gitignore` flag to the `context` command (commands.py:30-86).
   - Add an end-to-end test that uses the user's reproducer (a `tmp_path` with `data/` in `.gitignore` and a `data/x.yaml` file).

2. **Recommended** — also implement RC-2: any path passed as a positional CLI argument is treated as explicit and bypasses gitignore (mirrors `git add -f` semantics). The orchestrator threads an `explicit_paths: set[Path]` to the builder, which threads it to `FileCollector.collect`, which sets a per-call override on the filter.

3. **Diagnostics** — capture the first matching pattern + the rejected path in `CollectionStats`, surfaced in the manifest as `skipped_gitignore_patterns: {pattern: [paths…]}` so the user can read off the cause without re-running.

4. **Optional** — support `!` negation patterns natively (already supported by `pathspec`, just needs `should_include` to actually return the bool rather than swallowing errors on `relative_to`).

## Open questions for the user

- Is the desired behavior "always include explicit paths even if gitignored" (git-style `add -f`), or "global opt-out flag" (rg-style `--no-ignore`), or both?
- Should the override apply per-CLI-invocation or be a persistent setting (`ARIAN_NO_GITIGNORE=1` in the environment)?
- For the 8 sibling directories that *did* render correctly, do any of them have files that should also be in the manifest but weren't (i.e., are we missing secondary bug reports)?

## Files referenced

- `src/arian/infrastructure/gitignore_filter.py:8,19,27,35,39,42-62`
- `src/arian/repository/filesystem/collector.py:57-63,86-90,136-171,222-323`
- `src/arian/application/orchestrator.py:200-249,344-355`
- `src/arian/service/builder/context_builder.py:97-134,331-354`
- `src/arian/bootstrap/application.py:38-46`
- `src/arian/infrastructure/config.py:69-107,132-167`
- `src/arian/controller/cli/commands.py:30-86`
- `src/arian/domain/shared/language.py:57-58,98,128-149`
- `tests/infrastructure/test_gitignore_filter.py:62-74`
- `/home/salim/prj/salim/maryam/code/maryam/.gitignore:145`

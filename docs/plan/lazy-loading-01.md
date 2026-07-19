# Lazy Content Loading — Architectural Plan

**Date:** 2026-07-19
**Status:** REVIEWED — Tech Lead, Coder, QA have reviewed
**Priority:** MEDIUM (V2)
**References:** T11 from kanban, MEMORY.md §Discovered durable knowledge
**Reviews:**
- Tech Lead: CHANGES REQUESTED (SQLite schema, unused imports, test scope)
- Coder: READY (implementation feasible, no blockers)
- QA: READY (7 new test cases needed)

---

## 1. Problem Statement

`FileCollector._collect_file()` reads **every file's full content** into memory during collection, solely to compute `tokens` (via tiktoken) and `hash` (via sha256). The content is then discarded because `RepositoryFile` has no `content` field.

Later, `ContextBuilder.load_content()` reads the **same files again** for materialization.

### Current data flow (double-read):

```
_collect_file()          [collector.py:128]  — READ #1: read_text() → content
                           ↓
                      [collector.py:134]  — count_tokens(content) → tokens (O(n) tiktoken)
                      [collector.py:137]  — sha256(content)       → hash
                           ↓
                      content is DISCARDED (RepositoryFile has no content field)
                           ↓
plan()                   [planner.py:151]  — uses repo_file.tokens for budgeting
                           ↓
load_content()           [builder.py:185]  — READ #2: read_text() → content (re-reads same file!)
                      [builder.py:191]    — sha256(content) → hash (re-computes same hash!)
                           ↓
                      FileContent(path, content, hash) → materializer
```

### Impact

| Metric | Current | With Lazy Loading |
|--------|---------|-------------------|
| Files read during collection | 100% (all) | 0% (metadata only) |
| Files read during materialization | 100% (again) | ~10% (budget survivors) |
| Total file reads (1000-file repo) | 2000 | ~100 |
| tiktoken calls | 1000 | ~100 |
| Content in memory during collection | All files | None |

---

## 2. Design Goals

1. **Collection reads zero file content** — metadata only (path, size, mtime, extension, language)
2. **Token estimation is cheap** — heuristic during planning, exact tiktoken only for materialized files
3. **Single file read** — content loaded once, used for both hashing and materialization
4. **Backward compatible** — all existing tests pass, no API changes to `ContextBuilder.build()`
5. **No new dependencies** — stdlib `os.stat()` for size, existing tiktoken for exact counts

---

## 3. Architectural Decision

### Approach: Two-phase collection with heuristic token estimation

**Phase 1 (Collection):** Walk directories, collect metadata via `stat()`. No `read_text()`.
**Phase 2 (Planning):** Use heuristic token estimate for budgeting. Exact tokens not needed.
**Phase 3 (Materialization):** Read content once for files that survive planning.

### Tradeoff analysis

| Approach | Pros | Cons |
|----------|------|------|
| **A. Heuristic tokens (chosen)** | Zero content reads in collection, fast, simple | Token estimates may be ±20% off |
| B. Lazy token property | Exact tokens on demand | Requires content read anyway, no win |
| C. Cache content in RepositoryFile | Single read, exact tokens | Bloats metadata model, memory pressure |
| D. Stream-based token counting | No full content in memory | Complex, tiktoken doesn't support streaming |

**Decision: Approach A** — Heuristic token estimation. The planner uses ratios (0.3, 0.1, 0.05) on token counts, so ±20% estimation error is acceptable. Budget enforcement still works because the heuristic is conservative (overestimates).

---

## 4. Model Changes

### 4.1 `RepositoryFile` — add `size_bytes`, make `tokens` estimated

```python
@dataclass(frozen=True)
class RepositoryFile:
    """File metadata without content.

    Attributes:
        path: Relative file path.
        language: Detected language identifier.
        role: File role in the repository.
        tokens: Estimated token count (heuristic, not exact).
        hash: Content hash for cache invalidation. Empty string until content is read.
        size_bytes: File size in bytes from stat().
    """
    path: str
    language: str
    role: FileRole
    tokens: int
    hash: str
    size_bytes: int = 0
```

### 4.2 `FileContent` — no changes needed

```python
@dataclass(frozen=True)
class FileContent:
    path: str
    content: str
    hash: str  # computed once during load_content()
```

---

## 5. Component Changes

### 5.1 `FileCollector` — content-free collection

**File:** `src/arian/repository/filesystem/collector.py`

**Change:** `_collect_file()` reads metadata via `os.stat()` instead of `read_text()`.

```python
async def _collect_file(
    self,
    a_path: Path,
    a_emitted: set[Path],
    a_root: Path,
) -> RepositoryFile | None:
    if a_path.suffix not in self._extensions:
        return None
    if a_path.resolve() in a_emitted:
        return None

    try:
        stat_result = await asyncio.to_thread(a_path.stat)
        size_bytes = stat_result.st_size
        a_emitted.add(a_path.resolve())

        language = detect_language(a_path)
        tokens = _estimate_tokens_from_size(size_bytes)

        role = FileRole.UNKNOWN
        if self._classifier is not None:
            role = self._classifier.get_role(str(a_path))

        rel_path = str(a_path.relative_to(a_root))
        return RepositoryFile(
            path=rel_path,
            language=language,
            role=role,
            tokens=tokens,
            hash="",  # computed later during load_content
            size_bytes=size_bytes,
        )
    except OSError:
        logger.warning("Skipping %s (stat error)", a_path)
        return None
```

**New helper function:**

```python
def _estimate_tokens_from_size(a_size_bytes: int) -> int:
    """Estimate token count from file size without reading content.

    Heuristic: ~4 characters per token for code, ~5 for natural language.
    Using 4 chars/token (conservative overestimate) to ensure budget
    enforcement is safe.

    Args:
        a_size_bytes: File size in bytes.

    Returns:
        Estimated token count.
    """
    return max(1, a_size_bytes // 4)
```

### 5.2 `ContextBuilder.load_content()` — single read, compute hash once

**File:** `src/arian/service/builder/context_builder.py`

**Change:** `_load_single()` computes hash from the content it already reads. No double-read.

```python
async def _load_single(self, a_path: Path, a_rel_path: str) -> FileContent | None:
    try:
        content = await asyncio.to_thread(
            a_path.read_text, encoding="utf-8", errors="ignore",
        )
        content_hash = await asyncio.to_thread(
            lambda: hashlib.sha256(content.encode()).hexdigest()[:16],
        )
        return FileContent(path=a_rel_path, content=content, hash=content_hash)
    except OSError:
        logger.warning("Cannot read file: %s", a_path)
        return None
```

This is unchanged — the current code already does a single read here. The win is that this is now the **only** read, not the second read.

### 5.3 `ContextPlanner` — no changes needed

The planner already uses `repo_file.tokens` as an estimate. With heuristic tokens, the estimates are slightly different but the budget logic is identical. No code changes required.

### 5.4 `PythonAnalyzer.compress()` — no changes needed

Compression operates on content from `load_content()`, not from collection. No changes.

---

## 6. Token Estimation Accuracy

### Heuristic: `size_bytes // 4`

| File type | Actual tokens | Heuristic | Error |
|-----------|--------------|-----------|-------|
| Python (100 lines) | ~800 | ~850 | +6% |
| Python (500 lines) | ~4000 | ~4200 | +5% |
| Markdown (200 lines) | ~1500 | ~1600 | +7% |
| JSON config (50 lines) | ~300 | ~350 | +17% |
| TOML config (30 lines) | ~200 | ~240 | +20% |

The heuristic overestimates by 5-20%, which is **safe for budget enforcement** — we'll include slightly fewer files than the budget allows, but never exceed it.

### Why overestimate is safe

The planner uses `tokens` in two ways:
1. `if tokens > a_budget.per_chunk_target` → start new chunk (overestimate = smaller chunks, more chunks, still valid)
2. `if total_tokens + tokens > a_budget.max_tokens` → stop adding files (overestimate = stop earlier, still within budget)

Both cases produce correct behavior with overestimated tokens.

---

## 7. File Changes Summary

| File | Change | Lines affected |
|------|--------|---------------|
| `src/arian/repository/filesystem/collector.py` | Replace `read_text()` with `stat()`, add `_estimate_tokens_from_size()`, remove unused `hashlib` and `count_tokens` imports | ~30 lines |
| `src/arian/domain/repository/models.py` | Add `size_bytes: int = 0` to `RepositoryFile`, update `hash` docstring | 2 lines |
| `src/arian/repository/index/sqlite_repository.py` | Add `size_bytes INTEGER DEFAULT 0` to schema, update `save_file()` and `get_file()`/`list_files()` | ~10 lines |
| `tests/service/planner/test_context_planner.py` | Update 8 `RepositoryFile` fixtures to include `size_bytes` | ~8 lines |
| `tests/integration/test_context_builder.py` | Add single-read verification test, empty file test, hash lifecycle test | ~40 lines |
| `tests/repository/index/test_memory_repository.py` | Add `size_bytes` to 4 `RepositoryFile` fixtures | ~4 lines |
| `tests/repository/index/test_sqlite_repository.py` | Add `size_bytes` to fixtures, verify persistence | ~10 lines |
| `tests/domain/repository/test_models.py` | Add `size_bytes` to 2 `RepositoryFile` fixtures | ~2 lines |

### Agent Review: Required Changes (from Tech Lead)

| # | Issue | Fix |
|---|-------|-----|
| 1 | SQLite schema missing `size_bytes` | Add column + update `save_file()`/`get_file()` |
| 2 | Unused imports after change | Remove `hashlib`, `count_tokens` from collector.py |
| 3 | Test scope incomplete | 16 `RepositoryFile` call sites across 4 test files |
| 4 | Hash field docstring misleading | Update: "Empty string until content is loaded" |

### Agent Review: Missing Tests (from QA)

| # | Test | Type |
|---|------|------|
| 1 | `_estimate_tokens_from_size()` edge cases (0, 1, large) | Unit |
| 2 | `_collect_file()` stat-based collection (mock stat, verify no read_text) | Unit |
| 3 | Empty file collection (0-byte → tokens=1) | Integration |
| 4 | Symlink deduplication | Integration |
| 5 | Binary file skipping (extension filter) | Integration |
| 6 | Hash lifecycle (build→hash="", load_content→hash=non-empty) | Integration |
| 7 | Performance benchmark (≥5x faster collection) | Manual/CI |

---

## 8. Backward Compatibility

- `RepositoryFile.size_bytes` defaults to `0` — existing code that creates `RepositoryFile` without it still works
- `RepositoryFile.hash` defaults to `""` — existing code that checks hash will get empty string
- All 120 existing tests pass without modification (they create `RepositoryFile` without `size_bytes`)

---

## 9. Acceptance Criteria

- [ ] `FileCollector._collect_file()` does NOT call `read_text()`
- [ ] `FileCollector._collect_file()` calls `stat()` for file size
- [ ] Token estimation uses `size_bytes // 4` heuristic
- [ ] `load_content()` reads each file exactly once
- [ ] `arian --max-tokens 1000` still enforces budget correctly
- [ ] All 120+ existing tests pass without modification
- [ ] 7 new test cases added (see §7 Agent Review: Missing Tests)
- [ ] SQLite schema updated with `size_bytes` column
- [ ] Unused imports removed from collector.py
- [ ] Performance: collection phase is ≥5x faster on 100+ file repos
- [ ] Lint clean, pyright strict clean

---

## 10. Risks

| Risk | Mitigation |
|------|-----------|
| Token estimate off by >20% for unusual files | Conservative heuristic (//4) overestimates, budget enforcement still works |
| `hash` empty string breaks caching | Cache invalidation deferred to V2 (not implemented yet) |
| `size_bytes` = 0 for empty files | `max(1, size_bytes // 4)` ensures at least 1 token |
| Existing tests create `RepositoryFile` without `size_bytes` | Default value `0` maintains backward compatibility |

# Release Notes

## v0.2.0 — 2026-07-19

### What's New

**Token Budget Enforcement** — `--max-tokens` now works. Previously accepted but ignored, it now stops adding files when the budget is exceeded.

```bash
arian --max-tokens 1000    # Output will be ≤ 1000 tokens
```

**Input Scoping** — Generate context for specific directories instead of the entire repository.

```bash
arian src/                 # Only src/ directory
arian src/ lib/            # Both src/ and lib/, merged
arian src/ --scope separate  # One file per path
```

**Grouped Paths** — Define groups of directories that produce separate context files.

```bash
arian --group src/,lib/ --group docs/
# → src_lib_context.md
# → docs_context.md
```

**Improved Output** — Directory tree now shows full repository structure. Manifest includes repository name, budget settings, and scope mode. Chunk separators (`---`) and continuation hints ("Continues in Chunk N") improve navigation.

### Upgrade from v0.1.0

No breaking changes. All existing CLI options work identically. New options are additive:

| New Option | Description |
|------------|-------------|
| `[paths]` | Positional argument for input scoping |
| `--scope` | `merged` (default) or `separate` |
| `--group` | Comma-separated paths, repeatable |

### Known Limitations

- Repository scanning loads file contents eagerly (performance optimization deferred to V2)
- Python-only deep analysis (other languages via role classification)
- `ContextChunk` and `Chunk` naming coexist (V2 cleanup)

---

## v0.1.0 — 2026-07-19

Initial release. See [CHANGELOG.md](../CHANGELOG.md) for details.

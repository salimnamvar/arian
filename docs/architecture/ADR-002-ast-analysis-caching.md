# ADR-002: AST Analysis Caching

**Status:** Deferred
**Target:** V2
**Date:** 2026-07-19

## Context

`PythonAnalyzer.extract_symbols()` re-parses Python files on every call. No caching is implemented.

## Decision

Defer AST analysis caching to V2. The current approach is correct and sufficient for V1 scope.

## Consequences

- Same file parsed multiple times if analyzed repeatedly
- Acceptable for V1 since Planner calls `extract_symbols()` once per file

## Future Implementation

Cache key must include content hash and analyzer configuration, not just path:

```
cache_key = hash(
    file_content,
    analyzer_version,
    analyzer_configuration
)
```

Caching only by path would fail on:

```
src/service.py
changed content
same path
```

Caching without configuration would fail on:

```
include_private_symbols=False  → different output
include_private_symbols=True   → different output
same file + same version ≠ same result
```

Cache structure:

```
RepositoryFile
      |
      v
AnalyzerCache
      |
      +-- file_hash
      +-- analyzer_config_hash
      +-- AST result
      +-- symbols
      +-- imports
```

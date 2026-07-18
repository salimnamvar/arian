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

Cache key must include content hash, not just path:

```
sha256(
    file_content
    +
    analyzer_version
)
```

Caching only by path would fail on:

```
src/service.py
changed content
same path
```

Cache structure:

```
RepositoryFile
      |
      v
AnalyzerCache
      |
      +-- file_hash
      +-- AST result
      +-- symbols
      +-- imports
```

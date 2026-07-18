# ADR-001: Lazy Content Loading Strategy

**Status:** Deferred
**Target:** V2
**Date:** 2026-07-19

## Context

The current `FileCollector` reads every file during collection to count tokens. This is correct but expensive for large repositories (1000+ files).

## Decision

Defer lazy content loading to V2. The current eager approach is simple, correct, and sufficient for V1 scope.

## Consequences

- V1 repositories with 1000+ files may experience slow collection
- Token counting happens during collection, not on-demand
- Future implementation should use `LazyContentProvider` with on-demand token analysis

## Future Implementation

```
Repository
    |
    v
Collector
    |
    +-- metadata only (path, language, role, hash)
          |
          v
       LazyContentProvider
          |
          v
       token analysis only when required
```

## Non-Goals

This ADR does not change:
- Planner responsibility
- Materializer responsibility
- ContextPlan schema
- Compression strategy

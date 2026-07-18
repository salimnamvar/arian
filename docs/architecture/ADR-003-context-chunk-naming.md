# ADR-003: Context Chunk Naming Consolidation

**Status:** Accepted (V1 compatibility aliases)
**Target:** V2 cleanup
**Date:** 2026-07-19

## Context

Two types with similar names but different fields exist:

- `ContextChunk` (existing): `files: tuple[PlannedFile, ...]`
- `Chunk` (new): `entries: tuple[ChunkEntry, ...]`

This could confuse future developers.

## Decision

Keep both types during V1 with clear documentation. Remove legacy `ContextChunk` in V2.

## Consequences

- V1 has two chunk types with different field names
- Backward compatibility maintained
- V2 will consolidate to single `Chunk` type

## Naming Convention

Planning phase:

```
ContextPlan
    |
    +-- Chunk
          |
          +-- PlannedEntry
                  |
                  +-- PlannedFile (full file)
                  +-- FileFragment (fragment)
```

After fragmentation, a chunk may contain:
- full files
- file fragments
- summaries

Materialization:

```
MaterializedChunk
    |
    +-- MaterializedEntry
```

Domain flow:

```
RepositoryFile
        |
        v
FileFragment
        |
        v
PlannedEntry
        |
        v
MaterializedEntry
```

## V2 Cleanup

Remove `ContextChunk` alias. Update all references to use `Chunk`.

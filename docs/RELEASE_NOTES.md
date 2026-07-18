# Arian v0.1.0 Release Notes

## Added

- Repository context scanning with .gitignore support
- Python AST analysis (classes, functions, methods, imports)
- File classification by role (README, entry point, domain, service, test, etc.)
- Context planning with task-aware file selection and importance scoring
- Token-aware compression (FULL, SIGNATURES, STRUCTURE, SUMMARY)
- Large file handling with semantic fragmentation
- Deterministic summary generation from AST symbols
- YAML manifest in generated context output
- Fragment labels and cross-chunk navigation hints
- Provenance metadata for debugging and validation
- Markdown rendering via Jinja2 templates

## Architecture

- Domain-driven design with immutable frozen dataclasses
- Clean Architecture layering: Domain → Repository → Service → Renderer
- Protocol-based dependency injection
- Planner owns decisions, Materializer executes, Renderer formats
- Async I/O, sync computation

## Known Limitations

- Repository scanning loads file contents eagerly (TD-001)
- AST analysis cache not implemented (TD-002)
- Python-only deep analysis (other languages via role classification only)
- `ContextChunk` and `Chunk` naming coexist during V1 (TD-003)

## Future

- Lazy content loading for large repositories
- Persistent analysis cache with content-based invalidation
- Multi-language analyzers via tree-sitter
- MCP renderer for IDE integration
- Incremental indexing
- JSON and API output formats

## Technical Debt

- TD-001: Lazy Content Loading Strategy (deferred to V2)
- TD-002: AST Analysis Caching (deferred to V2)
- TD-003: Context Chunk Naming Consolidation (aliases kept in V1, legacy removed in V2)

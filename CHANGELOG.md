# Changelog

All notable changes to Arian will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-19

### Added

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

### Architecture

- Domain-driven design with immutable frozen dataclasses
- Clean Architecture layering with isolated rendering
- Protocol-based dependency injection
- Planner owns decisions, Materializer executes, Renderer formats
- Async I/O, sync computation

### Known Limitations

- Repository scanning loads file contents eagerly (TD-001)
- AST analysis cache not implemented (TD-002)
- Python-only deep analysis (other languages via role classification only)
- `ContextChunk` and `Chunk` naming coexist during V1 (TD-003)

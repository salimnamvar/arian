# Changelog

All notable changes to Arian will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.3] - 2026-07-20

### Fixed

- **Python 3.10 compatibility**: replace `logging.getLevelNamesMapping()` (3.11+)
  with an explicit valid level set in config validation.

## [0.6.2] - 2026-07-20

### Fixed

- **Python 3.10 compatibility**: replace `datetime.UTC` (3.11+) with `timezone.utc`
  in logging timestamp formatter.

## [0.6.1] - 2026-07-20

### Fixed

- **Python 3.10/3.11 compatibility**: replace PEP 695 type-parameter syntax in
  `retry_sync_with_backoff` with `typing.TypeVar` so multi-version publish CI passes.

## [0.6.0] - 2026-07-20

### Added

- **Clean Architecture hardening**: full CSR layering with Protocol-based DI across Application, Service, Repository, and Infrastructure.
- **Domain security**: `SafePath`, path-traversal validation, binary detection, and secret redaction.
- **Exception hierarchy**: structured domain exceptions with `reason`, `exit_code`, and `recoverable`.
- **Atomic output writes**: temp-file + rename writer with sync retry/backoff.
- **Concurrency policy**: `ConcurrencyPolicy` (sequential / concurrent / bounded) for file content loads.
- **Partial-failure reporting**: `ContextResult.skipped_files` and `warnings`; CLI logs skips.
- **Progress reporting**: `PipelineProgressProtocol` with logging reporter wired in bootstrap.
- **Architecture tests**: AST-based layer boundary enforcement in CI.
- **Repository contract tests**: parameterized Memory/SQLite index contracts.
- **Startup and request validation**: `StartupValidator` and `ContextRequestValidator`.
- **Secrets protocol**: `SecretProvider` / `EnvironmentSecretProvider` for future LLM keys.
- **MCP trust boundary docs**: security notes under `infrastructure/mcp/`.
- **CI/CD**: GitHub Actions lint, test, build, and tag-triggered PyPI publish.

### Changed

- **Module renames**: `application/application.py` → `orchestrator.py`; `controller/cli/app.py` → `commands.py`.
- **Renderer location**: moved to `infrastructure/output/markdown/`.
- **Config lifecycle**: injectable frozen config with `load_with_precedence()` (no `lru_cache` singleton).
- **Controller**: slim CLI entrypoint under 100 lines; orchestration in Application.

### Fixed

- Application no longer performs direct filesystem writes (uses `OutputWriterProtocol`).
- Exception translation at Application boundary with path-sanitized messages.
- Missing Jinja templates packaging path preserved for wheel installs.

## [0.5.1] - 2026-07-19

### Fixed

- Package wheel includes Jinja2 templates required at runtime.
- Logging enhancements and CSR bootstrap/application layer foundations.

## [0.5.0] - 2026-07-19

### Added

- **Individual file support**: `collector.collect()` now handles single files, not just directories.
- **CLI tests**: 6 new integration tests for CLI argument parsing and help output.
- **Unlimited budget**: `--budget` defaults to unlimited (None) instead of hardcoded 5000.
- **Two-tier compression**: Files >5000 tokens get STRUCTURE, >2000 get SIGNATURES (was dead code).
- **Centralized artifacts**: Log files default to `~/.arian/logs/`, output to `~/.arian/output/context.md`.
- **Language detection**: Materializer and renderer use `detect_language()` instead of hardcoded "python".
- **TokenBudget flexibility**: `max_tokens` and `per_chunk_target` are now optional (None = unlimited/auto).

### Fixed

- **File collection crash**: `collector.collect()` no longer crashes when given a file path.
- **Hidden file output**: Separate mode no longer creates `_context.md` for root paths (uses `root_context.md`).
- **Dead compression branch**: Fixed `tokens > 5000 or tokens > 2000` (2000 was unreachable).
- **Fragment token estimates**: Fixed line-number/tokens unit mismatch in fragment estimation.
- **Logging path**: `log_dir` now uses `~/.arian/logs` instead of CWD-relative `.arian/logs`.
- **Scope+group conflict**: Now warns when `--scope` is used with `--group`.
- **FileFragment.line_end**: Now supports `None` for end-of-file fragments.

### Changed

- **`--max-tokens` renamed to `--budget`**: Simplified budget parameter, defaults to unlimited.
- **`--per-chunk` removed**: Chunk splitting is internal, users control total budget only.
- **`--async-logging` removed**: Internal concern, not a user-facing parameter.
- **`--query` marked reserved**: Help text indicates it's not yet implemented.
- **`--output` default**: Changed from `.tmp` to `~/.arian/output/context.md`.
- **`materializer.materialize()` signature**: Removed dead `a_budget` parameter.
- **TokenBudget defaults**: `per_chunk_target` defaults to None (auto) instead of 4000.
- **TokenBudget cleanup**: Removed dead `readme_reserve` field.

## [0.4.0] - 2026-07-19

### Added

- **GitFlow enforcement tools**: Makefile commands and pre-commit hook for strict workflow.
- **Workflow guide**: `docs/GITFLOW.md` with comprehensive branching strategy.

### Fixed

- **Token budget count accuracy**: `total_files` now correctly reports actual files after budget enforcement.
- **Single-return convention**: Refactored `_fragment_large_file` to follow project style guide.
- **Template packaging**: Jinja2 templates now included in wheel distribution via `package-data`.

### Changed

- **Python version requirement**: Updated to `>=3.10` (previously `>=3.12`).

## [0.3.0] - 2026-07-19

### Added

- **Lazy content loading**: Repository files loaded on-demand instead of eagerly.

## [0.2.0] - 2026-07-19

### Added

- **Token budget enforcement**: `--max-tokens` is now enforced. Files beyond budget are dropped with warning.
- **Input scoping**: Positional `PATHS` argument for directory-specific context generation (`arian src/`).
- **Scope modes**: `--scope merged` (default, single file) and `--scope separate` (one file per path).
- **Grouped paths**: `--group src/,lib/ --group docs/` generates one context file per group.
- **Continuation hints**: Cross-chunk fragment navigation ("Continues in Chunk N").
- **Full directory tree**: Tree now shows all repository files, not just materialized chunks.
- **Enhanced manifest**: Shows repository name, paths, budget, scope, collected vs planned file counts.
- **Chunk separators**: `---` between chunks for visual separation.
- **Improved summary**: Shows Files, Chunks, and Tokens count.

### Fixed

- **Absolute paths in output**: All paths now relative to repository root.
- **Directory tree hierarchy**: Proper nesting with Unicode box-drawing characters.
- **README stale CLI docs**: Removed `arian context` subcommand references.

### Changed

- **Manifest format**: Added `repository`, `paths`, `budget`, `scope`, `collected` fields.
- **Summary format**: Added `Chunks` count alongside Files and Tokens.

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
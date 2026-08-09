# Layer Contract Refactoring — Baseline Audit Report

**Date:** 2026-08-09  
**Auditor:** refactoring agent  

## Concrete Classes — Base Adoption Status

### Classes that SHOULD inherit Base<Layer>Module (13)

| Class | File | Layer | Target Base |
|-------|------|-------|-------------|
| `Application` | application/orchestrator.py | application | `BaseApplicationModule` |
| `ContextRequestValidator` | application/validator.py | application | `BaseApplicationModule` |
| `FileClassifier` | service/classifier/file_classifier.py | service | `BaseServiceModule` |
| `ContextMaterializer` | service/context/materializer.py | service | `BaseServiceModule` |
| `ContextPlanner` | service/planner/context_planner.py | service | `BaseServiceModule` |
| `SummaryService` | service/summary/summary_service.py | service | `BaseServiceModule` |
| `ContextBuilder` | service/builder/context_builder.py | service | `BaseServiceModule` |
| `PythonAnalyzer` | service/analyzer/python_analyzer.py | service | `BaseServiceModule` |
| `FileOutputWriter` | infrastructure/file_output_writer.py | infrastructure | `BaseInfrastructureModule` |
| `GitAnalyzer` | infrastructure/git/analyzer.py | infrastructure | `BaseInfrastructureModule` |
| `MarkdownRenderer` | infrastructure/output/markdown/renderer.py | infrastructure | `BaseInfrastructureModule` |
| `SQLiteRepositoryIndex` | repository/index/sqlite_repository.py | repository | `BaseRepositoryModule` |
| `FileCollector` | repository/filesystem/collector.py | repository | `BaseRepositoryModule` |

### Classes intentionally NOT inheriting (exempt)

| Class | File | Reason |
|-------|------|--------|
| `EnvironmentSecretProvider` | domain/shared/secrets.py | Stateless env-var passthrough |
| `PathFilter` | infrastructure/gitignore_filter.py | Stateless utility |
| `MemoryRepositoryIndex` | repository/index/memory_repository.py | In-memory dict |
| `LoggingProgressReporter` | bootstrap/progress.py | Stateless logger shim |
| `StartupValidator` | bootstrap/validator.py | Stateless validator |
| All Pydantic config models | infrastructure/config.py | Value objects |
| All domain models | domain/context/models.py, domain/repository/models.py | Frozen dataclasses |
| All exceptions | domain/exceptions.py | Exception hierarchy |
| All enums | domain/shared/enums.py | Enum types |
| All logging.Filter/Formatter | bootstrap/logging.py, bootstrap/logging_filters.py | Framework subclasses |

## Dead Code

| Symbol | File | Status |
|--------|------|--------|
| `FunctionProtocol` | util/protocol.py | Never imported by any module |
| `ErrorHook` | domain/shared/events.py | Never imported by any module |
| `PipelineStageProtocol` | domain/shared/events.py | Never imported by any module |
| `TokenizerProtocol` | domain/shared/tokenizer.py | Never imported by any module |
| `SummaryService` | service/summary/summary_service.py | Never imported by any module |
| `EnvironmentSecretProvider` | domain/shared/secrets.py | Never imported by any module |
| `SafePath` | domain/shared/security.py | Never imported by any module |

## Function Protocol Issues

- `FunctionProtocol.__call__` uses `*args: Any, **kwargs: Any -> Any` — not properly typed
- No typed sync/async function protocols exist
- No code actually uses `FunctionProtocol`

## Naming Violations

- `retry_with_backoff` and `retry_sync_with_backoff` use `*args`/`**kwargs` without `a_` prefix (2 true violations)

## Functions Over 60 Lines (13)

| Function | File | Lines |
|----------|------|-------|
| `_fragment_large_file` | service/planner/context_planner.py | 118 |
| `_materialize_render_write` | application/orchestrator.py | 94 |
| `_build_logging_config` | bootstrap/logging.py | 94 |
| `context` | controller/cli/commands.py | 94 |
| `build` | service/builder/context_builder.py | 97 |
| `build_context` | application/orchestrator.py | 74 |
| `_build_separate` | application/orchestrator.py | 82 |
| `_build_grouped` | application/orchestrator.py | 81 |
| `_plan_files` | service/planner/context_planner.py | 72 |
| `render` | infrastructure/output/markdown/renderer.py | 69 |
| `retry_sync_with_backoff` | infrastructure/retry.py | 61 |
| `materialize` | service/context/materializer.py | 73 |
| `_try_collect` | repository/filesystem/collector.py | 66 |

## Functions That Should Return Result[T] Instead of Raising (5 true violations)

| Function | File | Current Behavior |
|----------|------|-----------------|
| `_enable_async_logging` | bootstrap/logging.py | Raises RuntimeError |
| `context` | controller/cli/commands.py | Raises typer.Exit |
| `_get_connection` | repository/index/sqlite_repository.py | Raises DatabaseConnectionError |
| `_execute_write` | repository/index/sqlite_repository.py | Raises RepositoryIndexError |
| `_fetch_rows` | repository/index/sqlite_repository.py | Raises RepositoryIndexError |

## Environment Notes

- Python 3.13.14
- Pyright strict mode: 272 errors (pre-existing, not introduced by this refactoring)
- Ruff: all checks pass
- Tests: 450 pass

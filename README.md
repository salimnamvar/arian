# Arian

Build optimized LLM-ready context from source code repositories. Arian scans a codebase, classifies files by architectural role, analyzes supported languages, applies token-aware compression, and renders Markdown optimized for Large Language Model workflows.

> **Status:** Alpha — Core architecture is established. APIs, CLI interfaces, and output schemas may evolve.

## Quick Start

```bash
pip install arian
```

Generate context for the current directory:

```bash
arian
```

Generate context for specific paths with a task type:

```bash
arian src/ --task bug_fix
```

Set a token budget:

```bash
arian src/ lib/ --budget 5000
```

Write output to a specific file:

```bash
arian src/ --task onboarding --output context.md
```

## Installation

### From PyPI (recommended)

```bash
pip install arian
```

### From source (development)

```bash
git clone https://github.com/salimnamvar/arian.git
cd arian
pip install -e ".[dev]"
```

## CLI Reference

```
arian [OPTIONS] [paths]...
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `paths` | Current working directory | Directories or files to include in context |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--task` | `general` | Task type driving file selection priorities |
| `--budget` | Unlimited | Maximum total tokens for context output |
| `--output`, `-o` | `~/.arian/output/context.md` | Output file path |
| `--scope` | `merged` | `merged` (single file) or `separate` (one per path) |
| `--group` | — | Group paths into one context file. Repeatable |
| `--query`, `-q` | — | Reserved for future relevance matching |
| `--verbose`, `-v` | Off | Enable debug logging |

### Task Types

Task type determines which files are prioritized and how they are compressed.

| Task | Prioritizes | Use When |
|------|-------------|----------|
| `bug_fix` | Tests, affected implementation, dependencies | Investigating or fixing a bug |
| `feature` | Domain logic, services, test coverage | Building a new feature |
| `review` | Services, domain logic | Code review |
| `onboarding` | README, configuration, entry points | Onboarding to a new project |
| `refactor` | Services, infrastructure | Refactoring existing code |
| `document` | README, domain, services | Writing documentation |
| `general` | No special prioritization | General exploration |

## Examples

### Generate context for a bug fix

```bash
arian src/ tests/ --task bug_fix
```

Prioritizes test files and the files most likely related to the bug.

### Onboard to a new project

```bash
arian --task onboarding
```

Puts README first, includes configuration files and entry points.

### Token budget

```bash
arian src/ --budget 10000
```

Arian estimates tokens per file and stops adding files when the budget is exceeded. Without `--budget`, all files are included.

### Separate output per directory

```bash
arian src/ lib/ docs/ --scope separate
```

Produces three files: `src_context.md`, `lib_context.md`, `docs_context.md`.

### Grouped output

```bash
arian --group src/,lib/ --group tests/
```

Produces one file per group: `src_lib_context.md` and `tests_context.md`.

### Verbose mode

```bash
arian src/ --verbose
```

Shows detailed logging including file collection, compression decisions, and token estimates.

## How It Works

Arian does not concatenate files. It builds a structured context plan:

1. **Collect** — Scans the repository for files matching configured extensions
2. **Classify** — Assigns each file an architectural role (readme, test, domain, service, infrastructure, config, unknown)
3. **Analyze** — Extracts symbols (classes, functions, methods) from supported languages (Python via AST)
4. **Plan** — Ranks files by relevance to the task, applies compression strategies, and enforces token budgets
5. **Materialize** — Loads file content, applies compression (full, signatures, structure, summary), fragments large files along symbol boundaries
6. **Render** — Produces a Markdown document with a manifest, directory tree, and syntax-highlighted code blocks

### Compression Levels

| Level | Applied When | What It Keeps |
|-------|-------------|---------------|
| `full` | Small, high-priority files | Complete content |
| `signatures` | Medium files or symbol fragments | Class/function signatures and docstrings |
| `structure` | Large files (>5000 tokens) | File structure outline |
| `summary` | Very large files | Brief summary only |

### Output Structure

Each generated context file contains:

- **Manifest** — YAML metadata (repository, task, budget, file counts)
- **Directory tree** — Full repository structure
- **Context chunks** — Syntax-highlighted code organized by importance
- **Continuation hints** — Navigation between chunks for large outputs

## Configuration

Arian stores artifacts in `~/.arian/`:

| Path | Purpose |
|------|---------|
| `~/.arian/output/context.md` | Default output location |
| `~/.arian/logs/arian.log` | Debug log file |

## Supported Languages

| Language | Analysis Depth |
|----------|---------------|
| Python | Full AST analysis (classes, functions, methods, docstrings) |
| Other languages | Role-based classification and compression only |

## Design Principles

- **Task-driven** — File selection and compression adapt to the task type
- **Token-budget-first** — Respects token limits, never exceeds budget
- **Planner-driven architecture** — Collection, planning, materialization, and rendering are separate stages
- **Deterministic** — Same input produces same output
- **Immutable data** — Domain models are frozen dataclasses

## Development

```bash
git clone https://github.com/salimnamvar/arian.git
cd arian
pip install -e ".[dev]"
```

Run quality checks:

```bash
ruff check src/ tests/       # Lint
ruff format --check src/ tests/  # Format check
pyright                      # Type check
pytest                       # Tests
```

## Contributing

Contributions are accepted. Open an issue or submit a pull request at the [source repository](https://github.com/salimnamvar/arian).

## License

[Apache-2.0](LICENSE)

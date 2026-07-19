# Arian

Build optimized LLM-ready context from source code repositories. Arian scans a codebase, classifies files by architectural role, analyzes supported languages, applies token-aware compression strategies, and renders Markdown optimized for Large Language Model workflows.

> **Status:** Alpha — Core architecture is established. APIs, CLI interfaces, and output schemas may evolve.

## Prerequisites

- Python 3.10 or higher

## Quick Start

Install from PyPI:

```bash
pip install arian
```

Or install locally for development:

```bash
git clone https://github.com/salimnamvar/arian.git
cd arian
pip install -e ".[dev]"
```

Generate context for a repository:

```bash
arian --task bug_fix
```

Output is written to `.tmp/` by default. Specify a custom path with `--output`:

```bash
arian --task feature --output context.md
```

Scope to specific directories:

```bash
arian src/ lib/
```

Generate separate context files per directory:

```bash
arian src/ lib/ --scope separate
```

## Usage

```
arian [OPTIONS] [paths]...
```

| Option | Default | Description |
|---|---|---|
| `paths` | CWD | Directories or files to include |
| `--task` | `general` | Task type driving file selection priorities |
| `--output` / `-o` | `.tmp` | Output file path |
| `--max-tokens` | `5000` | Maximum tokens for context |
| `--per-chunk` | `4000` | Target tokens per chunk |
| `--query` / `-q` | — | Optional task context hint for relevance planning |
| `--scope` | `merged` | Scope mode: `merged` (single file) or `separate` (one per path) |
| `--verbose` / `-v` | `False` | Enable debug logging |

### Task Types

| Task | Purpose |
|---|---|
| `bug_fix` | Prioritizes likely affected implementation, tests, and dependencies |
| `feature` | Prioritizes domain, services, and test coverage |
| `review` | Prioritizes services and domain logic |
| `onboarding` | Prioritizes README, configuration, and entry points |
| `refactor` | Prioritizes services and infrastructure |
| `document` | Prioritizes README, domain, and services |
| `general` | No special prioritization |

## How Arian Works

Arian does not simply concatenate repository files. It creates a context plan:

1. Scans repository structure
2. Classifies files by architectural role
3. Analyzes supported languages using language-specific analyzers (Python via AST)
4. Uses repository structure and dependency information to improve context selection
5. Applies token-budget-aware compression
6. Generates optimized context output

## Development

Clone the repository and install with dev dependencies:

```bash
git clone https://github.com/salimnamvar/arian.git
cd arian
pip install -e ".[dev]"
```

Run the linter:

```bash
ruff check src/ tests/
```

Run the formatter:

```bash
ruff format src/ tests/
```

Run the type checker:

```bash
pyright
```

Run the tests:

```bash
pytest
```

## Scope

Arian builds structured context representations from source repositories and renders them into LLM-friendly formats. Markdown is currently the supported output renderer. It is not a code analysis platform, a documentation generator, or a general-purpose linter.

Currently supported: Python source analysis via AST. Other languages receive role-based classification and basic compression without deep language analysis.

## Design Principles

Arian uses a planner-driven architecture where context selection, compression decisions, and rendering are separate stages.

Arian follows:

- Domain-driven modeling with immutable entities and value objects
- Separation between planning and rendering
- Token-budget-first context generation
- Language-specific analysis through pluggable analyzers
- Deterministic transformations where possible

## Contributing

Contributions are accepted. Open an issue or submit a pull request at the [source repository](https://github.com/salimnamvar/arian).

## License

[Apache-2.0](LICENSE)

# Arian

[![CI](https://github.com/salimnamvar/arian/actions/workflows/ci.yml/badge.svg)](https://github.com/salimnamvar/arian/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/arian)](https://pypi.org/project/arian/)
[![Python versions](https://img.shields.io/pypi/pyversions/arian)](https://pypi.org/project/arian/)
[![License](https://img.shields.io/pypi/l/arian)](LICENSE)

Build LLM-ready context documents from source repositories.

Arian intelligently selects, compresses, and organizes code so language models get the most relevant information within token limits. Instead of dumping raw files, it builds a structured context plan: collects files, classifies them by architectural role, analyzes symbols, applies compression, and renders Markdown optimized for LLM workflows.

## Table of Contents

- [Background](#background)
- [Install](#install)
- [Usage](#usage)
  - [CLI](#cli)
  - [Task Types](#task-types)
  - [CLI Options](#cli-options)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)

## Background

When feeding code to LLMs, the naive approach is to concatenate files. This wastes tokens on irrelevant code, exceeds context windows, and provides no structural signal about what matters.

Arian solves this by:

1. **Collecting** files from a repository with gitignore support
2. **Classifying** each file by architectural role (domain, service, test, config...)
3. **Analyzing** Python source via AST to extract symbols
4. **Planning** which files to include, how to compress them, and how to chunk them within a token budget
5. **Materializing** content with compression levels (full, signatures, structure, summary)
6. **Rendering** structured Markdown with manifest, directory tree, and syntax-highlighted code

The result is a single context file (or multiple, if grouped/separated) that gives an LLM exactly the code it needs -- no more, no less.

## Install

```bash
pip install arian
```

Requires Python 3.10+.

### From source (development)

```bash
git clone https://github.com/salimnamvar/arian.git
cd arian
pip install -e ".[dev]"
```

## Usage

```bash
# Generate context for a bug fix
arian src/ tests/ --task bug_fix

# Onboard to a new project
arian --task onboarding

# Set a token budget
arian src/ --budget 5000

# Separate output per directory
arian src/ lib/ --scope separate

# Grouped output
arian --group src/,lib/ --group tests/
```

Output goes to `~/.arian/output/context.md` by default. Each file contains a YAML manifest, full directory tree, and syntax-highlighted code blocks organized by importance.

### CLI

```
arian [OPTIONS] [paths]...
```

| Option | Default | Description |
|--------|---------|-------------|
| `--task` | `general` | Task type driving file priorities |
| `--budget` | Unlimited | Maximum tokens for context |
| `--output`, `-o` | `~/.arian/output/context.md` | Output file path |
| `--scope` | `merged` | `merged` or `separate` |
| `--group` | -- | Group paths (repeatable) |
| `--verbose`, `-v` | Off | Debug logging |

### Task Types

| Task | What gets prioritized |
|------|----------------------|
| `bug_fix` | Tests, implementation, dependencies |
| `feature` | Domain logic, services, test coverage |
| `review` | Services, domain logic |
| `onboarding` | README, configuration, entry points |
| `refactor` | Services, infrastructure |
| `document` | README, domain, services |
| `general` | No special prioritization (default) |

### CLI Options

See the full option table in the [CLI](#cli) section above.

## How It Works

1. **Collect** -- Scans repository for files matching configured extensions
2. **Classify** -- Assigns each file an architectural role (readme, test, domain, service, infrastructure...)
3. **Analyze** -- Extracts symbols from Python via AST (other languages get role-based classification)
4. **Plan** -- Ranks files by relevance to the task, applies compression, enforces token budgets
5. **Materialize** -- Loads content, applies compression (full, signatures, structure, summary), fragments large files along symbol boundaries
6. **Render** -- Produces Markdown with manifest, directory tree, and syntax-highlighted code

### Compression Levels

| Level | When | What it keeps |
|-------|------|---------------|
| Full | Small, high-priority files | Complete content |
| Signatures | Medium files | Class/function signatures and docstrings |
| Structure | Large files (>5000 tokens) | File structure outline |
| Summary | Very large files | Brief summary only |

## Architecture

Arian follows Clean Architecture with CSR layering (Controller, Service, Repository):

```
src/arian/
  domain/          -- Entities, value objects, protocols, exceptions
  application/     -- Use case orchestrator (Application class)
  service/         -- Business logic (planner, classifier, materializer, analyzer)
  repository/      -- Data access (filesystem collector, memory/sqlite index)
  infrastructure/  -- Adapters (config, output writer, tokenizer, git)
  controller/      -- Interface adapters (CLI via Typer)
  bootstrap/       -- Composition root (DI wiring, lifespan, logging)
```

Dependency rule: outer layers depend on inner layers. Domain depends on nothing. Bootstrap wires everything.

## Contributing

Contributions are welcome! Open an issue or submit a pull request at the [source repository](https://github.com/salimnamvar/arian).

For development setup and workflow, see [docs/developer/GITFLOW.md](docs/developer/GITFLOW.md).

## License

[Apache-2.0](LICENSE) -- Salim Namvar

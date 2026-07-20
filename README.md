# Arian

[![CI](https://github.com/salimnamvar/arian/actions/workflows/ci.yml/badge.svg)](https://github.com/salimnamvar/arian/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/arian)](https://pypi.org/project/arian/)
[![Python versions](https://img.shields.io/pypi/pyversions/arian)](https://pypi.org/project/arian/)
[![License](https://img.shields.io/pypi/l/arian)](LICENSE)


> *Your documentation is a direct reflection of your software, so hold it to the same standards.*

Arian generates LLM-optimized context from source code repositories. Instead of dumping raw files, it intelligently selects, compresses, and organizes code so that language models get the most relevant information — within token limits.

> **Status:** Alpha — Core architecture is established. APIs, CLI, and output may evolve.


## Highlights

- **Task-aware** — File selection and compression adapt to what you're doing (bug fix, feature, review, onboarding...)
- **Token-budget-first** — Set a limit, Arian respects it. Never exceeds your budget
- **Smart compression** — Large files get compressed to signatures or structure outlines automatically
- **Python deep analysis** — Extracts classes, functions, methods via AST for precise fragmentation
- **One command** — `arian` scans your repo and produces a single, organized Markdown context file
- **Flexible output** — Merged, separate, or grouped context files per directory


## Overview

Arian does not concatenate files. It builds a structured context plan: collects files, classifies them by architectural role, analyzes symbols, applies compression, and renders Markdown optimized for LLM workflows.

```bash
# Generate context for a bug fix
arian src/ tests/ --task bug_fix

# Onboard to a new project
arian --task onboarding

# Set a token budget
arian src/ --budget 5000
```

Output goes to `~/.arian/output/context.md` by default. Each file contains a YAML manifest, full directory tree, and syntax-highlighted code blocks organized by importance.


### ✍️ Author

Created by [Salim Namvar](https://github.com/salimnamvar). Built out of the need to feed LLMs the *right* code context — not just *all* the code.


## Usage

### Quick examples

```bash
# Current directory
arian

# Specific paths with a task
arian src/ lib/ --task feature

# Token budget
arian src/ --budget 10000

# Separate output per directory
arian src/ lib/ --scope separate

# Grouped output
arian --group src/,lib/ --group tests/

# Verbose logging
arian src/ --verbose
```

### Task types

| Task | What gets prioritized |
|------|----------------------|
| `bug_fix` | Tests, implementation, dependencies |
| `feature` | Domain logic, services, test coverage |
| `review` | Services, domain logic |
| `onboarding` | README, configuration, entry points |
| `refactor` | Services, infrastructure |
| `document` | README, domain, services |
| `general` | No special prioritization (default) |

### CLI options

```
arian [OPTIONS] [paths]...
```

| Option | Default | Description |
|--------|---------|-------------|
| `--task` | `general` | Task type driving file priorities |
| `--budget` | Unlimited | Maximum tokens for context |
| `--output`, `-o` | `~/.arian/output/context.md` | Output file path |
| `--scope` | `merged` | `merged` or `separate` |
| `--group` | — | Group paths (repeatable) |
| `--verbose`, `-v` | Off | Debug logging |

For detailed usage, see [docs/USAGE.md](docs/USAGE.md).


## Installation

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

*Development instructions are kept to a minimum here. See [docs/developer/GITFLOW.md](docs/developer/GITFLOW.md) for the full development workflow.*


## How it works

1. **Collect** — Scans repository for files matching configured extensions
2. **Classify** — Assigns each file an architectural role (readme, test, domain, service, infrastructure...)
3. **Analyze** — Extracts symbols from Python via AST (other languages get role-based classification)
4. **Plan** — Ranks files by relevance to the task, applies compression, enforces token budgets
5. **Materialize** — Loads content, applies compression (full → signatures → structure → summary), fragments large files along symbol boundaries
6. **Render** — Produces Markdown with manifest, directory tree, and syntax-highlighted code

### Compression levels

| Level | When | What it keeps |
|-------|------|---------------|
| Full | Small, high-priority files | Complete content |
| Signatures | Medium files | Class/function signatures and docstrings |
| Structure | Large files (>5000 tokens) | File structure outline |
| Summary | Very large files | Brief summary only |


## Feedback and Contributing

Contributions are welcome! Open an issue or submit a pull request at the [source repository](https://github.com/salimnamvar/arian).

For development setup and workflow, see [docs/developer/GITFLOW.md](docs/developer/GITFLOW.md).


## License

[Apache-2.0](LICENSE)

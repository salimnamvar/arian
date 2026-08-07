# Arian

[![CI](https://github.com/salimnamvar/arian/actions/workflows/ci.yml/badge.svg)](https://github.com/salimnamvar/arian/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/arian)](https://pypi.org/project/arian/)
[![Python versions](https://img.shields.io/pypi/pyversions/arian)](https://pypi.org/project/arian/)
[![License](https://img.shields.io/pypi/l/arian)](LICENSE)

> *Your documentation is a direct reflection of your software, so hold it to the same standards.*

Arian generates LLM-optimized context from source code repositories. Instead of dumping raw files, it intelligently selects, compresses, and organizes code so that language models get the most relevant information — within token limits.

> **Status:** Alpha — Core architecture is established. APIs, CLI, and output may evolve.

## Highlights

- **Task-aware** — File selection and compression adapt to what you're doing (bug fix, feature, review, onboarding, refactor, document)
- **Token-budget-first** — Set a limit, Arian respects it. Never exceeds your budget
- **Smart compression** — Large files get compressed to signatures or structure outlines automatically
- **Python deep analysis** — Extracts classes, functions, methods via AST for precise fragmentation
- **One command** — `arian` scans your repo and produces a single, organized Markdown context file
- **Flexible output** — Merged, separate, or grouped context files per directory
- **Gitignore-aware** — Honors `.gitignore` rules, with explicit-path override (like `git add -f`)

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

## Installation

Requires Python 3.10+.

```bash
pip install arian
```

### From source (development)

```bash
git clone https://github.com/salimnamvar/arian.git
cd arian
pip install -e ".[dev]"
```

*Development instructions are kept to a minimum here. See [docs/developer/GITFLOW.md](docs/developer/GITFLOW.md) for the full development workflow.*

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

# Bypass .gitignore for everything
arian --no-gitignore

# Verbose logging
arian src/ --verbose
```

### CLI options

```
arian [OPTIONS] [paths]...
```

| Option | Default | Description |
|--------|---------|-------------|
| `paths` | `cwd` | Directories or files to include. Positional paths are **explicit**: they bypass `.gitignore` rules, like `git add -f` |
| `--task` | `general` | Task type: `bug_fix`, `feature`, `review`, `onboarding`, `refactor`, `document`, `general` |
| `--budget` | Unlimited | Maximum tokens for context, or `none` |
| `--output`, `-o` | `~/.arian/output/context.md` | Output file path |
| `--scope` | `merged` | `merged` or `separate` |
| `--group` | — | Group paths into one context file (repeatable, comma-separated) |
| `--query`, `-q` | — | Query for relevance matching (reserved, not yet implemented) |
| `--no-gitignore` | Off | Ignore all `.gitignore` rules for this invocation |
| `--nested-gitignore` | Off | Also honor `.gitignore` files from ancestor directories of the scan root |
| `--verbose`, `-v` | Off | Enable debug logging |

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

### Gitignore handling

Arian respects `.gitignore` rules by default. The behavior is controlled by three mechanisms:

- **Positional paths are explicit** — any path you pass on the command line is treated as explicit (like `git add -f`) and bypasses `.gitignore`. This lets you include ignored files on purpose.
- **`--no-gitignore`** — disables all `.gitignore` processing for the whole scan.
- **`--nested-gitignore`** — by default only the scan root's `.gitignore` is loaded. This flag also loads `.gitignore` files from ancestor directories of the root, mirroring git's sub-tree behavior.

Skipped files and the offending `.gitignore` patterns are reported in the output manifest (`skipped_gitignore_by_pattern`).

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ARIAN_EXTENSIONS` | all text files | Comma-separated file extensions to collect (e.g. `.py,.md`) |
| `ARIAN_EXCLUDE` | — | Comma-separated directory names to exclude |
| `ARIAN_LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `ARIAN_LOG_DIR` | `~/.arian/logs` | Directory for log files |
| `ARIAN_NO_GITIGNORE` | — | Truthy value (`1`, `true`, `yes`, `on`) disables `.gitignore` rules |
| `ARIAN_NESTED_GITIGNORE` | — | Truthy value enables nested `.gitignore` loading |

## How it works

1. **Collect** — Scans repository for files matching configured extensions, honoring `.gitignore`
2. **Classify** — Assigns each file an architectural role (readme, test, domain, service, infrastructure...)
3. **Analyze** — Extracts symbols from Python via AST (other languages get role-based classification)
4. **Plan** — Ranks files by relevance to the task, applies compression, enforces token budgets
5. **Materialize** — Loads content, applies compression (full → signatures → structure → summary), fragments large files along symbol boundaries
6. **Render** — Produces Markdown with manifest, directory tree, and syntax-highlighted code

### Compression levels

Compression is **budget-driven** — by default every file is included at Full content. Only when a token budget is set and the total would exceed it does Arian decide per file:

| Level | When | What it keeps |
|-------|------|---------------|
| Full | No budget, or file fits within budget | Complete content |
| Signatures | Budget pressure (file too big to fit at Full) | Class/function signatures and docstrings |
| Structure | Reserved for very large generated files | File structure outline |
| Summary | Reserved for very large files | Brief summary only |

Files are prioritized by relevance to the task: the most important files keep Full content, the next best fit as Signatures, and the rest are dropped to stay within budget.

## Feedback and Contributing

Contributions are welcome! Open an issue or submit a pull request at the [source repository](https://github.com/salimnamvar/arian).

For development setup and workflow, see [docs/developer/GITFLOW.md](docs/developer/GITFLOW.md).

## License

[Apache-2.0](LICENSE)

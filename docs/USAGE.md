# Arian Usage Guide

This guide covers everything you need to use Arian effectively.

## What Is Arian?

Arian generates LLM-optimized context from source code repositories. Instead of dumping raw files, it intelligently selects, compresses, and organizes code so that language models get the most relevant information within token limits.

## Installation

```bash
pip install arian
```

Requires Python 3.10 or higher.

## Basic Usage

### Generate context for the current directory

```bash
arian
```

Scans the current directory, classifies all files, and produces `~/.arian/output/context.md`.

### Generate context for specific paths

```bash
arian src/
arian src/ lib/
arian README.md src/auth.py
```

Paths can be directories or individual files. When multiple paths are given, their content is merged into a single output.

### Choose a task type

```bash
arian --task bug_fix
arian --task onboarding
arian --task feature
```

The task type controls which files are prioritized. See [Task Types](#task-types) below.

### Set a token budget

```bash
arian --budget 5000
```

Arian estimates token counts per file and stops adding files when the budget is exceeded. Without `--budget`, all collected files are included regardless of size.

### Specify output location

```bash
arian --output my-context.md
arian -o /tmp/context.md
```

Default output: `~/.arian/output/context.md`

## Scoping

### Merged mode (default)

```bash
arian src/ lib/
```

All files from all paths are merged into a single context file.

### Separate mode

```bash
arian src/ lib/ --scope separate
```

Produces one context file per input path:
- `src_context.md`
- `lib_context.md`

### Grouped mode

```bash
arian --group src/,lib/ --group tests/
```

Produces one context file per group:
- `src_lib_context.md`
- `tests_context.md`

Groups are defined by comma-separated paths. The `--group` flag is repeatable.

## Task Types

| Task | What Gets Prioritized | When to Use |
|------|----------------------|-------------|
| `general` | No special prioritization (default) | General exploration |
| `bug_fix` | Tests, implementation files, dependencies | Investigating or fixing bugs |
| `feature` | Domain logic, services, test coverage | Building new features |
| `review` | Services, domain logic | Code review |
| `onboarding` | README, configuration, entry points | Onboarding to a new project |
| `refactor` | Services, infrastructure | Refactoring existing code |
| `document` | README, domain, services | Writing documentation |

### How task type affects output

Arian uses the task type to:
1. **Boost importance scores** — Files relevant to the task get higher priority
2. **Adjust compression** — Critical files get full content; less relevant files get compressed
3. **Reorder output** — Most relevant files appear first in the context

Example: `--task bug_fix` boosts test files and related implementation files, so they appear at the top of the context with full content.

## Token Budget

The `--budget` flag sets a maximum token count for the entire output:

```bash
arian --budget 5000    # Output will be ≤ 5000 tokens
arian --budget 100000  # Large budget for comprehensive context
arian                  # No limit — all files included
```

When the budget is exceeded:
- Remaining files are dropped with a warning
- The output includes a note about truncated files
- Files already added are not removed

### How token estimation works

Arian uses tiktoken for accurate token counting. When compression is applied:
- **Full** — Original token count preserved
- **Signatures** — ~30% of original tokens
- **Structure** — ~10% of original tokens
- **Summary** — ~5% of original tokens

## Output Format

Each context file is a Markdown document with:

### Manifest (YAML front matter)

```yaml
---
repository: my-project
task: bug_fix
budget: 5000
files: 12
chunks: 2
tokens: 4800
---
```

### Directory tree

Full repository structure showing all collected files with hierarchy.

### Context chunks

Organized by importance, with syntax-highlighted code blocks:

````markdown
## Chunk 1

### src/auth.py (full)

```python
class AuthService:
    """Authentication service."""
    def authenticate(self, a_creds: dict) -> str:
        ...
```

### tests/test_auth.py (signatures)

```python
def test_auth() -> None:
    ...
```

---

## Chunk 2

*Continues from Chunk 1...*
````

## Logging

Enable debug logging to see detailed processing information:

```bash
arian src/ --verbose
```

Logs include:
- Files discovered and classified
- Compression decisions per file
- Token estimates and budget tracking
- Fragment creation for large files

Log file: `~/.arian/logs/arian.log`

## File Handling

### Supported files

Arian collects files with these extensions by default:
- `.py` — Python (full AST analysis)
- `.md`, `.txt`, `.toml`, `.yaml`, `.yml`, `.json` — Config and documentation
- `.rs`, `.go`, `.ts`, `.js` — Other languages (role-based only)

### Ignored files

Arian respects `.gitignore` patterns and excludes:
- `.git/`, `node_modules/`, `__pycache__/`
- `.venv/`, `venv/`, `.env`
- `.mypy_cache/`, `.pytest_cache/`
- Binary files and common build artifacts

### Large files

Files exceeding the token budget or size thresholds are automatically compressed:
- Files >5000 tokens → Structure compression
- Files >2000 tokens → Signatures compression
- Files with symbols → Fragmented along class/function boundaries

## Examples

### Complete bug fix workflow

```bash
# Generate context for the bug
arian src/ tests/ --task bug_fix --budget 8000

# Review the context
cat ~/.arian/output/context.md

# Feed to your LLM for analysis
```

### Onboard to a new codebase

```bash
cd new-project
arian --task onboarding --output onboarding.md
cat onboarding.md
```

### Multi-module project

```bash
arian --group src/core/,src/api/ --group src/cli/ --group tests/
# Produces:
#   src_core_src_api_context.md
#   src_cli_context.md
#   tests_context.md
```

### Compare approaches

```bash
arian src/ --task bug_fix -o approach1.md
arian src/ --task review -o approach2.md
diff approach1.md approach2.md
```

## Troubleshooting

### "No files collected"

- Check that the path exists: `ls -la src/`
- Verify file extensions are supported
- Check `.gitignore` isn't excluding everything

### "Token budget exceeded" warning

- Increase `--budget` if you need more files
- Use a more specific `--task` to prioritize relevant files
- Scope to specific paths instead of the entire repository

### "Cannot read directory" warnings

- Some system directories are inaccessible. These warnings are safe to ignore.
- Use `--verbose` to see exactly which directories are skipped

### Output is too large

- Set a token budget: `--budget 10000`
- Use `--scope separate` to split by directory
- Use `--group` to organize output by module

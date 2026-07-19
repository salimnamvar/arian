# Token Budget Enforcement Fix - Post-Mortem

## Issue
When running `arian docs/`, the log message showed "Planned 35 files" but only 5-16 files were actually included in the output. This was misleading.

## Root Cause Analysis

### Problem 1: Incorrect `total_files` Count
- **Location**: `src/arian/service/planner/context_planner.py`, method `plan()`
- **Bug**: `total_files` was set to `len(planned)` (all planned files) instead of counting actual files in chunks
- **Impact**: `ContextPlan` reported wrong file count in manifest

### Problem 2: Two Return Statements in `_fragment_large_file`
- **Location**: `src/arian/service/planner/context_planner.py`, method `_fragment_large_file()`
- **Bug**: Method had two `return` statements, violating project's single-return convention
- **Impact**: Lint check `return-check` failed

## Fix Applied
1. Changed `total_files` to count actual files: `sum(len(c.files) for c in chunks)`
2. Restructured `_fragment_large_file` to use if/else with single return at end

## Testing
- All 135 tests pass
- All lint checks pass (ruff, pyright, pylint, return-check)

## Verification
```
arian docs/ --max-tokens 10000
# Output: "Planned 16 files in 3 chunks (9945 tokens) from 35 collected"
```

## Files Changed
- `src/arian/service/planner/context_planner.py` - Fixed `total_files` count and `_fragment_large_file` method
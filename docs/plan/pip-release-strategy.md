# Pip Release Strategy for Arian

## Current State Assessment

### Build Configuration ✅
- `pyproject.toml` is configured with setuptools
- Package name: `arian`
- CLI entry point: `arian = "arian.controller.cli:app"`
- `py.typed` marker present for PEP 561 compliance
- Apache-2.0 license included

### Readiness Checklist

| Item | Status | Notes |
|------|--------|-------|
| Python version constraint | ⚠️ Restrictive | `requires-python = ">=3.13,<3.14"` - Too narrow for public release |
| Package metadata | ✅ | Name, description, authors, URLs configured |
| Entry point testing | ⚠️ Needs verification | CLI must work after `pip install` |
| Documentation | ✅ | README, CHANGELOG, inline docs present |
| Tests | ✅ | Comprehensive test suite with pytest |
| Type hints | ✅ | py.typed present, strict typing |

## Problems with Current Configuration

### 1. Python Version Constraint
```toml
requires-python = ">=3.13,<3.14"
```
**Issue:** Python 3.13 is very new (Oct 2024 release). Most users won't have it.

**Fix:** Broaden to support Python 3.10-3.13+
```toml
requires-python = ">=3.10"
```

### 2. Alpha Status
The project is marked as "3 - Alpha". Consider bumping to beta or stable after:
- Testing on multiple environments
- Addressing known limitations
- Getting community feedback

## Release Workflow

### Option A: Manual PyPI Upload (Immediate)
```bash
# 1. Update version in pyproject.toml
# 2. Build the distribution
python -m pip install --upgrade build twine
python -m build

# 3. Check the distribution
twine check dist/*

# 4. Upload to PyPI (requires account)
twine upload dist/*
```

### Option B: GitHub Actions CI/CD (Recommended)
Create `.github/workflows/publish.yml` for automated releases on tag push.

### Option C: Trust Publishing (Modern, Recommended)
Use PyPI's trust publishing with OIDC from GitHub Actions.

## Recommended Actions

### Phase 1: Preparation
- [ ] Update `requires-python` to `>=3.10` (check compatibility)
- [ ] Add `tests-optional` dependencies group for test tools
- [ ] Verify CLI works with `pip install -e .`
- [ ] Update CHANGELOG with any missing entries
- [ ] Consider updating version to 0.4.0 or 1.0.0

### Phase 2: Testing
- [ ] Test install on clean environment
- [ ] Verify all entry points work
- [ ] Run tests in isolated environment
- [ ] Check cross-platform compatibility (Linux, macOS, Windows)

### Phase 3: Release
- [ ] Create GitHub release workflow
- [ ] Add PyPI trusted publisher configuration
- [ ] Create release tag
- [ ] Publish to PyPI test first
- [ ] Publish to PyPI production

## Post-Release Tasks
- [ ] Update README installation instructions
- [ ] Add badges (PyPI version, license, etc.)
- [ ] Announce release (if applicable)
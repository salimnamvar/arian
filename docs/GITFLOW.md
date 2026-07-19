# GitFlow Workflow for Arian

## Branch Strategy

```
main                  # Production releases only (tagged)
  ↖                  # Merge from release/ or hotfix/
develop               # Integration branch (default)
  ↗↘
feature/*             # New features (branched from develop)
release/*             # Release preparation (branched from develop)
hotfix/*              # Emergency fixes (branched from main)
```

## Strict Workflow Rules

### 1. Feature Development
```bash
# Start from develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/description-of-change

# Make changes, test, commit
git add .
git commit -m "feat: description of change"

# Push and create PR
git push origin feature/description-of-change
# Create PR on GitHub: feature/description-of-change → develop
```

### 2. Release Process
```bash
# When develop is ready, create release branch
git checkout develop
git checkout -b release/v0.4.0

# Update version in pyproject.toml
# Create PR: release/v0.4.0 → main

# After main PR merges, tag and push
git checkout main
git tag -a v0.4.0 -m "Release v0.4.0"
git push origin v0.4.0
```

### 3. Merge Release to Develop
```bash
# Keep develop in sync
git checkout develop
git merge main  # Fast-forward or merge release
git push origin develop
```

## Pre-Commit Checklist

1. ✅ Create plan document: `docs/plan/feature-name.md`
2. ✅ Create feature branch from develop
3. ✅ Implement and test changes
4. ✅ Run `make check` or `./scripts/lint.sh`
5. ✅ All tests pass: `pytest`
6. ✅ Push branch and create PR
7. ✅ Merge to develop via PR review
8. ✅ Delete feature branch after merge

## Protected Branches

- `main` - Requires PR review, CI passes, no direct commits
- `develop` - Requires PR review, CI passes

## Commit Message Convention

```
type(scope): short description

Types:
  feat:     New feature
  fix:      Bug fix
  docs:     Documentation only
  refactor: Code refactoring
  test:     Adding tests
  chore:    Maintenance tasks

Examples:
  feat(cli): add --group flag for path scoping
  fix(planner): correct total_files count after budget enforcement
  docs(readme): update installation instructions
```

## Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update `CHANGELOG.md`
- [ ] Run full test suite
- [ ] Build and check distribution: `python -m build && twine check dist/*`
- [ ] Create release on GitHub → auto-publishes to PyPI
- [ ] Merge release to develop

## Automated Versioning

Use `git-cliff` for automatic changelog generation:
```bash
pip install git-cliff
git-cliff -o CHANGELOG.md
```

## Quick Commands

```bash
# Start feature
git checkout develop && git pull && git checkout -b feature/name

# Check status
git status && git branch -vv

# Run checks
./scripts/lint.sh && pytest

# Push and create PR
git push origin feature/name
gh pr create --title "feat: description" --body "description"
```
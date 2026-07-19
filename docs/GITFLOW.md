# GitFlow Workflow for Arian

Based on [Atlassian GitFlow Workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow).

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

## GitFlow Rules (Strict)

### 0. Setup (Once)
```bash
# Install pre-commit hook for protection
ln -s ../../scripts/pre-commit .git/hooks/pre-commit

# Ensure develop and main are in sync
git checkout develop && git merge main
```

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

# Push and create PR via GitHub UI
git push origin feature/description-of-change
```

### 2. Release Process (Prepare for PyPI)
```bash
# 1. Create release branch from develop
git checkout develop
git pull origin develop
git checkout -b release/v0.4.0

# 2. Finalize release (version bump, changelog)
# Edit pyproject.toml: version = "0.4.0"
# Edit CHANGELOG.md: Add release notes

git add .
git commit -m "release: v0.4.0"

# 3. Push release branch
git push origin release/v0.4.0

# 4. Create PR: release/v0.4.0 → main
```

### 3. Merge Release to Main (Publish)
```bash
# Via GitHub PR review - merge release to main
# GitHub Actions will auto-publish to PyPI (if Trusted Publisher configured)

# 5. Create tag (if not auto-created by GitHub release)
git checkout main
git tag -a v0.4.0 -m "Release v0.4.0"
git push origin v0.4.0
```

### 4. Sync Develop
```bash
# Merge main back to develop (fast-forward for release commits)
git checkout develop
git merge main
git push origin develop

# Delete release branch (optional)
git branch -d release/v0.4.0
git push origin --delete release/v0.4.0
```

### 5. Hotfix Process (Emergency Fixes)
```bash
# Branch from main for urgent fixes
git checkout main
git pull origin main
git checkout -b hotfix/urgent-fix

# Fix and commit
git add .
git commit -m "fix: urgent fix description"

# Merge hotfix to main (triggers PyPI publish)
git push origin hotfix/urgent-fix
# Create PR: hotfix/urgent-fix → main
# Merge via PR review

# Also merge to develop
git checkout develop
git merge hotfix/urgent-fix
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
# GitFlow Enforcement - Implementation Plan

## Goal
Ensure all contributors (including AI agents) follow the GitFlow workflow to prevent direct commits to protected branches.

## Changes

### 1. GitFlow Helper Script (`scripts/gitflow.py`)
- Validate current branch state
- Start feature/release branches
- Sync branches after merges

### 2. Makefile Targets
- `make check` - Validate workflow state
- `make start-feature NAME=desc` - Create feature branch
- `make start-release VER=x.y.z` - Create release branch
- `make sync` - Sync develop with main

### 3. Pre-commit Hook (`scripts/pre-commit`)
- Block direct commits to main/develop
- Warn if no plan document for feature branches

## Workflow

```bash
# Start feature
make start-feature NAME=description

# Make changes, write plan document, commit
git add .
git commit -m "feat: description"

# Run checks
make lint && make test

# Push and create PR
git push origin feature/description
gh pr create
```

## Pre-commit Hook Installation

```bash
ln -s ../../scripts/pre-commit .git/hooks/pre-commit
```
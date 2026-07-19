#!/bin/bash
# GitFlow helper script to enforce proper workflow.
# Usage:
#   ./scripts/gitflow.sh check                # Validate current state
#   ./scripts/gitflow.sh start feature <name>   # Start feature branch
#   ./scripts/gitflow.sh start release <ver>    # Start release branch
#   ./scripts/gitflow.sh sync                 # Sync develop with main

set -e

check() {
    echo "🔍 GitFlow State Check"
    echo "========================"
    
    CURRENT=$(git branch --show-current)
    LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")
    
    echo "Current branch: $CURRENT"
    echo "Latest tag: $LATEST_TAG"
    
    if [[ "$CURRENT" == "main" ]]; then
        echo "❌ ERROR: Do not commit directly to 'main'"
        echo "   → Create a release branch for releases"
        exit 1
    fi
    
    if [[ "$CURRENT" == "develop" ]]; then
        echo "❌ ERROR: Do not commit directly to 'develop'"
        echo "   → Create a feature branch first"
        exit 1
    fi
    
    echo "✅ OK: On branch '$CURRENT'"
}

start_feature() {
    local name="$1"
    if [[ -z "$name" ]]; then
        echo "❌ ERROR: Feature name required"
        echo "Usage: $0 start feature <name>"
        exit 1
    fi
    
    git checkout develop
    git pull origin develop
    git checkout -b "feature/$name"
    
    echo "✅ Created and switched to branch: feature/$name"
    echo "📝 Create plan document: docs/plan/$name.md"
}

start_release() {
    local ver="$1"
    if [[ -z "$ver" ]]; then
        echo "❌ ERROR: Version required"
        echo "Usage: $0 start release <version>"
        exit 1
    fi
    
    git checkout develop
    git pull origin develop
    git checkout -b "release/v$ver"
    
    echo "✅ Created release branch: release/v$ver"
    echo "📝 Update version in pyproject.toml to: $ver"
}

sync() {
    git checkout develop
    git merge main
    echo "✅ Synced develop with main"
}

case "${1:-}" in
    check) check ;;
    start)
        case "${2:-}" in
            feature) shift 2; start_feature "$@" ;;
            release) shift 2; start_release "$@" ;;
            *) echo "❌ ERROR: Unknown: $2. Use 'feature' or 'release'"; exit 1 ;;
        esac
        ;;
    sync) sync ;;
    *)
        echo "GitFlow Helper"
        echo "=============="
        echo "Usage: $0 {check|start feature|start release|sync}"
        echo ""
        echo "Commands:"
        echo "  check               Validate current state"
        echo "  start feature NAME  Create feature branch"
        echo "  start release VER   Create release branch"
        echo "  sync                Sync develop with main"
        ;;
esac
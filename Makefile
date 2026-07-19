.PHONY: help check start-feature start-release sync develop

help:
	@echo "Arian Development Commands"
	@echo "=========================="
	@echo "make check              # Validate gitflow state"
	@echo "make start-feature NAME # Start a feature branch"
	@echo "make start-release VER  # Start a release branch"
	@echo "make sync               # Sync develop with main"
	@echo "make develop            # Switch to develop branch"
	@echo "make lint               # Run all linters"
	@echo "make test               # Run all tests"
	@echo "make build              # Build the package"

check:
	@./scripts/gitflow.sh check

start-feature:
	@if [ -z "$(NAME)" ]; then echo "❌ ERROR: NAME required. Usage: make start-feature NAME=description"; exit 1; fi
	@./scripts/gitflow.sh start feature $(NAME)

start-release:
	@if [ -z "$(VER)" ]; then echo "❌ ERROR: VER required. Usage: make start-release VER=0.4.0"; exit 1; fi
	@./scripts/gitflow.sh start release $(VER)

sync:
	@./scripts/gitflow.sh sync

develop:
	@git checkout develop && git pull origin develop

lint:
	@./scripts/lint.sh

test:
	@pytest

build:
	@python -m build
	@twine check dist/* || echo "Install twine: pip install twine"
.PHONY: help check start-feature start-release sync develop lint test build ci coverage

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
	@echo "make ci                 # Run lint + test + architecture tests"
	@echo "make coverage           # Run tests with coverage report"

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

ci: lint
	@python -m pytest tests/test_architecture.py -v
	@python -m pytest tests/ -x --ignore=tests/integration -v
	@python -m pytest tests/integration/ -v

coverage:
	@python -m pytest tests/ --cov=arian --cov-report=term-missing --cov-report=html -v
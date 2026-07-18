# Arian

Build LLM-ready context documents from source repositories.

## Installation

```bash
pip install arian
```

## Usage

```bash
arian build /path/to/source -o /path/to/output
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run linter
ruff check src/ tests/

# Run formatter
ruff format src/ tests/

# Run tests
pytest
```

## License

Apache-2.0

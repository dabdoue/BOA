# Contributing to BOA

Thank you for your interest in contributing to BOA! This document provides guidelines for contributing to the project.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/PV-Lab/BOA.git
   cd BOA
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Code Style

We use the following tools to maintain code quality:

- **Black** for code formatting
- **Ruff** for linting
- **MyPy** for type checking

### Running Code Quality Checks

```bash
# Format code
black src/boa tests

# Lint
ruff check src/boa tests

# Type check
mypy src/boa
```

## Testing

We use pytest for testing. All new features should include tests.

### Running Tests

```bash
# All tests
pytest tests/test_boa/ -v

# Specific module
pytest tests/test_boa/server/ -v

# With coverage
pytest tests/test_boa/ --cov=src/boa --cov-report=html
```

### Test Structure

```
tests/test_boa/
├── db/           # Database layer tests
├── spec/         # Specification tests
├── plugins/      # Plugin system tests
├── core/         # Core engine tests
├── server/       # API tests
├── sdk/          # SDK tests
├── benchmarks/   # Benchmark tests
└── cli/          # CLI tests
```

## Pull Request Process

1. **Fork** the repository and create a feature branch
2. **Write tests** for new functionality
3. **Update documentation** if needed
4. **Run all tests** and ensure they pass
5. **Submit a pull request** with a clear description

### PR Checklist

- [ ] Tests pass locally
- [ ] Code is formatted with Black
- [ ] No linting errors (Ruff)
- [ ] Type hints added for new functions
- [ ] Documentation updated if needed
- [ ] CHANGELOG updated for user-facing changes

## Adding New Features

### New Plugin Types

To add a new plugin (sampler, model, acquisition function):

1. Create the plugin in `src/boa/plugins/builtin/`
2. Register it in the module's `__init__.py`
3. Add tests in `tests/test_boa/plugins/`

Example:

```python
# src/boa/plugins/builtin/samplers.py
from boa.plugins.base import Sampler
from boa.plugins.registry import registry

class MyNewSampler(Sampler):
    name = "my_sampler"
    
    def sample(self, n_samples: int, bounds: list) -> list:
        # Implementation
        pass

# Register
registry.register(MyNewSampler)
```

### New API Endpoints

1. Add route in `src/boa/server/routes/`
2. Add schemas in `src/boa/server/schemas.py`
3. Add tests in `tests/test_boa/server/`
4. Update SDK client if needed

### New CLI Commands

1. Add command in `src/boa/cli/main.py`
2. Add tests in `tests/test_boa/cli/`
3. Update documentation

## Architecture Guidelines

- **Single Responsibility**: Each module should have one clear purpose
- **Dependency Injection**: Use FastAPI's dependency system
- **Repository Pattern**: All database access through repositories
- **Plugin System**: Extensibility through the plugin registry
- **Type Hints**: All public functions should have type hints

## Documentation

- Update `README.md` for major features
- Add docstrings to all public functions
- Update API reference for new endpoints
- Add examples for new capabilities

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions
- Contact maintainers for sensitive issues

Thank you for contributing to BOA!






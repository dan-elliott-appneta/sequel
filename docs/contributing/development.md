# Development Guide

## Setting Up the Development Environment

### Prerequisites

- Python 3.11 or higher
- Git
- Google Cloud SDK (for authentication during testing)

### Clone and Install

```bash
# Clone the repository
git clone https://github.com/dan-elliott-appneta/sequel.git
cd sequel

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e .
pip install -r requirements-dev.txt
```

### Development Dependencies

The `requirements-dev.txt` file includes:

- **pytest** - Testing framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage reporting
- **pytest-mock** - Mocking utilities
- **mypy** - Static type checker
- **ruff** - Fast Python linter
- **faker** - Test data generation
- **freezegun** - Time mocking for tests

## Running Tests

### Full Test Suite

```bash
# Run all tests with coverage
pytest --cov

# Run with coverage report
pytest --cov --cov-report=term-missing

# Fail if coverage below 60%
pytest --cov --cov-fail-under=60
```

### Test Specific Files

```bash
# Run tests for a specific file
pytest tests/unit/services/test_auth.py

# Run a specific test
pytest tests/unit/services/test_auth.py::TestAuthManager::test_initialize_success

# Run tests matching a pattern
pytest -k "test_auth"
```

### Test Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

## Code Quality

### Linting

```bash
# Run ruff linter
ruff check src tests

# Auto-fix issues
ruff check --fix src tests
```

### Type Checking

```bash
# Run mypy type checker
mypy src

# Run with strict mode (as used in CI)
mypy --strict src
```

### Running All Checks

```bash
# Run all quality checks at once
ruff check src tests && mypy src && pytest --cov --cov-fail-under=60
```

## Code Style Guidelines

### Python Style

- **Line length**: 100 characters (enforced by ruff)
- **Type hints**: Required for all functions and methods
- **Docstrings**: Required for all public classes and methods
- **Formatting**: Follows PEP 8 (enforced by ruff)

### Example Function

```python
def get_instance(project_id: str, instance_name: str) -> ComputeInstance | None:
    """Get a compute instance by name.

    Args:
        project_id: Google Cloud project ID
        instance_name: Name of the instance

    Returns:
        ComputeInstance if found, None otherwise

    Raises:
        PermissionError: If user lacks permission to view instance
    """
    # Implementation here
    pass
```

### Type Hints

- Use `|` for union types (Python 3.10+ syntax)
- Use `None` for optional return values
- Use `Any` sparingly (mypy strict mode enforces this)

### Docstring Format

- First line: Brief description
- Args: Parameter descriptions
- Returns: Return value description
- Raises: Exception descriptions (if applicable)

## Testing Guidelines

### Test Structure

```python
import pytest
from unittest.mock import MagicMock

class TestMyFeature:
    """Tests for MyFeature."""

    @pytest.mark.asyncio
    async def test_basic_functionality(self) -> None:
        """Test basic functionality works as expected."""
        # Arrange
        service = MyService()

        # Act
        result = await service.do_something()

        # Assert
        assert result is not None
```

### Async Tests

Use `@pytest.mark.asyncio` for async tests:

```python
@pytest.mark.asyncio
async def test_async_operation(self) -> None:
    """Test async operation."""
    result = await my_async_function()
    assert result == expected_value
```

### Mocking

Use `pytest-mock` for mocking:

```python
@pytest.mark.asyncio
async def test_with_mock(self, mocker: Any) -> None:
    """Test with mocked dependencies."""
    mock_client = mocker.patch('module.Client')
    mock_client.return_value.get.return_value = {'key': 'value'}

    result = await function_under_test()
    assert result == expected_value
```

### Coverage Requirements

- Minimum coverage: 60% (enforced by CI)
- Target coverage: 95%+
- All new features must include tests
- Critical paths must have 100% coverage

## Git Workflow

### Branch Naming

- Feature branches: `phase-N-description` (e.g., `phase-9-docs-tests`)
- Bug fixes: `fix-description` (e.g., `fix-auth-timeout`)

### Commit Messages

Follow conventional commits format:

```
type: Brief description

Detailed explanation if needed

Fixes: #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or fixes
- `refactor`: Code refactoring
- `perf`: Performance improvements

### Pull Request Process

1. Create a feature branch from `main`
2. Make changes with tests
3. Ensure all checks pass:
   ```bash
   ruff check src tests
   mypy src
   pytest --cov --cov-fail-under=60
   ```
4. Commit changes
5. Push branch and create pull request
6. Wait for CI checks to pass
7. Request review
8. Merge after approval

## CI/CD

### GitHub Actions Workflows

The repository uses GitHub Actions for continuous integration:

**Lint Job**:
- Runs `ruff check src tests`
- Python 3.11

**Type Check Job**:
- Runs `mypy --no-warn-unused-ignores src`
- Python 3.11

**Test Job**:
- Runs `pytest --cov --cov-fail-under=60`
- Python 3.11 and 3.12
- Uploads coverage to Codecov

### PR Requirements

All pull requests must pass:
- ✅ Lint check (ruff)
- ✅ Type check (mypy)
- ✅ Tests (pytest) on Python 3.11 and 3.12
- ✅ Minimum 60% coverage

## Debugging

### Debug Mode

Run Sequel with debug logging:

```bash
sequel --debug --log-file /tmp/sequel.log

# In another terminal, tail the log
tail -f /tmp/sequel.log
```

### Using Python Debugger

Add breakpoints in code:

```python
import pdb; pdb.set_trace()  # Python debugger

# Or use ipdb for better experience
import ipdb; ipdb.set_trace()  # Requires: pip install ipdb
```

### Testing UI Without GCP Access

Use mocked services in tests:

```python
@pytest.fixture
def mock_gcp_client(mocker):
    """Mock GCP client."""
    return mocker.patch('sequel.services.projects.Client')
```

## Project Structure

```
sequel/
├── src/sequel/          # Source code
│   ├── models/          # Pydantic data models
│   ├── services/        # GCP API wrappers
│   ├── cache/           # Caching layer
│   ├── widgets/         # Textual UI components
│   ├── screens/         # Textual screens
│   ├── utils/           # Utilities
│   ├── app.py           # Main application
│   ├── cli.py           # CLI entry point
│   └── config.py        # Configuration
├── tests/               # Test suite
│   ├── unit/            # Unit tests
│   └── conftest.py      # Pytest fixtures
├── docs/                # Documentation
└── scripts/             # Utility scripts
```

## Next Steps

See [Architecture Guide](architecture.md) for details on adding new features.

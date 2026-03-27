# Testing Guide for MiroFish

This document outlines the testing strategy and procedures for the MiroFish project.

## Table of Contents

- [Backend Testing](#backend-testing)
- [Frontend Testing](#frontend-testing)
- [Running Tests](#running-tests)
- [Coverage Standards](#coverage-standards)
- [Best Practices](#best-practices)

## Backend Testing

### Overview

Backend tests are written using **pytest** with the following tools:
- `pytest` - Test runner
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities

### Structure

```
backend/tests/
├── conftest.py              # Shared pytest fixtures and configuration
├── __init__.py
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── test_file_parser.py
│   └── services/
│       ├── __init__.py
│       └── test_simulation_runner.py
└── api/                     # API tests
    ├── __init__.py
    └── test_simulation.py
```

### Test Coverage

Currently covered modules:

#### Unit Tests

1. **`test_file_parser.py`** - File parsing utilities
   - Text extraction from PDF, Markdown, and text files
   - Encoding detection with fallback strategies
   - Error handling for unsupported formats

2. **`test_simulation_runner.py`** - Simulation runtime classes
   - `AgentAction` dataclass creation and serialization
   - `RoundSummary` creation and data transformation
   - `SimulationRunState` state management
   - Progress calculation and tracking
   - Recent actions list management with max limit

#### API Tests

1. **`test_simulation.py`** - Simulation API utilities
   - Interview prompt optimization
   - Prompt prefix avoidance
   - Content preservation in optimization

### Running Backend Tests

```bash
# Run all backend tests
cd backend
uv run pytest

# Run specific test file
uv run pytest tests/unit/utils/test_file_parser.py

# Run with verbose output
uv run pytest -v

# Run with coverage report
uv run pytest --cov=app --cov-report=html

# Run specific test
uv run pytest tests/unit/utils/test_file_parser.py::TestFileParser::test_extract_text_from_txt_file
```

### Test Configuration

Backend tests are configured in `backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
addopts = "-v --cov=app --cov-report=html --cov-report=term-missing"
asyncio_mode = "auto"
```

## Frontend Testing

### Overview

Frontend tests are written using **Vitest** with the following tools:
- `vitest` - Unit test runner
- `@vue/test-utils` - Vue component testing
- `happy-dom` - Lightweight DOM implementation
- `@vitest/ui` - Visual test interface

### Structure

```
frontend/tests/
├── setup.js                 # Global test setup
├── unit/
│   ├── api.test.js         # API utility tests
│   ├── api.simulation.test.js  # Simulation API tests
│   ├── app.test.js         # App component tests
│   └── utils.test.js       # General utility tests
```

### Test Coverage

Currently covered areas:

1. **`api.test.js`** - API utilities
   - `requestWithRetry` function with exponential backoff
   - Axios service instance configuration
   - Request/response interceptors

2. **`api.simulation.test.js`** - Simulation API functions
   - Create, fetch, and manage simulations
   - Platform-specific operations (Twitter/Reddit)
   - Batch operations (interviews, posts)
   - Pagination and filtering

3. **`app.test.js`** - App component and routing
   - Router configuration
   - Component rendering

4. **`utils.test.js`** - Common utility functions
   - String manipulation
   - Array operations
   - Object utilities
   - Number formatting
   - Date handling

### Running Frontend Tests

```bash
# Run all frontend tests
cd frontend
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with UI
npm run test:ui

# Generate coverage report
npm run test:coverage

# Run specific test file
npm test -- api.test.js

# Run tests matching pattern
npm test -- --grep "requestWithRetry"
```

### Test Configuration

Frontend tests are configured in `frontend/vitest.config.js`:

```javascript
export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./tests/setup.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
    }
  }
})
```

## Running Tests

### Full Test Suite

Run both backend and frontend tests:

```bash
# Backend tests
cd backend && uv run pytest

# Frontend tests
cd frontend && npm test
```

### Continuous Integration

Tests can be integrated into CI/CD pipelines. Example GitHub Actions workflow:

```yaml
name: Tests
on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: cd backend && pip install -e . && pytest

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - run: cd frontend && npm install && npm test
```

## Coverage Standards

### Backend

- **Target**: 70%+ code coverage for critical modules
- **View coverage**: Open `backend/htmlcov/index.html` after running `pytest --cov`

### Frontend

- **Target**: 60%+ code coverage for utilities and core functions
- **View coverage**: Check console output or open generated HTML report

### Minimum Requirements

- **Core API endpoints**: 80%+ coverage
- **Data models**: 100% coverage for dataclasses/models
- **Utilities**: 70%+ coverage
- **Components**: 50%+ coverage (focus on logic, not templates)

## Best Practices

### Writing Tests

1. **Use descriptive names**
   ```python
   # Good
   def test_extract_text_from_pdf_file(self):
       ...

   # Bad
   def test_pdf(self):
       ...
   ```

2. **Follow AAA pattern** (Arrange, Act, Assert)
   ```python
   def test_simulation_progress_calculation(self):
       # Arrange
       state = SimulationRunState(current_round=3, total_rounds=10)

       # Act
       state_dict = state.to_dict()

       # Assert
       assert state_dict["progress_percent"] == 30.0
   ```

3. **Use fixtures for common setup**
   ```python
   @pytest.fixture
   def temp_file():
       # Setup
       ...
       yield temp_path
       # Cleanup
       ...
   ```

4. **Mock external dependencies**
   ```python
   @patch('app.services.external_service')
   def test_with_mock(self, mock_service):
       ...
   ```

### Test Organization

1. **Group related tests in classes**
   ```python
   class TestFileParser:
       def test_extract_text_from_txt(self):
           ...

       def test_extract_text_from_pdf(self):
           ...
   ```

2. **Test edge cases**
   - Empty inputs
   - Null/None values
   - Large datasets
   - Invalid data types

3. **Keep tests independent**
   - Each test should not depend on others
   - Use setUp/tearDown or fixtures for isolation
   - Clean up resources after tests

### Debugging Tests

```bash
# Backend - Stop on first failure
uv run pytest -x

# Backend - Show print statements
uv run pytest -s

# Frontend - Debug mode
npm test -- --inspect-brk

# Frontend - Update snapshots
npm test -- -u
```

## Contributing Tests

When contributing to MiroFish:

1. **Write tests for new features**
   - Minimum 70% coverage for new code
   - Include positive and negative test cases

2. **Update tests when modifying existing code**
   - Ensure backward compatibility tests pass
   - Add tests for bug fixes

3. **Follow the existing test structure**
   - Use the same naming conventions
   - Place tests in appropriate directories

4. **Review test coverage**
   ```bash
   # Backend
   cd backend && uv run pytest --cov=app --cov-report=term-missing

   # Frontend
   cd frontend && npm run test:coverage
   ```

5. **Run full test suite before submitting PR**
   ```bash
   cd backend && uv run pytest
   cd ../frontend && npm test
   ```

## Troubleshooting

### Backend Tests

**Issue**: Tests fail with import errors
```bash
# Solution: Install development dependencies
cd backend
uv sync
```

**Issue**: Async test timeout
```python
# Solution: Use pytest.mark.timeout
@pytest.mark.timeout(10)
async def test_async_function():
    ...
```

### Frontend Tests

**Issue**: Tests fail with module not found
```bash
# Solution: Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Issue**: Mock not working
```javascript
// Solution: Import mocked module after mock declaration
vi.mock('./module')
const { function } = await import('./module')
```

## References

- [pytest documentation](https://docs.pytest.org/)
- [Vitest documentation](https://vitest.dev/)
- [Vue Test Utils](https://test-utils.vuejs.org/)
- [Testing Library best practices](https://testing-library.com/docs/)

---

Last updated: 2024-03-26

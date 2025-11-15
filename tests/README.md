# Cambridge Unit Tests

This directory contains unit tests for the Cambridge webhook application.

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest
```

### Run with Coverage Report

```bash
pytest --cov=app --cov-report=term-missing
```

### Run with HTML Coverage Report

```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in your browser
```

### Run Specific Tests

```bash
# Run a specific test file
pytest tests/test_main.py

# Run a specific test class
pytest tests/test_main.py::TestHealthEndpoints

# Run a specific test function
pytest tests/test_main.py::TestHealthEndpoints::test_root_endpoint

# Run tests matching a keyword
pytest -k "webhook"
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Test Coverage in XML (for CI)

```bash
pytest --cov=app --cov-report=xml
```

## Test Structure

```
tests/
├── __init__.py          # Package marker
├── test_main.py         # Main application tests
└── README.md            # This file
```

## Test Categories

### Health Endpoints Tests (`TestHealthEndpoints`)
- Root endpoint (`/`)
- Health check endpoint (`/health`)

### Frame.io Webhook Tests (`TestFrameIOWebhook`)
- Valid payload handling
- Payload logging verification
- Minimal payload handling
- Invalid JSON handling
- Field extraction
- Response structure

### Security Tests (`TestEndpointSecurity`)
- HTTP method validation
- 404 handling
- Large payload handling
- Empty payload handling

## Writing New Tests

When adding new tests:

1. Follow the existing test structure
2. Use descriptive test names starting with `test_`
3. Group related tests in classes starting with `Test`
4. Add docstrings explaining what each test does
5. Use fixtures for reusable test data
6. Mock external dependencies when needed

Example:

```python
class TestNewFeature:
    """Test the new feature."""

    @pytest.fixture
    def sample_data(self):
        """Sample data for testing."""
        return {"key": "value"}

    def test_new_endpoint(self, sample_data):
        """Test the new endpoint works correctly."""
        response = client.post("/api/v1/new", json=sample_data)
        assert response.status_code == 200
```

## Continuous Integration

Tests run automatically on:
- Every push to any branch
- Every pull request
- Manual workflow dispatch

See `.github/workflows/test.yml` for CI configuration.

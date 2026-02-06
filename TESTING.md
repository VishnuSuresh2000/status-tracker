# Testing Guide

This project includes a comprehensive test suite covering unit tests, integration tests, worker tests, and UI tests.

## Test Structure

```
tests/
├── test_auth.py              # Authentication tests
├── test_integration.py       # Integration tests
├── test_main.py              # Main API endpoint tests
├── test_nested_tasks.py      # Task hierarchy tests
├── test_notifications.py     # Notification system tests
├── test_protect_data.py      # Data protection tests (NEW)
├── test_ui.py                # Basic UI tests
└── test_ui_playwright.py     # Playwright UI tests (NEW)
└── test_worker.py            # Worker/background task tests
```

## Running Tests

### Run All Unit Tests (excluding UI tests)

```bash
source .venv/bin/activate
python -m pytest tests/ --ignore=tests/test_ui.py --ignore=tests/test_ui_playwright.py -v
```

### Run Specific Test Files

```bash
# Data protection tests
python -m pytest tests/test_protect_data.py -v

# API tests
python -m pytest tests/test_main.py -v

# Authentication tests
python -m pytest tests/test_auth.py -v

# Worker tests
python -m pytest tests/test_worker.py -v
```

### Run Playwright UI Tests

**Prerequisites:** Install Playwright browsers (requires root/admin):

```bash
# Install Playwright browsers (run once)
playwright install chromium

# Run UI tests
python -m pytest tests/test_ui_playwright.py -v
```

**Note:** If you cannot install browsers, the Playwright tests will be skipped. All unit tests can run without browser installation.

## Test Coverage

### Unit Tests (96 tests)

1. **test_protect_data.py** (31 tests)
   - Directory creation and management
   - File backup and restore
   - Manifest management
   - Data integrity checks
   - Git operation protection
   - Backup cleanup

2. **test_auth.py** (8 tests)
   - Bearer token authentication
   - Unauthorized access handling
   - Public endpoint access

3. **test_main.py** (16 tests)
   - Task CRUD operations
   - Notification endpoints
   - Phase and todo updates

4. **test_nested_tasks.py** (37 tests)
   - Task creation with phases
   - Progress calculation
   - Status transitions
   - System comments
   - Edge cases

5. **test_notifications.py** (11 tests)
   - Notification creation
   - Read/unread tracking
   - Utility functions

6. **test_worker.py** (3 tests)
   - Task reminder logic
   - Due date calculations
   - Naive datetime handling

### Integration Tests (1 test)

- **test_integration.py**: Full task lifecycle with notifications

### UI Tests (Playwright)

- **test_ui_playwright.py**: Dashboard, task creation, notifications
  - Dashboard functionality
  - Task creation via API and display
  - Task transitions
  - Notification panel
  - Responsive design
  - Error handling

## Continuous Integration

To add to your CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Run Unit Tests
  run: |
    pip install -r requirements.txt
    pytest tests/ --ignore=tests/test_ui.py --ignore=tests/test_ui_playwright.py

- name: Run UI Tests (optional)
  run: |
    playwright install chromium
    pytest tests/test_ui_playwright.py
```

## Test Configuration

Configuration is in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
addopts = "-v --tb=short"
```

## Environment Variables

Tests use the following environment variables:

- `API_AUTH_TOKEN`: Authentication token for protected endpoints (default: "secret-token-123")
- `DATABASE_URL`: Database URL for integration tests
- `REDIS_HOST`: Redis host for background tasks

## Writing New Tests

Follow existing patterns:

1. Use pytest fixtures for setup/teardown
2. Mock external dependencies (Redis, email, etc.)
3. Use descriptive test names
4. Group related tests in classes
5. Include docstrings explaining what is being tested

Example:

```python
def test_feature_description(self):
    """Test what the feature does."""
    # Arrange
    setup_data = create_test_data()
    
    # Act
    result = feature_function(setup_data)
    
    # Assert
    assert result == expected_value
```

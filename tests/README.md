# Test Suite Documentation

Comprehensive pytest test suite for claude-code-control-mcp with 82% code coverage.

## Test Results

- **Total Tests**: 91 tests
- **Coverage**: 82.19% (exceeds 80% target)
- **Status**: All tests passing

### Coverage Breakdown

| Module | Coverage |
|--------|----------|
| executor.py | 94% |
| file_tracker.py | 92% |
| server.py | 91% |

## Test Structure

### `conftest.py` - Fixtures and Configuration
Provides comprehensive fixtures for all tests:

- **Mock Fixtures**:
  - `mock_anthropic_client` - Mock Anthropic API client
  - `mock_anthropic_tool_response` - Tool use response
  - `mock_anthropic_end_response` - Completion response
  - `mock_subprocess_success/error` - Subprocess execution mocks
  - `mock_file_tracker` - FileTracker instance mock

- **Test Data Fixtures**:
  - `temp_dir` - Temporary directory for testing
  - `sample_files` - Sample file structure
  - `sample_task_result` - Example task execution result
  - `mcp_tool_arguments` - MCP tool call arguments

- **Environment Fixtures**:
  - `api_key` - Test API key
  - `set_api_key_env` - Environment variable setup
  - `reset_global_state` - Cleanup between tests

### `test_file_tracker.py` - FileTracker Tests (12 tests)

Tests for file change tracking functionality:

- **Initialization**: FileTracker setup
- **Hashing**: File hash calculation and validation
- **Tracking**: File read/write tracking
- **Change Detection**:
  - File modifications
  - File creation
  - File deletion
- **Summary Generation**: Change summary and detailed changes
- **Reset**: State cleanup

### `test_executor.py` - TaskExecutor Tests (21 tests)

Tests for Claude AI task execution:

- **Initialization**:
  - With API key
  - From environment
  - Error handling without key

- **Configuration**:
  - System prompt building
  - Tool definitions

- **Tool Handlers** (async tests):
  - `read_file` - File reading
  - `write_file` - File creation/writing
  - `edit_file` - File modification
  - `list_files` - Directory listing
  - `search_code` - Code search
  - `run_command` - Command execution

- **Task Execution**:
  - Successful execution
  - Tool use iteration
  - Max iteration handling
  - API error handling
  - History tracking

### `test_server.py` - MCP Server Tests (58 tests)

Tests for MCP server endpoints:

- **Server Initialization**:
  - Executor initialization success/failure
  - Environment variable handling

- **Tool Listing**:
  - Available tools
  - Schema validation

- **MCP Endpoints**:

  #### `execute_code_task`
  - Successful execution
  - Uninitialized executor handling

  #### `read_codebase`
  - File reading with patterns
  - Max files limit enforcement
  - Content truncation (10KB limit)

  #### `search_code`
  - Case-sensitive search
  - Case-insensitive search
  - Error handling

  #### `modify_files`
  - File writing
  - File editing
  - File deletion
  - Error handling

  #### `run_commands`
  - Successful execution
  - Command errors
  - Exception handling

  #### `get_execution_status`
  - Status without history
  - Status with history

- **Error Handling**:
  - Unknown tool calls
  - Exception handling

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test File
```bash
pytest tests/test_executor.py
pytest tests/test_file_tracker.py
pytest tests/test_server.py
```

### Run Specific Test Class
```bash
pytest tests/test_executor.py::TestTaskExecutor
pytest tests/test_server.py::TestModifyFiles
```

### Run Specific Test
```bash
pytest tests/test_executor.py::TestTaskExecutor::test_init_with_api_key
```

### Run with Coverage Report
```bash
pytest tests/ --cov=. --cov-report=html
```

View coverage report: `open htmlcov/index.html`

### Run Verbose
```bash
pytest tests/ -v
```

### Run with Output
```bash
pytest tests/ -s
```

## Test Patterns

### Async Tests
Uses `pytest-asyncio` for async function testing:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### Mocking Patterns

#### Mock Anthropic API
```python
with patch.object(executor.client.messages, 'create', return_value=mock_response):
    result = await executor.execute_task(...)
```

#### Mock Subprocess
```python
with patch('subprocess.run', return_value=mock_subprocess_success):
    result = await executor._handle_tool_use('run_command', ...)
```

### Fixture Usage
```python
def test_with_fixtures(temp_dir, sample_files, api_key):
    # temp_dir is a Path object
    # sample_files is a dict of created files
    # api_key is a test API key
    pass
```

## Coverage Configuration

Coverage settings in `pytest.ini`:

- **Minimum Coverage**: 80%
- **Branch Coverage**: Enabled
- **Exclusions**:
  - Tests directory
  - Virtual environments
  - Example files
  - Installation scripts

## CI/CD Integration

Add to `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/ --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v4
```

## Extending Tests

### Adding New Tests

1. Create test function in appropriate file
2. Use descriptive name: `test_<functionality>_<scenario>`
3. Add docstring explaining what's tested
4. Use fixtures for common setup
5. Assert actual functionality, not just mock calls

Example:
```python
def test_new_feature_success(temp_dir, mock_client):
    """Test new feature works correctly"""
    # Arrange
    feature = NewFeature()

    # Act
    result = feature.execute()

    # Assert
    assert result.success is True
    assert result.data is not None
```

### Adding New Fixtures

Add to `conftest.py`:

```python
@pytest.fixture
def new_fixture():
    """Provide test data for new feature"""
    data = {"key": "value"}
    yield data
    # Cleanup if needed
```

## Test Quality Standards

- No placeholder tests
- Every test verifies real functionality
- Mock external dependencies (API, subprocess)
- Use temporary directories for file operations
- Clean up resources in fixtures
- Test both success and error paths
- Use descriptive test names and docstrings
- Maintain 80%+ coverage

## Dependencies

Test dependencies in `requirements-dev.txt`:

- `pytest>=8.0.0` - Test framework
- `pytest-asyncio>=0.23.0` - Async test support
- `pytest-cov>=4.1.0` - Coverage reporting
- `pytest-mock>=3.12.0` - Mocking utilities
- `coverage[toml]>=7.4.0` - Coverage analysis

## Troubleshooting

### Tests Failing

1. Check API key is set: `export ANTHROPIC_API_KEY=test-key`
2. Verify dependencies: `pip install -r requirements-dev.txt`
3. Clear cache: `pytest --cache-clear`
4. Run single test: `pytest tests/test_file.py::test_name -v`

### Coverage Not Meeting Threshold

1. Run with coverage details: `pytest --cov=. --cov-report=term-missing`
2. Check missing lines in report
3. Add tests for uncovered code paths
4. Update `pytest.ini` if exclusions needed

### Import Errors

1. Install package in development mode: `pip install -e .`
2. Check PYTHONPATH includes project root
3. Verify all `__init__.py` files exist

## Maintenance

- Run tests before committing: `pytest tests/`
- Update fixtures when API changes
- Keep test coverage above 80%
- Add tests for new features
- Update documentation for new patterns

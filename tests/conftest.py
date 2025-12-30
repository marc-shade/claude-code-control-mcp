"""Pytest fixtures and configuration for claude-code-control-mcp tests"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, MagicMock
import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_files(temp_dir):
    """Create sample files for testing"""
    files = {
        'main.py': 'def main():\n    print("Hello")\n',
        'test.py': 'def test_main():\n    assert True\n',
        'README.md': '# Test Project\n',
        'src/utils.py': 'def helper():\n    return 42\n',
    }

    for path, content in files.items():
        file_path = temp_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

    return files


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client"""
    mock = MagicMock()

    # Mock response structure
    mock_response = MagicMock()
    mock_response.content = []
    mock_response.stop_reason = "end_turn"

    mock.messages.create = MagicMock(return_value=mock_response)

    return mock


@pytest.fixture
def mock_anthropic_tool_response():
    """Mock Anthropic API response with tool use"""
    mock_response = MagicMock()

    # Create mock tool use block
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "read_file"
    tool_block.input = {"path": "test.py"}
    tool_block.id = "tool_123"

    # Create mock text block
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "I will read the file first."

    mock_response.content = [text_block, tool_block]
    mock_response.stop_reason = "tool_use"

    return mock_response


@pytest.fixture
def mock_anthropic_end_response():
    """Mock Anthropic API response indicating completion"""
    mock_response = MagicMock()

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "Task completed successfully."

    mock_response.content = [text_block]
    mock_response.stop_reason = "end_turn"

    return mock_response


@pytest.fixture
def mock_subprocess_success():
    """Mock successful subprocess execution"""
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = "Command executed successfully\n"
    mock.stderr = ""
    return mock


@pytest.fixture
def mock_subprocess_error():
    """Mock failed subprocess execution"""
    mock = MagicMock()
    mock.returncode = 1
    mock.stdout = ""
    mock.stderr = "Error: command failed\n"
    return mock


@pytest.fixture
def api_key():
    """Provide test API key"""
    return "sk-ant-test-key-12345"


@pytest.fixture
def set_api_key_env(api_key):
    """Set ANTHROPIC_API_KEY environment variable"""
    original = os.environ.get("ANTHROPIC_API_KEY")
    os.environ["ANTHROPIC_API_KEY"] = api_key
    yield api_key
    if original:
        os.environ["ANTHROPIC_API_KEY"] = original
    else:
        os.environ.pop("ANTHROPIC_API_KEY", None)


@pytest.fixture
def mock_file_tracker():
    """Mock FileTracker instance"""
    tracker = MagicMock()
    tracker.track_file = MagicMock()
    tracker.record_read = MagicMock()
    tracker.check_changes = MagicMock(return_value=[])
    tracker.get_summary = MagicMock(return_value={
        'total_changes': 0,
        'files_created': 0,
        'files_modified': 0,
        'files_deleted': 0,
        'files_read': 0,
        'created_files': [],
        'modified_files': [],
        'deleted_files': [],
        'read_files': [],
        'detailed_changes': []
    })
    return tracker


@pytest.fixture
def sample_task_result():
    """Sample task execution result"""
    return {
        "success": True,
        "task_description": "Create a test file",
        "working_directory": "/tmp/test",
        "iterations": 3,
        "tool_uses": [
            {
                "tool": "write_file",
                "input": {"path": "test.py", "content": "print('test')"},
                "result": "Successfully wrote file"
            }
        ],
        "file_changes": {
            "total_changes": 1,
            "files_created": 1,
            "files_modified": 0,
            "files_deleted": 0,
            "created_files": ["test.py"]
        },
        "duration_seconds": 2.5,
        "timestamp": "2024-01-01T00:00:00",
        "final_message": "Task completed successfully"
    }


@pytest.fixture
def mcp_tool_arguments():
    """Sample MCP tool call arguments"""
    return {
        "execute_code_task": {
            "task_description": "Create a hello world script",
            "working_directory": "/tmp/test",
            "context_files": ["README.md"],
            "max_iterations": 10
        },
        "read_codebase": {
            "patterns": ["*.py"],
            "working_directory": "/tmp/test",
            "max_files": 50
        },
        "search_code": {
            "query": "def main",
            "working_directory": "/tmp/test",
            "file_pattern": "*.py",
            "case_sensitive": True,
            "max_results": 100
        },
        "modify_files": {
            "changes": [
                {
                    "path": "test.py",
                    "action": "write",
                    "content": "print('hello')"
                }
            ],
            "working_directory": "/tmp/test"
        },
        "run_commands": {
            "commands": ["echo 'test'", "ls -la"],
            "working_directory": "/tmp/test",
            "timeout": 30
        },
        "get_execution_status": {
            "include_history": True
        }
    }


@pytest.fixture
def mock_text_content():
    """Factory for creating TextContent mocks"""
    def _create(text: str):
        from unittest.mock import MagicMock
        content = MagicMock()
        content.type = "text"
        content.text = text
        return content
    return _create


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before each test"""
    yield
    # Cleanup happens after test
    import sys
    if 'server' in sys.modules:
        server = sys.modules['server']
        server.executor = None
        server.current_execution = None


@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

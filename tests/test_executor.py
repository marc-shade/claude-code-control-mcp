"""Tests for executor.py"""

import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
from executor import TaskExecutor


class TestTaskExecutor:
    """Test TaskExecutor class"""

    def test_init_with_api_key(self, api_key):
        """Test initialization with API key"""
        executor = TaskExecutor(api_key=api_key)
        assert executor.api_key == api_key
        assert executor.model == "claude-sonnet-4-5-20250929"
        assert len(executor.execution_history) == 0

    def test_init_from_env(self, set_api_key_env):
        """Test initialization from environment variable"""
        executor = TaskExecutor()
        assert executor.api_key == set_api_key_env

    def test_init_no_api_key(self):
        """Test initialization fails without API key"""
        # Remove env var if set
        old_key = os.environ.pop("ANTHROPIC_API_KEY", None)

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not found"):
            TaskExecutor()

        # Restore if it existed
        if old_key:
            os.environ["ANTHROPIC_API_KEY"] = old_key

    def test_build_system_prompt(self, api_key):
        """Test system prompt building"""
        executor = TaskExecutor(api_key=api_key)
        working_dir = "/tmp/test"
        context_files = ["main.py", "utils.py"]

        prompt = executor._build_system_prompt(working_dir, context_files)

        assert working_dir in prompt
        assert "main.py" in prompt
        assert "utils.py" in prompt
        assert "coding assistant" in prompt.lower()

    def test_build_tools(self, api_key):
        """Test tool definitions"""
        executor = TaskExecutor(api_key=api_key)
        tools = executor._build_tools()

        assert len(tools) == 6
        tool_names = [t["name"] for t in tools]

        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "edit_file" in tool_names
        assert "list_files" in tool_names
        assert "search_code" in tool_names
        assert "run_command" in tool_names

    @pytest.mark.asyncio
    async def test_handle_tool_read_file(self, api_key, temp_dir, sample_files, mock_file_tracker):
        """Test read_file tool execution"""
        executor = TaskExecutor(api_key=api_key)

        result = await executor._handle_tool_use(
            "read_file",
            {"path": "test.py"},
            temp_dir,
            mock_file_tracker
        )

        assert "File content" in result
        assert "def test_main" in result
        mock_file_tracker.record_read.assert_called_once_with("test.py")

    @pytest.mark.asyncio
    async def test_handle_tool_write_file(self, api_key, temp_dir, mock_file_tracker):
        """Test write_file tool execution"""
        executor = TaskExecutor(api_key=api_key)
        content = "print('hello world')\n"

        result = await executor._handle_tool_use(
            "write_file",
            {"path": "new_file.py", "content": content},
            temp_dir,
            mock_file_tracker
        )

        assert "Successfully wrote" in result
        assert (temp_dir / "new_file.py").exists()
        assert (temp_dir / "new_file.py").read_text() == content
        mock_file_tracker.track_file.assert_called_once_with("new_file.py")

    @pytest.mark.asyncio
    async def test_handle_tool_edit_file(self, api_key, temp_dir, sample_files, mock_file_tracker):
        """Test edit_file tool execution"""
        executor = TaskExecutor(api_key=api_key)

        result = await executor._handle_tool_use(
            "edit_file",
            {
                "path": "test.py",
                "old_content": "assert True",
                "new_content": "assert False"
            },
            temp_dir,
            mock_file_tracker
        )

        assert "Successfully edited" in result
        content = (temp_dir / "test.py").read_text()
        assert "assert False" in content
        assert "assert True" not in content
        mock_file_tracker.track_file.assert_called_once_with("test.py")

    @pytest.mark.asyncio
    async def test_handle_tool_edit_file_not_found(self, api_key, temp_dir, sample_files, mock_file_tracker):
        """Test edit_file with content not found"""
        executor = TaskExecutor(api_key=api_key)

        result = await executor._handle_tool_use(
            "edit_file",
            {
                "path": "test.py",
                "old_content": "nonexistent content",
                "new_content": "new content"
            },
            temp_dir,
            mock_file_tracker
        )

        assert "Error" in result
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_handle_tool_list_files(self, api_key, temp_dir, sample_files, mock_file_tracker):
        """Test list_files tool execution"""
        executor = TaskExecutor(api_key=api_key)

        result = await executor._handle_tool_use(
            "list_files",
            {"path": ".", "pattern": "*.py", "recursive": False},
            temp_dir,
            mock_file_tracker
        )

        assert "Found" in result
        assert "test.py" in result
        assert "main.py" in result

    @pytest.mark.asyncio
    async def test_handle_tool_list_files_recursive(self, api_key, temp_dir, sample_files, mock_file_tracker):
        """Test list_files with recursive option"""
        executor = TaskExecutor(api_key=api_key)

        result = await executor._handle_tool_use(
            "list_files",
            {"path": ".", "pattern": "*.py", "recursive": True},
            temp_dir,
            mock_file_tracker
        )

        assert "utils.py" in result

    @pytest.mark.asyncio
    async def test_handle_tool_search_code(self, api_key, temp_dir, sample_files, mock_file_tracker):
        """Test search_code tool execution"""
        executor = TaskExecutor(api_key=api_key)

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout="test.py:1:def test_main():",
                stderr=""
            )

            result = await executor._handle_tool_use(
                "search_code",
                {"pattern": "def test", "path": ".", "case_sensitive": True},
                temp_dir,
                mock_file_tracker
            )

            assert "Search results" in result or "No matches" in result

    @pytest.mark.asyncio
    async def test_handle_tool_run_command(self, api_key, temp_dir, mock_file_tracker, mock_subprocess_success):
        """Test run_command tool execution"""
        executor = TaskExecutor(api_key=api_key)

        with patch('subprocess.run', return_value=mock_subprocess_success):
            result = await executor._handle_tool_use(
                "run_command",
                {"command": "echo 'test'", "timeout": 30},
                temp_dir,
                mock_file_tracker
            )

            assert "Exit code: 0" in result
            assert "Command executed successfully" in result

    @pytest.mark.asyncio
    async def test_handle_tool_run_command_error(self, api_key, temp_dir, mock_file_tracker, mock_subprocess_error):
        """Test run_command with command failure"""
        executor = TaskExecutor(api_key=api_key)

        with patch('subprocess.run', return_value=mock_subprocess_error):
            result = await executor._handle_tool_use(
                "run_command",
                {"command": "false", "timeout": 30},
                temp_dir,
                mock_file_tracker
            )

            assert "Exit code: 1" in result

    @pytest.mark.asyncio
    async def test_handle_tool_unknown(self, api_key, temp_dir, mock_file_tracker):
        """Test handling unknown tool"""
        executor = TaskExecutor(api_key=api_key)

        result = await executor._handle_tool_use(
            "unknown_tool",
            {},
            temp_dir,
            mock_file_tracker
        )

        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_execute_task_success(self, api_key, temp_dir, mock_anthropic_end_response):
        """Test successful task execution"""
        executor = TaskExecutor(api_key=api_key)

        with patch.object(executor.client.messages, 'create', return_value=mock_anthropic_end_response):
            result = await executor.execute_task(
                task_description="Create a test file",
                working_directory=str(temp_dir),
                max_iterations=5
            )

            assert result["success"] is True
            assert "task_description" in result
            assert "iterations" in result
            assert "duration_seconds" in result
            assert len(executor.execution_history) == 1

    @pytest.mark.asyncio
    async def test_execute_task_with_tool_use(self, api_key, temp_dir, sample_files,
                                             mock_anthropic_tool_response, mock_anthropic_end_response):
        """Test task execution with tool usage"""
        executor = TaskExecutor(api_key=api_key)

        # Mock sequence: tool use then end
        responses = [mock_anthropic_tool_response, mock_anthropic_end_response]

        with patch.object(executor.client.messages, 'create', side_effect=responses):
            result = await executor.execute_task(
                task_description="Read and analyze test.py",
                working_directory=str(temp_dir),
                max_iterations=5
            )

            assert result["success"] is True
            assert result["iterations"] == 2
            assert len(result["tool_uses"]) > 0

    @pytest.mark.asyncio
    async def test_execute_task_max_iterations(self, api_key, temp_dir, mock_anthropic_tool_response):
        """Test task execution hitting max iterations"""
        executor = TaskExecutor(api_key=api_key)

        # Always return tool use to hit max iterations
        with patch.object(executor.client.messages, 'create', return_value=mock_anthropic_tool_response):
            result = await executor.execute_task(
                task_description="Infinite task",
                working_directory=str(temp_dir),
                max_iterations=3
            )

            assert result["iterations"] == 3

    @pytest.mark.asyncio
    async def test_execute_task_api_error(self, api_key, temp_dir):
        """Test task execution with API error"""
        executor = TaskExecutor(api_key=api_key)

        with patch.object(executor.client.messages, 'create', side_effect=Exception("API Error")):
            result = await executor.execute_task(
                task_description="Test task",
                working_directory=str(temp_dir),
                max_iterations=5
            )

            assert result["success"] is False
            assert "error" in result
            assert "API Error" in result["error"]

    def test_extract_final_text(self, api_key, mock_anthropic_end_response):
        """Test extracting final text from message"""
        executor = TaskExecutor(api_key=api_key)

        message = {
            "role": "assistant",
            "content": mock_anthropic_end_response.content
        }

        text = executor._extract_final_text(message)
        assert "completed" in text.lower()

    def test_get_execution_history(self, api_key, sample_task_result):
        """Test getting execution history"""
        executor = TaskExecutor(api_key=api_key)
        executor.execution_history.append(sample_task_result)

        history = executor.get_execution_history()
        assert len(history) == 1
        assert history[0] == sample_task_result

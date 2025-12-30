"""Tests for server.py MCP endpoints"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path


class TestServerInitialization:
    """Test server initialization and setup"""

    def test_init_executor_success(self, set_api_key_env):
        """Test successful executor initialization"""
        from server import init_executor

        init_executor()

        from server import executor
        assert executor is not None
        assert executor.api_key == set_api_key_env

    def test_init_executor_no_api_key(self):
        """Test executor initialization without API key"""
        from server import init_executor

        # Remove API key
        old_key = os.environ.pop("ANTHROPIC_API_KEY", None)

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            init_executor()

        # Restore
        if old_key:
            os.environ["ANTHROPIC_API_KEY"] = old_key


class TestListTools:
    """Test list_tools endpoint"""

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing available tools"""
        from server import list_tools

        tools = await list_tools()

        assert len(tools) == 6
        tool_names = [t.name for t in tools]

        assert "execute_code_task" in tool_names
        assert "read_codebase" in tool_names
        assert "search_code" in tool_names
        assert "modify_files" in tool_names
        assert "run_commands" in tool_names
        assert "get_execution_status" in tool_names

    @pytest.mark.asyncio
    async def test_tool_schemas(self):
        """Test that all tools have proper schemas"""
        from server import list_tools

        tools = await list_tools()

        for tool in tools:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'inputSchema')
            assert 'type' in tool.inputSchema
            assert 'properties' in tool.inputSchema


class TestExecuteCodeTask:
    """Test execute_code_task endpoint"""

    @pytest.mark.asyncio
    async def test_execute_code_task_success(self, set_api_key_env, mcp_tool_arguments, sample_task_result):
        """Test successful code task execution"""
        from server import call_tool, init_executor

        init_executor()

        # Mock the executor
        with patch('server.executor') as mock_executor:
            mock_executor.execute_task = AsyncMock(return_value=sample_task_result)

            result = await call_tool("execute_code_task", mcp_tool_arguments["execute_code_task"])

            assert len(result) == 1
            content = json.loads(result[0].text)
            assert content["success"] is True
            assert "tool_uses" in content

    @pytest.mark.asyncio
    async def test_execute_code_task_no_executor(self):
        """Test execute_code_task with uninitialized executor"""
        from server import call_tool
        import server

        # Ensure executor is None
        server.executor = None

        args = {"task_description": "Test task"}
        result = await call_tool("execute_code_task", args)

        assert len(result) == 1
        content = json.loads(result[0].text)
        assert "error" in content
        assert "not initialized" in content["error"]


class TestReadCodebase:
    """Test read_codebase endpoint"""

    @pytest.mark.asyncio
    async def test_read_codebase_success(self, temp_dir, sample_files):
        """Test reading codebase files"""
        from server import call_tool

        args = {
            "patterns": ["*.py"],
            "working_directory": str(temp_dir),
            "max_files": 50
        }

        result = await call_tool("read_codebase", args)

        assert len(result) == 1
        content = json.loads(result[0].text)
        assert "files_read" in content
        assert content["files_read"] > 0
        assert "files" in content

    @pytest.mark.asyncio
    async def test_read_codebase_max_files_limit(self, temp_dir, sample_files):
        """Test max_files limit enforcement"""
        from server import call_tool

        args = {
            "patterns": ["*.py"],
            "working_directory": str(temp_dir),
            "max_files": 1
        }

        result = await call_tool("read_codebase", args)

        content = json.loads(result[0].text)
        assert content["files_read"] <= 1

    @pytest.mark.asyncio
    async def test_read_codebase_content_truncation(self, temp_dir):
        """Test that large files are truncated"""
        from server import call_tool

        # Create a large file
        large_file = temp_dir / "large.py"
        large_file.write_text("x" * 20000)

        args = {
            "patterns": ["large.py"],
            "working_directory": str(temp_dir)
        }

        result = await call_tool("read_codebase", args)

        content = json.loads(result[0].text)
        if content["files_read"] > 0:
            file_content = content["files"][0]["content"]
            assert len(file_content) <= 10000


class TestSearchCode:
    """Test search_code endpoint"""

    @pytest.mark.asyncio
    async def test_search_code_success(self, temp_dir, sample_files):
        """Test code search"""
        from server import call_tool

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout="test.py:1:def test_main():\n",
                stderr=""
            )

            args = {
                "query": "def test",
                "working_directory": str(temp_dir),
                "file_pattern": "*.py",
                "case_sensitive": True
            }

            result = await call_tool("search_code", args)

            assert len(result) == 1
            content = json.loads(result[0].text)
            assert "query" in content
            assert "matches" in content

    @pytest.mark.asyncio
    async def test_search_code_case_insensitive(self, temp_dir):
        """Test case-insensitive search"""
        from server import call_tool

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="")

            args = {
                "query": "DEF",
                "working_directory": str(temp_dir),
                "case_sensitive": False
            }

            await call_tool("search_code", args)

            # Verify -i flag was used
            call_args = mock_run.call_args[0][0]
            assert "-i" in call_args

    @pytest.mark.asyncio
    async def test_search_code_error_handling(self, temp_dir):
        """Test search error handling"""
        from server import call_tool

        with patch('subprocess.run', side_effect=Exception("Search failed")):
            args = {
                "query": "test",
                "working_directory": str(temp_dir)
            }

            result = await call_tool("search_code", args)

            content = json.loads(result[0].text)
            assert "error" in content


class TestModifyFiles:
    """Test modify_files endpoint"""

    @pytest.mark.asyncio
    async def test_modify_files_write(self, temp_dir):
        """Test writing files"""
        from server import call_tool

        args = {
            "changes": [
                {
                    "path": "new_file.py",
                    "action": "write",
                    "content": "print('hello')\n"
                }
            ],
            "working_directory": str(temp_dir)
        }

        result = await call_tool("modify_files", args)

        content = json.loads(result[0].text)
        assert "modifications" in content
        assert content["modifications"][0]["status"] == "written"
        assert (temp_dir / "new_file.py").exists()

    @pytest.mark.asyncio
    async def test_modify_files_edit(self, temp_dir, sample_files):
        """Test editing files"""
        from server import call_tool

        args = {
            "changes": [
                {
                    "path": "test.py",
                    "action": "edit",
                    "old_content": "assert True",
                    "new_content": "assert False"
                }
            ],
            "working_directory": str(temp_dir)
        }

        result = await call_tool("modify_files", args)

        content = json.loads(result[0].text)
        assert content["modifications"][0]["status"] == "edited"

        # Verify edit
        edited_content = (temp_dir / "test.py").read_text()
        assert "assert False" in edited_content

    @pytest.mark.asyncio
    async def test_modify_files_delete(self, temp_dir, sample_files):
        """Test deleting files"""
        from server import call_tool

        args = {
            "changes": [
                {
                    "path": "test.py",
                    "action": "delete"
                }
            ],
            "working_directory": str(temp_dir)
        }

        result = await call_tool("modify_files", args)

        content = json.loads(result[0].text)
        assert content["modifications"][0]["status"] == "deleted"
        assert not (temp_dir / "test.py").exists()

    @pytest.mark.asyncio
    async def test_modify_files_error_handling(self, temp_dir):
        """Test error handling in file modifications"""
        from server import call_tool

        args = {
            "changes": [
                {
                    "path": "nonexistent.py",
                    "action": "edit",
                    "old_content": "test",
                    "new_content": "new"
                }
            ],
            "working_directory": str(temp_dir)
        }

        result = await call_tool("modify_files", args)

        content = json.loads(result[0].text)
        assert content["modifications"][0]["status"] == "error"


class TestRunCommands:
    """Test run_commands endpoint"""

    @pytest.mark.asyncio
    async def test_run_commands_success(self, temp_dir, mock_subprocess_success):
        """Test running commands successfully"""
        from server import call_tool

        with patch('subprocess.run', return_value=mock_subprocess_success):
            args = {
                "commands": ["echo 'test'", "ls"],
                "working_directory": str(temp_dir),
                "timeout": 30
            }

            result = await call_tool("run_commands", args)

            content = json.loads(result[0].text)
            assert "command_results" in content
            assert len(content["command_results"]) == 2
            assert content["command_results"][0]["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_run_commands_error(self, temp_dir, mock_subprocess_error):
        """Test command execution errors"""
        from server import call_tool

        with patch('subprocess.run', return_value=mock_subprocess_error):
            args = {
                "commands": ["false"],
                "working_directory": str(temp_dir)
            }

            result = await call_tool("run_commands", args)

            content = json.loads(result[0].text)
            assert content["command_results"][0]["exit_code"] == 1

    @pytest.mark.asyncio
    async def test_run_commands_exception(self, temp_dir):
        """Test handling command exceptions"""
        from server import call_tool

        with patch('subprocess.run', side_effect=Exception("Command failed")):
            args = {
                "commands": ["test"],
                "working_directory": str(temp_dir)
            }

            result = await call_tool("run_commands", args)

            content = json.loads(result[0].text)
            assert "error" in content["command_results"][0]


class TestGetExecutionStatus:
    """Test get_execution_status endpoint"""

    @pytest.mark.asyncio
    async def test_get_execution_status_no_history(self, set_api_key_env):
        """Test getting status without execution history"""
        from server import call_tool, init_executor

        init_executor()

        args = {"include_history": False}
        result = await call_tool("get_execution_status", args)

        content = json.loads(result[0].text)
        assert "executor_initialized" in content
        assert content["executor_initialized"] is True

    @pytest.mark.asyncio
    async def test_get_execution_status_with_history(self, set_api_key_env, sample_task_result):
        """Test getting status with execution history"""
        from server import call_tool, init_executor, executor

        init_executor()

        # Mock history
        with patch('server.executor') as mock_executor:
            mock_executor.get_execution_history = MagicMock(return_value=[sample_task_result])

            args = {"include_history": True}
            result = await call_tool("get_execution_status", args)

            content = json.loads(result[0].text)
            assert "execution_history" in content


class TestErrorHandling:
    """Test error handling in server"""

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Test calling unknown tool"""
        from server import call_tool

        result = await call_tool("unknown_tool", {})

        content = json.loads(result[0].text)
        assert "error" in content
        assert "Unknown tool" in content["error"]

    @pytest.mark.asyncio
    async def test_exception_in_tool(self, temp_dir):
        """Test exception handling in tool execution"""
        from server import call_tool

        # Trigger exception with invalid directory
        args = {
            "patterns": ["*.py"],
            "working_directory": "/nonexistent/path/that/does/not/exist"
        }

        result = await call_tool("read_codebase", args)

        # Should handle gracefully
        assert len(result) == 1

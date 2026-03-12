"""Smoke tests for SVP MCP server."""

import pytest


class TestMcpServerSmoke:
    """Smoke tests to verify MCP server can be imported and instantiated."""

    def test_server_module_imports(self):
        """Verify svp_mcp.server module can be imported."""
        import svp_mcp.server

        assert svp_mcp.server is not None

    def test_mcp_object_exists(self):
        """Verify FastMCP server object exists."""
        from svp_mcp.server import mcp

        assert mcp is not None

    def test_main_function_exists(self):
        """Verify main entry point exists."""
        from svp_mcp.server import main

        assert callable(main)

    def test_tools_are_registered(self):
        """Verify MCP tools are registered on the server."""
        from svp_mcp.server import mcp

        tool_names = [tool.name for tool in mcp._tool_manager._tools.values()]
        expected_tools = [
            "load_state_tool",
            "validate_state_tool",
            "route_tool",
            "dispatch_status_tool",
            "format_action_block_tool",
            "save_state_tool",
            "dispatch_gate_response_tool",
            "dispatch_agent_status_tool",
            "dispatch_command_status_tool",
        ]
        for tool in expected_tools:
            assert tool in tool_names, f"Tool {tool} not found in {tool_names}"

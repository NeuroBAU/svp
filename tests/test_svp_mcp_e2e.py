"""End-to-end tests for MCP server tools using real fixtures."""

from pathlib import Path
import pytest

from svp_core import create_initial_state, save_state, load_state


@pytest.fixture
def svp_project(tmp_path):
    """Create minimal SVP project with initial state."""
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir()

    state = create_initial_state("test_proj")
    save_state(state, tmp_path)

    return tmp_path


class TestMcpEndToEnd:
    """End-to-end tests for MCP tool chain."""

    def test_load_route_dispatch_gate_save_flow(self, svp_project):
        """Test full flow: load -> route -> dispatch_gate_response -> save -> verify."""
        from svp_mcp.server import (
            load_state_tool,
            route_tool,
            dispatch_gate_response_tool,
            save_state_tool,
        )

        result = load_state_tool(str(svp_project))
        assert result["stage"] == "0"
        assert result["sub_stage"] == "hook_activation"

        action = route_tool(str(svp_project))
        assert "ACTION" in action
        assert action["ACTION"] == "human_gate"

        dispatch_result = dispatch_gate_response_tool(
            str(svp_project),
            gate_id="gate_0_1_hook_activation",
            response="HOOKS ACTIVATED",
        )
        import sys

        sys.stderr.write(f"dispatch_result: {dispatch_result}\n")
        assert dispatch_result["ok"] is True
        assert dispatch_result["state"]["sub_stage"] == "project_context"

        save_result = save_state_tool(
            str(svp_project),
            dispatch_result["state"],
        )
        assert save_result["ok"] is True

        reload = load_state_tool(str(svp_project))
        assert reload["stage"] == "0"
        assert reload["sub_stage"] == "project_context"

    def test_load_route_save_flow(self, svp_project):
        """Test minimal flow: load -> route -> save."""
        from svp_mcp.server import (
            load_state_tool,
            route_tool,
            save_state_tool,
        )

        result = load_state_tool(str(svp_project))
        assert result["stage"] == "0"

        action = route_tool(str(svp_project))
        assert "ACTION" in action

        save_result = save_state_tool(
            str(svp_project),
            result,
        )
        assert save_result["ok"] is True

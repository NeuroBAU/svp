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

    def test_apply_next_action_tool_flow(self, svp_project):
        """Test apply_next_action_tool for gate, agent, and command actions."""
        from svp_mcp.server import (
            load_state_tool,
            apply_next_action_tool,
            save_state_tool,
        )

        initial = load_state_tool(str(svp_project))
        assert initial["sub_stage"] == "hook_activation"

        # 1) human_gate apply (no autosave)
        gate_apply = apply_next_action_tool(
            str(svp_project),
            response="HOOKS ACTIVATED",
            expected_action_type="human_gate",
        )
        assert gate_apply["ok"] is True
        assert gate_apply["applied_action_type"] == "human_gate"
        assert gate_apply["used_tool"] == "dispatch_gate_response_tool"
        assert gate_apply["state"]["sub_stage"] == "project_context"

        unchanged = load_state_tool(str(svp_project))
        assert unchanged["sub_stage"] == "hook_activation"

        save_gate = save_state_tool(str(svp_project), gate_apply["state"])
        assert save_gate["ok"] is True

        # 2) invoke_agent apply (setup_agent)
        agent_apply = apply_next_action_tool(
            str(svp_project),
            response="PROJECT_CONTEXT_COMPLETE",
            expected_action_type="invoke_agent",
        )
        assert agent_apply["ok"] is True
        assert agent_apply["applied_action_type"] == "invoke_agent"
        assert agent_apply["used_tool"] == "dispatch_agent_status_tool"
        assert agent_apply["phase"] == "project_context"

        save_agent = save_state_tool(str(svp_project), agent_apply["state"])
        assert save_agent["ok"] is True

        # 3) run_command apply from pre_stage_3 state
        state_for_cmd = load_state(svp_project)
        state_for_cmd.stage = "pre_stage_3"
        state_for_cmd.sub_stage = "infrastructure_setup"
        save_state(state_for_cmd, svp_project)

        cmd_apply = apply_next_action_tool(
            str(svp_project),
            response="COMMAND_SUCCEEDED",
            expected_action_type="run_command",
        )
        assert cmd_apply["ok"] is True
        assert cmd_apply["applied_action_type"] == "run_command"
        assert cmd_apply["used_tool"] == "dispatch_command_status_tool"
        assert cmd_apply["phase"] == "infrastructure_setup"

    def test_bootstrap_flow_create_initialize_save_load_explain_apply(self, tmp_path):
        """Test bootstrap flow using MCP-only project creation and state initialization."""
        from svp_mcp.server import (
            create_project_tool,
            initialize_state_tool,
            save_state_tool,
            load_state_tool,
            explain_next_action_tool,
            apply_next_action_tool,
        )

        project_root = tmp_path / "bootstrap_proj"

        created = create_project_tool(str(project_root))
        assert created["ok"] is True
        assert (project_root / ".svp" / "markers").is_dir()

        init = initialize_state_tool("bootstrap_proj")
        assert init["ok"] is True
        assert init["state"]["stage"] == "0"
        assert init["state"]["sub_stage"] == "hook_activation"

        save_result = save_state_tool(str(project_root), init["state"])
        assert save_result["ok"] is True

        loaded = load_state_tool(str(project_root))
        assert loaded["stage"] == "0"
        assert loaded["sub_stage"] == "hook_activation"

        explain = explain_next_action_tool(str(project_root))
        assert explain["action_type"] == "human_gate"
        assert explain["target"] == "gate_0_1_hook_activation"

        applied = apply_next_action_tool(
            str(project_root),
            response="HOOKS ACTIVATED",
            expected_action_type=explain["action_type"],
        )
        assert applied["ok"] is True
        assert applied["applied_action_type"] == "human_gate"
        assert applied["state"]["sub_stage"] == "project_context"

        save_after_apply = save_state_tool(str(project_root), applied["state"])
        assert save_after_apply["ok"] is True

        reloaded = load_state_tool(str(project_root))
        assert reloaded["sub_stage"] == "project_context"

    def test_run_pipeline_step_tool_flow(self, svp_project):
        """Test one-step convenience flow: explain -> apply -> save."""
        from svp_mcp.server import (
            load_state_tool,
            run_pipeline_step_tool,
        )

        before = load_state_tool(str(svp_project))
        assert before["sub_stage"] == "hook_activation"

        step = run_pipeline_step_tool(
            str(svp_project),
            response="HOOKS ACTIVATED",
            expected_action_type="human_gate",
        )
        assert step["ok"] is True
        assert step["saved"] is True
        assert step["action_type"] == "human_gate"
        assert step["phase"] == "hook_activation"
        assert step["state"]["sub_stage"] == "project_context"

        after = load_state_tool(str(svp_project))
        assert after["sub_stage"] == "project_context"

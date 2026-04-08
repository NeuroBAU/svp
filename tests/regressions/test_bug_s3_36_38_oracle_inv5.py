"""Regression tests for S3-36, S3-37, S3-38.

S3-36: QUALITY_ERROR must be reachable when subprocess fails.
       QUALITY_AUTO_FIXED must be reachable when auto-fix tools modify files.
S3-37: HOOKS_JSON_SCHEMA must use 'hooks' array, not 'handler' object.
S3-38: create_new_project must set sub_stage to 'hook_activation'.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from quality_gate import _execute_gate_operations
from hooks import HOOKS_JSON_SCHEMA
from svp_launcher import create_new_project


# ---------------------------------------------------------------------------
# S3-36: QUALITY_ERROR reachability
# ---------------------------------------------------------------------------


def test_quality_gate_error_status_reachable(tmp_path):
    """S3-36: QUALITY_ERROR must be reachable when subprocess fails."""
    target = tmp_path / "test_file.py"
    target.write_text("print('hello')", encoding="utf-8")

    mock_toolchain = {"environment": {"run_prefix": ""}}

    # Mock get_gate_composition to return one operation
    fake_ops = [{"operation": "quality.formatter.check", "command": "false_cmd {target}"}]

    with patch("quality_gate.get_gate_composition", return_value=fake_ops), \
         patch("quality_gate._tool_is_none", return_value=False), \
         patch("quality_gate.resolve_command", return_value="will_fail"), \
         patch("quality_gate._run_command", side_effect=OSError("command not found")):
        result = _execute_gate_operations(
            target_path=target,
            gate_id="gate_a",
            toolchain_config=mock_toolchain,
            env_name="test_env",
            allow_auto_fix=True,
        )

    assert result.status == "QUALITY_ERROR", (
        f"Expected QUALITY_ERROR when subprocess raises, got {result.status}"
    )


# ---------------------------------------------------------------------------
# S3-36: QUALITY_AUTO_FIXED reachability
# ---------------------------------------------------------------------------


def test_quality_gate_auto_fixed_reachable(tmp_path):
    """S3-36: QUALITY_AUTO_FIXED must be reachable when tools modify files."""
    target = tmp_path / "test_file.py"
    target.write_text("x=1", encoding="utf-8")

    mock_toolchain = {"environment": {"run_prefix": ""}}
    fake_ops = [{"operation": "quality.formatter.format", "command": "ruff format {target}"}]

    call_count = [0]

    def mock_run_command(cmd):
        """Simulate a formatter that modifies the file."""
        call_count[0] += 1
        # Simulate auto-fix: modify file content
        target.write_text("x = 1\n", encoding="utf-8")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "1 file reformatted"
        mock_result.stderr = ""
        return mock_result

    with patch("quality_gate.get_gate_composition", return_value=fake_ops), \
         patch("quality_gate._tool_is_none", return_value=False), \
         patch("quality_gate.resolve_command", return_value="ruff format test_file.py"), \
         patch("quality_gate._run_command", side_effect=mock_run_command):
        result = _execute_gate_operations(
            target_path=target,
            gate_id="gate_a",
            toolchain_config=mock_toolchain,
            env_name="test_env",
            allow_auto_fix=True,
        )

    assert result.status == "QUALITY_AUTO_FIXED", (
        f"Expected QUALITY_AUTO_FIXED when file is modified by tool, got {result.status}"
    )
    assert result.auto_fixed is True


# ---------------------------------------------------------------------------
# S3-37: Hooks JSON structure
# ---------------------------------------------------------------------------


def test_hooks_json_uses_hooks_array_not_handler():
    """S3-37: HOOKS_JSON_SCHEMA must use 'hooks' array, not 'handler' object."""
    data = json.loads(json.dumps(HOOKS_JSON_SCHEMA))  # ensure serializable
    for event_type in ["PreToolUse", "PostToolUse"]:
        entries = data.get("hooks", {}).get(event_type, [])
        assert len(entries) > 0, f"No entries found for {event_type}"
        for entry in entries:
            assert "handler" not in entry, (
                f"Entry uses 'handler' instead of 'hooks': {entry}"
            )
            assert "hooks" in entry, (
                f"Entry missing 'hooks' array: {entry}"
            )
            assert isinstance(entry["hooks"], list), (
                f"'hooks' must be array: {entry}"
            )
            assert len(entry["hooks"]) > 0, (
                f"'hooks' array must not be empty: {entry}"
            )
            for hook in entry["hooks"]:
                assert "type" in hook, f"Hook missing 'type': {hook}"
                assert "command" in hook, f"Hook missing 'command': {hook}"


def test_hooks_json_all_entries_have_matcher():
    """S3-37: Every hook entry must have a 'matcher' field."""
    data = json.loads(json.dumps(HOOKS_JSON_SCHEMA))
    for event_type in ["PreToolUse", "PostToolUse"]:
        for entry in data.get("hooks", {}).get(event_type, []):
            assert "matcher" in entry, f"Entry missing 'matcher': {entry}"


# ---------------------------------------------------------------------------
# S3-38: New project initial sub_stage
# ---------------------------------------------------------------------------


def test_new_project_initial_sub_stage_is_hook_activation(tmp_path, monkeypatch):
    """S3-38: create_new_project must set sub_stage to 'hook_activation'."""
    # Set cwd to tmp_path so create_new_project creates inside it
    monkeypatch.chdir(tmp_path)

    # Create a minimal mock plugin root
    plugin_root = tmp_path / "mock_plugin"
    plugin_root.mkdir()
    plugin_json_dir = plugin_root / ".claude-plugin"
    plugin_json_dir.mkdir()
    (plugin_json_dir / "plugin.json").write_text(
        json.dumps({"name": "svp"}), encoding="utf-8"
    )

    # Mock launch_session to avoid actually launching claude
    with patch("svp_launcher.launch_session", return_value=0):
        project_root = create_new_project("test_project", plugin_root)

    state_path = project_root / ".svp" / "pipeline_state.json"
    assert state_path.exists(), ".svp/pipeline_state.json was not created"

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["sub_stage"] == "hook_activation", (
        f"Expected sub_stage='hook_activation', got sub_stage={state['sub_stage']!r}"
    )
    assert state["stage"] == "0", (
        f"Expected stage='0', got stage={state['stage']!r}"
    )

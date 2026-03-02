"""Regression tests for Bug 7: unit_completion stale-status-file race condition.

When routing emits a unit_completion action, the COMMAND must ensure the
status file contains a valid COMMAND_SUCCEEDED line before update_state.py
reads it. Without this, the status file contains the previous phase's
output (e.g., COVERAGE_COMPLETE) which doesn't match COMMAND_STATUS_PATTERNS,
causing a ValueError.

DATA ASSUMPTION: We test the routing output structure, not the actual command
execution. The test verifies that the emitted command string includes a
status file write before the update_state.py invocation.
"""

import pytest
from pathlib import Path

from svp.scripts.routing import route
from svp.scripts.pipeline_state import PipelineState


def _make_state(**overrides) -> PipelineState:
    """Create a PipelineState with sensible defaults for Stage 3."""
    defaults = dict(
        stage="3",
        sub_stage="unit_completion",
        current_unit=1,
        total_units=3,
        fix_ladder_position=None,
        red_run_retries=0,
        alignment_iteration=0,
        verified_units=[],
        pass_history=[],
        log_references={},
        project_name="test_project",
        last_action="Coverage review complete",
    )
    defaults.update(overrides)
    return PipelineState(**defaults)


class TestUnitCompletionStatusFileWrite:
    """Bug 7: unit_completion command must write COMMAND_SUCCEEDED before dispatch."""

    def test_unit_completion_command_writes_status_first(self, tmp_path):
        """The emitted command must write COMMAND_SUCCEEDED before calling update_state."""
        from svp.scripts.routing import format_action_block

        state = _make_state()
        action_dict = route(state, tmp_path)
        output = format_action_block(action_dict)

        # The command should contain COMMAND_SUCCEEDED write before update_state.py
        command = action_dict.get("COMMAND", "")
        assert "COMMAND_SUCCEEDED" in command, (
            "unit_completion command must write COMMAND_SUCCEEDED to status file"
        )
        assert "update_state.py" in command, (
            "unit_completion command must invoke update_state.py"
        )

        # Verify the write comes BEFORE update_state.py in the command
        cmd_succeeded_pos = command.find("COMMAND_SUCCEEDED")
        update_state_pos = command.find("update_state.py")
        assert cmd_succeeded_pos < update_state_pos, (
            "COMMAND_SUCCEEDED must be written to status file BEFORE "
            "update_state.py reads it"
        )


class TestUnitCompletionDispatchWithValidStatus:
    """Verify that dispatch_command_status handles unit_completion correctly."""

    def test_dispatch_unit_completion_with_command_succeeded(self, tmp_path):
        """dispatch_command_status should handle COMMAND_SUCCEEDED for unit_completion."""
        from svp.scripts.routing import dispatch_command_status

        state = _make_state()

        # Create marker directory
        markers_dir = tmp_path / ".svp" / "markers"
        markers_dir.mkdir(parents=True, exist_ok=True)

        new_state = dispatch_command_status(
            state, "COMMAND_SUCCEEDED", unit=1, phase="unit_completion",
            project_root=tmp_path,
        )
        assert new_state.current_unit == 2, (
            "After unit_completion for unit 1, current_unit should advance to 2"
        )

"""Regression test for Bug 47: unit_completion action embeds state update in COMMAND causing double dispatch.

Tests that the route() action block for sub_stage == "unit_completion" does NOT
contain update_state.py in its command string. The command should be a simple
status echo, not a compound command with state updates. State updates are
exclusively the responsibility of post commands.

SVP 2.2 adaptation:
- route() takes only project_root; state saved to disk via save_state
- Action block keys lowercase (action_type, command, post)
- PipelineState from pipeline_state
"""

import tempfile
import unittest
from pathlib import Path

from pipeline_state import PipelineState, save_state
from routing import route


def _route_with_state(state, last_status=""):
    """Save state to disk and call route(project_root)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        save_state(root, state)
        svp_dir = root / ".svp"
        svp_dir.mkdir(exist_ok=True)
        (svp_dir / "last_status.txt").write_text(last_status)
        return route(root)


class TestBug47UnitCompletionDoubleDispatch(unittest.TestCase):
    """unit_completion command must not embed update_state.py calls."""

    def test_unit_completion_command_no_update_state(self):
        """The command for unit_completion should be a simple echo,
        not a compound command containing update_state.py."""
        state = PipelineState(stage="3", sub_stage="unit_completion",
                              current_unit=1, total_units=3)
        action = _route_with_state(state)

        self.assertEqual(action["action_type"], "run_command")
        cmd = action.get("command", "")
        self.assertNotIn("update_state.py", cmd,
                         "command must not embed state update calls; "
                         "state updates belong exclusively in post")

    def test_unit_completion_command_references_unit_completion(self):
        """The unit_completion action command must reference unit_completion.

        SVP 2.2: The command is simply "unit_completion" (not echo + COMMAND_SUCCEEDED).
        Post-processing happens via dispatch_command_status.
        """
        state = PipelineState(stage="3", sub_stage="unit_completion",
                              current_unit=1, total_units=3)
        action = _route_with_state(state)

        cmd = action.get("command", "")
        self.assertIn("unit_completion", cmd,
                      "command must reference unit_completion")

    def test_unit_completion_command_does_not_embed_state_update(self):
        """The command must not contain update_state.py calls."""
        state = PipelineState(stage="3", sub_stage="unit_completion",
                              current_unit=1, total_units=3)
        action = _route_with_state(state)

        cmd = action.get("command", "")
        self.assertNotIn("update_state.py", cmd,
                         "command must not embed state update calls")


if __name__ == "__main__":
    unittest.main()

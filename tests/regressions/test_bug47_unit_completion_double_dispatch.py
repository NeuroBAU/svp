"""Regression test for Bug 47: unit_completion action embeds state update in COMMAND causing double dispatch.

Tests that the route() action block for sub_stage == "unit_completion" does NOT
contain update_state.py in its COMMAND string. The COMMAND should be a simple
status echo, not a compound command with state updates. State updates are
exclusively the responsibility of POST commands.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Path setup: ensure scripts/ is importable
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _make_state(**kwargs):
    """Create a minimal mock PipelineState with sensible defaults."""
    defaults = {
        "stage": "0",
        "sub_stage": None,
        "current_unit": 1,
        "red_run_retries": 0,
        "debug_session": None,
        "alignment_iteration": 0,
        "fix_ladder": None,
        "pass_number": 1,
        "quality_gate": None,
        "delivered_repo_path": None,
        "redo_profile_revision": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _route_with_status(state, status_value):
    """Call route() with a mocked _read_last_status and Path.is_dir."""
    from routing import route
    project_root = Path("/tmp/fake_project")
    with patch("routing._read_last_status", return_value=status_value), \
         patch("pathlib.Path.is_dir", return_value=True):
        return route(state, project_root)


class TestBug47UnitCompletionDoubleDispatch(unittest.TestCase):
    """unit_completion COMMAND must not embed update_state.py calls."""

    def test_unit_completion_command_no_update_state(self):
        """The COMMAND for unit_completion should be a simple echo,
        not a compound command containing update_state.py."""
        state = _make_state(stage="3", sub_stage="unit_completion")
        action = _route_with_status(state, None)

        self.assertEqual(action["ACTION"], "run_command")
        self.assertNotIn("update_state.py", action["COMMAND"],
                         "COMMAND must not embed state update calls; "
                         "state updates belong exclusively in POST")

    def test_unit_completion_has_post_command(self):
        """The unit_completion action must have a POST command for state updates."""
        state = _make_state(stage="3", sub_stage="unit_completion")
        action = _route_with_status(state, None)

        self.assertIn("POST", action,
                      "unit_completion must have a POST command for state updates")
        self.assertIn("unit_completion", action["POST"],
                      "POST must reference unit_completion phase")

    def test_unit_completion_command_is_simple_echo(self):
        """The COMMAND should be a simple echo producing COMMAND_SUCCEEDED."""
        state = _make_state(stage="3", sub_stage="unit_completion")
        action = _route_with_status(state, None)

        self.assertIn("echo", action["COMMAND"].lower(),
                      "COMMAND should be a simple echo")
        self.assertIn("COMMAND_SUCCEEDED", action["COMMAND"],
                      "COMMAND should produce COMMAND_SUCCEEDED status")


if __name__ == "__main__":
    unittest.main()

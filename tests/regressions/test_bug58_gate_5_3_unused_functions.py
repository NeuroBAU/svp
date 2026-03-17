"""Regression test for Bug 58: Gate 5.3 (unused_functions) routing.

Verifies that:
1. gate_5_3_unused_functions exists in GATE_VOCABULARY with correct options
2. gate_5_3_unused_functions exists in ALL_GATE_IDS
3. dispatch_gate_response handles FIX SPEC (restart from Stage 1)
4. dispatch_gate_response handles OVERRIDE CONTINUE (proceed unchanged)
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "svp" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestGate53InVocabulary(unittest.TestCase):
    """Gate 5.3 must be registered in both GATE_VOCABULARY and ALL_GATE_IDS."""

    def test_gate_5_3_in_gate_vocabulary(self):
        from routing import GATE_VOCABULARY

        self.assertIn("gate_5_3_unused_functions", GATE_VOCABULARY)
        self.assertEqual(
            GATE_VOCABULARY["gate_5_3_unused_functions"],
            ["FIX SPEC", "OVERRIDE CONTINUE"],
        )

    def test_gate_5_3_in_all_gate_ids(self):
        from prepare_task import ALL_GATE_IDS

        self.assertIn("gate_5_3_unused_functions", ALL_GATE_IDS)


class TestGate53Dispatch(unittest.TestCase):
    """dispatch_gate_response must handle both Gate 5.3 responses."""

    def _make_state(self, **kwargs):
        from types import SimpleNamespace

        defaults = {
            "stage": "5",
            "sub_stage": "repo_test",
            "current_unit": 1,
            "red_run_retries": 0,
            "debug_session": None,
            "alignment_iteration": 0,
            "fix_ladder": None,
            "pass_number": 1,
            "quality_gate": None,
            "delivered_repo_path": None,
            "redo_profile_revision": None,
            "last_action": None,
        }
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    @patch("routing.restart_from_stage")
    @patch("routing._version_spec")
    def test_fix_spec_restarts_from_stage_1(self, mock_version, mock_restart):
        from routing import dispatch_gate_response

        state = self._make_state()
        mock_restart.return_value = self._make_state(stage="1", sub_stage=None)

        result = dispatch_gate_response(
            state, "gate_5_3_unused_functions", "FIX SPEC", Path("/tmp")
        )

        mock_version.assert_called_once()
        mock_restart.assert_called_once()
        # restart_from_stage should be called with stage "1"
        call_args = mock_restart.call_args
        self.assertEqual(call_args[0][1], "1")

    def test_override_continue_returns_state(self):
        from routing import dispatch_gate_response

        state = self._make_state()
        result = dispatch_gate_response(
            state, "gate_5_3_unused_functions", "OVERRIDE CONTINUE", Path("/tmp")
        )

        # State should be returned (not restarted)
        self.assertEqual(result.stage, "5")
        self.assertIn("overrode", result.last_action)


if __name__ == "__main__":
    unittest.main()

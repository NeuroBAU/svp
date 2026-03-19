"""Regression test for Bug 67: gate_5_3 routing path in route().

Verifies that:
1. route() presents gate_5_3_unused_functions when sub_stage is gate_5_3
2. dispatch_command_status advances to gate_5_3 on UNUSED_FUNCTIONS_DETECTED
3. UNUSED_FUNCTIONS_DETECTED is in COMMAND_STATUS_PATTERNS
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "svp" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestGate53Routing(unittest.TestCase):
    """route() must present gate_5_3_unused_functions when sub_stage is gate_5_3."""

    def _make_state(self, **overrides):
        from types import SimpleNamespace
        defaults = {
            "stage": "5",
            "sub_stage": "gate_5_3",
            "current_unit": None,
            "total_units": 10,
            "fix_ladder_position": None,
            "red_run_retries": 0,
            "alignment_iteration": 0,
            "verified_units": [],
            "pass_history": [],
            "log_references": {},
            "project_name": "test",
            "last_action": None,
            "debug_session": None,
            "debug_history": [],
            "redo_triggered_from": None,
            "delivered_repo_path": None,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    def test_route_gate_5_3_presents_gate(self):
        """When sub_stage is gate_5_3, route() must return a human_gate action."""
        from routing import route, GATE_VOCABULARY

        state = self._make_state()
        result = route(state, Path("/tmp"))

        self.assertEqual(result["ACTION"], "human_gate")
        self.assertEqual(result["GATE_ID"], "gate_5_3_unused_functions")
        self.assertEqual(
            result["OPTIONS"],
            GATE_VOCABULARY["gate_5_3_unused_functions"],
        )


class TestUnusedFunctionsDetectedStatus(unittest.TestCase):
    """UNUSED_FUNCTIONS_DETECTED must be in COMMAND_STATUS_PATTERNS."""

    def test_unused_functions_detected_in_patterns(self):
        from routing import COMMAND_STATUS_PATTERNS
        self.assertIn(
            "UNUSED_FUNCTIONS_DETECTED",
            COMMAND_STATUS_PATTERNS,
            "UNUSED_FUNCTIONS_DETECTED missing from COMMAND_STATUS_PATTERNS",
        )


class TestComplianceScanDispatch(unittest.TestCase):
    """dispatch_command_status must route UNUSED_FUNCTIONS_DETECTED to gate_5_3."""

    def _make_state(self, **overrides):
        from types import SimpleNamespace
        defaults = {
            "stage": "5",
            "sub_stage": "compliance_scan",
            "current_unit": None,
            "total_units": 10,
            "fix_ladder_position": None,
            "red_run_retries": 0,
            "alignment_iteration": 0,
            "verified_units": [],
            "pass_history": [],
            "log_references": {},
            "project_name": "test",
            "last_action": None,
            "debug_session": None,
            "debug_history": [],
            "redo_triggered_from": None,
            "delivered_repo_path": None,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    @patch("routing.advance_sub_stage")
    def test_unused_functions_detected_advances_to_gate_5_3(self, mock_advance):
        from routing import dispatch_command_status

        state = self._make_state()
        mock_advance.return_value = self._make_state(sub_stage="gate_5_3")

        dispatch_command_status(
            state, "UNUSED_FUNCTIONS_DETECTED", None, "compliance_scan", Path("/tmp")
        )

        mock_advance.assert_called_once()
        call_args = mock_advance.call_args
        self.assertEqual(call_args[0][1], "gate_5_3")


if __name__ == "__main__":
    unittest.main()

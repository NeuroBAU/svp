"""Regression test for Bug 58: Gate 5.3 (unused_functions) routing.

Verifies that:
1. gate_5_3_unused_functions exists in GATE_VOCABULARY with correct options
2. gate_5_3_unused_functions exists in ALL_GATE_IDS
3. dispatch_gate_response handles FIX SPEC (restart from Stage 1)
4. dispatch_gate_response handles OVERRIDE CONTINUE (proceed unchanged)

SVP 2.2 adaptation:
- PipelineState from src.unit_5.stub (no alignment_iteration, last_action, etc.)
- dispatch_gate_response from src.unit_14.stub (4 args)
- GATE_VOCABULARY from src.unit_14.stub
- ALL_GATE_IDS from scripts/prepare_task.py
"""

import sys
import unittest
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
if not SCRIPTS_DIR.is_dir():
    SCRIPTS_DIR = _PROJECT_ROOT / "svp" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from pipeline_state import PipelineState
from routing import dispatch_gate_response, GATE_VOCABULARY


def _make_state(**kwargs):
    defaults = {
        "stage": "5",
        "sub_stage": None,
        "current_unit": None,
        "total_units": 10,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iterations": 0,
        "verified_units": [],
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
    }
    defaults.update(kwargs)
    valid_fields = {f.name for f in PipelineState.__dataclass_fields__.values()}
    filtered = {k: v for k, v in defaults.items() if k in valid_fields}
    return PipelineState(**filtered)


class TestGate53InVocabulary(unittest.TestCase):
    """Gate 5.3 must be registered in both GATE_VOCABULARY and ALL_GATE_IDS."""

    def test_gate_5_3_in_gate_vocabulary(self):
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

    def test_fix_spec_restarts_from_stage_1(self):
        state = _make_state()

        result = dispatch_gate_response(
            state, "gate_5_3_unused_functions", "FIX SPEC", Path("/tmp")
        )

        self.assertEqual(result.stage, "1")

    def test_override_continue_advances_to_repo_complete(self):
        state = _make_state()
        result = dispatch_gate_response(
            state, "gate_5_3_unused_functions", "OVERRIDE CONTINUE", Path("/tmp")
        )

        # Bug 73-A: must advance to repo_complete, not return unchanged
        self.assertEqual(result.stage, "5")
        self.assertEqual(result.sub_stage, "repo_complete")


if __name__ == "__main__":
    unittest.main()

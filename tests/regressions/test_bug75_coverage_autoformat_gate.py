"""Regression test for Bug 75: coverage_review auto-format quality gate dispatch.

SVP 2.2 adaptation:
- dispatch_command_status does not support "coverage_review" as a
  quality_gate sub_stage. The coverage_review auto-format quality gate
  pattern from SVP 2.1 was removed. Coverage review results are handled
  by route() reading last_status in SVP 2.2.
- Normal quality gate dispatches still work.
"""

import unittest

from src.unit_5.stub import PipelineState
from src.unit_14.stub import dispatch_command_status


def _make_state(**overrides):
    defaults = {
        "stage": "3",
        "sub_stage": "coverage_review",
        "current_unit": 1,
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
    defaults.update(overrides)
    valid_fields = {f.name for f in PipelineState.__dataclass_fields__.values()}
    filtered = {k: v for k, v in defaults.items() if k in valid_fields}
    return PipelineState(**filtered)


class TestBug75NormalGateBStillWorks(unittest.TestCase):
    """Normal quality_gate_b dispatch must still work."""

    def test_gate_b_pass_advances_to_green_run(self):
        state = _make_state(sub_stage="quality_gate_b")
        result = dispatch_command_status(
            state, "quality_gate", "COMMAND_SUCCEEDED", "quality_gate_b"
        )
        self.assertEqual(result.sub_stage, "green_run")


if __name__ == "__main__":
    unittest.main()

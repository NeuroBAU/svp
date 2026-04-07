"""Regression test for Bug 76: Pre-Stage-3 must run infrastructure setup.

SVP 2.2 adaptation:
- pre_stage_3 routing immediately advances to Stage 3 and starts
  stub_generation. There is no separate infrastructure setup command
  or reference_indexing agent invocation in pre_stage_3.
- dispatch_command_status does not have an "infrastructure" command_type.
- Infrastructure setup and reference indexing are handled differently
  in SVP 2.2 (integrated into stage transitions).

The infrastructure-specific tests are skipped. The basic pre_stage_3
routing test verifies the stage advances correctly.
"""

import tempfile
import unittest
from pathlib import Path

import pytest

from pipeline_state import PipelineState, save_state
from routing import route


def _make_state(**overrides):
    defaults = {
        "stage": "pre_stage_3",
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
    defaults.update(overrides)
    valid_fields = {f.name for f in PipelineState.__dataclass_fields__.values()}
    filtered = {k: v for k, v in defaults.items() if k in valid_fields}
    return PipelineState(**filtered)


def _route_with_state(state, last_status=""):
    """Save state to disk and call route(project_root)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        save_state(root, state)
        svp_dir = root / ".svp"
        svp_dir.mkdir(exist_ok=True)
        (svp_dir / "last_status.txt").write_text(last_status)
        return route(root)


class TestBug76PreStage3Routing(unittest.TestCase):
    """pre_stage_3 routing in SVP 2.2."""

    def test_pre_stage_3_advances_to_stage_3(self):
        """pre_stage_3 with total_units > 0 advances to stage 3 stub_generation."""
        state = _make_state(sub_stage=None, total_units=10)
        result = _route_with_state(state)
        # Should advance to Stage 3 and start stub_generation
        self.assertEqual(result["action_type"], "run_command")
        self.assertIn("stub_generation", result.get("command", ""))


if __name__ == "__main__":
    unittest.main()

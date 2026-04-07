"""Regression test for Bug 66: gate_2_3 RETRY BLUEPRINT no-op causing routing loop.

When the human selects RETRY BLUEPRINT at gate_2_3_alignment_exhausted,
the dispatch must:
1. Reset alignment_iterations to 0
2. Reset sub_stage (so routing invokes blueprint_author, not blueprint_checker)
3. Produce a new state (not return unchanged)

SVP 2.2 adaptation:
- PipelineState from src.unit_5.stub (alignment_iterations, no last_action)
- dispatch_gate_response from src.unit_14.stub (4 args)
- route() takes only project_root; state saved to disk first
- Action block keys lowercase (action_type, agent_type)
- No _version_blueprint or _version_spec to mock (internal to dispatch)
- No last_action field
"""

import tempfile
import unittest
from pathlib import Path

from pipeline_state import PipelineState, save_state
from routing import dispatch_gate_response


def _make_state(**kwargs):
    """Create a PipelineState with sensible defaults."""
    defaults = {
        "stage": "2",
        "sub_stage": "alignment_check",
        "current_unit": None,
        "total_units": 5,
        "red_run_retries": 0,
        "fix_ladder_position": None,
        "debug_session": None,
        "alignment_iterations": 3,
        "verified_units": [],
        "pass_history": [],
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
    }
    defaults.update(kwargs)
    valid_fields = {f.name for f in PipelineState.__dataclass_fields__.values()}
    filtered = {k: v for k, v in defaults.items() if k in valid_fields}
    return PipelineState(**filtered)


def _route_with_state(state, last_status=""):
    """Save state to disk and call route(project_root)."""
    from routing import route
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        save_state(root, state)
        svp_dir = root / ".svp"
        svp_dir.mkdir(exist_ok=True)
        (svp_dir / "last_status.txt").write_text(last_status)
        return route(root)


class TestBug66Gate23RetryBlueprint(unittest.TestCase):
    """Test that RETRY BLUEPRINT at gate_2_3 resets sub_stage."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.project_root = Path(self.tmpdir)
        # Create required directories
        (self.project_root / ".svp").mkdir(parents=True, exist_ok=True)
        (self.project_root / "blueprint").mkdir(parents=True, exist_ok=True)
        (self.project_root / "blueprint" / "history").mkdir(parents=True, exist_ok=True)

    def test_retry_blueprint_resets_sub_stage(self):
        """RETRY BLUEPRINT must change sub_stage (not leave as alignment_check)."""
        state = _make_state(stage="2", sub_stage="alignment_check", alignment_iterations=3)

        result = dispatch_gate_response(
            state, "gate_2_3_alignment_exhausted", "RETRY BLUEPRINT", self.project_root
        )

        # Sub_stage should be reset for blueprint re-authoring
        self.assertNotEqual(
            result.sub_stage, "alignment_check",
            "RETRY BLUEPRINT must not leave sub_stage as 'alignment_check' (Bug 66)"
        )

    def test_retry_blueprint_sets_sub_stage_to_blueprint_dialog(self):
        """RETRY BLUEPRINT must set sub_stage to blueprint_dialog.

        SVP 2.2: RETRY BLUEPRINT sets sub_stage to 'blueprint_dialog'
        (not None) and does NOT reset alignment_iterations.
        """
        state = _make_state(stage="2", sub_stage="alignment_check", alignment_iterations=3)

        result = dispatch_gate_response(
            state, "gate_2_3_alignment_exhausted", "RETRY BLUEPRINT", self.project_root
        )

        self.assertEqual(
            result.sub_stage, "blueprint_dialog",
            "RETRY BLUEPRINT must set sub_stage to blueprint_dialog"
        )

    def test_retry_blueprint_produces_new_state(self):
        """RETRY BLUEPRINT must return a new state object."""
        state = _make_state(stage="2", sub_stage="alignment_check", alignment_iterations=3)

        result = dispatch_gate_response(
            state, "gate_2_3_alignment_exhausted", "RETRY BLUEPRINT", self.project_root
        )

        self.assertIsNot(result, state)

    def test_after_retry_blueprint_route_invokes_blueprint_author(self):
        """After RETRY BLUEPRINT, route() must invoke blueprint_author."""
        # State after RETRY BLUEPRINT: stage=2, sub_stage should allow blueprint_author
        state = _make_state(stage="2", sub_stage=None, alignment_iterations=0)
        result = _route_with_state(state, "")

        self.assertEqual(result["action_type"], "invoke_agent")
        self.assertEqual(
            result["agent_type"], "blueprint_author",
            "After RETRY BLUEPRINT (sub_stage=None), route must invoke blueprint_author"
        )

    def test_revise_spec_enters_targeted_spec_revision(self):
        """REVISE SPEC must set sub_stage to targeted_spec_revision.

        SVP 2.2: REVISE SPEC resets alignment_iterations and enters
        targeted_spec_revision sub_stage (stays in Stage 2, not restart
        from Stage 1). RESTART SPEC is the one that goes to Stage 1.
        """
        state = _make_state(stage="2", sub_stage="alignment_check", alignment_iterations=3)

        result = dispatch_gate_response(
            state, "gate_2_3_alignment_exhausted", "REVISE SPEC", self.project_root
        )

        self.assertEqual(result.sub_stage, "targeted_spec_revision")
        self.assertEqual(result.alignment_iterations, 0)

    def test_restart_spec_restarts_from_stage_1(self):
        """RESTART SPEC must restart from Stage 1."""
        state = _make_state(stage="2", sub_stage="alignment_check", alignment_iterations=3)

        result = dispatch_gate_response(
            state, "gate_2_3_alignment_exhausted", "RESTART SPEC", self.project_root
        )

        self.assertEqual(result.stage, "1", "RESTART SPEC must restart from Stage 1")

    def test_retry_blueprint_stays_in_stage_2(self):
        """RETRY BLUEPRINT must stay in Stage 2 (not restart from Stage 1)."""
        state = _make_state(stage="2", sub_stage="alignment_check", alignment_iterations=3)

        result = dispatch_gate_response(
            state, "gate_2_3_alignment_exhausted", "RETRY BLUEPRINT", self.project_root
        )

        self.assertEqual(result.stage, "2", "RETRY BLUEPRINT must stay in Stage 2")


if __name__ == "__main__":
    unittest.main()

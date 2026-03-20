"""Regression test for Bug 73: routing/dispatch loops from unchanged state returns.

Bug 73 covers three instances of the same category of bug where a dispatch
handler returns state unchanged, causing routing to loop:

Bug 73: Stage 0 project_context sub-stage only checks PROJECT_CONTEXT_COMPLETE.
  If the setup agent writes PROFILE_COMPLETE (having completed both artifacts),
  the routing falls through to re-invoke the setup agent indefinitely.

Bug 73-A: Gate 5.3 OVERRIDE CONTINUE returns state unchanged. Since sub_stage
  remains gate_5_3, routing re-presents the gate indefinitely.

Bug 73-B: Gate 4.1 ASSEMBLY FIX returns state unchanged. Since sub_stage
  remains gate_4_1, routing re-presents the gate indefinitely.

Verifies that:
1. route() at Stage 0 project_context with PROFILE_COMPLETE presents Gate 0.2
2. route() at Stage 0 project_profile with artifact present presents Gate 0.3
3. dispatch_gate_response for gate_5_3 OVERRIDE CONTINUE advances to repo_complete
4. dispatch_gate_response for gate_4_1 ASSEMBLY FIX resets sub_stage to None
"""

import tempfile
import unittest
from pathlib import Path


def _make_state(**overrides):
    from pipeline_state import PipelineState

    defaults = {
        "stage": "0",
        "sub_stage": "project_context",
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
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


class TestBug73ProfileCompleteAtProjectContext(unittest.TestCase):
    """Stage 0 project_context must present Gate 0.2 on PROFILE_COMPLETE."""

    def test_profile_complete_presents_gate_0_2(self):
        from routing import route

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            svp_dir = project_root / ".svp"
            svp_dir.mkdir()
            (svp_dir / "last_status.txt").write_text("PROFILE_COMPLETE")

            state = _make_state(stage="0", sub_stage="project_context")
            result = route(state, project_root)

            self.assertEqual(result["ACTION"], "human_gate")
            self.assertEqual(result["GATE_ID"], "gate_0_2_context_approval")

    def test_context_complete_still_works(self):
        """Existing behavior preserved: PROJECT_CONTEXT_COMPLETE -> Gate 0.2."""
        from routing import route

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            svp_dir = project_root / ".svp"
            svp_dir.mkdir()
            (svp_dir / "last_status.txt").write_text("PROJECT_CONTEXT_COMPLETE")

            state = _make_state(stage="0", sub_stage="project_context")
            result = route(state, project_root)

            self.assertEqual(result["ACTION"], "human_gate")
            self.assertEqual(result["GATE_ID"], "gate_0_2_context_approval")


class TestBug73ProfileArtifactFallback(unittest.TestCase):
    """Stage 0 project_profile must present Gate 0.3 when artifact exists."""

    def test_profile_exists_after_gate_0_2_invokes_agent(self):
        """After Gate 0.2 CONTEXT APPROVED, last_status is overwritten.
        Bug 86 fix: artifact-existence fallback removed. Only PROFILE_COMPLETE
        triggers the gate. CONTEXT APPROVED should invoke setup_agent for
        the profile dialog even if project_profile.json exists."""
        from routing import route

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            svp_dir = project_root / ".svp"
            svp_dir.mkdir()
            (svp_dir / "last_status.txt").write_text("CONTEXT APPROVED")
            (project_root / "project_profile.json").write_text("{}")

            state = _make_state(stage="0", sub_stage="project_profile")
            result = route(state, project_root)

            self.assertEqual(result["ACTION"], "invoke_agent")
            self.assertEqual(result["AGENT"], "setup_agent")

    def test_profile_rejected_reinvokes_agent(self):
        """PROFILE REJECTED should re-invoke setup_agent even if file exists."""
        from routing import route

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            svp_dir = project_root / ".svp"
            svp_dir.mkdir()
            (svp_dir / "last_status.txt").write_text("PROFILE REJECTED")
            (project_root / "project_profile.json").write_text("{}")

            state = _make_state(stage="0", sub_stage="project_profile")
            result = route(state, project_root)

            self.assertEqual(result["ACTION"], "invoke_agent")
            self.assertEqual(result["AGENT"], "setup_agent")


class TestBug73AGate53OverrideContinue(unittest.TestCase):
    """Gate 5.3 OVERRIDE CONTINUE must advance to repo_complete, not loop."""

    def test_override_continue_advances_to_repo_complete(self):
        from routing import dispatch_gate_response

        state = _make_state(stage="5", sub_stage="gate_5_3")
        result = dispatch_gate_response(
            state, "gate_5_3_unused_functions", "OVERRIDE CONTINUE", Path("/tmp")
        )
        self.assertEqual(result.sub_stage, "repo_complete")
        self.assertIsNot(result, state)


class TestBug73BGate41AssemblyFix(unittest.TestCase):
    """Gate 4.1 ASSEMBLY FIX must reset sub_stage to None, not loop."""

    def test_assembly_fix_resets_sub_stage(self):
        from routing import dispatch_gate_response

        state = _make_state(stage="4", sub_stage="gate_4_1")
        result = dispatch_gate_response(
            state, "gate_4_1_integration_failure", "ASSEMBLY FIX", Path("/tmp")
        )
        self.assertIsNone(result.sub_stage)
        self.assertIsNot(result, state)

    def test_assembly_fix_sets_last_action(self):
        from routing import dispatch_gate_response

        state = _make_state(stage="4", sub_stage="gate_4_1")
        result = dispatch_gate_response(
            state, "gate_4_1_integration_failure", "ASSEMBLY FIX", Path("/tmp")
        )
        self.assertIn("ASSEMBLY FIX", result.last_action)


if __name__ == "__main__":
    unittest.main()

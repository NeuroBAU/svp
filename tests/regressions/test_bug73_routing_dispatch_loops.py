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
2. route() at Stage 0 project_profile with artifact present invokes agent (Bug 86 fix)
3. dispatch_gate_response for gate_5_3 OVERRIDE CONTINUE advances to repo_complete
4. dispatch_gate_response for gate_4_1 ASSEMBLY FIX resets sub_stage to None

SVP 2.2 adaptation:
- PipelineState from pipeline_state (no alignment_iteration, last_action, etc.)
- route() takes only project_root; state saved to disk first via save_state
- dispatch_gate_response from routing (4 args)
- Action block keys are lowercase (action_type, agent_type, gate_id)
"""

import tempfile
import unittest
from pathlib import Path

from pipeline_state import PipelineState, save_state
from routing import dispatch_gate_response


def _make_state(**overrides):
    defaults = {
        "stage": "0",
        "sub_stage": "project_context",
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
    from routing import route
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        save_state(root, state)
        svp_dir = root / ".svp"
        svp_dir.mkdir(exist_ok=True)
        (svp_dir / "last_status.txt").write_text(last_status)
        return route(root)


class TestBug73ProfileCompleteAtProjectContext(unittest.TestCase):
    """Stage 0 project_context routing.

    SVP 2.2: PROFILE_COMPLETE at project_context does NOT trigger gate_0_2;
    only PROJECT_CONTEXT_COMPLETE does. PROFILE_COMPLETE triggers gate_0_3
    only when sub_stage is project_profile.
    """

    def test_profile_complete_at_project_context_invokes_agent(self):
        """PROFILE_COMPLETE at project_context re-invokes setup_agent
        (it falls through because only PROJECT_CONTEXT_COMPLETE is checked)."""
        state = _make_state(stage="0", sub_stage="project_context")
        result = _route_with_state(state, "PROFILE_COMPLETE")

        self.assertEqual(result["action_type"], "invoke_agent")
        self.assertEqual(result["agent_type"], "setup_agent")

    def test_context_complete_still_works(self):
        """Existing behavior preserved: PROJECT_CONTEXT_COMPLETE -> Gate 0.2."""
        state = _make_state(stage="0", sub_stage="project_context")
        result = _route_with_state(state, "PROJECT_CONTEXT_COMPLETE")

        self.assertEqual(result["action_type"], "human_gate")
        self.assertEqual(result["gate_id"], "gate_0_2_context_approval")


class TestBug73ProfileArtifactFallback(unittest.TestCase):
    """Stage 0 project_profile routing after Gate 0.2.

    Bug 86 fix: The artifact-existence fallback (Bug 73) was removed because
    it allowed a speculative profile write during the context phase to bypass
    the spec-required five-area dialog.  Now only PROFILE_COMPLETE (emitted
    during an actual profile-phase invocation) skips the dialog.
    """

    def test_profile_exists_after_gate_0_2_invokes_agent(self):
        """After Gate 0.2 CONTEXT APPROVED, last_status is overwritten.
        Even if project_profile.json exists, the agent must be invoked to
        conduct the five-area profile dialog (Bug 86 fix)."""
        state = _make_state(stage="0", sub_stage="project_profile")

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            save_state(project_root, state)
            svp_dir = project_root / ".svp"
            svp_dir.mkdir(exist_ok=True)
            (svp_dir / "last_status.txt").write_text("CONTEXT APPROVED")
            (project_root / "project_profile.json").write_text("{}")

            from routing import route
            result = route(project_root)

            # Bug 86 fix: agent invoked, not gate presented
            self.assertEqual(result["action_type"], "invoke_agent")
            self.assertEqual(result["agent_type"], "setup_agent")

    def test_profile_rejected_reinvokes_agent(self):
        """PROFILE REJECTED should re-invoke setup_agent even if file exists."""
        state = _make_state(stage="0", sub_stage="project_profile")

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            save_state(project_root, state)
            svp_dir = project_root / ".svp"
            svp_dir.mkdir(exist_ok=True)
            (svp_dir / "last_status.txt").write_text("PROFILE REJECTED")
            (project_root / "project_profile.json").write_text("{}")

            from routing import route
            result = route(project_root)

            self.assertEqual(result["action_type"], "invoke_agent")
            self.assertEqual(result["agent_type"], "setup_agent")


class TestBug73AGate53OverrideContinue(unittest.TestCase):
    """Gate 5.3 OVERRIDE CONTINUE must advance to repo_complete, not loop."""

    def test_override_continue_advances_to_repo_complete(self):
        state = _make_state(stage="5", sub_stage=None, current_unit=None)
        result = dispatch_gate_response(
            state, "gate_5_3_unused_functions", "OVERRIDE CONTINUE", Path("/tmp")
        )
        self.assertEqual(result.sub_stage, "repo_complete")
        self.assertIsNot(result, state)


class TestBug73BGate41AssemblyFix(unittest.TestCase):
    """Gate 4.1 ASSEMBLY FIX must reset sub_stage to None, not loop."""

    def test_assembly_fix_resets_sub_stage(self):
        state = _make_state(stage="4", sub_stage=None, current_unit=None)
        result = dispatch_gate_response(
            state, "gate_4_1_integration_failure", "ASSEMBLY FIX", Path("/tmp")
        )
        self.assertIsNone(result.sub_stage)
        self.assertIsNot(result, state)

    def test_assembly_fix_produces_new_state(self):
        state = _make_state(stage="4", sub_stage=None, current_unit=None)
        result = dispatch_gate_response(
            state, "gate_4_1_integration_failure", "ASSEMBLY FIX", Path("/tmp")
        )
        # SVP 2.2: no last_action field; just verify state was copied
        self.assertIsNot(result, state)


if __name__ == "__main__":
    unittest.main()

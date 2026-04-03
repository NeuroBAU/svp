"""Regression test for Bug 43: Two-branch routing invariant violations.

Tests that every sub-stage where an agent completion triggers a gate
presentation checks last_status before deciding whether to invoke
the agent or present the gate.

Adapted for SVP 2.2 API:
- route() reads state from disk (no state arg)
- PipelineState is a dataclass from src.unit_5.stub
- Action block keys: action_type, agent_type, gate_id (lowercase)
- Redo profile sub-stages are handled in stage 0 routing
- Gate vocabulary/consistency checks use src.unit_14.stub and src.unit_13.stub
"""

import json
import tempfile
import unittest
from pathlib import Path

from src.unit_5.stub import PipelineState, save_state
from src.unit_14.stub import route, GATE_VOCABULARY


def _make_state(**kwargs):
    """Create a PipelineState with sensible defaults."""
    defaults = {
        "stage": "0",
        "sub_stage": None,
        "current_unit": None,
        "total_units": 10,
        "red_run_retries": 0,
        "debug_session": None,
        "alignment_iterations": 0,
        "fix_ladder_position": None,
        "verified_units": [],
        "pass_history": [],
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
    }
    defaults.update(kwargs)
    return PipelineState(**defaults)


def _route_with_status(state, status_value):
    """Write state to disk with given last_status, then call route()."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        save_state(root, state)
        svp_dir = root / ".svp"
        svp_dir.mkdir(exist_ok=True)
        if status_value:
            (svp_dir / "last_status.txt").write_text(
                status_value, encoding="utf-8"
            )
        else:
            # Ensure file doesn't exist or is empty
            (svp_dir / "last_status.txt").write_text("", encoding="utf-8")
        (root / "svp_config.json").write_text(
            json.dumps({"iteration_limit": 3}), encoding="utf-8"
        )
        return route(root)


class TestBug43TwoBranchRouting(unittest.TestCase):
    """Verify two-branch routing invariant across all affected stages."""

    # ------------------------------------------------------------------
    # Stage 2: Blueprint dialog
    # ------------------------------------------------------------------

    def test_stage2_blueprint_draft_complete_presents_gate(self):
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        action = _route_with_status(state, "BLUEPRINT_DRAFT_COMPLETE")
        self.assertEqual(action["action_type"], "human_gate")
        self.assertEqual(action["gate_id"], "gate_2_1_blueprint_approval")

    def test_stage2_no_status_invokes_blueprint_author(self):
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        action = _route_with_status(state, None)
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "blueprint_author")

    # ------------------------------------------------------------------
    # Stage 4: Integration test author -> run integration tests
    # ------------------------------------------------------------------

    def test_stage4_integration_tests_complete_runs_command(self):
        state = _make_state(stage="4", sub_stage=None)
        action = _route_with_status(state, "INTEGRATION_TESTS_COMPLETE")
        self.assertEqual(action["action_type"], "run_command")
        self.assertIn("test_execution", action.get("command", ""))

    def test_stage4_no_status_invokes_integration_test_author(self):
        state = _make_state(stage="4", sub_stage=None)
        action = _route_with_status(state, None)
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "integration_test_author")

    # ------------------------------------------------------------------
    # Stage 5 sub_stage=None: Repo assembly -> gate_5_1
    # ------------------------------------------------------------------

    def test_stage5_repo_assembly_complete_presents_gate(self):
        state = _make_state(stage="5", sub_stage=None, debug_session=None)
        action = _route_with_status(state, "REPO_ASSEMBLY_COMPLETE")
        self.assertEqual(action["action_type"], "human_gate")
        self.assertEqual(action["gate_id"], "gate_5_1_repo_test")

    def test_stage5_no_status_invokes_git_repo_agent(self):
        state = _make_state(stage="5", sub_stage=None, debug_session=None)
        action = _route_with_status(state, None)
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "git_repo_agent")

    # ------------------------------------------------------------------
    # Redo profile sub-stages (handled in stage 0 routing in SVP 2.2)
    # ------------------------------------------------------------------

    def test_redo_profile_delivery_complete_presents_gate(self):
        state = _make_state(stage="0", sub_stage="redo_profile_delivery")
        action = _route_with_status(state, "PROFILE_COMPLETE")
        self.assertEqual(action["action_type"], "human_gate")
        self.assertEqual(action["gate_id"], "gate_0_3r_profile_revision")

    def test_redo_profile_delivery_no_status_invokes_setup_agent(self):
        state = _make_state(stage="0", sub_stage="redo_profile_delivery")
        action = _route_with_status(state, None)
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "setup_agent")

    def test_redo_profile_blueprint_complete_presents_gate(self):
        state = _make_state(stage="0", sub_stage="redo_profile_blueprint")
        action = _route_with_status(state, "PROFILE_COMPLETE")
        self.assertEqual(action["action_type"], "human_gate")
        self.assertEqual(action["gate_id"], "gate_0_3r_profile_revision")

    def test_redo_profile_blueprint_no_status_invokes_setup_agent(self):
        state = _make_state(stage="0", sub_stage="redo_profile_blueprint")
        action = _route_with_status(state, None)
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "setup_agent")

    # ------------------------------------------------------------------
    # Debug loop triage two-branch check
    # ------------------------------------------------------------------

    def test_debug_triage_complete_presents_classification_gate(self):
        ds = {
            "bug_number": 1, "classification": None, "affected_units": [],
            "phase": "triage", "authorized": True,
            "repair_retry_count": 0, "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(stage="5", sub_stage=None, debug_session=ds)
        action = _route_with_status(state, "TRIAGE_COMPLETE: single_unit")
        self.assertEqual(action["action_type"], "human_gate")
        self.assertEqual(action["gate_id"], "gate_6_2_debug_classification")

    def test_debug_triage_complete_build_env_fast_path(self):
        """Bug 55: build_env fast path bypasses Gate 6.2, goes to repair_agent."""
        ds = {
            "bug_number": 1, "classification": None, "affected_units": [],
            "phase": "triage", "authorized": True,
            "repair_retry_count": 0, "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(stage="5", sub_stage=None, debug_session=ds)
        action = _route_with_status(state, "TRIAGE_COMPLETE: build_env")
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "repair_agent")

    def test_debug_triage_non_reproducible_presents_gate(self):
        ds = {
            "bug_number": 1, "classification": None, "affected_units": [],
            "phase": "triage", "authorized": True,
            "repair_retry_count": 0, "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(stage="5", sub_stage=None, debug_session=ds)
        action = _route_with_status(state, "TRIAGE_NON_REPRODUCIBLE")
        self.assertEqual(action["action_type"], "human_gate")
        self.assertEqual(action["gate_id"], "gate_6_4_non_reproducible")

    def test_debug_no_status_invokes_bug_triage(self):
        ds = {
            "bug_number": 1, "classification": None, "affected_units": [],
            "phase": "triage", "authorized": True,
            "repair_retry_count": 0, "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(stage="5", sub_stage=None, debug_session=ds)
        action = _route_with_status(state, None)
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "bug_triage_agent")

    def test_debug_triage_needs_refinement_reinvokes_triage(self):
        ds = {
            "bug_number": 1, "classification": None, "affected_units": [],
            "phase": "triage", "authorized": True,
            "repair_retry_count": 0, "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(stage="5", sub_stage=None, debug_session=ds)
        action = _route_with_status(state, "TRIAGE_NEEDS_REFINEMENT")
        self.assertEqual(action["action_type"], "invoke_agent")
        self.assertEqual(action["agent_type"], "bug_triage_agent")


class TestGateVocabularyConsistency(unittest.TestCase):
    """Cross-unit consistency: every gate in GATE_VOCABULARY must be in ALL_GATE_IDS."""

    def test_all_gate_vocabulary_keys_in_all_gate_ids(self):
        from src.unit_13.stub import ALL_GATE_IDS

        missing = set(GATE_VOCABULARY.keys()) - set(ALL_GATE_IDS)
        self.assertEqual(
            missing, set(),
            f"Gate IDs in GATE_VOCABULARY but missing from ALL_GATE_IDS: {missing}"
        )

    def test_all_gate_ids_in_gate_vocabulary(self):
        """Every gate ID registered for prompt preparation should have a vocabulary entry."""
        from src.unit_13.stub import ALL_GATE_IDS

        missing = set(ALL_GATE_IDS) - set(GATE_VOCABULARY.keys())
        self.assertEqual(
            missing, set(),
            f"Gate IDs in ALL_GATE_IDS but missing from GATE_VOCABULARY: {missing}"
        )


if __name__ == "__main__":
    unittest.main()

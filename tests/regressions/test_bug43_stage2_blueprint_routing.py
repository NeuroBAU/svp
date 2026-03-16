"""Regression test for Bug 43: Two-branch routing invariant violations.

Tests that every sub-stage where an agent completion triggers a gate
presentation checks last_status.txt before deciding whether to invoke
the agent or present the gate.

Covers: Stage 2 (blueprint dialog), Stage 4 (integration test author),
Stage 5 sub_stage=None (repo assembly), redo profile sub-stages,
and debug loop triage.

Also tests cross-unit consistency: every gate ID in GATE_VOCABULARY
(routing.py) must appear in ALL_GATE_IDS (prepare_task.py).
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


class TestBug43TwoBranchRouting(unittest.TestCase):
    """Verify two-branch routing invariant across all affected stages."""

    # ------------------------------------------------------------------
    # Stage 2: Blueprint dialog (already fixed by Bug 21, verify intact)
    # ------------------------------------------------------------------

    def test_stage2_blueprint_draft_complete_presents_gate(self):
        state = _make_state(stage="2", sub_stage=None)
        action = _route_with_status(state, "BLUEPRINT_DRAFT_COMPLETE")
        self.assertEqual(action["ACTION"], "human_gate")
        self.assertEqual(action["GATE_ID"], "gate_2_1_blueprint_approval")

    def test_stage2_no_status_invokes_blueprint_author(self):
        state = _make_state(stage="2", sub_stage=None)
        action = _route_with_status(state, None)
        self.assertEqual(action["ACTION"], "invoke_agent")
        self.assertEqual(action["AGENT"], "blueprint_author")

    # ------------------------------------------------------------------
    # Stage 4: Integration test author -> run integration tests
    # ------------------------------------------------------------------

    def test_stage4_integration_tests_complete_runs_command(self):
        state = _make_state(stage="4")
        action = _route_with_status(state, "INTEGRATION_TESTS_COMPLETE")
        self.assertEqual(action["ACTION"], "run_command")
        self.assertIn("run_tests.py", action["COMMAND"])
        self.assertIn("tests/integration/", action["COMMAND"])

    def test_stage4_no_status_invokes_integration_test_author(self):
        state = _make_state(stage="4")
        action = _route_with_status(state, None)
        self.assertEqual(action["ACTION"], "invoke_agent")
        self.assertEqual(action["AGENT"], "integration_test_author")

    # ------------------------------------------------------------------
    # Stage 5 sub_stage=None: Repo assembly -> gate_5_1
    # ------------------------------------------------------------------

    def test_stage5_repo_assembly_complete_presents_gate(self):
        state = _make_state(stage="5", sub_stage=None, debug_session=None)
        action = _route_with_status(state, "REPO_ASSEMBLY_COMPLETE")
        self.assertEqual(action["ACTION"], "human_gate")
        self.assertEqual(action["GATE_ID"], "gate_5_1_repo_test")

    def test_stage5_no_status_invokes_git_repo_agent(self):
        state = _make_state(stage="5", sub_stage=None, debug_session=None)
        action = _route_with_status(state, None)
        self.assertEqual(action["ACTION"], "invoke_agent")
        self.assertEqual(action["AGENT"], "git_repo_agent")

    # ------------------------------------------------------------------
    # Redo profile sub-stages
    # ------------------------------------------------------------------

    def test_redo_profile_delivery_complete_presents_gate(self):
        state = _make_state(stage="2", sub_stage="redo_profile_delivery")
        action = _route_with_status(state, "PROFILE_COMPLETE")
        self.assertEqual(action["ACTION"], "human_gate")
        self.assertEqual(action["GATE_ID"], "gate_0_3r_profile_revision")

    def test_redo_profile_delivery_no_status_invokes_setup_agent(self):
        state = _make_state(stage="2", sub_stage="redo_profile_delivery")
        action = _route_with_status(state, None)
        self.assertEqual(action["ACTION"], "invoke_agent")
        self.assertEqual(action["AGENT"], "setup_agent")

    def test_redo_profile_blueprint_complete_presents_gate(self):
        state = _make_state(stage="3", sub_stage="redo_profile_blueprint")
        action = _route_with_status(state, "PROFILE_COMPLETE")
        self.assertEqual(action["ACTION"], "human_gate")
        self.assertEqual(action["GATE_ID"], "gate_0_3r_profile_revision")

    def test_redo_profile_blueprint_no_status_invokes_setup_agent(self):
        state = _make_state(stage="3", sub_stage="redo_profile_blueprint")
        action = _route_with_status(state, None)
        self.assertEqual(action["ACTION"], "invoke_agent")
        self.assertEqual(action["AGENT"], "setup_agent")

    # ------------------------------------------------------------------
    # Debug loop triage two-branch check
    # ------------------------------------------------------------------

    def test_debug_triage_complete_presents_classification_gate(self):
        state = _make_state(
            stage="5", sub_stage=None,
            debug_session={"bug_id": "test", "phase": "triage"},
        )
        action = _route_with_status(state, "TRIAGE_COMPLETE: single_unit")
        self.assertEqual(action["ACTION"], "human_gate")
        self.assertEqual(action["GATE_ID"], "gate_6_2_debug_classification")

    def test_debug_triage_complete_build_env_presents_gate(self):
        state = _make_state(
            stage="5", sub_stage=None,
            debug_session={"bug_id": "test", "phase": "triage"},
        )
        action = _route_with_status(state, "TRIAGE_COMPLETE: build_env")
        self.assertEqual(action["ACTION"], "human_gate")
        self.assertEqual(action["GATE_ID"], "gate_6_2_debug_classification")

    def test_debug_triage_non_reproducible_presents_gate(self):
        state = _make_state(
            stage="5", sub_stage=None,
            debug_session={"bug_id": "test", "phase": "triage"},
        )
        action = _route_with_status(state, "TRIAGE_NON_REPRODUCIBLE")
        self.assertEqual(action["ACTION"], "human_gate")
        self.assertEqual(action["GATE_ID"], "gate_6_4_non_reproducible")

    def test_debug_no_status_invokes_bug_triage(self):
        state = _make_state(
            stage="5", sub_stage=None,
            debug_session={"bug_id": "test", "phase": "triage"},
        )
        action = _route_with_status(state, None)
        self.assertEqual(action["ACTION"], "invoke_agent")
        self.assertEqual(action["AGENT"], "bug_triage")

    def test_debug_triage_needs_refinement_reinvokes_triage(self):
        state = _make_state(
            stage="5", sub_stage=None,
            debug_session={"bug_id": "test", "phase": "triage"},
        )
        action = _route_with_status(state, "TRIAGE_NEEDS_REFINEMENT")
        self.assertEqual(action["ACTION"], "invoke_agent")
        self.assertEqual(action["AGENT"], "bug_triage")


class TestGateVocabularyConsistency(unittest.TestCase):
    """Cross-unit consistency: every gate in GATE_VOCABULARY must be in ALL_GATE_IDS."""

    def test_all_gate_vocabulary_keys_in_all_gate_ids(self):
        from routing import GATE_VOCABULARY
        from prepare_task import ALL_GATE_IDS

        missing = set(GATE_VOCABULARY.keys()) - set(ALL_GATE_IDS)
        self.assertEqual(
            missing, set(),
            f"Gate IDs in GATE_VOCABULARY but missing from ALL_GATE_IDS: {missing}"
        )

    def test_all_gate_ids_in_gate_vocabulary(self):
        """Every gate ID registered for prompt preparation should have a vocabulary entry."""
        from routing import GATE_VOCABULARY
        from prepare_task import ALL_GATE_IDS

        missing = set(ALL_GATE_IDS) - set(GATE_VOCABULARY.keys())
        self.assertEqual(
            missing, set(),
            f"Gate IDs in ALL_GATE_IDS but missing from GATE_VOCABULARY: {missing}"
        )


if __name__ == "__main__":
    unittest.main()

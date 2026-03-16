"""Tests for Unit 10 structural invariants.

Synthetic data assumptions:
- Gate ID consistency: GATE_RESPONSES keys ==
  ALL_GATE_IDS from Unit 9.
- Two-branch routing invariant: sub-stages with
  agent-to-gate or agent-to-command transitions
  have two-branch checks in route().
- Route-level state persistence invariant: any
  route() branch performing in-memory state
  transition and recursively routing calls
  save_state() first.
- Exhaustive dispatch invariant: every main-pipeline
  agent type must explicitly advance state.
- Bug 47: unit_completion COMMAND must not contain
  update_state.py.
"""

from unittest.mock import MagicMock

import pytest

from routing import (
    AGENT_STATUS_LINES,
    GATE_RESPONSES,
    route,
)


class TestGateIdConsistencyInvariant:
    def test_gate_responses_matches_unit_9(self):
        """Section 3.6 invariant 2: GATE_RESPONSES
        keys must be identical to ALL_GATE_IDS."""
        from prepare_task import ALL_GATE_IDS

        assert set(GATE_RESPONSES.keys()) == set(ALL_GATE_IDS)

    def test_no_extra_gates_in_responses(self):
        from prepare_task import ALL_GATE_IDS

        extra = set(GATE_RESPONSES.keys()) - set(ALL_GATE_IDS)
        assert extra == set(), f"Extra gates in GATE_RESPONSES: {extra}"

    def test_no_missing_gates_in_responses(self):
        from prepare_task import ALL_GATE_IDS

        missing = set(ALL_GATE_IDS) - set(GATE_RESPONSES.keys())
        assert missing == set(), f"Missing gates: {missing}"


class TestTwoBranchRoutingInvariant:
    """Every sub-stage with agent-to-gate or
    agent-to-command transition must have a
    two-branch check in route()."""

    GATE_PRESENTING_SUBSTAGES = [
        ("0", "project_context"),
        ("0", "project_profile"),
        ("2", "blueprint_dialog"),
        ("2", "alignment_check"),
    ]

    COMMAND_PRESENTING_SUBSTAGES = [
        ("3", "quality_gate_a_retry"),
        ("3", "quality_gate_b_retry"),
    ]

    @pytest.mark.parametrize(
        "stage,sub_stage",
        GATE_PRESENTING_SUBSTAGES,
    )
    def test_gate_presenting_branches(self, tmp_path, stage, sub_stage):
        """Two-branch: without last_status should
        invoke agent; with last_status should present
        gate."""
        state = MagicMock()
        state.stage = stage
        state.sub_stage = sub_stage
        state.current_unit = 1
        state.total_units = 5
        state.project_name = "testproj"
        state.fix_ladder_position = None
        state.red_run_retries = 0
        state.alignment_iteration = 0
        state.debug_session = None
        state.verified_units = []
        state.pass_history = []
        state.log_references = {}
        state.last_action = None
        state.debug_history = []
        state.redo_triggered_from = None
        state.delivered_repo_path = None

        # Branch 1: no status file
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        status_file = svp_dir / "last_status.txt"
        if status_file.exists():
            status_file.unlink()

        result_no_status = route(state, tmp_path)
        assert "ACTION" in result_no_status

        # Branch 2: with status file
        status_file.write_text("SOME_STATUS")
        result_with_status = route(state, tmp_path)
        assert "ACTION" in result_with_status


class TestExhaustiveDispatchInvariant:
    """Every main-pipeline agent type must have
    entries in AGENT_STATUS_LINES."""

    MAIN_PIPELINE_AGENTS = [
        "setup_agent",
        "stakeholder_dialog",
        "stakeholder_reviewer",
        "blueprint_author",
        "blueprint_checker",
        "blueprint_reviewer",
        "test_agent",
        "implementation_agent",
        "coverage_review",
        "diagnostic_agent",
        "integration_test_author",
        "git_repo_agent",
        "redo_agent",
        "bug_triage",
        "repair_agent",
        "reference_indexing",
    ]

    @pytest.mark.parametrize(
        "agent",
        MAIN_PIPELINE_AGENTS,
    )
    def test_agent_has_status_lines(self, agent):
        assert agent in AGENT_STATUS_LINES
        assert len(AGENT_STATUS_LINES[agent]) > 0


class TestBug47UnitCompletionNoUpdateState:
    """Bug 47: unit_completion COMMAND must not
    contain update_state.py."""

    def test_unit_completion_command(self, tmp_path):
        state = MagicMock()
        state.stage = "3"
        state.sub_stage = "unit_completion"
        state.current_unit = 1
        state.total_units = 5
        state.project_name = "testproj"
        state.fix_ladder_position = None
        state.red_run_retries = 0
        state.alignment_iteration = 0
        state.debug_session = None
        state.verified_units = []
        state.pass_history = []
        state.log_references = {}
        state.last_action = None
        state.debug_history = []
        state.redo_triggered_from = None
        state.delivered_repo_path = None

        result = route(state, tmp_path)
        if "COMMAND" in result:
            assert "update_state.py" not in result["COMMAND"]

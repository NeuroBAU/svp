"""Regression tests for S3-18 through S3-21: routing loop prevention.

S3-18: Debug reassembly phase must check REPO_ASSEMBLY_COMPLETE and advance
       to regression_test, not re-invoke git_repo_agent indefinitely.
S3-19: Diagnostic escalation must check DIAGNOSIS_COMPLETE and present
       Gate 3.2, not re-invoke diagnostic_agent indefinitely.
S3-20: Debug repair phase on REPAIR_COMPLETE must transition to reassembly
       phase, not directly invoke git_repo_agent (which leaves phase as
       repair, causing a loop after assembly completes).
S3-21: dispatch_command_status must handle lessons_learned, debug_commit,
       and stage3_reentry command types.
"""

import json

from src.unit_5.stub import PipelineState
from src.unit_14.stub import dispatch_command_status, route


def _make_state(**overrides):
    """Build a minimal PipelineState with defaults."""
    defaults = {
        "stage": "5",
        "sub_stage": None,
        "current_unit": None,
        "total_units": 10,
        "verified_units": [],
        "alignment_iterations": 0,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "primary_language": "python",
        "component_languages": [],
        "secondary_language": None,
        "oracle_session_active": False,
        "oracle_test_project": None,
        "oracle_phase": None,
        "oracle_run_count": 0,
        "oracle_nested_session_path": None,
        "state_hash": None,
        "spec_revision_count": 0,
        "pass_": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


def _setup_project_root(tmp_path, state_dict, last_status=""):
    """Create a minimal project root with pipeline_state.json and last_status.txt."""
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(exist_ok=True)
    (svp_dir / "pipeline_state.json").write_text(json.dumps(state_dict, indent=2))
    (svp_dir / "last_status.txt").write_text(last_status)
    return tmp_path


# ---------------------------------------------------------------------------
# S3-18: Debug reassembly phase infinite loop
# ---------------------------------------------------------------------------


class TestS3_18_ReassemblyPhaseLoop:
    """S3-18: reassembly phase must advance on REPO_ASSEMBLY_COMPLETE."""

    def test_reassembly_advances_to_regression_test_on_assembly_complete(self, tmp_path):
        """After REPO_ASSEMBLY_COMPLETE in reassembly phase, must not re-invoke git_repo_agent."""
        state_dict = {
            "stage": "5",
            "sub_stage": None,
            "current_unit": None,
            "total_units": 10,
            "verified_units": [],
            "alignment_iterations": 0,
            "fix_ladder_position": None,
            "red_run_retries": 0,
            "pass_history": [],
            "debug_session": {
                "authorized": True,
                "phase": "reassembly",
                "bug_report": "test bug",
            },
            "debug_history": [],
            "redo_triggered_from": None,
            "delivered_repo_path": None,
            "primary_language": "python",
            "component_languages": [],
            "secondary_language": None,
            "oracle_session_active": False,
            "oracle_test_project": None,
            "oracle_phase": None,
            "oracle_run_count": 0,
            "oracle_nested_session_path": None,
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }
        root = _setup_project_root(tmp_path, state_dict, last_status="REPO_ASSEMBLY_COMPLETE")
        result = route(root)
        # Must NOT be invoke_agent for git_repo_agent (that would be a loop)
        # Should have transitioned to regression_test phase, which invokes test_agent
        if result["action_type"] == "invoke_agent":
            assert result.get("agent_type") != "git_repo_agent", (
                "S3-18 regression: reassembly phase re-invokes git_repo_agent "
                "after REPO_ASSEMBLY_COMPLETE instead of advancing to regression_test"
            )

    def test_reassembly_invokes_git_repo_when_not_complete(self, tmp_path):
        """When no REPO_ASSEMBLY_COMPLETE status, reassembly should invoke git_repo_agent."""
        state_dict = {
            "stage": "5",
            "sub_stage": None,
            "current_unit": None,
            "total_units": 10,
            "verified_units": [],
            "alignment_iterations": 0,
            "fix_ladder_position": None,
            "red_run_retries": 0,
            "pass_history": [],
            "debug_session": {
                "authorized": True,
                "phase": "reassembly",
                "bug_report": "test bug",
            },
            "debug_history": [],
            "redo_triggered_from": None,
            "delivered_repo_path": None,
            "primary_language": "python",
            "component_languages": [],
            "secondary_language": None,
            "oracle_session_active": False,
            "oracle_test_project": None,
            "oracle_phase": None,
            "oracle_run_count": 0,
            "oracle_nested_session_path": None,
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }
        root = _setup_project_root(tmp_path, state_dict, last_status="")
        result = route(root)
        assert result["action_type"] == "invoke_agent"
        assert result["agent_type"] == "git_repo_agent"


# ---------------------------------------------------------------------------
# S3-19: Diagnostic escalation infinite loop
# ---------------------------------------------------------------------------


class TestS3_19_DiagnosticEscalationLoop:
    """S3-19: diagnostic escalation must present gate on DIAGNOSIS_COMPLETE."""

    def test_diagnostic_presents_gate_on_diagnosis_complete(self, tmp_path):
        """After DIAGNOSIS_COMPLETE, must present Gate 3.2, not re-invoke diagnostic_agent."""
        state_dict = {
            "stage": "3",
            "sub_stage": "implementation",
            "current_unit": 1,
            "total_units": 10,
            "verified_units": [],
            "alignment_iterations": 0,
            "fix_ladder_position": "diagnostic",
            "red_run_retries": 0,
            "pass_history": [],
            "debug_session": None,
            "debug_history": [],
            "redo_triggered_from": None,
            "delivered_repo_path": None,
            "primary_language": "python",
            "component_languages": [],
            "secondary_language": None,
            "oracle_session_active": False,
            "oracle_test_project": None,
            "oracle_phase": None,
            "oracle_run_count": 0,
            "oracle_nested_session_path": None,
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }
        root = _setup_project_root(tmp_path, state_dict, last_status="DIAGNOSIS_COMPLETE")
        result = route(root)
        assert result["action_type"] == "human_gate", (
            "S3-19 regression: diagnostic escalation re-invokes diagnostic_agent "
            "after DIAGNOSIS_COMPLETE instead of presenting Gate 3.2"
        )
        assert result["gate_id"] == "gate_3_2_diagnostic_decision"

    def test_diagnostic_invokes_agent_when_not_complete(self, tmp_path):
        """When no DIAGNOSIS_COMPLETE status, diagnostic should invoke diagnostic_agent."""
        state_dict = {
            "stage": "3",
            "sub_stage": "implementation",
            "current_unit": 1,
            "total_units": 10,
            "verified_units": [],
            "alignment_iterations": 0,
            "fix_ladder_position": "diagnostic",
            "red_run_retries": 0,
            "pass_history": [],
            "debug_session": None,
            "debug_history": [],
            "redo_triggered_from": None,
            "delivered_repo_path": None,
            "primary_language": "python",
            "component_languages": [],
            "secondary_language": None,
            "oracle_session_active": False,
            "oracle_test_project": None,
            "oracle_phase": None,
            "oracle_run_count": 0,
            "oracle_nested_session_path": None,
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }
        root = _setup_project_root(tmp_path, state_dict, last_status="")
        result = route(root)
        assert result["action_type"] == "invoke_agent"
        assert result["agent_type"] == "diagnostic_agent"


# ---------------------------------------------------------------------------
# S3-20: Debug repair phase routing loop
# ---------------------------------------------------------------------------


class TestS3_20_RepairPhaseLoop:
    """S3-20: repair phase on REPAIR_COMPLETE must transition to reassembly phase."""

    def test_repair_complete_transitions_to_reassembly(self, tmp_path):
        """After REPAIR_COMPLETE, repair handler must transition to reassembly phase."""
        state_dict = {
            "stage": "5",
            "sub_stage": None,
            "current_unit": None,
            "total_units": 10,
            "verified_units": [],
            "alignment_iterations": 0,
            "fix_ladder_position": None,
            "red_run_retries": 0,
            "pass_history": [],
            "debug_session": {
                "authorized": True,
                "phase": "repair",
                "bug_report": "test bug",
            },
            "debug_history": [],
            "redo_triggered_from": None,
            "delivered_repo_path": None,
            "primary_language": "python",
            "component_languages": [],
            "secondary_language": None,
            "oracle_session_active": False,
            "oracle_test_project": None,
            "oracle_phase": None,
            "oracle_run_count": 0,
            "oracle_nested_session_path": None,
            "state_hash": None,
            "spec_revision_count": 0,
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }
        root = _setup_project_root(tmp_path, state_dict, last_status="REPAIR_COMPLETE")
        result = route(root)
        # After repair->reassembly transition, should invoke git_repo_agent
        # (from the reassembly handler, not from the repair handler)
        assert result["action_type"] == "invoke_agent"
        assert result["agent_type"] == "git_repo_agent"
        # Verify the debug phase was updated to "reassembly" in the state file
        import json as json_mod
        state_path = root / ".svp" / "pipeline_state.json"
        saved_state = json_mod.loads(state_path.read_text())
        assert saved_state["debug_session"]["phase"] == "reassembly", (
            "S3-20 regression: repair phase should transition to reassembly, "
            "not remain as repair"
        )


# ---------------------------------------------------------------------------
# S3-21: Missing dispatch_command_status handlers
# ---------------------------------------------------------------------------


class TestS3_21_MissingCommandHandlers:
    """S3-21: dispatch_command_status must handle lessons_learned, debug_commit, stage3_reentry."""

    def test_dispatch_handles_lessons_learned_succeeded(self):
        """S3-21: dispatch_command_status must handle lessons_learned COMMAND_SUCCEEDED."""
        state = _make_state(
            debug_session={
                "authorized": True,
                "phase": "lessons_learned",
                "bug_report": "test bug",
            },
        )
        # Should not raise ValueError
        new = dispatch_command_status(state, "lessons_learned", "COMMAND_SUCCEEDED")
        assert new is not None

    def test_dispatch_lessons_learned_advances_to_commit(self):
        """S3-21: lessons_learned COMMAND_SUCCEEDED should transition debug phase to commit."""
        state = _make_state(
            debug_session={
                "authorized": True,
                "phase": "lessons_learned",
                "bug_report": "test bug",
            },
        )
        new = dispatch_command_status(state, "lessons_learned", "COMMAND_SUCCEEDED")
        assert new.debug_session is not None
        assert new.debug_session["phase"] == "commit"

    def test_dispatch_handles_lessons_learned_failed(self):
        """S3-21: dispatch_command_status must handle lessons_learned COMMAND_FAILED."""
        state = _make_state(
            debug_session={
                "authorized": True,
                "phase": "lessons_learned",
                "bug_report": "test bug",
            },
        )
        new = dispatch_command_status(state, "lessons_learned", "COMMAND_FAILED")
        assert new is not None

    def test_dispatch_handles_debug_commit_succeeded(self):
        """S3-21: dispatch_command_status must handle debug_commit COMMAND_SUCCEEDED."""
        state = _make_state(
            debug_session={
                "authorized": True,
                "phase": "commit",
                "bug_report": "test bug",
            },
        )
        new = dispatch_command_status(state, "debug_commit", "COMMAND_SUCCEEDED")
        assert new is not None
        # debug_commit COMMAND_SUCCEEDED should complete the debug session
        assert new.debug_session is None, (
            "S3-21 regression: debug_commit should complete (clear) the debug session"
        )

    def test_dispatch_handles_debug_commit_failed(self):
        """S3-21: dispatch_command_status must handle debug_commit COMMAND_FAILED."""
        state = _make_state(
            debug_session={
                "authorized": True,
                "phase": "commit",
                "bug_report": "test bug",
            },
        )
        new = dispatch_command_status(state, "debug_commit", "COMMAND_FAILED")
        assert new is not None

    def test_dispatch_handles_stage3_reentry_succeeded(self):
        """S3-21: dispatch_command_status must handle stage3_reentry COMMAND_SUCCEEDED."""
        state = _make_state(
            stage="3",
            sub_stage="stub_generation",
            current_unit=1,
        )
        new = dispatch_command_status(state, "stage3_reentry", "COMMAND_SUCCEEDED")
        assert new is not None
        assert new.sub_stage == "stub_generation"

    def test_dispatch_handles_stage3_reentry_failed(self):
        """S3-21: dispatch_command_status must handle stage3_reentry COMMAND_FAILED."""
        state = _make_state(
            stage="3",
            sub_stage="stub_generation",
            current_unit=1,
        )
        new = dispatch_command_status(state, "stage3_reentry", "COMMAND_FAILED")
        assert new is not None

    def test_dispatch_rejects_unknown_status_for_new_commands(self):
        """S3-21: new handlers must reject unknown status lines."""
        state = _make_state()
        import pytest
        for cmd in ("lessons_learned", "debug_commit", "stage3_reentry"):
            with pytest.raises(ValueError, match="Unknown status"):
                dispatch_command_status(state, cmd, "BOGUS_STATUS")

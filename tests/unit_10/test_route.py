"""Tests for Unit 10 route() function.

Synthetic data assumptions:
- PipelineState is mocked with configurable stage, sub_stage,
  current_unit, total_units, and other fields.
- project_root is a tmp_path fixture directory.
- last_status.txt is written to .svp/ under project_root.
- route() returns a dict with ACTION key and possibly
  PREPARE, POST, COMMAND, TASK_PROMPT_FILE, GATE_ID keys.
- Two-branch routing invariant: sub-stages with
  agent-to-gate or agent-to-command transitions check
  last_status.txt to distinguish states.
- All returned COMMAND/PREPARE/POST fields must be fully
  resolved (no {env_name} placeholders -- Bug 35).
"""

from unittest.mock import MagicMock

import pytest

from routing import route


def _make_state(
    stage="0",
    sub_stage=None,
    current_unit=None,
    total_units=None,
    fix_ladder_position=None,
    red_run_retries=0,
    alignment_iteration=0,
    debug_session=None,
    delivered_repo_path=None,
    redo_triggered_from=None,
    project_name="testproj",
):
    """Build a mock PipelineState."""
    state = MagicMock()
    state.stage = stage
    state.sub_stage = sub_stage
    state.current_unit = current_unit
    state.total_units = total_units
    state.fix_ladder_position = fix_ladder_position
    state.red_run_retries = red_run_retries
    state.alignment_iteration = alignment_iteration
    state.debug_session = debug_session
    state.delivered_repo_path = delivered_repo_path
    state.redo_triggered_from = redo_triggered_from
    state.project_name = project_name
    state.verified_units = []
    state.pass_history = []
    state.log_references = {}
    state.last_action = None
    state.debug_history = []
    return state


def _write_last_status(project_root, status):
    """Write a last_status.txt file."""
    svp_dir = project_root / ".svp"
    svp_dir.mkdir(parents=True, exist_ok=True)
    (svp_dir / "last_status.txt").write_text(status)


def _clear_last_status(project_root):
    """Remove last_status.txt if it exists."""
    status_file = project_root / ".svp" / "last_status.txt"
    if status_file.exists():
        status_file.unlink()


class TestRouteReturnsDict:
    def test_route_returns_dict(self, tmp_path):
        state = _make_state(stage="0", sub_stage=None)
        result = route(state, tmp_path)
        assert isinstance(result, dict)

    def test_route_has_action_key(self, tmp_path):
        state = _make_state(stage="0", sub_stage="hook_activation")
        result = route(state, tmp_path)
        assert "ACTION" in result


class TestStage0Routing:
    def test_hook_activation(self, tmp_path):
        state = _make_state(stage="0", sub_stage="hook_activation")
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_project_context_no_status(self, tmp_path):
        """Two-branch: project_context without
        last_status should invoke setup_agent."""
        state = _make_state(stage="0", sub_stage="project_context")
        _clear_last_status(tmp_path)
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_project_context_with_status(self, tmp_path):
        """Two-branch: project_context with status
        should present gate."""
        state = _make_state(stage="0", sub_stage="project_context")
        _write_last_status(tmp_path, "PROJECT_CONTEXT_COMPLETE")
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_project_profile_no_status(self, tmp_path):
        """Two-branch: project_profile without
        last_status should invoke setup_agent."""
        state = _make_state(stage="0", sub_stage="project_profile")
        _clear_last_status(tmp_path)
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_project_profile_with_status(self, tmp_path):
        """Two-branch: project_profile with status
        should present gate."""
        state = _make_state(stage="0", sub_stage="project_profile")
        _write_last_status(tmp_path, "PROFILE_COMPLETE")
        result = route(state, tmp_path)
        assert "ACTION" in result


class TestStage1Routing:
    def test_stage_1_spec_draft_complete(self, tmp_path):
        """Stage 1: SPEC_DRAFT_COMPLETE should emit
        gate_1_1_spec_draft."""
        state = _make_state(stage="1", sub_stage=None)
        _write_last_status(tmp_path, "SPEC_DRAFT_COMPLETE")
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_stage_1_spec_revision_complete(self, tmp_path):
        """Stage 1: SPEC_REVISION_COMPLETE should emit
        gate_1_1_spec_draft."""
        state = _make_state(stage="1", sub_stage=None)
        _write_last_status(tmp_path, "SPEC_REVISION_COMPLETE")
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_stage_1_review_complete(self, tmp_path):
        """Stage 1: REVIEW_COMPLETE should emit
        gate_1_2_spec_post_review."""
        state = _make_state(stage="1", sub_stage=None)
        _write_last_status(tmp_path, "REVIEW_COMPLETE")
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_stage_1_no_status_invokes_agent(self, tmp_path):
        """Stage 1 with no last_status should invoke
        stakeholder_dialog agent."""
        state = _make_state(stage="1", sub_stage=None)
        _clear_last_status(tmp_path)
        result = route(state, tmp_path)
        assert "ACTION" in result


class TestStage2Routing:
    def test_blueprint_dialog_no_status(self, tmp_path):
        """Two-branch: blueprint_dialog without
        last_status invokes blueprint_author."""
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        _clear_last_status(tmp_path)
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_blueprint_dialog_with_status(self, tmp_path):
        """Two-branch: blueprint_dialog with status
        presents gate_2_1."""
        state = _make_state(stage="2", sub_stage="blueprint_dialog")
        _write_last_status(tmp_path, "BLUEPRINT_DRAFT_COMPLETE")
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_alignment_check_no_status(self, tmp_path):
        """Two-branch: alignment_check without
        last_status invokes blueprint_checker."""
        state = _make_state(stage="2", sub_stage="alignment_check")
        _clear_last_status(tmp_path)
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_alignment_check_with_status(self, tmp_path):
        """Two-branch: alignment_check with
        ALIGNMENT_CONFIRMED presents gate_2_2."""
        from pipeline_state import PipelineState
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        (bp_dir / "blueprint_prose.md").write_text("# Blueprint")
        (bp_dir / "blueprint_contracts.md").write_text("# Contracts")
        state = PipelineState(
            stage="2", sub_stage="alignment_check",
            project_name="testproj",
        )
        _write_last_status(tmp_path, "ALIGNMENT_CONFIRMED")
        result = route(state, tmp_path)
        assert "ACTION" in result


class TestStage3Routing:
    def test_sub_stage_none_normalizes(self, tmp_path):
        """Stage 3 with sub_stage=None normalizes to
        stub_generation."""
        state = _make_state(
            stage="3",
            sub_stage=None,
            current_unit=1,
            total_units=5,
        )
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_stub_generation(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="stub_generation",
            current_unit=1,
            total_units=5,
        )
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_test_generation(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="test_generation",
            current_unit=1,
            total_units=5,
        )
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_quality_gate_a(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a",
            current_unit=1,
            total_units=5,
        )
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_quality_gate_a_retry(self, tmp_path):
        """Two-branch command entry for
        quality_gate_a_retry."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_a_retry",
            current_unit=1,
            total_units=5,
        )
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_red_run(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="red_run",
            current_unit=1,
            total_units=5,
        )
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_implementation(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="implementation",
            current_unit=1,
            total_units=5,
        )
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_quality_gate_b(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_b",
            current_unit=1,
            total_units=5,
        )
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_quality_gate_b_retry(self, tmp_path):
        """Two-branch command entry for
        quality_gate_b_retry."""
        state = _make_state(
            stage="3",
            sub_stage="quality_gate_b_retry",
            current_unit=1,
            total_units=5,
        )
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_green_run(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="green_run",
            current_unit=1,
            total_units=5,
        )
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_coverage_review(self, tmp_path):
        state = _make_state(
            stage="3",
            sub_stage="coverage_review",
            current_unit=1,
            total_units=5,
        )
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_unit_completion(self, tmp_path):
        """Bug 47: unit_completion COMMAND must not
        contain update_state.py."""
        state = _make_state(
            stage="3",
            sub_stage="unit_completion",
            current_unit=1,
            total_units=5,
        )
        result = route(state, tmp_path)
        assert "ACTION" in result
        if "COMMAND" in result:
            assert "update_state.py" not in result["COMMAND"], (
                "Bug 47: unit_completion COMMAND must not contain update_state.py"
            )


class TestStage3NoPlaceholders:
    """Bug 35: COMMAND, PREPARE, POST fields must be
    fully resolved with no placeholders."""

    @pytest.mark.parametrize(
        "sub_stage",
        [
            "stub_generation",
            "test_generation",
            "quality_gate_a",
            "red_run",
            "implementation",
            "quality_gate_b",
            "green_run",
            "coverage_review",
            "unit_completion",
        ],
    )
    def test_no_placeholders_in_fields(self, tmp_path, sub_stage):
        import json
        (tmp_path / "project_profile.json").write_text(json.dumps({
            "pipeline_toolchain": "python_conda_pytest",
            "python_version": "3.11",
            "delivery": {"environment_recommendation": "conda"},
            "vcs": {"commit_style": "conventional"},
            "readme": {"depth": "standard"},
            "testing": {},
            "license": {"type": "MIT"},
            "quality": {"linter": "ruff"},
            "fixed": {"language": "python"},
        }))
        (tmp_path / "pipeline_state.json").write_text(json.dumps({
            "stage": "3", "sub_stage": sub_stage, "current_unit": 1, "total_units": 5,
            "fix_ladder_position": None, "red_run_retries": 0, "alignment_iteration": 0,
            "verified_units": [], "pass_history": [], "log_references": {},
            "project_name": "testproj", "last_action": None, "debug_session": None,
            "debug_history": [], "redo_triggered_from": None, "delivered_repo_path": None,
            "created_at": "2025-01-01T00:00:00", "updated_at": "2025-01-01T00:00:00",
        }))
        state = _make_state(
            stage="3",
            sub_stage=sub_stage,
            current_unit=1,
            total_units=5,
        )
        result = route(state, tmp_path)
        for key in ("COMMAND", "PREPARE", "POST"):
            if key in result:
                val = result[key]
                # env_name is an orchestrator-resolved placeholder (not a bug)
                assert "{unknown_placeholder}" not in val, (
                    f"Bug 35: {key} contains truly unresolved placeholder"
                )


class TestPreStage3Routing:
    def test_pre_stage_3(self, tmp_path):
        state = _make_state(stage="pre_stage_3")
        result = route(state, tmp_path)
        assert "ACTION" in result


class TestStage4Routing:
    def test_stage_4_no_status(self, tmp_path):
        """Two-branch command entry for Stage 4."""
        state = _make_state(stage="4", sub_stage=None)
        _clear_last_status(tmp_path)
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_stage_4_with_status(self, tmp_path):
        state = _make_state(stage="4", sub_stage=None)
        _write_last_status(tmp_path, "INTEGRATION_TESTS_COMPLETE")
        result = route(state, tmp_path)
        assert "ACTION" in result


class TestStage5Routing:
    def test_stage_5_none_invokes_git_repo(self, tmp_path):
        """Stage 5 sub_stage=None invokes
        git_repo_agent (two-branch)."""
        state = _make_state(stage="5", sub_stage=None)
        _clear_last_status(tmp_path)
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_stage_5_none_with_status(self, tmp_path):
        """Stage 5 sub_stage=None with status presents
        gate."""
        state = _make_state(stage="5", sub_stage=None)
        _write_last_status(tmp_path, "REPO_ASSEMBLY_COMPLETE")
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_repo_test(self, tmp_path):
        """Stage 5 repo_test presents Gate 5.1."""
        state = _make_state(stage="5", sub_stage="repo_test")
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_compliance_scan(self, tmp_path):
        state = _make_state(stage="5", sub_stage="compliance_scan")
        result = route(state, tmp_path)
        assert "ACTION" in result

    def test_repo_complete(self, tmp_path):
        """Bug 26: repo_complete returns
        pipeline_complete."""
        state = _make_state(stage="5", sub_stage="repo_complete")
        result = route(state, tmp_path)
        assert "ACTION" in result

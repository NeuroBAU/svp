"""Regression tests for S3-44 and S3-45.

S3-44: ORACLE_ALL_CLEAR must exit the oracle session directly (via
       complete_oracle_session with "all_clear"), NOT present Gate 7B.
       Gate 7B is exclusively for ORACLE_FIX_APPLIED.
S3-45: Gates gate_5_2_assembly_exhausted, gate_5_3_unused_functions,
       and gate_4_1a must be routable via their respective sub_stage
       values in route().
"""

import json
from pathlib import Path

from pipeline_state import PipelineState
from routing import dispatch_agent_status, route


def _make_state(**overrides):
    """Build a minimal PipelineState with defaults."""
    defaults = {
        "stage": "5",
        "sub_stage": "repo_complete",
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
# S3-44: ORACLE_ALL_CLEAR must exit, not present Gate 7B
# ---------------------------------------------------------------------------


def test_oracle_all_clear_does_not_present_gate_b(tmp_path):
    """S3-44: ORACLE_ALL_CLEAR must exit, not present Gate 7B."""
    state_dict = {
        "stage": "5",
        "sub_stage": "repo_complete",
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
        "oracle_session_active": True,
        "oracle_phase": "green_run",
        "oracle_test_project": "test-proj/",
        "oracle_run_count": 1,
        "oracle_nested_session_path": None,
        "state_hash": None,
        "spec_revision_count": 0,
        "pass": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    project_root = _setup_project_root(tmp_path, state_dict, "ORACLE_ALL_CLEAR")
    result = route(project_root)

    assert result["action_type"] == "pipeline_complete", (
        f"S3-44 regression: ORACLE_ALL_CLEAR must produce pipeline_complete, "
        f"got {result['action_type']}"
    )
    assert result.get("gate_id") != "gate_7_b_fix_plan_review", (
        "S3-44 regression: ORACLE_ALL_CLEAR must NOT present Gate 7B"
    )


def test_oracle_fix_applied_presents_gate_b(tmp_path):
    """S3-44: ORACLE_FIX_APPLIED must present Gate 7B."""
    state_dict = {
        "stage": "5",
        "sub_stage": "repo_complete",
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
        "oracle_session_active": True,
        "oracle_phase": "green_run",
        "oracle_test_project": "test-proj/",
        "oracle_run_count": 1,
        "oracle_nested_session_path": None,
        "state_hash": None,
        "spec_revision_count": 0,
        "pass": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    project_root = _setup_project_root(tmp_path, state_dict, "ORACLE_FIX_APPLIED")
    result = route(project_root)

    assert result["action_type"] == "human_gate", (
        f"S3-44 regression: ORACLE_FIX_APPLIED must present a gate, "
        f"got {result['action_type']}"
    )
    assert result["gate_id"] == "gate_7_b_fix_plan_review", (
        f"S3-44 regression: ORACLE_FIX_APPLIED must present Gate 7B, "
        f"got {result.get('gate_id')}"
    )


def test_oracle_all_clear_dispatch_sets_exit_phase(tmp_path):
    """S3-44: dispatch_agent_status for ORACLE_ALL_CLEAR must set oracle_phase to 'exit'."""
    state = _make_state(
        oracle_session_active=True,
        oracle_phase="green_run",
        oracle_test_project="test-proj/",
        oracle_run_count=1,
    )
    new = dispatch_agent_status(state, "oracle_agent", "ORACLE_ALL_CLEAR", tmp_path)
    assert new.oracle_phase == "exit", (
        f"S3-44 regression: ORACLE_ALL_CLEAR dispatch must set oracle_phase to 'exit', "
        f"got {new.oracle_phase!r}"
    )


def test_oracle_fix_applied_dispatch_sets_gate_b_phase(tmp_path):
    """S3-44: dispatch_agent_status for ORACLE_FIX_APPLIED must set oracle_phase to 'gate_b'."""
    state = _make_state(
        oracle_session_active=True,
        oracle_phase="green_run",
        oracle_test_project="test-proj/",
        oracle_run_count=1,
    )
    new = dispatch_agent_status(state, "oracle_agent", "ORACLE_FIX_APPLIED", tmp_path)
    assert new.oracle_phase == "gate_b", (
        f"S3-44 regression: ORACLE_FIX_APPLIED dispatch must set oracle_phase to 'gate_b', "
        f"got {new.oracle_phase!r}"
    )


# ---------------------------------------------------------------------------
# S3-45: Unreachable gates must be routable via sub_stage
# ---------------------------------------------------------------------------


def test_gate_5_2_routable(tmp_path):
    """S3-45: gate_5_2_assembly_exhausted must be routable via sub_stage."""
    state_dict = {
        "stage": "5",
        "sub_stage": "gate_5_2",
        "current_unit": None,
        "total_units": 10,
        "verified_units": [],
        "alignment_iterations": 0,
        "fix_ladder_position": None,
        "red_run_retries": 3,
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "oracle_session_active": False,
        "oracle_phase": None,
        "oracle_test_project": None,
        "oracle_run_count": 0,
        "oracle_nested_session_path": None,
        "state_hash": None,
        "spec_revision_count": 0,
        "pass": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    project_root = _setup_project_root(tmp_path, state_dict, "")
    result = route(project_root)

    assert result["action_type"] == "human_gate", (
        f"S3-45 regression: gate_5_2 sub_stage must present a gate, "
        f"got {result['action_type']}"
    )
    assert result["gate_id"] == "gate_5_2_assembly_exhausted", (
        f"S3-45 regression: gate_5_2 sub_stage must present gate_5_2_assembly_exhausted, "
        f"got {result.get('gate_id')}"
    )


def test_gate_5_3_routable(tmp_path):
    """S3-45: gate_5_3_unused_functions must be routable via sub_stage."""
    state_dict = {
        "stage": "5",
        "sub_stage": "gate_5_3",
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
        "oracle_session_active": False,
        "oracle_phase": None,
        "oracle_test_project": None,
        "oracle_run_count": 0,
        "oracle_nested_session_path": None,
        "state_hash": None,
        "spec_revision_count": 0,
        "pass": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    project_root = _setup_project_root(tmp_path, state_dict, "")
    result = route(project_root)

    assert result["action_type"] == "human_gate", (
        f"S3-45 regression: gate_5_3 sub_stage must present a gate, "
        f"got {result['action_type']}"
    )
    assert result["gate_id"] == "gate_5_3_unused_functions", (
        f"S3-45 regression: gate_5_3 sub_stage must present gate_5_3_unused_functions, "
        f"got {result.get('gate_id')}"
    )


def test_gate_4_1a_routable(tmp_path):
    """S3-45: gate_4_1a must be routable via sub_stage."""
    state_dict = {
        "stage": "4",
        "sub_stage": "gate_4_1a",
        "current_unit": None,
        "total_units": 10,
        "verified_units": [],
        "alignment_iterations": 0,
        "fix_ladder_position": None,
        "red_run_retries": 1,
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "oracle_session_active": False,
        "oracle_phase": None,
        "oracle_test_project": None,
        "oracle_run_count": 0,
        "oracle_nested_session_path": None,
        "state_hash": None,
        "spec_revision_count": 0,
        "pass": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    project_root = _setup_project_root(tmp_path, state_dict, "")
    result = route(project_root)

    assert result["action_type"] == "human_gate", (
        f"S3-45 regression: gate_4_1a sub_stage must present a gate, "
        f"got {result['action_type']}"
    )
    assert result["gate_id"] == "gate_4_1a", (
        f"S3-45 regression: gate_4_1a sub_stage must present gate_4_1a, "
        f"got {result.get('gate_id')}"
    )

"""Regression tests for Bug S3-81: oracle_start must normalize ORACLE_REQUESTED sentinel.

S3-81: The /svp:oracle command writes "ORACLE_REQUESTED" to last_status.txt before
running update_state.py --command oracle_start. The oracle_start handler passed this
string as the test_project to enter_oracle_session(), causing _route_oracle() to skip
the deterministic test project selection gate (because "ORACLE_REQUESTED" is truthy).
Fix: normalize "ORACLE_REQUESTED" to empty string in the oracle_start handler.

Tests:
1. oracle_start with "ORACLE_REQUESTED" normalizes to empty test_project.
2. oracle_start with a real path preserves it.
3. oracle_start with empty string preserves empty.
4. End-to-end: after oracle_start with "ORACLE_REQUESTED", routing shows selection gate.
"""

import json
from pathlib import Path

from pipeline_state import PipelineState
from routing import dispatch_command_status, route


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**overrides):
    """Build a minimal PipelineState with sensible defaults."""
    defaults = {
        "stage": "5",
        "sub_stage": "pass_transition",
        "current_unit": None,
        "total_units": 29,
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
        "oracle_modification_count": 0,
        "state_hash": None,
        "spec_revision_count": 0,
        "pass_": 2,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


def _state_to_json(state):
    """Convert PipelineState to a JSON-serializable dict for disk."""
    from dataclasses import asdict

    data = asdict(state)
    result = {}
    for key, value in data.items():
        if key == "pass_":
            result["pass"] = value
        else:
            result[key] = value
    return result


def _setup_project_root(tmp_path, state, last_status=""):
    """Create a minimal project root with pipeline_state.json and last_status.txt."""
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(exist_ok=True)
    state_dict = _state_to_json(state)
    (svp_dir / "pipeline_state.json").write_text(json.dumps(state_dict, indent=2))
    (svp_dir / "last_status.txt").write_text(last_status)
    (tmp_path / "svp_config.json").write_text(json.dumps({"iteration_limit": 3}))
    return tmp_path


# ---------------------------------------------------------------------------
# 1. oracle_start normalizes "ORACLE_REQUESTED" to empty
# ---------------------------------------------------------------------------


def test_oracle_start_normalizes_oracle_requested():
    """dispatch_command_status("oracle_start", "ORACLE_REQUESTED") must yield empty test_project."""
    state = _make_state()
    new_state = dispatch_command_status(state, "oracle_start", "ORACLE_REQUESTED")
    assert new_state.oracle_session_active is True, (
        "oracle_start must activate oracle session"
    )
    assert not new_state.oracle_test_project, (
        f"Expected empty oracle_test_project, got {new_state.oracle_test_project!r}. "
        "ORACLE_REQUESTED sentinel must be normalized to empty string."
    )


# ---------------------------------------------------------------------------
# 2. oracle_start preserves real path
# ---------------------------------------------------------------------------


def test_oracle_start_preserves_real_path():
    """dispatch_command_status("oracle_start", "docs/") must preserve the path."""
    state = _make_state()
    new_state = dispatch_command_status(state, "oracle_start", "docs/")
    assert new_state.oracle_session_active is True
    assert new_state.oracle_test_project == "docs/", (
        f"Expected 'docs/', got {new_state.oracle_test_project!r}"
    )


# ---------------------------------------------------------------------------
# 3. oracle_start with empty string preserved
# ---------------------------------------------------------------------------


def test_oracle_start_empty_string_preserved():
    """dispatch_command_status("oracle_start", "") must leave test_project empty."""
    state = _make_state()
    new_state = dispatch_command_status(state, "oracle_start", "")
    assert new_state.oracle_session_active is True
    assert not new_state.oracle_test_project, (
        f"Expected empty oracle_test_project, got {new_state.oracle_test_project!r}"
    )


# ---------------------------------------------------------------------------
# 4. End-to-end: after ORACLE_REQUESTED, routing shows selection gate
# ---------------------------------------------------------------------------


def test_route_after_oracle_requested_shows_selection(tmp_path):
    """After oracle_start with ORACLE_REQUESTED, routing must present test project selection."""
    # Simulate the command entry: oracle_start with ORACLE_REQUESTED
    state = _make_state()
    new_state = dispatch_command_status(state, "oracle_start", "ORACLE_REQUESTED")

    # Now route with the resulting state
    project_root = _setup_project_root(tmp_path, new_state, last_status="ORACLE_REQUESTED")
    result = route(project_root)
    assert result["action_type"] == "oracle_select_test_project", (
        f"Expected oracle_select_test_project, got {result['action_type']}. "
        "After ORACLE_REQUESTED sentinel, routing must present the selection gate."
    )

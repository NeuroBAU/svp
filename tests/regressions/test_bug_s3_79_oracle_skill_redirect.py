"""Regression tests for Bug S3-79: /svp:oracle skill must be a thin redirect.

S3-79: The /svp:oracle skill definition delegated test project list construction
to the orchestrator via instructional text (scan docs/ and examples/). This
bypassed the routing script's deterministic oracle_select_test_project action
block (fixed in S3-76). Fix: reduce the skill to a thin state-transition trigger
that enters the oracle session and redirects to the routing script.

Tests:
1. Skill definition does NOT contain directory-scanning instructions.
2. Skill definition references the routing script.
3. Skill definition contains "Do NOT scan directories".
4. oracle_start command with empty status_line transitions to oracle_session_active=True.
5. Routing script's oracle_select_test_project reminder contains "F-mode".
"""

import json
from pathlib import Path

import pytest

from src.unit_5.stub import PipelineState
from src.unit_14.stub import dispatch_command_status, route
from src.unit_25.stub import COMMAND_DEFINITIONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**overrides):
    defaults = {
        "stage": "5",
        "sub_stage": "repo_complete",
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
        "pass_": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


def _state_to_json(state):
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
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(exist_ok=True)
    state_dict = _state_to_json(state)
    (svp_dir / "pipeline_state.json").write_text(json.dumps(state_dict, indent=2))
    (svp_dir / "last_status.txt").write_text(last_status)
    (tmp_path / "svp_config.json").write_text(json.dumps({"iteration_limit": 3}))
    return tmp_path


# ---------------------------------------------------------------------------
# 1. Skill definition must NOT contain directory-scanning instructions
# ---------------------------------------------------------------------------


def test_skill_no_directory_scanning_from_docs():
    """Skill must not tell orchestrator to scan docs/ directory."""
    defn = COMMAND_DEFINITIONS["svp_oracle"]
    assert "from the `docs/`" not in defn, (
        "Skill definition still contains directory-scanning instruction for docs/"
    )


def test_skill_no_directory_scanning_from_examples():
    """Skill must not tell orchestrator to scan examples/ directory."""
    defn = COMMAND_DEFINITIONS["svp_oracle"]
    assert "from the `examples/`" not in defn, (
        "Skill definition still contains directory-scanning instruction for examples/"
    )


def test_skill_no_numbered_list_instruction():
    """Skill must not instruct orchestrator to build a numbered list."""
    defn = COMMAND_DEFINITIONS["svp_oracle"]
    assert "numbered list of available test projects" not in defn, (
        "Skill definition still delegates list construction to orchestrator"
    )


# ---------------------------------------------------------------------------
# 2. Skill definition must redirect to routing script
# ---------------------------------------------------------------------------


def test_skill_references_routing_script():
    """Skill must reference routing.py for the action cycle."""
    defn = COMMAND_DEFINITIONS["svp_oracle"]
    assert "routing.py" in defn, (
        "Skill definition must redirect to the routing script"
    )


# ---------------------------------------------------------------------------
# 3. Skill definition must prohibit directory scanning
# ---------------------------------------------------------------------------


def test_skill_prohibits_directory_scanning():
    """Skill must explicitly prohibit directory scanning."""
    defn = COMMAND_DEFINITIONS["svp_oracle"]
    assert "Do NOT scan directories" in defn, (
        "Skill definition must contain explicit prohibition against directory scanning"
    )


# ---------------------------------------------------------------------------
# 4. oracle_start with empty status_line enters oracle session
# ---------------------------------------------------------------------------


def test_oracle_start_empty_enters_session():
    """oracle_start command with empty test_project must enter oracle session."""
    state = _make_state()
    new_state = dispatch_command_status(state, "oracle_start", "")
    assert new_state.oracle_session_active is True, (
        "oracle_start with empty test_project must set oracle_session_active=True"
    )
    assert new_state.oracle_phase == "dry_run", (
        "oracle_start must set oracle_phase to dry_run"
    )
    assert new_state.oracle_run_count == 1, (
        "oracle_start must increment oracle_run_count"
    )


def test_oracle_start_empty_leaves_test_project_empty():
    """oracle_start with empty test_project must leave oracle_test_project empty."""
    state = _make_state()
    new_state = dispatch_command_status(state, "oracle_start", "")
    assert not new_state.oracle_test_project, (
        "oracle_start with empty test_project must leave oracle_test_project empty"
    )


# ---------------------------------------------------------------------------
# 5. Routing script's oracle_select_test_project contains F-mode
# ---------------------------------------------------------------------------


def test_oracle_select_contains_fmode(tmp_path):
    """oracle_select_test_project reminder must contain hardcoded F-mode entry."""
    state = _make_state(
        oracle_session_active=True,
        oracle_phase="dry_run",
        oracle_test_project="",
    )
    project_root = _setup_project_root(tmp_path, state, last_status="")
    result = route(project_root)
    assert result["action_type"] == "oracle_select_test_project", (
        f"Expected oracle_select_test_project, got {result['action_type']}"
    )
    reminder = result.get("reminder", "")
    assert "F-mode" in reminder, (
        "oracle_select_test_project reminder must contain hardcoded F-mode entry"
    )

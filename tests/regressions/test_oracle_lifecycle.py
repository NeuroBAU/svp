"""Oracle (Stage 7) lifecycle tests -- end-to-end routing verification."""

import json
from pathlib import Path

import pytest

from pipeline_state import PipelineState
from state_transitions import (
    abandon_oracle_session,
    enter_debug_session,
    enter_oracle_session,
    complete_oracle_session,
    TransitionError,
)
from ledger_manager import append_oracle_run_entry, read_oracle_run_ledger
from routing import (
    dispatch_agent_status,
    dispatch_command_status,
    dispatch_gate_response,
    route,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**overrides):
    """Build a minimal PipelineState with sensible defaults."""
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
    """Convert PipelineState to a JSON-serializable dict for disk."""
    from dataclasses import asdict

    data = asdict(state)
    # Rename pass_ -> pass for JSON serialization
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
    # Also write svp_config.json for routing
    (tmp_path / "svp_config.json").write_text(json.dumps({"iteration_limit": 3}))
    return tmp_path


# ---------------------------------------------------------------------------
# 1. Test project selection gate
# ---------------------------------------------------------------------------


def test_project_selection_gate(tmp_path):
    """When oracle active, dry_run, no test project -> oracle_select_test_project."""
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


# ---------------------------------------------------------------------------
# 2. Dry run with test project -> invoke oracle_agent
# ---------------------------------------------------------------------------


def test_dry_run_with_test_project(tmp_path):
    """oracle_test_project set -> routing returns invoke_agent for oracle_agent."""
    state = _make_state(
        oracle_session_active=True,
        oracle_phase="dry_run",
        oracle_test_project="examples/gol-python",
    )
    project_root = _setup_project_root(tmp_path, state, last_status="")
    result = route(project_root)
    assert result["action_type"] == "invoke_agent", (
        f"Expected invoke_agent, got {result['action_type']}"
    )
    assert result.get("agent_type") == "oracle_agent", (
        f"Expected oracle_agent, got {result.get('agent_type')}"
    )


# ---------------------------------------------------------------------------
# 3. Gate 7.A APPROVE -> green_run
# ---------------------------------------------------------------------------


def test_gate_7a_approve_sets_green_run(tmp_path):
    """Gate 7.A APPROVE TRAJECTORY -> oracle_phase becomes green_run."""
    state = _make_state(
        oracle_session_active=True,
        oracle_phase="gate_a",
        oracle_test_project="examples/gol-python",
        oracle_run_count=1,
    )
    new = dispatch_gate_response(
        state, "gate_7_a_trajectory_review", "APPROVE TRAJECTORY", tmp_path
    )
    assert new.oracle_phase == "green_run", (
        f"Expected green_run, got {new.oracle_phase}"
    )


# ---------------------------------------------------------------------------
# 4. Gate 7.A MODIFY -> dry_run + counter incremented
# ---------------------------------------------------------------------------


def test_gate_7a_modify_stays_dry_run_and_increments(tmp_path):
    """Gate 7.A MODIFY TRAJECTORY -> stays dry_run, oracle_modification_count incremented."""
    state = _make_state(
        oracle_session_active=True,
        oracle_phase="gate_a",
        oracle_test_project="examples/gol-python",
        oracle_run_count=1,
        oracle_modification_count=0,
    )
    new = dispatch_gate_response(
        state, "gate_7_a_trajectory_review", "MODIFY TRAJECTORY", tmp_path
    )
    assert new.oracle_phase == "dry_run", (
        f"Expected dry_run, got {new.oracle_phase}"
    )
    assert new.oracle_modification_count == 1, (
        f"Expected modification_count=1, got {new.oracle_modification_count}"
    )


# ---------------------------------------------------------------------------
# 5. Modification bound (>= 3 produces warning)
# ---------------------------------------------------------------------------


def test_modification_bound_warning(tmp_path):
    """After 3 MODIFYs, routing includes warning about bound."""
    state = _make_state(
        oracle_session_active=True,
        oracle_phase="gate_a",
        oracle_test_project="examples/gol-python",
        oracle_run_count=1,
        oracle_modification_count=3,
    )
    project_root = _setup_project_root(tmp_path, state, last_status="")
    result = route(project_root)
    assert result["action_type"] == "human_gate"
    assert result["gate_id"] == "gate_7_a_trajectory_review"
    reminder = result.get("reminder", "")
    assert "WARNING" in reminder or "limit" in reminder.lower() or "3" in reminder, (
        f"Expected modification bound warning in reminder, got: {reminder}"
    )


# ---------------------------------------------------------------------------
# 6. Gate 7.A ABORT -> abandon_oracle_session
# ---------------------------------------------------------------------------


def test_gate_7a_abort_abandons_session(tmp_path):
    """Gate 7.A ABORT -> oracle_session_active=False."""
    state = _make_state(
        oracle_session_active=True,
        oracle_phase="gate_a",
        oracle_test_project="examples/gol-python",
        oracle_run_count=1,
    )
    new = dispatch_gate_response(
        state, "gate_7_a_trajectory_review", "ABORT", tmp_path
    )
    assert new.oracle_session_active is False, (
        "Gate 7.A ABORT must deactivate oracle session"
    )


# ---------------------------------------------------------------------------
# 7. ORACLE_ALL_CLEAR -> exit
# ---------------------------------------------------------------------------


def test_oracle_all_clear_sets_exit_phase(tmp_path):
    """dispatch_agent_status oracle_agent ORACLE_ALL_CLEAR -> oracle_phase=exit."""
    state = _make_state(
        oracle_session_active=True,
        oracle_phase="green_run",
        oracle_test_project="examples/gol-python",
        oracle_run_count=1,
    )
    new = dispatch_agent_status(state, "oracle_agent", "ORACLE_ALL_CLEAR", tmp_path)
    assert new.oracle_phase == "exit", (
        f"Expected oracle_phase=exit, got {new.oracle_phase}"
    )


# ---------------------------------------------------------------------------
# 8. ORACLE_FIX_APPLIED -> gate_b
# ---------------------------------------------------------------------------


def test_oracle_fix_applied_sets_gate_b(tmp_path):
    """dispatch_agent_status oracle_agent ORACLE_FIX_APPLIED -> oracle_phase=gate_b."""
    state = _make_state(
        oracle_session_active=True,
        oracle_phase="green_run",
        oracle_test_project="examples/gol-python",
        oracle_run_count=1,
    )
    new = dispatch_agent_status(state, "oracle_agent", "ORACLE_FIX_APPLIED", tmp_path)
    assert new.oracle_phase == "gate_b", (
        f"Expected oracle_phase=gate_b, got {new.oracle_phase}"
    )


# ---------------------------------------------------------------------------
# 9. Gate 7.B APPROVE FIX -> enter_debug_session, oracle stays active
# ---------------------------------------------------------------------------


def test_gate_7b_approve_fix_enters_debug_session(tmp_path):
    """Gate 7.B APPROVE FIX -> enter_debug_session called, oracle_session_active stays True."""
    state = _make_state(
        oracle_session_active=True,
        oracle_phase="gate_b",
        oracle_test_project="examples/gol-python",
        oracle_run_count=1,
    )
    new = dispatch_gate_response(
        state, "gate_7_b_fix_plan_review", "APPROVE FIX", tmp_path
    )
    assert new.debug_session is not None, (
        "Gate 7.B APPROVE FIX must enter a debug session"
    )
    assert new.oracle_session_active is True, (
        "Oracle session must remain active during debug"
    )


# ---------------------------------------------------------------------------
# 10. Gate 7.B ABORT -> abandon oracle session
# ---------------------------------------------------------------------------


def test_gate_7b_abort_abandons_oracle(tmp_path):
    """Gate 7.B ABORT -> abandon_oracle_session called."""
    state = _make_state(
        oracle_session_active=True,
        oracle_phase="gate_b",
        oracle_test_project="examples/gol-python",
        oracle_run_count=1,
    )
    new = dispatch_gate_response(
        state, "gate_7_b_fix_plan_review", "ABORT", tmp_path
    )
    assert new.oracle_session_active is False, (
        "Gate 7.B ABORT must deactivate oracle session"
    )


# ---------------------------------------------------------------------------
# 11. Exit phase cleanup -> pipeline_complete, oracle_session_active=False
# ---------------------------------------------------------------------------


def test_exit_phase_completes_pipeline(tmp_path):
    """Route at exit phase -> pipeline_complete, oracle_session_active=False."""
    state = _make_state(
        oracle_session_active=True,
        oracle_phase="exit",
        oracle_test_project="examples/gol-python",
        oracle_run_count=1,
    )
    project_root = _setup_project_root(tmp_path, state, last_status="")
    result = route(project_root)
    assert result["action_type"] == "pipeline_complete", (
        f"Expected pipeline_complete at exit, got {result['action_type']}"
    )
    # Verify oracle session was deactivated by re-loading state
    reloaded = json.loads(
        (tmp_path / ".svp" / "pipeline_state.json").read_text()
    )
    assert reloaded["oracle_session_active"] is False, (
        "Oracle session must be deactivated after exit"
    )


# ---------------------------------------------------------------------------
# 12. oracle_start command
# ---------------------------------------------------------------------------


def test_oracle_start_command(tmp_path):
    """dispatch_command_status oracle_start enters oracle session with test_project."""
    state = _make_state(
        oracle_session_active=False,
        oracle_phase=None,
        oracle_test_project=None,
        oracle_run_count=0,
    )
    new = dispatch_command_status(state, "oracle_start", "examples/gol-python", None)
    assert new.oracle_session_active is True, (
        "oracle_start must activate oracle session"
    )
    assert new.oracle_test_project == "examples/gol-python", (
        f"Expected test_project=examples/gol-python, got {new.oracle_test_project}"
    )
    assert new.oracle_phase == "dry_run", (
        f"Expected oracle_phase=dry_run, got {new.oracle_phase}"
    )


# ---------------------------------------------------------------------------
# 13. Run ledger append/read
# ---------------------------------------------------------------------------


def test_oracle_run_ledger_append_and_read(tmp_path):
    """Test append_oracle_run_entry and read_oracle_run_ledger."""
    entry1 = {"run_number": 1, "test_project": "examples/gol-python", "exit_reason": "complete"}
    entry2 = {"run_number": 2, "test_project": "docs/", "exit_reason": "abort"}

    # Empty ledger
    entries = read_oracle_run_ledger(tmp_path)
    assert entries == [], "Empty ledger should return []"

    # Append and read
    append_oracle_run_entry(tmp_path, entry1)
    entries = read_oracle_run_ledger(tmp_path)
    assert len(entries) == 1
    assert entries[0]["run_number"] == 1
    assert "timestamp" in entries[0]

    # Append second entry
    append_oracle_run_entry(tmp_path, entry2)
    entries = read_oracle_run_ledger(tmp_path)
    assert len(entries) == 2
    assert entries[1]["run_number"] == 2


# ---------------------------------------------------------------------------
# 14. Nested session bootstrap
# ---------------------------------------------------------------------------


def test_bootstrap_oracle_nested_session(tmp_path):
    """_bootstrap_oracle_nested_session creates workspace directory."""
    # Create minimal project root structure
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir()
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    (specs_dir / "stakeholder_spec.md").write_text("# Spec")
    blueprint_dir = tmp_path / "blueprint"
    blueprint_dir.mkdir()
    (blueprint_dir / "blueprint_contracts.md").write_text("# Contracts")

    state = _make_state(
        oracle_session_active=True,
        oracle_phase="green_run",
        oracle_test_project="examples/gol-python",
        oracle_run_count=1,
        oracle_nested_session_path=None,
    )
    # Write state to disk so route() can load it
    state_dict = _state_to_json(state)
    (svp_dir / "pipeline_state.json").write_text(json.dumps(state_dict, indent=2))
    (svp_dir / "last_status.txt").write_text("")
    (tmp_path / "svp_config.json").write_text(json.dumps({"iteration_limit": 3}))

    # Call route() which should trigger _bootstrap_oracle_nested_session
    result = route(tmp_path)

    # After routing, the nested session path should be set in saved state
    reloaded = json.loads(
        (svp_dir / "pipeline_state.json").read_text()
    )
    assert reloaded.get("oracle_nested_session_path") is not None, (
        "Nested session path should be set after green_run bootstrap"
    )
    nested_path = Path(reloaded["oracle_nested_session_path"])
    assert nested_path.exists(), (
        f"Nested session workspace should exist at {nested_path}"
    )

"""Regression tests for Bug S3-119.

S3-119: /svp:bug could not bootstrap a Stage 6 debug session from
pipeline_complete. The spec (§12.18.13) mandates null -> "triage" on
/svp:bug entry but no code path implemented it. The prior
_SVP_BUG_DEFINITION documented a Group B 5-step action cycle
(prepare_task -> agent -> status -> update_state --phase -> routing),
none of which create the debug_session object.

The fix mirrors the /svp:oracle thin-trigger pattern (Bug S3-79):

1. New svp_bug_entry command in dispatch_command_status (unit 14)
   that calls enter_debug_session(state, 0), with guards for
   oracle_session_active and already-active debug_session.

2. _SVP_BUG_DEFINITION (unit 25) rewritten as a thin trigger that
   runs update_state.py --command svp_bug_entry, then routing.py.

This test file locks all five behaviors against regression:

- Test A: svp_bug_entry creates debug_session when null.
- Test B: svp_bug_entry refuses when debug_session already active.
- Test C: svp_bug_entry refuses when oracle_session_active.
- Test D: end-to-end bootstrap yields Gate 6.0 from pipeline_complete.
- Test E: _SVP_BUG_DEFINITION is a thin trigger (no prepare_task.py).
"""
import tempfile
from pathlib import Path

import pytest

from pipeline_state import PipelineState, save_state
from routing import dispatch_command_status, route


# ---------------------------------------------------------------------------
# Test A: svp_bug_entry creates the debug session from a null baseline.
# ---------------------------------------------------------------------------


def test_svp_bug_entry_creates_debug_session_from_null():
    """dispatch_command_status('svp_bug_entry', ...) must create a
    debug_session with authorized=False, phase='triage', bug_number=0,
    matching spec §12.18.13 (null -> 'triage' transition).
    """
    state = PipelineState(
        stage="5",
        sub_stage="repo_complete",
        total_units=29,
        pass_=2,
        debug_session=None,
    )
    new_state = dispatch_command_status(state, "svp_bug_entry", "")

    assert new_state.debug_session is not None, (
        "svp_bug_entry must create a debug_session object "
        "(spec §12.18.13: null -> 'triage')"
    )
    assert new_state.debug_session["authorized"] is False, (
        "New debug session must start unauthorized; Gate 6.0 authorizes "
        "via AUTHORIZE DEBUG response."
    )
    assert new_state.debug_session["phase"] == "triage", (
        "New debug session must start in triage phase."
    )
    assert new_state.debug_session["bug_number"] == 0, (
        "bug_number 0 is the placeholder convention; the triage agent "
        "assigns the real number from len(debug_history) + 1."
    )
    assert new_state.debug_session["classification"] is None
    assert new_state.debug_session["affected_units"] == []


# ---------------------------------------------------------------------------
# Test B: svp_bug_entry refuses when a debug_session is already active.
# ---------------------------------------------------------------------------


def test_svp_bug_entry_refuses_when_debug_session_active():
    """Spec §12.18.1: 'one debug session at a time'. svp_bug_entry must
    raise ValueError if debug_session is already populated, rather than
    silently overwriting an active session.
    """
    state = PipelineState(
        stage="5",
        sub_stage="repo_complete",
        total_units=29,
        pass_=2,
        debug_session={
            "authorized": True,
            "bug_number": 7,
            "classification": "single_unit",
            "affected_units": [14],
            "phase": "repair",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
        },
    )
    with pytest.raises(ValueError, match="already active"):
        dispatch_command_status(state, "svp_bug_entry", "")


# ---------------------------------------------------------------------------
# Test C: svp_bug_entry refuses when oracle session is active.
# ---------------------------------------------------------------------------


def test_svp_bug_entry_refuses_when_oracle_session_active():
    """Spec §35.3: /svp:bug is blocked for the human during active
    /svp:oracle sessions. The oracle enters debug sessions internally
    via Gate 7.B; the human must not race against it.
    """
    state = PipelineState(
        stage="5",
        sub_stage="repo_complete",
        total_units=29,
        pass_=2,
        debug_session=None,
        oracle_session_active=True,
    )
    with pytest.raises(ValueError, match="oracle"):
        dispatch_command_status(state, "svp_bug_entry", "")


# ---------------------------------------------------------------------------
# Test D: end-to-end bootstrap from pipeline_complete to Gate 6.0.
# ---------------------------------------------------------------------------


def test_svp_bug_entry_end_to_end_reaches_gate_6_0():
    """The end-to-end contract: from a clean pipeline_complete state
    with debug_session=None, invoking svp_bug_entry and then routing()
    must yield a human_gate action block with gate_id
    'gate_6_0_debug_permission'. This is the full bootstrap path the
    /svp:bug slash command will exercise.
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state = PipelineState(
            stage="5",
            sub_stage="repo_complete",
            total_units=29,
            pass_=2,
            debug_session=None,
            oracle_session_active=False,
        )
        new_state = dispatch_command_status(state, "svp_bug_entry", "")
        save_state(root, new_state)

        svp_dir = root / ".svp"
        svp_dir.mkdir(exist_ok=True)
        (svp_dir / "last_status.txt").write_text("")

        action = route(root)

        assert action["action_type"] == "human_gate", (
            "After svp_bug_entry, routing must present a human_gate "
            "(Gate 6.0 debug permission), not re-dispatch or fall "
            "through to pipeline_complete."
        )
        assert action["gate_id"] == "gate_6_0_debug_permission", (
            f"Expected gate_6_0_debug_permission, got {action.get('gate_id')}"
        )


# ---------------------------------------------------------------------------
# Test E: _SVP_BUG_DEFINITION is a thin state-transition trigger.
# ---------------------------------------------------------------------------


def test_svp_bug_definition_is_thin_state_trigger():
    """Per the Unit 25 invariant (Bug S3-79, extended by S3-119),
    /svp:bug's skill definition must be a thin state-transition
    trigger: run update_state.py --command svp_bug_entry, then
    routing.py. It must NOT contain the Group B 5-step cycle
    (prepare_task, spawn agent, write status, update_state --phase).
    That machinery lives in _route_debug.

    This test parses COMMAND_DEFINITIONS rather than the private
    _SVP_BUG_DEFINITION so it works from both workspace and delivered
    repo layouts.
    """
    from slash_commands import COMMAND_DEFINITIONS

    assert "svp_bug" in COMMAND_DEFINITIONS, (
        "svp_bug must be registered in COMMAND_DEFINITIONS"
    )
    body = COMMAND_DEFINITIONS["svp_bug"]

    assert "svp_bug_entry" in body, (
        "/svp:bug skill definition must reference the svp_bug_entry "
        "command — this is the bootstrap step that creates debug_session "
        "(Bug S3-119 fix)."
    )
    assert "prepare_task.py" not in body, (
        "/svp:bug is a thin state-transition trigger (Bug S3-79 + S3-119). "
        "It must not invoke prepare_task.py — _route_debug dispatches the "
        "bug_triage_agent via _agent_prepare_cmd after Gate 6.0 authorization."
    )
    assert "--phase bug_triage" not in body, (
        "/svp:bug must not use the --phase bug_triage dispatch path — "
        "the svp_bug_entry command is the single state-transition entry "
        "point for this command."
    )


# ---------------------------------------------------------------------------
# Test F: symmetry — /svp:oracle definition is also a thin trigger.
# ---------------------------------------------------------------------------


def test_svp_oracle_definition_is_thin_state_trigger_symmetry():
    """Symmetry lock: /svp:oracle was the first thin-trigger slash
    command (Bug S3-79). /svp:bug was added as the second (Bug S3-119).
    If either regresses to the 5-step pattern, this test fails.
    """
    from slash_commands import COMMAND_DEFINITIONS

    body = COMMAND_DEFINITIONS["svp_oracle"]
    assert "oracle_start" in body
    assert "prepare_task.py" not in body

"""Regression: debug/break-glass sessions must be exitable and bounded.

Audit 2026-07-06 (P2): human_authorize sessions had no scripted exit
(invoke_break_glass looped forever); stage3_rebuild_active recursed to
RecursionError at rebuild completion; gate_6_5 COMMIT APPROVED completed
the session before the debug_commit command could run (and COMMIT REJECTED
looped the gate); the repair/triage retry counters could never increment.
"""

from tests.regressions.helpers import make_state, read_state_dict, write_status

from routing import dispatch_command_status, dispatch_gate_response, route


def test_debug_session_complete_exits_break_glass(project_root):
    make_state(
        project_root,
        stage="1",
        sub_stage="spec_review",
        debug_session={
            "authorized": True,
            "source": "human_authorize",
            "mode": "bug",
            "phase": "triage",
        },
    )
    write_status(project_root, "DEBUG_SESSION_COMPLETE")

    action = route(project_root)

    assert action["action_type"] != "invoke_break_glass"
    saved = read_state_dict(project_root)
    assert saved["debug_session"] is None
    assert len(saved["debug_history"]) == 1


def test_stage3_rebuild_completion_transitions_to_reassembly(project_root):
    make_state(
        project_root,
        stage="3",
        sub_stage=None,
        current_unit=None,
        total_units=1,
        verified_units=[{"unit": 1}],
        debug_session={
            "authorized": True,
            "source": "bug_entry",
            "phase": "stage3_rebuild_active",
        },
    )
    write_status(project_root, "")

    action = route(project_root)  # must not RecursionError

    assert action["action_type"] == "invoke_agent"
    assert action["agent_type"] == "git_repo_agent"
    saved = read_state_dict(project_root)
    assert saved["debug_session"]["phase"] == "reassembly"
    assert saved["stage"] == "3"


def test_commit_approved_runs_debug_commit_then_completes_session(project_root):
    state = make_state(
        project_root,
        stage="5",
        sub_stage=None,
        debug_session={"authorized": True, "source": "bug_entry", "phase": "commit"},
    )
    write_status(project_root, "COMMIT APPROVED")

    new = dispatch_gate_response(
        state, "gate_6_5_debug_commit", "COMMIT APPROVED", project_root
    )
    assert new.debug_session is not None  # NOT completed at the gate POST

    from pipeline_state import save_state

    save_state(project_root, new)
    action = route(project_root)
    assert action["action_type"] == "run_command"
    assert action["command"] == "debug_commit"

    done = dispatch_command_status(
        new, "debug_commit", "COMMAND_SUCCEEDED", project_root=project_root
    )
    assert done.debug_session is None


def test_commit_rejected_returns_to_repair(project_root):
    state = make_state(
        project_root,
        stage="5",
        sub_stage=None,
        debug_session={"authorized": True, "source": "bug_entry", "phase": "commit"},
    )

    new = dispatch_gate_response(
        state, "gate_6_5_debug_commit", "COMMIT REJECTED", project_root
    )

    assert new.debug_session["phase"] == "repair"


def test_reclassify_bug_honored_even_at_refinement_limit(project_root):
    state = make_state(
        project_root,
        stage="5",
        sub_stage=None,
        debug_session={
            "authorized": True,
            "source": "bug_entry",
            "phase": "repair",
            "triage_refinement_count": 5,
        },
    )

    new = dispatch_gate_response(
        state, "gate_6_3_repair_exhausted", "RECLASSIFY BUG", project_root
    )

    assert new.debug_session["phase"] == "triage"
    assert new.debug_session["triage_refinement_count"] == 6


def test_completing_debug_during_oracle_flags_rebootstrap():
    from pipeline_state import PipelineState
    from state_transitions import complete_debug_session

    state = PipelineState(
        stage="5",
        oracle_session_active=True,
        oracle_nested_session_path="/tmp/nested",
        debug_session={"authorized": True, "phase": "commit"},
    )

    new = complete_debug_session(state)

    assert new.oracle_needs_rebootstrap is True
    assert new.debug_session is None


def test_completing_debug_outside_oracle_does_not_flag():
    from pipeline_state import PipelineState
    from state_transitions import complete_debug_session

    state = PipelineState(
        stage="5",
        debug_session={"authorized": True, "phase": "commit"},
    )

    new = complete_debug_session(state)

    assert new.oracle_needs_rebootstrap is False


def test_repair_failed_increments_counter_once_per_failure(project_root):
    make_state(
        project_root,
        stage="5",
        sub_stage=None,
        debug_session={
            "authorized": True,
            "source": "bug_entry",
            "phase": "repair",
        },
    )
    write_status(project_root, "REPAIR_FAILED")

    action = route(project_root)
    assert action["agent_type"] == "repair_agent"
    assert read_state_dict(project_root)["debug_session"]["repair_retry_count"] == 1

    # Status was cleared: a second routing pass re-invokes without
    # re-incrementing.
    action = route(project_root)
    assert action["agent_type"] == "repair_agent"
    assert read_state_dict(project_root)["debug_session"]["repair_retry_count"] == 1

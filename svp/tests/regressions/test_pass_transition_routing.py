"""Regression: the two-pass protocol must be reachable end-to-end.

Audit 2026-07-06 (P2): enter_pass_1 had no caller (Stage 5 completion of a
self-build emitted pipeline_complete); PROCEED TO PASS 2 never set
sub_stage="pass2_active" (Pass 2 silently skipped); nothing consumed the
Pass-2 completion; RUN ORACLE never cleared pass bookkeeping (post-pass2
gate re-presented forever).
"""

from tests.regressions.helpers import make_state, read_state_dict, write_profile, write_status

import sync_debug_docs
from pipeline_state import save_state
from routing import dispatch_gate_response, route


def test_self_build_repo_complete_enters_pass_1_and_presents_post_pass1_gate(
    project_root,
):
    write_profile(project_root, archetype="svp_architectural")
    make_state(project_root, stage="5", sub_stage="repo_complete")
    write_status(project_root, "")

    action = route(project_root)

    assert action["action_type"] == "human_gate"
    assert action["gate_id"] == "gate_pass_transition_post_pass1"
    saved = read_state_dict(project_root)
    assert saved["pass"] == 1
    assert saved["sub_stage"] == "pass_transition"


def test_non_self_build_repo_complete_still_completes_pipeline(project_root):
    write_profile(project_root, archetype="python_project")
    make_state(project_root, stage="5", sub_stage="repo_complete")
    write_status(project_root, "")

    action = route(project_root)

    assert action["action_type"] == "pipeline_complete"


def test_proceed_to_pass_2_activates_pass2_nested_session(project_root):
    state = make_state(
        project_root, stage="5", sub_stage="pass_transition", pass_=1
    )

    new = dispatch_gate_response(
        state,
        "gate_pass_transition_post_pass1",
        "PROCEED TO PASS 2",
        project_root,
    )

    assert new.pass_ == 2
    assert new.sub_stage == "pass2_active"
    save_state(project_root, new)
    action = route(project_root)
    assert action["action_type"] == "invoke_agent"
    assert action["agent_type"] == "pass2_nested"


def test_pass_2_complete_returns_to_pass_transition_gate(
    project_root, monkeypatch
):
    monkeypatch.setattr(
        sync_debug_docs,
        "sync_pass1_artifacts",
        lambda root: {"synced_files": [], "merged_files": []},
    )
    write_profile(project_root, archetype="svp_architectural")
    make_state(project_root, stage="5", sub_stage="pass2_active", pass_=2)
    write_status(project_root, "PASS_2_COMPLETE")

    action = route(project_root)

    assert action["action_type"] == "human_gate"
    assert action["gate_id"] == "gate_pass_transition_post_pass2"
    assert read_state_dict(project_root)["sub_stage"] == "pass_transition"


def test_run_oracle_clears_pass_so_post_oracle_routing_completes(project_root):
    state = make_state(
        project_root, stage="5", sub_stage="pass_transition", pass_=2
    )

    new = dispatch_gate_response(
        state,
        "gate_pass_transition_post_pass2",
        "RUN ORACLE",
        project_root,
    )

    assert new.oracle_session_active is True
    assert new.pass_ is None
    assert new.pass2_nested_session_path is None

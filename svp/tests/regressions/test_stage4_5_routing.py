"""Regression: Stage 4/5 gate and completion handling.

Audit 2026-07-06 (P2): gate_4_1 ASSEMBLY FIX was a copy-only no-op that
re-presented the gate forever; REPO_ASSEMBLY_COMPLETE never set
delivered_repo_path (the git_repo_agent dispatch handler was unreachable);
gate_2_3 RESTART SPEC / RETRY BLUEPRINT left the alignment budget spent.
"""

from tests.regressions.helpers import make_state, read_state_dict, write_profile, write_status

from pipeline_state import save_state
from routing import dispatch_gate_response, route


def test_gate_4_1_assembly_fix_reinvokes_integration_test_author(project_root):
    state = make_state(project_root, stage="4", sub_stage="gate_4_1")

    new = dispatch_gate_response(
        state, "gate_4_1_integration_failure", "ASSEMBLY FIX", project_root
    )

    assert new.sub_stage is None
    save_state(project_root, new)
    action = route(project_root)
    assert action["action_type"] == "invoke_agent"
    assert action["agent_type"] == "integration_test_author"


def test_repo_assembly_complete_sets_delivered_repo_path(project_root):
    write_profile(project_root, archetype="python_project", name="proj")
    delivered = project_root.parent / "proj-repo"
    delivered.mkdir()
    make_state(project_root, stage="5", sub_stage=None)
    write_status(project_root, "REPO_ASSEMBLY_COMPLETE")

    action = route(project_root)

    assert action["action_type"] == "human_gate"
    assert action["gate_id"] == "gate_5_1_repo_test"
    saved = read_state_dict(project_root)
    assert saved["delivered_repo_path"] == str(delivered.resolve())


def test_repo_assembly_complete_with_missing_destination_holds_pipeline(
    project_root,
):
    write_profile(project_root, archetype="python_project", name="proj")
    make_state(project_root, stage="5", sub_stage=None)
    write_status(project_root, "REPO_ASSEMBLY_COMPLETE")

    action = route(project_root)

    assert action["action_type"] == "pipeline_held"


def test_gate_2_3_restart_spec_resets_alignment_budget(project_root):
    state = make_state(
        project_root, stage="2", sub_stage="alignment_check",
        alignment_iterations=3,
    )

    new = dispatch_gate_response(
        state, "gate_2_3_alignment_exhausted", "RESTART SPEC", project_root
    )

    assert new.stage == "1"
    assert new.alignment_iterations == 0


def test_gate_2_3_retry_blueprint_resets_alignment_budget(project_root):
    state = make_state(
        project_root, stage="2", sub_stage="alignment_check",
        alignment_iterations=3,
    )

    new = dispatch_gate_response(
        state, "gate_2_3_alignment_exhausted", "RETRY BLUEPRINT", project_root
    )

    assert new.sub_stage == "blueprint_dialog"
    assert new.alignment_iterations == 0

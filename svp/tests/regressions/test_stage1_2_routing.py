"""Regression: Stage 1/2 routing fixes.

Audit 2026-07-06 (P2): gate_1_1 REVISE re-invoked the dialog agent in
fresh-draft mode (revision context lost); the S3-116/S3-158 blueprint
validators only lived in unreachable dispatch code; the statistical
correctness reviewer re-invoked forever (its done-flag setter was
unreachable).
"""

from tests.regressions.helpers import make_state, read_state_dict, write_status

import routing
from routing import dispatch_gate_response, route


def test_gate_1_1_revise_enters_targeted_spec_revision(project_root):
    state = make_state(project_root, stage="1", sub_stage=None)

    new = dispatch_gate_response(
        state, "gate_1_1_spec_draft", "REVISE", project_root
    )

    assert new.sub_stage == "targeted_spec_revision"
    from pipeline_state import save_state

    save_state(project_root, new)
    action = route(project_root)
    assert action["action_type"] == "invoke_agent"
    assert action["agent_type"] == "stakeholder_dialog"
    assert "targeted_revision" in action.get("prepare", "")


def test_blueprint_validation_violation_holds_before_gate_2_1(
    project_root, monkeypatch
):
    monkeypatch.setattr(
        routing, "_validate_blueprint_artifacts", lambda root: "VIOLATION X"
    )
    make_state(project_root, stage="2", sub_stage="blueprint_dialog")
    write_status(project_root, "BLUEPRINT_DRAFT_COMPLETE")

    action = route(project_root)

    assert action["action_type"] == "pipeline_held"
    assert "VIOLATION X" in action.get("message", "")


def test_blueprint_validation_pass_presents_gate_2_1(project_root, monkeypatch):
    monkeypatch.setattr(
        routing, "_validate_blueprint_artifacts", lambda root: None
    )
    make_state(project_root, stage="2", sub_stage="blueprint_dialog")
    write_status(project_root, "BLUEPRINT_DRAFT_COMPLETE")

    action = route(project_root)

    assert action["action_type"] == "human_gate"
    assert action["gate_id"] == "gate_2_1_blueprint_approval"


def test_blueprint_audit_warnings_do_not_block_gate_2_1(project_root, monkeypatch):
    """Warning-severity audit findings (e.g. 'stub not found' at Stage 2,
    where stubs cannot exist yet) must not hold the pipeline (P4)."""
    import structural_check

    monkeypatch.setattr(
        structural_check,
        "audit_blueprint_contracts",
        lambda root: [
            {
                "check": "reachability",
                "severity": "warning",
                "location": "Unit 1",
                "description": "stub file not found; skipping check",
            }
        ],
    )
    # Neutralize the heading validator (no blueprint dir in fixture).
    import blueprint_extractor

    monkeypatch.setattr(
        blueprint_extractor, "validate_unit_heading_format", lambda d: []
    )
    make_state(project_root, stage="2", sub_stage="blueprint_dialog")
    write_status(project_root, "BLUEPRINT_DRAFT_COMPLETE")

    action = route(project_root)

    assert action["action_type"] == "human_gate"
    assert action["gate_id"] == "gate_2_1_blueprint_approval"


def test_statistical_reviewer_runs_exactly_once(project_root):
    make_state(
        project_root,
        stage="2",
        sub_stage="blueprint_review",
        requires_statistical_analysis=True,
        statistical_review_done=False,
    )
    write_status(project_root, "REVIEW_COMPLETE")

    first = route(project_root)
    assert first["action_type"] == "invoke_agent"
    assert first["agent_type"] == "statistical_correctness_reviewer"
    assert read_state_dict(project_root)["statistical_review_done"] is True

    # The specialist's own REVIEW_COMPLETE now reaches gate 2.2 instead of
    # re-invoking the specialist forever.
    write_status(project_root, "REVIEW_COMPLETE")
    second = route(project_root)
    assert second["action_type"] == "human_gate"
    assert second["gate_id"] == "gate_2_2_blueprint_post_review"

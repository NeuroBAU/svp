"""Regression: gate_1_2_spec_post_review REVISE must route to targeted spec revision.

The original handler cleared last_status and copied state without changing
sub_stage, leaving the pipeline at sub_stage="spec_review" — whose fallback
re-invokes the stakeholder reviewer forever. REVISE at Gate 1.2 must instead
enter the "targeted_spec_revision" sub-stage so routing dispatches the
stakeholder dialog agent in targeted_revision mode (mirroring the Gate 2.3
"REVISE SPEC" handler).
"""

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = str(Path(__file__).resolve().parents[2] / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from pipeline_state import PipelineState, save_state  # noqa: E402
from routing import dispatch_gate_response, route  # noqa: E402


@pytest.fixture()
def stage_1_spec_review_root(tmp_path):
    """A minimal project root sitting at Stage 1, sub_stage=spec_review."""
    (tmp_path / ".svp").mkdir()
    state = PipelineState(stage="1", sub_stage="spec_review")
    save_state(tmp_path, state)
    return tmp_path


def _state(sub_stage="spec_review"):
    return PipelineState(stage="1", sub_stage=sub_stage)


def test_gate_1_2_revise_enters_targeted_spec_revision(stage_1_spec_review_root):
    new = dispatch_gate_response(
        _state(),
        "gate_1_2_spec_post_review",
        "REVISE",
        stage_1_spec_review_root,
    )
    assert new.sub_stage == "targeted_spec_revision"
    assert new.stage == "1"


def test_gate_1_2_revise_then_routing_dispatches_stakeholder_dialog_revision(
    stage_1_spec_review_root,
):
    new = dispatch_gate_response(
        _state(),
        "gate_1_2_spec_post_review",
        "REVISE",
        stage_1_spec_review_root,
    )
    save_state(stage_1_spec_review_root, new)

    action = route(stage_1_spec_review_root)

    assert action["action_type"] == "invoke_agent"
    assert action["agent_type"] == "stakeholder_dialog"
    assert "targeted_revision" in action.get("prepare", "")


def test_gate_1_2_approve_still_advances_to_checklist_generation(
    stage_1_spec_review_root,
):
    new = dispatch_gate_response(
        _state(),
        "gate_1_2_spec_post_review",
        "APPROVE",
        stage_1_spec_review_root,
    )
    assert new.sub_stage == "checklist_generation"


def test_gate_1_2_fresh_review_still_reenters_spec_review(stage_1_spec_review_root):
    new = dispatch_gate_response(
        _state(),
        "gate_1_2_spec_post_review",
        "FRESH REVIEW",
        stage_1_spec_review_root,
    )
    assert new.sub_stage == "spec_review"

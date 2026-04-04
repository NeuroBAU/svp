"""Regression tests for Bug S3-17: gate dispatch routing corrections."""
import json
import tempfile

from src.unit_5.stub import PipelineState, save_state
from src.unit_14.stub import dispatch_gate_response, route
from pathlib import Path
import pytest


def _state(**overrides):
    defaults = dict(
        stage="0", sub_stage=None, current_unit=None,
        total_units=0, verified_units=[], alignment_iterations=0,
        fix_ladder_position=None, red_run_retries=0, pass_history=[],
        debug_session=None, debug_history=[], redo_triggered_from=None,
        delivered_repo_path=None,
    )
    defaults.update(overrides)
    return PipelineState(**defaults)


def test_gate_1_1_fresh_review_does_not_route_to_dialog():
    """S3-17: FRESH REVIEW at Gate 1.1 must not leave sub_stage as None (which routes to dialog)."""
    state = _state(stage="1", sub_stage=None)
    new = dispatch_gate_response(state, "gate_1_1_spec_draft", "FRESH REVIEW", Path("."))
    # sub_stage must be set to something that routes to reviewer, not None
    assert new.sub_stage is not None, "FRESH REVIEW must set sub_stage to route to reviewer"


def test_gate_1_1_fresh_review_routes_to_spec_review():
    """S3-17: FRESH REVIEW at Gate 1.1 must set sub_stage to 'spec_review'."""
    state = _state(stage="1", sub_stage=None)
    new = dispatch_gate_response(state, "gate_1_1_spec_draft", "FRESH REVIEW", Path("."))
    assert new.sub_stage == "spec_review", (
        f"FRESH REVIEW must set sub_stage='spec_review', got {new.sub_stage!r}"
    )


def test_gate_1_2_fresh_review_routes_to_spec_review():
    """S3-17: FRESH REVIEW at Gate 1.2 must also set sub_stage to 'spec_review'."""
    state = _state(stage="1", sub_stage=None)
    new = dispatch_gate_response(state, "gate_1_2_spec_post_review", "FRESH REVIEW", Path("."))
    assert new.sub_stage == "spec_review", (
        f"FRESH REVIEW must set sub_stage='spec_review', got {new.sub_stage!r}"
    )


def test_gate_5_1_tests_failed_does_not_loop():
    """S3-17: TESTS FAILED at Gate 5.1 must not set sub_stage to repo_test (which loops)."""
    state = _state(stage="5", sub_stage="repo_test")
    new = dispatch_gate_response(state, "gate_5_1_repo_test", "TESTS FAILED", Path("."))
    assert new.sub_stage != "repo_test", "Must not loop back to repo_test"


def test_gate_5_1_tests_failed_resets_sub_stage():
    """S3-17: TESTS FAILED at Gate 5.1 must set sub_stage to None for fix cycle re-entry."""
    state = _state(stage="5", sub_stage="repo_test")
    new = dispatch_gate_response(state, "gate_5_1_repo_test", "TESTS FAILED", Path("."))
    assert new.sub_stage is None, (
        f"TESTS FAILED must reset sub_stage to None, got {new.sub_stage!r}"
    )


def test_pass_transition_blocks_with_deferred_broken():
    """S3-17: PROCEED TO PASS 2 must block when deferred_broken_units non-empty."""
    state = _state(stage="5", sub_stage="pass_transition", deferred_broken_units=[7])
    state.pass_ = 1
    with pytest.raises((ValueError, Exception)):
        dispatch_gate_response(state, "gate_pass_transition_post_pass1", "PROCEED TO PASS 2", Path("."))


def test_pass_transition_allows_with_empty_deferred():
    """S3-17: PROCEED TO PASS 2 succeeds when deferred_broken_units empty."""
    state = _state(stage="5", sub_stage="pass_transition", deferred_broken_units=[])
    state.pass_ = 1
    new = dispatch_gate_response(state, "gate_pass_transition_post_pass1", "PROCEED TO PASS 2", Path("."))
    # Should not raise


# ---------------------------------------------------------------------------
# Routing-side tests for blueprint_review sub-stage (Bug S3-17)
# ---------------------------------------------------------------------------


def _route_with_status(state, status_value):
    """Write state to a temp dir with last_status, then call route()."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        save_state(root, state)
        svp_dir = root / ".svp"
        svp_dir.mkdir(exist_ok=True)
        if status_value:
            (svp_dir / "last_status.txt").write_text(status_value, encoding="utf-8")
        else:
            (svp_dir / "last_status.txt").write_text("", encoding="utf-8")
        (root / "svp_config.json").write_text(
            json.dumps({"iteration_limit": 3}), encoding="utf-8"
        )
        return route(root)


def _make_route_state(**kwargs):
    defaults = dict(
        stage="2", sub_stage="blueprint_review", current_unit=None,
        total_units=0, verified_units=[], alignment_iterations=0,
        fix_ladder_position=None, red_run_retries=0, pass_history=[],
        debug_session=None, debug_history=[], redo_triggered_from=None,
        delivered_repo_path=None,
    )
    defaults.update(kwargs)
    return PipelineState(**defaults)


def test_gate_2_1_fresh_review_sets_blueprint_review_sub_stage():
    """S3-17: FRESH REVIEW at Gate 2.1 must set sub_stage='blueprint_review' (not alignment_check)."""
    state = _state(stage="2", sub_stage="blueprint_dialog")
    new = dispatch_gate_response(state, "gate_2_1_blueprint_approval", "FRESH REVIEW", Path("."))
    assert new.sub_stage == "blueprint_review", (
        f"FRESH REVIEW at Gate 2.1 must set sub_stage='blueprint_review', got {new.sub_stage!r}"
    )


def test_gate_2_2_fresh_review_sets_blueprint_review_sub_stage():
    """S3-17: FRESH REVIEW at Gate 2.2 must set sub_stage='blueprint_review' (not alignment_check)."""
    state = _state(stage="2", sub_stage="alignment_confirmed")
    new = dispatch_gate_response(state, "gate_2_2_blueprint_post_review", "FRESH REVIEW", Path("."))
    assert new.sub_stage == "blueprint_review", (
        f"FRESH REVIEW at Gate 2.2 must set sub_stage='blueprint_review', got {new.sub_stage!r}"
    )


def test_blueprint_review_sub_stage_routes_to_blueprint_reviewer():
    """S3-17: sub_stage='blueprint_review' must route to blueprint_reviewer agent (not blueprint_author)."""
    state = _make_route_state(sub_stage="blueprint_review")
    action = _route_with_status(state, None)
    assert action["action_type"] == "invoke_agent", (
        f"blueprint_review must invoke an agent, got {action['action_type']!r}"
    )
    assert action.get("agent_type") == "blueprint_reviewer", (
        f"blueprint_review must invoke blueprint_reviewer, got {action.get('agent_type')!r}"
    )


def test_blueprint_review_review_complete_presents_gate_2_2():
    """S3-17: REVIEW_COMPLETE in blueprint_review sub-stage must present gate_2_2_blueprint_post_review."""
    state = _make_route_state(sub_stage="blueprint_review")
    action = _route_with_status(state, "REVIEW_COMPLETE")
    assert action["action_type"] == "human_gate", (
        f"REVIEW_COMPLETE in blueprint_review must present a human gate, got {action['action_type']!r}"
    )
    assert action.get("gate_id") == "gate_2_2_blueprint_post_review", (
        f"REVIEW_COMPLETE in blueprint_review must present gate_2_2_blueprint_post_review, "
        f"got {action.get('gate_id')!r}"
    )

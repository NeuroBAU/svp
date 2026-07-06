"""Regression: Stage 3 unit-gate responses must actually restart/advance.

Audit 2026-07-06 (P2): gate_3_completion_failure RESTART STAGE 3 was a
no-op loop (verified_units untouched, current_unit None); ABANDON UNIT at
gates 3.3/3.4 entered the next unit at test_generation (no stub) with
stale per-unit counters.
"""

from tests.regressions.helpers import make_state


from routing import dispatch_gate_response


def test_restart_stage_3_rolls_back_to_unit_1(project_root):
    state = make_state(
        project_root,
        stage="3",
        sub_stage=None,
        current_unit=None,
        total_units=3,
        verified_units=[{"unit": 1}, {"unit": 2}],
    )

    new = dispatch_gate_response(
        state, "gate_3_completion_failure", "RESTART STAGE 3", project_root
    )

    assert new.current_unit == 1
    assert new.sub_stage == "stub_generation"
    assert new.verified_units == []


def _abandon_common(project_root, gate_id):
    state = make_state(
        project_root,
        stage="3",
        sub_stage="implementation",
        current_unit=1,
        total_units=2,
        fix_ladder_position="diagnostic_impl",
        red_run_retries=2,
        test_layer_review_count=1,
    )
    return dispatch_gate_response(state, gate_id, "ABANDON UNIT", project_root)


def test_gate_3_4_abandon_unit_starts_next_unit_at_stub_generation(project_root):
    new = _abandon_common(project_root, "gate_3_4_test_generation_blocked")

    assert new.current_unit == 2
    assert new.sub_stage == "stub_generation"
    assert new.deferred_broken_units == [1]
    assert new.fix_ladder_position is None
    assert new.red_run_retries == 0
    assert new.test_layer_review_count == 0


def test_gate_3_3_abandon_unit_starts_next_unit_at_stub_generation(project_root):
    new = _abandon_common(project_root, "gate_3_3_test_layer_review")

    assert new.current_unit == 2
    assert new.sub_stage == "stub_generation"
    assert new.deferred_broken_units == [1]
    assert new.fix_ladder_position is None
    assert new.red_run_retries == 0
    assert new.test_layer_review_count == 0

"""Regression test for Bug S3-16: Stage 4 test dispatch must present gates.

dispatch_command_status for Stage 4 test_execution must differentiate:
- TESTS_FAILED: present Gate 4.1 (gate_4_1_integration_failure) under limit,
  Gate 4.2 (gate_4_2_assembly_exhausted) at limit.
- TESTS_ERROR: re-invoke integration_test_author (sub_stage=None) under limit,
  Gate 4.2 at limit.
- TESTS_PASSED: advance to regression_adaptation (unchanged).
Simple retry-increment without gate presentation is incorrect.
"""

from src.unit_5.stub import PipelineState
from src.unit_14.stub import dispatch_command_status


def _make_state(**overrides):
    """Build a minimal PipelineState with defaults for Stage 4."""
    defaults = {
        "stage": "4",
        "sub_stage": None,
        "current_unit": None,
        "total_units": 10,
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
        "state_hash": None,
        "spec_revision_count": 0,
        "pass_": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


def test_stage4_tests_failed_presents_gate_4_1():
    """S3-16: TESTS_FAILED at Stage 4 must route toward Gate 4.1."""
    state = _make_state()
    new = dispatch_command_status(state, "test_execution", "TESTS_FAILED")
    assert new.sub_stage is not None, "Must set sub_stage (not just increment retries)"
    assert new.sub_stage == "gate_4_1"


def test_stage4_tests_error_resets_for_re_invocation():
    """S3-16: TESTS_ERROR at Stage 4 should re-invoke integration test author."""
    state = _make_state()
    new = dispatch_command_status(state, "test_execution", "TESTS_ERROR")
    # Sub_stage should be None to allow re-invocation of integration_test_author
    assert new.sub_stage is None


def test_stage4_exhaustion_presents_gate_4_2_on_failed():
    """S3-16: Exhausted retries at Stage 4 via TESTS_FAILED must route toward Gate 4.2."""
    state = _make_state(red_run_retries=2)  # Will become 3 after increment = exhausted
    new = dispatch_command_status(state, "test_execution", "TESTS_FAILED")
    assert new.sub_stage == "gate_4_2"


def test_stage4_exhaustion_presents_gate_4_2_on_error():
    """S3-16: Exhausted retries at Stage 4 via TESTS_ERROR must route toward Gate 4.2."""
    state = _make_state(red_run_retries=2)  # Will become 3 after increment = exhausted
    new = dispatch_command_status(state, "test_execution", "TESTS_ERROR")
    assert new.sub_stage == "gate_4_2"


def test_stage4_tests_passed_still_advances():
    """S3-16: TESTS_PASSED at Stage 4 still advances to regression_adaptation."""
    state = _make_state()
    new = dispatch_command_status(state, "test_execution", "TESTS_PASSED")
    assert new.sub_stage == "regression_adaptation"


def test_stage4_tests_failed_increments_retries():
    """S3-16: TESTS_FAILED must still increment red_run_retries."""
    state = _make_state(red_run_retries=0)
    new = dispatch_command_status(state, "test_execution", "TESTS_FAILED")
    assert new.red_run_retries == 1


def test_stage4_tests_error_increments_retries():
    """S3-16: TESTS_ERROR must still increment red_run_retries."""
    state = _make_state(red_run_retries=0)
    new = dispatch_command_status(state, "test_execution", "TESTS_ERROR")
    assert new.red_run_retries == 1


def test_stage4_tests_failed_vs_error_differentiation():
    """S3-16: TESTS_FAILED and TESTS_ERROR must produce different sub_stages under limit."""
    state_f = _make_state(red_run_retries=0)
    state_e = _make_state(red_run_retries=0)
    new_f = dispatch_command_status(state_f, "test_execution", "TESTS_FAILED")
    new_e = dispatch_command_status(state_e, "test_execution", "TESTS_ERROR")
    assert new_f.sub_stage != new_e.sub_stage, (
        "TESTS_FAILED and TESTS_ERROR must produce different dispatch paths"
    )

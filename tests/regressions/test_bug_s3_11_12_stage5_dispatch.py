"""Regression tests for Bugs S3-11 and S3-12."""
import copy
from pipeline_state import PipelineState
from routing import dispatch_command_status, route


def _make_state(**overrides):
    defaults = dict(
        stage="5", sub_stage="compliance_scan", current_unit=None,
        total_units=29, verified_units=[], fix_ladder_position=None,
        red_run_retries=0, alignment_iterations=0, pass_history=[],
        debug_session=None, debug_history=[], redo_triggered_from=None,
        delivered_repo_path=None,
    )
    defaults.update(overrides)
    return PipelineState(**defaults)


def test_dispatch_handles_compliance_scan_succeeded():
    """S3-11: compliance_scan COMMAND_SUCCEEDED advances to repo_complete."""
    state = _make_state(sub_stage="compliance_scan")
    new = dispatch_command_status(state, "compliance_scan", "COMMAND_SUCCEEDED")
    assert new.sub_stage == "repo_complete"


def test_dispatch_handles_compliance_scan_failed():
    """S3-11: compliance_scan COMMAND_FAILED re-enters assembly."""
    state = _make_state(sub_stage="compliance_scan")
    new = dispatch_command_status(state, "compliance_scan", "COMMAND_FAILED")
    assert new.sub_stage is None


def test_dispatch_handles_structural_check_succeeded():
    """S3-11: structural_check COMMAND_SUCCEEDED advances to compliance_scan."""
    state = _make_state(sub_stage="structural_check")
    new = dispatch_command_status(state, "structural_check", "COMMAND_SUCCEEDED")
    assert new.sub_stage == "compliance_scan"


def test_dispatch_does_not_raise_on_compliance_scan():
    """S3-11: dispatch_command_status must not raise ValueError for compliance_scan."""
    state = _make_state(sub_stage="compliance_scan")
    # Should not raise
    dispatch_command_status(state, "compliance_scan", "COMMAND_SUCCEEDED")


def test_dispatch_does_not_raise_on_structural_check():
    """S3-11: dispatch_command_status must not raise ValueError for structural_check."""
    state = _make_state(sub_stage="structural_check")
    # Should not raise
    dispatch_command_status(state, "structural_check", "COMMAND_SUCCEEDED")

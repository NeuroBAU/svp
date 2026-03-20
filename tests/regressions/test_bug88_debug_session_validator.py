"""Regression test for Bug 88: Debug session validator rejects legitimate triage state.

Root cause: validate_state() unconditionally required classification and
affected_units in any active debug session. But during triage_readonly and
triage phases, these fields are legitimately None/empty -- they are set by
set_debug_classification() only after the triage agent completes.

Fix: Guard classification/affected_units validation with a phase check.
Only require them in post-triage phases (repair, regression_test, stage3_reentry).
"""

import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parents[2]
_scripts = _project_root / "scripts"
if not _scripts.is_dir():
    _scripts = _project_root / "svp" / "scripts"
sys.path.insert(0, str(_scripts))

from pipeline_state import DebugSession, PipelineState, validate_state


def _make_debug_session(**overrides):
    defaults = {
        "bug_id": 1,
        "description": "test bug",
        "classification": None,
        "affected_units": [],
        "regression_test_path": None,
        "phase": "triage_readonly",
        "authorized": False,
        "triage_refinement_count": 0,
        "repair_retry_count": 0,
        "created_at": "2026-03-20T00:00:00+00:00",
    }
    defaults.update(overrides)
    return DebugSession(**defaults)


def _make_state(**ds_overrides):
    state = PipelineState(stage="5", sub_stage="repo_complete")
    state.debug_session = _make_debug_session(**ds_overrides)
    return state


class TestBug88TriagePhaseValidation:
    """validate_state must accept classification=None and affected_units=[]
    during triage_readonly and triage phases."""

    def test_triage_readonly_with_null_classification_passes(self):
        state = _make_state(phase="triage_readonly", classification=None, affected_units=[])
        errors = validate_state(state)
        classification_errors = [e for e in errors if "classification" in e or "affected_units" in e]
        assert classification_errors == [], f"Unexpected errors: {classification_errors}"

    def test_triage_with_null_classification_passes(self):
        state = _make_state(phase="triage", classification=None, affected_units=[])
        errors = validate_state(state)
        classification_errors = [e for e in errors if "classification" in e or "affected_units" in e]
        assert classification_errors == [], f"Unexpected errors: {classification_errors}"

    def test_repair_phase_requires_classification(self):
        state = _make_state(phase="repair", classification=None, affected_units=[])
        errors = validate_state(state)
        assert any("classification" in e for e in errors), \
            "repair phase should require classification"

    def test_repair_phase_requires_affected_units(self):
        state = _make_state(phase="repair", classification="single_unit", affected_units=[])
        errors = validate_state(state)
        assert any("affected_units" in e for e in errors), \
            "repair phase should require affected_units"

    def test_repair_phase_with_valid_fields_passes(self):
        state = _make_state(
            phase="repair",
            classification="single_unit",
            affected_units=[1],
            authorized=True,
        )
        errors = validate_state(state)
        classification_errors = [e for e in errors if "classification" in e or "affected_units" in e]
        assert classification_errors == [], f"Unexpected errors: {classification_errors}"

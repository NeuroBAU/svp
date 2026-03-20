"""Bug 96 regression tests: FIX IN PLACE option for Gate 6.2.

Verifies:
- FIX IN PLACE dispatch sets classification and transitions phase to "regression_test"
- FIX IN PLACE does NOT change stage (stays at "5") -- no rollback
- FIX IN PLACE with no debug session is a no-op
- After FIX IN PLACE, routing emits invoke_agent for test agent in regression mode
- GATE_VOCABULARY includes "FIX IN PLACE" for gate_6_2
"""

import sys
from pathlib import Path

import pytest

# Ensure scripts/ is on the path for imports
_project_root = Path(__file__).resolve().parent.parent.parent
_scripts = _project_root / "scripts"
if not _scripts.is_dir():
    _scripts = _project_root / "svp" / "scripts"
sys.path.insert(0, str(_scripts))


def _make_state(**kwargs):
    """Create a PipelineState with sensible defaults for debug testing."""
    from pipeline_state import PipelineState, DebugSession

    defaults = {
        "stage": "5",
        "sub_stage": None,
        "current_unit": 10,
        "total_units": 10,
        "verified_units": [{"unit": i, "timestamp": f"t{i}"} for i in range(1, 11)],
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iteration": 0,
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "last_action": "",
        "delivered_repo_path": "/tmp/test-repo",
    }
    defaults.update(kwargs)

    # Handle debug_session dict -> DebugSession conversion
    ds = defaults.pop("debug_session", None)

    state = PipelineState.from_dict(defaults)
    if ds is not None:
        if isinstance(ds, dict):
            state.debug_session = DebugSession(**ds)
        else:
            state.debug_session = ds
    return state


def _make_debug_session(**kwargs):
    """Create a debug session dict with defaults for an authorized triage session."""
    defaults = {
        "bug_id": 96,
        "description": "test bug for fix in place",
        "classification": None,
        "affected_units": [],
        "regression_test_path": None,
        "phase": "triage",
        "authorized": True,
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------
# Gate 6.2 FIX IN PLACE dispatch tests
# ---------------------------------------------------------------


class TestGate62FixInPlace:
    """Gate 6.2 FIX IN PLACE must skip rollback and go to regression_test."""

    def test_fix_in_place_sets_phase_to_regression_test(self, tmp_path):
        """FIX IN PLACE transitions debug phase to regression_test."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(
            affected_units=[5, 7],
            classification="single_unit",
        )
        state = _make_state(debug_session=ds)

        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX IN PLACE", tmp_path
        )

        assert result.debug_session is not None
        assert result.debug_session.phase == "regression_test"

    def test_fix_in_place_does_not_change_stage(self, tmp_path):
        """FIX IN PLACE stays at stage 5 -- no rollback."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(
            affected_units=[5, 7],
            classification="single_unit",
        )
        state = _make_state(debug_session=ds)

        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX IN PLACE", tmp_path
        )

        assert result.stage == "5"

    def test_fix_in_place_preserves_verified_units(self, tmp_path):
        """FIX IN PLACE does not invalidate any verified units."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(
            affected_units=[5, 7],
            classification="single_unit",
        )
        state = _make_state(debug_session=ds)
        original_verified_count = len(state.verified_units)

        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX IN PLACE", tmp_path
        )

        assert len(result.verified_units) == original_verified_count

    def test_fix_in_place_no_session_noop(self, tmp_path):
        """FIX IN PLACE without debug session returns state unchanged."""
        from routing import dispatch_gate_response

        state = _make_state(debug_session=None)
        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX IN PLACE", tmp_path
        )
        assert result.stage == "5"
        assert result.debug_session is None

    def test_fix_in_place_sets_classification(self, tmp_path):
        """FIX IN PLACE sets classification on the debug session."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(
            affected_units=[3],
            classification="single_unit",
        )
        state = _make_state(debug_session=ds)

        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX IN PLACE", tmp_path
        )

        assert result.debug_session.classification == "single_unit"

    def test_fix_in_place_defaults_classification_when_none(self, tmp_path):
        """FIX IN PLACE defaults classification to single_unit when None."""
        from routing import dispatch_gate_response

        ds = _make_debug_session(
            affected_units=[3],
            classification=None,
        )
        state = _make_state(debug_session=ds)

        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX IN PLACE", tmp_path
        )

        assert result.debug_session.classification == "single_unit"


# ---------------------------------------------------------------
# GATE_VOCABULARY consistency
# ---------------------------------------------------------------


class TestGateVocabulary:
    """GATE_VOCABULARY must include FIX IN PLACE for gate_6_2."""

    def test_gate_vocabulary_includes_fix_in_place(self):
        """GATE_VOCABULARY gate_6_2 contains FIX IN PLACE."""
        from routing import GATE_VOCABULARY

        assert "FIX IN PLACE" in GATE_VOCABULARY["gate_6_2_debug_classification"]

    def test_gate_vocabulary_preserves_existing_options(self):
        """Existing gate_6_2 options are preserved."""
        from routing import GATE_VOCABULARY

        options = GATE_VOCABULARY["gate_6_2_debug_classification"]
        assert "FIX UNIT" in options
        assert "FIX BLUEPRINT" in options
        assert "FIX SPEC" in options


# ---------------------------------------------------------------
# Routing after FIX IN PLACE
# ---------------------------------------------------------------


class TestRoutingAfterFixInPlace:
    """After FIX IN PLACE, routing should invoke test agent in regression mode."""

    def test_routing_invokes_test_agent_after_fix_in_place(self, tmp_path):
        """With phase=regression_test and no last_status, routing invokes test agent."""
        from routing import route

        ds = _make_debug_session(
            phase="regression_test",
            classification="single_unit",
            affected_units=[5],
        )
        state = _make_state(debug_session=ds)

        # Ensure no last_status.txt exists
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)

        action = route(state, tmp_path)

        assert action["ACTION"] == "invoke_agent"

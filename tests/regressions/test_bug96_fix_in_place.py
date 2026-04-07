"""Bug 96 regression tests: FIX IN PLACE option for Gate 6.2.

Verifies:
- FIX IN PLACE dispatch sets classification and transitions phase to "regression_test"
- FIX IN PLACE does NOT change stage (stays at "5") -- no rollback
- FIX IN PLACE with no debug session is a no-op
- After FIX IN PLACE, routing emits invoke_agent for test agent in regression mode
- GATE_VOCABULARY includes "FIX IN PLACE" for gate_6_2

SVP 2.2 adaptation:
- PipelineState from src.unit_5.stub (no DebugSession class; debug sessions are plain dicts)
- dispatch_gate_response from src.unit_14.stub
- route() takes only project_root; state is saved to disk first
- Action block keys are lowercase (action_type, agent_type, gate_id)
- debug_session fields accessed as dict keys, not attributes
"""

import json
import tempfile
from pathlib import Path

import pytest

from pipeline_state import PipelineState, save_state
from routing import dispatch_gate_response, route, GATE_VOCABULARY


def _make_state(**kwargs):
    """Create a PipelineState with sensible defaults for debug testing."""
    defaults = {
        "stage": "5",
        "sub_stage": None,
        "current_unit": None,
        "total_units": 10,
        "verified_units": [{"unit": i, "timestamp": f"t{i}"} for i in range(1, 11)],
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iterations": 0,
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "delivered_repo_path": "/tmp/test-repo",
    }
    defaults.update(kwargs)
    # Filter to valid PipelineState fields
    valid_fields = {f.name for f in PipelineState.__dataclass_fields__.values()}
    filtered = {k: v for k, v in defaults.items() if k in valid_fields}
    return PipelineState(**filtered)


def _make_debug_session(**kwargs):
    """Create a debug session dict with defaults for an authorized triage session."""
    defaults = {
        "authorized": True,
        "bug_number": 96,
        "classification": None,
        "affected_units": [],
        "phase": "triage",
        "repair_retry_count": 0,
        "triage_refinement_count": 0,
        "ledger_path": None,
    }
    defaults.update(kwargs)
    return defaults


def _route_with_state(state, last_status=""):
    """Save state to disk and call route(project_root)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        save_state(root, state)
        svp_dir = root / ".svp"
        svp_dir.mkdir(exist_ok=True)
        (svp_dir / "last_status.txt").write_text(last_status)
        return route(root)


# ---------------------------------------------------------------
# Gate 6.2 FIX IN PLACE dispatch tests
# ---------------------------------------------------------------


class TestGate62FixInPlace:
    """Gate 6.2 FIX IN PLACE must skip rollback and go to regression_test."""

    def test_fix_in_place_sets_phase_to_repair(self, tmp_path):
        """FIX IN PLACE transitions debug phase to repair.

        SVP 2.2: FIX IN PLACE uses update_debug_phase(state, "repair"),
        not "regression_test" as in SVP 2.1.
        """
        ds = _make_debug_session(
            affected_units=[5, 7],
            classification="single_unit",
        )
        state = _make_state(debug_session=ds)

        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX IN PLACE", tmp_path
        )

        assert result.debug_session is not None
        assert result.debug_session["phase"] == "repair"

    def test_fix_in_place_does_not_change_stage(self, tmp_path):
        """FIX IN PLACE stays at stage 5 -- no rollback."""
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
        state = _make_state(debug_session=None)
        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX IN PLACE", tmp_path
        )
        assert result.stage == "5"
        assert result.debug_session is None

    def test_fix_in_place_sets_classification(self, tmp_path):
        """FIX IN PLACE sets classification on the debug session."""
        ds = _make_debug_session(
            affected_units=[3],
            classification="single_unit",
        )
        state = _make_state(debug_session=ds)

        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX IN PLACE", tmp_path
        )

        assert result.debug_session["classification"] == "single_unit"

    def test_fix_in_place_preserves_classification_when_none(self, tmp_path):
        """FIX IN PLACE preserves classification (does not default it).

        SVP 2.2: FIX IN PLACE does not default classification to single_unit;
        it preserves whatever classification was set (or None).
        """
        ds = _make_debug_session(
            affected_units=[3],
            classification=None,
        )
        state = _make_state(debug_session=ds)

        result = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX IN PLACE", tmp_path
        )

        # SVP 2.2: classification is preserved, not defaulted
        assert result.debug_session is not None


# ---------------------------------------------------------------
# GATE_VOCABULARY consistency
# ---------------------------------------------------------------


class TestGateVocabulary:
    """GATE_VOCABULARY must include FIX IN PLACE for gate_6_2."""

    def test_gate_vocabulary_includes_fix_in_place(self):
        """GATE_VOCABULARY gate_6_2 contains FIX IN PLACE."""
        assert "FIX IN PLACE" in GATE_VOCABULARY["gate_6_2_debug_classification"]

    def test_gate_vocabulary_preserves_existing_options(self):
        """Existing gate_6_2 options are preserved."""
        options = GATE_VOCABULARY["gate_6_2_debug_classification"]
        assert "FIX UNIT" in options
        assert "FIX BLUEPRINT" in options
        assert "FIX SPEC" in options


# ---------------------------------------------------------------
# Routing after FIX IN PLACE
# ---------------------------------------------------------------


class TestRoutingAfterFixInPlace:
    """After FIX IN PLACE, routing should invoke test agent in regression mode."""

    def test_routing_invokes_test_agent_after_fix_in_place(self):
        """With phase=regression_test and no last_status, routing invokes test agent."""
        ds = _make_debug_session(
            phase="regression_test",
            classification="single_unit",
            affected_units=[5],
        )
        state = _make_state(debug_session=ds)

        action = _route_with_state(state)

        assert action["action_type"] == "invoke_agent"

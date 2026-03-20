"""Regression test for Bug 93: Triage agent doesn't write triage_result.json.

Root cause: _read_triage_affected_units at routing.py:244 expects
.svp/triage_result.json to communicate which units are affected. The
triage agent definition never instructed the agent to write it. When
Gate 6.2 FIX UNIT fires, affected_units is empty, so dispatch silently
no-ops.

Fix: Added instruction to the triage agent definition (step 4) to write
.svp/triage_result.json after classification.
"""

import json
import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parents[2]
_scripts = _project_root / "scripts"
if not _scripts.is_dir():
    _scripts = _project_root / "svp" / "scripts"
sys.path.insert(0, str(_scripts))

from pipeline_state import DebugSession, PipelineState
from routing import _read_triage_affected_units, dispatch_gate_response


def _make_state(phase="triage", classification="single_unit", affected=None):
    state = PipelineState(
        stage="5",
        sub_stage="repo_complete",
        delivered_repo_path="/tmp/fake-repo",
    )
    state.debug_session = DebugSession(
        bug_id=99,
        description="test bug",
        classification=classification,
        affected_units=affected or [10],
        regression_test_path=None,
        phase=phase,
        authorized=True,
        triage_refinement_count=0,
        repair_retry_count=0,
        created_at="2026-03-20T00:00:00+00:00",
    )
    return state


class TestBug93ReadTriageAffectedUnits:
    """_read_triage_affected_units must correctly read triage_result.json."""

    def test_reads_affected_units_from_file(self, tmp_path):
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        result = {"affected_units": [10, 19], "classification": "cross_unit"}
        (svp_dir / "triage_result.json").write_text(json.dumps(result))

        units = _read_triage_affected_units(tmp_path)

        assert units == [10, 19]

    def test_returns_empty_when_file_missing(self, tmp_path):
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()

        units = _read_triage_affected_units(tmp_path)

        assert units == []

    def test_returns_empty_on_malformed_json(self, tmp_path):
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (svp_dir / "triage_result.json").write_text("not json")

        units = _read_triage_affected_units(tmp_path)

        assert units == []

    def test_returns_empty_when_key_missing(self, tmp_path):
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (svp_dir / "triage_result.json").write_text(json.dumps({"classification": "single_unit"}))

        units = _read_triage_affected_units(tmp_path)

        assert units == []


class TestBug93Gate62FixUnitDispatch:
    """Gate 6.2 FIX UNIT must call rollback_to_unit when affected_units is populated."""

    def test_fix_unit_with_affected_units_transitions(self, tmp_path):
        """When affected_units is populated, FIX UNIT should produce a state
        transition (stage changes to '3' via rollback_to_unit)."""
        state = _make_state(affected=[10])
        # rollback_to_unit needs current_unit >= target and total_units
        state.current_unit = 20
        state.total_units = 20
        state.verified_units = [{"unit": i} for i in range(1, 21)]
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        # Create unit marker files that rollback tries to delete
        for i in range(10, 21):
            (svp_dir / f"unit_{i}_complete").touch()

        new_state = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX UNIT", tmp_path
        )

        # rollback_to_unit sets stage to "3"
        assert new_state.stage == "3"

    def test_fix_unit_with_empty_affected_noop(self, tmp_path):
        """When affected_units is empty, FIX UNIT should no-op (Bug 93 symptom)."""
        state = _make_state(affected=[])
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()

        new_state = dispatch_gate_response(
            state, "gate_6_2_debug_classification", "FIX UNIT", tmp_path
        )

        # With empty affected_units, dispatch returns state unchanged
        assert new_state.stage == "5"


class TestBug93AgentDefinitionIncludesInstruction:
    """The triage agent definition must instruct the agent to write triage_result.json."""

    def test_triage_agent_definition_mentions_triage_result(self):
        from debug_loop_agent_definitions import BUG_TRIAGE_AGENT_MD_CONTENT

        assert "triage_result.json" in BUG_TRIAGE_AGENT_MD_CONTENT, \
            "Bug triage agent definition must instruct agent to write triage_result.json"

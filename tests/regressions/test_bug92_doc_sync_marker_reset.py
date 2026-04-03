"""Regression test for Bug 92: Doc sync marker not reset on phase transition.

Root cause (SVP 2.1): The .svp/doc_sync_done marker persists across the
triage_readonly -> triage phase transition (Gate 6.0 AUTHORIZE DEBUG).
The authorized triage agent writes new content but the sync doesn't
run again because the marker still exists.

Fix (SVP 2.1): dispatch_gate_response for Gate 6.0 AUTHORIZE DEBUG now deletes
the .svp/doc_sync_done marker after calling authorize_debug_session.

SVP 2.2 adaptation: The doc_sync_done marker and triage_readonly phase do not
exist in SVP 2.2. Tests for marker deletion are skipped. The core Gate 6.0
AUTHORIZE/ABANDON behavior is tested.
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

from pipeline_state import PipelineState
from routing import dispatch_gate_response, route


def _make_debug_session_dict(phase="triage", authorized=False):
    """Build a plain-dict debug session for SVP 2.2."""
    return {
        "authorized": authorized,
        "bug_number": 99,
        "classification": None,
        "affected_units": [],
        "phase": phase,
        "repair_retry_count": 0,
        "triage_refinement_count": 0,
        "ledger_path": None,
    }


def _make_state(authorized=False):
    """Create a state with an unauthorized debug session."""
    state = PipelineState(
        stage="5",
        sub_stage="repo_complete",
        delivered_repo_path="/tmp/fake-repo",
    )
    state.debug_session = _make_debug_session_dict(phase="triage", authorized=authorized)
    return state


class TestBug92Gate60DispatchBehavior:
    """SVP 2.2 equivalent: verify Gate 6.0 AUTHORIZE/ABANDON DEBUG
    transitions work correctly with plain-dict debug sessions."""

    def test_authorize_debug_sets_authorized(self, tmp_path):
        """AUTHORIZE DEBUG sets debug_session['authorized'] = True."""
        state = _make_state(authorized=False)
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()

        new_state = dispatch_gate_response(
            state, "gate_6_0_debug_permission", "AUTHORIZE DEBUG", tmp_path
        )

        assert new_state.debug_session is not None
        assert new_state.debug_session["authorized"] is True

    def test_abandon_debug_clears_session(self, tmp_path):
        """ABANDON DEBUG moves session to debug_history and clears it."""
        state = _make_state(authorized=False)
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()

        new_state = dispatch_gate_response(
            state, "gate_6_0_debug_permission", "ABANDON DEBUG", tmp_path
        )

        assert new_state.debug_session is None
        assert len(new_state.debug_history) == 1

    def test_authorize_then_route_presents_triage_agent(self, tmp_path):
        """After authorization, routing invokes the bug_triage_agent."""
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (svp_dir / "last_status.txt").write_text("")
        # Write state with authorized triage session
        state_data = {
            "stage": "5",
            "sub_stage": "repo_complete",
            "current_unit": None,
            "total_units": 0,
            "verified_units": [],
            "alignment_iterations": 0,
            "fix_ladder_position": None,
            "red_run_retries": 0,
            "pass_history": [],
            "debug_session": _make_debug_session_dict(phase="triage", authorized=True),
            "debug_history": [],
            "redo_triggered_from": None,
            "delivered_repo_path": "/tmp/fake-repo",
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
            "pass": None,
            "pass2_nested_session_path": None,
            "deferred_broken_units": [],
        }
        state_path = svp_dir / "pipeline_state.json"
        state_path.write_text(json.dumps(state_data, indent=2), encoding="utf-8")

        action = route(tmp_path)

        assert action["action_type"] == "invoke_agent"
        assert action["agent_type"] == "bug_triage_agent"

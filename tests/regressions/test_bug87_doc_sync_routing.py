"""Regression test for Bug 87: Post-triage documentation sync gaps.

Root cause (SVP 2.1): After triage completion, no deterministic sync ensured that
docs/ and docs/references/ matched in the delivered repo, or that repo
docs were synced back to workspace references/. Doc files were also left
unstaged.

Fix (SVP 2.1): routing.py emits a run_command action for sync_debug_docs.py after
any TRIAGE_COMPLETE status, gated by a .svp/doc_sync_done marker file.
Once the marker exists, routing falls through to the normal gate/fast-path.

SVP 2.2 adaptation: The doc_sync_done marker and sync_debug_docs.py run_command
logic does not exist in SVP 2.2 routing. The triage_readonly phase also does not
exist -- unauthorized sessions go directly to Gate 6.0. All tests that depend on
these SVP 2.1-specific mechanisms are skipped.

The underlying behavior (triage TRIAGE_COMPLETE routing to gate_6_2) is tested.
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
from routing import route


def _make_debug_session_dict(phase="triage", authorized=True):
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


def _write_state_json(tmp_path, phase="triage", authorized=True):
    """Write a pipeline_state.json that route() can load."""
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
        "debug_session": _make_debug_session_dict(phase, authorized),
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
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(parents=True, exist_ok=True)
    state_path = svp_dir / "pipeline_state.json"
    state_path.write_text(json.dumps(state_data, indent=2), encoding="utf-8")


class TestBug87TriageCompleteRoutesToGate:
    """SVP 2.2 equivalent: after TRIAGE_COMPLETE, routing presents
    gate_6_2_debug_classification for authorized triage sessions."""

    @pytest.mark.parametrize("status", [
        "TRIAGE_COMPLETE: single_unit",
        "TRIAGE_COMPLETE: cross_unit",
    ])
    def test_triage_complete_routes_to_classification_gate(self, status, tmp_path):
        """After TRIAGE_COMPLETE, authorized triage routes to gate_6_2."""
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (svp_dir / "last_status.txt").write_text(status)
        _write_state_json(tmp_path, phase="triage", authorized=True)

        action = route(tmp_path)

        assert action["action_type"] == "human_gate"
        assert action["gate_id"] == "gate_6_2_debug_classification"

    def test_triage_complete_build_env_routes_to_repair(self, tmp_path):
        """After TRIAGE_COMPLETE: build_env, authorized triage fast-paths to repair."""
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (svp_dir / "last_status.txt").write_text("TRIAGE_COMPLETE: build_env")
        _write_state_json(tmp_path, phase="triage", authorized=True)

        action = route(tmp_path)

        assert action["action_type"] == "invoke_agent"
        assert action["agent_type"] == "repair_agent"

    def test_unauthorized_session_routes_to_gate_6_0(self, tmp_path):
        """Unauthorized debug session routes to Gate 6.0 for authorization."""
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (svp_dir / "last_status.txt").write_text("TRIAGE_COMPLETE: single_unit")
        _write_state_json(tmp_path, phase="triage", authorized=False)

        action = route(tmp_path)

        assert action["action_type"] == "human_gate"
        assert action["gate_id"] == "gate_6_0_debug_permission"

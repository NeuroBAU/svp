"""Regression test for Bug 89: Doc sync command clobbers last_status.txt.

Root cause: The Bug 87 doc sync run_command action follows the standard
action cycle which writes COMMAND_SUCCEEDED to last_status.txt. This
clobbers the triage status (e.g. TRIAGE_COMPLETE: cross_unit) that
routing needs on re-entry to present the correct gate.

Fix: The POST command for the sync action now restores the original
triage status to last_status.txt after creating the marker file.
"""

import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parents[2]
_scripts = _project_root / "scripts"
if not _scripts.is_dir():
    _scripts = _project_root / "svp" / "scripts"
sys.path.insert(0, str(_scripts))

from pipeline_state import DebugSession, PipelineState
from routing import route


def _make_state(phase="triage_readonly"):
    state = PipelineState(
        stage="5",
        sub_stage="repo_complete",
        delivered_repo_path="/tmp/fake-repo",
    )
    state.debug_session = DebugSession(
        bug_id=99,
        description="test bug",
        classification=None,
        affected_units=[],
        regression_test_path=None,
        phase=phase,
        authorized=phase != "triage_readonly",
        triage_refinement_count=0,
        repair_retry_count=0,
        created_at="2026-03-20T00:00:00+00:00",
    )
    return state


class TestBug89SyncStatusRestore:
    """The sync action's POST command must restore the original triage
    status to last_status.txt so routing sees the correct status on re-entry."""

    @pytest.mark.parametrize("status", [
        "TRIAGE_COMPLETE: single_unit",
        "TRIAGE_COMPLETE: cross_unit",
        "TRIAGE_COMPLETE: build_env",
        "TRIAGE_NON_REPRODUCIBLE",
    ])
    def test_triage_sync_post_restores_status(self, status, tmp_path):
        """POST command must contain the original triage status."""
        state = _make_state(phase="triage")
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (svp_dir / "last_status.txt").write_text(status)

        action = route(state, tmp_path)

        assert action["ACTION"] == "run_command"
        assert "sync_debug_docs.py" in action["COMMAND"]
        # POST must restore the original status
        assert status in action["POST"], \
            f"POST must restore '{status}' but got: {action['POST']}"

    @pytest.mark.parametrize("status", [
        "TRIAGE_COMPLETE: single_unit",
        "TRIAGE_COMPLETE: cross_unit",
        "TRIAGE_COMPLETE: build_env",
        "TRIAGE_NON_REPRODUCIBLE",
        "TRIAGE_NEEDS_REFINEMENT",
    ])
    def test_triage_readonly_sync_post_restores_status(self, status, tmp_path):
        """POST command must contain the original triage status."""
        state = _make_state(phase="triage_readonly")
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (svp_dir / "last_status.txt").write_text(status)

        action = route(state, tmp_path)

        assert action["ACTION"] == "run_command"
        assert "sync_debug_docs.py" in action["COMMAND"]
        assert status in action["POST"], \
            f"POST must restore '{status}' but got: {action['POST']}"

    def test_after_sync_routing_presents_gate_not_agent(self, tmp_path):
        """After sync completes (marker exists), routing must present
        Gate 6.0, not re-invoke the triage agent."""
        state = _make_state(phase="triage_readonly")
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (svp_dir / "last_status.txt").write_text("TRIAGE_COMPLETE: cross_unit")
        (svp_dir / "doc_sync_done").touch()

        action = route(state, tmp_path)

        assert action["ACTION"] == "human_gate"
        assert action["GATE_ID"] == "gate_6_0_debug_permission"

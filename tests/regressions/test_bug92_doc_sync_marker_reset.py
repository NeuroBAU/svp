"""Regression test for Bug 92: Doc sync marker not reset on phase transition.

Root cause: The .svp/doc_sync_done marker persists across the
triage_readonly -> triage phase transition (Gate 6.0 AUTHORIZE DEBUG).
The authorized triage agent writes new content but the sync doesn't
run again because the marker still exists.

Fix: dispatch_gate_response for Gate 6.0 AUTHORIZE DEBUG now deletes
the .svp/doc_sync_done marker after calling authorize_debug_session.
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
from routing import dispatch_gate_response, route


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


class TestBug92DocSyncMarkerReset:
    """Gate 6.0 AUTHORIZE DEBUG must delete .svp/doc_sync_done marker."""

    def test_authorize_debug_deletes_marker(self, tmp_path):
        """After AUTHORIZE DEBUG, the doc_sync_done marker must be removed."""
        state = _make_state(phase="triage_readonly")
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        marker = svp_dir / "doc_sync_done"
        marker.write_text("done")

        new_state = dispatch_gate_response(
            state, "gate_6_0_debug_permission", "AUTHORIZE DEBUG", tmp_path
        )

        assert not marker.exists(), \
            "doc_sync_done marker must be deleted after AUTHORIZE DEBUG"
        # State should have transitioned to authorized triage
        assert new_state.debug_session is not None
        assert new_state.debug_session.authorized is True

    def test_authorize_debug_works_without_marker(self, tmp_path):
        """AUTHORIZE DEBUG must not fail if marker doesn't exist."""
        state = _make_state(phase="triage_readonly")
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()

        new_state = dispatch_gate_response(
            state, "gate_6_0_debug_permission", "AUTHORIZE DEBUG", tmp_path
        )

        assert new_state.debug_session is not None
        assert new_state.debug_session.authorized is True

    def test_abandon_debug_does_not_touch_marker(self, tmp_path):
        """ABANDON DEBUG should not affect the marker."""
        state = _make_state(phase="triage_readonly")
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        marker = svp_dir / "doc_sync_done"
        marker.write_text("done")

        dispatch_gate_response(
            state, "gate_6_0_debug_permission", "ABANDON DEBUG", tmp_path
        )

        assert marker.exists(), \
            "ABANDON DEBUG should not delete the marker"

    def test_sync_runs_after_authorized_triage(self, tmp_path):
        """After Gate 6.0 AUTHORIZE DEBUG, routing in triage phase should
        emit sync command when marker is absent and TRIAGE_COMPLETE exists."""
        state = _make_state(phase="triage")
        state.debug_session.authorized = True
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        # No doc_sync_done marker — sync should run
        (svp_dir / "last_status.txt").write_text("TRIAGE_COMPLETE: single_unit")

        action = route(state, tmp_path)

        assert action["ACTION"] == "run_command"
        assert "sync_debug_docs.py" in action["COMMAND"]

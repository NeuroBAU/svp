"""Regression test for Bug 87: Post-triage documentation sync gaps.

Root cause: After triage completion, no deterministic sync ensured that
docs/ and docs/references/ matched in the delivered repo, or that repo
docs were synced back to workspace references/. Doc files were also left
unstaged.

Fix: routing.py emits a run_command action for sync_debug_docs.py after
any TRIAGE_COMPLETE status, gated by a .svp/doc_sync_done marker file.
Once the marker exists, routing falls through to the normal gate/fast-path.
"""

import sys
import tempfile
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parents[2]
_scripts = _project_root / "scripts"
if not _scripts.is_dir():
    _scripts = _project_root / "svp" / "scripts"
sys.path.insert(0, str(_scripts))

from pipeline_state import DebugSession, PipelineState
from routing import route


def _make_state(phase="triage"):
    state = PipelineState(
        stage="5",
        sub_stage="repo_complete",
        delivered_repo_path="/tmp/fake-repo",
    )
    state.debug_session = DebugSession(
        bug_id=99,
        description="test bug",
        classification="single_unit" if phase not in ("triage_readonly", "triage") else None,
        affected_units=[1] if phase not in ("triage_readonly", "triage") else [],
        regression_test_path=None,
        phase=phase,
        authorized=phase != "triage_readonly",
        triage_refinement_count=0,
        repair_retry_count=0,
        created_at="2026-03-20T00:00:00+00:00",
    )
    return state


class TestBug87DocSyncRouting:
    """route() must emit sync_debug_docs.py run_command after TRIAGE_COMPLETE
    when the marker file does not exist, and skip it when the marker exists."""

    @pytest.mark.parametrize("status", [
        "TRIAGE_COMPLETE: single_unit",
        "TRIAGE_COMPLETE: cross_unit",
        "TRIAGE_COMPLETE: build_env",
        "TRIAGE_NON_REPRODUCIBLE",
    ])
    def test_triage_phase_emits_doc_sync_without_marker(self, status, tmp_path):
        state = _make_state(phase="triage")
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (svp_dir / "last_status.txt").write_text(status)
        # No doc_sync_done marker

        action = route(state, tmp_path)

        assert action["ACTION"] == "run_command"
        assert "sync_debug_docs.py" in action["COMMAND"]

    @pytest.mark.parametrize("status", [
        "TRIAGE_COMPLETE: single_unit",
        "TRIAGE_COMPLETE: cross_unit",
        "TRIAGE_COMPLETE: build_env",
        "TRIAGE_NON_REPRODUCIBLE",
    ])
    def test_triage_phase_skips_doc_sync_with_marker(self, status, tmp_path):
        state = _make_state(phase="triage")
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (svp_dir / "last_status.txt").write_text(status)
        (svp_dir / "doc_sync_done").touch()  # Marker exists

        action = route(state, tmp_path)

        # Should NOT be the sync command — should be a gate or agent action
        if action["ACTION"] == "run_command":
            assert "sync_debug_docs.py" not in action.get("COMMAND", "")

    @pytest.mark.parametrize("status", [
        "TRIAGE_COMPLETE: single_unit",
        "TRIAGE_COMPLETE: cross_unit",
        "TRIAGE_COMPLETE: build_env",
        "TRIAGE_NON_REPRODUCIBLE",
        "TRIAGE_NEEDS_REFINEMENT",
    ])
    def test_triage_readonly_emits_doc_sync_without_marker(self, status, tmp_path):
        state = _make_state(phase="triage_readonly")
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (svp_dir / "last_status.txt").write_text(status)

        action = route(state, tmp_path)

        assert action["ACTION"] == "run_command"
        assert "sync_debug_docs.py" in action["COMMAND"]

    @pytest.mark.parametrize("status", [
        "TRIAGE_COMPLETE: single_unit",
        "TRIAGE_COMPLETE: cross_unit",
        "TRIAGE_COMPLETE: build_env",
        "TRIAGE_NON_REPRODUCIBLE",
        "TRIAGE_NEEDS_REFINEMENT",
    ])
    def test_triage_readonly_skips_doc_sync_with_marker(self, status, tmp_path):
        state = _make_state(phase="triage_readonly")
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        (svp_dir / "last_status.txt").write_text(status)
        (svp_dir / "doc_sync_done").touch()

        action = route(state, tmp_path)

        if action["ACTION"] == "run_command":
            assert "sync_debug_docs.py" not in action.get("COMMAND", "")

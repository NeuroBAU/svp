"""Regression test for Bug 95: abandon/complete_debug_session missing resolution field.

Root cause: validate_state requires 'resolution' in every debug_history entry,
but abandon_debug_session and complete_debug_session don't write it. After
abandoning a session, the next load_state() call fails validation.

Fix: Both functions now set session_record["resolution"] when moving the
session to debug_history.
"""

import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parents[2]
_scripts = _project_root / "scripts"
if not _scripts.is_dir():
    _scripts = _project_root / "svp" / "scripts"
sys.path.insert(0, str(_scripts))

from pipeline_state import PipelineState, DebugSession, validate_state
from state_transitions import (
    abandon_debug_session,
    complete_debug_session,
    enter_debug_session,
)


def _make_stage5_state():
    state = PipelineState(
        stage="5",
        sub_stage="repo_complete",
        delivered_repo_path="/tmp/fake-repo",
    )
    return state


class TestBug95AbandonResolutionField:
    """abandon_debug_session must produce a history entry that passes validate_state."""

    def test_abandon_sets_resolution_field(self):
        state = _make_stage5_state()
        state = enter_debug_session(state, "test bug")
        abandoned = abandon_debug_session(state)

        assert len(abandoned.debug_history) == 1
        entry = abandoned.debug_history[0]
        assert "resolution" in entry, "History entry must have 'resolution' field"
        assert isinstance(entry["resolution"], str)
        assert len(entry["resolution"]) > 0

    def test_abandon_passes_validate_state(self):
        state = _make_stage5_state()
        state = enter_debug_session(state, "test bug")
        abandoned = abandon_debug_session(state)

        errors = validate_state(abandoned)
        resolution_errors = [e for e in errors if "resolution" in e]
        assert len(resolution_errors) == 0, f"validate_state failed: {resolution_errors}"

    def test_complete_sets_resolution_field(self):
        state = _make_stage5_state()
        state = enter_debug_session(state, "test bug")
        # Manually authorize for complete_debug_session
        state.debug_session.authorized = True
        completed = complete_debug_session(state, "Fixed the thing")

        assert len(completed.debug_history) == 1
        entry = completed.debug_history[0]
        assert "resolution" in entry, "History entry must have 'resolution' field"
        assert entry["resolution"] == "Fixed the thing"

    def test_complete_passes_validate_state(self):
        state = _make_stage5_state()
        state = enter_debug_session(state, "test bug")
        state.debug_session.authorized = True
        completed = complete_debug_session(state, "Fixed the thing")

        errors = validate_state(completed)
        resolution_errors = [e for e in errors if "resolution" in e]
        assert len(resolution_errors) == 0, f"validate_state failed: {resolution_errors}"

    def test_multiple_sessions_all_have_resolution(self):
        """Multiple abandon/complete cycles should all produce valid history."""
        state = _make_stage5_state()

        # First session: abandon
        state = enter_debug_session(state, "bug one")
        state = abandon_debug_session(state)

        # Second session: complete
        state = enter_debug_session(state, "bug two")
        state.debug_session.authorized = True
        state = complete_debug_session(state, "Fixed bug two")

        assert len(state.debug_history) == 2
        for i, entry in enumerate(state.debug_history):
            assert "resolution" in entry, f"History entry {i} missing 'resolution'"

        errors = validate_state(state)
        resolution_errors = [e for e in errors if "resolution" in e]
        assert len(resolution_errors) == 0

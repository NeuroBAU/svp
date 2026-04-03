"""Regression test for Bug 95: abandon/complete_debug_session missing resolution field.

Root cause (SVP 2.1): validate_state requires 'resolution' in every debug_history
entry, but abandon_debug_session and complete_debug_session don't write it. After
abandoning a session, the next load_state() call fails validation.

Fix (SVP 2.1): Both functions now set session_record["resolution"] when moving the
session to debug_history.

Adapted for SVP 2.2: In SVP 2.2:
- validate_state() does not exist
- enter_debug_session takes (state, bug_number: int) not (state, description)
- complete_debug_session takes (state) only, no resolution param
- abandon_debug_session marks session with "abandoned": True, no "resolution" field
- The "resolution" field concept does not apply in SVP 2.2

The tests that verify resolution field behavior are skipped.
The tests that verify basic enter/abandon/complete flow are adapted.
"""

import sys
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parents[2]
_scripts = _project_root / "scripts"
if not _scripts.is_dir():
    _scripts = _project_root / "svp" / "scripts"
sys.path.insert(0, str(_scripts))

from pipeline_state import PipelineState
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
    """In SVP 2.2, abandon_debug_session must produce a valid history entry.
    Resolution field tests are skipped (not part of SVP 2.2 schema)."""

    def test_abandon_creates_history_entry(self):
        """abandon_debug_session must move session to debug_history."""
        state = _make_stage5_state()
        state = enter_debug_session(state, 95)
        abandoned = abandon_debug_session(state)

        assert len(abandoned.debug_history) == 1
        entry = abandoned.debug_history[0]
        assert entry.get("abandoned") is True
        assert abandoned.debug_session is None

    def test_complete_creates_history_entry(self):
        """complete_debug_session must move session to debug_history."""
        state = _make_stage5_state()
        state = enter_debug_session(state, 95)
        # Manually authorize for complete_debug_session
        state.debug_session["authorized"] = True
        completed = complete_debug_session(state)

        assert len(completed.debug_history) == 1
        entry = completed.debug_history[0]
        assert completed.debug_session is None

    def test_multiple_sessions_all_have_history(self):
        """Multiple abandon/complete cycles should all produce valid history."""
        state = _make_stage5_state()

        # First session: abandon
        state = enter_debug_session(state, 1)
        state = abandon_debug_session(state)

        # Second session: complete
        state = enter_debug_session(state, 2)
        state.debug_session["authorized"] = True
        state = complete_debug_session(state)

        assert len(state.debug_history) == 2
        assert state.debug_session is None

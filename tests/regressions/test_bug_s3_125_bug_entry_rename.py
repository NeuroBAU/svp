"""Regression tests for Bug S3-125: svp_bug_entry orphan prefix rename.

`src/unit_14/stub.py` dispatch_command_status had 14 command_type branches.
Thirteen were bare-named (stub_generation, test_execution, quality_gate,
unit_completion, compliance_scan, structural_check, lessons_learned,
debug_commit, stage3_reentry, oracle_start, oracle_test_project_selection,
oracle_gate_7a, oracle_gate_7b). One — svp_bug_entry — carried an svp_
prefix from the pre-S3-121 era when slash command files were prefixed
(svp_bug.md). S3-121 renamed the file from svp_bug.md to bug.md but
explicitly scoped out state-machine command names, leaving svp_bug_entry
as a 13:1 asymmetry in the dispatcher.

S3-125 hard-renames svp_bug_entry → bug_entry everywhere. No dual-form
dispatch. No backward compatibility layer. Same pattern family as
S3-121/S3-122/S3-124 (P28 — Half-Applied Dispatch Fix).

These tests lock three invariants:

1. Positive dispatch: dispatch_command_status accepts "bug_entry" and
   creates a debug session correctly.
2. Negative sentinel: dispatch_command_status with the old "svp_bug_entry"
   string does NOT create a debug session (either raises or falls through).
   This is the load-bearing guard against a future re-introduction of the
   old name by copy-paste, historical-commit revival, or refactor mistake.
3. Body-text check: the /svp:bug slash command body (COMMAND_DEFINITIONS["bug"])
   contains --command bug_entry and does NOT contain --command svp_bug_entry.
"""

from __future__ import annotations

import pytest

from pipeline_state import PipelineState
from routing import dispatch_command_status
from slash_commands import COMMAND_DEFINITIONS


class TestPositiveDispatch:
    """bug_entry dispatches correctly (Bug S3-125)."""

    def test_bug_entry_creates_debug_session(self):
        """dispatch_command_status accepts 'bug_entry' and creates a debug session."""
        state = PipelineState(
            stage="5",
            sub_stage="repo_complete",
            total_units=29,
            pass_=2,
            debug_session=None,
            oracle_session_active=False,
        )
        new_state = dispatch_command_status(state, "bug_entry", "")

        assert new_state.debug_session is not None, (
            "Bug S3-125: dispatch_command_status with 'bug_entry' must create "
            "the debug_session object (mirrors the original Bug S3-119 behavior "
            "under the renamed dispatch key)."
        )
        assert new_state.debug_session["phase"] == "triage"
        assert new_state.debug_session["authorized"] is False


class TestNegativeSentinel:
    """The old svp_bug_entry name is forbidden (Bug S3-125).

    This is the load-bearing regression guard. If a future refactor
    accidentally re-introduces svp_bug_entry (via copy-paste from a
    historical commit, a revert, or a typo), these assertions fire
    immediately.
    """

    def test_old_svp_bug_entry_does_not_create_debug_session(self):
        """dispatch_command_status with 'svp_bug_entry' must NOT succeed.

        The S3-125 hard rename removes the dispatch branch for the old
        name. Calling with 'svp_bug_entry' falls through to whatever
        default behavior dispatch_command_status has for unknown command
        types (either returns state unchanged or raises ValueError).
        Either way, a debug session must NOT be created.
        """
        state = PipelineState(
            stage="5",
            sub_stage="repo_complete",
            total_units=29,
            pass_=2,
            debug_session=None,
            oracle_session_active=False,
        )
        # Either the call raises (unknown command type) or it returns a state
        # with debug_session still None. Both outcomes satisfy the guard.
        try:
            new_state = dispatch_command_status(state, "svp_bug_entry", "")
        except ValueError:
            # Raising on unknown command is acceptable — the old name is gone.
            return
        except Exception as e:
            # Any other exception is unexpected but still means no debug session
            # was created, which is what the sentinel checks. Re-raise for visibility.
            raise

        # If the call returned, assert the debug_session was NOT created.
        assert new_state.debug_session is None, (
            "Bug S3-125 negative sentinel FIRED: dispatch_command_status "
            "accepted 'svp_bug_entry' and created a debug session. "
            "The S3-125 hard rename removes this dispatch key. Someone "
            "has re-introduced the old name. Remove the svp_bug_entry "
            "dispatch branch and restore the hard rename."
        )

    def test_svp_bug_entry_literal_absent_from_dispatch_source(self):
        """The literal string 'svp_bug_entry' must not appear as a dispatch key.

        Parse routing.py and grep for `command_type == "svp_bug_entry"`.
        If this assertion fires, someone has re-added the dispatch branch
        under the old name.
        """
        import routing
        from pathlib import Path

        src = Path(routing.__file__).read_text()
        assert 'command_type == "svp_bug_entry"' not in src, (
            "Bug S3-125 regression: routing.py contains a dispatch branch "
            "for the old `svp_bug_entry` name. The hard rename to `bug_entry` "
            "must be preserved."
        )


class TestCommandBodyText:
    """The /svp:bug slash command body uses the new bug_entry name (Bug S3-125)."""

    def test_bug_body_contains_bug_entry(self):
        """COMMAND_DEFINITIONS['bug'] must reference --command bug_entry."""
        body = COMMAND_DEFINITIONS["bug"]
        assert "--command bug_entry" in body, (
            "Bug S3-125: /svp:bug body must invoke --command bug_entry. "
            "The slash command body is the producer side of the dispatch "
            "call; after the rename it must use the new name."
        )

    def test_bug_body_does_not_contain_svp_bug_entry(self):
        """COMMAND_DEFINITIONS['bug'] must NOT contain the old svp_bug_entry literal.

        Load-bearing negative sentinel — catches any future copy-paste
        revival of the old name.
        """
        body = COMMAND_DEFINITIONS["bug"]
        assert "svp_bug_entry" not in body, (
            "Bug S3-125 regression: /svp:bug body contains the old "
            "`svp_bug_entry` literal. The hard rename forbids the old name. "
            "Update the body text to use `bug_entry` and remove every "
            "reference to the old name."
        )


class TestDispatchTableUniformity:
    """All state-machine dispatch commands must be bare-named (Bug S3-125).

    This is the forward-looking guard: after S3-125 closes the 13:1
    asymmetry, the dispatcher should have zero svp_-prefixed command
    types. If a future change adds a new svp_-prefixed entry, this
    test fires immediately.
    """

    def test_no_svp_prefixed_dispatch_keys(self):
        """No dispatch branch in routing.py should use a `command_type == "svp_..."` key."""
        import re
        import routing
        from pathlib import Path

        src = Path(routing.__file__).read_text()
        # Find every `command_type == "<name>"` literal in the source.
        matches = re.findall(r'command_type\s*==\s*"([a-z_]+)"', src)
        offenders = [m for m in matches if m.startswith("svp_")]
        assert not offenders, (
            f"Bug S3-125 forward guard: dispatch_command_status contains "
            f"svp_-prefixed command types: {offenders}. Every state-machine "
            f"dispatch command must be bare-named. Pattern P28 — Half-Applied "
            f"Dispatch Fix. Rename the offending command(s) to remove the svp_ "
            f"prefix and audit all callers."
        )

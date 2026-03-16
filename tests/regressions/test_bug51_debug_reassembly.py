"""Bug 51 regression test: debug loop reassembly
routing after repair completion.

Verifies that dispatch_agent_status for repair_agent
with REPAIR_COMPLETE during an active debug session
triggers Stage 5 reassembly (re-invoke git_repo_agent).
"""

from __future__ import annotations

import sys
from pathlib import Path

# --------------- path setup ---------------------- #

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent.parent

_SCRIPTS_DIR = _REPO_ROOT / "svp" / "scripts"
if not _SCRIPTS_DIR.is_dir():
    _SCRIPTS_DIR = _REPO_ROOT / "scripts"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# ------------------------------------------------- #

from pipeline_state import (  # noqa: E402
    DebugSession,
    PipelineState,
)
from routing import dispatch_agent_status  # noqa: E402


def _make_debug_state() -> PipelineState:
    """Create a state with an active debug
    session."""
    state = PipelineState(
        stage="5",
        sub_stage=None,
        current_unit=10,
        total_units=24,
        delivered_repo_path="/tmp/fake-repo",
    )
    state.debug_session = DebugSession(
        phase="repair",
        affected_units=[10],
        classification="single_unit",
    )
    return state


def _make_no_debug_state() -> PipelineState:
    """Create a state with no debug session."""
    return PipelineState(
        stage="5",
        sub_stage=None,
        current_unit=10,
        total_units=24,
        delivered_repo_path="/tmp/fake-repo",
    )


class TestRepairCompleteTriggersReassembly:
    """REPAIR_COMPLETE during active debug session
    must trigger Stage 5 reassembly."""

    def test_repair_complete_triggers_reassembly(
        self,
    ) -> None:
        """Returned state should have stage='5' and
        sub_stage=None for git_repo_agent."""
        state = _make_debug_state()
        result = dispatch_agent_status(
            state,
            "repair_agent",
            "REPAIR_COMPLETE",
            unit=None,
            phase="repair",
            project_root=Path("."),
        )
        assert result.stage == "5"
        assert result.sub_stage is None
        assert result is not state

    def test_repair_complete_preserves_debug(
        self,
    ) -> None:
        """Debug session should still be active
        after reassembly trigger."""
        state = _make_debug_state()
        result = dispatch_agent_status(
            state,
            "repair_agent",
            "REPAIR_COMPLETE",
            unit=None,
            phase="repair",
            project_root=Path("."),
        )
        assert result.debug_session is not None


class TestRepairNonCompleteNoReassembly:
    """REPAIR_FAILED and REPAIR_RECLASSIFY should
    NOT trigger reassembly."""

    def test_repair_failed_no_reassemble(
        self,
    ) -> None:
        """REPAIR_FAILED should not change stage."""
        state = _make_debug_state()
        result = dispatch_agent_status(
            state,
            "repair_agent",
            "REPAIR_FAILED",
            unit=None,
            phase="repair",
            project_root=Path("."),
        )
        assert result.stage == "5"

    def test_repair_reclassify_no_reassemble(
        self,
    ) -> None:
        """REPAIR_RECLASSIFY should not trigger
        reassembly."""
        state = _make_debug_state()
        result = dispatch_agent_status(
            state,
            "repair_agent",
            "REPAIR_RECLASSIFY",
            unit=None,
            phase="repair",
            project_root=Path("."),
        )
        assert result.stage == "5"

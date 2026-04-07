"""Regression tests for Bug S3-41 and S3-42.

S3-41: SETUP_AGENT_DEFINITION must use correct terminal status names
       (PROJECT_CONTEXT_COMPLETE, PROJECT_CONTEXT_REJECTED, PROFILE_COMPLETE)
       not variant spellings (CONTEXT_DIALOG_COMPLETE, PROFILE_DIALOG_COMPLETE).

S3-42: dispatch_agent_status must handle HINT_BLUEPRINT_CONFLICT for all
       hint-receiving agents (implementation_agent, test_agent,
       coverage_review_agent, diagnostic_agent).
"""

from pathlib import Path

import pytest

from setup_agent import SETUP_AGENT_DEFINITION


# ---------------------------------------------------------------------------
# S3-41: Setup agent definition terminal status names
# ---------------------------------------------------------------------------


class TestSetupAgentDefinitionStatusNames:
    """S3-41: SETUP_AGENT_DEFINITION must use correct status names."""

    def test_uses_project_context_complete(self):
        assert "PROJECT_CONTEXT_COMPLETE" in SETUP_AGENT_DEFINITION

    def test_uses_project_context_rejected(self):
        assert "PROJECT_CONTEXT_REJECTED" in SETUP_AGENT_DEFINITION

    def test_uses_profile_complete(self):
        assert "PROFILE_COMPLETE" in SETUP_AGENT_DEFINITION

    def test_no_context_dialog_complete(self):
        assert "CONTEXT_DIALOG_COMPLETE" not in SETUP_AGENT_DEFINITION

    def test_no_profile_dialog_complete(self):
        assert "PROFILE_DIALOG_COMPLETE" not in SETUP_AGENT_DEFINITION


# ---------------------------------------------------------------------------
# S3-42: HINT_BLUEPRINT_CONFLICT dispatch for hint-receiving agents
# ---------------------------------------------------------------------------


class TestHintBlueprintConflictDispatch:
    """S3-42: dispatch_agent_status must handle HINT_BLUEPRINT_CONFLICT
    for all hint-receiving agents."""

    HINT_RECEIVING_AGENTS = [
        "implementation_agent",
        "test_agent",
        "coverage_review_agent",
        "diagnostic_agent",
    ]

    @pytest.fixture
    def state(self):
        from pipeline_state import PipelineState

        state = PipelineState(
            stage="3",
            current_unit=1,
            sub_stage="implementation",
        )
        return state

    @pytest.mark.parametrize("agent_type", HINT_RECEIVING_AGENTS)
    def test_hint_conflict_does_not_raise(self, state, agent_type):
        """dispatch_agent_status must not raise ValueError for
        HINT_BLUEPRINT_CONFLICT from hint-receiving agents."""
        from routing import dispatch_agent_status

        # Should not raise ValueError
        new = dispatch_agent_status(
            state,
            agent_type,
            "HINT_BLUEPRINT_CONFLICT: test conflict",
            Path("."),
        )
        # Must return a new state object (no bare return)
        assert new is not state

    @pytest.mark.parametrize("agent_type", HINT_RECEIVING_AGENTS)
    def test_hint_conflict_in_agent_status_lines(self, agent_type):
        """AGENT_STATUS_LINES must include HINT_BLUEPRINT_CONFLICT
        for all hint-receiving agents."""
        from routing import AGENT_STATUS_LINES

        assert agent_type in AGENT_STATUS_LINES, (
            f"{agent_type} missing from AGENT_STATUS_LINES"
        )
        assert "HINT_BLUEPRINT_CONFLICT" in AGENT_STATUS_LINES[agent_type], (
            f"HINT_BLUEPRINT_CONFLICT missing from AGENT_STATUS_LINES[{agent_type!r}]"
        )

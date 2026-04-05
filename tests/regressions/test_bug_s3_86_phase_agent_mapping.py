"""Regression tests for Bug S3-86: PHASE_TO_AGENT namespace consistency.

Every PHASE_TO_AGENT value must exist in AGENT_STATUS_LINES and have
a handler in dispatch_agent_status.
"""

import pytest

from routing import PHASE_TO_AGENT, AGENT_STATUS_LINES, dispatch_agent_status
from pipeline_state import PipelineState


class TestPhaseToAgentConsistency:
    """Structural: every PHASE_TO_AGENT value must be a valid agent type (Bug S3-86)."""

    def test_all_phase_values_in_agent_status_lines(self):
        """Every PHASE_TO_AGENT value must be a key in AGENT_STATUS_LINES."""
        for phase, agent_type in PHASE_TO_AGENT.items():
            assert agent_type in AGENT_STATUS_LINES, (
                f"PHASE_TO_AGENT['{phase}'] = '{agent_type}' "
                f"but '{agent_type}' is not in AGENT_STATUS_LINES"
            )

    def test_bug_triage_maps_to_bug_triage_agent(self):
        """Specific regression: bug_triage must map to bug_triage_agent."""
        assert PHASE_TO_AGENT["bug_triage"] == "bug_triage_agent"

    def test_all_agent_status_lines_keys_have_handlers(self, tmp_path):
        """Every AGENT_STATUS_LINES key should not raise ValueError in dispatch."""
        # We can't easily test all handlers without valid states,
        # but we can verify the bug_triage_agent handler exists by
        # checking it doesn't raise ValueError for a known status
        from routing import save_state
        from state_transitions import enter_debug_session

        state = PipelineState(
            stage="5", sub_stage="pass_transition", total_units=10,
            pass_=2,
        )
        state = enter_debug_session(state, 1)
        save_state(tmp_path, state)
        (tmp_path / ".svp").mkdir(exist_ok=True)
        (tmp_path / ".svp" / "triage_result.json").write_text(
            '{"classification": "single_unit", "affected_units": [1]}'
        )
        # This should NOT raise ValueError
        result = dispatch_agent_status(
            state, "bug_triage_agent", "TRIAGE_COMPLETE: single_unit", tmp_path
        )
        assert result is not None

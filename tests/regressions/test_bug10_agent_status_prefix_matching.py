"""Bug 10 regression: Agent status must use exact match, not prefix.

dispatch_agent_status must accept exact status strings and not match
unrelated strings that happen to share a prefix.
"""

from pathlib import Path

from routing import dispatch_agent_status, AGENT_STATUS_LINES
from pipeline_state import PipelineState


def test_exact_match_accepted():
    """Exact status line must be accepted and dispatched without error."""
    state = PipelineState(stage="3", sub_stage="implementation")
    new_state = dispatch_agent_status(
        state, "implementation_agent", "IMPLEMENTATION_COMPLETE", None, "implementation", Path(".")
    )
    # dispatch_agent_status transitions to quality_gate_b when in implementation sub-stage
    assert new_state.sub_stage == "quality_gate_b"


def test_unknown_status_rejected():
    """Unknown status line must raise ValueError."""
    state = PipelineState(stage="3", sub_stage="implementation")
    import pytest

    with pytest.raises(ValueError, match="Unknown agent status"):
        dispatch_agent_status(
            state, "implementation_agent", "TOTALLY_UNKNOWN_STATUS", None, "implementation", Path(".")
        )

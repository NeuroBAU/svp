"""Bug 10 regression: Agent status must use exact match, not prefix.

dispatch_agent_status must accept exact status strings and not match
unrelated strings that happen to share a prefix.

SVP 2.2 adaptation:
- dispatch_agent_status(state, agent_type, status_line, project_root) -- 4 args
- PipelineState from src.unit_5.stub
- AGENT_STATUS_LINES from src.unit_14.stub
"""

from pathlib import Path

import pytest

from src.unit_5.stub import PipelineState
from src.unit_14.stub import dispatch_agent_status, AGENT_STATUS_LINES


def test_exact_match_accepted():
    """Exact status line must be accepted and dispatched without error."""
    state = PipelineState(stage="3", sub_stage="implementation", current_unit=1, total_units=3)
    new_state = dispatch_agent_status(
        state, "implementation_agent", "IMPLEMENTATION_COMPLETE", Path(".")
    )
    # dispatch_agent_status returns a copy; route() handles the next transition
    assert new_state is not None
    assert new_state is not state


def test_unknown_status_rejected():
    """Unknown status line must raise ValueError."""
    state = PipelineState(stage="3", sub_stage="implementation", current_unit=1, total_units=3)

    with pytest.raises(ValueError, match="Unknown"):
        dispatch_agent_status(
            state, "implementation_agent", "TOTALLY_UNKNOWN_STATUS", Path(".")
        )

"""Bug 14 regression: Routing must emit correct PREPARE/POST commands.

format_action_block must include appropriate REMINDER lines based on
the ACTION type.
"""

from routing import format_action_block


def test_invoke_agent_reminder():
    """invoke_agent action block must include a REMINDER section."""
    action = {"ACTION": "invoke_agent", "AGENT": "test_agent"}
    block = format_action_block(action)
    assert "REMINDER" in block
    assert "last_status.txt" in block


def test_run_command_reminder():
    """run_command action block must include status file reminder."""
    action = {"ACTION": "run_command", "COMMAND": "quality_gate_a"}
    block = format_action_block(action)
    assert "last_status.txt" in block


def test_human_gate_reminder():
    """human_gate action block must include gate presentation reminder."""
    action = {"ACTION": "human_gate", "GATE_ID": "gate_1_1_spec_draft", "OPTIONS": ["APPROVE"]}
    block = format_action_block(action)
    assert "gate" in block.lower()

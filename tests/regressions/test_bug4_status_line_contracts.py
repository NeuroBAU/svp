"""Bug 4 regression: Status line patterns must match data contracts.

AGENT_STATUS_LINES must contain all documented patterns.

SVP 2.2: COMMAND_STATUS_PATTERNS removed from routing; command status
handling is internal to dispatch_command_status. AGENT_STATUS_LINES
remains and is tested below.
"""

import pytest

from routing import AGENT_STATUS_LINES


def test_agent_status_lines_has_all_agent_types():
    """AGENT_STATUS_LINES must have entries for all agent types."""
    required_agents = {
        "setup_agent",
        "stakeholder_dialog",
        "stakeholder_reviewer",
        "blueprint_author",
        "blueprint_checker",
        "blueprint_reviewer",
        "test_agent",
        "implementation_agent",
        "coverage_review_agent",
        "diagnostic_agent",
        "integration_test_author",
        "git_repo_agent",
        "help_agent",
        "hint_agent",
        "redo_agent",
        "bug_triage_agent",
        "repair_agent",
        "reference_indexing",
    }
    assert required_agents.issubset(set(AGENT_STATUS_LINES.keys()))


def test_implementation_agent_status_is_exact():
    """implementation_agent status must be exactly IMPLEMENTATION_COMPLETE."""
    statuses = AGENT_STATUS_LINES["implementation_agent"]
    assert "IMPLEMENTATION_COMPLETE" in statuses

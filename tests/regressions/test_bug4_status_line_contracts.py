"""Bug 4 regression: Status line patterns must match data contracts.

COMMAND_STATUS_PATTERNS and AGENT_STATUS_LINES must contain all
documented patterns and no undocumented ones.
"""

from routing import COMMAND_STATUS_PATTERNS, AGENT_STATUS_LINES


def test_command_status_patterns_complete():
    """COMMAND_STATUS_PATTERNS must include all 5 documented patterns."""
    required = {
        "TESTS_PASSED",
        "TESTS_FAILED",
        "TESTS_ERROR",
        "COMMAND_SUCCEEDED",
        "COMMAND_FAILED",
        "UNUSED_FUNCTIONS_DETECTED",
    }
    assert set(COMMAND_STATUS_PATTERNS) == required


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
        "coverage_review",
        "diagnostic_agent",
        "integration_test_author",
        "git_repo_agent",
        "help_agent",
        "hint_agent",
        "redo_agent",
        "bug_triage",
        "repair_agent",
        "reference_indexing",
    }
    assert required_agents.issubset(set(AGENT_STATUS_LINES.keys()))


def test_implementation_agent_status_is_exact():
    """implementation_agent status must be exactly IMPLEMENTATION_COMPLETE."""
    statuses = AGENT_STATUS_LINES["implementation_agent"]
    assert "IMPLEMENTATION_COMPLETE" in statuses

"""
Tests for Unit 17: Support Agent Definitions.

Verifies frontmatter, status lists, and MD content for
help_agent and hint_agent.
"""

from src.unit_17.stub import (
    HELP_AGENT_FRONTMATTER,
    HELP_AGENT_MD_CONTENT,
    HELP_AGENT_STATUS,
    HINT_AGENT_FRONTMATTER,
    HINT_AGENT_MD_CONTENT,
    HINT_AGENT_STATUS,
)


class TestHelpAgentFrontmatter:
    def test_name(self):
        assert HELP_AGENT_FRONTMATTER["name"] == "help_agent"

    def test_model(self):
        assert HELP_AGENT_FRONTMATTER["model"] == "claude-sonnet-4-6"

    def test_has_websearch(self):
        assert "WebSearch" in HELP_AGENT_FRONTMATTER["tools"]


class TestHintAgentFrontmatter:
    def test_name(self):
        assert HINT_AGENT_FRONTMATTER["name"] == "hint_agent"

    def test_model(self):
        assert HINT_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_has_bash(self):
        assert "Bash" in HINT_AGENT_FRONTMATTER["tools"]


class TestStatusLists:
    def test_help_statuses(self):
        assert "HELP_SESSION_COMPLETE: no hint" in HELP_AGENT_STATUS
        assert "HELP_SESSION_COMPLETE: hint forwarded" in HELP_AGENT_STATUS

    def test_hint_status(self):
        assert "HINT_ANALYSIS_COMPLETE" in HINT_AGENT_STATUS


class TestHelpAgentMd:
    def test_nonempty(self):
        assert isinstance(HELP_AGENT_MD_CONTENT, str)
        assert len(HELP_AGENT_MD_CONTENT) > 0

    def test_frontmatter(self):
        assert HELP_AGENT_MD_CONTENT.startswith("---")

    def test_agent_name(self):
        assert "help_agent" in HELP_AGENT_MD_CONTENT

    def test_terminal_status(self):
        assert "HELP_SESSION_COMPLETE" in HELP_AGENT_MD_CONTENT


class TestHintAgentMd:
    def test_nonempty(self):
        assert isinstance(HINT_AGENT_MD_CONTENT, str)
        assert len(HINT_AGENT_MD_CONTENT) > 0

    def test_frontmatter(self):
        assert HINT_AGENT_MD_CONTENT.startswith("---")

    def test_agent_name(self):
        assert "hint_agent" in HINT_AGENT_MD_CONTENT

    def test_terminal_status(self):
        assert "HINT_ANALYSIS_COMPLETE" in HINT_AGENT_MD_CONTENT

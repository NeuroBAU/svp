"""
Tests for Unit 16: Diagnostic and Classification
Agent Definitions.

Verifies frontmatter, status lists, and MD content for
diagnostic_agent and redo_agent.
"""

from diagnostic_agents import (
    DIAGNOSTIC_AGENT_FRONTMATTER,
    DIAGNOSTIC_AGENT_MD_CONTENT,
    DIAGNOSTIC_AGENT_STATUS,
    REDO_AGENT_FRONTMATTER,
    REDO_AGENT_MD_CONTENT,
    REDO_AGENT_STATUS,
)


class TestDiagnosticAgentFrontmatter:
    def test_name(self):
        fm = DIAGNOSTIC_AGENT_FRONTMATTER
        assert fm["name"] == "diagnostic_agent"

    def test_model(self):
        fm = DIAGNOSTIC_AGENT_FRONTMATTER
        assert fm["model"] == "claude-opus-4-6"

    def test_tools(self):
        assert "Bash" in DIAGNOSTIC_AGENT_FRONTMATTER["tools"]


class TestRedoAgentFrontmatter:
    def test_name(self):
        assert REDO_AGENT_FRONTMATTER["name"] == "redo_agent"

    def test_model(self):
        assert REDO_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"


class TestStatusLists:
    def test_diagnostic_statuses(self):
        assert "DIAGNOSIS_COMPLETE: implementation" in DIAGNOSTIC_AGENT_STATUS
        assert "DIAGNOSIS_COMPLETE: blueprint" in DIAGNOSTIC_AGENT_STATUS
        assert "DIAGNOSIS_COMPLETE: spec" in DIAGNOSTIC_AGENT_STATUS

    def test_redo_five_classifications(self):
        assert len(REDO_AGENT_STATUS) == 5
        assert "REDO_CLASSIFIED: spec" in REDO_AGENT_STATUS
        assert "REDO_CLASSIFIED: blueprint" in REDO_AGENT_STATUS
        assert "REDO_CLASSIFIED: gate" in REDO_AGENT_STATUS
        assert "REDO_CLASSIFIED: profile_delivery" in REDO_AGENT_STATUS
        assert "REDO_CLASSIFIED: profile_blueprint" in REDO_AGENT_STATUS


class TestDiagnosticAgentMd:
    def test_nonempty(self):
        assert isinstance(DIAGNOSTIC_AGENT_MD_CONTENT, str)
        assert len(DIAGNOSTIC_AGENT_MD_CONTENT) > 0

    def test_frontmatter(self):
        content = DIAGNOSTIC_AGENT_MD_CONTENT
        assert content.startswith("---")

    def test_agent_name(self):
        assert "diagnostic_agent" in DIAGNOSTIC_AGENT_MD_CONTENT

    def test_terminal_status(self):
        assert "DIAGNOSIS_COMPLETE" in DIAGNOSTIC_AGENT_MD_CONTENT


class TestRedoAgentMd:
    def test_nonempty(self):
        assert isinstance(REDO_AGENT_MD_CONTENT, str)
        assert len(REDO_AGENT_MD_CONTENT) > 0

    def test_frontmatter(self):
        assert REDO_AGENT_MD_CONTENT.startswith("---")

    def test_agent_name(self):
        assert "redo_agent" in REDO_AGENT_MD_CONTENT

    def test_five_classifications(self):
        assert "profile_delivery" in REDO_AGENT_MD_CONTENT
        assert "profile_blueprint" in REDO_AGENT_MD_CONTENT

    def test_terminal_status(self):
        assert "REDO_CLASSIFIED" in REDO_AGENT_MD_CONTENT

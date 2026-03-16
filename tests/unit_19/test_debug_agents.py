"""
Tests for Unit 19: Debug Loop Agent Definitions.

Verifies frontmatter, status lists, and MD content for
bug_triage_agent and repair_agent.
"""

from debug_agents import (
    BUG_TRIAGE_AGENT_MD_CONTENT,
    BUG_TRIAGE_FRONTMATTER,
    BUG_TRIAGE_STATUS,
    REPAIR_AGENT_FRONTMATTER,
    REPAIR_AGENT_MD_CONTENT,
    REPAIR_AGENT_STATUS,
)


class TestBugTriageFrontmatter:
    def test_name(self):
        fm = BUG_TRIAGE_FRONTMATTER
        assert fm["name"] == "bug_triage_agent"

    def test_model(self):
        fm = BUG_TRIAGE_FRONTMATTER
        assert fm["model"] == "claude-opus-4-6"


class TestRepairAgentFrontmatter:
    def test_name(self):
        fm = REPAIR_AGENT_FRONTMATTER
        assert fm["name"] == "repair_agent"

    def test_model(self):
        fm = REPAIR_AGENT_FRONTMATTER
        assert fm["model"] == "claude-sonnet-4-6"


class TestStatusLists:
    def test_bug_triage_statuses(self):
        assert "TRIAGE_COMPLETE: build_env" in BUG_TRIAGE_STATUS
        assert "TRIAGE_COMPLETE: single_unit" in BUG_TRIAGE_STATUS
        assert "TRIAGE_COMPLETE: cross_unit" in BUG_TRIAGE_STATUS
        assert "TRIAGE_NEEDS_REFINEMENT" in BUG_TRIAGE_STATUS
        assert "TRIAGE_NON_REPRODUCIBLE" in BUG_TRIAGE_STATUS

    def test_repair_statuses(self):
        assert "REPAIR_COMPLETE" in REPAIR_AGENT_STATUS
        assert "REPAIR_FAILED" in REPAIR_AGENT_STATUS
        assert "REPAIR_RECLASSIFY" in REPAIR_AGENT_STATUS


class TestBugTriageMd:
    def test_nonempty(self):
        assert isinstance(BUG_TRIAGE_AGENT_MD_CONTENT, str)
        assert len(BUG_TRIAGE_AGENT_MD_CONTENT) > 0

    def test_frontmatter(self):
        content = BUG_TRIAGE_AGENT_MD_CONTENT
        assert content.startswith("---")

    def test_agent_name(self):
        assert "bug_triage_agent" in BUG_TRIAGE_AGENT_MD_CONTENT

    def test_delivered_repo_path(self):
        assert "delivered_repo_path" in BUG_TRIAGE_AGENT_MD_CONTENT

    def test_read_only_start(self):
        content = BUG_TRIAGE_AGENT_MD_CONTENT.lower()
        assert "read-only" in content or ("read only" in content)

    def test_lessons_learned(self):
        content = BUG_TRIAGE_AGENT_MD_CONTENT.lower()
        assert "lessons" in content

    def test_terminal_status(self):
        assert "TRIAGE_COMPLETE" in BUG_TRIAGE_AGENT_MD_CONTENT


class TestRepairAgentMd:
    def test_nonempty(self):
        assert isinstance(REPAIR_AGENT_MD_CONTENT, str)
        assert len(REPAIR_AGENT_MD_CONTENT) > 0

    def test_frontmatter(self):
        assert REPAIR_AGENT_MD_CONTENT.startswith("---")

    def test_agent_name(self):
        assert "repair_agent" in REPAIR_AGENT_MD_CONTENT

    def test_terminal_status(self):
        assert "REPAIR_COMPLETE" in REPAIR_AGENT_MD_CONTENT

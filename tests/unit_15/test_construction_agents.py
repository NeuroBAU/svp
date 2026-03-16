"""
Tests for Unit 15: Construction Agent Definitions.

Verifies frontmatter, status lists, and MD content for
test_agent, implementation_agent, and
coverage_review_agent.
"""

from construction_agents import (
    COVERAGE_REVIEW_AGENT_MD_CONTENT,
    COVERAGE_REVIEW_FRONTMATTER,
    COVERAGE_REVIEW_STATUS,
    IMPLEMENTATION_AGENT_FRONTMATTER,
    IMPLEMENTATION_AGENT_MD_CONTENT,
    IMPLEMENTATION_AGENT_STATUS,
    TEST_AGENT_FRONTMATTER,
    TEST_AGENT_MD_CONTENT,
    TEST_AGENT_STATUS,
)


class TestTestAgentFrontmatter:
    def test_name(self):
        assert TEST_AGENT_FRONTMATTER["name"] == "test_agent"

    def test_model(self):
        assert TEST_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_tools(self):
        assert "Read" in TEST_AGENT_FRONTMATTER["tools"]
        assert "Write" in TEST_AGENT_FRONTMATTER["tools"]
        assert "Bash" in TEST_AGENT_FRONTMATTER["tools"]


class TestImplAgentFrontmatter:
    def test_name(self):
        fm = IMPLEMENTATION_AGENT_FRONTMATTER
        assert fm["name"] == "implementation_agent"

    def test_model(self):
        fm = IMPLEMENTATION_AGENT_FRONTMATTER
        assert fm["model"] == "claude-opus-4-6"


class TestCoverageReviewFrontmatter:
    def test_name(self):
        fm = COVERAGE_REVIEW_FRONTMATTER
        assert fm["name"] == "coverage_review_agent"


class TestStatusLists:
    def test_test_agent(self):
        assert "TEST_GENERATION_COMPLETE" in TEST_AGENT_STATUS
        assert "REGRESSION_TEST_COMPLETE" in TEST_AGENT_STATUS

    def test_impl_agent(self):
        assert "IMPLEMENTATION_COMPLETE" in IMPLEMENTATION_AGENT_STATUS

    def test_coverage_review(self):
        assert "COVERAGE_COMPLETE: no gaps" in COVERAGE_REVIEW_STATUS
        assert "COVERAGE_COMPLETE: tests added" in COVERAGE_REVIEW_STATUS


class TestTestAgentMd:
    def test_nonempty(self):
        assert isinstance(TEST_AGENT_MD_CONTENT, str)
        assert len(TEST_AGENT_MD_CONTENT) > 0

    def test_frontmatter(self):
        assert TEST_AGENT_MD_CONTENT.startswith("---")

    def test_agent_name(self):
        assert "test_agent" in TEST_AGENT_MD_CONTENT

    def test_mentions_contracts_only(self):
        assert "blueprint_contracts" in TEST_AGENT_MD_CONTENT

    def test_terminal_status(self):
        assert "TEST_GENERATION_COMPLETE" in TEST_AGENT_MD_CONTENT


class TestImplAgentMd:
    def test_nonempty(self):
        assert isinstance(IMPLEMENTATION_AGENT_MD_CONTENT, str)
        assert len(IMPLEMENTATION_AGENT_MD_CONTENT) > 0

    def test_frontmatter(self):
        content = IMPLEMENTATION_AGENT_MD_CONTENT
        assert content.startswith("---")

    def test_agent_name(self):
        assert "implementation_agent" in IMPLEMENTATION_AGENT_MD_CONTENT

    def test_terminal_status(self):
        assert "IMPLEMENTATION_COMPLETE" in IMPLEMENTATION_AGENT_MD_CONTENT


class TestCoverageReviewMd:
    def test_nonempty(self):
        assert isinstance(COVERAGE_REVIEW_AGENT_MD_CONTENT, str)
        assert len(COVERAGE_REVIEW_AGENT_MD_CONTENT) > 0

    def test_frontmatter(self):
        content = COVERAGE_REVIEW_AGENT_MD_CONTENT
        assert content.startswith("---")

    def test_agent_name(self):
        assert "coverage_review_agent" in COVERAGE_REVIEW_AGENT_MD_CONTENT

    def test_terminal_status(self):
        assert "COVERAGE_COMPLETE" in COVERAGE_REVIEW_AGENT_MD_CONTENT

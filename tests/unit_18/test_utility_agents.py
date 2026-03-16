"""
Tests for Unit 18: Utility Agent Definitions.

Verifies frontmatter, status lists, and MD content for
reference_indexing_agent, integration_test_author,
and git_repo_agent.
"""

from utility_agents import (
    GIT_REPO_AGENT_FRONTMATTER,
    GIT_REPO_AGENT_MD_CONTENT,
    GIT_REPO_AGENT_STATUS,
    INTEGRATION_TEST_AUTHOR_FRONTMATTER,
    INTEGRATION_TEST_AUTHOR_MD_CONTENT,
    INTEGRATION_TEST_AUTHOR_STATUS,
    REFERENCE_INDEXING_FRONTMATTER,
    REFERENCE_INDEXING_MD_CONTENT,
    REFERENCE_INDEXING_STATUS,
)


class TestRefIndexingFrontmatter:
    def test_name(self):
        fm = REFERENCE_INDEXING_FRONTMATTER
        assert fm["name"] == "reference_indexing_agent"

    def test_model(self):
        fm = REFERENCE_INDEXING_FRONTMATTER
        assert fm["model"] == "claude-sonnet-4-6"


class TestIntTestAuthorFrontmatter:
    def test_name(self):
        fm = INTEGRATION_TEST_AUTHOR_FRONTMATTER
        assert fm["name"] == "integration_test_author"

    def test_model(self):
        fm = INTEGRATION_TEST_AUTHOR_FRONTMATTER
        assert fm["model"] == "claude-opus-4-6"


class TestGitRepoAgentFrontmatter:
    def test_name(self):
        fm = GIT_REPO_AGENT_FRONTMATTER
        assert fm["name"] == "git_repo_agent"

    def test_model(self):
        fm = GIT_REPO_AGENT_FRONTMATTER
        assert fm["model"] == "claude-sonnet-4-6"

    def test_tools(self):
        tools = GIT_REPO_AGENT_FRONTMATTER["tools"]
        assert "Edit" in tools


class TestStatusLists:
    def test_ref_indexing(self):
        assert "INDEXING_COMPLETE" in REFERENCE_INDEXING_STATUS

    def test_int_test_author(self):
        assert "INTEGRATION_TESTS_COMPLETE" in INTEGRATION_TEST_AUTHOR_STATUS

    def test_git_repo(self):
        assert "REPO_ASSEMBLY_COMPLETE" in GIT_REPO_AGENT_STATUS


class TestRefIndexingMd:
    def test_nonempty(self):
        assert isinstance(REFERENCE_INDEXING_MD_CONTENT, str)
        assert len(REFERENCE_INDEXING_MD_CONTENT) > 0

    def test_frontmatter(self):
        content = REFERENCE_INDEXING_MD_CONTENT
        assert content.startswith("---")

    def test_agent_name(self):
        assert "reference_indexing_agent" in REFERENCE_INDEXING_MD_CONTENT

    def test_terminal_status(self):
        assert "INDEXING_COMPLETE" in REFERENCE_INDEXING_MD_CONTENT


class TestIntTestAuthorMd:
    def test_nonempty(self):
        assert isinstance(INTEGRATION_TEST_AUTHOR_MD_CONTENT, str)
        assert len(INTEGRATION_TEST_AUTHOR_MD_CONTENT) > 0

    def test_frontmatter(self):
        content = INTEGRATION_TEST_AUTHOR_MD_CONTENT
        assert content.startswith("---")

    def test_agent_name(self):
        assert "integration_test_author" in INTEGRATION_TEST_AUTHOR_MD_CONTENT

    def test_terminal_status(self):
        assert "INTEGRATION_TESTS_COMPLETE" in INTEGRATION_TEST_AUTHOR_MD_CONTENT


class TestGitRepoAgentMd:
    def test_nonempty(self):
        assert isinstance(GIT_REPO_AGENT_MD_CONTENT, str)
        assert len(GIT_REPO_AGENT_MD_CONTENT) > 0

    def test_frontmatter(self):
        content = GIT_REPO_AGENT_MD_CONTENT
        assert content.startswith("---")

    def test_agent_name(self):
        assert "git_repo_agent" in GIT_REPO_AGENT_MD_CONTENT

    def test_sibling_directory(self):
        content = GIT_REPO_AGENT_MD_CONTENT
        assert "sibling" in content.lower() or ("-repo" in content)

    def test_delivered_repo_path(self):
        assert "delivered_repo_path" in GIT_REPO_AGENT_MD_CONTENT

    def test_quality_config(self):
        content = GIT_REPO_AGENT_MD_CONTENT.lower()
        assert "quality" in content
        assert "ruff" in content

    def test_changelog(self):
        content = GIT_REPO_AGENT_MD_CONTENT.lower()
        assert "changelog" in content

    def test_terminal_status(self):
        assert "REPO_ASSEMBLY_COMPLETE" in GIT_REPO_AGENT_MD_CONTENT

    def test_svp_stub_check(self):
        content = GIT_REPO_AGENT_MD_CONTENT
        assert "__SVP_STUB__" in content

    def test_conventional_commits(self):
        content = GIT_REPO_AGENT_MD_CONTENT.lower()
        assert "conventional" in content

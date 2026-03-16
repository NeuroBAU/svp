"""
Tests for Unit 14: Review and Checker Agent Definitions.

Verifies frontmatter, status lists, and MD content for
stakeholder_reviewer, blueprint_checker, and
blueprint_reviewer agents.
"""

from src.unit_14.stub import (
    BLUEPRINT_CHECKER_FRONTMATTER,
    BLUEPRINT_CHECKER_MD_CONTENT,
    BLUEPRINT_CHECKER_STATUS,
    BLUEPRINT_REVIEWER_FRONTMATTER,
    BLUEPRINT_REVIEWER_MD_CONTENT,
    BLUEPRINT_REVIEWER_STATUS,
    STAKEHOLDER_REVIEWER_FRONTMATTER,
    STAKEHOLDER_REVIEWER_MD_CONTENT,
    STAKEHOLDER_REVIEWER_STATUS,
)


class TestStakeholderReviewerFrontmatter:
    def test_name(self):
        assert STAKEHOLDER_REVIEWER_FRONTMATTER["name"] == "stakeholder_reviewer"

    def test_model(self):
        assert STAKEHOLDER_REVIEWER_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_tools(self):
        tools = STAKEHOLDER_REVIEWER_FRONTMATTER["tools"]
        assert "Read" in tools
        assert "Glob" in tools


class TestBlueprintCheckerFrontmatter:
    def test_name(self):
        assert BLUEPRINT_CHECKER_FRONTMATTER["name"] == "blueprint_checker"

    def test_model(self):
        assert BLUEPRINT_CHECKER_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_has_bash_tool(self):
        assert "Bash" in (BLUEPRINT_CHECKER_FRONTMATTER["tools"])


class TestBlueprintReviewerFrontmatter:
    def test_name(self):
        assert BLUEPRINT_REVIEWER_FRONTMATTER["name"] == "blueprint_reviewer"


class TestStatusLists:
    def test_stakeholder_reviewer(self):
        assert "REVIEW_COMPLETE" in (STAKEHOLDER_REVIEWER_STATUS)

    def test_blueprint_checker_alignment(self):
        assert "ALIGNMENT_CONFIRMED" in (BLUEPRINT_CHECKER_STATUS)
        assert "ALIGNMENT_FAILED: spec" in (BLUEPRINT_CHECKER_STATUS)
        assert "ALIGNMENT_FAILED: blueprint" in (BLUEPRINT_CHECKER_STATUS)

    def test_blueprint_reviewer(self):
        assert "REVIEW_COMPLETE" in (BLUEPRINT_REVIEWER_STATUS)


class TestStakeholderReviewerMd:
    def test_nonempty(self):
        assert isinstance(STAKEHOLDER_REVIEWER_MD_CONTENT, str)
        assert len(STAKEHOLDER_REVIEWER_MD_CONTENT) > 0

    def test_frontmatter(self):
        assert STAKEHOLDER_REVIEWER_MD_CONTENT.startswith("---")

    def test_agent_name(self):
        assert "stakeholder_reviewer" in (STAKEHOLDER_REVIEWER_MD_CONTENT)

    def test_terminal_status(self):
        assert "REVIEW_COMPLETE" in (STAKEHOLDER_REVIEWER_MD_CONTENT)


class TestBlueprintCheckerMd:
    def test_nonempty(self):
        assert isinstance(BLUEPRINT_CHECKER_MD_CONTENT, str)
        assert len(BLUEPRINT_CHECKER_MD_CONTENT) > 0

    def test_frontmatter(self):
        assert BLUEPRINT_CHECKER_MD_CONTENT.startswith("---")

    def test_agent_name(self):
        assert "blueprint_checker" in (BLUEPRINT_CHECKER_MD_CONTENT)

    def test_alignment_status(self):
        assert "ALIGNMENT_CONFIRMED" in (BLUEPRINT_CHECKER_MD_CONTENT)

    def test_validates_quality(self):
        assert "quality" in (BLUEPRINT_CHECKER_MD_CONTENT.lower())

    def test_validates_dag(self):
        content = BLUEPRINT_CHECKER_MD_CONTENT.lower()
        assert "dag" in content or "acycl" in content


class TestBlueprintReviewerMd:
    def test_nonempty(self):
        assert isinstance(BLUEPRINT_REVIEWER_MD_CONTENT, str)
        assert len(BLUEPRINT_REVIEWER_MD_CONTENT) > 0

    def test_frontmatter(self):
        assert BLUEPRINT_REVIEWER_MD_CONTENT.startswith("---")

    def test_agent_name(self):
        assert "blueprint_reviewer" in (BLUEPRINT_REVIEWER_MD_CONTENT)

    def test_terminal_status(self):
        assert "REVIEW_COMPLETE" in (BLUEPRINT_REVIEWER_MD_CONTENT)

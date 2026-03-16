"""
Tests for Unit 13: Dialog Agent Definitions.

Verifies frontmatter dicts, status lists, and
Markdown content strings for setup_agent,
stakeholder_dialog_agent, and blueprint_author_agent.
"""

from dialog_agents import (
    BLUEPRINT_AUTHOR_AGENT_FRONTMATTER,
    BLUEPRINT_AUTHOR_AGENT_MD_CONTENT,
    BLUEPRINT_AUTHOR_STATUS,
    SETUP_AGENT_FRONTMATTER,
    SETUP_AGENT_MD_CONTENT,
    SETUP_AGENT_STATUS,
    STAKEHOLDER_DIALOG_AGENT_FRONTMATTER,
    STAKEHOLDER_DIALOG_AGENT_MD_CONTENT,
    STAKEHOLDER_DIALOG_STATUS,
)

# -------------------------------------------------------
# Frontmatter dicts
# -------------------------------------------------------


class TestSetupAgentFrontmatter:
    def test_name(self):
        assert SETUP_AGENT_FRONTMATTER["name"] == "setup_agent"

    def test_model(self):
        assert SETUP_AGENT_FRONTMATTER["model"] == "claude-sonnet-4-6"

    def test_tools_list(self):
        tools = SETUP_AGENT_FRONTMATTER["tools"]
        assert "Read" in tools
        assert "Write" in tools


class TestStakeholderDialogFrontmatter:
    def test_name(self):
        assert (
            STAKEHOLDER_DIALOG_AGENT_FRONTMATTER["name"] == "stakeholder_dialog_agent"
        )

    def test_model(self):
        assert STAKEHOLDER_DIALOG_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"


class TestBlueprintAuthorFrontmatter:
    def test_name(self):
        assert BLUEPRINT_AUTHOR_AGENT_FRONTMATTER["name"] == "blueprint_author_agent"

    def test_model(self):
        assert BLUEPRINT_AUTHOR_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"


# -------------------------------------------------------
# Status lists
# -------------------------------------------------------


class TestStatusLists:
    def test_setup_agent_statuses(self):
        assert "PROJECT_CONTEXT_COMPLETE" in (SETUP_AGENT_STATUS)
        assert "PROJECT_CONTEXT_REJECTED" in (SETUP_AGENT_STATUS)
        assert "PROFILE_COMPLETE" in SETUP_AGENT_STATUS

    def test_stakeholder_dialog_statuses(self):
        assert "SPEC_DRAFT_COMPLETE" in (STAKEHOLDER_DIALOG_STATUS)
        assert "SPEC_REVISION_COMPLETE" in (STAKEHOLDER_DIALOG_STATUS)

    def test_blueprint_author_statuses(self):
        assert "BLUEPRINT_DRAFT_COMPLETE" in (BLUEPRINT_AUTHOR_STATUS)
        assert "BLUEPRINT_REVISION_COMPLETE" in (BLUEPRINT_AUTHOR_STATUS)


# -------------------------------------------------------
# MD content: setup_agent
# -------------------------------------------------------


class TestSetupAgentMdContent:
    def test_is_nonempty_string(self):
        assert isinstance(SETUP_AGENT_MD_CONTENT, str)
        assert len(SETUP_AGENT_MD_CONTENT) > 0

    def test_has_frontmatter_delimiters(self):
        assert SETUP_AGENT_MD_CONTENT.startswith("---")
        assert SETUP_AGENT_MD_CONTENT.count("---") >= 2

    def test_has_agent_name_in_frontmatter(self):
        assert "setup_agent" in SETUP_AGENT_MD_CONTENT

    def test_has_model_in_frontmatter(self):
        assert "claude-sonnet-4-6" in (SETUP_AGENT_MD_CONTENT)

    def test_mentions_project_context(self):
        assert "project_context" in (SETUP_AGENT_MD_CONTENT.lower())

    def test_mentions_project_profile(self):
        assert "project_profile" in (SETUP_AGENT_MD_CONTENT.lower())

    def test_mentions_quality_preferences(self):
        content = SETUP_AGENT_MD_CONTENT.lower()
        assert "quality" in content

    def test_has_terminal_status_lines(self):
        assert "PROJECT_CONTEXT_COMPLETE" in (SETUP_AGENT_MD_CONTENT)
        assert "PROFILE_COMPLETE" in (SETUP_AGENT_MD_CONTENT)


# -------------------------------------------------------
# MD content: stakeholder_dialog_agent
# -------------------------------------------------------


class TestStakeholderDialogMdContent:
    def test_is_nonempty_string(self):
        assert isinstance(STAKEHOLDER_DIALOG_AGENT_MD_CONTENT, str)
        assert len(STAKEHOLDER_DIALOG_AGENT_MD_CONTENT) > 0

    def test_has_frontmatter_delimiters(self):
        content = STAKEHOLDER_DIALOG_AGENT_MD_CONTENT
        assert content.startswith("---")

    def test_has_agent_name(self):
        assert "stakeholder_dialog_agent" in (STAKEHOLDER_DIALOG_AGENT_MD_CONTENT)

    def test_has_terminal_status(self):
        assert "SPEC_DRAFT_COMPLETE" in (STAKEHOLDER_DIALOG_AGENT_MD_CONTENT)


# -------------------------------------------------------
# MD content: blueprint_author_agent
# -------------------------------------------------------


class TestBlueprintAuthorMdContent:
    def test_is_nonempty_string(self):
        assert isinstance(BLUEPRINT_AUTHOR_AGENT_MD_CONTENT, str)
        assert len(BLUEPRINT_AUTHOR_AGENT_MD_CONTENT) > 0

    def test_has_frontmatter_delimiters(self):
        content = BLUEPRINT_AUTHOR_AGENT_MD_CONTENT
        assert content.startswith("---")

    def test_has_agent_name(self):
        assert "blueprint_author_agent" in (BLUEPRINT_AUTHOR_AGENT_MD_CONTENT)

    def test_mentions_blueprint_prose(self):
        assert "blueprint_prose" in (BLUEPRINT_AUTHOR_AGENT_MD_CONTENT)

    def test_mentions_blueprint_contracts(self):
        assert "blueprint_contracts" in (BLUEPRINT_AUTHOR_AGENT_MD_CONTENT)

    def test_has_terminal_status(self):
        assert "BLUEPRINT_DRAFT_COMPLETE" in (BLUEPRINT_AUTHOR_AGENT_MD_CONTENT)

    def test_mentions_quality_in_profile(self):
        content = BLUEPRINT_AUTHOR_AGENT_MD_CONTENT
        assert "quality" in content.lower()

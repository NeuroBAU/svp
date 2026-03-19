"""Bug 11 regression: Delivered repo must have all required artifacts.

The git_repo_agent definition must instruct delivery of project_context.md
to docs/project_context.md in the delivered repo.
"""

from utility_agents import GIT_REPO_AGENT_MD_CONTENT


def test_git_repo_agent_delivers_project_context():
    """git_repo_agent instructions must mention project_context.md delivery."""
    assert "project_context.md" in GIT_REPO_AGENT_MD_CONTENT
    assert "docs/" in GIT_REPO_AGENT_MD_CONTENT


def test_git_repo_agent_delivers_references():
    """git_repo_agent instructions must mention reference document delivery."""
    assert "references" in GIT_REPO_AGENT_MD_CONTENT.lower()

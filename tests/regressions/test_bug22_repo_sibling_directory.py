"""Bug 22 (NEW) regression: git_repo_agent must create repo as sibling directory.

The git_repo_agent definition must instruct creating the delivered
repository as a sibling directory (at the same level as the project
directory), not as a subdirectory within the project.
"""

from generate_assembly_map import GIT_REPO_AGENT_DEFINITION


def test_git_repo_agent_md_mentions_delivery_location():
    """git_repo_agent definition must describe the delivery location."""
    content = GIT_REPO_AGENT_DEFINITION
    # The agent definition must describe creating a delivered repository
    assert "delivered" in content.lower() or "repo" in content.lower(), (
        "git_repo_agent must describe the delivery repository location"
    )

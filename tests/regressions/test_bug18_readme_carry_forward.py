"""Bug 18 (2.1) regression: Documentation preservation during reassembly.

The git_repo_agent definition must instruct delivering documentation
and quality configuration derived from the project profile, ensuring
documentation content is not lost during repo reassembly.
"""

from generate_assembly_map import GIT_REPO_AGENT_DEFINITION


def test_git_repo_agent_mentions_delivered_documentation():
    """git_repo_agent instructions must mention delivered documentation."""
    content_lower = GIT_REPO_AGENT_DEFINITION.lower()
    assert "delivered documentation" in content_lower or "deliver" in content_lower, (
        "git_repo_agent must instruct documentation delivery"
    )


def test_git_repo_agent_mentions_profile_preferences():
    """git_repo_agent must reference profile preferences for quality config."""
    assert "profile" in GIT_REPO_AGENT_DEFINITION.lower()
    assert "quality" in GIT_REPO_AGENT_DEFINITION.lower()

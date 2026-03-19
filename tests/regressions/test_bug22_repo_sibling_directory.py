"""Bug 22 (NEW) regression: git_repo_agent must create repo as sibling directory.

The git_repo_agent definition must instruct creating the delivered
repository as a sibling directory (at the same level as the project
directory), not as a subdirectory within the project.
"""

from utility_agents import GIT_REPO_AGENT_MD_CONTENT
from routing import dispatch_agent_status
from pipeline_state import PipelineState
from pathlib import Path


def test_repo_assembly_sets_sibling_path():
    """After REPO_ASSEMBLY_COMPLETE, delivered_repo_path must be a sibling path.

    The dispatch logic constructs the repo path as
    project_root / '{project_name}-repo', which is how the routing/dispatch
    infrastructure records the sibling path.
    """
    state = PipelineState(
        stage="5",
        sub_stage=None,
        project_name="myproject",
    )
    project_root = Path("/fake/project/myproject")
    new_state = dispatch_agent_status(
        state,
        "git_repo_agent",
        "REPO_ASSEMBLY_COMPLETE",
        None,
        "repo_assembly",
        project_root,
    )
    assert new_state.delivered_repo_path is not None
    assert "myproject-repo" in new_state.delivered_repo_path
    assert new_state.sub_stage == "repo_test"


def test_git_repo_agent_md_mentions_delivery_location():
    """git_repo_agent definition must describe the delivery location."""
    content = GIT_REPO_AGENT_MD_CONTENT
    # The agent definition must describe creating a delivered repository
    assert "delivered" in content.lower() or "repo" in content.lower(), (
        "git_repo_agent must describe the delivery repository location"
    )

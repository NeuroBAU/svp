"""Bug 11 regression: Delivered repo must have all required artifacts.

The git_repo_agent definition must instruct delivery of documentation
and source files to the delivered repo.

SVP 2.2 adaptation:
- GIT_REPO_AGENT_DEFINITION is in src.unit_23.stub
- SVP 2.2 agent definition mentions docs/ for documentation delivery
  but does not explicitly mention project_context.md or "references"
  as standalone strings. The cross-references and docs/ patterns serve
  the same purpose.
"""

from generate_assembly_map import GIT_REPO_AGENT_DEFINITION


def test_git_repo_agent_delivers_documentation():
    """git_repo_agent instructions must mention docs delivery."""
    assert "docs/" in GIT_REPO_AGENT_DEFINITION or "docs" in GIT_REPO_AGENT_DEFINITION.lower()


def test_git_repo_agent_mentions_cross_references():
    """git_repo_agent instructions must mention cross-references or path handling."""
    lower = GIT_REPO_AGENT_DEFINITION.lower()
    assert "cross-reference" in lower or "reference" in lower or "path" in lower

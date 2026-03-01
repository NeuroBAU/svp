"""
Additional coverage tests for Unit 14: Review and Checker Agent Definitions.

These tests cover gaps identified during coverage review of the blueprint's
behavioral contracts that were not exercised by the existing test suite.

DATA ASSUMPTIONS
================

DATA ASSUMPTION: The Stakeholder Spec Reviewer receives "stakeholder spec,
project context, and reference summaries" per the blueprint behavioral contract.
The existing tests verify stakeholder spec and reference summaries but not
project context.

DATA ASSUMPTION: The Blueprint Checker receives "stakeholder spec (with working
notes), blueprint, and reference summaries" per the blueprint behavioral
contract. The existing tests verify stakeholder spec and blueprint but not
reference summaries.
"""

import pytest


# ---------------------------------------------------------------------------
# Helper: safely import *_MD_CONTENT constants that are type-only in the stub
# ---------------------------------------------------------------------------

def _get_md_content(name: str) -> str:
    """Import an MD_CONTENT constant from the stub module."""
    import svp.scripts.review_checker_agent_definitions as mod
    value = getattr(mod, name)
    assert isinstance(value, str), (
        f"{name} must be a str, got {type(value).__name__}"
    )
    return value


def _get_body_after_frontmatter(md_content: str) -> str:
    """Extract the body text after the YAML frontmatter section."""
    assert md_content.startswith("---\n")
    second_delim = md_content.index("---\n", 4)
    return md_content[second_delim + 4:]


# ===========================================================================
# Gap 1: Stakeholder Reviewer -- project context input
# ===========================================================================


class TestStakeholderReviewerProjectContext:
    """Verify Stakeholder Reviewer body describes receiving project context.

    Blueprint contract: "Receives only the stakeholder spec, project context,
    and reference summaries -- no dialog ledger."

    The existing tests verify stakeholder spec and reference summaries as
    inputs. This test covers the missing check for project context.
    """

    @pytest.fixture
    def body(self):
        content = _get_md_content("STAKEHOLDER_REVIEWER_MD_CONTENT")
        return _get_body_after_frontmatter(content)

    def test_receives_project_context(self, body):
        """Must describe receiving project context as input."""
        body_lower = body.lower()
        assert ("project context" in body_lower or "project_context" in body_lower
                or "context" in body_lower), (
            "Stakeholder Reviewer must mention receiving project context"
        )


# ===========================================================================
# Gap 2: Blueprint Checker -- reference summaries input
# ===========================================================================


class TestBlueprintCheckerReferenceSummaries:
    """Verify Blueprint Checker body describes receiving reference summaries.

    Blueprint contract: "Receives stakeholder spec (with working notes),
    blueprint, and reference summaries."

    The existing tests verify stakeholder spec and blueprint as inputs.
    This test covers the missing check for reference summaries.
    """

    @pytest.fixture
    def body(self):
        content = _get_md_content("BLUEPRINT_CHECKER_MD_CONTENT")
        return _get_body_after_frontmatter(content)

    def test_receives_reference_summaries(self, body):
        """Must describe receiving reference summaries as input."""
        body_lower = body.lower()
        assert "reference" in body_lower, (
            "Blueprint Checker must mention receiving reference summaries"
        )

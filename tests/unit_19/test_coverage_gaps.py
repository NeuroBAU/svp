"""
Additional coverage tests for Unit 19: Debug Loop Agent Definitions.

These tests cover behavioral contracts implied or explicitly stated
in the blueprint that are not covered by the primary test suite.

DATA ASSUMPTIONS
================

DATA ASSUMPTION: Bug Triage Agent is described as "ledger-based multi-turn"
in the Tier 1 description. The body must describe the multi-turn dialog
pattern.

DATA ASSUMPTION: Repair Agent is described as "single-shot" for
build/environment fixes. The body must describe the single-shot nature.

DATA ASSUMPTION: Both agents implement spec Section 12.9. The agent
definition bodies should reference this specification section.

DATA ASSUMPTION: Repair Agent can modify "directory structure" per the
behavioral contract. The body must mention directory structure as a
modifiable item.

DATA ASSUMPTION: Bug Triage Agent triage dialog uses its own ledger
format "bug_triage_N.jsonl" -- the .jsonl extension must appear in
the body alongside the bug_triage naming convention.

DATA ASSUMPTION: Repair Agent body must specifically name "stub.py"
as a prohibited file, since the invariant says "implementation .py
files in src/unit_N/ other than __init__.py" and stub.py is the
primary implementation module.
"""

import pytest

from svp.scripts.debug_loop_agent_definitions import (
    BUG_TRIAGE_AGENT_FRONTMATTER,
    REPAIR_AGENT_FRONTMATTER,
    BUG_TRIAGE_STATUS,
    REPAIR_AGENT_STATUS,
)


# ---------------------------------------------------------------------------
# Helper: safely import *_MD_CONTENT constants
# ---------------------------------------------------------------------------

def _get_md_content(name: str) -> str:
    """Safely retrieve an MD_CONTENT constant by name."""
    import svp.scripts.debug_loop_agent_definitions as mod
    val = getattr(mod, name, None)
    if val is None or not isinstance(val, str):
        pytest.fail(f"{name} is not defined or not a string in svp.scripts.debug_loop_agent_definitions")
    return val


def _get_body_after_frontmatter(md_content: str) -> str:
    """Extract the body text after the YAML frontmatter section."""
    assert md_content.startswith("---\n")
    second_delim = md_content.index("---\n", 4)
    return md_content[second_delim + 4:]


# ===========================================================================
# Gap 1: Bug Triage Agent multi-turn nature
# Blueprint Tier 1: "The Bug Triage Agent uses ledger-based multi-turn
# for Socratic triage dialog."
# ===========================================================================


class TestBugTriageMultiTurn:
    """Bug Triage Agent uses ledger-based multi-turn dialog per Tier 1 description."""

    def test_describes_multi_turn(self):
        """Body must describe the multi-turn dialog pattern."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content).lower()
        assert "multi-turn" in body or "multi turn" in body or "multiple turn" in body, (
            "Bug Triage Agent body must describe the multi-turn dialog pattern"
        )


# ===========================================================================
# Gap 2: Repair Agent single-shot nature
# Blueprint Tier 1: "The Repair Agent is single-shot for
# build/environment fixes."
# ===========================================================================


class TestRepairAgentSingleShot:
    """Repair Agent is single-shot for build/environment fixes per Tier 1 description."""

    def test_describes_single_shot(self):
        """Body must describe the single-shot execution model."""
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content).lower()
        assert "single-shot" in body or "single shot" in body or "one pass" in body, (
            "Repair Agent body must describe the single-shot execution model"
        )


# ===========================================================================
# Gap 3: Spec Section 12.9 reference
# Blueprint Tier 1: "Implements spec Section 12.9."
# ===========================================================================


class TestSpecSectionReference:
    """Both agents implement spec Section 12.9 per the blueprint description."""

    def test_bug_triage_references_spec_section(self):
        """Bug Triage Agent body should reference spec Section 12.9."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        assert "12.9" in body or "section 12" in body.lower(), (
            "Bug Triage Agent body must reference spec Section 12.9"
        )

    def test_repair_references_spec_section(self):
        """Repair Agent body should reference spec Section 12.9."""
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        assert "12.9" in body or "section 12" in body.lower(), (
            "Repair Agent body must reference spec Section 12.9"
        )


# ===========================================================================
# Gap 4: Repair Agent directory structure modification
# Blueprint Tier 3 Behavioral Contract: "Can modify: environment files,
# pyproject.toml, __init__.py files, directory structure."
# The existing test_describes_narrow_mandate checks environment,
# pyproject.toml, and __init__.py but not directory structure.
# ===========================================================================


class TestRepairAgentDirectoryStructure:
    """Repair Agent can modify directory structure per the behavioral contract."""

    def test_mentions_directory_structure(self):
        """Body must mention directory structure as a modifiable item."""
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content).lower()
        assert "directory" in body or "directories" in body, (
            "Repair Agent body must mention directory structure as modifiable"
        )


# ===========================================================================
# Gap 5: Bug Triage ledger jsonl format
# Blueprint Tier 3 Behavioral Contract: "Triage dialog uses its own
# ledger (bug_triage_N.jsonl)."
# The existing test_describes_own_ledger has operator precedence that
# allows passing with just "ledger" present. This test explicitly
# verifies the .jsonl format is documented.
# ===========================================================================


class TestBugTriageLedgerJsonlFormat:
    """Bug Triage Agent ledger uses .jsonl format specifically."""

    def test_mentions_jsonl_format(self):
        """Body must specifically mention the .jsonl ledger file format."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content).lower()
        assert "jsonl" in body, (
            "Bug Triage Agent body must mention the .jsonl ledger format"
        )

    def test_mentions_bug_triage_and_jsonl_together(self):
        """Body must describe the bug_triage_N.jsonl naming convention."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content).lower()
        # Both must appear to confirm the naming convention
        assert "bug_triage" in body and "jsonl" in body, (
            "Bug Triage Agent body must describe the bug_triage_N.jsonl naming convention"
        )


# ===========================================================================
# Gap 6: Repair Agent specifically names stub.py as prohibited
# Blueprint invariant: "Repair Agent cannot modify implementation files
# (src/unit_N/*.py other than __init__.py)"
# The existing tests check broadly for "implementation" + restriction
# language, but do not verify that the specific file name "stub.py"
# is called out as prohibited.
# ===========================================================================


class TestRepairAgentStubPyProhibited:
    """Repair Agent body must specifically name stub.py as prohibited."""

    def test_mentions_stub_py(self):
        """Body must specifically name stub.py as a prohibited file."""
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content).lower()
        assert "stub.py" in body, (
            "Repair Agent body must specifically name stub.py as a prohibited file"
        )

"""
Additional coverage tests for Unit 13: Dialog Agent Definitions.

These tests cover behavioral contracts and invariants from the blueprint
that were not exercised by the existing test suite.

DATA ASSUMPTIONS
================

DATA ASSUMPTION: The structured response format invariant requires ALL THREE
tokens -- [QUESTION], [DECISION], [CONFIRMED] -- to be mentioned in every
agent's instructions, not just "at least one." This is because the invariant
states "Every response must end with exactly one of: [QUESTION], [DECISION],
[CONFIRMED]" which requires the agent to know about all three options.

DATA ASSUMPTION: The YAML frontmatter in *_MD_CONTENT must match the
corresponding *_FRONTMATTER dict on ALL fields, including description.
The behavioral contract states "The YAML frontmatter must match the
corresponding *_FRONTMATTER dict."

DATA ASSUMPTION: All three agents use the "ledger-based multi-turn
interaction pattern" per the unit description and the Unit 4 dependency.
Their instructions must mention the conversation ledger mechanism.

DATA ASSUMPTION: The Blueprint Author's spec ambiguity handling must
describe BOTH clarification (working note) AND contradiction (targeted
spec revision) as distinct handling paths. The behavioral contract says
"distinguishes clarification (working note) from contradiction (targeted
spec revision)."

DATA ASSUMPTION: Each agent's behavioral instructions must describe:
the agent's purpose, its methodology, its input/output format, its
constraints, and its terminal status line(s) per the Tier 3 behavioral
contract about completeness of instructions.

DATA ASSUMPTION: The frontmatter "description" field in *_FRONTMATTER
contains a colon (e.g., "Creates structured project_context.md through
Socratic dialog") but the simple YAML parser handles this correctly by
using partition on the first colon only.
"""

import pytest
from typing import Any, Dict

from svp.scripts.dialog_agent_definitions import (
    SETUP_AGENT_FRONTMATTER,
    STAKEHOLDER_DIALOG_AGENT_FRONTMATTER,
    BLUEPRINT_AUTHOR_AGENT_FRONTMATTER,
)


# ---------------------------------------------------------------------------
# Helpers (duplicated from main test file for independence)
# ---------------------------------------------------------------------------

def _get_md_content(name: str) -> str:
    """Import an MD_CONTENT constant from the stub module."""
    import svp.scripts.dialog_agent_definitions as mod
    value = getattr(mod, name)
    assert isinstance(value, str), (
        f"{name} must be a str, got {type(value).__name__}"
    )
    return value


def _parse_frontmatter(md_content: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from an agent definition Markdown string."""
    assert md_content.startswith("---\n")
    second_delim = md_content.index("---\n", 4)
    yaml_block = md_content[4:second_delim]
    result: Dict[str, Any] = {}
    current_key = None
    current_list: list = []
    lines = yaml_block.splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith("  - ") or line.startswith("\t- "):
            item = stripped[2:].strip().strip("\"'")
            current_list.append(item)
            continue
        if current_key and current_list:
            result[current_key] = current_list
            current_list = []
            current_key = None
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1]
                items = [item.strip().strip("\"'") for item in inner.split(",") if item.strip()]
                result[key] = items
            elif val == "":
                current_key = key
            elif val.startswith('"') and val.endswith('"'):
                result[key] = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                result[key] = val[1:-1]
            else:
                result[key] = val
    if current_key and current_list:
        result[current_key] = current_list
    return result


def _get_body_after_frontmatter(md_content: str) -> str:
    """Extract the body text after the YAML frontmatter section."""
    assert md_content.startswith("---\n")
    second_delim = md_content.index("---\n", 4)
    return md_content[second_delim + 4:]


# ===========================================================================
# Gap 1: All agents must mention ALL THREE structured response format tokens
# ===========================================================================


class TestStructuredResponseFormatCompleteness:
    """The invariant states every response must end with exactly one of
    [QUESTION], [DECISION], [CONFIRMED]. This means ALL three tokens must
    be documented in each agent's instructions so the agent knows the full
    vocabulary. The existing cross-cutting test only checks for 'at least one.'
    """

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_mentions_question_token(self, const_name):
        """Each agent must mention [QUESTION] in its instructions."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        assert "[QUESTION]" in body, (
            f"{const_name} must mention [QUESTION] structured response token"
        )

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_mentions_decision_token(self, const_name):
        """Each agent must mention [DECISION] in its instructions."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        assert "[DECISION]" in body, (
            f"{const_name} must mention [DECISION] structured response token"
        )

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_mentions_confirmed_token(self, const_name):
        """Each agent must mention [CONFIRMED] in its instructions."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        assert "[CONFIRMED]" in body, (
            f"{const_name} must mention [CONFIRMED] structured response token"
        )


# ===========================================================================
# Gap 2: Frontmatter description field must match between MD_CONTENT and
#         the *_FRONTMATTER constant dict
# ===========================================================================


class TestFrontmatterDescriptionMatches:
    """The behavioral contract says 'The YAML frontmatter must match the
    corresponding *_FRONTMATTER dict.' The existing Section 5 tests check
    name, model, and tools but omit the description field.
    """

    def test_setup_agent_description_matches(self):
        """Setup Agent MD_CONTENT frontmatter description must match
        SETUP_AGENT_FRONTMATTER['description']."""
        content = _get_md_content("SETUP_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert "description" in fm, (
            "SETUP_AGENT_MD_CONTENT frontmatter must contain 'description:'"
        )
        assert fm["description"] == SETUP_AGENT_FRONTMATTER["description"], (
            f"SETUP_AGENT_MD_CONTENT description mismatch: "
            f"got {fm['description']!r}, expected "
            f"{SETUP_AGENT_FRONTMATTER['description']!r}"
        )

    def test_stakeholder_dialog_description_matches(self):
        """Stakeholder Dialog Agent MD_CONTENT frontmatter description must
        match STAKEHOLDER_DIALOG_AGENT_FRONTMATTER['description']."""
        content = _get_md_content("STAKEHOLDER_DIALOG_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert "description" in fm, (
            "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT frontmatter must contain "
            "'description:'"
        )
        assert fm["description"] == STAKEHOLDER_DIALOG_AGENT_FRONTMATTER["description"], (
            f"STAKEHOLDER_DIALOG_AGENT_MD_CONTENT description mismatch: "
            f"got {fm['description']!r}, expected "
            f"{STAKEHOLDER_DIALOG_AGENT_FRONTMATTER['description']!r}"
        )

    def test_blueprint_author_description_matches(self):
        """Blueprint Author Agent MD_CONTENT frontmatter description must
        match BLUEPRINT_AUTHOR_AGENT_FRONTMATTER['description']."""
        content = _get_md_content("BLUEPRINT_AUTHOR_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert "description" in fm, (
            "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT frontmatter must contain "
            "'description:'"
        )
        assert fm["description"] == BLUEPRINT_AUTHOR_AGENT_FRONTMATTER["description"], (
            f"BLUEPRINT_AUTHOR_AGENT_MD_CONTENT description mismatch: "
            f"got {fm['description']!r}, expected "
            f"{BLUEPRINT_AUTHOR_AGENT_FRONTMATTER['description']!r}"
        )


# ===========================================================================
# Gap 3: All agents must mention the conversation ledger mechanism
# ===========================================================================


class TestConversationLedgerMention:
    """The unit description says agents use the 'ledger-based multi-turn
    interaction pattern (spec Section 15.1)' and lists Unit 4 (Ledger Manager)
    as a dependency. Each agent's instructions must mention the conversation
    ledger so the agent knows how to interact with it.
    """

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_mentions_ledger(self, const_name):
        """Each agent's body must mention the conversation ledger."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        body_lower = body.lower()
        assert "ledger" in body_lower, (
            f"{const_name} must mention the conversation ledger in its "
            "instructions (ledger-based multi-turn interaction pattern)"
        )


# ===========================================================================
# Gap 4: Blueprint Author must describe BOTH clarification AND contradiction
#         as distinct spec ambiguity handling paths
# ===========================================================================


class TestBlueprintAuthorAmbiguityDistinction:
    """The behavioral contract says the Blueprint Author 'distinguishes
    clarification (working note) from contradiction (targeted spec revision).'
    The existing test checks for clarification/working note/ambiguity but
    does not verify the contradiction path is also described.
    """

    @pytest.fixture
    def body(self):
        return _get_body_after_frontmatter(
            _get_md_content("BLUEPRINT_AUTHOR_AGENT_MD_CONTENT")
        )

    def test_describes_contradiction_handling(self, body):
        """Blueprint Author must describe contradiction handling as distinct
        from clarification -- contradictions require targeted spec revision."""
        body_lower = body.lower()
        assert "contradiction" in body_lower, (
            "Blueprint Author must mention 'contradiction' as a distinct "
            "ambiguity handling path (requiring targeted spec revision)"
        )

    def test_describes_clarification_as_working_note(self, body):
        """Blueprint Author must describe clarification as a working note
        that can be resolved without spec revision."""
        body_lower = body.lower()
        assert ("clarification" in body_lower and "working note" in body_lower), (
            "Blueprint Author must describe clarification as a 'working note' "
            "that can be resolved without spec revision"
        )


# ===========================================================================
# Gap 5: Each agent must describe its methodology and input/output format
# ===========================================================================


class TestAgentInstructionSections:
    """The behavioral contract says agent instructions must describe:
    'the agent's purpose, its methodology, its input/output format, its
    constraints, and its terminal status line(s).' Purpose, constraints,
    and terminal status lines are already tested. This covers methodology
    and input/output format.
    """

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_describes_methodology(self, const_name):
        """Each agent must describe its methodology."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        body_lower = body.lower()
        assert ("methodology" in body_lower or "method" in body_lower
                or "step" in body_lower or "process" in body_lower
                or "approach" in body_lower), (
            f"{const_name} must describe its methodology (how it works)"
        )

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_describes_input_output_format(self, const_name):
        """Each agent must describe its input/output format."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        body_lower = body.lower()
        has_input = "input" in body_lower
        has_output = "output" in body_lower
        assert has_input and has_output, (
            f"{const_name} must describe both its input and output format "
            f"(has_input={has_input}, has_output={has_output})"
        )


# ===========================================================================
# Gap 6: Frontmatter contains 'description:' key in all MD_CONTENT strings
# ===========================================================================


class TestFrontmatterContainsDescription:
    """The YAML frontmatter invariant lists 'name:', 'model:', 'tools:' as
    required fields. The *_FRONTMATTER dicts also include 'description'.
    The existing tests check the frontmatter dict has description but do not
    verify the MD_CONTENT YAML frontmatter itself contains 'description:'.
    """

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_frontmatter_contains_description_key(self, const_name):
        """Parsed frontmatter from MD_CONTENT must have 'description' key."""
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert "description" in fm, (
            f"{const_name} YAML frontmatter must contain 'description:' key"
        )


# ===========================================================================
# Gap 7: Blueprint Author describes decomposition-level hint weighting
# ===========================================================================


class TestBlueprintAuthorHintWeighting:
    """The behavioral contract says 'decomposition-level hints carry
    additional weight.' The existing test checks for the word 'hint' but
    does not verify the concept of weighted/prioritized hints is described.
    """

    def test_describes_decomposition_hint_weight(self):
        """Blueprint Author must describe that decomposition-level hints
        carry additional weight."""
        body = _get_body_after_frontmatter(
            _get_md_content("BLUEPRINT_AUTHOR_AGENT_MD_CONTENT")
        )
        body_lower = body.lower()
        assert ("weight" in body_lower or "priorit" in body_lower
                or "additional" in body_lower), (
            "Blueprint Author must describe that decomposition-level hints "
            "carry additional weight or priority"
        )

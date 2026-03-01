"""
Tests for Unit 13: Dialog Agent Definitions.

Validates the YAML frontmatter dictionaries, terminal status line lists,
and the three *_MD_CONTENT agent definition strings for the Setup Agent,
Stakeholder Dialog Agent, and Blueprint Author Agent.

DATA ASSUMPTIONS
================

DATA ASSUMPTION: YAML frontmatter in each *_MD_CONTENT string uses the
standard "---" delimiter on separate lines, with key: value pairs between
them. This is the Claude Code agent definition format.

DATA ASSUMPTION: The frontmatter dictionaries defined in Tier 2 signatures
exactly match the keys/values specified in the blueprint. These are the
canonical agent metadata attributes.

DATA ASSUMPTION: The structured response format requires every agent response
to end with exactly one of [QUESTION], [DECISION], [CONFIRMED]. This is
the ledger-based multi-turn interaction pattern from spec Section 15.1.

DATA ASSUMPTION: The three-tier format for Blueprint Author units uses the
exact heading "### Tier 2 \\u2014 Signatures" (with em-dash, Unicode U+2014).

DATA ASSUMPTION: "Substantial behavioral instructions" means >100 characters
after the second YAML frontmatter delimiter, per the Tier 2 invariant.

DATA ASSUMPTION: The six tools available to all agents are the standard
Claude Code tool set: Read, Write, Edit, Bash, Glob, Grep.

DATA ASSUMPTION: Setup Agent uses claude-sonnet-4-6, while Stakeholder Dialog
and Blueprint Author agents use claude-opus-4-6, reflecting the different
complexity requirements of each role.

DATA ASSUMPTION: Terminal status lines are exact string matches used by the
main session routing script. No variations or prefixes are allowed.
"""

import re
import json
from typing import Any, Dict, List

import pytest

# Import the unit under test from the stub module
from svp.scripts.dialog_agent_definitions import (
    SETUP_AGENT_FRONTMATTER,
    STAKEHOLDER_DIALOG_AGENT_FRONTMATTER,
    BLUEPRINT_AUTHOR_AGENT_FRONTMATTER,
    SETUP_AGENT_STATUS,
    STAKEHOLDER_DIALOG_STATUS,
    BLUEPRINT_AUTHOR_STATUS,
)


# ---------------------------------------------------------------------------
# Helper: safely import *_MD_CONTENT constants that are type-only in the stub
# ---------------------------------------------------------------------------

def _get_md_content(name: str) -> str:
    """Import an MD_CONTENT constant from the stub module.

    The stub declares these as type annotations without values, so import
    will fail on the stub (red run) and succeed on the implementation.
    """
    import svp.scripts.dialog_agent_definitions as mod
    value = getattr(mod, name)
    assert isinstance(value, str), (
        f"{name} must be a str, got {type(value).__name__}"
    )
    return value


def _parse_frontmatter(md_content: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from an agent definition Markdown string.

    Expects the content to start with '---\\n', followed by YAML,
    followed by another '---\\n'.
    """
    assert md_content.startswith("---\n"), (
        "MD content must start with '---\\n' (YAML frontmatter delimiter)"
    )
    # Find the second '---' delimiter
    second_delim = md_content.index("---\n", 4)
    yaml_block = md_content[4:second_delim]
    # Simple YAML frontmatter parser (avoids pyyaml dependency)
    result: Dict[str, Any] = {}
    current_key = None
    current_list: list = []
    lines = yaml_block.splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Check for list item (indented "- value")
        if line.startswith("  - ") or line.startswith("\t- "):
            item = stripped[2:].strip().strip("\"'")
            current_list.append(item)
            continue
        # If we were collecting a list, save it
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
                # Could be a multiline list follows
                current_key = key
            elif val.startswith('"') and val.endswith('"'):
                result[key] = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                result[key] = val[1:-1]
            else:
                result[key] = val
    # Final list if any
    if current_key and current_list:
        result[current_key] = current_list
    return result


def _get_body_after_frontmatter(md_content: str) -> str:
    """Extract the body text after the YAML frontmatter section."""
    assert md_content.startswith("---\n")
    second_delim = md_content.index("---\n", 4)
    return md_content[second_delim + 4:]


# ===========================================================================
# Section 1: Frontmatter Dictionary Constants
# ===========================================================================


class TestFrontmatterConstants:
    """Verify the YAML frontmatter dictionaries match the blueprint."""

    # -- Setup Agent --

    def test_setup_agent_frontmatter_is_dict(self):
        assert isinstance(SETUP_AGENT_FRONTMATTER, dict)

    def test_setup_agent_frontmatter_name(self):
        assert SETUP_AGENT_FRONTMATTER["name"] == "setup_agent"

    def test_setup_agent_frontmatter_description(self):
        assert SETUP_AGENT_FRONTMATTER["description"] == (
            "Creates structured project_context.md through Socratic dialog"
        )

    def test_setup_agent_frontmatter_model(self):
        # DATA ASSUMPTION: Setup Agent uses claude-sonnet-4-6 per blueprint
        assert SETUP_AGENT_FRONTMATTER["model"] == "claude-sonnet-4-6"

    def test_setup_agent_frontmatter_tools(self):
        # DATA ASSUMPTION: Standard Claude Code tool set
        assert SETUP_AGENT_FRONTMATTER["tools"] == [
            "Read", "Write", "Edit", "Bash", "Glob", "Grep"
        ]

    # -- Stakeholder Dialog Agent --

    def test_stakeholder_dialog_frontmatter_is_dict(self):
        assert isinstance(STAKEHOLDER_DIALOG_AGENT_FRONTMATTER, dict)

    def test_stakeholder_dialog_frontmatter_name(self):
        assert STAKEHOLDER_DIALOG_AGENT_FRONTMATTER["name"] == (
            "stakeholder_dialog_agent"
        )

    def test_stakeholder_dialog_frontmatter_description(self):
        assert STAKEHOLDER_DIALOG_AGENT_FRONTMATTER["description"] == (
            "Conducts Socratic dialog to produce the stakeholder spec"
        )

    def test_stakeholder_dialog_frontmatter_model(self):
        assert STAKEHOLDER_DIALOG_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_stakeholder_dialog_frontmatter_tools(self):
        assert STAKEHOLDER_DIALOG_AGENT_FRONTMATTER["tools"] == [
            "Read", "Write", "Edit", "Bash", "Glob", "Grep"
        ]

    # -- Blueprint Author Agent --

    def test_blueprint_author_frontmatter_is_dict(self):
        assert isinstance(BLUEPRINT_AUTHOR_AGENT_FRONTMATTER, dict)

    def test_blueprint_author_frontmatter_name(self):
        assert BLUEPRINT_AUTHOR_AGENT_FRONTMATTER["name"] == (
            "blueprint_author_agent"
        )

    def test_blueprint_author_frontmatter_description(self):
        assert BLUEPRINT_AUTHOR_AGENT_FRONTMATTER["description"] == (
            "Conducts decomposition dialog and produces the technical blueprint"
        )

    def test_blueprint_author_frontmatter_model(self):
        assert BLUEPRINT_AUTHOR_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_blueprint_author_frontmatter_tools(self):
        assert BLUEPRINT_AUTHOR_AGENT_FRONTMATTER["tools"] == [
            "Read", "Write", "Edit", "Bash", "Glob", "Grep"
        ]

    # -- Cross-cutting frontmatter checks --

    def test_all_frontmatter_have_required_keys(self):
        """Every frontmatter dict must have name, description, model, tools."""
        required_keys = {"name", "description", "model", "tools"}
        for label, fm in [
            ("SETUP_AGENT", SETUP_AGENT_FRONTMATTER),
            ("STAKEHOLDER_DIALOG", STAKEHOLDER_DIALOG_AGENT_FRONTMATTER),
            ("BLUEPRINT_AUTHOR", BLUEPRINT_AUTHOR_AGENT_FRONTMATTER),
        ]:
            missing = required_keys - set(fm.keys())
            assert not missing, (
                f"{label}_FRONTMATTER missing keys: {missing}"
            )


# ===========================================================================
# Section 2: Terminal Status Line Constants
# ===========================================================================


class TestStatusLineConstants:
    """Verify terminal status line lists match the blueprint."""

    def test_setup_agent_status_is_list(self):
        assert isinstance(SETUP_AGENT_STATUS, list)

    def test_setup_agent_status_values(self):
        assert SETUP_AGENT_STATUS == [
            "PROJECT_CONTEXT_COMPLETE", "PROJECT_CONTEXT_REJECTED"
        ]

    def test_stakeholder_dialog_status_is_list(self):
        assert isinstance(STAKEHOLDER_DIALOG_STATUS, list)

    def test_stakeholder_dialog_status_values(self):
        assert STAKEHOLDER_DIALOG_STATUS == [
            "SPEC_DRAFT_COMPLETE", "SPEC_REVISION_COMPLETE"
        ]

    def test_blueprint_author_status_is_list(self):
        assert isinstance(BLUEPRINT_AUTHOR_STATUS, list)

    def test_blueprint_author_status_values(self):
        assert BLUEPRINT_AUTHOR_STATUS == ["BLUEPRINT_DRAFT_COMPLETE"]


# ===========================================================================
# Section 3: MD_CONTENT String Existence and Type
# ===========================================================================


class TestMdContentExistence:
    """Verify that *_MD_CONTENT constants exist and are non-empty strings.

    These tests will fail on the stub (red run) because the stub only
    declares type annotations without assigning values.
    """

    def test_setup_agent_md_content_is_string(self):
        content = _get_md_content("SETUP_AGENT_MD_CONTENT")
        assert isinstance(content, str)
        assert len(content) > 0, "SETUP_AGENT_MD_CONTENT must not be empty"

    def test_stakeholder_dialog_agent_md_content_is_string(self):
        content = _get_md_content("STAKEHOLDER_DIALOG_AGENT_MD_CONTENT")
        assert isinstance(content, str)
        assert len(content) > 0

    def test_blueprint_author_agent_md_content_is_string(self):
        content = _get_md_content("BLUEPRINT_AUTHOR_AGENT_MD_CONTENT")
        assert isinstance(content, str)
        assert len(content) > 0


# ===========================================================================
# Section 4: YAML Frontmatter Structure Invariants
# ===========================================================================


class TestYamlFrontmatterInvariants:
    """Verify every *_MD_CONTENT string starts with valid YAML frontmatter.

    Invariant: Starts with '---\\n', contains 'name:', 'model:', 'tools:',
    and has a second '---\\n' to close the frontmatter.
    """

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_starts_with_yaml_delimiter(self, const_name):
        content = _get_md_content(const_name)
        assert content.startswith("---\n"), (
            f"{const_name} must start with '---\\n'"
        )

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_has_closing_yaml_delimiter(self, const_name):
        content = _get_md_content(const_name)
        # There must be a second "---\n" after the opening one
        idx = content.index("---\n", 4)
        assert idx > 4, (
            f"{const_name} must have a closing '---\\n' frontmatter delimiter"
        )

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_frontmatter_contains_name(self, const_name):
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert "name" in fm, f"{const_name} frontmatter must contain 'name:'"

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_frontmatter_contains_model(self, const_name):
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert "model" in fm, f"{const_name} frontmatter must contain 'model:'"

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_frontmatter_contains_tools(self, const_name):
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert "tools" in fm, f"{const_name} frontmatter must contain 'tools:'"

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_body_after_frontmatter_is_substantial(self, const_name):
        """Invariant: >100 chars of behavioral instructions after frontmatter."""
        content = _get_md_content(const_name)
        body = _get_body_after_frontmatter(content)
        assert len(body.strip()) > 100, (
            f"{const_name} must have >100 chars of instructions after "
            f"frontmatter, got {len(body.strip())}"
        )


# ===========================================================================
# Section 5: Frontmatter Values Match Constants
# ===========================================================================


class TestFrontmatterMatchesConstants:
    """Verify the YAML frontmatter in each *_MD_CONTENT matches its
    corresponding *_FRONTMATTER dict.
    """

    def test_setup_agent_frontmatter_matches(self):
        content = _get_md_content("SETUP_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["name"] == SETUP_AGENT_FRONTMATTER["name"]
        assert fm["model"] == SETUP_AGENT_FRONTMATTER["model"]
        assert fm["tools"] == SETUP_AGENT_FRONTMATTER["tools"]

    def test_stakeholder_dialog_frontmatter_matches(self):
        content = _get_md_content("STAKEHOLDER_DIALOG_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["name"] == STAKEHOLDER_DIALOG_AGENT_FRONTMATTER["name"]
        assert fm["model"] == STAKEHOLDER_DIALOG_AGENT_FRONTMATTER["model"]
        assert fm["tools"] == STAKEHOLDER_DIALOG_AGENT_FRONTMATTER["tools"]

    def test_blueprint_author_frontmatter_matches(self):
        content = _get_md_content("BLUEPRINT_AUTHOR_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["name"] == BLUEPRINT_AUTHOR_AGENT_FRONTMATTER["name"]
        assert fm["model"] == BLUEPRINT_AUTHOR_AGENT_FRONTMATTER["model"]
        assert fm["tools"] == BLUEPRINT_AUTHOR_AGENT_FRONTMATTER["tools"]


# ===========================================================================
# Section 6: Behavioral Contracts -- Setup Agent
# ===========================================================================


class TestSetupAgentBehavioralContracts:
    """Verify Setup Agent MD content describes the required behaviors."""

    @pytest.fixture
    def content(self):
        return _get_md_content("SETUP_AGENT_MD_CONTENT")

    @pytest.fixture
    def body(self, content):
        return _get_body_after_frontmatter(content)

    def test_describes_project_context_creation(self, body):
        """Setup Agent must describe project_context.md creation dialog."""
        body_lower = body.lower()
        assert "project_context" in body_lower, (
            "Setup Agent must mention project_context in its instructions"
        )

    def test_describes_socratic_dialog_or_rewriting(self, body):
        """Setup Agent actively rewrites human input into well-structured,
        LLM-optimized context."""
        body_lower = body.lower()
        # Should mention rewriting or restructuring input
        assert ("rewrite" in body_lower or "restructur" in body_lower
                or "well-structured" in body_lower or "optimiz" in body_lower
                or "socratic" in body_lower), (
            "Setup Agent must describe active rewriting/optimization of input"
        )

    def test_describes_quality_gate(self, body):
        """Setup Agent enforces quality gate -- refuses to advance if
        content is insufficient."""
        body_lower = body.lower()
        assert ("quality" in body_lower or "sufficient" in body_lower
                or "refuse" in body_lower or "gate" in body_lower
                or "reject" in body_lower), (
            "Setup Agent must describe its quality gate / refusal mechanism"
        )

    def test_terminal_status_project_context_complete(self, body):
        """Setup Agent must mention PROJECT_CONTEXT_COMPLETE status line."""
        assert "PROJECT_CONTEXT_COMPLETE" in body

    def test_terminal_status_project_context_rejected(self, body):
        """Setup Agent must mention PROJECT_CONTEXT_REJECTED status line."""
        assert "PROJECT_CONTEXT_REJECTED" in body

    def test_uses_sonnet_model(self, content):
        """Setup Agent uses claude-sonnet-4-6."""
        fm = _parse_frontmatter(content)
        assert fm["model"] == "claude-sonnet-4-6"


# ===========================================================================
# Section 7: Behavioral Contracts -- Stakeholder Dialog Agent
# ===========================================================================


class TestStakeholderDialogBehavioralContracts:
    """Verify Stakeholder Dialog Agent MD content describes required behaviors."""

    @pytest.fixture
    def content(self):
        return _get_md_content("STAKEHOLDER_DIALOG_AGENT_MD_CONTENT")

    @pytest.fixture
    def body(self, content):
        return _get_body_after_frontmatter(content)

    def test_describes_socratic_dialog(self, body):
        """Stakeholder Dialog Agent conducts Socratic dialog."""
        body_lower = body.lower()
        assert "socratic" in body_lower or "dialog" in body_lower, (
            "Stakeholder Dialog Agent must describe Socratic dialog"
        )

    def test_describes_stakeholder_spec(self, body):
        """Stakeholder Dialog Agent produces the stakeholder spec."""
        body_lower = body.lower()
        assert "stakeholder" in body_lower or "spec" in body_lower, (
            "Stakeholder Dialog Agent must mention stakeholder spec"
        )

    def test_describes_one_question_at_a_time(self, body):
        """Asks one question at a time."""
        body_lower = body.lower()
        assert "one question" in body_lower or "single question" in body_lower, (
            "Stakeholder Dialog Agent must enforce one-question-at-a-time"
        )

    def test_describes_consensus(self, body):
        """Seeks consensus per topic."""
        body_lower = body.lower()
        assert ("consensus" in body_lower or "confirm" in body_lower
                or "agree" in body_lower), (
            "Stakeholder Dialog Agent must describe consensus-seeking"
        )

    def test_describes_contradictions_and_edge_cases(self, body):
        """Surfaces contradictions and edge cases."""
        body_lower = body.lower()
        assert ("contradiction" in body_lower or "edge case" in body_lower
                or "inconsisten" in body_lower), (
            "Stakeholder Dialog Agent must mention contradictions/edge cases"
        )

    def test_describes_reference_summaries(self, body):
        """Draws on reference summaries."""
        body_lower = body.lower()
        assert "reference" in body_lower, (
            "Stakeholder Dialog Agent must mention reference summaries"
        )

    def test_describes_revision_mode(self, body):
        """Operates in revision mode for targeted corrections."""
        body_lower = body.lower()
        assert "revision" in body_lower, (
            "Stakeholder Dialog Agent must describe revision mode"
        )

    def test_terminal_status_spec_draft_complete(self, body):
        assert "SPEC_DRAFT_COMPLETE" in body

    def test_terminal_status_spec_revision_complete(self, body):
        assert "SPEC_REVISION_COMPLETE" in body

    def test_uses_opus_model(self, content):
        """Stakeholder Dialog Agent uses claude-opus-4-6."""
        fm = _parse_frontmatter(content)
        assert fm["model"] == "claude-opus-4-6"


# ===========================================================================
# Section 8: Behavioral Contracts -- Blueprint Author Agent
# ===========================================================================


class TestBlueprintAuthorBehavioralContracts:
    """Verify Blueprint Author Agent MD content describes required behaviors."""

    @pytest.fixture
    def content(self):
        return _get_md_content("BLUEPRINT_AUTHOR_AGENT_MD_CONTENT")

    @pytest.fixture
    def body(self, content):
        return _get_body_after_frontmatter(content)

    def test_describes_decomposition_dialog(self, body):
        """Conducts decomposition dialog with domain expert."""
        body_lower = body.lower()
        assert "decomposition" in body_lower, (
            "Blueprint Author Agent must describe decomposition dialog"
        )

    def test_describes_domain_questions(self, body):
        """Asks domain-level questions about phases, data flow, boundaries."""
        body_lower = body.lower()
        # Should mention at least some of: phases, data flow, boundaries
        has_phases = "phase" in body_lower
        has_data_flow = "data flow" in body_lower or "dataflow" in body_lower
        has_boundaries = "boundar" in body_lower
        assert has_phases or has_data_flow or has_boundaries, (
            "Blueprint Author must mention phases, data flow, or boundaries"
        )

    def test_describes_spec_ambiguity_handling(self, body):
        """Distinguishes clarification (working note) from contradiction
        (targeted spec revision) when a spec ambiguity is found."""
        body_lower = body.lower()
        assert ("clarification" in body_lower or "working note" in body_lower
                or "ambigui" in body_lower), (
            "Blueprint Author must describe spec ambiguity handling"
        )

    def test_describes_three_tier_format(self, body):
        """Produces units in the three-tier format."""
        body_lower = body.lower()
        assert ("three-tier" in body_lower or "three tier" in body_lower
                or "tier 1" in body_lower or "tier 2" in body_lower
                or "tier 3" in body_lower), (
            "Blueprint Author must describe three-tier unit format"
        )

    def test_describes_structured_response_format(self, body):
        """Uses the structured response format with [QUESTION], [DECISION],
        [CONFIRMED] closing lines."""
        assert "[QUESTION]" in body, (
            "Blueprint Author must mention [QUESTION] closing line"
        )
        assert "[DECISION]" in body, (
            "Blueprint Author must mention [DECISION] closing line"
        )
        assert "[CONFIRMED]" in body, (
            "Blueprint Author must mention [CONFIRMED] closing line"
        )

    def test_describes_hint_evaluation(self, body):
        """Evaluates human domain hints -- decomposition-level hints carry
        additional weight."""
        body_lower = body.lower()
        assert "hint" in body_lower, (
            "Blueprint Author must describe hint evaluation"
        )

    def test_describes_hint_blueprint_conflict(self, body):
        """If a hint contradicts a blueprint contract, returns
        HINT_BLUEPRINT_CONFLICT: [details]."""
        assert "HINT_BLUEPRINT_CONFLICT" in body, (
            "Blueprint Author must mention HINT_BLUEPRINT_CONFLICT status"
        )

    def test_terminal_status_blueprint_draft_complete(self, body):
        assert "BLUEPRINT_DRAFT_COMPLETE" in body

    def test_uses_opus_model(self, content):
        """Blueprint Author Agent uses claude-opus-4-6."""
        fm = _parse_frontmatter(content)
        assert fm["model"] == "claude-opus-4-6"


# ===========================================================================
# Section 9: Cross-Cutting Behavioral Contracts (All Agents)
# ===========================================================================


class TestAllAgentsCommonContracts:
    """Verify behavioral contracts that apply to all three agents."""

    @pytest.mark.parametrize("const_name,status_list", [
        ("SETUP_AGENT_MD_CONTENT", SETUP_AGENT_STATUS),
        ("STAKEHOLDER_DIALOG_AGENT_MD_CONTENT", STAKEHOLDER_DIALOG_STATUS),
        ("BLUEPRINT_AUTHOR_AGENT_MD_CONTENT", BLUEPRINT_AUTHOR_STATUS),
    ])
    def test_all_terminal_status_lines_mentioned(self, const_name, status_list):
        """Each agent's body must mention all its terminal status lines."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        for status in status_list:
            assert status in body, (
                f"{const_name} must mention terminal status line '{status}'"
            )

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_describes_structured_response_format(self, const_name):
        """All dialog agents must enforce the structured response format.
        Invariant: every response must end with one of [QUESTION], [DECISION],
        [CONFIRMED]."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        # At minimum, the structured response format tokens should appear
        has_question = "[QUESTION]" in body
        has_decision = "[DECISION]" in body
        has_confirmed = "[CONFIRMED]" in body
        assert has_question or has_decision or has_confirmed, (
            f"{const_name} must mention at least one structured response "
            "format token ([QUESTION], [DECISION], or [CONFIRMED])"
        )

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_describes_terminal_status_line_concept(self, const_name):
        """All agents must describe their terminal status line mechanism."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        body_lower = body.lower()
        assert ("terminal status" in body_lower or "status line" in body_lower
                or "terminal line" in body_lower), (
            f"{const_name} must describe the terminal status line concept"
        )

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_describes_file_scope_constraint(self, const_name):
        """All agents must include constraint against modifying files outside
        their scope."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        body_lower = body.lower()
        assert ("scope" in body_lower or "outside" in body_lower
                or "modif" in body_lower or "authorized" in body_lower
                or "restrict" in body_lower), (
            f"{const_name} must describe the file scope constraint"
        )

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_describes_purpose(self, const_name):
        """All agents must describe their purpose."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        # Purpose is guaranteed to be substantial (>100 chars), but we also
        # check it's not just whitespace or boilerplate
        stripped = body.strip()
        assert len(stripped) > 100, (
            f"{const_name} body must be >100 chars (got {len(stripped)})"
        )

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_is_valid_yaml_frontmatter(self, const_name):
        """Frontmatter YAML must be parseable without errors."""
        content = _get_md_content(const_name)
        # This will raise if the YAML is invalid
        fm = _parse_frontmatter(content)
        assert isinstance(fm, dict), (
            f"{const_name} frontmatter must parse as a dict"
        )


# ===========================================================================
# Section 10: Invariant -- Blueprint Author Three-Tier Format
# ===========================================================================


class TestBlueprintAuthorThreeTierInvariant:
    """Blueprint Author must produce units in the three-tier format.
    Tier 2 heading must be exactly: '### Tier 2 \\u2014 Signatures' (em-dash).

    We verify that the agent instructions mention this exact format.
    """

    def test_mentions_em_dash_tier_heading(self):
        """The agent definition must mention the em-dash format for Tier 2."""
        body = _get_body_after_frontmatter(
            _get_md_content("BLUEPRINT_AUTHOR_AGENT_MD_CONTENT")
        )
        # The em-dash character \u2014
        assert "\u2014" in body, (
            "Blueprint Author instructions must include the em-dash character "
            "(\\u2014) for the Tier 2 heading format"
        )


# ===========================================================================
# Section 11: Agent Definition Completeness
# ===========================================================================


class TestAgentDefinitionCompleteness:
    """Verify each *_MD_CONTENT is a complete agent definition, not a
    placeholder or skeleton."""

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_not_a_placeholder(self, const_name):
        """Content must not be a placeholder -- it should have multiple
        paragraphs or sections of substantive text."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        # A real agent definition should be hundreds of characters
        # DATA ASSUMPTION: A non-skeleton agent definition is at least 500 chars
        assert len(body.strip()) >= 500, (
            f"{const_name} appears to be a skeleton/placeholder "
            f"({len(body.strip())} chars). Expected >= 500 chars of "
            "substantive instructions."
        )

    @pytest.mark.parametrize("const_name", [
        "SETUP_AGENT_MD_CONTENT",
        "STAKEHOLDER_DIALOG_AGENT_MD_CONTENT",
        "BLUEPRINT_AUTHOR_AGENT_MD_CONTENT",
    ])
    def test_has_multiple_sections_or_paragraphs(self, const_name):
        """A complete agent definition should have multiple paragraphs."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        # Count non-empty lines as a proxy for content density
        non_empty_lines = [
            line for line in body.split("\n") if line.strip()
        ]
        # DATA ASSUMPTION: A complete agent definition has at least 10
        # non-empty lines of instructions
        assert len(non_empty_lines) >= 10, (
            f"{const_name} has only {len(non_empty_lines)} non-empty lines. "
            "Expected >= 10 for a complete agent definition."
        )

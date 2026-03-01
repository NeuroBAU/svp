"""
Tests for Unit 14: Review and Checker Agent Definitions.

Validates the YAML frontmatter dictionaries, terminal status line lists,
and the three *_MD_CONTENT agent definition strings for the Stakeholder Spec
Reviewer, Blueprint Checker, and Blueprint Reviewer agents.

DATA ASSUMPTIONS
================

DATA ASSUMPTION: YAML frontmatter in each *_MD_CONTENT string uses the
standard "---" delimiter on separate lines, with key: value pairs between
them. This is the Claude Code agent definition format.

DATA ASSUMPTION: The frontmatter dictionaries defined in Tier 2 signatures
exactly match the keys/values specified in the blueprint. These are the
canonical agent metadata attributes.

DATA ASSUMPTION: These are single-shot agents (not dialog agents). They
receive documents, produce a critique or verdict, and terminate. They do
NOT use the conversation ledger or structured response format
([QUESTION], [DECISION], [CONFIRMED]).

DATA ASSUMPTION: "Substantial behavioral instructions" means >100 characters
after the second YAML frontmatter delimiter, per the Tier 2 invariant.

DATA ASSUMPTION: Stakeholder Reviewer and Blueprint Reviewer use tools
[Read, Glob, Grep] while Blueprint Checker additionally has Bash for
running ast.parse() to validate Python signatures.

DATA ASSUMPTION: All three agents use claude-opus-4-6 per the blueprint.

DATA ASSUMPTION: Terminal status lines are exact string matches used by the
main session routing script. No variations or prefixes are allowed.

DATA ASSUMPTION: Blueprint Checker has three possible outcomes reflecting
where the fault lies: ALIGNMENT_CONFIRMED (no fault), ALIGNMENT_FAILED: spec
(spec is the problem), ALIGNMENT_FAILED: blueprint (blueprint is the problem).

DATA ASSUMPTION: A non-skeleton agent definition is at least 500 chars and
has at least 10 non-empty lines of substantive instructions.

DATA ASSUMPTION: The "report most fundamental level" principle means Blueprint
Checker, when finding multiple issues, reports only the most fundamental one
(spec supersedes blueprint).
"""

import pytest
from typing import Any, Dict, List

# Import the unit under test from the stub module
from svp.scripts.review_checker_agent_definitions import (
    STAKEHOLDER_REVIEWER_FRONTMATTER,
    BLUEPRINT_CHECKER_FRONTMATTER,
    BLUEPRINT_REVIEWER_FRONTMATTER,
    STAKEHOLDER_REVIEWER_STATUS,
    BLUEPRINT_CHECKER_STATUS,
    BLUEPRINT_REVIEWER_STATUS,
)


# ---------------------------------------------------------------------------
# Helper: safely import *_MD_CONTENT constants that are type-only in the stub
# ---------------------------------------------------------------------------

def _get_md_content(name: str) -> str:
    """Import an MD_CONTENT constant from the stub module.

    The stub declares these as type annotations without values, so import
    will fail on the stub (red run) and succeed on the implementation.
    """
    import svp.scripts.review_checker_agent_definitions as mod
    value = getattr(mod, name)
    assert isinstance(value, str), (
        f"{name} must be a str, got {type(value).__name__}"
    )
    return value


def _parse_frontmatter(md_content: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from a Markdown string (no pyyaml dependency)."""
    assert md_content.startswith("---\n")
    second_delim = md_content.index("---\n", 4)
    yaml_block = md_content[4:second_delim]
    result: Dict[str, Any] = {}
    current_key = None
    current_list: list = []
    for line in yaml_block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith("  - ") or line.startswith("\t- "):
            current_list.append(stripped[2:].strip().strip("\"'"))
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
                result[key] = [i.strip().strip("\"'") for i in inner.split(",") if i.strip()]
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
# Section 1: Frontmatter Dictionary Constants
# ===========================================================================


class TestFrontmatterConstants:
    """Verify the YAML frontmatter dictionaries match the blueprint."""

    # -- Stakeholder Reviewer --

    def test_stakeholder_reviewer_frontmatter_is_dict(self):
        assert isinstance(STAKEHOLDER_REVIEWER_FRONTMATTER, dict)

    def test_stakeholder_reviewer_frontmatter_name(self):
        assert STAKEHOLDER_REVIEWER_FRONTMATTER["name"] == "stakeholder_reviewer"

    def test_stakeholder_reviewer_frontmatter_description(self):
        assert STAKEHOLDER_REVIEWER_FRONTMATTER["description"] == (
            "Reviews stakeholder spec cold, produces structured critique"
        )

    def test_stakeholder_reviewer_frontmatter_model(self):
        # DATA ASSUMPTION: All review/checker agents use claude-opus-4-6 per blueprint
        assert STAKEHOLDER_REVIEWER_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_stakeholder_reviewer_frontmatter_tools(self):
        # DATA ASSUMPTION: Stakeholder Reviewer uses Read, Glob, Grep (no Bash)
        assert STAKEHOLDER_REVIEWER_FRONTMATTER["tools"] == [
            "Read", "Glob", "Grep"
        ]

    # -- Blueprint Checker --

    def test_blueprint_checker_frontmatter_is_dict(self):
        assert isinstance(BLUEPRINT_CHECKER_FRONTMATTER, dict)

    def test_blueprint_checker_frontmatter_name(self):
        assert BLUEPRINT_CHECKER_FRONTMATTER["name"] == "blueprint_checker"

    def test_blueprint_checker_frontmatter_description(self):
        assert BLUEPRINT_CHECKER_FRONTMATTER["description"] == (
            "Verifies blueprint alignment with stakeholder spec"
        )

    def test_blueprint_checker_frontmatter_model(self):
        assert BLUEPRINT_CHECKER_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_blueprint_checker_frontmatter_tools(self):
        # DATA ASSUMPTION: Blueprint Checker additionally has Bash for running
        # ast.parse() to validate Python signatures
        assert BLUEPRINT_CHECKER_FRONTMATTER["tools"] == [
            "Read", "Glob", "Grep", "Bash"
        ]

    # -- Blueprint Reviewer --

    def test_blueprint_reviewer_frontmatter_is_dict(self):
        assert isinstance(BLUEPRINT_REVIEWER_FRONTMATTER, dict)

    def test_blueprint_reviewer_frontmatter_name(self):
        assert BLUEPRINT_REVIEWER_FRONTMATTER["name"] == "blueprint_reviewer"

    def test_blueprint_reviewer_frontmatter_description(self):
        assert BLUEPRINT_REVIEWER_FRONTMATTER["description"] == (
            "Reviews blueprint cold, produces structured critique"
        )

    def test_blueprint_reviewer_frontmatter_model(self):
        assert BLUEPRINT_REVIEWER_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_blueprint_reviewer_frontmatter_tools(self):
        # DATA ASSUMPTION: Blueprint Reviewer uses Read, Glob, Grep (no Bash)
        assert BLUEPRINT_REVIEWER_FRONTMATTER["tools"] == [
            "Read", "Glob", "Grep"
        ]

    # -- Cross-cutting frontmatter checks --

    def test_all_frontmatter_have_required_keys(self):
        """Every frontmatter dict must have name, description, model, tools."""
        required_keys = {"name", "description", "model", "tools"}
        for label, fm in [
            ("STAKEHOLDER_REVIEWER", STAKEHOLDER_REVIEWER_FRONTMATTER),
            ("BLUEPRINT_CHECKER", BLUEPRINT_CHECKER_FRONTMATTER),
            ("BLUEPRINT_REVIEWER", BLUEPRINT_REVIEWER_FRONTMATTER),
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

    def test_stakeholder_reviewer_status_is_list(self):
        assert isinstance(STAKEHOLDER_REVIEWER_STATUS, list)

    def test_stakeholder_reviewer_status_values(self):
        assert STAKEHOLDER_REVIEWER_STATUS == ["REVIEW_COMPLETE"]

    def test_blueprint_checker_status_is_list(self):
        assert isinstance(BLUEPRINT_CHECKER_STATUS, list)

    def test_blueprint_checker_status_values(self):
        # DATA ASSUMPTION: Three outcomes reflecting where fault lies
        assert BLUEPRINT_CHECKER_STATUS == [
            "ALIGNMENT_CONFIRMED",
            "ALIGNMENT_FAILED: spec",
            "ALIGNMENT_FAILED: blueprint",
        ]

    def test_blueprint_reviewer_status_is_list(self):
        assert isinstance(BLUEPRINT_REVIEWER_STATUS, list)

    def test_blueprint_reviewer_status_values(self):
        assert BLUEPRINT_REVIEWER_STATUS == ["REVIEW_COMPLETE"]

    def test_blueprint_checker_has_three_outcomes(self):
        """Blueprint Checker must have exactly three possible outcomes."""
        assert len(BLUEPRINT_CHECKER_STATUS) == 3

    def test_stakeholder_and_blueprint_reviewer_share_status(self):
        """Both reviewers use REVIEW_COMPLETE as their only terminal status."""
        assert STAKEHOLDER_REVIEWER_STATUS == BLUEPRINT_REVIEWER_STATUS


# ===========================================================================
# Section 3: MD_CONTENT String Existence and Type
# ===========================================================================


class TestMdContentExistence:
    """Verify that *_MD_CONTENT constants exist and are non-empty strings.

    These tests will fail on the stub (red run) because the stub only
    declares type annotations without assigning values.
    """

    def test_stakeholder_reviewer_md_content_is_string(self):
        content = _get_md_content("STAKEHOLDER_REVIEWER_MD_CONTENT")
        assert isinstance(content, str)
        assert len(content) > 0, "STAKEHOLDER_REVIEWER_MD_CONTENT must not be empty"

    def test_blueprint_checker_md_content_is_string(self):
        content = _get_md_content("BLUEPRINT_CHECKER_MD_CONTENT")
        assert isinstance(content, str)
        assert len(content) > 0, "BLUEPRINT_CHECKER_MD_CONTENT must not be empty"

    def test_blueprint_reviewer_md_content_is_string(self):
        content = _get_md_content("BLUEPRINT_REVIEWER_MD_CONTENT")
        assert isinstance(content, str)
        assert len(content) > 0, "BLUEPRINT_REVIEWER_MD_CONTENT must not be empty"


# ===========================================================================
# Section 4: YAML Frontmatter Structure Invariants
# ===========================================================================


class TestYamlFrontmatterInvariants:
    """Verify every *_MD_CONTENT string starts with valid YAML frontmatter.

    Invariant: Starts with '---\\n', contains 'name:', 'model:', 'tools:',
    and has a second '---\\n' to close the frontmatter.
    """

    ALL_MD_CONTENT_NAMES = [
        "STAKEHOLDER_REVIEWER_MD_CONTENT",
        "BLUEPRINT_CHECKER_MD_CONTENT",
        "BLUEPRINT_REVIEWER_MD_CONTENT",
    ]

    @pytest.mark.parametrize("const_name", ALL_MD_CONTENT_NAMES)
    def test_starts_with_yaml_delimiter(self, const_name):
        content = _get_md_content(const_name)
        assert content.startswith("---\n"), (
            f"{const_name} must start with '---\\n'"
        )

    @pytest.mark.parametrize("const_name", ALL_MD_CONTENT_NAMES)
    def test_has_closing_yaml_delimiter(self, const_name):
        content = _get_md_content(const_name)
        # There must be a second "---\n" after the opening one
        idx = content.index("---\n", 4)
        assert idx > 4, (
            f"{const_name} must have a closing '---\\n' frontmatter delimiter"
        )

    @pytest.mark.parametrize("const_name", ALL_MD_CONTENT_NAMES)
    def test_frontmatter_contains_name(self, const_name):
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert "name" in fm, f"{const_name} frontmatter must contain 'name:'"

    @pytest.mark.parametrize("const_name", ALL_MD_CONTENT_NAMES)
    def test_frontmatter_contains_model(self, const_name):
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert "model" in fm, f"{const_name} frontmatter must contain 'model:'"

    @pytest.mark.parametrize("const_name", ALL_MD_CONTENT_NAMES)
    def test_frontmatter_contains_tools(self, const_name):
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert "tools" in fm, f"{const_name} frontmatter must contain 'tools:'"

    @pytest.mark.parametrize("const_name", ALL_MD_CONTENT_NAMES)
    def test_body_after_frontmatter_is_substantial(self, const_name):
        """Invariant: >100 chars of behavioral instructions after frontmatter."""
        content = _get_md_content(const_name)
        body = _get_body_after_frontmatter(content)
        assert len(body.strip()) > 100, (
            f"{const_name} must have >100 chars of instructions after "
            f"frontmatter, got {len(body.strip())}"
        )

    @pytest.mark.parametrize("const_name", ALL_MD_CONTENT_NAMES)
    def test_is_valid_yaml_frontmatter(self, const_name):
        """Frontmatter YAML must be parseable without errors."""
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert isinstance(fm, dict), (
            f"{const_name} frontmatter must parse as a dict"
        )


# ===========================================================================
# Section 5: Frontmatter Values Match Constants
# ===========================================================================


class TestFrontmatterMatchesConstants:
    """Verify the YAML frontmatter in each *_MD_CONTENT matches its
    corresponding *_FRONTMATTER dict.
    """

    def test_stakeholder_reviewer_frontmatter_name_matches(self):
        content = _get_md_content("STAKEHOLDER_REVIEWER_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["name"] == STAKEHOLDER_REVIEWER_FRONTMATTER["name"]

    def test_stakeholder_reviewer_frontmatter_model_matches(self):
        content = _get_md_content("STAKEHOLDER_REVIEWER_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["model"] == STAKEHOLDER_REVIEWER_FRONTMATTER["model"]

    def test_stakeholder_reviewer_frontmatter_tools_matches(self):
        content = _get_md_content("STAKEHOLDER_REVIEWER_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["tools"] == STAKEHOLDER_REVIEWER_FRONTMATTER["tools"]

    def test_stakeholder_reviewer_frontmatter_description_matches(self):
        content = _get_md_content("STAKEHOLDER_REVIEWER_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert "description" in fm, (
            "STAKEHOLDER_REVIEWER_MD_CONTENT frontmatter must contain 'description:'"
        )
        assert fm["description"] == STAKEHOLDER_REVIEWER_FRONTMATTER["description"]

    def test_blueprint_checker_frontmatter_name_matches(self):
        content = _get_md_content("BLUEPRINT_CHECKER_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["name"] == BLUEPRINT_CHECKER_FRONTMATTER["name"]

    def test_blueprint_checker_frontmatter_model_matches(self):
        content = _get_md_content("BLUEPRINT_CHECKER_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["model"] == BLUEPRINT_CHECKER_FRONTMATTER["model"]

    def test_blueprint_checker_frontmatter_tools_matches(self):
        content = _get_md_content("BLUEPRINT_CHECKER_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["tools"] == BLUEPRINT_CHECKER_FRONTMATTER["tools"]

    def test_blueprint_checker_frontmatter_description_matches(self):
        content = _get_md_content("BLUEPRINT_CHECKER_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert "description" in fm, (
            "BLUEPRINT_CHECKER_MD_CONTENT frontmatter must contain 'description:'"
        )
        assert fm["description"] == BLUEPRINT_CHECKER_FRONTMATTER["description"]

    def test_blueprint_reviewer_frontmatter_name_matches(self):
        content = _get_md_content("BLUEPRINT_REVIEWER_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["name"] == BLUEPRINT_REVIEWER_FRONTMATTER["name"]

    def test_blueprint_reviewer_frontmatter_model_matches(self):
        content = _get_md_content("BLUEPRINT_REVIEWER_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["model"] == BLUEPRINT_REVIEWER_FRONTMATTER["model"]

    def test_blueprint_reviewer_frontmatter_tools_matches(self):
        content = _get_md_content("BLUEPRINT_REVIEWER_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["tools"] == BLUEPRINT_REVIEWER_FRONTMATTER["tools"]

    def test_blueprint_reviewer_frontmatter_description_matches(self):
        content = _get_md_content("BLUEPRINT_REVIEWER_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert "description" in fm, (
            "BLUEPRINT_REVIEWER_MD_CONTENT frontmatter must contain 'description:'"
        )
        assert fm["description"] == BLUEPRINT_REVIEWER_FRONTMATTER["description"]


# ===========================================================================
# Section 6: Behavioral Contracts -- Stakeholder Spec Reviewer
# ===========================================================================


class TestStakeholderReviewerBehavioralContracts:
    """Verify Stakeholder Spec Reviewer MD content describes the required behaviors.

    Blueprint contract: Receives only the stakeholder spec, project context, and
    reference summaries -- no dialog ledger. Reads the document cold. Produces a
    structured critique identifying gaps, contradictions, underspecified areas,
    and missing edge cases. Terminal status: REVIEW_COMPLETE. Uses claude-opus-4-6.
    """

    @pytest.fixture
    def content(self):
        return _get_md_content("STAKEHOLDER_REVIEWER_MD_CONTENT")

    @pytest.fixture
    def body(self, content):
        return _get_body_after_frontmatter(content)

    def test_describes_cold_reading(self, body):
        """Stakeholder Reviewer reads the document cold (no prior dialog context)."""
        body_lower = body.lower()
        assert ("cold" in body_lower or "fresh" in body_lower
                or "no prior" in body_lower or "no dialog" in body_lower
                or "without" in body_lower), (
            "Stakeholder Reviewer must describe cold reading (no prior context)"
        )

    def test_describes_structured_critique(self, body):
        """Produces a structured critique."""
        body_lower = body.lower()
        assert ("critique" in body_lower or "structured" in body_lower
                or "review" in body_lower), (
            "Stakeholder Reviewer must describe producing a structured critique"
        )

    def test_describes_identifying_gaps(self, body):
        """Identifies gaps in the stakeholder spec."""
        body_lower = body.lower()
        assert "gap" in body_lower, (
            "Stakeholder Reviewer must mention identifying gaps"
        )

    def test_describes_identifying_contradictions(self, body):
        """Identifies contradictions in the stakeholder spec."""
        body_lower = body.lower()
        assert "contradiction" in body_lower, (
            "Stakeholder Reviewer must mention identifying contradictions"
        )

    def test_describes_identifying_underspecified_areas(self, body):
        """Identifies underspecified areas."""
        body_lower = body.lower()
        assert ("underspecified" in body_lower or "under-specified" in body_lower
                or "vague" in body_lower or "ambiguous" in body_lower
                or "unclear" in body_lower or "incomplete" in body_lower), (
            "Stakeholder Reviewer must mention identifying underspecified areas"
        )

    def test_describes_identifying_missing_edge_cases(self, body):
        """Identifies missing edge cases."""
        body_lower = body.lower()
        assert "edge case" in body_lower or "edge-case" in body_lower, (
            "Stakeholder Reviewer must mention identifying missing edge cases"
        )

    def test_no_dialog_ledger(self, body):
        """Stakeholder Reviewer does NOT use a dialog ledger.
        It is a single-shot agent, not a dialog agent."""
        body_lower = body.lower()
        # The agent should NOT mention operating on a ledger
        # (or if mentioned, should clarify it does NOT receive one)
        # We verify it does not describe a ledger-based interaction pattern
        has_no_ledger = ("no ledger" in body_lower or "no dialog" in body_lower
                         or "without" in body_lower or "single" in body_lower
                         or "cold" in body_lower)
        assert has_no_ledger, (
            "Stakeholder Reviewer must indicate it operates without a dialog ledger "
            "(single-shot agent)"
        )

    def test_terminal_status_review_complete(self, body):
        """Terminal status: REVIEW_COMPLETE."""
        assert "REVIEW_COMPLETE" in body

    def test_uses_opus_model(self, content):
        """Stakeholder Reviewer uses claude-opus-4-6."""
        fm = _parse_frontmatter(content)
        assert fm["model"] == "claude-opus-4-6"

    def test_receives_stakeholder_spec(self, body):
        """Must describe receiving the stakeholder spec as input."""
        body_lower = body.lower()
        assert ("stakeholder" in body_lower and "spec" in body_lower), (
            "Stakeholder Reviewer must mention receiving the stakeholder spec"
        )

    def test_receives_reference_summaries(self, body):
        """Must describe receiving reference summaries as input."""
        body_lower = body.lower()
        assert "reference" in body_lower, (
            "Stakeholder Reviewer must mention receiving reference summaries"
        )


# ===========================================================================
# Section 7: Behavioral Contracts -- Blueprint Checker
# ===========================================================================


class TestBlueprintCheckerBehavioralContracts:
    """Verify Blueprint Checker MD content describes the required behaviors.

    Blueprint contract: Receives stakeholder spec (with working notes), blueprint,
    and reference summaries. Verifies alignment. Validates structural requirements:
    signatures parseable via ast, all types have imports, per-unit context budget
    within threshold (65% default), working note consistency. Reports only the most
    fundamental level when multiple issues found (spec supersedes blueprint).
    Produces dual-format output (prose + structured block). Three outcomes:
    ALIGNMENT_CONFIRMED, ALIGNMENT_FAILED: spec, ALIGNMENT_FAILED: blueprint.
    Uses claude-opus-4-6. The Bash tool is included so the checker can validate
    Python signatures by running ast.parse().
    """

    @pytest.fixture
    def content(self):
        return _get_md_content("BLUEPRINT_CHECKER_MD_CONTENT")

    @pytest.fixture
    def body(self, content):
        return _get_body_after_frontmatter(content)

    def test_describes_alignment_verification(self, body):
        """Verifies alignment between blueprint and stakeholder spec."""
        body_lower = body.lower()
        assert "alignment" in body_lower or "align" in body_lower, (
            "Blueprint Checker must describe verifying alignment"
        )

    def test_describes_ast_validation(self, body):
        """Validates signatures are parseable via ast."""
        body_lower = body.lower()
        assert "ast" in body_lower, (
            "Blueprint Checker must mention ast (Python abstract syntax tree) "
            "for signature validation"
        )

    def test_describes_ast_parse(self, body):
        """Specifically mentions ast.parse() for validating Python signatures."""
        assert "ast.parse" in body or "ast module" in body.lower(), (
            "Blueprint Checker must mention ast.parse() for signature validation"
        )

    def test_describes_type_import_validation(self, body):
        """All referenced types must have corresponding import statements."""
        body_lower = body.lower()
        assert ("import" in body_lower and "type" in body_lower), (
            "Blueprint Checker must describe validating that all referenced "
            "types have corresponding import statements"
        )

    def test_describes_context_budget_validation(self, body):
        """Per-unit context budget must be within threshold."""
        body_lower = body.lower()
        assert ("context budget" in body_lower or "context" in body_lower
                and "budget" in body_lower), (
            "Blueprint Checker must describe context budget validation"
        )

    def test_describes_context_budget_threshold(self, body):
        """Context budget threshold is 65% by default."""
        assert "65" in body, (
            "Blueprint Checker must mention the 65% default context budget threshold"
        )

    def test_describes_working_note_consistency(self, body):
        """Working notes must be consistent with original spec text."""
        body_lower = body.lower()
        assert "working note" in body_lower, (
            "Blueprint Checker must describe working note consistency validation"
        )

    def test_describes_most_fundamental_level_principle(self, body):
        """Reports only the most fundamental level when multiple issues found."""
        body_lower = body.lower()
        assert ("fundamental" in body_lower or "most fundamental" in body_lower), (
            "Blueprint Checker must describe the 'report most fundamental level' "
            "principle"
        )

    def test_describes_spec_supersedes_blueprint(self, body):
        """Spec supersedes blueprint when reporting issues."""
        body_lower = body.lower()
        assert ("spec" in body_lower and ("supersede" in body_lower
                or "prior" in body_lower or "fundamental" in body_lower
                or "first" in body_lower)), (
            "Blueprint Checker must describe that spec supersedes blueprint "
            "when multiple issues are found"
        )

    def test_describes_dual_format_output(self, body):
        """Produces dual-format output: prose + structured block."""
        body_lower = body.lower()
        assert ("prose" in body_lower or "narrative" in body_lower
                or "dual" in body_lower or "structured" in body_lower), (
            "Blueprint Checker must describe dual-format output "
            "(prose + structured block)"
        )

    def test_terminal_status_alignment_confirmed(self, body):
        """Terminal status: ALIGNMENT_CONFIRMED."""
        assert "ALIGNMENT_CONFIRMED" in body

    def test_terminal_status_alignment_failed_spec(self, body):
        """Terminal status: ALIGNMENT_FAILED: spec."""
        assert "ALIGNMENT_FAILED: spec" in body or "ALIGNMENT_FAILED:spec" in body

    def test_terminal_status_alignment_failed_blueprint(self, body):
        """Terminal status: ALIGNMENT_FAILED: blueprint."""
        assert "ALIGNMENT_FAILED: blueprint" in body or "ALIGNMENT_FAILED:blueprint" in body

    def test_uses_opus_model(self, content):
        """Blueprint Checker uses claude-opus-4-6."""
        fm = _parse_frontmatter(content)
        assert fm["model"] == "claude-opus-4-6"

    def test_has_bash_tool(self, content):
        """Blueprint Checker must have Bash tool for running ast.parse()."""
        fm = _parse_frontmatter(content)
        assert "Bash" in fm["tools"], (
            "Blueprint Checker frontmatter must include Bash tool"
        )

    def test_receives_stakeholder_spec_with_working_notes(self, body):
        """Must describe receiving stakeholder spec with working notes."""
        body_lower = body.lower()
        assert "stakeholder" in body_lower, (
            "Blueprint Checker must mention receiving the stakeholder spec"
        )

    def test_receives_blueprint(self, body):
        """Must describe receiving the blueprint as input."""
        body_lower = body.lower()
        assert "blueprint" in body_lower, (
            "Blueprint Checker must mention receiving the blueprint"
        )

    def test_three_outcomes_documented(self, body):
        """All three possible outcomes must be documented in the body."""
        has_confirmed = "ALIGNMENT_CONFIRMED" in body
        has_failed_spec = "ALIGNMENT_FAILED" in body and "spec" in body
        has_failed_blueprint = "ALIGNMENT_FAILED" in body and "blueprint" in body
        assert has_confirmed and has_failed_spec and has_failed_blueprint, (
            "Blueprint Checker must document all three outcomes"
        )


# ===========================================================================
# Section 8: Behavioral Contracts -- Blueprint Reviewer
# ===========================================================================


class TestBlueprintReviewerBehavioralContracts:
    """Verify Blueprint Reviewer MD content describes the required behaviors.

    Blueprint contract: Receives blueprint, stakeholder spec, project context,
    and reference summaries -- no dialog ledger. Reads documents cold. Produces
    a structured critique. Terminal status: REVIEW_COMPLETE. Uses claude-opus-4-6.
    """

    @pytest.fixture
    def content(self):
        return _get_md_content("BLUEPRINT_REVIEWER_MD_CONTENT")

    @pytest.fixture
    def body(self, content):
        return _get_body_after_frontmatter(content)

    def test_describes_cold_reading(self, body):
        """Blueprint Reviewer reads documents cold (no prior dialog context)."""
        body_lower = body.lower()
        assert ("cold" in body_lower or "fresh" in body_lower
                or "no prior" in body_lower or "no dialog" in body_lower
                or "without" in body_lower), (
            "Blueprint Reviewer must describe cold reading (no prior context)"
        )

    def test_describes_structured_critique(self, body):
        """Produces a structured critique."""
        body_lower = body.lower()
        assert ("critique" in body_lower or "structured" in body_lower
                or "review" in body_lower), (
            "Blueprint Reviewer must describe producing a structured critique"
        )

    def test_receives_blueprint(self, body):
        """Must describe receiving the blueprint as input."""
        body_lower = body.lower()
        assert "blueprint" in body_lower, (
            "Blueprint Reviewer must mention receiving the blueprint"
        )

    def test_receives_stakeholder_spec(self, body):
        """Must describe receiving the stakeholder spec as input."""
        body_lower = body.lower()
        assert "stakeholder" in body_lower or "spec" in body_lower, (
            "Blueprint Reviewer must mention receiving the stakeholder spec"
        )

    def test_receives_reference_summaries(self, body):
        """Must describe receiving reference summaries as input."""
        body_lower = body.lower()
        assert "reference" in body_lower, (
            "Blueprint Reviewer must mention receiving reference summaries"
        )

    def test_no_dialog_ledger(self, body):
        """Blueprint Reviewer does NOT use a dialog ledger.
        It is a single-shot agent, not a dialog agent."""
        body_lower = body.lower()
        has_no_ledger = ("no ledger" in body_lower or "no dialog" in body_lower
                         or "without" in body_lower or "single" in body_lower
                         or "cold" in body_lower)
        assert has_no_ledger, (
            "Blueprint Reviewer must indicate it operates without a dialog "
            "ledger (single-shot agent)"
        )

    def test_terminal_status_review_complete(self, body):
        """Terminal status: REVIEW_COMPLETE."""
        assert "REVIEW_COMPLETE" in body

    def test_uses_opus_model(self, content):
        """Blueprint Reviewer uses claude-opus-4-6."""
        fm = _parse_frontmatter(content)
        assert fm["model"] == "claude-opus-4-6"

    def test_receives_project_context(self, body):
        """Must describe receiving project context as input."""
        body_lower = body.lower()
        assert ("project context" in body_lower or "project_context" in body_lower
                or "context" in body_lower), (
            "Blueprint Reviewer must mention receiving project context"
        )


# ===========================================================================
# Section 9: Cross-Cutting Behavioral Contracts (All Agents)
# ===========================================================================


class TestAllAgentsCommonContracts:
    """Verify behavioral contracts that apply to all three agents."""

    ALL_MD_CONTENT_NAMES = [
        "STAKEHOLDER_REVIEWER_MD_CONTENT",
        "BLUEPRINT_CHECKER_MD_CONTENT",
        "BLUEPRINT_REVIEWER_MD_CONTENT",
    ]

    @pytest.mark.parametrize("const_name,status_list", [
        ("STAKEHOLDER_REVIEWER_MD_CONTENT", STAKEHOLDER_REVIEWER_STATUS),
        ("BLUEPRINT_CHECKER_MD_CONTENT", BLUEPRINT_CHECKER_STATUS),
        ("BLUEPRINT_REVIEWER_MD_CONTENT", BLUEPRINT_REVIEWER_STATUS),
    ])
    def test_all_terminal_status_lines_mentioned(self, const_name, status_list):
        """Each agent's body must mention all its terminal status lines."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        for status in status_list:
            assert status in body, (
                f"{const_name} must mention terminal status line '{status}'"
            )

    @pytest.mark.parametrize("const_name", ALL_MD_CONTENT_NAMES)
    def test_describes_terminal_status_line_concept(self, const_name):
        """All agents must describe their terminal status line mechanism."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        body_lower = body.lower()
        assert ("terminal status" in body_lower or "status line" in body_lower
                or "terminal line" in body_lower), (
            f"{const_name} must describe the terminal status line concept"
        )

    @pytest.mark.parametrize("const_name", ALL_MD_CONTENT_NAMES)
    def test_describes_purpose(self, const_name):
        """All agents must describe their purpose."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        stripped = body.strip()
        assert len(stripped) > 100, (
            f"{const_name} body must be >100 chars (got {len(stripped)})"
        )

    @pytest.mark.parametrize("const_name", ALL_MD_CONTENT_NAMES)
    def test_describes_methodology(self, const_name):
        """Each agent must describe its methodology (how it works)."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        body_lower = body.lower()
        assert ("methodology" in body_lower or "method" in body_lower
                or "step" in body_lower or "process" in body_lower
                or "approach" in body_lower or "procedure" in body_lower), (
            f"{const_name} must describe its methodology"
        )

    @pytest.mark.parametrize("const_name", ALL_MD_CONTENT_NAMES)
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

    @pytest.mark.parametrize("const_name", ALL_MD_CONTENT_NAMES)
    def test_describes_constraints(self, const_name):
        """Each agent must describe its constraints."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        body_lower = body.lower()
        assert ("constraint" in body_lower or "must not" in body_lower
                or "do not" in body_lower or "scope" in body_lower
                or "restrict" in body_lower or "limit" in body_lower), (
            f"{const_name} must describe its constraints"
        )

    @pytest.mark.parametrize("const_name", ALL_MD_CONTENT_NAMES)
    def test_all_agents_use_opus_model(self, const_name):
        """All three review/checker agents use claude-opus-4-6."""
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert fm["model"] == "claude-opus-4-6", (
            f"{const_name} must use claude-opus-4-6"
        )


# ===========================================================================
# Section 10: Agent Definition Completeness
# ===========================================================================


class TestAgentDefinitionCompleteness:
    """Verify each *_MD_CONTENT is a complete agent definition, not a
    placeholder or skeleton."""

    ALL_MD_CONTENT_NAMES = [
        "STAKEHOLDER_REVIEWER_MD_CONTENT",
        "BLUEPRINT_CHECKER_MD_CONTENT",
        "BLUEPRINT_REVIEWER_MD_CONTENT",
    ]

    @pytest.mark.parametrize("const_name", ALL_MD_CONTENT_NAMES)
    def test_not_a_placeholder(self, const_name):
        """Content must not be a placeholder -- it should have multiple
        paragraphs or sections of substantive text."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        # DATA ASSUMPTION: A non-skeleton agent definition is at least 500 chars
        assert len(body.strip()) >= 500, (
            f"{const_name} appears to be a skeleton/placeholder "
            f"({len(body.strip())} chars). Expected >= 500 chars of "
            "substantive instructions."
        )

    @pytest.mark.parametrize("const_name", ALL_MD_CONTENT_NAMES)
    def test_has_multiple_sections_or_paragraphs(self, const_name):
        """A complete agent definition should have multiple paragraphs."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        non_empty_lines = [
            line for line in body.split("\n") if line.strip()
        ]
        # DATA ASSUMPTION: A complete agent definition has at least 10
        # non-empty lines of instructions
        assert len(non_empty_lines) >= 10, (
            f"{const_name} has only {len(non_empty_lines)} non-empty lines. "
            "Expected >= 10 for a complete agent definition."
        )


# ===========================================================================
# Section 11: Single-Shot Agent Pattern (Not Dialog Agents)
# ===========================================================================


class TestSingleShotAgentPattern:
    """These are single-shot agents, not dialog agents. They do NOT use
    the conversation ledger or structured response format. Verify that the
    distinction is clear in the agent definitions.

    DATA ASSUMPTION: Single-shot agents terminate with their terminal status
    line. They do not have the [QUESTION]/[DECISION]/[CONFIRMED] pattern
    that dialog agents use.
    """

    def test_stakeholder_reviewer_is_single_shot(self):
        """Stakeholder Reviewer should indicate it is single-shot / terminates."""
        body = _get_body_after_frontmatter(
            _get_md_content("STAKEHOLDER_REVIEWER_MD_CONTENT")
        )
        body_lower = body.lower()
        assert ("single" in body_lower or "terminat" in body_lower
                or "one-shot" in body_lower or "single-shot" in body_lower
                or "cold" in body_lower or "complete" in body_lower), (
            "Stakeholder Reviewer must indicate it is a single-shot agent"
        )

    def test_blueprint_reviewer_is_single_shot(self):
        """Blueprint Reviewer should indicate it is single-shot / terminates."""
        body = _get_body_after_frontmatter(
            _get_md_content("BLUEPRINT_REVIEWER_MD_CONTENT")
        )
        body_lower = body.lower()
        assert ("single" in body_lower or "terminat" in body_lower
                or "one-shot" in body_lower or "single-shot" in body_lower
                or "cold" in body_lower or "complete" in body_lower), (
            "Blueprint Reviewer must indicate it is a single-shot agent"
        )

    def test_blueprint_checker_is_single_shot(self):
        """Blueprint Checker should indicate it terminates with a verdict."""
        body = _get_body_after_frontmatter(
            _get_md_content("BLUEPRINT_CHECKER_MD_CONTENT")
        )
        body_lower = body.lower()
        assert ("terminat" in body_lower or "verdict" in body_lower
                or "complete" in body_lower or "single" in body_lower
                or "outcome" in body_lower), (
            "Blueprint Checker must indicate it terminates with a verdict"
        )


# ===========================================================================
# Section 12: Blueprint Checker Structural Validation Details
# ===========================================================================


class TestBlueprintCheckerStructuralValidation:
    """Verify the Blueprint Checker describes all five structural validation
    requirements from the blueprint invariants:
    1. Machine-readable signatures are parseable (valid Python via ast)
    2. All referenced types have corresponding import statements
    3. Per-unit worst-case context budget is within threshold
    4. Working notes are consistent with original spec text
    5. Report most fundamental level when multiple issues found
    """

    @pytest.fixture
    def body(self):
        return _get_body_after_frontmatter(
            _get_md_content("BLUEPRINT_CHECKER_MD_CONTENT")
        )

    def test_describes_signature_parseability(self, body):
        """Must describe validating that signatures are parseable Python."""
        body_lower = body.lower()
        assert ("parseable" in body_lower or "parse" in body_lower
                or "valid python" in body_lower or "syntax" in body_lower
                or "ast" in body_lower), (
            "Blueprint Checker must describe validating signature parseability"
        )

    def test_describes_import_completeness(self, body):
        """Must describe validating that all types have imports."""
        body_lower = body.lower()
        assert "import" in body_lower, (
            "Blueprint Checker must describe import validation"
        )

    def test_describes_context_budget_check(self, body):
        """Must describe validating per-unit context budget."""
        body_lower = body.lower()
        has_context = "context" in body_lower
        has_budget = "budget" in body_lower
        assert has_context and has_budget, (
            "Blueprint Checker must describe context budget validation"
        )

    def test_describes_working_note_consistency(self, body):
        """Must describe validating working note consistency."""
        body_lower = body.lower()
        assert "working note" in body_lower, (
            "Blueprint Checker must describe working note consistency validation"
        )

    def test_describes_fundamental_level_reporting(self, body):
        """Must describe reporting the most fundamental level."""
        body_lower = body.lower()
        assert "fundamental" in body_lower, (
            "Blueprint Checker must describe the most fundamental level principle"
        )


# ===========================================================================
# Section 13: Frontmatter Contains Description Key
# ===========================================================================


class TestFrontmatterContainsDescription:
    """The *_FRONTMATTER dicts include 'description'. Verify the MD_CONTENT
    YAML frontmatter itself also contains 'description:'.
    """

    ALL_MD_CONTENT_NAMES = [
        "STAKEHOLDER_REVIEWER_MD_CONTENT",
        "BLUEPRINT_CHECKER_MD_CONTENT",
        "BLUEPRINT_REVIEWER_MD_CONTENT",
    ]

    @pytest.mark.parametrize("const_name", ALL_MD_CONTENT_NAMES)
    def test_frontmatter_contains_description_key(self, const_name):
        """Parsed frontmatter from MD_CONTENT must have 'description' key."""
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert "description" in fm, (
            f"{const_name} YAML frontmatter must contain 'description:' key"
        )


# ===========================================================================
# Section 14: Tool Set Differentiation
# ===========================================================================


class TestToolSetDifferentiation:
    """Verify that tool sets differ appropriately between agents.

    DATA ASSUMPTION: Stakeholder Reviewer and Blueprint Reviewer have the same
    read-only tool set [Read, Glob, Grep], while Blueprint Checker additionally
    has Bash for ast.parse() validation.
    """

    def test_stakeholder_reviewer_no_bash(self):
        """Stakeholder Reviewer should NOT have Bash tool."""
        assert "Bash" not in STAKEHOLDER_REVIEWER_FRONTMATTER["tools"]

    def test_blueprint_reviewer_no_bash(self):
        """Blueprint Reviewer should NOT have Bash tool."""
        assert "Bash" not in BLUEPRINT_REVIEWER_FRONTMATTER["tools"]

    def test_blueprint_checker_has_bash(self):
        """Blueprint Checker MUST have Bash tool for ast.parse()."""
        assert "Bash" in BLUEPRINT_CHECKER_FRONTMATTER["tools"]

    def test_all_have_read(self):
        """All agents must have Read tool."""
        for fm in [STAKEHOLDER_REVIEWER_FRONTMATTER,
                    BLUEPRINT_CHECKER_FRONTMATTER,
                    BLUEPRINT_REVIEWER_FRONTMATTER]:
            assert "Read" in fm["tools"]

    def test_all_have_glob(self):
        """All agents must have Glob tool."""
        for fm in [STAKEHOLDER_REVIEWER_FRONTMATTER,
                    BLUEPRINT_CHECKER_FRONTMATTER,
                    BLUEPRINT_REVIEWER_FRONTMATTER]:
            assert "Glob" in fm["tools"]

    def test_all_have_grep(self):
        """All agents must have Grep tool."""
        for fm in [STAKEHOLDER_REVIEWER_FRONTMATTER,
                    BLUEPRINT_CHECKER_FRONTMATTER,
                    BLUEPRINT_REVIEWER_FRONTMATTER]:
            assert "Grep" in fm["tools"]

    def test_reviewers_have_no_write_tools(self):
        """Neither reviewer should have Write or Edit tools (read-only review)."""
        for label, fm in [("STAKEHOLDER_REVIEWER", STAKEHOLDER_REVIEWER_FRONTMATTER),
                          ("BLUEPRINT_REVIEWER", BLUEPRINT_REVIEWER_FRONTMATTER)]:
            assert "Write" not in fm["tools"], (
                f"{label} should not have Write tool (read-only agent)"
            )
            assert "Edit" not in fm["tools"], (
                f"{label} should not have Edit tool (read-only agent)"
            )

    def test_md_content_tools_match_frontmatter_stakeholder_reviewer(self):
        """Verify MD_CONTENT tools match the frontmatter constant for Stakeholder Reviewer."""
        content = _get_md_content("STAKEHOLDER_REVIEWER_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["tools"] == STAKEHOLDER_REVIEWER_FRONTMATTER["tools"]

    def test_md_content_tools_match_frontmatter_blueprint_checker(self):
        """Verify MD_CONTENT tools match the frontmatter constant for Blueprint Checker."""
        content = _get_md_content("BLUEPRINT_CHECKER_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["tools"] == BLUEPRINT_CHECKER_FRONTMATTER["tools"]

    def test_md_content_tools_match_frontmatter_blueprint_reviewer(self):
        """Verify MD_CONTENT tools match the frontmatter constant for Blueprint Reviewer."""
        content = _get_md_content("BLUEPRINT_REVIEWER_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["tools"] == BLUEPRINT_REVIEWER_FRONTMATTER["tools"]

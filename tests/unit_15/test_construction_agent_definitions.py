"""Tests for Unit 15: Construction Agent Definitions

Verifies that the three construction agent definition constants (Test Agent,
Implementation Agent, Coverage Review Agent) conform to the blueprint's
contracts, invariants, and signature specifications.

DATA ASSUMPTIONS:
- All expected constant values are derived directly from the blueprint's
  Tier 2 Signatures section. No domain-specific data generation is needed
  since this unit defines static configuration constants.
- Frontmatter field values (name, description, model, tools) are taken
  verbatim from the blueprint.
- The minimum instruction length threshold of 100 characters is taken from
  the blueprint's Tier 2 Invariants.
"""

import pytest
from typing import Dict, Any, List


# ---------------------------------------------------------------------------
# Helper: parse YAML frontmatter without pyyaml
# ---------------------------------------------------------------------------

def _parse_frontmatter(md_content: str) -> dict:
    """Parse YAML frontmatter from a Markdown string (no pyyaml dependency)."""
    assert md_content.startswith("---\n"), "MD content must start with '---\\n'"
    second_delim = md_content.index("---\n", 4)
    yaml_block = md_content[4:second_delim]
    result = {}
    current_key = None
    current_list = []
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


# ---------------------------------------------------------------------------
# Import the unit under test
# ---------------------------------------------------------------------------

from svp.scripts.construction_agent_definitions import (
    TEST_AGENT_FRONTMATTER,
    IMPLEMENTATION_AGENT_FRONTMATTER,
    COVERAGE_REVIEW_AGENT_FRONTMATTER,
    TEST_AGENT_STATUS,
    IMPLEMENTATION_AGENT_STATUS,
    COVERAGE_REVIEW_STATUS,
)


def _get_md_content(name: str) -> str:
    """Import an MD_CONTENT constant from the stub module.

    The stub declares these as type annotations without values, so getattr
    will fail on the stub (red run) and succeed on the implementation.
    """
    import svp.scripts.construction_agent_definitions as mod
    value = getattr(mod, name)
    assert isinstance(value, str), (
        f"{name} must be a str, got {type(value).__name__}"
    )
    return value


# ===========================================================================
# SECTION 1: Type and Signature Verification
# ===========================================================================

class TestTypeSignatures:
    """Verify that all exported constants have the correct types as specified
    in the blueprint's Tier 2 Signatures."""

    def test_test_agent_frontmatter_is_dict(self):
        """TEST_AGENT_FRONTMATTER must be Dict[str, Any]."""
        assert isinstance(TEST_AGENT_FRONTMATTER, dict)

    def test_implementation_agent_frontmatter_is_dict(self):
        """IMPLEMENTATION_AGENT_FRONTMATTER must be Dict[str, Any]."""
        assert isinstance(IMPLEMENTATION_AGENT_FRONTMATTER, dict)

    def test_coverage_review_agent_frontmatter_is_dict(self):
        """COVERAGE_REVIEW_AGENT_FRONTMATTER must be Dict[str, Any]."""
        assert isinstance(COVERAGE_REVIEW_AGENT_FRONTMATTER, dict)

    def test_test_agent_status_is_list(self):
        """TEST_AGENT_STATUS must be List[str]."""
        assert isinstance(TEST_AGENT_STATUS, list)
        for item in TEST_AGENT_STATUS:
            assert isinstance(item, str)

    def test_implementation_agent_status_is_list(self):
        """IMPLEMENTATION_AGENT_STATUS must be List[str]."""
        assert isinstance(IMPLEMENTATION_AGENT_STATUS, list)
        for item in IMPLEMENTATION_AGENT_STATUS:
            assert isinstance(item, str)

    def test_coverage_review_status_is_list(self):
        """COVERAGE_REVIEW_STATUS must be List[str]."""
        assert isinstance(COVERAGE_REVIEW_STATUS, list)
        for item in COVERAGE_REVIEW_STATUS:
            assert isinstance(item, str)

    def test_test_agent_md_content_is_str(self):
        """TEST_AGENT_MD_CONTENT must be str."""
        content = _get_md_content("TEST_AGENT_MD_CONTENT")
        assert isinstance(content, str)

    def test_implementation_agent_md_content_is_str(self):
        """IMPLEMENTATION_AGENT_MD_CONTENT must be str."""
        content = _get_md_content("IMPLEMENTATION_AGENT_MD_CONTENT")
        assert isinstance(content, str)

    def test_coverage_review_agent_md_content_is_str(self):
        """COVERAGE_REVIEW_AGENT_MD_CONTENT must be str."""
        content = _get_md_content("COVERAGE_REVIEW_AGENT_MD_CONTENT")
        assert isinstance(content, str)


# ===========================================================================
# SECTION 2: Frontmatter Dict Value Verification
# ===========================================================================

class TestTestAgentFrontmatter:
    """Verify TEST_AGENT_FRONTMATTER matches the blueprint specification."""

    # DATA ASSUMPTION: Values taken verbatim from blueprint Tier 2 Signatures.
    EXPECTED = {
        "name": "test_agent",
        "description": "Generates pytest test suite for a single unit",
        "model": "claude-opus-4-6",
        "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
    }

    def test_name(self):
        assert TEST_AGENT_FRONTMATTER["name"] == self.EXPECTED["name"]

    def test_description(self):
        assert TEST_AGENT_FRONTMATTER["description"] == self.EXPECTED["description"]

    def test_model(self):
        assert TEST_AGENT_FRONTMATTER["model"] == self.EXPECTED["model"]

    def test_tools(self):
        assert TEST_AGENT_FRONTMATTER["tools"] == self.EXPECTED["tools"]

    def test_has_exactly_expected_keys(self):
        assert set(TEST_AGENT_FRONTMATTER.keys()) == set(self.EXPECTED.keys())


class TestImplementationAgentFrontmatter:
    """Verify IMPLEMENTATION_AGENT_FRONTMATTER matches the blueprint specification."""

    # DATA ASSUMPTION: Values taken verbatim from blueprint Tier 2 Signatures.
    EXPECTED = {
        "name": "implementation_agent",
        "description": "Generates Python implementation for a single unit",
        "model": "claude-opus-4-6",
        "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
    }

    def test_name(self):
        assert IMPLEMENTATION_AGENT_FRONTMATTER["name"] == self.EXPECTED["name"]

    def test_description(self):
        assert IMPLEMENTATION_AGENT_FRONTMATTER["description"] == self.EXPECTED["description"]

    def test_model(self):
        assert IMPLEMENTATION_AGENT_FRONTMATTER["model"] == self.EXPECTED["model"]

    def test_tools(self):
        assert IMPLEMENTATION_AGENT_FRONTMATTER["tools"] == self.EXPECTED["tools"]

    def test_has_exactly_expected_keys(self):
        assert set(IMPLEMENTATION_AGENT_FRONTMATTER.keys()) == set(self.EXPECTED.keys())


class TestCoverageReviewAgentFrontmatter:
    """Verify COVERAGE_REVIEW_AGENT_FRONTMATTER matches the blueprint specification."""

    # DATA ASSUMPTION: Values taken verbatim from blueprint Tier 2 Signatures.
    EXPECTED = {
        "name": "coverage_review_agent",
        "description": "Reviews test coverage and adds missing tests",
        "model": "claude-opus-4-6",
        "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
    }

    def test_name(self):
        assert COVERAGE_REVIEW_AGENT_FRONTMATTER["name"] == self.EXPECTED["name"]

    def test_description(self):
        assert COVERAGE_REVIEW_AGENT_FRONTMATTER["description"] == self.EXPECTED["description"]

    def test_model(self):
        assert COVERAGE_REVIEW_AGENT_FRONTMATTER["model"] == self.EXPECTED["model"]

    def test_tools(self):
        assert COVERAGE_REVIEW_AGENT_FRONTMATTER["tools"] == self.EXPECTED["tools"]

    def test_has_exactly_expected_keys(self):
        assert set(COVERAGE_REVIEW_AGENT_FRONTMATTER.keys()) == set(self.EXPECTED.keys())


# ===========================================================================
# SECTION 3: Terminal Status Line Verification
# ===========================================================================

class TestStatusLines:
    """Verify that terminal status constants match blueprint specification."""

    # DATA ASSUMPTION: Status line values taken verbatim from blueprint Tier 2.

    def test_test_agent_status_values(self):
        assert TEST_AGENT_STATUS == ["TEST_GENERATION_COMPLETE"]

    def test_implementation_agent_status_values(self):
        assert IMPLEMENTATION_AGENT_STATUS == ["IMPLEMENTATION_COMPLETE"]

    def test_coverage_review_status_values(self):
        assert COVERAGE_REVIEW_STATUS == [
            "COVERAGE_COMPLETE: no gaps",
            "COVERAGE_COMPLETE: tests added",
        ]

    def test_coverage_review_status_has_two_entries(self):
        assert len(COVERAGE_REVIEW_STATUS) == 2

    def test_test_agent_status_has_one_entry(self):
        assert len(TEST_AGENT_STATUS) == 1

    def test_implementation_agent_status_has_one_entry(self):
        assert len(IMPLEMENTATION_AGENT_STATUS) == 1


# ===========================================================================
# SECTION 4: MD Content Structural Invariants
# ===========================================================================

class TestMDContentStructuralInvariants:
    """Verify the structural invariants from the blueprint:
    - Starts with '---\\n' (YAML frontmatter delimiter)
    - Contains 'name:' in frontmatter
    - Contains 'model:' in frontmatter
    - Contains 'tools:' in frontmatter
    - Contains a second '---\\n' (end of frontmatter)
    - Has substantial behavioral instructions after frontmatter (>100 chars)
    """

    @pytest.mark.parametrize("content_name,content", [
        ("TEST_AGENT_MD_CONTENT", None),
        ("IMPLEMENTATION_AGENT_MD_CONTENT", None),
        ("COVERAGE_REVIEW_AGENT_MD_CONTENT", None),
    ])
    def test_starts_with_yaml_delimiter(self, content_name, content):
        actual = _get_content_by_name(content_name)
        assert actual.startswith("---\n"), (
            f"{content_name} must start with '---\\n' (YAML frontmatter delimiter)"
        )

    @pytest.mark.parametrize("content_name", [
        "TEST_AGENT_MD_CONTENT",
        "IMPLEMENTATION_AGENT_MD_CONTENT",
        "COVERAGE_REVIEW_AGENT_MD_CONTENT",
    ])
    def test_has_second_yaml_delimiter(self, content_name):
        actual = _get_content_by_name(content_name)
        # Find second occurrence of "---\n"
        first_end = 4  # past the first "---\n"
        second_idx = actual.find("---\n", first_end)
        assert second_idx > first_end, (
            f"{content_name} must contain a second '---\\n' to close frontmatter"
        )

    @pytest.mark.parametrize("content_name", [
        "TEST_AGENT_MD_CONTENT",
        "IMPLEMENTATION_AGENT_MD_CONTENT",
        "COVERAGE_REVIEW_AGENT_MD_CONTENT",
    ])
    def test_frontmatter_contains_name(self, content_name):
        actual = _get_content_by_name(content_name)
        frontmatter = _extract_frontmatter_block(actual)
        assert "name:" in frontmatter, (
            f"{content_name} frontmatter must contain 'name:'"
        )

    @pytest.mark.parametrize("content_name", [
        "TEST_AGENT_MD_CONTENT",
        "IMPLEMENTATION_AGENT_MD_CONTENT",
        "COVERAGE_REVIEW_AGENT_MD_CONTENT",
    ])
    def test_frontmatter_contains_model(self, content_name):
        actual = _get_content_by_name(content_name)
        frontmatter = _extract_frontmatter_block(actual)
        assert "model:" in frontmatter, (
            f"{content_name} frontmatter must contain 'model:'"
        )

    @pytest.mark.parametrize("content_name", [
        "TEST_AGENT_MD_CONTENT",
        "IMPLEMENTATION_AGENT_MD_CONTENT",
        "COVERAGE_REVIEW_AGENT_MD_CONTENT",
    ])
    def test_frontmatter_contains_tools(self, content_name):
        actual = _get_content_by_name(content_name)
        frontmatter = _extract_frontmatter_block(actual)
        assert "tools:" in frontmatter, (
            f"{content_name} frontmatter must contain 'tools:'"
        )

    @pytest.mark.parametrize("content_name", [
        "TEST_AGENT_MD_CONTENT",
        "IMPLEMENTATION_AGENT_MD_CONTENT",
        "COVERAGE_REVIEW_AGENT_MD_CONTENT",
    ])
    def test_substantial_instructions_after_frontmatter(self, content_name):
        actual = _get_content_by_name(content_name)
        instructions = _extract_instructions(actual)
        assert len(instructions) > 100, (
            f"{content_name} must have >100 chars of behavioral instructions "
            f"after frontmatter, got {len(instructions)}"
        )


# ===========================================================================
# SECTION 5: Frontmatter-to-MD Content Alignment
# ===========================================================================

class TestFrontmatterMDAlignment:
    """Verify that the YAML frontmatter in each *_MD_CONTENT string
    matches the corresponding *_FRONTMATTER dict."""

    def test_test_agent_frontmatter_matches_md(self):
        """TEST_AGENT_MD_CONTENT frontmatter must match TEST_AGENT_FRONTMATTER."""
        parsed = _parse_frontmatter(_get_md_content("TEST_AGENT_MD_CONTENT"))
        assert parsed["name"] == TEST_AGENT_FRONTMATTER["name"]
        assert parsed["description"] == TEST_AGENT_FRONTMATTER["description"]
        assert parsed["model"] == TEST_AGENT_FRONTMATTER["model"]
        assert parsed["tools"] == TEST_AGENT_FRONTMATTER["tools"]

    def test_implementation_agent_frontmatter_matches_md(self):
        """IMPLEMENTATION_AGENT_MD_CONTENT frontmatter must match
        IMPLEMENTATION_AGENT_FRONTMATTER."""
        parsed = _parse_frontmatter(_get_md_content("IMPLEMENTATION_AGENT_MD_CONTENT"))
        assert parsed["name"] == IMPLEMENTATION_AGENT_FRONTMATTER["name"]
        assert parsed["description"] == IMPLEMENTATION_AGENT_FRONTMATTER["description"]
        assert parsed["model"] == IMPLEMENTATION_AGENT_FRONTMATTER["model"]
        assert parsed["tools"] == IMPLEMENTATION_AGENT_FRONTMATTER["tools"]

    def test_coverage_review_frontmatter_matches_md(self):
        """COVERAGE_REVIEW_AGENT_MD_CONTENT frontmatter must match
        COVERAGE_REVIEW_AGENT_FRONTMATTER."""
        parsed = _parse_frontmatter(_get_md_content("COVERAGE_REVIEW_AGENT_MD_CONTENT"))
        assert parsed["name"] == COVERAGE_REVIEW_AGENT_FRONTMATTER["name"]
        assert parsed["description"] == COVERAGE_REVIEW_AGENT_FRONTMATTER["description"]
        assert parsed["model"] == COVERAGE_REVIEW_AGENT_FRONTMATTER["model"]
        assert parsed["tools"] == COVERAGE_REVIEW_AGENT_FRONTMATTER["tools"]


# ===========================================================================
# SECTION 6: Behavioral Contract - Test Agent MD Content
# ===========================================================================

class TestTestAgentBehavioralContracts:
    """Verify behavioral contracts for the Test Agent definition.

    Blueprint says: Receives unit definition and upstream contracts from blueprint.
    Generates a complete pytest test suite including synthetic test data. Must
    declare synthetic data assumptions. Does NOT see any implementation. Terminal
    status: TEST_GENERATION_COMPLETE. Uses claude-opus-4-6.
    """

    # DATA ASSUMPTION: Keywords checked are derived from the behavioral contracts
    # in the blueprint. We check for the presence of key concepts, not exact prose.

    def test_instructions_describe_purpose(self):
        """Instructions must describe the agent's purpose."""
        instructions = _extract_instructions(_get_md_content("TEST_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "test" in lower, "Test agent instructions must mention tests"

    def test_instructions_mention_pytest(self):
        """Test agent instructions must mention pytest framework."""
        instructions = _extract_instructions(_get_md_content("TEST_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "pytest" in lower, "Test agent must use pytest"

    def test_instructions_mention_synthetic_data(self):
        """Test agent must mention synthetic test data generation."""
        instructions = _extract_instructions(_get_md_content("TEST_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "synthetic" in lower, (
            "Test agent must mention synthetic data"
        )

    def test_instructions_mention_data_assumptions(self):
        """Test agent must require declaration of synthetic data assumptions."""
        instructions = _extract_instructions(_get_md_content("TEST_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "assumption" in lower, (
            "Test agent must mention data assumptions"
        )

    def test_instructions_prohibit_seeing_implementation(self):
        """Test agent must NOT see the implementation code."""
        instructions = _extract_instructions(_get_md_content("TEST_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        # Must contain language about not seeing/accessing implementation
        assert "implementation" in lower, (
            "Test agent instructions must reference implementation (to prohibit seeing it)"
        )
        # Check for prohibition language
        has_prohibition = (
            "not see" in lower
            or "must not" in lower
            or "never see" in lower
            or "do not" in lower
            or "shall not" in lower
            or "must not see" in lower
            or "not request" in lower
            or "not access" in lower
            or "never" in lower
        )
        assert has_prohibition, (
            "Test agent instructions must prohibit seeing implementation"
        )

    def test_instructions_mention_terminal_status(self):
        """Test agent instructions must mention the terminal status line."""
        instructions = _extract_instructions(_get_md_content("TEST_AGENT_MD_CONTENT"))
        assert "TEST_GENERATION_COMPLETE" in instructions, (
            "Test agent instructions must reference its terminal status line"
        )

    def test_instructions_mention_blueprint_or_unit_definition(self):
        """Test agent receives unit definition and upstream contracts."""
        instructions = _extract_instructions(_get_md_content("TEST_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        has_input_ref = "blueprint" in lower or "unit" in lower
        assert has_input_ref, (
            "Test agent instructions must reference blueprint/unit definitions as input"
        )

    def test_instructions_mention_upstream_contracts(self):
        """Test agent receives upstream contracts."""
        instructions = _extract_instructions(_get_md_content("TEST_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "upstream" in lower or "contract" in lower or "dependencies" in lower, (
            "Test agent instructions must reference upstream contracts"
        )

    def test_model_is_claude_opus_4_6(self):
        """Test agent uses claude-opus-4-6."""
        assert TEST_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"


# ===========================================================================
# SECTION 7: Behavioral Contract - Implementation Agent MD Content
# ===========================================================================

class TestImplementationAgentBehavioralContracts:
    """Verify behavioral contracts for the Implementation Agent definition.

    Blueprint says: Receives unit definition and upstream contracts from blueprint.
    Generates the Python implementation. Does NOT see the tests. In fix ladder
    positions: receives diagnostic guidance, prior failure output, and optional hint.
    If a hint contradicts the blueprint, returns HINT_BLUEPRINT_CONFLICT: [details].
    Terminal status: IMPLEMENTATION_COMPLETE. Uses claude-opus-4-6.
    """

    # DATA ASSUMPTION: Keywords checked are derived from the behavioral contracts
    # in the blueprint.

    def test_instructions_describe_purpose(self):
        """Instructions must describe generating implementation."""
        instructions = _extract_instructions(_get_md_content("IMPLEMENTATION_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "implementation" in lower or "implement" in lower, (
            "Implementation agent instructions must mention implementation"
        )

    def test_instructions_mention_python(self):
        """Implementation agent generates Python code."""
        instructions = _extract_instructions(_get_md_content("IMPLEMENTATION_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "python" in lower, (
            "Implementation agent must mention Python"
        )

    def test_instructions_prohibit_seeing_tests(self):
        """Implementation agent must NOT see the tests."""
        instructions = _extract_instructions(_get_md_content("IMPLEMENTATION_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "test" in lower, (
            "Implementation agent instructions must reference tests (to prohibit seeing them)"
        )
        # Check for prohibition language
        has_prohibition = (
            "not see" in lower
            or "must not" in lower
            or "never see" in lower
            or "do not" in lower
            or "shall not" in lower
            or "never" in lower
            or "not request" in lower
            or "not access" in lower
        )
        assert has_prohibition, (
            "Implementation agent instructions must prohibit seeing tests"
        )

    def test_instructions_mention_terminal_status(self):
        """Implementation agent instructions must mention the terminal status line."""
        instructions = _extract_instructions(_get_md_content("IMPLEMENTATION_AGENT_MD_CONTENT"))
        assert "IMPLEMENTATION_COMPLETE" in instructions, (
            "Implementation agent instructions must reference its terminal status line"
        )

    def test_instructions_mention_hint_blueprint_conflict(self):
        """Implementation agent must handle HINT_BLUEPRINT_CONFLICT."""
        instructions = _extract_instructions(_get_md_content("IMPLEMENTATION_AGENT_MD_CONTENT"))
        assert "HINT_BLUEPRINT_CONFLICT" in instructions, (
            "Implementation agent instructions must reference HINT_BLUEPRINT_CONFLICT"
        )

    def test_instructions_mention_fix_ladder(self):
        """Implementation agent must handle fix ladder positions."""
        instructions = _extract_instructions(_get_md_content("IMPLEMENTATION_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        has_fix_ref = (
            "fix" in lower
            or "diagnostic" in lower
            or "failure" in lower
            or "prior" in lower
        )
        assert has_fix_ref, (
            "Implementation agent instructions must reference fix ladder / diagnostic guidance"
        )

    def test_instructions_mention_blueprint_input(self):
        """Implementation agent receives unit definition from blueprint."""
        instructions = _extract_instructions(_get_md_content("IMPLEMENTATION_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "blueprint" in lower or "unit" in lower, (
            "Implementation agent instructions must reference blueprint/unit as input"
        )

    def test_instructions_mention_upstream_contracts(self):
        """Implementation agent receives upstream contracts from blueprint.

        Blueprint behavioral contract: 'Receives unit definition and upstream
        contracts from blueprint.' The instructions must reference upstream
        contracts or dependencies.
        """
        # DATA ASSUMPTION: Keywords checked mirror the test agent's equivalent
        # test (test_instructions_mention_upstream_contracts in Section 6),
        # applied to the implementation agent per its behavioral contract.
        instructions = _extract_instructions(_get_md_content("IMPLEMENTATION_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "upstream" in lower or "contract" in lower or "dependencies" in lower, (
            "Implementation agent instructions must reference upstream contracts"
        )

    def test_model_is_claude_opus_4_6(self):
        """Implementation agent uses claude-opus-4-6."""
        assert IMPLEMENTATION_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"


# ===========================================================================
# SECTION 8: Behavioral Contract - Coverage Review Agent MD Content
# ===========================================================================

class TestCoverageReviewAgentBehavioralContracts:
    """Verify behavioral contracts for the Coverage Review Agent definition.

    Blueprint says: Receives blueprint unit definition, upstream contracts, and
    passing test suite. Identifies behaviors implied by blueprint that no test
    covers. Adds missing coverage. Newly added tests must be validated as meaningful
    (fail for the right reason, not just because the stub raises NotImplementedError).
    Terminal status: COVERAGE_COMPLETE: no gaps or COVERAGE_COMPLETE: tests added.
    Uses claude-opus-4-6.
    """

    # DATA ASSUMPTION: Keywords checked are derived from the behavioral contracts
    # in the blueprint.

    def test_instructions_describe_purpose(self):
        """Instructions must describe reviewing test coverage."""
        instructions = _extract_instructions(_get_md_content("COVERAGE_REVIEW_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "coverage" in lower, (
            "Coverage review agent instructions must mention coverage"
        )

    def test_instructions_mention_identifying_gaps(self):
        """Coverage review identifies behaviors not covered by tests."""
        instructions = _extract_instructions(_get_md_content("COVERAGE_REVIEW_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        has_gap_ref = "gap" in lower or "missing" in lower or "uncovered" in lower
        assert has_gap_ref, (
            "Coverage review agent must mention identifying gaps/missing coverage"
        )

    def test_instructions_mention_adding_tests(self):
        """Coverage review adds missing tests."""
        instructions = _extract_instructions(_get_md_content("COVERAGE_REVIEW_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "test" in lower, (
            "Coverage review agent must mention tests"
        )

    def test_instructions_mention_meaningful_validation(self):
        """Newly added tests must be validated as meaningful (not just
        failing because stub raises NotImplementedError)."""
        instructions = _extract_instructions(_get_md_content("COVERAGE_REVIEW_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        has_meaningful_ref = (
            "meaningful" in lower
            or "notimplementederror" in lower
            or "not just" in lower
            or "right reason" in lower
            or "stub" in lower
        )
        assert has_meaningful_ref, (
            "Coverage review agent must mention meaningful test validation "
            "(not just failing on NotImplementedError)"
        )

    def test_instructions_mention_terminal_status_no_gaps(self):
        """Coverage review must mention COVERAGE_COMPLETE: no gaps."""
        instructions = _extract_instructions(_get_md_content("COVERAGE_REVIEW_AGENT_MD_CONTENT"))
        assert "COVERAGE_COMPLETE: no gaps" in instructions or "COVERAGE_COMPLETE" in instructions, (
            "Coverage review agent must reference its terminal status line(s)"
        )

    def test_instructions_mention_terminal_status_tests_added(self):
        """Coverage review must mention COVERAGE_COMPLETE: tests added."""
        instructions = _extract_instructions(_get_md_content("COVERAGE_REVIEW_AGENT_MD_CONTENT"))
        assert "COVERAGE_COMPLETE: tests added" in instructions or "COVERAGE_COMPLETE" in instructions, (
            "Coverage review agent must reference its terminal status line(s)"
        )

    def test_instructions_mention_both_terminal_statuses(self):
        """Coverage review must mention both terminal status variants."""
        instructions = _extract_instructions(_get_md_content("COVERAGE_REVIEW_AGENT_MD_CONTENT"))
        assert "COVERAGE_COMPLETE" in instructions, (
            "Coverage review agent must reference COVERAGE_COMPLETE status"
        )

    def test_instructions_mention_blueprint_input(self):
        """Coverage review receives blueprint unit definition."""
        instructions = _extract_instructions(_get_md_content("COVERAGE_REVIEW_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "blueprint" in lower or "unit" in lower, (
            "Coverage review agent instructions must reference blueprint/unit as input"
        )

    def test_instructions_mention_test_suite_input(self):
        """Coverage review receives the passing test suite."""
        instructions = _extract_instructions(_get_md_content("COVERAGE_REVIEW_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "test" in lower and ("passing" in lower or "suite" in lower or "existing" in lower), (
            "Coverage review agent must receive the passing test suite"
        )

    def test_instructions_mention_upstream_contracts(self):
        """Coverage review receives upstream contracts.

        Blueprint behavioral contract: 'Receives blueprint unit definition,
        upstream contracts, and passing test suite.' The instructions must
        reference upstream contracts or dependencies.
        """
        # DATA ASSUMPTION: Keywords checked mirror the test agent's equivalent
        # test (test_instructions_mention_upstream_contracts in Section 6),
        # applied to the coverage review agent per its behavioral contract.
        instructions = _extract_instructions(_get_md_content("COVERAGE_REVIEW_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "upstream" in lower or "contract" in lower or "dependencies" in lower, (
            "Coverage review agent instructions must reference upstream contracts"
        )

    def test_model_is_claude_opus_4_6(self):
        """Coverage review agent uses claude-opus-4-6."""
        assert COVERAGE_REVIEW_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"


# ===========================================================================
# SECTION 9: Cross-Agent Isolation Invariants
# ===========================================================================

class TestAgentIsolationInvariants:
    """Verify the invariant that test agent and implementation agent are
    isolated -- they must never see each other's artifacts.

    Blueprint invariants:
    - Test agent must never see the implementation
    - Implementation agent must never see the tests
    - These agents are invoked independently with no shared context
    """

    def test_test_agent_name_distinct_from_implementation(self):
        """Test and implementation agents have distinct names."""
        assert TEST_AGENT_FRONTMATTER["name"] != IMPLEMENTATION_AGENT_FRONTMATTER["name"]

    def test_test_agent_name_distinct_from_coverage(self):
        """Test and coverage review agents have distinct names."""
        assert TEST_AGENT_FRONTMATTER["name"] != COVERAGE_REVIEW_AGENT_FRONTMATTER["name"]

    def test_implementation_agent_name_distinct_from_coverage(self):
        """Implementation and coverage review agents have distinct names."""
        assert IMPLEMENTATION_AGENT_FRONTMATTER["name"] != COVERAGE_REVIEW_AGENT_FRONTMATTER["name"]

    def test_all_agents_use_same_model(self):
        """All three construction agents use claude-opus-4-6."""
        assert TEST_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"
        assert IMPLEMENTATION_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"
        assert COVERAGE_REVIEW_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_all_agents_have_same_tools(self):
        """All three construction agents have the same tool set."""
        expected_tools = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
        assert TEST_AGENT_FRONTMATTER["tools"] == expected_tools
        assert IMPLEMENTATION_AGENT_FRONTMATTER["tools"] == expected_tools
        assert COVERAGE_REVIEW_AGENT_FRONTMATTER["tools"] == expected_tools


# ===========================================================================
# SECTION 10: MD Content Descriptions (methodology, I/O, constraints)
# ===========================================================================

class TestMDContentCompleteness:
    """Verify that MD content behavioral instructions describe: the agent's
    purpose, its methodology, its input/output format, its constraints, and
    its terminal status line(s). From the behavioral contract:
    'The behavioral instructions after the frontmatter must describe: the
    agent's purpose, its methodology, its input/output format, its constraints,
    and its terminal status line(s).'
    """

    # DATA ASSUMPTION: We check for section-like markers or keyword presence
    # to verify completeness. The exact section headings are not prescribed,
    # so we check for the presence of key concepts.

    @pytest.mark.parametrize("content_name", [
        "TEST_AGENT_MD_CONTENT",
        "IMPLEMENTATION_AGENT_MD_CONTENT",
        "COVERAGE_REVIEW_AGENT_MD_CONTENT",
    ])
    def test_describes_purpose(self, content_name):
        """Each agent definition must describe its purpose."""
        instructions = _extract_instructions(_get_content_by_name(content_name))
        lower = instructions.lower()
        assert "purpose" in lower or "role" in lower or "you are" in lower, (
            f"{content_name} must describe agent's purpose"
        )

    @pytest.mark.parametrize("content_name", [
        "TEST_AGENT_MD_CONTENT",
        "IMPLEMENTATION_AGENT_MD_CONTENT",
        "COVERAGE_REVIEW_AGENT_MD_CONTENT",
    ])
    def test_describes_methodology(self, content_name):
        """Each agent definition must describe its methodology."""
        instructions = _extract_instructions(_get_content_by_name(content_name))
        lower = instructions.lower()
        has_methodology = (
            "methodolog" in lower
            or "step" in lower
            or "process" in lower
            or "procedure" in lower
            or "approach" in lower
            or "how" in lower
        )
        assert has_methodology, (
            f"{content_name} must describe agent's methodology"
        )

    @pytest.mark.parametrize("content_name", [
        "TEST_AGENT_MD_CONTENT",
        "IMPLEMENTATION_AGENT_MD_CONTENT",
        "COVERAGE_REVIEW_AGENT_MD_CONTENT",
    ])
    def test_describes_input_output(self, content_name):
        """Each agent definition must describe input/output format."""
        instructions = _extract_instructions(_get_content_by_name(content_name))
        lower = instructions.lower()
        has_io = (
            "input" in lower
            or "output" in lower
            or "receive" in lower
            or "produce" in lower
            or "format" in lower
        )
        assert has_io, (
            f"{content_name} must describe input/output format"
        )

    @pytest.mark.parametrize("content_name", [
        "TEST_AGENT_MD_CONTENT",
        "IMPLEMENTATION_AGENT_MD_CONTENT",
        "COVERAGE_REVIEW_AGENT_MD_CONTENT",
    ])
    def test_describes_constraints(self, content_name):
        """Each agent definition must describe its constraints."""
        instructions = _extract_instructions(_get_content_by_name(content_name))
        lower = instructions.lower()
        has_constraints = (
            "constraint" in lower
            or "must not" in lower
            or "do not" in lower
            or "never" in lower
            or "restriction" in lower
            or "requirement" in lower
        )
        assert has_constraints, (
            f"{content_name} must describe agent's constraints"
        )

    @pytest.mark.parametrize("content_name", [
        "TEST_AGENT_MD_CONTENT",
        "IMPLEMENTATION_AGENT_MD_CONTENT",
        "COVERAGE_REVIEW_AGENT_MD_CONTENT",
    ])
    def test_describes_terminal_status(self, content_name):
        """Each agent definition must describe its terminal status line(s)."""
        instructions = _extract_instructions(_get_content_by_name(content_name))
        lower = instructions.lower()
        has_status = (
            "terminal status" in lower
            or "status line" in lower
            or "_COMPLETE" in instructions
        )
        assert has_status, (
            f"{content_name} must describe terminal status line(s)"
        )


# ===========================================================================
# SECTION 11: Agent definitions are not placeholders
# ===========================================================================

class TestNotPlaceholder:
    """Verify that the instructions are detailed enough for autonomous operation,
    not just a skeleton or placeholder."""

    # DATA ASSUMPTION: A meaningful agent definition should have at least 500
    # characters of instructions based on the pattern seen in other agent
    # definitions (unit 13, unit 14 have ~1000+ characters each).

    @pytest.mark.parametrize("content_name", [
        "TEST_AGENT_MD_CONTENT",
        "IMPLEMENTATION_AGENT_MD_CONTENT",
        "COVERAGE_REVIEW_AGENT_MD_CONTENT",
    ])
    def test_instructions_are_substantial(self, content_name):
        """Agent instructions must be substantial (>500 chars), not a skeleton."""
        instructions = _extract_instructions(_get_content_by_name(content_name))
        assert len(instructions) > 500, (
            f"{content_name} instructions should be >500 chars for autonomous "
            f"agent operation, got {len(instructions)}"
        )

    @pytest.mark.parametrize("content_name", [
        "TEST_AGENT_MD_CONTENT",
        "IMPLEMENTATION_AGENT_MD_CONTENT",
        "COVERAGE_REVIEW_AGENT_MD_CONTENT",
    ])
    def test_instructions_have_multiple_sections(self, content_name):
        """Agent instructions should have multiple sections (headings)."""
        instructions = _extract_instructions(_get_content_by_name(content_name))
        heading_count = instructions.count("\n#")
        assert heading_count >= 2, (
            f"{content_name} should have at least 2 section headings for "
            f"comprehensive instructions, got {heading_count}"
        )


# ===========================================================================
# SECTION 12: Specific agent-level contract details
# ===========================================================================

class TestTestAgentSyntheticDataContract:
    """The test agent must specifically require synthetic data assumption declarations."""

    def test_mentions_data_assumption_format(self):
        """Test agent instructions should mention the DATA ASSUMPTION format."""
        instructions = _extract_instructions(_get_md_content("TEST_AGENT_MD_CONTENT"))
        # The blueprint says: "Test agent must declare synthetic data assumptions"
        lower = instructions.lower()
        assert "data assumption" in lower or ("assumption" in lower and "data" in lower), (
            "Test agent must reference DATA ASSUMPTION declarations"
        )


class TestImplementationAgentHintConflict:
    """The implementation agent must handle hint-blueprint conflicts."""

    def test_mentions_hint(self):
        """Implementation agent must discuss hints."""
        instructions = _extract_instructions(_get_md_content("IMPLEMENTATION_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "hint" in lower, (
            "Implementation agent must discuss hint handling"
        )

    def test_mentions_conflict_protocol(self):
        """Implementation agent must specify HINT_BLUEPRINT_CONFLICT protocol."""
        instructions = _extract_instructions(_get_md_content("IMPLEMENTATION_AGENT_MD_CONTENT"))
        assert "HINT_BLUEPRINT_CONFLICT" in instructions, (
            "Implementation agent must specify HINT_BLUEPRINT_CONFLICT status"
        )


class TestCoverageReviewValidation:
    """The coverage review agent must validate new tests as meaningful."""

    def test_mentions_notimplementederror_or_stub_validation(self):
        """Coverage review must reference stub/NotImplementedError validation."""
        instructions = _extract_instructions(_get_md_content("COVERAGE_REVIEW_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        has_validation_ref = (
            "notimplementederror" in lower
            or "stub" in lower
            or "meaningful" in lower
            or "right reason" in lower
        )
        assert has_validation_ref, (
            "Coverage review must reference meaningful test validation"
        )


# ===========================================================================
# SECTION 13: Module exports completeness
# ===========================================================================

class TestModuleExports:
    """Verify that the module exports all expected names."""

    def test_all_nine_constants_importable(self):
        """All nine constants from the blueprint must be importable."""
        import svp.scripts.construction_agent_definitions as mod
        expected_names = [
            "TEST_AGENT_FRONTMATTER",
            "IMPLEMENTATION_AGENT_FRONTMATTER",
            "COVERAGE_REVIEW_AGENT_FRONTMATTER",
            "TEST_AGENT_STATUS",
            "IMPLEMENTATION_AGENT_STATUS",
            "COVERAGE_REVIEW_STATUS",
            "TEST_AGENT_MD_CONTENT",
            "IMPLEMENTATION_AGENT_MD_CONTENT",
            "COVERAGE_REVIEW_AGENT_MD_CONTENT",
        ]
        for name in expected_names:
            assert hasattr(mod, name), f"Module must export {name}"


# ===========================================================================
# SECTION 14: Coverage gap tests -- upstream contracts and terminal statuses
# ===========================================================================

class TestImplementationAgentUpstreamContracts:
    """Verify that the Implementation Agent instructions mention upstream
    contracts/dependencies, as required by the blueprint behavioral contract:
    'Receives unit definition and upstream contracts from blueprint.'

    This was a gap: the Test Agent had test_instructions_mention_upstream_contracts
    in Section 6, but the Implementation Agent Section 7 had no equivalent test.
    """

    # DATA ASSUMPTION: Keywords checked are the same set used in the Test Agent's
    # equivalent test (Section 6, test_instructions_mention_upstream_contracts),
    # now applied to the Implementation Agent.

    def test_instructions_reference_upstream_dependencies(self):
        """Implementation agent instructions must reference upstream
        dependencies to satisfy the blueprint contract that it 'receives
        unit definition and upstream contracts from blueprint.'"""
        instructions = _extract_instructions(_get_md_content("IMPLEMENTATION_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "upstream" in lower or "dependencies" in lower, (
            "Implementation agent instructions must reference upstream "
            "dependencies (blueprint says it receives upstream contracts)"
        )


class TestCoverageReviewAgentUpstreamContracts:
    """Verify that the Coverage Review Agent instructions mention upstream
    contracts/dependencies, as required by the blueprint behavioral contract:
    'Receives blueprint unit definition, upstream contracts, and passing
    test suite.'

    This was a gap: neither Section 8 nor Section 12 tested that the
    Coverage Review Agent references upstream contracts in its instructions.
    """

    # DATA ASSUMPTION: Keywords checked are the same set used in the Test Agent's
    # equivalent test (Section 6, test_instructions_mention_upstream_contracts),
    # now applied to the Coverage Review Agent.

    def test_instructions_reference_upstream_dependencies(self):
        """Coverage review agent instructions must reference upstream
        dependencies to satisfy the blueprint contract that it 'receives
        blueprint unit definition, upstream contracts, and passing test suite.'"""
        instructions = _extract_instructions(_get_md_content("COVERAGE_REVIEW_AGENT_MD_CONTENT"))
        lower = instructions.lower()
        assert "upstream" in lower or "dependencies" in lower, (
            "Coverage review agent instructions must reference upstream "
            "dependencies (blueprint says it receives upstream contracts)"
        )


class TestCoverageReviewBothTerminalStatusesPresent:
    """Verify that the Coverage Review Agent instructions contain BOTH
    specific terminal status variants, not just the common COVERAGE_COMPLETE
    prefix.

    Blueprint specifies two terminal statuses:
    - COVERAGE_COMPLETE: no gaps
    - COVERAGE_COMPLETE: tests added

    The existing tests in Section 8 (test_instructions_mention_terminal_status_no_gaps
    and test_instructions_mention_terminal_status_tests_added) both fall back to
    checking just 'COVERAGE_COMPLETE' as an alternative, which means they pass
    even if only one variant is present. This test verifies both are present.
    """

    # DATA ASSUMPTION: Both terminal status strings are taken verbatim from the
    # blueprint Tier 2 Signatures and Tier 3 Behavioral Contracts.

    def test_instructions_contain_no_gaps_status_specifically(self):
        """Coverage review instructions must contain the exact string
        'COVERAGE_COMPLETE: no gaps'."""
        instructions = _extract_instructions(_get_md_content("COVERAGE_REVIEW_AGENT_MD_CONTENT"))
        assert "COVERAGE_COMPLETE: no gaps" in instructions, (
            "Coverage review agent instructions must contain the exact "
            "terminal status 'COVERAGE_COMPLETE: no gaps'"
        )

    def test_instructions_contain_tests_added_status_specifically(self):
        """Coverage review instructions must contain the exact string
        'COVERAGE_COMPLETE: tests added'."""
        instructions = _extract_instructions(_get_md_content("COVERAGE_REVIEW_AGENT_MD_CONTENT"))
        assert "COVERAGE_COMPLETE: tests added" in instructions, (
            "Coverage review agent instructions must contain the exact "
            "terminal status 'COVERAGE_COMPLETE: tests added'"
        )


# ===========================================================================
# Helper functions
# ===========================================================================

def _get_content_by_name(name: str) -> str:
    """Return the MD content constant by name."""
    return _get_md_content(name)


def _extract_frontmatter_block(md_content: str) -> str:
    """Extract the raw frontmatter text between the two --- delimiters."""
    assert md_content.startswith("---\n")
    second_delim = md_content.index("---\n", 4)
    return md_content[4:second_delim]


def _extract_instructions(md_content: str) -> str:
    """Extract the behavioral instructions after the YAML frontmatter."""
    assert md_content.startswith("---\n")
    second_delim = md_content.index("---\n", 4)
    return md_content[second_delim + 4:]

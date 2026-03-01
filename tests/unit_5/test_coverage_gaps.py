"""
Additional coverage tests for Unit 5: Blueprint Extractor

These tests fill gaps identified during coverage review, ensuring all
behavioral contracts, invariants, and error conditions from the blueprint
are exercised with strong assertions.

## Synthetic Data Assumptions

DATA ASSUMPTION: Same blueprint Markdown conventions as the main test file.
Uses the same _make_unit_block and _make_blueprint helpers.

DATA ASSUMPTION: "Full definition" in build_unit_context includes all
fields: description, signatures, invariants, error_conditions,
behavioral_contracts.

DATA ASSUMPTION: The context produced by build_unit_context places the
unit's own definition before the upstream contract signatures section.
"""

import textwrap
from pathlib import Path
from typing import List

import pytest

from svp.scripts.blueprint_extractor import (
    UnitDefinition,
    build_unit_context,
    extract_unit,
    extract_upstream_contracts,
    parse_blueprint,
)


# ---------------------------------------------------------------------------
# Helpers: synthetic blueprint generation (same as main test file)
# ---------------------------------------------------------------------------

def _make_blueprint(*unit_blocks: str) -> str:
    """Join multiple unit block strings into a complete blueprint document."""
    return "\n\n".join(unit_blocks)


def _make_unit_block(
    unit_number: int,
    unit_name: str,
    description: str = "A test unit.",
    signatures: str = "def foo() -> None: ...",
    invariants: str = "assert True",
    error_conditions: str = "- `ValueError`: when bad input",
    behavioral_contracts: str = "- `foo` does nothing.",
    dependencies_text: str = "None.",
) -> str:
    """
    Build a single unit section in the blueprint Markdown format.

    DATA ASSUMPTION: Uses the exact heading patterns described in the
    blueprint's behavioral contracts.
    """
    return textwrap.dedent(f"""\
    ## Unit {unit_number}: {unit_name}

    **Artifact category:** Python script

    ### Tier 1 -- Description

    {description}

    ### Tier 2 \u2014 Signatures

    ```python
    {signatures}
    ```

    ### Tier 2 \u2014 Invariants

    ```python
    {invariants}
    ```

    ### Tier 3 -- Error Conditions

    {error_conditions}

    ### Tier 3 -- Behavioral Contracts

    {behavioral_contracts}

    ### Tier 3 -- Dependencies

    {dependencies_text}
    """)


# DATA ASSUMPTION: Reusable unit blocks with distinctive content for
# verifying field-level extraction.
UNIT_1_BLOCK = _make_unit_block(
    unit_number=1,
    unit_name="Alpha Module",
    description="The alpha module provides base functionality.",
    signatures="def alpha_func(x: int) -> str: ...",
    invariants="assert x > 0",
    error_conditions="- `ValueError`: when x is negative",
    behavioral_contracts="- `alpha_func` converts x to string.",
    dependencies_text="None.",
)

UNIT_2_BLOCK = _make_unit_block(
    unit_number=2,
    unit_name="Beta Module",
    description="The beta module builds on alpha.",
    signatures="def beta_func(y: str) -> bool: ...",
    invariants="assert len(y) > 0",
    error_conditions="- `TypeError`: when y is not a string",
    behavioral_contracts="- `beta_func` validates the string.",
    dependencies_text="Unit 1.",
)

UNIT_3_BLOCK = _make_unit_block(
    unit_number=3,
    unit_name="Gamma Module",
    description="The gamma module depends on both alpha and beta.",
    signatures="def gamma_func(z: float) -> float: ...",
    invariants="assert z >= 0.0",
    error_conditions="- `ValueError`: when z is negative",
    behavioral_contracts="- `gamma_func` squares z.",
    dependencies_text="Unit 1, Unit 2.",
)

TWO_UNIT_BLUEPRINT = _make_blueprint(UNIT_1_BLOCK, UNIT_2_BLOCK)
THREE_UNIT_BLUEPRINT = _make_blueprint(UNIT_1_BLOCK, UNIT_2_BLOCK, UNIT_3_BLOCK)
SINGLE_UNIT_BLUEPRINT = _make_blueprint(UNIT_1_BLOCK)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def single_unit_file(tmp_path: Path) -> Path:
    bp = tmp_path / "blueprint.md"
    bp.write_text(SINGLE_UNIT_BLUEPRINT, encoding="utf-8")
    return bp


@pytest.fixture
def two_unit_file(tmp_path: Path) -> Path:
    bp = tmp_path / "blueprint.md"
    bp.write_text(TWO_UNIT_BLUEPRINT, encoding="utf-8")
    return bp


@pytest.fixture
def three_unit_file(tmp_path: Path) -> Path:
    bp = tmp_path / "blueprint.md"
    bp.write_text(THREE_UNIT_BLUEPRINT, encoding="utf-8")
    return bp


@pytest.fixture
def empty_blueprint_file(tmp_path: Path) -> Path:
    bp = tmp_path / "blueprint.md"
    bp.write_text("# Project Blueprint\n\nSome introductory text.\n", encoding="utf-8")
    return bp


# ---------------------------------------------------------------------------
# Gap 1: build_unit_context includes ALL fields of the unit's full definition
# ---------------------------------------------------------------------------

class TestBuildUnitContextFullDefinition:
    """
    The blueprint states: 'build_unit_context produces a formatted string
    containing the unit's full definition followed by all upstream contract
    signatures.' Existing tests only check for function names. These tests
    verify each field of the definition is present in the output.
    """

    def test_context_includes_description(self, single_unit_file: Path):
        """The built context should include the unit's Tier 1 description text."""
        # DATA ASSUMPTION: Unit 1's description is "The alpha module provides base functionality."
        result = build_unit_context(single_unit_file, 1)
        assert "alpha module provides base functionality" in result.lower()

    def test_context_includes_invariants(self, single_unit_file: Path):
        """The built context should include the unit's Tier 2 invariants."""
        # DATA ASSUMPTION: Unit 1's invariants contain "assert x > 0"
        result = build_unit_context(single_unit_file, 1)
        assert "assert x > 0" in result

    def test_context_includes_error_conditions(self, single_unit_file: Path):
        """The built context should include the unit's Tier 3 error conditions."""
        # DATA ASSUMPTION: Unit 1's error conditions contain "when x is negative"
        result = build_unit_context(single_unit_file, 1)
        assert "when x is negative" in result

    def test_context_includes_behavioral_contracts(self, single_unit_file: Path):
        """The built context should include the unit's Tier 3 behavioral contracts."""
        # DATA ASSUMPTION: Unit 1's behavioral contracts mention "alpha_func converts x to string"
        result = build_unit_context(single_unit_file, 1)
        assert "alpha_func" in result and "converts x to string" in result


# ---------------------------------------------------------------------------
# Gap 2: build_unit_context ordering -- unit definition before upstream
# ---------------------------------------------------------------------------

class TestBuildUnitContextOrdering:
    """
    The blueprint states the context has 'the unit's full definition followed
    by all upstream contract signatures.' This verifies the ordering.
    """

    def test_unit_definition_precedes_upstream_contracts(self, two_unit_file: Path):
        """
        For Unit 2 (depends on Unit 1), the context should have Unit 2's own
        signatures before Unit 1's upstream signatures.

        DATA ASSUMPTION: Unit 2 signatures contain 'beta_func' and Unit 1
        upstream signatures contain 'alpha_func'. The unit's own definition
        should appear first in the output.
        """
        result = build_unit_context(two_unit_file, 2)
        # Unit 2's own signature should appear before the upstream section
        beta_pos = result.index("beta_func")
        # The upstream section should contain alpha_func after beta_func
        alpha_pos = result.index("alpha_func")
        assert beta_pos < alpha_pos, (
            "Unit's own definition should precede upstream contract signatures"
        )

    def test_context_with_multiple_upstreams_ordering(self, three_unit_file: Path):
        """
        For Unit 3 (depends on 1 and 2), the unit's own definition should
        precede upstream contracts.

        DATA ASSUMPTION: Unit 3 contains 'gamma_func'. Upstream contracts
        include 'alpha_func' (Unit 1) and 'beta_func' (Unit 2).
        """
        result = build_unit_context(three_unit_file, 3)
        gamma_pos = result.index("gamma_func")
        alpha_pos = result.index("alpha_func")
        beta_pos = result.index("beta_func")
        assert gamma_pos < alpha_pos, (
            "Unit 3's definition should precede Unit 1's upstream contract"
        )
        assert gamma_pos < beta_pos, (
            "Unit 3's definition should precede Unit 2's upstream contract"
        )


# ---------------------------------------------------------------------------
# Gap 3: Negative unit_number for extract_upstream_contracts and build_unit_context
# ---------------------------------------------------------------------------

class TestNegativeUnitNumberAllFunctions:
    """
    The invariant 'unit_number >= 1' should be enforced by all functions
    that accept a unit_number. Existing tests cover 0 for all three and -1
    for extract_unit only. These cover -1 for the remaining functions.
    """

    def test_negative_unit_number_extract_upstream(self, single_unit_file: Path):
        """Pre-condition: negative unit_number must be rejected by extract_upstream_contracts."""
        with pytest.raises((ValueError, AssertionError)):
            extract_upstream_contracts(single_unit_file, -1)

    def test_negative_unit_number_build_context(self, single_unit_file: Path):
        """Pre-condition: negative unit_number must be rejected by build_unit_context."""
        with pytest.raises((ValueError, AssertionError)):
            build_unit_context(single_unit_file, -1)


# ---------------------------------------------------------------------------
# Gap 4: Strong assertion that 'None.' dependencies yields empty list
# ---------------------------------------------------------------------------

class TestNoneDependenciesStrong:
    """
    The existing test_no_dependencies_parsed uses a weak assertion that
    always passes. This verifies with a strict equality check.
    """

    def test_none_dependencies_yields_empty_list(self, single_unit_file: Path):
        """
        Unit 1 has 'None.' as its dependencies text. parse_blueprint should
        return an empty list for its dependencies, not None or a non-empty list.

        DATA ASSUMPTION: Unit 1's dependencies_text is 'None.'
        """
        result = parse_blueprint(single_unit_file)
        unit1 = result[0]
        assert unit1.dependencies == [], (
            f"Expected empty dependencies list for unit with 'None.' deps, got {unit1.dependencies!r}"
        )


# ---------------------------------------------------------------------------
# Gap 5: Strong assertions for parsed field content
# ---------------------------------------------------------------------------

class TestParsedFieldContentStrong:
    """
    The existing TestMarkdownParsing tests use 'or' fallback assertions that
    always pass (e.g., '... or len(unit.invariants) >= 0'). These tests
    use strong assertions to verify actual content extraction.
    """

    def test_description_contains_expected_text(self, single_unit_file: Path):
        """
        The description for Unit 1 should contain the text we set:
        'The alpha module provides base functionality.'

        DATA ASSUMPTION: The Tier 1 Description section content is faithfully extracted.
        """
        result = parse_blueprint(single_unit_file)
        unit = result[0]
        assert "alpha module provides base functionality" in unit.description.lower()

    def test_invariants_contain_expected_assertion(self, single_unit_file: Path):
        """
        The invariants for Unit 1 should contain 'assert x > 0'.

        DATA ASSUMPTION: The Tier 2 Invariants code block content is faithfully extracted.
        """
        result = parse_blueprint(single_unit_file)
        unit = result[0]
        assert "assert x > 0" in unit.invariants

    def test_error_conditions_contain_expected_text(self, single_unit_file: Path):
        """
        The error conditions for Unit 1 should contain 'ValueError' and
        'when x is negative'.

        DATA ASSUMPTION: The Tier 3 Error Conditions section is faithfully extracted.
        """
        result = parse_blueprint(single_unit_file)
        unit = result[0]
        assert "ValueError" in unit.error_conditions
        assert "when x is negative" in unit.error_conditions

    def test_behavioral_contracts_contain_expected_text(self, single_unit_file: Path):
        """
        The behavioral contracts for Unit 1 should mention 'alpha_func' and
        'converts x to string'.

        DATA ASSUMPTION: The Tier 3 Behavioral Contracts section is faithfully extracted.
        """
        result = parse_blueprint(single_unit_file)
        unit = result[0]
        assert "alpha_func" in unit.behavioral_contracts
        assert "converts x to string" in unit.behavioral_contracts


# ---------------------------------------------------------------------------
# Gap 6: extract_unit returns all parsed fields
# ---------------------------------------------------------------------------

class TestExtractUnitAllFields:
    """
    Existing tests for extract_unit only verify unit_number, unit_name, and
    signatures. This verifies all fields of the extracted UnitDefinition.
    """

    def test_extract_unit_has_description(self, two_unit_file: Path):
        """extract_unit should populate the description field."""
        result = extract_unit(two_unit_file, 1)
        assert "alpha module provides base functionality" in result.description.lower()

    def test_extract_unit_has_invariants(self, two_unit_file: Path):
        """extract_unit should populate the invariants field."""
        result = extract_unit(two_unit_file, 1)
        assert "assert x > 0" in result.invariants

    def test_extract_unit_has_error_conditions(self, two_unit_file: Path):
        """extract_unit should populate the error_conditions field."""
        result = extract_unit(two_unit_file, 1)
        assert "ValueError" in result.error_conditions

    def test_extract_unit_has_behavioral_contracts(self, two_unit_file: Path):
        """extract_unit should populate the behavioral_contracts field."""
        result = extract_unit(two_unit_file, 1)
        assert "alpha_func" in result.behavioral_contracts

    def test_extract_unit_has_dependencies(self, two_unit_file: Path):
        """extract_unit for Unit 2 should include its parsed dependencies."""
        result = extract_unit(two_unit_file, 2)
        assert 1 in result.dependencies


# ---------------------------------------------------------------------------
# Gap 7: FileNotFoundError message includes the path
# ---------------------------------------------------------------------------

class TestFileNotFoundErrorIncludesPath:
    """
    The blueprint specifies the error message format:
    'Blueprint file not found: {path}'. Existing tests match only the prefix.
    These tests verify the actual path is included in the message.
    """

    def test_parse_blueprint_error_includes_path(self, tmp_path: Path):
        """FileNotFoundError message should include the path to the missing file."""
        missing = tmp_path / "nonexistent_blueprint.md"
        with pytest.raises(FileNotFoundError, match=r"nonexistent_blueprint\.md"):
            parse_blueprint(missing)

    def test_extract_unit_error_includes_path(self, tmp_path: Path):
        """FileNotFoundError message should include the path to the missing file."""
        missing = tmp_path / "missing_file.md"
        with pytest.raises(FileNotFoundError, match=r"missing_file\.md"):
            extract_unit(missing, 1)

    def test_extract_upstream_error_includes_path(self, tmp_path: Path):
        """FileNotFoundError message should include the path to the missing file."""
        missing = tmp_path / "absent_blueprint.md"
        with pytest.raises(FileNotFoundError, match=r"absent_blueprint\.md"):
            extract_upstream_contracts(missing, 1)

    def test_build_context_error_includes_path(self, tmp_path: Path):
        """FileNotFoundError message should include the path to the missing file."""
        missing = tmp_path / "gone_blueprint.md"
        with pytest.raises(FileNotFoundError, match=r"gone_blueprint\.md"):
            build_unit_context(missing, 1)


# ---------------------------------------------------------------------------
# Gap 8: No parseable units error via extract_unit and build_unit_context
# ---------------------------------------------------------------------------

class TestNoParsableUnitsViaOtherFunctions:
    """
    The 'Blueprint has no parseable unit definitions' error is only tested
    via parse_blueprint. Since extract_unit and build_unit_context delegate
    to parse_blueprint, they should propagate this error.
    """

    def test_no_parseable_units_extract_unit(self, empty_blueprint_file: Path):
        """extract_unit should raise ValueError when blueprint has no unit headings."""
        with pytest.raises(ValueError, match=r"Blueprint has no parseable unit definitions"):
            extract_unit(empty_blueprint_file, 1)

    def test_no_parseable_units_extract_upstream(self, empty_blueprint_file: Path):
        """extract_upstream_contracts should raise ValueError when blueprint has no units."""
        with pytest.raises(ValueError, match=r"Blueprint has no parseable unit definitions"):
            extract_upstream_contracts(empty_blueprint_file, 1)

    def test_no_parseable_units_build_context(self, empty_blueprint_file: Path):
        """build_unit_context should raise ValueError when blueprint has no units."""
        with pytest.raises(ValueError, match=r"Blueprint has no parseable unit definitions"):
            build_unit_context(empty_blueprint_file, 1)


# ---------------------------------------------------------------------------
# Gap 9: extract_upstream_contracts returns signatures (raw Python content)
# ---------------------------------------------------------------------------

class TestUpstreamContractSignaturesContent:
    """
    The blueprint says extract_upstream_contracts returns 'Tier 2 signatures'
    for upstream units. Verify the signatures value contains the actual
    raw Python code block content.
    """

    def test_upstream_signatures_are_raw_python(self, three_unit_file: Path):
        """
        The signatures field in upstream contracts should contain the raw
        Python from the Tier 2 Signatures code block, not Markdown.

        DATA ASSUMPTION: Unit 1's Tier 2 signatures contain
        'def alpha_func(x: int) -> str: ...'
        """
        result = extract_upstream_contracts(three_unit_file, 3)
        # Find Unit 1's upstream entry
        unit1_entry = [e for e in result if str(e["unit_number"]) == "1" or e["unit_number"] == 1][0]
        # Should contain the full function stub, not just the name
        assert "def alpha_func(x: int) -> str" in unit1_entry["signatures"]

    def test_upstream_signatures_for_unit2(self, three_unit_file: Path):
        """
        Unit 3 depends on Unit 2. The upstream entry for Unit 2 should
        contain Unit 2's raw Python signatures.

        DATA ASSUMPTION: Unit 2's signatures contain 'def beta_func(y: str) -> bool: ...'
        """
        result = extract_upstream_contracts(three_unit_file, 3)
        unit2_entry = [e for e in result if str(e["unit_number"]) == "2" or e["unit_number"] == 2][0]
        assert "def beta_func(y: str) -> bool" in unit2_entry["signatures"]

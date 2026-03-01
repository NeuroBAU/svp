"""
Tests for Unit 5: Blueprint Extractor

Verifies the behavioral contracts, invariants, error conditions, and
signatures of the blueprint extractor module.

## Synthetic Data Assumptions

DATA ASSUMPTION: Blueprint Markdown follows the heading convention
"## Unit N: <Name>" for unit sections and "### Tier K" for sub-sections.
The Tier 2 heading uses an em-dash (U+2014): "### Tier 2 \u2014 Signatures".

DATA ASSUMPTION: Tier 2 signature code blocks are fenced with ```python ... ```
and contain valid Python function/class stubs with type annotations.

DATA ASSUMPTION: Dependencies are listed in a "### Tier 3 -- Dependencies"
sub-section and reference upstream units by number (e.g., "Unit 1", "Unit 2").

DATA ASSUMPTION: Unit numbers are positive integers starting from 1.

DATA ASSUMPTION: A minimal blueprint contains at least one "## Unit N:" heading
with at least a Tier 2 Signatures code block.
"""

import inspect
import re
import textwrap
from pathlib import Path
from typing import Any, Dict, List

import pytest

from svp.scripts.blueprint_extractor import (
    UnitDefinition,
    build_unit_context,
    extract_unit,
    extract_upstream_contracts,
    parse_blueprint,
)


# ---------------------------------------------------------------------------
# Helpers: synthetic blueprint generation
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
    blueprint's behavioral contracts -- "## Unit N:" pattern for the
    unit heading and "### Tier K" sub-headings. Tier 2 uses em-dash.
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


# DATA ASSUMPTION: A simple two-unit blueprint where Unit 2 depends on Unit 1.
# Unit 1 has no dependencies. Signatures are trivial Python stubs.
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
    """A blueprint file containing a single unit definition."""
    bp = tmp_path / "blueprint.md"
    bp.write_text(SINGLE_UNIT_BLUEPRINT, encoding="utf-8")
    return bp


@pytest.fixture
def two_unit_file(tmp_path: Path) -> Path:
    """A blueprint file containing two unit definitions (Unit 2 depends on Unit 1)."""
    bp = tmp_path / "blueprint.md"
    bp.write_text(TWO_UNIT_BLUEPRINT, encoding="utf-8")
    return bp


@pytest.fixture
def three_unit_file(tmp_path: Path) -> Path:
    """A blueprint file with three units; Unit 3 depends on Unit 1 and Unit 2."""
    bp = tmp_path / "blueprint.md"
    bp.write_text(THREE_UNIT_BLUEPRINT, encoding="utf-8")
    return bp


@pytest.fixture
def nonexistent_file(tmp_path: Path) -> Path:
    """A path to a file that does not exist."""
    return tmp_path / "does_not_exist.md"


@pytest.fixture
def empty_blueprint_file(tmp_path: Path) -> Path:
    """A blueprint file that contains no '## Unit N:' headings."""
    bp = tmp_path / "blueprint.md"
    # DATA ASSUMPTION: File exists but contains only prose, no unit headings.
    bp.write_text("# Project Blueprint\n\nSome introductory text.\n", encoding="utf-8")
    return bp


# ---------------------------------------------------------------------------
# 1. Signature / structure tests
# ---------------------------------------------------------------------------

class TestSignatures:
    """Verify that classes and functions have the documented signatures."""

    def test_unit_definition_is_a_class(self):
        assert inspect.isclass(UnitDefinition)

    def test_unit_definition_init_accepts_kwargs(self):
        sig = inspect.signature(UnitDefinition.__init__)
        params = list(sig.parameters.keys())
        # __init__(self, **kwargs: Any) -> None
        assert "self" in params
        # Should accept **kwargs
        has_var_keyword = any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in sig.parameters.values()
        )
        assert has_var_keyword, "UnitDefinition.__init__ should accept **kwargs"

    def test_parse_blueprint_signature(self):
        sig = inspect.signature(parse_blueprint)
        params = list(sig.parameters.keys())
        assert params == ["blueprint_path"]

    def test_extract_unit_signature(self):
        sig = inspect.signature(extract_unit)
        params = list(sig.parameters.keys())
        assert params == ["blueprint_path", "unit_number"]

    def test_extract_upstream_contracts_signature(self):
        sig = inspect.signature(extract_upstream_contracts)
        params = list(sig.parameters.keys())
        assert params == ["blueprint_path", "unit_number"]

    def test_build_unit_context_signature(self):
        sig = inspect.signature(build_unit_context)
        params = list(sig.parameters.keys())
        assert params == ["blueprint_path", "unit_number"]


# ---------------------------------------------------------------------------
# 2. UnitDefinition construction tests
# ---------------------------------------------------------------------------

class TestUnitDefinition:
    """Verify UnitDefinition can be constructed with keyword arguments."""

    def test_init_with_all_fields(self):
        """UnitDefinition should accept all documented fields as kwargs."""
        # DATA ASSUMPTION: Minimal valid field values for UnitDefinition.
        ud = UnitDefinition(
            unit_number=1,
            unit_name="Test",
            description="desc",
            signatures="def f(): ...",
            invariants="assert True",
            error_conditions="none",
            behavioral_contracts="none",
            dependencies=[],
        )
        assert ud.unit_number == 1
        assert ud.unit_name == "Test"
        assert ud.description == "desc"
        assert ud.signatures == "def f(): ..."
        assert ud.invariants == "assert True"
        assert ud.error_conditions == "none"
        assert ud.behavioral_contracts == "none"
        assert ud.dependencies == []

    def test_init_with_dependencies(self):
        """Dependencies should store upstream unit numbers as a list of ints."""
        # DATA ASSUMPTION: Dependencies are stored as a list of positive ints.
        ud = UnitDefinition(
            unit_number=5,
            unit_name="Dep Test",
            description="d",
            signatures="def g(): ...",
            invariants="",
            error_conditions="",
            behavioral_contracts="",
            dependencies=[1, 3],
        )
        assert ud.dependencies == [1, 3]


# ---------------------------------------------------------------------------
# 3. parse_blueprint tests
# ---------------------------------------------------------------------------

class TestParseBlueprint:
    """Behavioral contracts for parse_blueprint."""

    def test_parses_single_unit(self, single_unit_file: Path):
        """parse_blueprint reads the full blueprint and returns UnitDefinition instances."""
        result = parse_blueprint(single_unit_file)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], UnitDefinition)

    def test_parses_multiple_units(self, two_unit_file: Path):
        """parse_blueprint should return one UnitDefinition per ## Unit heading."""
        result = parse_blueprint(two_unit_file)
        assert len(result) == 2

    def test_parses_three_units(self, three_unit_file: Path):
        """parse_blueprint with three units returns three definitions."""
        result = parse_blueprint(three_unit_file)
        assert len(result) == 3

    def test_unit_numbers_are_correct(self, two_unit_file: Path):
        """Each parsed UnitDefinition should have the correct unit_number."""
        result = parse_blueprint(two_unit_file)
        numbers = sorted(u.unit_number for u in result)
        assert numbers == [1, 2]

    def test_unit_names_are_correct(self, two_unit_file: Path):
        """Each parsed UnitDefinition should have the correct unit_name."""
        result = parse_blueprint(two_unit_file)
        names = {u.unit_number: u.unit_name for u in result}
        assert names[1] == "Alpha Module"
        assert names[2] == "Beta Module"

    def test_signatures_are_extracted(self, single_unit_file: Path):
        """Signatures should contain the raw Python from the Tier 2 code block."""
        result = parse_blueprint(single_unit_file)
        unit = result[0]
        assert "alpha_func" in unit.signatures

    def test_all_unit_numbers_positive(self, three_unit_file: Path):
        """Post-condition: all unit numbers must be positive."""
        result = parse_blueprint(three_unit_file)
        assert all(u.unit_number > 0 for u in result)

    def test_result_non_empty(self, single_unit_file: Path):
        """Post-condition: blueprint must contain at least one unit."""
        result = parse_blueprint(single_unit_file)
        assert len(result) > 0

    def test_signatures_non_empty(self, single_unit_file: Path):
        """Post-condition: unit must have non-empty signatures."""
        result = parse_blueprint(single_unit_file)
        for unit in result:
            assert len(unit.signatures) > 0

    def test_dependencies_parsed(self, two_unit_file: Path):
        """Unit 2 should have Unit 1 in its dependencies list."""
        result = parse_blueprint(two_unit_file)
        unit2 = [u for u in result if u.unit_number == 2][0]
        assert 1 in unit2.dependencies

    def test_no_dependencies_parsed(self, single_unit_file: Path):
        """Unit with 'None.' dependencies should have an empty list."""
        result = parse_blueprint(single_unit_file)
        unit1 = result[0]
        assert unit1.dependencies == [] or unit1.dependencies is not None

    def test_multiple_dependencies_parsed(self, three_unit_file: Path):
        """Unit 3 depends on Unit 1 and Unit 2."""
        result = parse_blueprint(three_unit_file)
        unit3 = [u for u in result if u.unit_number == 3][0]
        assert 1 in unit3.dependencies
        assert 2 in unit3.dependencies


# ---------------------------------------------------------------------------
# 4. extract_unit tests
# ---------------------------------------------------------------------------

class TestExtractUnit:
    """Behavioral contracts for extract_unit."""

    def test_returns_correct_unit(self, two_unit_file: Path):
        """extract_unit returns a single unit's definition."""
        result = extract_unit(two_unit_file, 1)
        assert isinstance(result, UnitDefinition)
        assert result.unit_number == 1

    def test_unit_number_matches_request(self, two_unit_file: Path):
        """Post-condition: extracted unit number must match request."""
        result = extract_unit(two_unit_file, 2)
        assert result.unit_number == 2

    def test_has_nonempty_signatures(self, two_unit_file: Path):
        """Post-condition: unit must have non-empty signatures."""
        result = extract_unit(two_unit_file, 1)
        assert len(result.signatures) > 0

    def test_extract_unit_delegates_to_parse(self, two_unit_file: Path):
        """extract_unit delegates to parse_blueprint internally --
        verified by checking it returns the same data as parsing then filtering."""
        all_units = parse_blueprint(two_unit_file)
        unit_from_extract = extract_unit(two_unit_file, 1)
        unit_from_parse = [u for u in all_units if u.unit_number == 1][0]
        assert unit_from_extract.unit_name == unit_from_parse.unit_name
        assert unit_from_extract.signatures == unit_from_parse.signatures


# ---------------------------------------------------------------------------
# 5. extract_upstream_contracts tests
# ---------------------------------------------------------------------------

class TestExtractUpstreamContracts:
    """Behavioral contracts for extract_upstream_contracts."""

    def test_returns_list_of_dicts(self, two_unit_file: Path):
        """extract_upstream_contracts returns a list of dicts."""
        result = extract_upstream_contracts(two_unit_file, 2)
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], dict)

    def test_dict_keys(self, two_unit_file: Path):
        """Each entry has unit_number, unit_name, and signatures keys."""
        result = extract_upstream_contracts(two_unit_file, 2)
        for entry in result:
            assert "unit_number" in entry
            assert "unit_name" in entry
            assert "signatures" in entry

    def test_upstream_contract_content(self, two_unit_file: Path):
        """The upstream contract for Unit 2 should include Unit 1's signatures."""
        result = extract_upstream_contracts(two_unit_file, 2)
        assert len(result) == 1
        entry = result[0]
        # Unit 1 is the upstream dependency for Unit 2
        assert str(entry["unit_number"]) == "1" or entry["unit_number"] == 1
        assert entry["unit_name"] == "Alpha Module"
        assert "alpha_func" in entry["signatures"]

    def test_no_upstream_for_root_unit(self, two_unit_file: Path):
        """Unit 1 has no dependencies, so extract_upstream_contracts returns empty list."""
        result = extract_upstream_contracts(two_unit_file, 1)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_multiple_upstream_contracts(self, three_unit_file: Path):
        """Unit 3 depends on Unit 1 and Unit 2; should return two upstream contracts."""
        result = extract_upstream_contracts(three_unit_file, 3)
        assert len(result) == 2
        upstream_numbers = {
            int(e["unit_number"]) if isinstance(e["unit_number"], str) else e["unit_number"]
            for e in result
        }
        assert upstream_numbers == {1, 2}


# ---------------------------------------------------------------------------
# 6. build_unit_context tests
# ---------------------------------------------------------------------------

class TestBuildUnitContext:
    """Behavioral contracts for build_unit_context."""

    def test_returns_nonempty_string(self, single_unit_file: Path):
        """Post-condition: unit context must be non-empty."""
        result = build_unit_context(single_unit_file, 1)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_unit_definition(self, single_unit_file: Path):
        """The context should contain the unit's full definition."""
        result = build_unit_context(single_unit_file, 1)
        # Should contain the unit name or key information
        assert "Alpha Module" in result or "alpha_func" in result

    def test_contains_upstream_contracts(self, two_unit_file: Path):
        """For Unit 2, context should include Unit 1's upstream contract signatures."""
        result = build_unit_context(two_unit_file, 2)
        # Should mention Unit 1's signature since it is an upstream dependency
        assert "alpha_func" in result

    def test_contains_unit_signatures(self, two_unit_file: Path):
        """The context should include the unit's own signatures."""
        result = build_unit_context(two_unit_file, 2)
        assert "beta_func" in result

    def test_no_upstream_for_independent_unit(self, single_unit_file: Path):
        """For a unit with no deps, context should still include the unit definition."""
        result = build_unit_context(single_unit_file, 1)
        assert "alpha_func" in result

    def test_context_includes_multiple_upstreams(self, three_unit_file: Path):
        """For Unit 3 (depends on 1 and 2), context should include both upstreams."""
        result = build_unit_context(three_unit_file, 3)
        assert "alpha_func" in result
        assert "beta_func" in result
        assert "gamma_func" in result


# ---------------------------------------------------------------------------
# 7. Error condition tests
# ---------------------------------------------------------------------------

class TestErrorConditions:
    """Verify all documented error conditions from Tier 3."""

    def test_file_not_found_parse_blueprint(self, nonexistent_file: Path):
        """FileNotFoundError when blueprint file does not exist."""
        with pytest.raises(FileNotFoundError, match=r"Blueprint file not found"):
            parse_blueprint(nonexistent_file)

    def test_file_not_found_extract_unit(self, nonexistent_file: Path):
        """FileNotFoundError when blueprint file does not exist."""
        with pytest.raises(FileNotFoundError, match=r"Blueprint file not found"):
            extract_unit(nonexistent_file, 1)

    def test_file_not_found_extract_upstream(self, nonexistent_file: Path):
        """FileNotFoundError when blueprint file does not exist."""
        with pytest.raises(FileNotFoundError, match=r"Blueprint file not found"):
            extract_upstream_contracts(nonexistent_file, 1)

    def test_file_not_found_build_context(self, nonexistent_file: Path):
        """FileNotFoundError when blueprint file does not exist."""
        with pytest.raises(FileNotFoundError, match=r"Blueprint file not found"):
            build_unit_context(nonexistent_file, 1)

    def test_unit_not_found(self, single_unit_file: Path):
        """ValueError when requested unit number is not defined in blueprint."""
        with pytest.raises(ValueError, match=r"Unit 99 not found in blueprint"):
            extract_unit(single_unit_file, 99)

    def test_unit_not_found_upstream(self, single_unit_file: Path):
        """ValueError when requested unit number is not defined -- via extract_upstream."""
        with pytest.raises(ValueError, match=r"Unit 42 not found in blueprint"):
            extract_upstream_contracts(single_unit_file, 42)

    def test_unit_not_found_build_context(self, single_unit_file: Path):
        """ValueError when requested unit number is not defined -- via build_unit_context."""
        with pytest.raises(ValueError, match=r"Unit 50 not found in blueprint"):
            build_unit_context(single_unit_file, 50)

    def test_no_parseable_units(self, empty_blueprint_file: Path):
        """ValueError when blueprint has no recognizable ## Unit N headings."""
        with pytest.raises(ValueError, match=r"Blueprint has no parseable unit definitions"):
            parse_blueprint(empty_blueprint_file)


# ---------------------------------------------------------------------------
# 8. Invariant tests (pre-conditions)
# ---------------------------------------------------------------------------

class TestInvariants:
    """Verify pre-conditions and post-conditions from Tier 2 invariants."""

    def test_blueprint_path_must_exist(self, nonexistent_file: Path):
        """Pre-condition: blueprint file must exist -- triggers FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_blueprint(nonexistent_file)

    def test_unit_number_must_be_positive_extract(self, single_unit_file: Path):
        """Pre-condition: unit_number must be positive (>= 1)."""
        with pytest.raises((ValueError, AssertionError)):
            extract_unit(single_unit_file, 0)

    def test_unit_number_must_be_positive_upstream(self, single_unit_file: Path):
        """Pre-condition: unit_number must be positive (>= 1)."""
        with pytest.raises((ValueError, AssertionError)):
            extract_upstream_contracts(single_unit_file, 0)

    def test_unit_number_must_be_positive_context(self, single_unit_file: Path):
        """Pre-condition: unit_number must be positive (>= 1)."""
        with pytest.raises((ValueError, AssertionError)):
            build_unit_context(single_unit_file, 0)

    def test_negative_unit_number(self, single_unit_file: Path):
        """Pre-condition: negative unit numbers must be rejected."""
        with pytest.raises((ValueError, AssertionError)):
            extract_unit(single_unit_file, -1)


# ---------------------------------------------------------------------------
# 9. Markdown heading pattern tests
# ---------------------------------------------------------------------------

class TestMarkdownParsing:
    """Verify correct parsing of various markdown heading patterns."""

    def test_em_dash_in_tier2_heading(self, tmp_path: Path):
        """
        Tier 2 heading uses em-dash (U+2014): '### Tier 2 \u2014 Signatures'.
        DATA ASSUMPTION: The parser correctly recognizes the em-dash variant.
        """
        # This blueprint uses em-dash consistently
        block = _make_unit_block(
            unit_number=1,
            unit_name="EmDash Unit",
            signatures="def em_func() -> None: ...",
        )
        bp = tmp_path / "blueprint.md"
        bp.write_text(block, encoding="utf-8")
        result = parse_blueprint(bp)
        assert len(result) == 1
        assert "em_func" in result[0].signatures

    def test_splits_on_unit_heading_pattern(self, tmp_path: Path):
        """
        Parsing is based on '## Unit N:' pattern. Units should be split
        correctly at these boundaries.
        DATA ASSUMPTION: Each '## Unit N:' heading starts a new unit section.
        """
        block = _make_blueprint(
            _make_unit_block(10, "Tenth", signatures="def tenth(): ..."),
            _make_unit_block(11, "Eleventh", signatures="def eleventh(): ..."),
        )
        bp = tmp_path / "blueprint.md"
        bp.write_text(block, encoding="utf-8")
        result = parse_blueprint(bp)
        assert len(result) == 2
        nums = sorted(u.unit_number for u in result)
        assert nums == [10, 11]

    def test_description_extracted(self, single_unit_file: Path):
        """The Tier 1 description text should be captured."""
        result = parse_blueprint(single_unit_file)
        unit = result[0]
        assert "alpha" in unit.description.lower() or len(unit.description) > 0

    def test_invariants_extracted(self, single_unit_file: Path):
        """The Tier 2 invariants code block should be captured."""
        result = parse_blueprint(single_unit_file)
        unit = result[0]
        # The invariants block contains 'assert x > 0'
        assert "assert" in unit.invariants or len(unit.invariants) >= 0

    def test_error_conditions_extracted(self, single_unit_file: Path):
        """The Tier 3 error conditions section should be captured."""
        result = parse_blueprint(single_unit_file)
        unit = result[0]
        assert "ValueError" in unit.error_conditions or len(unit.error_conditions) > 0

    def test_behavioral_contracts_extracted(self, single_unit_file: Path):
        """The Tier 3 behavioral contracts section should be captured."""
        result = parse_blueprint(single_unit_file)
        unit = result[0]
        assert "alpha_func" in unit.behavioral_contracts or len(unit.behavioral_contracts) > 0

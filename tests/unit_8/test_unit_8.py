"""
Test suite for Unit 8: Blueprint Extractor.

Synthetic data assumptions:
- Blueprint directories are created as temporary directories via tmp_path fixtures.
- blueprint_prose.md files contain synthetic unit headings ("## Unit N: Name")
  with known Tier 1 body text beneath each heading.
- blueprint_contracts.md files contain synthetic unit headings with
  "### Tier 2" and "### Tier 3" subsections containing known content.
- Tier 2 subsections include both em-dash ("### Tier 2 \u2014 Signatures") and
  plain suffix ("### Tier 2 -- Signatures") variants to test prefix matching.
- Code blocks in Tier 2 sections use triple backtick fences with language tags
  (```python, ```r, ```stan) or untagged (```) to test language detection and stripping.
- Dependencies are expressed as lists of integer unit numbers (e.g., [1, 2]).
- Machinery marker text "machinery: true" is embedded in Tier 1 prose for
  synthetic units representing machinery units (5, 6, 14, 15).
- Non-machinery units omit the "machinery: true" marker, verifying False default.
- Synthetic UnitDefinition instances are constructed manually for build_unit_context
  tests that do not require file parsing.
- Language mapping tests use code fences tagged python, r, stan, and untagged
  to verify the documented mapping and default behavior.
"""

from pathlib import Path

import pytest

from src.unit_8.stub import (
    UnitDefinition,
    build_unit_context,
    detect_code_block_language,
    extract_units,
)

# ---------------------------------------------------------------------------
# Helpers for creating synthetic blueprint files
# ---------------------------------------------------------------------------


def _write_prose(bp_dir: Path, units: list):
    """Write a synthetic blueprint_prose.md file.

    Each entry in units is a dict with keys: number, name, tier1_body.
    """
    lines = []
    for u in units:
        lines.append(f"## Unit {u['number']}: {u['name']}\n")
        lines.append(u["tier1_body"] + "\n\n")
    (bp_dir / "blueprint_prose.md").write_text("".join(lines))


def _write_contracts(bp_dir: Path, units: list, tier2_heading_style="em_dash"):
    """Write a synthetic blueprint_contracts.md file.

    Each entry in units is a dict with keys: number, name, tier2_body, tier3_body.
    tier2_heading_style: "em_dash" uses \u2014, "plain" uses --, "suffix" uses custom text.
    """
    lines = []
    for u in units:
        lines.append(f"## Unit {u['number']}: {u['name']}\n\n")
        if tier2_heading_style == "em_dash":
            lines.append("### Tier 2 \u2014 Signatures\n\n")
        elif tier2_heading_style == "plain":
            lines.append("### Tier 2 -- Signatures\n\n")
        else:
            lines.append(f"### Tier 2 {tier2_heading_style}\n\n")
        lines.append(u["tier2_body"] + "\n\n")
        lines.append("### Tier 3 -- Behavioral Contracts\n\n")
        lines.append(u["tier3_body"] + "\n\n")
    (bp_dir / "blueprint_contracts.md").write_text("".join(lines))


def _make_unit_def(
    number: int,
    name: str = "TestUnit",
    tier1: str = "Tier 1 text",
    tier2: str = "Tier 2 text",
    tier3: str = "Tier 3 text",
    dependencies: list = None,
    languages: set = None,
    machinery: bool = False,
) -> UnitDefinition:
    """Construct a synthetic UnitDefinition for non-parsing tests."""
    ud = UnitDefinition()
    ud.number = number
    ud.name = name
    ud.tier1 = tier1
    ud.tier2 = tier2
    ud.tier3 = tier3
    ud.dependencies = dependencies if dependencies is not None else []
    ud.languages = languages if languages is not None else {"python"}
    ud.machinery = machinery
    return ud


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def two_unit_blueprint(tmp_path):
    """Create a minimal blueprint directory with two units."""
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir()
    _write_prose(
        bp_dir,
        [
            {
                "number": 1,
                "name": "Core Config",
                "tier1_body": "This is unit 1 tier 1 prose.",
            },
            {
                "number": 2,
                "name": "Language Registry",
                "tier1_body": "This is unit 2 tier 1 prose.",
            },
        ],
    )
    _write_contracts(
        bp_dir,
        [
            {
                "number": 1,
                "name": "Core Config",
                "tier2_body": "```python\ndef load_config(): ...\n```",
                "tier3_body": "load_config returns a dict.",
            },
            {
                "number": 2,
                "name": "Language Registry",
                "tier2_body": "```python\nLANGUAGE_REGISTRY = {}\n```",
                "tier3_body": "Registry must contain python entry.",
            },
        ],
    )
    return bp_dir


@pytest.fixture
def machinery_blueprint(tmp_path):
    """Create a blueprint directory with machinery and non-machinery units."""
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir()
    _write_prose(
        bp_dir,
        [
            {
                "number": 3,
                "name": "Regular Unit",
                "tier1_body": "A regular unit with no special markers.",
            },
            {
                "number": 5,
                "name": "Pipeline State",
                "tier1_body": "Pipeline state management.\nmachinery: true\nHandles state transitions.",
            },
            {
                "number": 6,
                "name": "State Transitions",
                "tier1_body": "machinery: true\nState transition logic.",
            },
            {
                "number": 14,
                "name": "Routing",
                "tier1_body": "Routing dispatch.\nmachinery: true",
            },
            {
                "number": 15,
                "name": "Quality Gate",
                "tier1_body": "Gate evaluation.\nmachinery: true",
            },
        ],
    )
    _write_contracts(
        bp_dir,
        [
            {
                "number": 3,
                "name": "Regular Unit",
                "tier2_body": "```python\ndef foo(): ...\n```",
                "tier3_body": "foo does things.",
            },
            {
                "number": 5,
                "name": "Pipeline State",
                "tier2_body": "```python\ndef state(): ...\n```",
                "tier3_body": "State contract.",
            },
            {
                "number": 6,
                "name": "State Transitions",
                "tier2_body": "```python\ndef transition(): ...\n```",
                "tier3_body": "Transition contract.",
            },
            {
                "number": 14,
                "name": "Routing",
                "tier2_body": "```python\ndef route(): ...\n```",
                "tier3_body": "Routing contract.",
            },
            {
                "number": 15,
                "name": "Quality Gate",
                "tier2_body": "```python\ndef gate(): ...\n```",
                "tier3_body": "Gate contract.",
            },
        ],
    )
    return bp_dir


@pytest.fixture
def multi_language_blueprint(tmp_path):
    """Create a blueprint directory with multiple language code fences."""
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir()
    prose_content = (
        "## Unit 1: Multi Lang\n\n"
        "Some prose.\n\n"
        "```python\nx = 1\n```\n\n"
        "```r\ny <- 2\n```\n\n"
    )
    (bp_dir / "blueprint_prose.md").write_text(prose_content)
    contracts_content = (
        "## Unit 1: Multi Lang\n\n"
        "### Tier 2 \u2014 Signatures\n\n"
        "```python\ndef foo(): ...\n```\n\n"
        "```stan\nmodel {}\n```\n\n"
        "### Tier 3 -- Behavioral Contracts\n\n"
        "Some contracts.\n\n"
    )
    (bp_dir / "blueprint_contracts.md").write_text(contracts_content)
    return bp_dir


@pytest.fixture
def dependency_chain_blueprint(tmp_path):
    """Create a blueprint with units that have dependencies for context assembly tests."""
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir()
    _write_prose(
        bp_dir,
        [
            {"number": 1, "name": "Base", "tier1_body": "Base unit tier 1 content."},
            {
                "number": 2,
                "name": "Middle",
                "tier1_body": "Middle unit tier 1 content.",
            },
            {"number": 3, "name": "Top", "tier1_body": "Top unit tier 1 content."},
        ],
    )
    _write_contracts(
        bp_dir,
        [
            {
                "number": 1,
                "name": "Base",
                "tier2_body": "```python\ndef base_fn(): ...\n```",
                "tier3_body": "Base contracts here.",
            },
            {
                "number": 2,
                "name": "Middle",
                "tier2_body": "```python\ndef middle_fn(): ...\n```",
                "tier3_body": "Middle contracts here.",
            },
            {
                "number": 3,
                "name": "Top",
                "tier2_body": "```python\ndef top_fn(): ...\n```",
                "tier3_body": "Top contracts here.",
            },
        ],
    )
    return bp_dir


# ===========================================================================
# UnitDefinition dataclass
# ===========================================================================


class TestUnitDefinitionDataclass:
    """Tests for UnitDefinition dataclass fields and types."""

    def test_unit_definition_has_number_field(self):
        ud = _make_unit_def(number=7, name="Test")
        assert ud.number == 7

    def test_unit_definition_has_name_field(self):
        ud = _make_unit_def(number=1, name="CoreConfig")
        assert ud.name == "CoreConfig"

    def test_unit_definition_has_tier1_field(self):
        ud = _make_unit_def(number=1, tier1="Tier 1 content here")
        assert ud.tier1 == "Tier 1 content here"

    def test_unit_definition_has_tier2_field(self):
        ud = _make_unit_def(number=1, tier2="def foo(): ...")
        assert ud.tier2 == "def foo(): ..."

    def test_unit_definition_has_tier3_field(self):
        ud = _make_unit_def(number=1, tier3="Behavioral contracts")
        assert ud.tier3 == "Behavioral contracts"

    def test_unit_definition_has_dependencies_field(self):
        ud = _make_unit_def(number=3, dependencies=[1, 2])
        assert ud.dependencies == [1, 2]

    def test_unit_definition_has_languages_field(self):
        ud = _make_unit_def(number=1, languages={"python", "r"})
        assert ud.languages == {"python", "r"}

    def test_unit_definition_has_machinery_field(self):
        ud = _make_unit_def(number=5, machinery=True)
        assert ud.machinery is True

    def test_unit_definition_machinery_defaults_false(self):
        ud = _make_unit_def(number=1, machinery=False)
        assert ud.machinery is False


# ===========================================================================
# extract_units
# ===========================================================================


class TestExtractUnitsBasicParsing:
    """Tests for extract_units: basic heading detection and content extraction."""

    def test_returns_list(self, two_unit_blueprint):
        result = extract_units(two_unit_blueprint)
        assert isinstance(result, list)

    def test_extracts_correct_number_of_units(self, two_unit_blueprint):
        result = extract_units(two_unit_blueprint)
        assert len(result) == 2

    def test_each_element_is_unit_definition(self, two_unit_blueprint):
        result = extract_units(two_unit_blueprint)
        for ud in result:
            assert isinstance(ud, UnitDefinition)

    def test_unit_number_parsed_from_heading(self, two_unit_blueprint):
        result = extract_units(two_unit_blueprint)
        numbers = [ud.number for ud in result]
        assert 1 in numbers
        assert 2 in numbers

    def test_unit_name_parsed_from_heading(self, two_unit_blueprint):
        result = extract_units(two_unit_blueprint)
        names = {ud.number: ud.name for ud in result}
        assert names[1] == "Core Config"
        assert names[2] == "Language Registry"


class TestExtractUnitsSortOrder:
    """Tests for extract_units: return list sorted by unit number."""

    def test_results_sorted_by_unit_number(self, tmp_path):
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        # Write units out of order in the files
        _write_prose(
            bp_dir,
            [
                {"number": 3, "name": "Third", "tier1_body": "Third prose."},
                {"number": 1, "name": "First", "tier1_body": "First prose."},
                {"number": 2, "name": "Second", "tier1_body": "Second prose."},
            ],
        )
        _write_contracts(
            bp_dir,
            [
                {
                    "number": 3,
                    "name": "Third",
                    "tier2_body": "```python\n...\n```",
                    "tier3_body": "Third.",
                },
                {
                    "number": 1,
                    "name": "First",
                    "tier2_body": "```python\n...\n```",
                    "tier3_body": "First.",
                },
                {
                    "number": 2,
                    "name": "Second",
                    "tier2_body": "```python\n...\n```",
                    "tier3_body": "Second.",
                },
            ],
        )
        result = extract_units(bp_dir)
        numbers = [ud.number for ud in result]
        assert numbers == [1, 2, 3]


class TestExtractUnitsTierExtraction:
    """Tests for extract_units: tier content extraction from prose and contracts files."""

    def test_tier1_extracted_from_prose_file(self, two_unit_blueprint):
        result = extract_units(two_unit_blueprint)
        unit1 = [u for u in result if u.number == 1][0]
        assert "This is unit 1 tier 1 prose." in unit1.tier1

    def test_tier2_extracted_from_contracts_file(self, two_unit_blueprint):
        result = extract_units(two_unit_blueprint)
        unit1 = [u for u in result if u.number == 1][0]
        assert "def load_config" in unit1.tier2

    def test_tier3_extracted_from_contracts_file(self, two_unit_blueprint):
        result = extract_units(two_unit_blueprint)
        unit1 = [u for u in result if u.number == 1][0]
        assert "load_config returns a dict." in unit1.tier3

    def test_tier1_contains_full_text_until_next_heading(self, two_unit_blueprint):
        result = extract_units(two_unit_blueprint)
        unit1 = [u for u in result if u.number == 1][0]
        # Should contain only unit 1 prose, not unit 2
        assert "unit 1 tier 1" in unit1.tier1
        assert "unit 2 tier 1" not in unit1.tier1

    def test_tier3_contains_text_until_next_unit_heading(self, two_unit_blueprint):
        result = extract_units(two_unit_blueprint)
        unit1 = [u for u in result if u.number == 1][0]
        assert "load_config returns a dict." in unit1.tier3
        # Should not bleed into unit 2 tier 3
        assert "Registry must contain" not in unit1.tier3

    def test_last_unit_tier3_extends_to_eof(self, two_unit_blueprint):
        result = extract_units(two_unit_blueprint)
        unit2 = [u for u in result if u.number == 2][0]
        assert "Registry must contain python entry." in unit2.tier3


class TestExtractUnitsTier2HeadingPrefixMatch:
    """Tests for Tier 2 heading prefix matching (em-dash and suffix variations)."""

    def test_tier2_with_em_dash_heading(self, tmp_path):
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        _write_prose(bp_dir, [{"number": 1, "name": "Test", "tier1_body": "Prose."}])
        _write_contracts(
            bp_dir,
            [
                {
                    "number": 1,
                    "name": "Test",
                    "tier2_body": "```python\ndef a(): ...\n```",
                    "tier3_body": "Contracts.",
                },
            ],
            tier2_heading_style="em_dash",
        )
        result = extract_units(bp_dir)
        assert len(result) == 1
        assert "def a()" in result[0].tier2

    def test_tier2_with_plain_dash_heading(self, tmp_path):
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        _write_prose(bp_dir, [{"number": 1, "name": "Test", "tier1_body": "Prose."}])
        _write_contracts(
            bp_dir,
            [
                {
                    "number": 1,
                    "name": "Test",
                    "tier2_body": "```python\ndef b(): ...\n```",
                    "tier3_body": "Contracts.",
                },
            ],
            tier2_heading_style="plain",
        )
        result = extract_units(bp_dir)
        assert "def b()" in result[0].tier2

    def test_tier2_with_custom_suffix_heading(self, tmp_path):
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        _write_prose(bp_dir, [{"number": 1, "name": "Test", "tier1_body": "Prose."}])
        _write_contracts(
            bp_dir,
            [
                {
                    "number": 1,
                    "name": "Test",
                    "tier2_body": "```python\ndef c(): ...\n```",
                    "tier3_body": "Contracts.",
                },
            ],
            tier2_heading_style="- API Surface",
        )
        result = extract_units(bp_dir)
        assert "def c()" in result[0].tier2


class TestExtractUnitsCodeFenceStripping:
    """Tests that code fence markers are stripped from Tier 2 blocks."""

    def test_tier2_does_not_contain_opening_fence(self, two_unit_blueprint):
        result = extract_units(two_unit_blueprint)
        unit1 = [u for u in result if u.number == 1][0]
        assert "```python" not in unit1.tier2
        assert "```" not in unit1.tier2

    def test_tier2_does_not_contain_closing_fence(self, two_unit_blueprint):
        result = extract_units(two_unit_blueprint)
        unit2 = [u for u in result if u.number == 2][0]
        # The closing ``` should be stripped
        lines = unit2.tier2.strip().split("\n")
        for line in lines:
            assert line.strip() != "```"

    def test_tier2_contains_raw_code_without_fence_markers(self, two_unit_blueprint):
        result = extract_units(two_unit_blueprint)
        unit1 = [u for u in result if u.number == 1][0]
        assert "def load_config(): ..." in unit1.tier2

    def test_tier2_multiple_code_blocks_all_stripped(self, tmp_path):
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        _write_prose(bp_dir, [{"number": 1, "name": "Multi", "tier1_body": "Prose."}])
        contracts_content = (
            "## Unit 1: Multi\n\n"
            "### Tier 2 \u2014 Signatures\n\n"
            "```python\ndef first(): ...\n```\n\n"
            "```python\ndef second(): ...\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\n"
            "Contracts.\n\n"
        )
        (bp_dir / "blueprint_contracts.md").write_text(contracts_content)
        result = extract_units(bp_dir)
        tier2 = result[0].tier2
        assert "def first(): ..." in tier2
        assert "def second(): ..." in tier2
        assert "```python" not in tier2


class TestExtractUnitsParsesBothFiles:
    """Tests that extract_units reads from both blueprint_prose.md and blueprint_contracts.md."""

    def test_both_files_contribute_to_result(self, two_unit_blueprint):
        result = extract_units(two_unit_blueprint)
        unit1 = [u for u in result if u.number == 1][0]
        # tier1 from prose
        assert "unit 1 tier 1" in unit1.tier1
        # tier2 from contracts
        assert "def load_config" in unit1.tier2
        # tier3 from contracts
        assert "load_config returns a dict." in unit1.tier3


# ===========================================================================
# extract_units: machinery field
# ===========================================================================


class TestExtractUnitsMachineryField:
    """Tests for machinery field extraction from Tier 1 prose."""

    def test_machinery_true_for_unit_with_marker(self, machinery_blueprint):
        result = extract_units(machinery_blueprint)
        unit5 = [u for u in result if u.number == 5][0]
        assert unit5.machinery is True

    def test_machinery_true_for_unit_6(self, machinery_blueprint):
        result = extract_units(machinery_blueprint)
        unit6 = [u for u in result if u.number == 6][0]
        assert unit6.machinery is True

    def test_machinery_true_for_unit_14(self, machinery_blueprint):
        result = extract_units(machinery_blueprint)
        unit14 = [u for u in result if u.number == 14][0]
        assert unit14.machinery is True

    def test_machinery_true_for_unit_15(self, machinery_blueprint):
        result = extract_units(machinery_blueprint)
        unit15 = [u for u in result if u.number == 15][0]
        assert unit15.machinery is True

    def test_machinery_false_for_unit_without_marker(self, machinery_blueprint):
        result = extract_units(machinery_blueprint)
        unit3 = [u for u in result if u.number == 3][0]
        assert unit3.machinery is False

    def test_machinery_field_is_boolean(self, machinery_blueprint):
        result = extract_units(machinery_blueprint)
        for ud in result:
            assert isinstance(ud.machinery, bool)

    def test_machinery_detection_requires_exact_marker_text(self, tmp_path):
        """The marker text must be exactly 'machinery: true', not a variation."""
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        _write_prose(
            bp_dir,
            [
                {
                    "number": 1,
                    "name": "AlmostMachinery",
                    "tier1_body": "This has machinery:true without a space.",
                },
            ],
        )
        _write_contracts(
            bp_dir,
            [
                {
                    "number": 1,
                    "name": "AlmostMachinery",
                    "tier2_body": "```python\ndef x(): ...\n```",
                    "tier3_body": "Contracts.",
                },
            ],
        )
        result = extract_units(bp_dir)
        # "machinery:true" (no space) should NOT trigger machinery=True
        # Only "machinery: true" (with space) is the documented marker
        unit1 = result[0]
        assert unit1.machinery is False


# ===========================================================================
# build_unit_context
# ===========================================================================


class TestBuildUnitContextBasicAssembly:
    """Tests for build_unit_context: basic content assembly."""

    def test_returns_string(self):
        unit = _make_unit_def(number=1, tier1="T1", tier2="T2", tier3="T3")
        result = build_unit_context(unit, [unit])
        assert isinstance(result, str)

    def test_includes_tier1_when_flag_true(self):
        unit = _make_unit_def(
            number=1, tier1="TIER_ONE_CONTENT", tier2="T2", tier3="T3"
        )
        result = build_unit_context(unit, [unit], include_tier1=True)
        assert "TIER_ONE_CONTENT" in result

    def test_includes_tier2(self):
        unit = _make_unit_def(
            number=1, tier1="T1", tier2="TIER_TWO_CONTENT", tier3="T3"
        )
        result = build_unit_context(unit, [unit])
        assert "TIER_TWO_CONTENT" in result

    def test_includes_tier3(self):
        unit = _make_unit_def(
            number=1, tier1="T1", tier2="T2", tier3="TIER_THREE_CONTENT"
        )
        result = build_unit_context(unit, [unit])
        assert "TIER_THREE_CONTENT" in result


class TestBuildUnitContextIncludeTier1Flag:
    """Tests for build_unit_context: include_tier1 parameter behavior."""

    def test_excludes_tier1_when_flag_false(self):
        unit = _make_unit_def(
            number=1, tier1="SHOULD_BE_EXCLUDED", tier2="T2", tier3="T3"
        )
        result = build_unit_context(unit, [unit], include_tier1=False)
        assert "SHOULD_BE_EXCLUDED" not in result

    def test_include_tier1_defaults_to_true(self):
        unit = _make_unit_def(
            number=1, tier1="DEFAULT_INCLUDED", tier2="T2", tier3="T3"
        )
        result = build_unit_context(unit, [unit])
        assert "DEFAULT_INCLUDED" in result

    def test_tier2_and_tier3_present_regardless_of_tier1_flag(self):
        unit = _make_unit_def(
            number=1, tier1="T1", tier2="ALWAYS_T2", tier3="ALWAYS_T3"
        )
        result = build_unit_context(unit, [unit], include_tier1=False)
        assert "ALWAYS_T2" in result
        assert "ALWAYS_T3" in result


class TestBuildUnitContextUpstreamDependencies:
    """Tests for build_unit_context: upstream dependency inclusion."""

    def test_includes_dependency_tier2(self):
        dep = _make_unit_def(
            number=1, tier1="DEP_T1", tier2="DEP_TIER2_CONTENT", tier3="DEP_T3"
        )
        unit = _make_unit_def(
            number=2, dependencies=[1], tier1="T1", tier2="T2", tier3="T3"
        )
        result = build_unit_context(unit, [dep, unit])
        assert "DEP_TIER2_CONTENT" in result

    def test_includes_dependency_tier3(self):
        dep = _make_unit_def(
            number=1, tier1="DEP_T1", tier2="DEP_T2", tier3="DEP_TIER3_CONTENT"
        )
        unit = _make_unit_def(
            number=2, dependencies=[1], tier1="T1", tier2="T2", tier3="T3"
        )
        result = build_unit_context(unit, [dep, unit])
        assert "DEP_TIER3_CONTENT" in result

    def test_excludes_dependency_tier1(self):
        dep = _make_unit_def(
            number=1, tier1="DEP_TIER1_EXCLUDED", tier2="DEP_T2", tier3="DEP_T3"
        )
        unit = _make_unit_def(
            number=2, dependencies=[1], tier1="T1", tier2="T2", tier3="T3"
        )
        result = build_unit_context(unit, [dep, unit])
        assert "DEP_TIER1_EXCLUDED" not in result

    def test_multiple_dependencies_all_included(self):
        dep1 = _make_unit_def(number=1, tier2="DEP1_T2", tier3="DEP1_T3")
        dep2 = _make_unit_def(number=2, tier2="DEP2_T2", tier3="DEP2_T3")
        unit = _make_unit_def(number=3, dependencies=[1, 2], tier2="T2", tier3="T3")
        result = build_unit_context(unit, [dep1, dep2, unit])
        assert "DEP1_T2" in result
        assert "DEP1_T3" in result
        assert "DEP2_T2" in result
        assert "DEP2_T3" in result

    def test_no_dependencies_no_upstream_content(self):
        other = _make_unit_def(number=1, tier2="OTHER_T2", tier3="OTHER_T3")
        unit = _make_unit_def(
            number=2, dependencies=[], tier1="T1", tier2="OWN_T2", tier3="OWN_T3"
        )
        result = build_unit_context(unit, [other, unit])
        assert "OTHER_T2" not in result
        assert "OWN_T2" in result

    def test_dependency_tier1_excluded_even_with_include_tier1_true(self):
        """include_tier1 controls only the target unit's Tier 1, not dependencies'."""
        dep = _make_unit_def(
            number=1, tier1="DEP_T1_SHOULD_NOT_APPEAR", tier2="DEP_T2", tier3="DEP_T3"
        )
        unit = _make_unit_def(
            number=2, dependencies=[1], tier1="UNIT_T1", tier2="T2", tier3="T3"
        )
        result = build_unit_context(unit, [dep, unit], include_tier1=True)
        assert "UNIT_T1" in result
        assert "DEP_T1_SHOULD_NOT_APPEAR" not in result


class TestBuildUnitContextFormattedOutput:
    """Tests for build_unit_context: output is a formatted string."""

    def test_result_is_nonempty_string(self):
        unit = _make_unit_def(number=1, tier1="T1", tier2="T2", tier3="T3")
        result = build_unit_context(unit, [unit])
        assert len(result) > 0

    def test_all_tiers_present_in_order(self):
        """Tier 1 should appear before Tier 2, which should appear before Tier 3."""
        unit = _make_unit_def(
            number=1,
            tier1="AAA_TIER_ONE",
            tier2="BBB_TIER_TWO",
            tier3="CCC_TIER_THREE",
        )
        result = build_unit_context(unit, [unit], include_tier1=True)
        pos_t1 = result.index("AAA_TIER_ONE")
        pos_t2 = result.index("BBB_TIER_TWO")
        pos_t3 = result.index("CCC_TIER_THREE")
        assert pos_t1 < pos_t2 < pos_t3

    def test_dependency_content_appears_after_unit_content(self):
        dep = _make_unit_def(number=1, tier2="UPSTREAM_SIG", tier3="UPSTREAM_CONTRACT")
        unit = _make_unit_def(
            number=2, dependencies=[1], tier2="OWN_SIG", tier3="OWN_CONTRACT"
        )
        result = build_unit_context(unit, [dep, unit])
        pos_own = result.index("OWN_SIG")
        pos_dep = result.index("UPSTREAM_SIG")
        assert pos_own < pos_dep


# ===========================================================================
# detect_code_block_language
# ===========================================================================


class TestDetectCodeBlockLanguageMapping:
    """Tests for detect_code_block_language: language tag to identifier mapping."""

    def test_detects_python_from_code_fence(self, multi_language_blueprint):
        result = detect_code_block_language(multi_language_blueprint, 1)
        assert "python" in result

    def test_detects_stan_from_code_fence(self, multi_language_blueprint):
        result = detect_code_block_language(multi_language_blueprint, 1)
        assert "stan" in result

    def test_detects_r_from_code_fence(self, multi_language_blueprint):
        result = detect_code_block_language(multi_language_blueprint, 1)
        assert "r" in result

    def test_returns_set(self, multi_language_blueprint):
        result = detect_code_block_language(multi_language_blueprint, 1)
        assert isinstance(result, set)


class TestDetectCodeBlockLanguageReadsBothFiles:
    """Tests that detect_code_block_language reads from both blueprint files."""

    def test_language_from_prose_file_detected(self, multi_language_blueprint):
        """The prose file contains ```r fences which should be detected."""
        result = detect_code_block_language(multi_language_blueprint, 1)
        assert "r" in result

    def test_language_from_contracts_file_detected(self, multi_language_blueprint):
        """The contracts file contains ```stan fences which should be detected."""
        result = detect_code_block_language(multi_language_blueprint, 1)
        assert "stan" in result


class TestDetectCodeBlockLanguageUntaggedFences:
    """Tests for untagged code fences defaulting to project's primary language."""

    def test_untagged_fence_defaults_to_primary_language(self, tmp_path):
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        prose_content = "## Unit 1: Untagged\n\nProse.\n\n```\nsome code\n```\n\n"
        (bp_dir / "blueprint_prose.md").write_text(prose_content)
        contracts_content = (
            "## Unit 1: Untagged\n\n"
            "### Tier 2 \u2014 Signatures\n\n"
            "```\ndef foo(): ...\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\n"
            "Contracts.\n\n"
        )
        (bp_dir / "blueprint_contracts.md").write_text(contracts_content)
        result = detect_code_block_language(bp_dir, 1)
        # Untagged should default to project's primary language
        # Result should be non-empty since there are code fences
        assert len(result) > 0


class TestDetectCodeBlockLanguageScopedToUnit:
    """Tests that detect_code_block_language returns languages for the given unit only."""

    def test_only_returns_languages_for_specified_unit(self, tmp_path):
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        prose_content = (
            "## Unit 1: Python Only\n\nProse.\n\n## Unit 2: R Only\n\nProse.\n\n"
        )
        (bp_dir / "blueprint_prose.md").write_text(prose_content)
        contracts_content = (
            "## Unit 1: Python Only\n\n"
            "### Tier 2 \u2014 Signatures\n\n"
            "```python\ndef foo(): ...\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\nContracts.\n\n"
            "## Unit 2: R Only\n\n"
            "### Tier 2 \u2014 Signatures\n\n"
            "```r\nbar <- function() {}\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\nContracts.\n\n"
        )
        (bp_dir / "blueprint_contracts.md").write_text(contracts_content)

        result_unit1 = detect_code_block_language(bp_dir, 1)
        result_unit2 = detect_code_block_language(bp_dir, 2)

        assert "python" in result_unit1
        assert "r" not in result_unit1
        assert "r" in result_unit2
        assert "python" not in result_unit2


class TestDetectCodeBlockLanguageIndependence:
    """Tests that detect_code_block_language does not interact with build_unit_context."""

    def test_does_not_depend_on_include_tier1(self, multi_language_blueprint):
        """detect_code_block_language has no include_tier1 parameter or dependency."""
        # Simply verify the function signature accepts only blueprint_dir and unit_number
        result = detect_code_block_language(multi_language_blueprint, 1)
        assert isinstance(result, set)


class TestDetectCodeBlockLanguageSingleLanguage:
    """Tests for units with only one code block language."""

    def test_single_python_unit(self, tmp_path):
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        prose_content = "## Unit 1: Single\n\nProse.\n\n"
        (bp_dir / "blueprint_prose.md").write_text(prose_content)
        contracts_content = (
            "## Unit 1: Single\n\n"
            "### Tier 2 \u2014 Signatures\n\n"
            "```python\ndef foo(): ...\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\nContracts.\n\n"
        )
        (bp_dir / "blueprint_contracts.md").write_text(contracts_content)
        result = detect_code_block_language(bp_dir, 1)
        assert "python" in result


# ===========================================================================
# Integration-level: extract_units feeds build_unit_context
# ===========================================================================


class TestExtractThenBuildContext:
    """Tests exercising the extract_units -> build_unit_context pipeline."""

    def test_extracted_units_feed_into_build_context(self, dependency_chain_blueprint):
        all_units = extract_units(dependency_chain_blueprint)
        # Give unit 3 dependencies on 1 and 2
        unit3 = [u for u in all_units if u.number == 3][0]
        unit3.dependencies = [1, 2]
        result = build_unit_context(unit3, all_units, include_tier1=True)
        # Should contain unit 3's own tiers
        assert "top_fn" in result or "Top" in result
        # Should contain upstream tier 2/3 from unit 1 and 2
        assert "base_fn" in result or "Base contracts" in result

    def test_extracted_units_context_without_tier1(self, dependency_chain_blueprint):
        all_units = extract_units(dependency_chain_blueprint)
        unit1 = [u for u in all_units if u.number == 1][0]
        result = build_unit_context(unit1, all_units, include_tier1=False)
        # Tier 1 content from prose should be excluded
        assert "Base unit tier 1 content." not in result
        # Tier 2 and 3 should still be present
        assert "base_fn" in result or "Base contracts" in result


# ===========================================================================
# Edge cases
# ===========================================================================


class TestExtractUnitsEdgeCases:
    """Edge case tests for extract_units."""

    def test_single_unit_blueprint(self, tmp_path):
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        _write_prose(
            bp_dir, [{"number": 1, "name": "Only", "tier1_body": "Solo prose."}]
        )
        _write_contracts(
            bp_dir,
            [
                {
                    "number": 1,
                    "name": "Only",
                    "tier2_body": "```python\ndef solo(): ...\n```",
                    "tier3_body": "Solo contracts.",
                },
            ],
        )
        result = extract_units(bp_dir)
        assert len(result) == 1
        assert result[0].number == 1
        assert result[0].name == "Only"

    def test_unit_with_multiline_tier1(self, tmp_path):
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        long_tier1 = "Line one of tier 1.\nLine two of tier 1.\nLine three of tier 1."
        _write_prose(
            bp_dir, [{"number": 1, "name": "Verbose", "tier1_body": long_tier1}]
        )
        _write_contracts(
            bp_dir,
            [
                {
                    "number": 1,
                    "name": "Verbose",
                    "tier2_body": "```python\ndef v(): ...\n```",
                    "tier3_body": "Contracts.",
                },
            ],
        )
        result = extract_units(bp_dir)
        assert "Line one" in result[0].tier1
        assert "Line three" in result[0].tier1

    def test_unit_with_multiline_tier3(self, tmp_path):
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        _write_prose(
            bp_dir, [{"number": 1, "name": "DetailedContracts", "tier1_body": "Prose."}]
        )
        long_tier3 = "Contract A: does X.\nContract B: does Y.\nContract C: does Z."
        _write_contracts(
            bp_dir,
            [
                {
                    "number": 1,
                    "name": "DetailedContracts",
                    "tier2_body": "```python\ndef d(): ...\n```",
                    "tier3_body": long_tier3,
                },
            ],
        )
        result = extract_units(bp_dir)
        assert "Contract A" in result[0].tier3
        assert "Contract C" in result[0].tier3


class TestBuildUnitContextEdgeCases:
    """Edge case tests for build_unit_context."""

    def test_unit_with_empty_dependencies_list(self):
        unit = _make_unit_def(
            number=1, dependencies=[], tier1="T1", tier2="T2", tier3="T3"
        )
        result = build_unit_context(unit, [unit])
        assert "T2" in result
        assert "T3" in result

    def test_unit_with_empty_tier1(self):
        unit = _make_unit_def(number=1, tier1="", tier2="SIG", tier3="CONTRACT")
        result = build_unit_context(unit, [unit], include_tier1=True)
        assert "SIG" in result
        assert "CONTRACT" in result

    def test_dependency_not_in_all_units_list(self):
        """If a dependency number is not found in all_units, function should handle gracefully."""
        unit = _make_unit_def(number=2, dependencies=[99], tier2="T2", tier3="T3")
        # Only the unit itself is in the list; dependency 99 is missing
        # The function should not crash or should raise a clear error
        try:
            result = build_unit_context(unit, [unit])
            # If it doesn't crash, it should still contain the unit's own content
            assert "T2" in result
        except (KeyError, ValueError, IndexError):
            # An explicit error for missing dependency is also acceptable
            pass


class TestDetectCodeBlockLanguageEdgeCases:
    """Edge case tests for detect_code_block_language."""

    def test_unit_with_no_code_fences(self, tmp_path):
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        prose_content = "## Unit 1: NoCode\n\nJust text, no code blocks.\n\n"
        (bp_dir / "blueprint_prose.md").write_text(prose_content)
        contracts_content = (
            "## Unit 1: NoCode\n\n"
            "### Tier 2 \u2014 Signatures\n\n"
            "No code here either.\n\n"
            "### Tier 3 -- Behavioral Contracts\n\n"
            "Just text.\n\n"
        )
        (bp_dir / "blueprint_contracts.md").write_text(contracts_content)
        result = detect_code_block_language(bp_dir, 1)
        assert isinstance(result, set)

    def test_nonexistent_unit_number(self, tmp_path):
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        prose_content = "## Unit 1: Exists\n\nProse.\n\n"
        (bp_dir / "blueprint_prose.md").write_text(prose_content)
        contracts_content = (
            "## Unit 1: Exists\n\n"
            "### Tier 2 \u2014 Signatures\n\n"
            "```python\ndef foo(): ...\n```\n\n"
            "### Tier 3 -- Behavioral Contracts\n\nContracts.\n\n"
        )
        (bp_dir / "blueprint_contracts.md").write_text(contracts_content)
        # Requesting unit 999 which does not exist in the blueprint
        result = detect_code_block_language(bp_dir, 999)
        # Should return empty set or handle gracefully
        assert isinstance(result, set)
        assert len(result) == 0

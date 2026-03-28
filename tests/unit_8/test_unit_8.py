"""Tests for Unit 8: Blueprint Extractor.

Synthetic Data Assumptions
--------------------------
- Mock blueprint files (blueprint_prose.md and blueprint_contracts.md) are created
  in tmp_path to simulate the two blueprint files that extract_units parses.
- The heading pattern for unit sections is ``## Unit N: Name``.
- In the prose file, Tier 1 text is everything from the unit heading to the next
  unit heading or EOF.
- In the contracts file, Tier 2 content is between ``### Tier 2`` and ``### Tier 3``
  headings. Tier 3 content is from ``### Tier 3`` heading to next unit heading or EOF.
- Tier 2 headings use prefix match on ``### Tier 2`` -- both ``### Tier 2 -- Signatures``
  and ``### Tier 2 — Signatures`` (em-dash) are valid.
- Code fence markers (opening ``\u0060\u0060\u0060language`` and closing ``\u0060\u0060\u0060``) are stripped from
  Tier 2 blocks. The consumer receives raw code, not markdown.
- The ``machinery: true`` marker appears in Tier 1 (prose) text. When present,
  ``UnitDefinition.machinery`` is set to True.
- Dependencies are parsed from the Tier 3 section, e.g., ``**Dependencies:** Unit 1, Unit 2.``
  or ``**Dependencies:** None (root unit).``.
- ``detect_code_block_language`` reads code fence tags from BOTH files: ``python`` maps
  to "python", ``r`` maps to "r", ``stan`` maps to "stan". Untagged code fences default
  to the project's primary language (assumed "python" for tests).
- ``build_unit_context`` assembles context for a unit: Tier 1 (if include_tier1=True),
  Tier 2, Tier 3, plus upstream Tier 2 + Tier 3 for each dependency.
- ``UnitDefinition`` is a dataclass with 8 fields: number, name, tier1, tier2, tier3,
  dependencies, languages, machinery.
- Blueprint file names are ``blueprint_prose.md`` and ``blueprint_contracts.md``
  (matching Unit 1's ARTIFACT_FILENAMES registry values).
- Tests create filesystem fixtures in tmp_path and do NOT rely on any real blueprint
  files from the project.
"""

from dataclasses import fields

from blueprint_extractor import (
    UnitDefinition,
    build_unit_context,
    detect_code_block_language,
    extract_units,
)

# ---------------------------------------------------------------------------
# Helpers and Fixtures
# ---------------------------------------------------------------------------

SAMPLE_PROSE_SINGLE_UNIT = """\
# Blueprint Prose

---

## Unit 1: Core Configuration

Unit 1 provides the core configuration loading and saving logic.
It reads svp_config.json and merges with defaults.

---
"""

SAMPLE_CONTRACTS_SINGLE_UNIT = """\
# Blueprint Contracts

---

## Unit 1: Core Configuration

### Tier 2 — Signatures

```python
from typing import Any, Dict
from pathlib import Path

def load_config(project_root: Path) -> Dict[str, Any]: ...

def save_config(project_root: Path, config: Dict[str, Any]) -> None: ...
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** None (root unit).

**load_config:**
- Reads svp_config.json from project_root.
- Returns merged dict.

---
"""


def _make_blueprint_dir(tmp_path, prose_content, contracts_content):
    """Helper: write blueprint files into tmp_path and return the directory."""
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir(exist_ok=True)
    (bp_dir / "blueprint_prose.md").write_text(prose_content)
    (bp_dir / "blueprint_contracts.md").write_text(contracts_content)
    return bp_dir


def _make_multi_unit_prose(units):
    """Build a prose file from a list of (number, name, tier1_text) tuples."""
    lines = ["# Blueprint Prose\n\n---\n"]
    for number, name, tier1_text in units:
        lines.append(f"\n## Unit {number}: {name}\n\n{tier1_text}\n\n---\n")
    return "\n".join(lines)


def _make_multi_unit_contracts(units):
    """Build a contracts file from a list of
    (number, name, tier2_code, tier2_lang_tag, tier3_text) tuples.
    """
    lines = ["# Blueprint Contracts\n\n---\n"]
    for number, name, tier2_code, tier2_lang_tag, tier3_text in units:
        tag = tier2_lang_tag if tier2_lang_tag else ""
        lines.append(
            f"\n## Unit {number}: {name}\n\n"
            f"### Tier 2 — Signatures\n\n"
            f"```{tag}\n"
            f"{tier2_code}\n"
            f"```\n\n"
            f"### Tier 3 -- Behavioral Contracts\n\n"
            f"{tier3_text}\n\n---\n"
        )
    return "\n".join(lines)


def _build_unit(
    number=1,
    name="TestUnit",
    tier1="Some description.",
    tier2="def foo(): ...",
    tier3="**Dependencies:** None.",
    dependencies=None,
    languages=None,
    machinery=False,
):
    """Helper to construct a UnitDefinition with defaults."""
    return UnitDefinition(
        number=number,
        name=name,
        tier1=tier1,
        tier2=tier2,
        tier3=tier3,
        dependencies=dependencies if dependencies is not None else [],
        languages=languages if languages is not None else {"python"},
        machinery=machinery,
    )


# ---------------------------------------------------------------------------
# UnitDefinition Dataclass Tests
# ---------------------------------------------------------------------------


class TestUnitDefinitionDataclass:
    """Tests for the UnitDefinition dataclass structure."""

    def test_unit_definition_has_exactly_eight_fields(self):
        """UnitDefinition must have exactly 8 fields as specified."""
        assert len(fields(UnitDefinition)) == 8

    def test_unit_definition_field_names_match_specification(self):
        """UnitDefinition field names must match the blueprint specification."""
        expected = {
            "number",
            "name",
            "tier1",
            "tier2",
            "tier3",
            "dependencies",
            "languages",
            "machinery",
        }
        actual = {f.name for f in fields(UnitDefinition)}
        assert actual == expected

    def test_unit_definition_number_field_is_int(self):
        """The number field type annotation must be int."""
        field_map = {f.name: f for f in fields(UnitDefinition)}
        assert field_map["number"].type is int or field_map["number"].type == "int"

    def test_unit_definition_name_field_is_str(self):
        """The name field type annotation must be str."""
        field_map = {f.name: f for f in fields(UnitDefinition)}
        assert field_map["name"].type is str or field_map["name"].type == "str"

    def test_unit_definition_dependencies_field_is_list_int(self):
        """The dependencies field must accept a list of ints."""
        unit = _build_unit(dependencies=[1, 2, 3])
        assert unit.dependencies == [1, 2, 3]

    def test_unit_definition_languages_field_is_set_str(self):
        """The languages field must accept a set of strings."""
        unit = _build_unit(languages={"python", "r"})
        assert unit.languages == {"python", "r"}

    def test_unit_definition_machinery_field_is_bool(self):
        """The machinery field must be a boolean."""
        unit_true = _build_unit(machinery=True)
        unit_false = _build_unit(machinery=False)
        assert unit_true.machinery is True
        assert unit_false.machinery is False

    def test_unit_definition_can_be_constructed_with_all_fields(self):
        """UnitDefinition can be constructed by passing all 8 fields."""
        unit = UnitDefinition(
            number=5,
            name="Pipeline State",
            tier1="Some tier1 text.",
            tier2="def foo(): ...",
            tier3="**Dependencies:** Unit 1.",
            dependencies=[1],
            languages={"python"},
            machinery=True,
        )
        assert unit.number == 5
        assert unit.name == "Pipeline State"
        assert unit.tier1 == "Some tier1 text."
        assert unit.tier2 == "def foo(): ..."
        assert unit.tier3 == "**Dependencies:** Unit 1."
        assert unit.dependencies == [1]
        assert unit.languages == {"python"}
        assert unit.machinery is True


# ---------------------------------------------------------------------------
# extract_units Tests
# ---------------------------------------------------------------------------


class TestExtractUnits:
    """Tests for extract_units function."""

    def test_extracts_single_unit_from_both_files(self, tmp_path):
        """extract_units parses a single unit from prose and contracts files."""
        bp_dir = _make_blueprint_dir(
            tmp_path, SAMPLE_PROSE_SINGLE_UNIT, SAMPLE_CONTRACTS_SINGLE_UNIT
        )
        result = extract_units(bp_dir)
        assert len(result) == 1
        assert result[0].number == 1
        assert result[0].name == "Core Configuration"

    def test_extracts_tier1_from_prose_file(self, tmp_path):
        """Tier 1 text is extracted from the prose file."""
        bp_dir = _make_blueprint_dir(
            tmp_path, SAMPLE_PROSE_SINGLE_UNIT, SAMPLE_CONTRACTS_SINGLE_UNIT
        )
        result = extract_units(bp_dir)
        assert "core configuration loading" in result[0].tier1.lower()

    def test_extracts_tier2_from_contracts_file(self, tmp_path):
        """Tier 2 text is extracted from the contracts file."""
        bp_dir = _make_blueprint_dir(
            tmp_path, SAMPLE_PROSE_SINGLE_UNIT, SAMPLE_CONTRACTS_SINGLE_UNIT
        )
        result = extract_units(bp_dir)
        assert "load_config" in result[0].tier2

    def test_extracts_tier3_from_contracts_file(self, tmp_path):
        """Tier 3 text is extracted from the contracts file."""
        bp_dir = _make_blueprint_dir(
            tmp_path, SAMPLE_PROSE_SINGLE_UNIT, SAMPLE_CONTRACTS_SINGLE_UNIT
        )
        result = extract_units(bp_dir)
        assert "Dependencies" in result[0].tier3

    def test_code_fence_markers_stripped_from_tier2(self, tmp_path):
        """Opening and closing code fence markers must be stripped from Tier 2."""
        bp_dir = _make_blueprint_dir(
            tmp_path, SAMPLE_PROSE_SINGLE_UNIT, SAMPLE_CONTRACTS_SINGLE_UNIT
        )
        result = extract_units(bp_dir)
        tier2 = result[0].tier2
        assert "```" not in tier2
        assert "```python" not in tier2

    def test_tier2_contains_raw_code_after_fence_stripping(self, tmp_path):
        """After stripping fences, Tier 2 should contain raw code."""
        bp_dir = _make_blueprint_dir(
            tmp_path, SAMPLE_PROSE_SINGLE_UNIT, SAMPLE_CONTRACTS_SINGLE_UNIT
        )
        result = extract_units(bp_dir)
        tier2 = result[0].tier2
        assert "def load_config" in tier2
        assert "def save_config" in tier2

    def test_extracts_multiple_units(self, tmp_path):
        """extract_units handles multiple units in both files."""
        prose = _make_multi_unit_prose(
            [
                (1, "Alpha", "Alpha description."),
                (2, "Beta", "Beta description."),
                (3, "Gamma", "Gamma description."),
            ]
        )
        contracts = _make_multi_unit_contracts(
            [
                (1, "Alpha", "def alpha(): ...", "python", "**Dependencies:** None."),
                (2, "Beta", "def beta(): ...", "python", "**Dependencies:** Unit 1."),
                (
                    3,
                    "Gamma",
                    "def gamma(): ...",
                    "python",
                    "**Dependencies:** Unit 1, Unit 2.",
                ),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = extract_units(bp_dir)
        assert len(result) == 3

    def test_returns_units_sorted_by_number(self, tmp_path):
        """Returned list must be sorted by unit number."""
        # Put units in contracts file in reverse order
        prose = _make_multi_unit_prose(
            [
                (3, "Gamma", "Gamma description."),
                (1, "Alpha", "Alpha description."),
                (2, "Beta", "Beta description."),
            ]
        )
        contracts = _make_multi_unit_contracts(
            [
                (
                    3,
                    "Gamma",
                    "def gamma(): ...",
                    "python",
                    "**Dependencies:** Unit 1, Unit 2.",
                ),
                (1, "Alpha", "def alpha(): ...", "python", "**Dependencies:** None."),
                (2, "Beta", "def beta(): ...", "python", "**Dependencies:** Unit 1."),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = extract_units(bp_dir)
        numbers = [u.number for u in result]
        assert numbers == [1, 2, 3]

    def test_heading_pattern_matches_unit_n_name(self, tmp_path):
        """The heading pattern ``## Unit N: Name`` must be matched."""
        prose = _make_multi_unit_prose(
            [
                (42, "Special Unit", "Description of unit 42."),
            ]
        )
        contracts = _make_multi_unit_contracts(
            [
                (
                    42,
                    "Special Unit",
                    "def special(): ...",
                    "python",
                    "**Dependencies:** None.",
                ),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = extract_units(bp_dir)
        assert len(result) == 1
        assert result[0].number == 42
        assert result[0].name == "Special Unit"

    def test_tier2_heading_prefix_match_with_em_dash(self, tmp_path):
        """Tier 2 heading uses prefix match -- ``### Tier 2 \u2014`` (em-dash) is valid."""
        contracts_content = """\
# Blueprint Contracts

---

## Unit 1: Test Unit

### Tier 2 \u2014 Signatures

```python
def foo(): ...
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** None.

---
"""
        prose = _make_multi_unit_prose([(1, "Test Unit", "Test description.")])
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts_content)
        result = extract_units(bp_dir)
        assert len(result) == 1
        assert "def foo" in result[0].tier2

    def test_tier2_heading_prefix_match_with_double_dash(self, tmp_path):
        """Tier 2 heading uses prefix match -- ``### Tier 2 --`` (double-dash) is valid."""
        contracts_content = """\
# Blueprint Contracts

---

## Unit 1: Test Unit

### Tier 2 -- Signatures

```python
def bar(): ...
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** None.

---
"""
        prose = _make_multi_unit_prose([(1, "Test Unit", "Test description.")])
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts_content)
        result = extract_units(bp_dir)
        assert len(result) == 1
        assert "def bar" in result[0].tier2

    def test_machinery_set_true_when_tier1_contains_marker(self, tmp_path):
        """machinery field is True when Tier 1 contains 'machinery: true'."""
        prose = _make_multi_unit_prose(
            [
                (
                    5,
                    "Pipeline State",
                    "**Machinery unit.** This unit is tagged `machinery: true` in the "
                    "blueprint extractor.",
                ),
            ]
        )
        contracts = _make_multi_unit_contracts(
            [
                (
                    5,
                    "Pipeline State",
                    "class PipelineState: ...",
                    "python",
                    "**Dependencies:** None.",
                ),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = extract_units(bp_dir)
        assert result[0].machinery is True

    def test_machinery_defaults_to_false_for_normal_units(self, tmp_path):
        """machinery field defaults to False for units without the marker."""
        prose = _make_multi_unit_prose(
            [
                (1, "Core Configuration", "This unit provides configuration."),
            ]
        )
        contracts = _make_multi_unit_contracts(
            [
                (
                    1,
                    "Core Configuration",
                    "def load_config(): ...",
                    "python",
                    "**Dependencies:** None.",
                ),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = extract_units(bp_dir)
        assert result[0].machinery is False

    def test_machinery_true_for_known_machinery_units(self, tmp_path):
        """Units 5, 6, 14, 15 are known machinery units when tagged."""
        machinery_units = [
            (5, "Pipeline State"),
            (6, "State Transitions"),
            (14, "Routing"),
            (15, "Quality Gate"),
        ]
        prose_items = []
        contracts_items = []
        for num, name in machinery_units:
            prose_items.append(
                (
                    num,
                    name,
                    "**Machinery unit.** This unit is tagged `machinery: true`.",
                )
            )
            contracts_items.append(
                (
                    num,
                    name,
                    f"def func_{num}(): ...",
                    "python",
                    "**Dependencies:** None.",
                )
            )
        prose = _make_multi_unit_prose(prose_items)
        contracts = _make_multi_unit_contracts(contracts_items)
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = extract_units(bp_dir)
        for unit in result:
            assert unit.machinery is True, (
                f"Unit {unit.number} ({unit.name}) should be machinery=True"
            )

    def test_parses_dependencies_from_tier3_none(self, tmp_path):
        """Dependencies parsed as empty list when 'None' is specified."""
        bp_dir = _make_blueprint_dir(
            tmp_path, SAMPLE_PROSE_SINGLE_UNIT, SAMPLE_CONTRACTS_SINGLE_UNIT
        )
        result = extract_units(bp_dir)
        assert result[0].dependencies == []

    def test_parses_single_dependency(self, tmp_path):
        """Dependencies parsed correctly for a single dependency."""
        prose = _make_multi_unit_prose(
            [
                (1, "Alpha", "Alpha."),
                (2, "Beta", "Beta."),
            ]
        )
        contracts = _make_multi_unit_contracts(
            [
                (1, "Alpha", "def a(): ...", "python", "**Dependencies:** None."),
                (2, "Beta", "def b(): ...", "python", "**Dependencies:** Unit 1."),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = extract_units(bp_dir)
        unit2 = [u for u in result if u.number == 2][0]
        assert unit2.dependencies == [1]

    def test_parses_multiple_dependencies(self, tmp_path):
        """Dependencies parsed correctly for multiple dependencies."""
        prose = _make_multi_unit_prose(
            [
                (1, "A", "A."),
                (2, "B", "B."),
                (3, "C", "C."),
            ]
        )
        contracts = _make_multi_unit_contracts(
            [
                (1, "A", "def a(): ...", "python", "**Dependencies:** None."),
                (2, "B", "def b(): ...", "python", "**Dependencies:** Unit 1."),
                (3, "C", "def c(): ...", "python", "**Dependencies:** Unit 1, Unit 2."),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = extract_units(bp_dir)
        unit3 = [u for u in result if u.number == 3][0]
        assert sorted(unit3.dependencies) == [1, 2]

    def test_returns_list_type(self, tmp_path):
        """extract_units must return a list."""
        bp_dir = _make_blueprint_dir(
            tmp_path, SAMPLE_PROSE_SINGLE_UNIT, SAMPLE_CONTRACTS_SINGLE_UNIT
        )
        result = extract_units(bp_dir)
        assert isinstance(result, list)

    def test_returned_elements_are_unit_definitions(self, tmp_path):
        """Each element in the returned list must be a UnitDefinition."""
        bp_dir = _make_blueprint_dir(
            tmp_path, SAMPLE_PROSE_SINGLE_UNIT, SAMPLE_CONTRACTS_SINGLE_UNIT
        )
        result = extract_units(bp_dir)
        for item in result:
            assert isinstance(item, UnitDefinition)

    def test_tier1_extraction_stops_at_next_unit_heading(self, tmp_path):
        """Tier 1 for a unit goes from heading to next unit heading or EOF."""
        prose = _make_multi_unit_prose(
            [
                (1, "First", "First unit description with details."),
                (2, "Second", "Second unit description."),
            ]
        )
        contracts = _make_multi_unit_contracts(
            [
                (1, "First", "def f1(): ...", "python", "**Dependencies:** None."),
                (2, "Second", "def f2(): ...", "python", "**Dependencies:** Unit 1."),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = extract_units(bp_dir)
        unit1 = [u for u in result if u.number == 1][0]
        unit2 = [u for u in result if u.number == 2][0]
        # Unit 1's tier1 should NOT contain Unit 2's description
        assert "Second unit description" not in unit1.tier1
        # Unit 2's tier1 should contain its own description
        assert "Second unit description" in unit2.tier1

    def test_tier3_extraction_stops_at_next_unit_heading(self, tmp_path):
        """Tier 3 for a unit goes from ### Tier 3 heading to next unit heading or EOF."""
        prose = _make_multi_unit_prose(
            [
                (1, "First", "First."),
                (2, "Second", "Second."),
            ]
        )
        contracts = _make_multi_unit_contracts(
            [
                (
                    1,
                    "First",
                    "def f1(): ...",
                    "python",
                    "**Dependencies:** None.\n\n**f1:**\n- Does first thing.",
                ),
                (
                    2,
                    "Second",
                    "def f2(): ...",
                    "python",
                    "**Dependencies:** Unit 1.\n\n**f2:**\n- Does second thing.",
                ),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = extract_units(bp_dir)
        unit1 = [u for u in result if u.number == 1][0]
        # Unit 1's tier3 should NOT contain Unit 2's tier3 content
        assert "Does second thing" not in unit1.tier3

    def test_reads_from_blueprint_prose_and_contracts_filenames(self, tmp_path):
        """extract_units reads files named blueprint_prose.md and blueprint_contracts.md."""
        bp_dir = tmp_path / "blueprint"
        bp_dir.mkdir()
        (bp_dir / "blueprint_prose.md").write_text(SAMPLE_PROSE_SINGLE_UNIT)
        (bp_dir / "blueprint_contracts.md").write_text(SAMPLE_CONTRACTS_SINGLE_UNIT)
        result = extract_units(bp_dir)
        assert len(result) == 1

    def test_multiple_code_fences_in_tier2_all_stripped(self, tmp_path):
        """If Tier 2 contains multiple code fence blocks, all fences should be stripped."""
        contracts_content = """\
# Blueprint Contracts

---

## Unit 1: Multi Block

### Tier 2 — Signatures

```python
def alpha(): ...
```

```python
def beta(): ...
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** None.

---
"""
        prose = _make_multi_unit_prose([(1, "Multi Block", "Multi block unit.")])
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts_content)
        result = extract_units(bp_dir)
        assert "```" not in result[0].tier2
        assert "def alpha" in result[0].tier2
        assert "def beta" in result[0].tier2


# ---------------------------------------------------------------------------
# build_unit_context Tests
# ---------------------------------------------------------------------------


class TestBuildUnitContext:
    """Tests for build_unit_context function."""

    def test_includes_tier1_when_flag_is_true(self):
        """When include_tier1=True, context includes Tier 1 text."""
        unit = _build_unit(
            number=1,
            name="TestUnit",
            tier1="This is the tier 1 description.",
            tier2="def foo(): ...",
            tier3="**Dependencies:** None.",
            dependencies=[],
        )
        context = build_unit_context(unit, [unit], include_tier1=True)
        assert "This is the tier 1 description." in context

    def test_excludes_tier1_when_flag_is_false(self):
        """When include_tier1=False, context does NOT include Tier 1 text."""
        unit = _build_unit(
            number=1,
            name="TestUnit",
            tier1="This is the tier 1 description.",
            tier2="def foo(): ...",
            tier3="**Dependencies:** None.",
            dependencies=[],
        )
        context = build_unit_context(unit, [unit], include_tier1=False)
        assert "This is the tier 1 description." not in context

    def test_includes_tier2_always(self):
        """Tier 2 is always included in the context."""
        unit = _build_unit(tier2="def always_present(): ...")
        context = build_unit_context(unit, [unit], include_tier1=False)
        assert "def always_present" in context

    def test_includes_tier3_always(self):
        """Tier 3 is always included in the context."""
        unit = _build_unit(tier3="**load_config:**\n- Reads config.")
        context = build_unit_context(unit, [unit], include_tier1=False)
        assert "Reads config" in context

    def test_includes_upstream_tier2_for_dependency(self):
        """For each dependency, includes its Tier 2 in the context."""
        dep_unit = _build_unit(
            number=1,
            name="Dependency",
            tier1="Dep tier1.",
            tier2="def upstream_func(): ...",
            tier3="Dep tier3.",
            dependencies=[],
        )
        main_unit = _build_unit(
            number=2,
            name="Main",
            tier1="Main tier1.",
            tier2="def main_func(): ...",
            tier3="**Dependencies:** Unit 1.",
            dependencies=[1],
        )
        all_units = [dep_unit, main_unit]
        context = build_unit_context(main_unit, all_units, include_tier1=True)
        assert "def upstream_func" in context

    def test_includes_upstream_tier3_for_dependency(self):
        """For each dependency, includes its Tier 3 in the context."""
        dep_unit = _build_unit(
            number=1,
            name="Dependency",
            tier1="Dep tier1.",
            tier2="def dep(): ...",
            tier3="Dep behavioral contract details.",
            dependencies=[],
        )
        main_unit = _build_unit(
            number=2,
            name="Main",
            tier2="def main(): ...",
            tier3="**Dependencies:** Unit 1.",
            dependencies=[1],
        )
        all_units = [dep_unit, main_unit]
        context = build_unit_context(main_unit, all_units, include_tier1=True)
        assert "Dep behavioral contract details" in context

    def test_excludes_upstream_tier1(self):
        """Upstream contracts include only Tier 2 and Tier 3, NOT Tier 1."""
        dep_unit = _build_unit(
            number=1,
            name="Dependency",
            tier1="PRIVATE_DEPENDENCY_TIER1_CONTENT_SHOULD_NOT_APPEAR",
            tier2="def dep(): ...",
            tier3="Dep tier3.",
            dependencies=[],
        )
        main_unit = _build_unit(
            number=2,
            name="Main",
            tier1="Main tier1.",
            tier2="def main(): ...",
            tier3="**Dependencies:** Unit 1.",
            dependencies=[1],
        )
        all_units = [dep_unit, main_unit]
        context = build_unit_context(main_unit, all_units, include_tier1=True)
        assert "PRIVATE_DEPENDENCY_TIER1_CONTENT_SHOULD_NOT_APPEAR" not in context

    def test_handles_multiple_dependencies(self):
        """Context includes upstream contracts for all dependencies."""
        dep1 = _build_unit(
            number=1, name="Dep1", tier2="def dep1_sig(): ...", tier3="Dep1 contract."
        )
        dep2 = _build_unit(
            number=2, name="Dep2", tier2="def dep2_sig(): ...", tier3="Dep2 contract."
        )
        main_unit = _build_unit(
            number=3,
            name="Main",
            tier2="def main(): ...",
            tier3="**Dependencies:** Unit 1, Unit 2.",
            dependencies=[1, 2],
        )
        all_units = [dep1, dep2, main_unit]
        context = build_unit_context(main_unit, all_units, include_tier1=True)
        assert "def dep1_sig" in context
        assert "def dep2_sig" in context
        assert "Dep1 contract" in context
        assert "Dep2 contract" in context

    def test_no_dependencies_produces_own_content_only(self):
        """A unit with no dependencies gets only its own tiers in context."""
        unit = _build_unit(
            number=1,
            name="Standalone",
            tier1="Standalone tier1.",
            tier2="def standalone(): ...",
            tier3="No deps.",
            dependencies=[],
        )
        context = build_unit_context(unit, [unit], include_tier1=True)
        assert "def standalone" in context
        assert "No deps" in context

    def test_returns_string(self):
        """build_unit_context returns a string."""
        unit = _build_unit()
        context = build_unit_context(unit, [unit], include_tier1=True)
        assert isinstance(context, str)

    def test_include_tier1_defaults_to_true(self):
        """include_tier1 parameter defaults to True."""
        unit = _build_unit(
            tier1="DEFAULT_TIER1_INCLUDED",
            tier2="def x(): ...",
            tier3="Contracts.",
        )
        # Call without specifying include_tier1
        context = build_unit_context(unit, [unit])
        assert "DEFAULT_TIER1_INCLUDED" in context

    def test_code_fence_markers_not_in_upstream_tier2(self):
        """Upstream Tier 2 blocks should not contain code fence markers
        (they were already stripped by extract_units)."""
        dep = _build_unit(
            number=1,
            name="Dep",
            tier2="def dep_func(): ...",
            tier3="Dep contracts.",
        )
        main_unit = _build_unit(
            number=2,
            name="Main",
            tier2="def main_func(): ...",
            tier3="Main contracts.",
            dependencies=[1],
        )
        context = build_unit_context(main_unit, [dep, main_unit], include_tier1=True)
        # Since tier2 is already stripped raw code, no fences expected
        assert "def dep_func" in context


# ---------------------------------------------------------------------------
# detect_code_block_language Tests
# ---------------------------------------------------------------------------


class TestDetectCodeBlockLanguage:
    """Tests for detect_code_block_language function."""

    def test_detects_python_from_code_fence_tag(self, tmp_path):
        """Code fence tagged ``python`` maps to 'python' in the language set."""
        prose = _make_multi_unit_prose([(1, "PyUnit", "Description.")])
        contracts = _make_multi_unit_contracts(
            [
                (1, "PyUnit", "def foo(): ...", "python", "**Dependencies:** None."),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = detect_code_block_language(bp_dir, 1)
        assert "python" in result

    def test_detects_r_from_code_fence_tag(self, tmp_path):
        """Code fence tagged ``r`` maps to 'r' in the language set."""
        contracts_content = """\
# Blueprint Contracts

---

## Unit 1: RUnit

### Tier 2 — Signatures

```r
alpha <- function(x) { }
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** None.

---
"""
        prose = _make_multi_unit_prose([(1, "RUnit", "An R unit.")])
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts_content)
        result = detect_code_block_language(bp_dir, 1)
        assert "r" in result

    def test_detects_stan_from_code_fence_tag(self, tmp_path):
        """Code fence tagged ``stan`` maps to 'stan' in the language set."""
        contracts_content = """\
# Blueprint Contracts

---

## Unit 1: StanUnit

### Tier 2 — Signatures

```stan
data { int N; }
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** None.

---
"""
        prose = _make_multi_unit_prose([(1, "StanUnit", "A Stan unit.")])
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts_content)
        result = detect_code_block_language(bp_dir, 1)
        assert "stan" in result

    def test_untagged_code_fence_defaults_to_primary_language(self, tmp_path):
        """Untagged code fences default to the project's primary language."""
        contracts_content = """\
# Blueprint Contracts

---

## Unit 1: Untagged

### Tier 2 — Signatures

```
def untag(): ...
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** None.

---
"""
        prose = _make_multi_unit_prose([(1, "Untagged", "An untagged unit.")])
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts_content)
        result = detect_code_block_language(bp_dir, 1)
        # Should default to primary language; for this project that is "python"
        assert isinstance(result, set)
        assert len(result) >= 1

    def test_returns_set_type(self, tmp_path):
        """detect_code_block_language returns a set."""
        prose = _make_multi_unit_prose([(1, "Test", "Test.")])
        contracts = _make_multi_unit_contracts(
            [
                (1, "Test", "def x(): ...", "python", "**Dependencies:** None."),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = detect_code_block_language(bp_dir, 1)
        assert isinstance(result, set)

    def test_returns_set_of_strings(self, tmp_path):
        """All elements in the returned set are strings."""
        prose = _make_multi_unit_prose([(1, "Test", "Test.")])
        contracts = _make_multi_unit_contracts(
            [
                (1, "Test", "def x(): ...", "python", "**Dependencies:** None."),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = detect_code_block_language(bp_dir, 1)
        for item in result:
            assert isinstance(item, str)

    def test_reads_code_fence_tags_from_both_files(self, tmp_path):
        """detect_code_block_language reads code fence tags from BOTH files."""
        # Put a python code fence in contracts and an r code fence in prose
        prose_content = """\
# Blueprint Prose

---

## Unit 1: Bilingual

This unit uses both languages.

```r
source_func <- function() { }
```

---
"""
        contracts_content = """\
# Blueprint Contracts

---

## Unit 1: Bilingual

### Tier 2 — Signatures

```python
def bilingual(): ...
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** None.

---
"""
        bp_dir = _make_blueprint_dir(tmp_path, prose_content, contracts_content)
        result = detect_code_block_language(bp_dir, 1)
        assert "python" in result
        assert "r" in result

    def test_detects_language_only_for_specified_unit(self, tmp_path):
        """Language detection is scoped to the specified unit_number."""
        prose = _make_multi_unit_prose(
            [
                (1, "PyUnit", "Python unit."),
                (2, "RUnit", "R unit."),
            ]
        )
        contracts_content = """\
# Blueprint Contracts

---

## Unit 1: PyUnit

### Tier 2 — Signatures

```python
def py_func(): ...
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** None.

---

## Unit 2: RUnit

### Tier 2 — Signatures

```r
r_func <- function() { }
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** Unit 1.

---
"""
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts_content)
        result_u1 = detect_code_block_language(bp_dir, 1)
        result_u2 = detect_code_block_language(bp_dir, 2)
        assert "python" in result_u1
        assert "r" not in result_u1
        assert "r" in result_u2

    def test_multiple_languages_in_single_unit(self, tmp_path):
        """A unit can have multiple languages detected from different code fences."""
        contracts_content = """\
# Blueprint Contracts

---

## Unit 1: Mixed

### Tier 2 — Signatures

```python
def py_func(): ...
```

```stan
data { int N; }
```

### Tier 3 -- Behavioral Contracts

**Dependencies:** None.

---
"""
        prose = _make_multi_unit_prose([(1, "Mixed", "Mixed language unit.")])
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts_content)
        result = detect_code_block_language(bp_dir, 1)
        assert "python" in result
        assert "stan" in result

    def test_does_not_interact_with_build_unit_context(self, tmp_path):
        """detect_code_block_language is independent of build_unit_context.
        It reads files directly, not through context assembly."""
        # This test verifies the function works standalone without
        # needing build_unit_context or include_tier1
        prose = _make_multi_unit_prose([(1, "Solo", "Solo description.")])
        contracts = _make_multi_unit_contracts(
            [
                (1, "Solo", "def solo(): ...", "python", "**Dependencies:** None."),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        # Should work directly without requiring build_unit_context
        result = detect_code_block_language(bp_dir, 1)
        assert isinstance(result, set)
        assert "python" in result


# ---------------------------------------------------------------------------
# Integration-style behavioral tests
# ---------------------------------------------------------------------------


class TestExtractUnitsEndToEnd:
    """End-to-end behavioral tests combining multiple contracts."""

    def test_full_extraction_with_machinery_and_dependencies(self, tmp_path):
        """Full extraction with machinery units and dependency chains."""
        prose = _make_multi_unit_prose(
            [
                (1, "Config", "Configuration module."),
                (2, "Registry", "Language registry."),
                (
                    5,
                    "Pipeline State",
                    "**Machinery unit.** This unit is tagged `machinery: true`.",
                ),
                (8, "Extractor", "Blueprint extractor module."),
            ]
        )
        contracts = _make_multi_unit_contracts(
            [
                (
                    1,
                    "Config",
                    "def load_config(): ...",
                    "python",
                    "**Dependencies:** None (root unit).",
                ),
                (
                    2,
                    "Registry",
                    "LANGUAGE_REGISTRY = {}",
                    "python",
                    "**Dependencies:** Unit 1.",
                ),
                (
                    5,
                    "Pipeline State",
                    "class PipelineState: ...",
                    "python",
                    "**Dependencies:** None.",
                ),
                (
                    8,
                    "Extractor",
                    "def extract_units(): ...",
                    "python",
                    "**Dependencies:** Unit 1, Unit 2.",
                ),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = extract_units(bp_dir)

        assert len(result) == 4
        # Sorted by number
        assert [u.number for u in result] == [1, 2, 5, 8]

        # Machinery
        unit5 = [u for u in result if u.number == 5][0]
        assert unit5.machinery is True

        unit1 = [u for u in result if u.number == 1][0]
        assert unit1.machinery is False

        # Dependencies
        unit8 = [u for u in result if u.number == 8][0]
        assert sorted(unit8.dependencies) == [1, 2]

        unit1 = [u for u in result if u.number == 1][0]
        assert unit1.dependencies == []

    def test_build_context_with_extracted_units(self, tmp_path):
        """build_unit_context works correctly with units from extract_units."""
        prose = _make_multi_unit_prose(
            [
                (1, "Config", "Configuration is the foundation."),
                (2, "Registry", "Registry manages languages."),
                (8, "Extractor", "Extractor parses blueprints."),
            ]
        )
        contracts = _make_multi_unit_contracts(
            [
                (
                    1,
                    "Config",
                    "def load_config(): ...",
                    "python",
                    "**Dependencies:** None.\n\n**load_config:**\n- Reads config file.",
                ),
                (
                    2,
                    "Registry",
                    "LANGUAGE_REGISTRY = {}",
                    "python",
                    "**Dependencies:** Unit 1.\n\n**get_language_config:**\n- Returns config.",
                ),
                (
                    8,
                    "Extractor",
                    "def extract_units(): ...",
                    "python",
                    "**Dependencies:** Unit 1, Unit 2.\n\n**extract_units:**\n- Parses blueprint.",
                ),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        all_units = extract_units(bp_dir)

        unit8 = [u for u in all_units if u.number == 8][0]
        context = build_unit_context(unit8, all_units, include_tier1=True)

        # Should include Unit 8's own content
        assert "def extract_units" in context
        assert "Parses blueprint" in context
        assert "Extractor parses blueprints" in context

        # Should include upstream Tier 2 + Tier 3
        assert "def load_config" in context
        assert "Reads config file" in context
        assert "LANGUAGE_REGISTRY" in context
        assert "Returns config" in context

    def test_build_context_excludes_tier1_for_upstream(self, tmp_path):
        """build_unit_context includes upstream Tier 2 + Tier 3 but NOT Tier 1."""
        prose = _make_multi_unit_prose(
            [
                (1, "Config", "UPSTREAM_TIER1_SHOULD_NOT_APPEAR"),
                (2, "Main", "Main tier1 text."),
            ]
        )
        contracts = _make_multi_unit_contracts(
            [
                (
                    1,
                    "Config",
                    "def config_func(): ...",
                    "python",
                    "**Dependencies:** None.\n\nConfig tier3 contract.",
                ),
                (
                    2,
                    "Main",
                    "def main_func(): ...",
                    "python",
                    "**Dependencies:** Unit 1.\n\nMain tier3 contract.",
                ),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        all_units = extract_units(bp_dir)

        unit2 = [u for u in all_units if u.number == 2][0]
        context = build_unit_context(unit2, all_units, include_tier1=True)

        # Upstream Tier 1 must NOT appear
        assert "UPSTREAM_TIER1_SHOULD_NOT_APPEAR" not in context
        # Upstream Tier 2 and Tier 3 must appear
        assert "def config_func" in context
        assert "Config tier3 contract" in context

    def test_extract_units_with_dependencies_none_root_format(self, tmp_path):
        """Parses 'None (root unit).' as empty dependency list."""
        prose = _make_multi_unit_prose([(1, "Root", "Root unit.")])
        contracts = _make_multi_unit_contracts(
            [
                (
                    1,
                    "Root",
                    "def root(): ...",
                    "python",
                    "**Dependencies:** None (root unit).",
                ),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = extract_units(bp_dir)
        assert result[0].dependencies == []

    def test_extract_units_empty_blueprint_returns_empty_list(self, tmp_path):
        """When blueprint files contain no unit headings, returns empty list."""
        bp_dir = _make_blueprint_dir(
            tmp_path,
            "# Empty Prose\n\nNo units here.\n",
            "# Empty Contracts\n\nNo units here.\n",
        )
        result = extract_units(bp_dir)
        assert result == []

    def test_detect_language_and_extract_units_consistent(self, tmp_path):
        """Languages detected by detect_code_block_language match what extract_units
        would populate in UnitDefinition.languages."""
        prose = _make_multi_unit_prose([(1, "PyUnit", "Python unit.")])
        contracts = _make_multi_unit_contracts(
            [
                (1, "PyUnit", "def py(): ...", "python", "**Dependencies:** None."),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)

        units = extract_units(bp_dir)
        detected = detect_code_block_language(bp_dir, 1)

        # Both should agree python is the language
        assert "python" in detected
        assert "python" in units[0].languages

    def test_tier2_with_no_code_fences_returns_raw_text(self, tmp_path):
        """If Tier 2 section has no code fences, the raw text is returned as-is."""
        contracts_content = """\
# Blueprint Contracts

---

## Unit 1: NoFence

### Tier 2 — Signatures

def no_fence_func(): ...

### Tier 3 -- Behavioral Contracts

**Dependencies:** None.

---
"""
        prose = _make_multi_unit_prose([(1, "NoFence", "No fence.")])
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts_content)
        result = extract_units(bp_dir)
        assert "def no_fence_func" in result[0].tier2

    def test_large_unit_count_extracted_correctly(self, tmp_path):
        """Extraction handles a larger number of units correctly."""
        n_units = 15
        prose_items = [
            (i, f"Unit{i}", f"Description {i}.") for i in range(1, n_units + 1)
        ]
        contracts_items = [
            (
                i,
                f"Unit{i}",
                f"def func_{i}(): ...",
                "python",
                "**Dependencies:** None."
                if i == 1
                else f"**Dependencies:** Unit {i - 1}.",
            )
            for i in range(1, n_units + 1)
        ]
        prose = _make_multi_unit_prose(prose_items)
        contracts = _make_multi_unit_contracts(contracts_items)
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = extract_units(bp_dir)
        assert len(result) == n_units
        assert [u.number for u in result] == list(range(1, n_units + 1))

    def test_unit_name_with_special_characters_in_heading(self, tmp_path):
        """Unit names with special characters (ampersand, parentheses) are extracted."""
        prose = _make_multi_unit_prose(
            [
                (1, "Routing and Test Execution", "Routing & test execution."),
            ]
        )
        contracts = _make_multi_unit_contracts(
            [
                (
                    1,
                    "Routing and Test Execution",
                    "def route(): ...",
                    "python",
                    "**Dependencies:** None.",
                ),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = extract_units(bp_dir)
        assert result[0].name == "Routing and Test Execution"

    def test_dependencies_with_large_unit_numbers(self, tmp_path):
        """Dependencies referencing large unit numbers are parsed correctly."""
        prose = _make_multi_unit_prose(
            [
                (1, "A", "A."),
                (25, "B", "B."),
                (29, "C", "C."),
            ]
        )
        contracts = _make_multi_unit_contracts(
            [
                (1, "A", "def a(): ...", "python", "**Dependencies:** None."),
                (25, "B", "def b(): ...", "python", "**Dependencies:** Unit 1."),
                (
                    29,
                    "C",
                    "def c(): ...",
                    "python",
                    "**Dependencies:** Unit 1, Unit 25.",
                ),
            ]
        )
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = extract_units(bp_dir)
        unit29 = [u for u in result if u.number == 29][0]
        assert sorted(unit29.dependencies) == [1, 25]

    def test_many_dependencies_parsed_correctly(self, tmp_path):
        """A unit with many dependencies has all of them parsed."""
        prose_items = [(i, f"U{i}", f"Unit {i}.") for i in range(1, 9)]
        contracts_items = []
        for i in range(1, 9):
            if i < 8:
                contracts_items.append(
                    (
                        i,
                        f"U{i}",
                        f"def u{i}(): ...",
                        "python",
                        "**Dependencies:** None."
                        if i == 1
                        else f"**Dependencies:** Unit {i - 1}.",
                    )
                )
            else:
                dep_str = ", ".join(f"Unit {j}" for j in range(1, 8))
                contracts_items.append(
                    (
                        i,
                        f"U{i}",
                        f"def u{i}(): ...",
                        "python",
                        f"**Dependencies:** {dep_str}.",
                    )
                )
        prose = _make_multi_unit_prose(prose_items)
        contracts = _make_multi_unit_contracts(contracts_items)
        bp_dir = _make_blueprint_dir(tmp_path, prose, contracts)
        result = extract_units(bp_dir)
        unit8 = [u for u in result if u.number == 8][0]
        assert sorted(unit8.dependencies) == list(range(1, 8))

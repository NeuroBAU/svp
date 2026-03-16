"""
Tests for Unit 5: Blueprint Extractor.

Synthetic Data Assumptions:
- Blueprint prose file uses '## Unit N:' heading patterns
  to delimit unit definitions.
- Blueprint contracts file uses '### Tier 2 -- Signatures'
  (em-dash) sub-headings for signature blocks.
- Tier 1 content is the description paragraph(s) between
  the unit heading and the first Tier 2/3 sub-heading.
- Tier 2 content is enclosed in python fenced code blocks
  after '### Tier 2 -- Signatures'.
- Tier 3 behavioral contracts appear after
  '### Tier 3 -- Behavioral Contracts'.
- Tier 3 dependencies appear after
  '### Tier 3 -- Dependencies'.
- Unit numbers are positive integers extracted from headings.
- Unit names follow the colon after the unit number.
- Dependencies are listed as 'Unit N' references or 'None'.
- Two-file architecture: blueprint_prose.md has Tier 1,
  blueprint_contracts.md has Tier 2 and Tier 3.
- Single-file architecture: one file contains all tiers.
- Temporary directories are used for all file I/O.
"""

import textwrap

import pytest

# ---------------------------------------------------------
# Synthetic blueprint content factories
# ---------------------------------------------------------

SINGLE_UNIT_PROSE = textwrap.dedent("""\
    ## Unit 1: Widget Manager

    **Artifact category:** Python script

    ### Tier 1 -- Description

    Manages widgets and their lifecycle.

    ---
""")

SINGLE_UNIT_CONTRACTS = textwrap.dedent("""\
    ## Unit 1: Widget Manager

    **Artifact category:** Python script

    ### Tier 2 -- Signatures

    ```python
    def create_widget(name: str) -> dict: ...

    def delete_widget(widget_id: int) -> bool: ...
    ```

    ### Tier 3 -- Behavioral Contracts

    - `create_widget` returns a dict with 'id' and 'name'.
    - `delete_widget` returns True on success.

    ### Tier 3 -- Dependencies

    None.

    ---
""")

MULTI_UNIT_PROSE = textwrap.dedent("""\
    ## Unit 1: Widget Manager

    **Artifact category:** Python script

    ### Tier 1 -- Description

    Manages widgets and their lifecycle.

    ---

    ## Unit 2: Widget Store

    **Artifact category:** Python script

    ### Tier 1 -- Description

    Persists widgets to disk.

    ---

    ## Unit 3: Widget API

    **Artifact category:** Python script

    ### Tier 1 -- Description

    HTTP API layer for widget operations.

    ---
""")

MULTI_UNIT_CONTRACTS = textwrap.dedent("""\
    ## Unit 1: Widget Manager

    **Artifact category:** Python script

    ### Tier 2 -- Signatures

    ```python
    def create_widget(name: str) -> dict: ...
    ```

    ### Tier 3 -- Behavioral Contracts

    - `create_widget` returns dict with id and name.

    ### Tier 3 -- Dependencies

    None.

    ---

    ## Unit 2: Widget Store

    **Artifact category:** Python script

    ### Tier 2 -- Signatures

    ```python
    def save_widget(widget: dict) -> bool: ...
    ```

    ### Tier 3 -- Behavioral Contracts

    - `save_widget` persists to JSON.

    ### Tier 3 -- Dependencies

    - **Unit 1 (Widget Manager):** Uses `create_widget`.

    ---

    ## Unit 3: Widget API

    **Artifact category:** Python script

    ### Tier 2 -- Signatures

    ```python
    def handle_request(req: dict) -> dict: ...
    ```

    ### Tier 3 -- Behavioral Contracts

    - `handle_request` dispatches to manager.

    ### Tier 3 -- Dependencies

    - **Unit 1 (Widget Manager):** Uses `create_widget`.
    - **Unit 2 (Widget Store):** Uses `save_widget`.

    ---
""")

SINGLE_FILE_BLUEPRINT = textwrap.dedent("""\
    ## Unit 1: Widget Manager

    **Artifact category:** Python script

    ### Tier 1 -- Description

    Manages widgets and their lifecycle.

    ### Tier 2 -- Signatures

    ```python
    def create_widget(name: str) -> dict: ...
    ```

    ### Tier 3 -- Behavioral Contracts

    - `create_widget` returns dict with id and name.

    ### Tier 3 -- Dependencies

    None.

    ---

    ## Unit 2: Widget Store

    **Artifact category:** Python script

    ### Tier 1 -- Description

    Persists widgets to disk.

    ### Tier 2 -- Signatures

    ```python
    def save_widget(widget: dict) -> bool: ...
    ```

    ### Tier 3 -- Behavioral Contracts

    - `save_widget` persists to JSON.

    ### Tier 3 -- Dependencies

    - **Unit 1 (Widget Manager):** Uses `create_widget`.

    ---
""")


@pytest.fixture
def tmp_prose(tmp_path):
    """Write multi-unit prose file, return path."""
    p = tmp_path / "blueprint_prose.md"
    p.write_text(MULTI_UNIT_PROSE, encoding="utf-8")
    return p


@pytest.fixture
def tmp_contracts(tmp_path):
    """Write multi-unit contracts file, return path."""
    p = tmp_path / "blueprint_contracts.md"
    p.write_text(MULTI_UNIT_CONTRACTS, encoding="utf-8")
    return p


@pytest.fixture
def tmp_single_file(tmp_path):
    """Write single-file blueprint, return path."""
    p = tmp_path / "blueprint.md"
    p.write_text(SINGLE_FILE_BLUEPRINT, encoding="utf-8")
    return p


@pytest.fixture
def tmp_single_prose(tmp_path):
    """Write single-unit prose file, return path."""
    p = tmp_path / "blueprint_prose.md"
    p.write_text(SINGLE_UNIT_PROSE, encoding="utf-8")
    return p


@pytest.fixture
def tmp_single_contracts(tmp_path):
    """Write single-unit contracts file, return path."""
    p = tmp_path / "blueprint_contracts.md"
    p.write_text(SINGLE_UNIT_CONTRACTS, encoding="utf-8")
    return p


# =========================================================
# UnitDefinition class tests
# =========================================================


class TestUnitDefinitionInit:
    """UnitDefinition.__init__ contracts."""

    def test_init_stores_all_fields(self):
        """All keyword args stored as attributes."""
        from src.unit_5.stub import UnitDefinition

        ud = UnitDefinition(
            unit_number=1,
            unit_name="Widget",
            description="Manages widgets.",
            signatures="def foo(): ...",
            invariants="",
            error_conditions="",
            behavioral_contracts="- foo returns 1",
            dependencies=[],
        )
        assert ud.unit_number == 1
        assert ud.unit_name == "Widget"
        assert ud.description == "Manages widgets."
        assert ud.signatures == "def foo(): ..."
        assert ud.invariants == ""
        assert ud.error_conditions == ""
        assert ud.behavioral_contracts == "- foo returns 1"
        assert ud.dependencies == []

    def test_init_with_dependencies(self):
        """Dependencies list is preserved."""
        from src.unit_5.stub import UnitDefinition

        ud = UnitDefinition(
            unit_number=3,
            unit_name="API",
            description="",
            signatures="",
            invariants="",
            error_conditions="",
            behavioral_contracts="",
            dependencies=[1, 2],
        )
        assert ud.dependencies == [1, 2]

    def test_unit_number_type(self):
        """unit_number is an int."""
        from src.unit_5.stub import UnitDefinition

        ud = UnitDefinition(
            unit_number=5,
            unit_name="Test",
            description="",
            signatures="",
            invariants="",
            error_conditions="",
            behavioral_contracts="",
            dependencies=[],
        )
        assert isinstance(ud.unit_number, int)

    def test_unit_name_type(self):
        """unit_name is a str."""
        from src.unit_5.stub import UnitDefinition

        ud = UnitDefinition(
            unit_number=1,
            unit_name="Manager",
            description="",
            signatures="",
            invariants="",
            error_conditions="",
            behavioral_contracts="",
            dependencies=[],
        )
        assert isinstance(ud.unit_name, str)

    def test_dependencies_type(self):
        """dependencies is a list."""
        from src.unit_5.stub import UnitDefinition

        ud = UnitDefinition(
            unit_number=1,
            unit_name="X",
            description="",
            signatures="",
            invariants="",
            error_conditions="",
            behavioral_contracts="",
            dependencies=[1, 2, 3],
        )
        assert isinstance(ud.dependencies, list)


# =========================================================
# parse_blueprint tests
# =========================================================


class TestParseBlueprint:
    """parse_blueprint function contracts."""

    def test_single_file_returns_list(self, tmp_single_file):
        """Single-file parse returns list of UnitDefinition."""
        from src.unit_5.stub import parse_blueprint

        result = parse_blueprint(tmp_single_file)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_single_file_unit_count(self, tmp_single_file):
        """Single-file with 2 units returns 2 definitions."""
        from src.unit_5.stub import parse_blueprint

        result = parse_blueprint(tmp_single_file)
        assert len(result) == 2

    def test_single_file_unit_numbers(self, tmp_single_file):
        """Extracted unit numbers match heading numbers."""
        from src.unit_5.stub import parse_blueprint

        result = parse_blueprint(tmp_single_file)
        numbers = [u.unit_number for u in result]
        assert 1 in numbers
        assert 2 in numbers

    def test_single_file_unit_names(self, tmp_single_file):
        """Extracted unit names match heading names."""
        from src.unit_5.stub import parse_blueprint

        result = parse_blueprint(tmp_single_file)
        names = {u.unit_number: u.unit_name for u in result}
        assert "Widget Manager" in names[1]
        assert "Widget Store" in names[2]

    def test_single_file_signatures_populated(self, tmp_single_file):
        """Signatures field contains code block content."""
        from src.unit_5.stub import parse_blueprint

        result = parse_blueprint(tmp_single_file)
        unit1 = [u for u in result if u.unit_number == 1][0]
        assert "create_widget" in unit1.signatures

    def test_single_file_contracts_populated(self, tmp_single_file):
        """Behavioral contracts field is populated."""
        from src.unit_5.stub import parse_blueprint

        result = parse_blueprint(tmp_single_file)
        unit1 = [u for u in result if u.unit_number == 1][0]
        assert "create_widget" in unit1.behavioral_contracts

    def test_two_file_returns_list(self, tmp_prose, tmp_contracts):
        """Two-file parse returns list of UnitDefinition."""
        from src.unit_5.stub import parse_blueprint

        result = parse_blueprint(tmp_prose, contracts_path=tmp_contracts)
        assert isinstance(result, list)

    def test_two_file_unit_count(self, tmp_prose, tmp_contracts):
        """Two-file with 3 units returns 3 definitions."""
        from src.unit_5.stub import parse_blueprint

        result = parse_blueprint(tmp_prose, contracts_path=tmp_contracts)
        assert len(result) == 3

    def test_two_file_tier1_from_prose(self, tmp_prose, tmp_contracts):
        """Tier 1 description sourced from prose file."""
        from src.unit_5.stub import parse_blueprint

        result = parse_blueprint(tmp_prose, contracts_path=tmp_contracts)
        unit1 = [u for u in result if u.unit_number == 1][0]
        assert "Manages widgets" in unit1.description

    def test_two_file_tier2_from_contracts(self, tmp_prose, tmp_contracts):
        """Tier 2 signatures sourced from contracts file."""
        from src.unit_5.stub import parse_blueprint

        result = parse_blueprint(tmp_prose, contracts_path=tmp_contracts)
        unit1 = [u for u in result if u.unit_number == 1][0]
        assert "create_widget" in unit1.signatures

    def test_two_file_tier3_from_contracts(self, tmp_prose, tmp_contracts):
        """Tier 3 contracts sourced from contracts file."""
        from src.unit_5.stub import parse_blueprint

        result = parse_blueprint(tmp_prose, contracts_path=tmp_contracts)
        unit2 = [u for u in result if u.unit_number == 2][0]
        assert "save_widget" in unit2.behavioral_contracts

    def test_returns_unit_definition_instances(self, tmp_single_file):
        """Each element is a UnitDefinition instance."""
        from src.unit_5.stub import (
            UnitDefinition,
            parse_blueprint,
        )

        result = parse_blueprint(tmp_single_file)
        for item in result:
            assert isinstance(item, UnitDefinition)

    def test_heading_pattern_unit_n_colon(self, tmp_single_file):
        """Parser recognizes '## Unit N:' heading pattern."""
        from src.unit_5.stub import parse_blueprint

        result = parse_blueprint(tmp_single_file)
        assert len(result) >= 1
        assert result[0].unit_number == 1

    def test_contracts_path_none_single_file(self, tmp_single_file):
        """contracts_path=None reads all tiers from one file."""
        from src.unit_5.stub import parse_blueprint

        result = parse_blueprint(tmp_single_file, contracts_path=None)
        unit1 = [u for u in result if u.unit_number == 1][0]
        assert unit1.description != ""
        assert unit1.signatures != ""


# =========================================================
# extract_unit tests
# =========================================================


class TestExtractUnit:
    """extract_unit function contracts."""

    def test_returns_unit_definition(self, tmp_single_file):
        """Returns a UnitDefinition for valid unit number."""
        from src.unit_5.stub import (
            UnitDefinition,
            extract_unit,
        )

        result = extract_unit(tmp_single_file, 1)
        assert isinstance(result, UnitDefinition)

    def test_correct_unit_number(self, tmp_single_file):
        """Returned definition has matching unit_number."""
        from src.unit_5.stub import extract_unit

        result = extract_unit(tmp_single_file, 1)
        assert result.unit_number == 1

    def test_correct_unit_name(self, tmp_single_file):
        """Returned definition has correct unit_name."""
        from src.unit_5.stub import extract_unit

        result = extract_unit(tmp_single_file, 1)
        assert "Widget Manager" in result.unit_name

    def test_extract_second_unit(self, tmp_single_file):
        """Can extract non-first unit."""
        from src.unit_5.stub import extract_unit

        result = extract_unit(tmp_single_file, 2)
        assert result.unit_number == 2
        assert "Widget Store" in result.unit_name

    def test_two_file_extract(self, tmp_prose, tmp_contracts):
        """Two-file extraction merges prose and contracts."""
        from src.unit_5.stub import extract_unit

        result = extract_unit(tmp_prose, 1, contracts_path=tmp_contracts)
        assert result.unit_number == 1
        assert "Manages widgets" in result.description
        assert "create_widget" in result.signatures

    def test_two_file_extract_unit2(self, tmp_prose, tmp_contracts):
        """Two-file extraction for unit with dependencies."""
        from src.unit_5.stub import extract_unit

        result = extract_unit(tmp_prose, 2, contracts_path=tmp_contracts)
        assert result.unit_number == 2
        assert "save_widget" in result.signatures

    def test_signatures_contain_function_defs(self, tmp_single_file):
        """Signatures field has function definitions."""
        from src.unit_5.stub import extract_unit

        result = extract_unit(tmp_single_file, 1)
        assert "def " in result.signatures

    def test_description_populated(self, tmp_single_file):
        """Description field populated from Tier 1."""
        from src.unit_5.stub import extract_unit

        result = extract_unit(tmp_single_file, 1)
        assert len(result.description) > 0

    def test_invalid_unit_number_raises(self, tmp_single_file):
        """Non-existent unit number raises an error."""
        from src.unit_5.stub import extract_unit

        with pytest.raises(Exception):
            extract_unit(tmp_single_file, 999)


# =========================================================
# extract_upstream_contracts tests
# =========================================================


class TestExtractUpstreamContracts:
    """extract_upstream_contracts function contracts."""

    def test_unit_with_no_deps_returns_empty(self, tmp_single_file):
        """Unit 1 (no deps) returns empty list."""
        from src.unit_5.stub import extract_upstream_contracts

        result = extract_upstream_contracts(tmp_single_file, 1)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_unit_with_deps_returns_contracts(self, tmp_single_file):
        """Unit 2 (depends on 1) returns upstream info."""
        from src.unit_5.stub import extract_upstream_contracts

        result = extract_upstream_contracts(tmp_single_file, 2)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_upstream_contract_is_dict(self, tmp_single_file):
        """Each upstream contract is a dict."""
        from src.unit_5.stub import extract_upstream_contracts

        result = extract_upstream_contracts(tmp_single_file, 2)
        for item in result:
            assert isinstance(item, dict)

    def test_upstream_contract_has_str_values(self, tmp_single_file):
        """Dict values are strings."""
        from src.unit_5.stub import extract_upstream_contracts

        result = extract_upstream_contracts(tmp_single_file, 2)
        for item in result:
            for val in item.values():
                assert isinstance(val, str)

    def test_two_file_upstream(self, tmp_prose, tmp_contracts):
        """Two-file mode returns upstream contracts."""
        from src.unit_5.stub import extract_upstream_contracts

        result = extract_upstream_contracts(tmp_prose, 2, contracts_path=tmp_contracts)
        assert len(result) > 0

    def test_two_file_unit3_multiple_deps(self, tmp_prose, tmp_contracts):
        """Unit 3 with deps on 1 and 2 returns both."""
        from src.unit_5.stub import extract_upstream_contracts

        result = extract_upstream_contracts(tmp_prose, 3, contracts_path=tmp_contracts)
        assert len(result) >= 2

    def test_upstream_contains_signatures(self, tmp_single_file):
        """Upstream contract dicts contain signature info."""
        from src.unit_5.stub import extract_upstream_contracts

        result = extract_upstream_contracts(tmp_single_file, 2)
        assert len(result) > 0
        all_values = " ".join(v for d in result for v in d.values())
        assert "create_widget" in all_values

    def test_invalid_unit_raises(self, tmp_single_file):
        """Non-existent unit raises an error."""
        from src.unit_5.stub import extract_upstream_contracts

        with pytest.raises(Exception):
            extract_upstream_contracts(tmp_single_file, 999)


# =========================================================
# build_unit_context tests
# =========================================================


class TestBuildUnitContext:
    """build_unit_context function contracts."""

    def test_returns_string(self, tmp_single_file):
        """Returns a non-empty string."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(tmp_single_file, 1)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_includes_tier1_by_default(self, tmp_single_file):
        """Default include_tier1=True includes description."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(tmp_single_file, 1)
        assert "Manages widgets" in result

    def test_includes_tier2(self, tmp_single_file):
        """Output includes signature content."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(tmp_single_file, 1)
        assert "create_widget" in result

    def test_include_tier1_false_excludes_description(self, tmp_single_file):
        """include_tier1=False omits Tier 1 description."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(tmp_single_file, 1, include_tier1=False)
        assert "Manages widgets" not in result

    def test_include_tier1_false_keeps_signatures(self, tmp_single_file):
        """include_tier1=False still includes signatures."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(tmp_single_file, 1, include_tier1=False)
        assert "create_widget" in result

    def test_include_tier1_false_keeps_contracts(self, tmp_single_file):
        """include_tier1=False still includes contracts."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(tmp_single_file, 1, include_tier1=False)
        assert "create_widget" in result

    def test_include_tier1_true_explicit(self, tmp_single_file):
        """Explicit include_tier1=True includes Tier 1."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(tmp_single_file, 1, include_tier1=True)
        assert "Manages widgets" in result

    def test_two_file_with_tier1(self, tmp_prose, tmp_contracts):
        """Two-file mode with include_tier1=True."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(
            tmp_prose,
            1,
            include_tier1=True,
            contracts_path=tmp_contracts,
        )
        assert "Manages widgets" in result
        assert "create_widget" in result

    def test_two_file_without_tier1(self, tmp_prose, tmp_contracts):
        """Two-file mode with include_tier1=False."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(
            tmp_prose,
            1,
            include_tier1=False,
            contracts_path=tmp_contracts,
        )
        assert "Manages widgets" not in result
        assert "create_widget" in result

    def test_includes_upstream_for_dependent_unit(self, tmp_single_file):
        """Context for unit with deps includes upstream."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(tmp_single_file, 2)
        assert "create_widget" in result

    def test_invalid_unit_raises(self, tmp_single_file):
        """Non-existent unit number raises an error."""
        from src.unit_5.stub import build_unit_context

        with pytest.raises(Exception):
            build_unit_context(tmp_single_file, 999)

    def test_contracts_path_none_single_file(self, tmp_single_file):
        """contracts_path=None works for single file."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(
            tmp_single_file,
            1,
            contracts_path=None,
        )
        assert isinstance(result, str)
        assert len(result) > 0


# =========================================================
# Heading pattern parsing tests
# =========================================================


class TestHeadingPatterns:
    """Parser heading pattern recognition."""

    def test_unit_heading_pattern(self, tmp_path):
        """Recognizes '## Unit N:' heading pattern."""
        from src.unit_5.stub import parse_blueprint

        content = textwrap.dedent("""\
            ## Unit 42: Custom Thing

            **Artifact category:** Python script

            ### Tier 1 -- Description

            Does custom things.

            ### Tier 2 -- Signatures

            ```python
            def custom() -> None: ...
            ```

            ### Tier 3 -- Behavioral Contracts

            - custom does things.

            ### Tier 3 -- Dependencies

            None.

            ---
        """)
        p = tmp_path / "bp.md"
        p.write_text(content, encoding="utf-8")
        result = parse_blueprint(p)
        assert len(result) == 1
        assert result[0].unit_number == 42

    def test_tier2_em_dash_heading(self, tmp_path):
        """Recognizes '### Tier 2 -- Signatures' with em-dash."""
        from src.unit_5.stub import parse_blueprint

        content = textwrap.dedent("""\
            ## Unit 1: Test

            **Artifact category:** Python script

            ### Tier 1 -- Description

            Test unit.

            ### Tier 2 \u2014 Signatures

            ```python
            def test_fn() -> None: ...
            ```

            ### Tier 3 \u2014 Behavioral Contracts

            - test_fn does nothing.

            ### Tier 3 \u2014 Dependencies

            None.

            ---
        """)
        p = tmp_path / "bp.md"
        p.write_text(content, encoding="utf-8")
        result = parse_blueprint(p)
        assert len(result) == 1


# =========================================================
# Edge case and error tests
# =========================================================


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_empty_signatures_block(self, tmp_path):
        """Unit with empty signature block."""
        from src.unit_5.stub import parse_blueprint

        content = textwrap.dedent("""\
            ## Unit 1: Empty Sigs

            **Artifact category:** Python script

            ### Tier 1 -- Description

            Has no signatures.

            ### Tier 2 -- Signatures

            ```python
            ```

            ### Tier 3 -- Behavioral Contracts

            None.

            ### Tier 3 -- Dependencies

            None.

            ---
        """)
        p = tmp_path / "bp.md"
        p.write_text(content, encoding="utf-8")
        result = parse_blueprint(p)
        assert len(result) == 1

    def test_unit_with_no_dependencies(self, tmp_single_file):
        """Unit 1 has empty dependencies list."""
        from src.unit_5.stub import extract_unit

        result = extract_unit(tmp_single_file, 1)
        assert result.dependencies == [] or (
            isinstance(result.dependencies, list) and len(result.dependencies) == 0
        )

    def test_unit_with_dependencies_list(self, tmp_prose, tmp_contracts):
        """Unit 2 dependencies include unit 1."""
        from src.unit_5.stub import extract_unit

        result = extract_unit(tmp_prose, 2, contracts_path=tmp_contracts)
        assert 1 in result.dependencies

    def test_unit3_has_two_dependencies(self, tmp_prose, tmp_contracts):
        """Unit 3 depends on both unit 1 and unit 2."""
        from src.unit_5.stub import extract_unit

        result = extract_unit(tmp_prose, 3, contracts_path=tmp_contracts)
        assert 1 in result.dependencies
        assert 2 in result.dependencies

    def test_single_unit_prose_only(self, tmp_single_prose, tmp_single_contracts):
        """Single-unit two-file extraction."""
        from src.unit_5.stub import extract_unit

        result = extract_unit(
            tmp_single_prose,
            1,
            contracts_path=tmp_single_contracts,
        )
        assert result.unit_number == 1
        assert "Manages widgets" in result.description
        assert "create_widget" in result.signatures
        assert "delete_widget" in result.signatures


# =========================================================
# Return type contract tests
# =========================================================


class TestReturnTypeContracts:
    """Verify return type contracts for all functions."""

    def test_parse_blueprint_returns_list(self, tmp_single_file):
        """parse_blueprint returns List[UnitDefinition]."""
        from src.unit_5.stub import parse_blueprint

        result = parse_blueprint(tmp_single_file)
        assert isinstance(result, list)

    def test_extract_unit_returns_unit_def(self, tmp_single_file):
        """extract_unit returns UnitDefinition."""
        from src.unit_5.stub import (
            UnitDefinition,
            extract_unit,
        )

        result = extract_unit(tmp_single_file, 1)
        assert isinstance(result, UnitDefinition)

    def test_extract_upstream_returns_list_of_dicts(self, tmp_single_file):
        """extract_upstream_contracts returns List[Dict]."""
        from src.unit_5.stub import extract_upstream_contracts

        result = extract_upstream_contracts(tmp_single_file, 2)
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, dict)

    def test_build_unit_context_returns_str(self, tmp_single_file):
        """build_unit_context returns str."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(tmp_single_file, 1)
        assert isinstance(result, str)

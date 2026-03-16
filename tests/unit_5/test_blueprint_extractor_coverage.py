"""
Coverage-gap tests for Unit 5: Blueprint Extractor.

These tests close gaps identified by comparing the
existing 59 tests against the blueprint Tier 2 signatures
and Tier 3 behavioral contracts.

Gaps addressed:
- extract_upstream_contracts dict key verification
- Two-file isolation: Tier 1 only from prose
- Two-file isolation: Tier 2/3 only from contracts
- UnitDefinition defaults when no kwargs provided
- build_unit_context includes behavioral_contracts
- Tier 3 heading patterns (double-hyphen --)
- extract_unit contracts_path passthrough
- build_unit_context upstream description exclusion
"""

import textwrap

import pytest

# ---------------------------------------------------------
# Synthetic content for isolation tests
# ---------------------------------------------------------

PROSE_WITH_DESCRIPTION = textwrap.dedent("""\
    ## Unit 1: Isolated Widget

    **Artifact category:** Python script

    ### Tier 1 -- Description

    Prose-only description content.

    ---
""")

CONTRACTS_WITH_ALL_TIERS = textwrap.dedent("""\
    ## Unit 1: Isolated Widget

    **Artifact category:** Python script

    ### Tier 2 -- Signatures

    ```python
    def isolated_fn(x: int) -> str: ...
    ```

    ### Tier 3 -- Behavioral Contracts

    - `isolated_fn` converts int to string.

    ### Tier 3 -- Dependencies

    None.

    ---
""")

# Contracts file that also contains a description
# section to test isolation.
CONTRACTS_WITH_DESC = textwrap.dedent("""\
    ## Unit 1: Isolated Widget

    **Artifact category:** Python script

    ### Tier 1 -- Description

    Contracts-file description that should be ignored.

    ### Tier 2 -- Signatures

    ```python
    def isolated_fn(x: int) -> str: ...
    ```

    ### Tier 3 -- Behavioral Contracts

    - `isolated_fn` converts int to string.

    ### Tier 3 -- Dependencies

    None.

    ---
""")

MULTI_UNIT_SINGLE = textwrap.dedent("""\
    ## Unit 1: Alpha

    **Artifact category:** Python script

    ### Tier 1 -- Description

    Alpha unit for upstream testing.

    ### Tier 2 -- Signatures

    ```python
    def alpha_fn() -> None: ...
    ```

    ### Tier 3 -- Behavioral Contracts

    - `alpha_fn` does alpha work.

    ### Tier 3 -- Dependencies

    None.

    ---

    ## Unit 2: Beta

    **Artifact category:** Python script

    ### Tier 1 -- Description

    Beta unit depends on Alpha.

    ### Tier 2 -- Signatures

    ```python
    def beta_fn() -> None: ...
    ```

    ### Tier 3 -- Behavioral Contracts

    - `beta_fn` does beta work.

    ### Tier 3 -- Dependencies

    - **Unit 1 (Alpha):** Uses `alpha_fn`.

    ---
""")


@pytest.fixture
def prose_file(tmp_path):
    """Prose-only file for isolation tests."""
    p = tmp_path / "blueprint_prose.md"
    p.write_text(
        PROSE_WITH_DESCRIPTION, encoding="utf-8"
    )
    return p


@pytest.fixture
def contracts_file(tmp_path):
    """Contracts-only file for isolation tests."""
    p = tmp_path / "blueprint_contracts.md"
    p.write_text(
        CONTRACTS_WITH_ALL_TIERS, encoding="utf-8"
    )
    return p


@pytest.fixture
def contracts_with_desc_file(tmp_path):
    """Contracts file that also has Tier 1 content."""
    p = tmp_path / "blueprint_contracts.md"
    p.write_text(
        CONTRACTS_WITH_DESC, encoding="utf-8"
    )
    return p


@pytest.fixture
def multi_unit_file(tmp_path):
    """Single file with two units and a dependency."""
    p = tmp_path / "blueprint.md"
    p.write_text(
        MULTI_UNIT_SINGLE, encoding="utf-8"
    )
    return p


# =========================================================
# Upstream contract dict key verification
# =========================================================


class TestUpstreamContractKeys:
    """Verify dict keys from extract_upstream_contracts."""

    def test_dict_has_unit_number_key(
        self, multi_unit_file
    ):
        """Returned dict contains 'unit_number' key."""
        from src.unit_5.stub import (
            extract_upstream_contracts,
        )

        result = extract_upstream_contracts(
            multi_unit_file, 2
        )
        assert len(result) > 0
        assert "unit_number" in result[0]

    def test_dict_has_unit_name_key(
        self, multi_unit_file
    ):
        """Returned dict contains 'unit_name' key."""
        from src.unit_5.stub import (
            extract_upstream_contracts,
        )

        result = extract_upstream_contracts(
            multi_unit_file, 2
        )
        assert "unit_name" in result[0]

    def test_dict_has_signatures_key(
        self, multi_unit_file
    ):
        """Returned dict contains 'signatures' key."""
        from src.unit_5.stub import (
            extract_upstream_contracts,
        )

        result = extract_upstream_contracts(
            multi_unit_file, 2
        )
        assert "signatures" in result[0]

    def test_dict_unit_number_value(
        self, multi_unit_file
    ):
        """unit_number value matches upstream unit."""
        from src.unit_5.stub import (
            extract_upstream_contracts,
        )

        result = extract_upstream_contracts(
            multi_unit_file, 2
        )
        assert result[0]["unit_number"] == "1"

    def test_dict_unit_name_value(
        self, multi_unit_file
    ):
        """unit_name value matches upstream unit name."""
        from src.unit_5.stub import (
            extract_upstream_contracts,
        )

        result = extract_upstream_contracts(
            multi_unit_file, 2
        )
        assert "Alpha" in result[0]["unit_name"]

    def test_dict_signatures_value(
        self, multi_unit_file
    ):
        """signatures value has upstream signatures."""
        from src.unit_5.stub import (
            extract_upstream_contracts,
        )

        result = extract_upstream_contracts(
            multi_unit_file, 2
        )
        assert "alpha_fn" in result[0]["signatures"]


# =========================================================
# Two-file isolation tests
# =========================================================


class TestTwoFileIsolation:
    """Verify two-file architecture isolation."""

    def test_tier1_from_prose_file(
        self, prose_file, contracts_file
    ):
        """Tier 1 description sourced from prose."""
        from src.unit_5.stub import extract_unit

        result = extract_unit(
            prose_file,
            1,
            contracts_path=contracts_file,
        )
        assert "Prose-only description" in (
            result.description
        )

    def test_tier2_from_contracts_file(
        self, prose_file, contracts_file
    ):
        """Tier 2 signatures sourced from contracts."""
        from src.unit_5.stub import extract_unit

        result = extract_unit(
            prose_file,
            1,
            contracts_path=contracts_file,
        )
        assert "isolated_fn" in result.signatures

    def test_tier3_contracts_from_contracts_file(
        self, prose_file, contracts_file
    ):
        """Tier 3 behavioral contracts from contracts."""
        from src.unit_5.stub import extract_unit

        result = extract_unit(
            prose_file,
            1,
            contracts_path=contracts_file,
        )
        assert "isolated_fn" in (
            result.behavioral_contracts
        )

    def test_prose_has_no_signatures(
        self, prose_file, contracts_file
    ):
        """Prose file alone has no signatures."""
        from src.unit_5.stub import parse_blueprint

        result = parse_blueprint(prose_file)
        unit1 = [
            u for u in result if u.unit_number == 1
        ][0]
        assert unit1.signatures == ""

    def test_parse_blueprint_contracts_path(
        self, prose_file, contracts_file
    ):
        """parse_blueprint with contracts_path merges."""
        from src.unit_5.stub import parse_blueprint

        result = parse_blueprint(
            prose_file,
            contracts_path=contracts_file,
        )
        unit1 = [
            u for u in result if u.unit_number == 1
        ][0]
        assert "Prose-only description" in (
            unit1.description
        )
        assert "isolated_fn" in unit1.signatures


# =========================================================
# UnitDefinition defaults
# =========================================================


class TestUnitDefinitionDefaults:
    """UnitDefinition kwargs defaults."""

    def test_default_unit_number(self):
        """Default unit_number is 0."""
        from src.unit_5.stub import UnitDefinition

        ud = UnitDefinition()
        assert ud.unit_number == 0

    def test_default_unit_name(self):
        """Default unit_name is empty string."""
        from src.unit_5.stub import UnitDefinition

        ud = UnitDefinition()
        assert ud.unit_name == ""

    def test_default_description(self):
        """Default description is empty string."""
        from src.unit_5.stub import UnitDefinition

        ud = UnitDefinition()
        assert ud.description == ""

    def test_default_signatures(self):
        """Default signatures is empty string."""
        from src.unit_5.stub import UnitDefinition

        ud = UnitDefinition()
        assert ud.signatures == ""

    def test_default_dependencies(self):
        """Default dependencies is empty list."""
        from src.unit_5.stub import UnitDefinition

        ud = UnitDefinition()
        assert ud.dependencies == []

    def test_default_behavioral_contracts(self):
        """Default behavioral_contracts is empty."""
        from src.unit_5.stub import UnitDefinition

        ud = UnitDefinition()
        assert ud.behavioral_contracts == ""

    def test_default_invariants(self):
        """Default invariants is empty string."""
        from src.unit_5.stub import UnitDefinition

        ud = UnitDefinition()
        assert ud.invariants == ""

    def test_default_error_conditions(self):
        """Default error_conditions is empty string."""
        from src.unit_5.stub import UnitDefinition

        ud = UnitDefinition()
        assert ud.error_conditions == ""


# =========================================================
# build_unit_context behavioral contracts output
# =========================================================


class TestBuildUnitContextBehavioral:
    """build_unit_context output content verification."""

    def test_includes_behavioral_contracts_text(
        self, multi_unit_file
    ):
        """Output includes behavioral contracts."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(
            multi_unit_file, 1
        )
        assert "alpha_fn" in result
        assert "alpha work" in result

    def test_includes_tier3_heading(
        self, multi_unit_file
    ):
        """Output includes Tier 3 heading."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(
            multi_unit_file, 1
        )
        assert "Behavioral Contracts" in result

    def test_upstream_section_for_dependent(
        self, multi_unit_file
    ):
        """Dependent unit context has upstream."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(
            multi_unit_file, 2
        )
        assert "Upstream" in result
        assert "Alpha" in result

    def test_upstream_includes_dep_signatures(
        self, multi_unit_file
    ):
        """Upstream section includes dep signatures."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(
            multi_unit_file, 2
        )
        assert "alpha_fn" in result

    def test_tier1_false_excludes_upstream_desc(
        self, multi_unit_file
    ):
        """include_tier1=False excludes upstream desc."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(
            multi_unit_file,
            2,
            include_tier1=False,
        )
        assert "Alpha unit for upstream" not in result

    def test_tier1_true_includes_upstream_desc(
        self, multi_unit_file
    ):
        """include_tier1=True includes upstream desc."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(
            multi_unit_file,
            2,
            include_tier1=True,
        )
        assert "Alpha unit for upstream" in result

    def test_two_file_build_context(
        self, prose_file, contracts_file
    ):
        """build_unit_context with two-file mode."""
        from src.unit_5.stub import build_unit_context

        result = build_unit_context(
            prose_file,
            1,
            contracts_path=contracts_file,
        )
        assert "Prose-only description" in result
        assert "isolated_fn" in result


# =========================================================
# Heading pattern: double-hyphen for Tier 3
# =========================================================


class TestTier3HeadingPatterns:
    """Tier 3 heading pattern recognition."""

    def test_tier3_double_hyphen_behavioral(
        self, tmp_path
    ):
        """Recognizes Tier 3 -- Behavioral Contracts."""
        from src.unit_5.stub import parse_blueprint

        content = textwrap.dedent("""\
            ## Unit 1: Heading Test

            **Artifact category:** Python script

            ### Tier 1 -- Description

            Testing heading patterns.

            ### Tier 2 -- Signatures

            ```python
            def heading_fn() -> None: ...
            ```

            ### Tier 3 -- Behavioral Contracts

            - heading_fn does heading work.

            ### Tier 3 -- Dependencies

            None.

            ---
        """)
        p = tmp_path / "bp.md"
        p.write_text(content, encoding="utf-8")
        result = parse_blueprint(p)
        assert len(result) == 1
        assert "heading_fn" in (
            result[0].behavioral_contracts
        )

    def test_tier3_double_hyphen_dependencies(
        self, tmp_path
    ):
        """Recognizes Tier 3 -- Dependencies heading."""
        from src.unit_5.stub import parse_blueprint

        content = textwrap.dedent("""\
            ## Unit 1: Dep Heading

            **Artifact category:** Python script

            ### Tier 1 -- Description

            Test deps heading.

            ### Tier 2 -- Signatures

            ```python
            def dep_fn() -> None: ...
            ```

            ### Tier 3 -- Behavioral Contracts

            - dep_fn works.

            ### Tier 3 -- Dependencies

            None.

            ---
        """)
        p = tmp_path / "bp.md"
        p.write_text(content, encoding="utf-8")
        result = parse_blueprint(p)
        assert result[0].dependencies == []


# =========================================================
# extract_unit contracts_path passthrough
# =========================================================


class TestExtractUnitContractsPath:
    """extract_unit passes contracts_path through."""

    def test_extract_unit_with_contracts_path(
        self, prose_file, contracts_file
    ):
        """extract_unit merges via contracts_path."""
        from src.unit_5.stub import (
            UnitDefinition,
            extract_unit,
        )

        result = extract_unit(
            prose_file,
            1,
            contracts_path=contracts_file,
        )
        assert isinstance(result, UnitDefinition)
        assert result.unit_number == 1
        assert "isolated_fn" in result.signatures
        assert "Prose-only description" in (
            result.description
        )

    def test_extract_unit_no_contracts_path(
        self, multi_unit_file
    ):
        """extract_unit without contracts_path works."""
        from src.unit_5.stub import extract_unit

        result = extract_unit(multi_unit_file, 1)
        assert result.unit_number == 1
        assert "alpha_fn" in result.signatures

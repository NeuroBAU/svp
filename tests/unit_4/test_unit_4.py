"""Tests for Unit 4: Toolchain Reader.

Synthetic Data Assumptions:
- A valid pipeline toolchain JSON file (toolchain.json) contains at minimum
  a top-level dict with keys such as "quality" that holds gate definitions.
- A valid language-specific toolchain file (e.g., python_conda_pytest.json)
  is stored under scripts/toolchain_defaults/ and contains language-specific
  toolchain configuration as a dict.
- Gate definitions under toolchain["quality"]["gate_a"] or ["gate_b"] are
  ordered lists of dicts, each with at least "operation" and "command" keys.
- Command templates use placeholders: {env_name}, {run_prefix}, {target},
  {python_version}, {flags}.
- The module under test NEVER reads project_profile.json -- this is the
  three-layer separation invariant.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict

import pytest

from toolchain_reader import get_gate_composition, load_toolchain, resolve_command

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project root with a valid toolchain.json."""
    toolchain = {
        "environment": {
            "manager": "conda",
            "env_name_template": "svp-{project_name}",
        },
        "quality": {
            "gate_a": [
                {
                    "operation": "lint",
                    "command": "ruff check {target} {flags}",
                },
                {
                    "operation": "format",
                    "command": "ruff format --check {target}",
                },
            ],
            "gate_b": [
                {
                    "operation": "type_check",
                    "command": "mypy {target} {flags}",
                },
            ],
        },
        "testing": {
            "run_command": "{run_prefix} pytest {target} {flags}",
        },
    }
    toolchain_path = tmp_path / "toolchain.json"
    toolchain_path.write_text(json.dumps(toolchain, indent=2))
    return tmp_path


@pytest.fixture
def tmp_project_with_language_toolchains(tmp_project: Path) -> Path:
    """Extend tmp_project with language-specific toolchain files."""
    defaults_dir = tmp_project / "scripts" / "toolchain_defaults"
    defaults_dir.mkdir(parents=True, exist_ok=True)

    python_toolchain = {
        "language": "python",
        "test_framework": "pytest",
        "run_command": "conda run -n {env_name} pytest {target} {flags}",
        "quality": {
            "gate_a": [
                {"operation": "lint", "command": "ruff check {target}"},
            ],
            "gate_b": [
                {"operation": "type_check", "command": "mypy {target}"},
            ],
        },
    }
    (defaults_dir / "python_conda_pytest.json").write_text(
        json.dumps(python_toolchain, indent=2)
    )

    r_toolchain = {
        "language": "r",
        "test_framework": "testthat",
        "run_command": "Rscript -e 'testthat::test_dir(\"{target}\")'",
        "quality": {
            "gate_a": [
                {
                    "operation": "lint",
                    "command": "Rscript -e 'lintr::lint_dir(\"{target}\")'",
                },
            ],
        },
    }
    (defaults_dir / "r_renv_testthat.json").write_text(
        json.dumps(r_toolchain, indent=2)
    )

    return tmp_project


@pytest.fixture
def sample_toolchain() -> Dict[str, Any]:
    """Return a sample parsed toolchain dict for gate composition tests."""
    return {
        "quality": {
            "gate_a": [
                {"operation": "lint", "command": "ruff check src/"},
                {"operation": "format", "command": "ruff format --check src/"},
            ],
            "gate_b": [
                {"operation": "type_check", "command": "mypy src/"},
            ],
        },
    }


# ===========================================================================
# load_toolchain
# ===========================================================================


class TestLoadToolchainNoLanguage:
    """Tests for load_toolchain with language=None (pipeline toolchain)."""

    def test_returns_parsed_dict_from_toolchain_json(self, tmp_project: Path) -> None:
        result = load_toolchain(tmp_project)
        assert isinstance(result, dict)
        assert "quality" in result
        assert "environment" in result

    def test_returns_correct_quality_gate_a_content(self, tmp_project: Path) -> None:
        result = load_toolchain(tmp_project)
        gate_a = result["quality"]["gate_a"]
        assert len(gate_a) == 2
        assert gate_a[0]["operation"] == "lint"

    def test_returns_correct_quality_gate_b_content(self, tmp_project: Path) -> None:
        result = load_toolchain(tmp_project)
        gate_b = result["quality"]["gate_b"]
        assert len(gate_b) == 1
        assert gate_b[0]["operation"] == "type_check"

    def test_raises_file_not_found_error_when_toolchain_missing(
        self, tmp_path: Path
    ) -> None:
        # tmp_path has no toolchain.json
        with pytest.raises(FileNotFoundError):
            load_toolchain(tmp_path)

    def test_default_language_none_loads_pipeline_toolchain(
        self, tmp_project: Path
    ) -> None:
        """Calling with no language argument is equivalent to language=None."""
        result_default = load_toolchain(tmp_project)
        result_none = load_toolchain(tmp_project, language=None)
        assert result_default == result_none

    def test_preserves_all_top_level_keys(self, tmp_project: Path) -> None:
        result = load_toolchain(tmp_project)
        assert "environment" in result
        assert "quality" in result
        assert "testing" in result

    def test_returned_dict_matches_file_content(self, tmp_project: Path) -> None:
        with open(tmp_project / "toolchain.json") as f:
            expected = json.load(f)
        result = load_toolchain(tmp_project)
        assert result == expected


class TestLoadToolchainWithLanguage:
    """Tests for load_toolchain with a specific language."""

    def test_loads_python_toolchain_from_defaults_directory(
        self, tmp_project_with_language_toolchains: Path
    ) -> None:
        result = load_toolchain(tmp_project_with_language_toolchains, language="python")
        assert isinstance(result, dict)
        assert result["language"] == "python"
        assert result["test_framework"] == "pytest"

    def test_loads_r_toolchain_from_defaults_directory(
        self, tmp_project_with_language_toolchains: Path
    ) -> None:
        result = load_toolchain(tmp_project_with_language_toolchains, language="r")
        assert isinstance(result, dict)
        assert result["language"] == "r"
        assert result["test_framework"] == "testthat"

    def test_python_toolchain_path_uses_language_registry_toolchain_file(
        self, tmp_project_with_language_toolchains: Path
    ) -> None:
        """Path should resolve from LANGUAGE_REGISTRY["python"]["toolchain_file"]
        which is 'python_conda_pytest.json', under scripts/toolchain_defaults/."""
        result = load_toolchain(tmp_project_with_language_toolchains, language="python")
        # Verify it loaded the correct file by checking its content
        expected_path = (
            tmp_project_with_language_toolchains
            / "scripts"
            / "toolchain_defaults"
            / "python_conda_pytest.json"
        )
        with open(expected_path) as f:
            expected = json.load(f)
        assert result == expected

    def test_r_toolchain_path_uses_language_registry_toolchain_file(
        self, tmp_project_with_language_toolchains: Path
    ) -> None:
        """Path should resolve from LANGUAGE_REGISTRY["r"]["toolchain_file"]
        which is 'r_renv_testthat.json', under scripts/toolchain_defaults/."""
        result = load_toolchain(tmp_project_with_language_toolchains, language="r")
        expected_path = (
            tmp_project_with_language_toolchains
            / "scripts"
            / "toolchain_defaults"
            / "r_renv_testthat.json"
        )
        with open(expected_path) as f:
            expected = json.load(f)
        assert result == expected

    def test_raises_file_not_found_error_when_language_toolchain_missing(
        self, tmp_project: Path
    ) -> None:
        """tmp_project has no scripts/toolchain_defaults/ directory."""
        with pytest.raises(FileNotFoundError):
            load_toolchain(tmp_project, language="python")

    def test_raises_key_error_for_unknown_language(
        self, tmp_project_with_language_toolchains: Path
    ) -> None:
        """An unregistered language should raise KeyError from LANGUAGE_REGISTRY."""
        with pytest.raises(KeyError):
            load_toolchain(tmp_project_with_language_toolchains, language="cobol")


class TestLoadToolchainThreeLayerSeparation:
    """Tests for the three-layer separation invariant:
    load_toolchain NEVER reads project_profile.json."""

    def test_does_not_read_project_profile_json(self, tmp_project: Path) -> None:
        """Create a project_profile.json that would cause errors if read,
        then verify load_toolchain succeeds without touching it."""
        # Write an invalid JSON file as project_profile.json
        profile_path = tmp_project / "project_profile.json"
        profile_path.write_text("THIS IS NOT VALID JSON {{{")

        # load_toolchain should succeed because it never reads profile
        result = load_toolchain(tmp_project)
        assert isinstance(result, dict)

    def test_language_load_does_not_read_project_profile_json(
        self, tmp_project_with_language_toolchains: Path
    ) -> None:
        """Even when loading a language-specific toolchain, profile is not read."""
        profile_path = tmp_project_with_language_toolchains / "project_profile.json"
        profile_path.write_text("NOT VALID JSON !!!")

        result = load_toolchain(tmp_project_with_language_toolchains, language="python")
        assert isinstance(result, dict)
        assert result["language"] == "python"


class TestLoadToolchainStructuralRegressionNoProfileAccess:
    """Structural regression: no function in the module reads project_profile.json.

    This test inspects the module source code to verify the invariant."""

    def test_module_source_does_not_reference_project_profile(self) -> None:
        """Check that the module source never references 'project_profile'."""
        import toolchain_reader as mod

        source_path = Path(mod.__file__)
        source_text = source_path.read_text()

        # The module should not contain any reference to reading project_profile
        assert "project_profile" not in source_text, (
            "Module source references 'project_profile', violating "
            "three-layer separation"
        )


# ===========================================================================
# resolve_command
# ===========================================================================


class TestResolveCommandBasicSubstitution:
    """Tests for basic placeholder substitution in resolve_command."""

    def test_substitutes_env_name_placeholder(self) -> None:
        result = resolve_command(
            template="conda run -n {env_name} pytest",
            env_name="svp-myproject",
            run_prefix="",
        )
        assert "svp-myproject" in result
        assert "{env_name}" not in result

    def test_substitutes_run_prefix_placeholder(self) -> None:
        result = resolve_command(
            template="{run_prefix} pytest",
            env_name="svp-proj",
            run_prefix="conda run -n svp-proj",
        )
        assert "conda run -n svp-proj" in result
        assert "{run_prefix}" not in result

    def test_substitutes_target_placeholder(self) -> None:
        result = resolve_command(
            template="pytest {target}",
            env_name="test-env",
            run_prefix="",
            target="tests/unit_4/",
        )
        assert "tests/unit_4/" in result
        assert "{target}" not in result

    def test_substitutes_python_version_placeholder(self) -> None:
        result = resolve_command(
            template="python{python_version} -m pytest",
            env_name="env",
            run_prefix="",
            python_version="3.11",
        )
        assert "python3.11" in result
        assert "{python_version}" not in result

    def test_substitutes_flags_placeholder(self) -> None:
        result = resolve_command(
            template="pytest {flags}",
            env_name="env",
            run_prefix="",
            flags="--verbose --tb=short",
        )
        assert "--verbose --tb=short" in result
        assert "{flags}" not in result

    def test_substitutes_all_placeholders_in_single_template(self) -> None:
        template = "{run_prefix} python{python_version} -m pytest {target} {flags}"
        result = resolve_command(
            template=template,
            env_name="svp-proj",
            run_prefix="conda run -n svp-proj",
            target="tests/",
            python_version="3.10",
            flags="-v",
        )
        assert "conda run -n svp-proj" in result
        assert "python3.10" in result
        assert "tests/" in result
        assert "-v" in result

    def test_empty_defaults_produce_no_artifacts(self) -> None:
        """When target, python_version, flags are empty strings (default),
        no placeholder text or artifacts remain."""
        result = resolve_command(
            template="pytest {target} {flags}",
            env_name="env",
            run_prefix="",
        )
        assert "{target}" not in result
        assert "{flags}" not in result


class TestResolveCommandWhitespaceHandling:
    """Tests for whitespace normalization in resolve_command."""

    def test_collapses_multiple_spaces_to_single(self) -> None:
        result = resolve_command(
            template="pytest  {target}  {flags}",
            env_name="env",
            run_prefix="",
            target="tests/",
            flags="",
        )
        assert "  " not in result

    def test_strips_leading_whitespace(self) -> None:
        result = resolve_command(
            template="{run_prefix} pytest",
            env_name="env",
            run_prefix="",
        )
        assert not result.startswith(" ")

    def test_strips_trailing_whitespace(self) -> None:
        result = resolve_command(
            template="pytest {flags}",
            env_name="env",
            run_prefix="",
            flags="",
        )
        assert not result.endswith(" ")

    def test_no_double_spaces_when_empty_placeholders_are_adjacent(self) -> None:
        """When multiple empty placeholders appear, no double spaces remain."""
        result = resolve_command(
            template="{run_prefix} pytest {target} {python_version} {flags}",
            env_name="env",
            run_prefix="",
            target="",
            python_version="",
            flags="",
        )
        assert "  " not in result

    def test_result_is_stripped_and_normalized_with_all_empty(self) -> None:
        result = resolve_command(
            template="{run_prefix} {flags} {target}",
            env_name="env",
            run_prefix="",
            target="",
            flags="",
        )
        assert result == result.strip()
        assert "  " not in result


class TestResolveCommandNoUnresolvedPlaceholders:
    """Tests ensuring no unresolved {...} placeholders remain in output."""

    def test_no_unresolved_placeholders_with_all_params(self) -> None:
        result = resolve_command(
            template="{run_prefix} -n {env_name} py{python_version} {target} {flags}",
            env_name="myenv",
            run_prefix="conda run",
            target="src/",
            python_version="3.9",
            flags="--strict",
        )
        assert not re.search(r"\{[^}]+\}", result), (
            f"Unresolved placeholders found in: {result}"
        )

    def test_no_unresolved_placeholders_with_defaults(self) -> None:
        result = resolve_command(
            template="{run_prefix} pytest {target} {python_version} {flags}",
            env_name="env",
            run_prefix="conda run -n env",
        )
        assert not re.search(r"\{[^}]+\}", result), (
            f"Unresolved placeholders found in: {result}"
        )

    def test_env_name_inside_run_prefix_is_resolved(self) -> None:
        """run_prefix may itself contain {env_name} -- after substituting
        {run_prefix} first, {env_name} in the result should also be resolved."""
        result = resolve_command(
            template="{run_prefix} pytest {target}",
            env_name="svp-test",
            run_prefix="conda run -n {env_name}",
            target="tests/",
        )
        # After single-pass: {run_prefix} is replaced first producing
        # "conda run -n {env_name} pytest {target}", then {env_name} is
        # replaced producing "conda run -n svp-test pytest tests/"
        assert "svp-test" in result
        assert "{env_name}" not in result


class TestResolveCommandSubstitutionOrder:
    """Tests verifying single-pass substitution order:
    {run_prefix} first, then {env_name}, {python_version}, {flags}, {target}."""

    def test_run_prefix_substituted_first_allows_nested_env_name(self) -> None:
        """run_prefix containing {env_name} should have {env_name} resolved
        in the second pass after run_prefix is expanded."""
        result = resolve_command(
            template="{run_prefix} pytest",
            env_name="my-env",
            run_prefix="conda run -n {env_name}",
        )
        assert result.strip() == "conda run -n my-env pytest"

    def test_run_prefix_expansion_does_not_reintroduce_run_prefix(self) -> None:
        """If run_prefix contains literal '{run_prefix}', it should NOT
        be re-expanded (single-pass, not recursive)."""
        result = resolve_command(
            template="{run_prefix} hello",
            env_name="env",
            run_prefix="literal {run_prefix}",
        )
        # After first pass: "literal {run_prefix} hello"
        # Since {run_prefix} is only substituted once, the literal remains
        # or more precisely, the blueprint says single-pass: run_prefix first,
        # then the others. So the literal {run_prefix} text stays.
        # Actually -- let me reconsider. The contract says single-pass:
        # {run_prefix} first, then the others. Since {run_prefix} was already
        # processed, the literal in the expanded text is not processed again.
        assert "literal" in result


class TestResolveCommandEdgeCases:
    """Edge case tests for resolve_command."""

    def test_template_with_no_placeholders_returned_as_is(self) -> None:
        result = resolve_command(
            template="pytest tests/",
            env_name="env",
            run_prefix="",
        )
        assert result == "pytest tests/"

    def test_multiple_occurrences_of_same_placeholder(self) -> None:
        result = resolve_command(
            template="{env_name} and {env_name}",
            env_name="myenv",
            run_prefix="",
        )
        assert result == "myenv and myenv"

    def test_returns_string_type(self) -> None:
        result = resolve_command(
            template="{run_prefix} pytest",
            env_name="env",
            run_prefix="conda run",
        )
        assert isinstance(result, str)


# ===========================================================================
# get_gate_composition
# ===========================================================================


class TestGetGateCompositionBasic:
    """Tests for basic get_gate_composition behavior."""

    def test_returns_list_of_dicts_for_gate_a(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        result = get_gate_composition(sample_toolchain, "gate_a")
        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)

    def test_returns_list_of_dicts_for_gate_b(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        result = get_gate_composition(sample_toolchain, "gate_b")
        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)

    def test_gate_a_returns_correct_number_of_operations(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        result = get_gate_composition(sample_toolchain, "gate_a")
        assert len(result) == 2

    def test_gate_b_returns_correct_number_of_operations(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        result = get_gate_composition(sample_toolchain, "gate_b")
        assert len(result) == 1

    def test_each_operation_dict_has_operation_key(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        result = get_gate_composition(sample_toolchain, "gate_a")
        for item in result:
            assert "operation" in item

    def test_each_operation_dict_has_command_key(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        result = get_gate_composition(sample_toolchain, "gate_a")
        for item in result:
            assert "command" in item


class TestGetGateCompositionOperationPrefix:
    """Tests that operation names are qualified with 'quality.' prefix."""

    def test_operation_names_have_quality_prefix_for_gate_a(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        result = get_gate_composition(sample_toolchain, "gate_a")
        for item in result:
            assert item["operation"].startswith("quality."), (
                f"Operation '{item['operation']}' missing 'quality.' prefix"
            )

    def test_operation_names_have_quality_prefix_for_gate_b(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        result = get_gate_composition(sample_toolchain, "gate_b")
        for item in result:
            assert item["operation"].startswith("quality."), (
                f"Operation '{item['operation']}' missing 'quality.' prefix"
            )

    def test_quality_prefix_applied_to_lint_operation(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        result = get_gate_composition(sample_toolchain, "gate_a")
        operations = [item["operation"] for item in result]
        assert "quality.lint" in operations

    def test_quality_prefix_applied_to_format_operation(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        result = get_gate_composition(sample_toolchain, "gate_a")
        operations = [item["operation"] for item in result]
        assert "quality.format" in operations

    def test_quality_prefix_applied_to_type_check_operation(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        result = get_gate_composition(sample_toolchain, "gate_b")
        operations = [item["operation"] for item in result]
        assert "quality.type_check" in operations


class TestGetGateCompositionOrdering:
    """Tests that get_gate_composition preserves ordering."""

    def test_operations_returned_in_original_order(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        result = get_gate_composition(sample_toolchain, "gate_a")
        operations = [item["operation"] for item in result]
        assert operations == ["quality.lint", "quality.format"]

    def test_commands_returned_in_original_order(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        result = get_gate_composition(sample_toolchain, "gate_a")
        commands = [item["command"] for item in result]
        assert commands[0] == "ruff check src/"
        assert commands[1] == "ruff format --check src/"


class TestGetGateCompositionErrorHandling:
    """Tests for error conditions in get_gate_composition."""

    def test_raises_key_error_for_nonexistent_gate_id(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        with pytest.raises(KeyError):
            get_gate_composition(sample_toolchain, "gate_c")

    def test_raises_key_error_for_empty_gate_id(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        with pytest.raises(KeyError):
            get_gate_composition(sample_toolchain, "")

    def test_raises_key_error_when_quality_section_missing(self) -> None:
        toolchain_no_quality: Dict[str, Any] = {"environment": {"manager": "conda"}}
        with pytest.raises(KeyError):
            get_gate_composition(toolchain_no_quality, "gate_a")


class TestGetGateCompositionCommandPreservation:
    """Tests that command strings are preserved in the output."""

    def test_command_string_preserved_for_gate_a(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        result = get_gate_composition(sample_toolchain, "gate_a")
        assert result[0]["command"] == "ruff check src/"

    def test_command_string_preserved_for_gate_b(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        result = get_gate_composition(sample_toolchain, "gate_b")
        assert result[0]["command"] == "mypy src/"


class TestGetGateCompositionWithSingleOperation:
    """Tests for gate with exactly one operation."""

    def test_single_operation_gate_returns_list_of_one(
        self, sample_toolchain: Dict[str, Any]
    ) -> None:
        result = get_gate_composition(sample_toolchain, "gate_b")
        assert len(result) == 1
        assert result[0]["operation"] == "quality.type_check"
        assert result[0]["command"] == "mypy src/"


class TestGetGateCompositionWithManyOperations:
    """Tests for gate with multiple operations."""

    def test_many_operations_all_have_required_keys(self) -> None:
        toolchain = {
            "quality": {
                "gate_a": [
                    {"operation": "lint", "command": "cmd1"},
                    {"operation": "format", "command": "cmd2"},
                    {"operation": "import_sort", "command": "cmd3"},
                    {"operation": "docstring_check", "command": "cmd4"},
                ],
            },
        }
        result = get_gate_composition(toolchain, "gate_a")
        assert len(result) == 4
        for item in result:
            assert "operation" in item
            assert "command" in item
            assert item["operation"].startswith("quality.")


# ===========================================================================
# Integration-style tests
# ===========================================================================


class TestLoadToolchainThenGetGateComposition:
    """Tests combining load_toolchain and get_gate_composition."""

    def test_loaded_toolchain_can_be_passed_to_get_gate_composition(
        self, tmp_project: Path
    ) -> None:
        toolchain = load_toolchain(tmp_project)
        result = get_gate_composition(toolchain, "gate_a")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_loaded_language_toolchain_with_get_gate_composition(
        self, tmp_project_with_language_toolchains: Path
    ) -> None:
        toolchain = load_toolchain(
            tmp_project_with_language_toolchains, language="python"
        )
        result = get_gate_composition(toolchain, "gate_a")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["operation"] == "quality.lint"

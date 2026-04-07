"""test_unit_2.py -- Test suite for Unit 2: Language Registry.

Tests all behavioral contracts from the blueprint for the language registry module,
including LANGUAGE_REGISTRY contents, key sets, get_language_config, validate_registry_entry,
validate_component_entry, load_registry_extensions, and import-time validation.

Synthetic Data Assumptions:
- The LANGUAGE_REGISTRY contains at minimum three entries: "python" (full), "r" (full), "stan" (component-only).
- FULL_REQUIRED_KEYS and COMPONENT_REQUIRED_KEYS are sets of strings representing required keys for
  full-language and component-only entries respectively.
- Extension files are JSON files containing dicts of language entries keyed by language id.
- Invalid entries use deliberately missing or wrong-typed fields to trigger validation errors.
- Temporary directories and files are created via pytest tmp_path for load_registry_extensions tests.
"""

import copy
import json

import pytest

from language_registry import (
    COMPONENT_REQUIRED_KEYS,
    FULL_REQUIRED_KEYS,
    LANGUAGE_REGISTRY,
    QualityResult,
    RunResult,
    get_language_config,
    load_registry_extensions,
    validate_component_entry,
    validate_registry_entry,
)

# ---------------------------------------------------------------------------
# RunResult and QualityResult NamedTuples
# ---------------------------------------------------------------------------


class TestRunResultNamedTuple:
    """Tests for the RunResult NamedTuple definition."""

    def test_run_result_has_status_field(self):
        r = RunResult(
            status="TESTS_PASSED",
            passed=5,
            failed=0,
            errors=0,
            output="ok",
            collection_error=False,
        )
        assert r.status == "TESTS_PASSED"

    def test_run_result_has_passed_field(self):
        r = RunResult(
            status="TESTS_PASSED",
            passed=5,
            failed=0,
            errors=0,
            output="ok",
            collection_error=False,
        )
        assert r.passed == 5

    def test_run_result_has_failed_field(self):
        r = RunResult(
            status="TESTS_FAILED",
            passed=3,
            failed=2,
            errors=0,
            output="out",
            collection_error=False,
        )
        assert r.failed == 2

    def test_run_result_has_errors_field(self):
        r = RunResult(
            status="TESTS_ERROR",
            passed=0,
            failed=0,
            errors=1,
            output="err",
            collection_error=False,
        )
        assert r.errors == 1

    def test_run_result_has_output_field(self):
        r = RunResult(
            status="TESTS_PASSED",
            passed=1,
            failed=0,
            errors=0,
            output="hello",
            collection_error=False,
        )
        assert r.output == "hello"

    def test_run_result_has_collection_error_field(self):
        r = RunResult(
            status="COLLECTION_ERROR",
            passed=0,
            failed=0,
            errors=0,
            output="err",
            collection_error=True,
        )
        assert r.collection_error is True

    def test_run_result_is_namedtuple(self):
        r = RunResult(
            status="TESTS_PASSED",
            passed=0,
            failed=0,
            errors=0,
            output="",
            collection_error=False,
        )
        assert hasattr(r, "_fields")
        assert "status" in r._fields


class TestQualityResultNamedTuple:
    """Tests for the QualityResult NamedTuple definition."""

    def test_quality_result_has_status_field(self):
        q = QualityResult(
            status="QUALITY_CLEAN", auto_fixed=False, residuals=[], report="clean"
        )
        assert q.status == "QUALITY_CLEAN"

    def test_quality_result_has_auto_fixed_field(self):
        q = QualityResult(
            status="QUALITY_AUTO_FIXED", auto_fixed=True, residuals=[], report="fixed"
        )
        assert q.auto_fixed is True

    def test_quality_result_has_residuals_field(self):
        q = QualityResult(
            status="QUALITY_RESIDUAL", auto_fixed=False, residuals=["err1"], report="r"
        )
        assert q.residuals == ["err1"]

    def test_quality_result_has_report_field(self):
        q = QualityResult(
            status="QUALITY_CLEAN", auto_fixed=False, residuals=[], report="report text"
        )
        assert q.report == "report text"

    def test_quality_result_is_namedtuple(self):
        q = QualityResult(
            status="QUALITY_CLEAN", auto_fixed=False, residuals=[], report=""
        )
        assert hasattr(q, "_fields")
        assert "status" in q._fields


# ---------------------------------------------------------------------------
# LANGUAGE_REGISTRY structure
# ---------------------------------------------------------------------------


class TestLanguageRegistryStructure:
    """Tests that LANGUAGE_REGISTRY is a dict with expected top-level keys."""

    def test_registry_is_a_dict(self):
        assert isinstance(LANGUAGE_REGISTRY, dict)

    def test_registry_contains_python_key(self):
        assert "python" in LANGUAGE_REGISTRY

    def test_registry_contains_r_key(self):
        assert "r" in LANGUAGE_REGISTRY

    def test_registry_contains_stan_key(self):
        assert "stan" in LANGUAGE_REGISTRY

    def test_registry_entries_are_dicts(self):
        for lang, entry in LANGUAGE_REGISTRY.items():
            assert isinstance(entry, dict), f"Entry for '{lang}' is not a dict"


# ---------------------------------------------------------------------------
# Python full-language entry
# ---------------------------------------------------------------------------


class TestPythonRegistryEntry:
    """Tests for the 'python' entry in LANGUAGE_REGISTRY."""

    @pytest.fixture
    def py(self):
        return LANGUAGE_REGISTRY["python"]

    def test_python_id(self, py):
        assert py["id"] == "python"

    def test_python_display_name(self, py):
        assert py["display_name"] == "Python"

    def test_python_file_extension(self, py):
        assert py["file_extension"] == ".py"

    def test_python_source_dir(self, py):
        assert py["source_dir"] == "src"

    def test_python_test_dir(self, py):
        assert py["test_dir"] == "tests"

    def test_python_test_file_pattern(self, py):
        assert py["test_file_pattern"] == "test_*.py"

    def test_python_toolchain_file(self, py):
        assert py["toolchain_file"] == "python_conda_pytest.json"

    def test_python_environment_manager(self, py):
        assert py["environment_manager"] == "conda"

    def test_python_test_framework(self, py):
        assert py["test_framework"] == "pytest"

    def test_python_version_check_command(self, py):
        assert py["version_check_command"] == "python --version"

    def test_python_stub_sentinel(self, py):
        assert (
            py["stub_sentinel"]
            == "__SVP_STUB__ = True  # DO NOT DELIVER -- stub file generated by SVP"
        )

    def test_python_stub_generator_key(self, py):
        assert py["stub_generator_key"] == "python"

    def test_python_test_output_parser_key(self, py):
        assert py["test_output_parser_key"] == "python"

    def test_python_quality_runner_key(self, py):
        assert py["quality_runner_key"] == "python"

    def test_python_is_not_component_only(self, py):
        assert py["is_component_only"] is False

    def test_python_compatible_hosts_is_empty(self, py):
        assert py["compatible_hosts"] == []

    def test_python_bridge_libraries_has_python_r(self, py):
        assert "python_r" in py["bridge_libraries"]
        assert py["bridge_libraries"]["python_r"]["library"] == "rpy2"
        assert py["bridge_libraries"]["python_r"]["conda_package"] == "rpy2"

    def test_python_collection_error_indicators(self, py):
        expected = [
            "ERROR collecting",
            "ImportError",
            "ModuleNotFoundError",
            "SyntaxError",
            "no tests ran",
        ]
        assert py["collection_error_indicators"] == expected

    def test_python_authorized_write_dirs(self, py):
        assert py["authorized_write_dirs"] == ["src", "tests", "."]

    def test_python_default_delivery_environment_recommendation(self, py):
        assert py["default_delivery"]["environment_recommendation"] == "conda"

    def test_python_default_delivery_dependency_format(self, py):
        assert py["default_delivery"]["dependency_format"] == "environment.yml"

    def test_python_default_delivery_source_layout(self, py):
        assert py["default_delivery"]["source_layout"] == "conventional"

    def test_python_default_delivery_entry_points(self, py):
        assert py["default_delivery"]["entry_points"] is False

    def test_python_default_quality_linter(self, py):
        assert py["default_quality"]["linter"] == "ruff"

    def test_python_default_quality_formatter(self, py):
        assert py["default_quality"]["formatter"] == "ruff"

    def test_python_default_quality_type_checker(self, py):
        assert py["default_quality"]["type_checker"] == "mypy"

    def test_python_default_quality_import_sorter(self, py):
        assert py["default_quality"]["import_sorter"] == "ruff"

    def test_python_default_quality_line_length(self, py):
        assert py["default_quality"]["line_length"] == 88

    def test_python_valid_linters(self, py):
        assert py["valid_linters"] == {"ruff", "flake8", "pylint", "none"}

    def test_python_valid_formatters(self, py):
        assert py["valid_formatters"] == {"ruff", "black", "autopep8", "none"}

    def test_python_valid_type_checkers(self, py):
        assert py["valid_type_checkers"] == {"mypy", "pyright", "none"}

    def test_python_valid_source_layouts(self, py):
        assert py["valid_source_layouts"] == ["conventional", "flat", "svp_native"]

    def test_python_environment_file_name(self, py):
        assert py["environment_file_name"] == "environment.yml"

    def test_python_project_manifest_file(self, py):
        assert py["project_manifest_file"] == "pyproject.toml"

    def test_python_gitignore_patterns(self, py):
        expected = ["__pycache__/", "*.pyc", ".mypy_cache/", "dist/", "*.egg-info/"]
        assert py["gitignore_patterns"] == expected

    def test_python_entry_point_mechanism(self, py):
        assert py["entry_point_mechanism"] == "pyproject_scripts"

    def test_python_quality_config_mapping_ruff(self, py):
        assert py["quality_config_mapping"]["ruff"] == "ruff.toml"

    def test_python_quality_config_mapping_black(self, py):
        assert py["quality_config_mapping"]["black"] == "pyproject.toml [tool.black]"

    def test_python_quality_config_mapping_flake8(self, py):
        assert py["quality_config_mapping"]["flake8"] == ".flake8"

    def test_python_quality_config_mapping_mypy(self, py):
        assert py["quality_config_mapping"]["mypy"] == "pyproject.toml [tool.mypy]"

    def test_python_quality_config_mapping_pyright(self, py):
        assert (
            py["quality_config_mapping"]["pyright"] == "pyproject.toml [tool.pyright]"
        )

    def test_python_non_source_embedding(self, py):
        assert py["non_source_embedding"] == "module_level_string"

    def test_python_agent_prompts_has_test_agent(self, py):
        assert "test_agent" in py["agent_prompts"]
        assert isinstance(py["agent_prompts"]["test_agent"], str)

    def test_python_agent_prompts_has_implementation_agent(self, py):
        assert "implementation_agent" in py["agent_prompts"]
        assert isinstance(py["agent_prompts"]["implementation_agent"], str)

    def test_python_agent_prompts_has_coverage_review_agent(self, py):
        assert "coverage_review_agent" in py["agent_prompts"]
        assert isinstance(py["agent_prompts"]["coverage_review_agent"], str)


# ---------------------------------------------------------------------------
# R full-language entry
# ---------------------------------------------------------------------------


class TestRRegistryEntry:
    """Tests for the 'r' entry in LANGUAGE_REGISTRY."""

    @pytest.fixture
    def r_entry(self):
        return LANGUAGE_REGISTRY["r"]

    def test_r_id(self, r_entry):
        assert r_entry["id"] == "r"

    def test_r_display_name(self, r_entry):
        assert r_entry["display_name"] == "R"

    def test_r_file_extension(self, r_entry):
        assert r_entry["file_extension"] == ".R"

    def test_r_source_dir(self, r_entry):
        assert r_entry["source_dir"] == "R"

    def test_r_test_dir(self, r_entry):
        assert r_entry["test_dir"] == "tests/testthat"

    def test_r_test_file_pattern(self, r_entry):
        assert r_entry["test_file_pattern"] == "test-*.R"

    def test_r_toolchain_file(self, r_entry):
        assert r_entry["toolchain_file"] == "r_renv_testthat.json"

    def test_r_environment_manager(self, r_entry):
        assert r_entry["environment_manager"] == "renv"

    def test_r_test_framework(self, r_entry):
        assert r_entry["test_framework"] == "testthat"

    def test_r_version_check_command(self, r_entry):
        assert r_entry["version_check_command"] == "Rscript --version"

    def test_r_stub_sentinel(self, r_entry):
        assert (
            r_entry["stub_sentinel"]
            == "# __SVP_STUB__ <- TRUE  # DO NOT DELIVER -- stub file generated by SVP"
        )

    def test_r_stub_generator_key(self, r_entry):
        assert r_entry["stub_generator_key"] == "r"

    def test_r_test_output_parser_key(self, r_entry):
        assert r_entry["test_output_parser_key"] == "r"

    def test_r_quality_runner_key(self, r_entry):
        assert r_entry["quality_runner_key"] == "r"

    def test_r_is_not_component_only(self, r_entry):
        assert r_entry["is_component_only"] is False

    def test_r_compatible_hosts_is_empty(self, r_entry):
        assert r_entry["compatible_hosts"] == []

    def test_r_bridge_libraries_has_r_python(self, r_entry):
        assert "r_python" in r_entry["bridge_libraries"]
        assert r_entry["bridge_libraries"]["r_python"]["library"] == "reticulate"
        assert (
            r_entry["bridge_libraries"]["r_python"]["conda_package"] == "r-reticulate"
        )

    def test_r_collection_error_indicators(self, r_entry):
        expected = [
            "Error in library",
            "there is no package called",
            "could not find function",
        ]
        assert r_entry["collection_error_indicators"] == expected

    def test_r_authorized_write_dirs(self, r_entry):
        assert r_entry["authorized_write_dirs"] == ["R", "tests/testthat", "."]

    def test_r_default_delivery_environment_recommendation(self, r_entry):
        assert r_entry["default_delivery"]["environment_recommendation"] == "renv"

    def test_r_default_delivery_dependency_format(self, r_entry):
        assert r_entry["default_delivery"]["dependency_format"] == "renv.lock"

    def test_r_default_delivery_source_layout(self, r_entry):
        assert r_entry["default_delivery"]["source_layout"] == "package"

    def test_r_default_delivery_entry_points(self, r_entry):
        assert r_entry["default_delivery"]["entry_points"] is False

    def test_r_default_quality_linter(self, r_entry):
        assert r_entry["default_quality"]["linter"] == "lintr"

    def test_r_default_quality_formatter(self, r_entry):
        assert r_entry["default_quality"]["formatter"] == "styler"

    def test_r_default_quality_type_checker(self, r_entry):
        assert r_entry["default_quality"]["type_checker"] == "none"

    def test_r_default_quality_line_length(self, r_entry):
        assert r_entry["default_quality"]["line_length"] == 80

    def test_r_valid_linters(self, r_entry):
        assert r_entry["valid_linters"] == {"lintr", "none"}

    def test_r_valid_formatters(self, r_entry):
        assert r_entry["valid_formatters"] == {"styler", "none"}

    def test_r_valid_type_checkers(self, r_entry):
        assert r_entry["valid_type_checkers"] == {"none"}

    def test_r_valid_source_layouts(self, r_entry):
        assert r_entry["valid_source_layouts"] == ["package", "scripts"]

    def test_r_environment_file_name(self, r_entry):
        assert r_entry["environment_file_name"] == "renv.lock"

    def test_r_project_manifest_file(self, r_entry):
        assert r_entry["project_manifest_file"] == "DESCRIPTION"

    def test_r_gitignore_patterns(self, r_entry):
        expected = [".Rhistory", ".RData", ".Rproj.user/", "inst/doc/"]
        assert r_entry["gitignore_patterns"] == expected

    def test_r_entry_point_mechanism(self, r_entry):
        assert r_entry["entry_point_mechanism"] == "namespace_exports"

    def test_r_quality_config_mapping_lintr(self, r_entry):
        assert r_entry["quality_config_mapping"]["lintr"] == ".lintr"

    def test_r_quality_config_mapping_styler(self, r_entry):
        assert r_entry["quality_config_mapping"]["styler"] == ".styler.R"

    def test_r_non_source_embedding(self, r_entry):
        assert r_entry["non_source_embedding"] == "toplevel_character"

    def test_r_agent_prompts_has_test_agent(self, r_entry):
        assert "test_agent" in r_entry["agent_prompts"]
        assert isinstance(r_entry["agent_prompts"]["test_agent"], str)

    def test_r_agent_prompts_has_implementation_agent(self, r_entry):
        assert "implementation_agent" in r_entry["agent_prompts"]
        assert isinstance(r_entry["agent_prompts"]["implementation_agent"], str)

    def test_r_agent_prompts_has_coverage_review_agent(self, r_entry):
        assert "coverage_review_agent" in r_entry["agent_prompts"]
        assert isinstance(r_entry["agent_prompts"]["coverage_review_agent"], str)


# ---------------------------------------------------------------------------
# Stan component-only entry
# ---------------------------------------------------------------------------


class TestStanRegistryEntry:
    """Tests for the 'stan' component-only entry in LANGUAGE_REGISTRY."""

    @pytest.fixture
    def stan(self):
        return LANGUAGE_REGISTRY["stan"]

    def test_stan_id(self, stan):
        assert stan["id"] == "stan"

    def test_stan_display_name(self, stan):
        assert stan["display_name"] == "Stan"

    def test_stan_file_extension(self, stan):
        assert stan["file_extension"] == ".stan"

    def test_stan_is_component_only(self, stan):
        assert stan["is_component_only"] is True

    def test_stan_compatible_hosts(self, stan):
        assert stan["compatible_hosts"] == ["r", "python"]

    def test_stan_stub_generator_key(self, stan):
        assert stan["stub_generator_key"] == "stan_template"

    def test_stan_quality_runner_key(self, stan):
        assert stan["quality_runner_key"] == "stan_syntax_check"

    def test_stan_required_dispatch_entries(self, stan):
        assert stan["required_dispatch_entries"] == [
            "stub_generator_key",
            "quality_runner_key",
        ]

    def test_stan_bridge_libraries_is_empty(self, stan):
        assert stan["bridge_libraries"] == {}


# ---------------------------------------------------------------------------
# FULL_REQUIRED_KEYS and COMPONENT_REQUIRED_KEYS
# ---------------------------------------------------------------------------


class TestRequiredKeySets:
    """Tests for FULL_REQUIRED_KEYS and COMPONENT_REQUIRED_KEYS sets."""

    def test_full_required_keys_is_a_set(self):
        assert isinstance(FULL_REQUIRED_KEYS, set)

    def test_component_required_keys_is_a_set(self):
        assert isinstance(COMPONENT_REQUIRED_KEYS, set)

    def test_full_required_keys_are_strings(self):
        for key in FULL_REQUIRED_KEYS:
            assert isinstance(key, str), f"Key '{key}' is not a string"

    def test_component_required_keys_are_strings(self):
        for key in COMPONENT_REQUIRED_KEYS:
            assert isinstance(key, str), f"Key '{key}' is not a string"

    def test_full_required_keys_covers_python_entry(self):
        """Every key listed in FULL_REQUIRED_KEYS should be present in the python entry."""
        py = LANGUAGE_REGISTRY["python"]
        for key in FULL_REQUIRED_KEYS:
            assert key in py, (
                f"FULL_REQUIRED_KEYS contains '{key}' but python entry lacks it"
            )

    def test_full_required_keys_covers_r_entry(self):
        """Every key listed in FULL_REQUIRED_KEYS should be present in the r entry."""
        r_entry = LANGUAGE_REGISTRY["r"]
        for key in FULL_REQUIRED_KEYS:
            assert key in r_entry, (
                f"FULL_REQUIRED_KEYS contains '{key}' but r entry lacks it"
            )

    def test_component_required_keys_includes_required_dispatch_entries(self):
        """COMPONENT_REQUIRED_KEYS should include 'required_dispatch_entries'."""
        assert "required_dispatch_entries" in COMPONENT_REQUIRED_KEYS

    def test_component_required_keys_covers_stan_entry(self):
        """Every key in COMPONENT_REQUIRED_KEYS should be present in the stan entry."""
        stan = LANGUAGE_REGISTRY["stan"]
        for key in COMPONENT_REQUIRED_KEYS:
            assert key in stan, (
                f"COMPONENT_REQUIRED_KEYS contains '{key}' but stan entry lacks it"
            )

    def test_component_required_keys_is_subset_relationship(self):
        """COMPONENT_REQUIRED_KEYS should not contain full-language-only keys.

        Specifically, keys that are only in FULL_REQUIRED_KEYS and not in
        COMPONENT_REQUIRED_KEYS should not appear in the component key set.
        """
        full_only = FULL_REQUIRED_KEYS - COMPONENT_REQUIRED_KEYS
        component_only = COMPONENT_REQUIRED_KEYS - FULL_REQUIRED_KEYS
        # component_only should contain 'required_dispatch_entries' at minimum
        assert "required_dispatch_entries" in component_only
        # full_only keys should not be in COMPONENT_REQUIRED_KEYS
        for key in full_only:
            assert key not in COMPONENT_REQUIRED_KEYS

    def test_full_required_keys_contains_identity_keys(self):
        for key in ["id", "display_name", "file_extension"]:
            assert key in FULL_REQUIRED_KEYS, f"Missing identity key: {key}"

    def test_full_required_keys_contains_filesystem_keys(self):
        for key in ["source_dir", "test_dir", "test_file_pattern"]:
            assert key in FULL_REQUIRED_KEYS, f"Missing filesystem key: {key}"

    def test_full_required_keys_contains_toolchain_keys(self):
        for key in ["toolchain_file", "environment_manager", "test_framework"]:
            assert key in FULL_REQUIRED_KEYS, f"Missing toolchain key: {key}"

    def test_full_required_keys_contains_code_gen_keys(self):
        for key in [
            "stub_sentinel",
            "stub_generator_key",
            "test_output_parser_key",
            "quality_runner_key",
        ]:
            assert key in FULL_REQUIRED_KEYS, f"Missing code gen key: {key}"

    def test_full_required_keys_contains_delivery_and_quality_keys(self):
        for key in [
            "default_delivery",
            "default_quality",
            "valid_linters",
            "valid_formatters",
            "valid_type_checkers",
            "valid_source_layouts",
        ]:
            assert key in FULL_REQUIRED_KEYS, f"Missing delivery/quality key: {key}"

    def test_full_required_keys_contains_component_support_keys(self):
        for key in ["is_component_only", "compatible_hosts", "bridge_libraries"]:
            assert key in FULL_REQUIRED_KEYS, f"Missing component support key: {key}"

    def test_full_required_keys_contains_agent_prompts(self):
        assert "agent_prompts" in FULL_REQUIRED_KEYS

    def test_full_required_keys_contains_error_detection_keys(self):
        assert "collection_error_indicators" in FULL_REQUIRED_KEYS

    def test_full_required_keys_contains_authorized_write_dirs(self):
        assert "authorized_write_dirs" in FULL_REQUIRED_KEYS

    def test_full_required_keys_contains_delivery_structure_keys(self):
        for key in [
            "environment_file_name",
            "project_manifest_file",
            "gitignore_patterns",
            "entry_point_mechanism",
        ]:
            assert key in FULL_REQUIRED_KEYS, f"Missing delivery structure key: {key}"

    def test_full_required_keys_contains_hook_configuration_keys(self):
        for key in ["quality_config_mapping", "non_source_embedding"]:
            assert key in FULL_REQUIRED_KEYS, f"Missing hook config key: {key}"


# ---------------------------------------------------------------------------
# get_language_config
# ---------------------------------------------------------------------------


class TestGetLanguageConfig:
    """Tests for get_language_config function."""

    def test_returns_python_config(self):
        config = get_language_config("python")
        assert config["id"] == "python"

    def test_returns_r_config(self):
        config = get_language_config("r")
        assert config["id"] == "r"

    def test_returns_stan_config(self):
        config = get_language_config("stan")
        assert config["id"] == "stan"

    def test_raises_key_error_for_unknown_language(self):
        with pytest.raises(KeyError, match="Unknown language: javascript"):
            get_language_config("javascript")

    def test_raises_key_error_for_empty_string(self):
        with pytest.raises(KeyError, match="Unknown language: "):
            get_language_config("")

    def test_returns_deep_copy_not_reference(self):
        """Returned config must be a deep copy so mutations do not affect the registry."""
        config = get_language_config("python")
        config["id"] = "MUTATED"
        original = LANGUAGE_REGISTRY["python"]
        assert original["id"] == "python", "get_language_config must return a deep copy"

    def test_deep_copy_includes_nested_dicts(self):
        """Nested dicts within the config must also be independent copies."""
        config = get_language_config("python")
        config["default_delivery"]["environment_recommendation"] = "MUTATED"
        original = LANGUAGE_REGISTRY["python"]
        assert original["default_delivery"]["environment_recommendation"] == "conda"

    def test_deep_copy_includes_nested_lists(self):
        """Nested lists within the config must also be independent copies."""
        config = get_language_config("python")
        config["collection_error_indicators"].append("MUTATED")
        original = LANGUAGE_REGISTRY["python"]
        assert "MUTATED" not in original["collection_error_indicators"]

    def test_deep_copy_includes_nested_sets(self):
        """Nested sets should be independent copies."""
        config = get_language_config("python")
        original_linters = LANGUAGE_REGISTRY["python"]["valid_linters"].copy()
        config["valid_linters"].add("MUTATED")
        assert LANGUAGE_REGISTRY["python"]["valid_linters"] == original_linters

    def test_returned_config_has_all_full_required_keys_for_python(self):
        config = get_language_config("python")
        for key in FULL_REQUIRED_KEYS:
            assert key in config, f"Returned python config missing key: {key}"

    def test_returned_config_has_all_component_required_keys_for_stan(self):
        config = get_language_config("stan")
        for key in COMPONENT_REQUIRED_KEYS:
            assert key in config, f"Returned stan config missing key: {key}"

    def test_key_error_message_format(self):
        """Error message must include the requested language name."""
        try:
            get_language_config("fortran")
            assert False, "Expected KeyError"
        except KeyError as e:
            assert "fortran" in str(e)


# ---------------------------------------------------------------------------
# validate_registry_entry
# ---------------------------------------------------------------------------


class TestValidateRegistryEntry:
    """Tests for validate_registry_entry function."""

    def test_python_entry_validates_cleanly(self):
        errors = validate_registry_entry(LANGUAGE_REGISTRY["python"])
        assert errors == [], f"Python entry should be valid but got errors: {errors}"

    def test_r_entry_validates_cleanly(self):
        errors = validate_registry_entry(LANGUAGE_REGISTRY["r"])
        assert errors == [], f"R entry should be valid but got errors: {errors}"

    def test_returns_list(self):
        errors = validate_registry_entry(LANGUAGE_REGISTRY["python"])
        assert isinstance(errors, list)

    def test_missing_single_required_key_produces_error(self):
        """Removing a required key should produce at least one error."""
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["id"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0, "Missing 'id' key should produce validation error"

    def test_missing_multiple_required_keys_produces_errors(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["id"]
        del entry["display_name"]
        del entry["file_extension"]
        errors = validate_registry_entry(entry)
        assert len(errors) >= 3, "Missing 3 keys should produce at least 3 errors"

    def test_empty_entry_produces_many_errors(self):
        errors = validate_registry_entry({})
        assert len(errors) >= len(FULL_REQUIRED_KEYS), (
            "Empty entry should produce at least one error per required key"
        )

    def test_checks_default_delivery_environment_recommendation(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_delivery"]["environment_recommendation"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0, (
            "Missing environment_recommendation in default_delivery should error"
        )

    def test_checks_default_delivery_dependency_format(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_delivery"]["dependency_format"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0, (
            "Missing dependency_format in default_delivery should error"
        )

    def test_checks_default_delivery_source_layout(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_delivery"]["source_layout"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0, "Missing source_layout in default_delivery should error"

    def test_checks_default_delivery_entry_points(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_delivery"]["entry_points"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0, "Missing entry_points in default_delivery should error"

    def test_checks_default_quality_linter(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_quality"]["linter"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0, "Missing linter in default_quality should error"

    def test_checks_default_quality_formatter(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_quality"]["formatter"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0, "Missing formatter in default_quality should error"

    def test_checks_default_quality_type_checker(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_quality"]["type_checker"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0, "Missing type_checker in default_quality should error"

    def test_checks_default_quality_line_length(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_quality"]["line_length"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0, "Missing line_length in default_quality should error"

    def test_checks_default_quality_import_sorter_for_python(self):
        """Python entry must have import_sorter in default_quality."""
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_quality"]["import_sorter"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0, "Missing import_sorter for Python should error"

    def test_r_default_quality_does_not_require_import_sorter(self):
        """R entry should validate without import_sorter in default_quality."""
        errors = validate_registry_entry(LANGUAGE_REGISTRY["r"])
        assert errors == [], "R entry should be valid without import_sorter"

    def test_error_strings_are_descriptive(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["id"]
        errors = validate_registry_entry(entry)
        assert any("id" in err for err in errors), (
            "Error messages should reference the missing key"
        )

    def test_all_full_required_keys_checked(self):
        """Removing each required key individually should produce an error."""
        for key in FULL_REQUIRED_KEYS:
            entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
            if key in entry:
                del entry[key]
                errors = validate_registry_entry(entry)
                assert len(errors) > 0, (
                    f"Removing '{key}' should produce validation error"
                )


# ---------------------------------------------------------------------------
# validate_component_entry
# ---------------------------------------------------------------------------


class TestValidateComponentEntry:
    """Tests for validate_component_entry function."""

    def test_stan_entry_validates_cleanly(self):
        errors = validate_component_entry(LANGUAGE_REGISTRY["stan"])
        assert errors == [], f"Stan entry should be valid but got errors: {errors}"

    def test_returns_list(self):
        errors = validate_component_entry(LANGUAGE_REGISTRY["stan"])
        assert isinstance(errors, list)

    def test_checks_all_component_required_keys_present(self):
        for key in COMPONENT_REQUIRED_KEYS:
            entry = copy.deepcopy(LANGUAGE_REGISTRY["stan"])
            if key in entry:
                del entry[key]
                errors = validate_component_entry(entry)
                assert len(errors) > 0, (
                    f"Removing '{key}' should produce validation error"
                )

    def test_checks_is_component_only_is_true(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["stan"])
        entry["is_component_only"] = False
        errors = validate_component_entry(entry)
        assert len(errors) > 0, (
            "is_component_only=False should produce validation error"
        )

    def test_checks_compatible_hosts_is_non_empty(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["stan"])
        entry["compatible_hosts"] = []
        errors = validate_component_entry(entry)
        assert len(errors) > 0, "Empty compatible_hosts should produce validation error"

    def test_checks_required_dispatch_entries_is_non_empty(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["stan"])
        entry["required_dispatch_entries"] = []
        errors = validate_component_entry(entry)
        assert len(errors) > 0, (
            "Empty required_dispatch_entries should produce validation error"
        )

    def test_checks_required_dispatch_entries_are_strings(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["stan"])
        entry["required_dispatch_entries"] = [123, 456]
        errors = validate_component_entry(entry)
        assert len(errors) > 0, (
            "Non-string required_dispatch_entries should produce validation error"
        )

    def test_checks_required_dispatch_entries_is_list(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["stan"])
        entry["required_dispatch_entries"] = "not_a_list"
        errors = validate_component_entry(entry)
        assert len(errors) > 0, (
            "Non-list required_dispatch_entries should produce validation error"
        )

    def test_empty_entry_produces_errors(self):
        errors = validate_component_entry({})
        assert len(errors) > 0, "Empty entry should produce validation errors"

    def test_error_strings_are_descriptive(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["stan"])
        entry["is_component_only"] = False
        errors = validate_component_entry(entry)
        assert len(errors) > 0
        # Errors should be non-empty strings
        for err in errors:
            assert isinstance(err, str)
            assert len(err) > 0

    def test_missing_is_component_only_key_produces_error(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["stan"])
        del entry["is_component_only"]
        errors = validate_component_entry(entry)
        assert len(errors) > 0

    def test_missing_compatible_hosts_key_produces_error(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["stan"])
        del entry["compatible_hosts"]
        errors = validate_component_entry(entry)
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# Import-time validation
# ---------------------------------------------------------------------------


class TestImportTimeValidation:
    """Tests that the module validates all registry entries at import time."""

    def test_all_full_language_entries_pass_validation(self):
        """Every non-component entry in LANGUAGE_REGISTRY should validate cleanly."""
        for lang, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                errors = validate_registry_entry(entry)
                assert errors == [], (
                    f"Full-language entry '{lang}' has validation errors: {errors}"
                )

    def test_all_component_entries_pass_validation(self):
        """Every component-only entry in LANGUAGE_REGISTRY should validate cleanly."""
        for lang, entry in LANGUAGE_REGISTRY.items():
            if entry.get("is_component_only", False):
                errors = validate_component_entry(entry)
                assert errors == [], (
                    f"Component entry '{lang}' has validation errors: {errors}"
                )

    def test_python_is_full_language(self):
        assert LANGUAGE_REGISTRY["python"]["is_component_only"] is False

    def test_r_is_full_language(self):
        assert LANGUAGE_REGISTRY["r"]["is_component_only"] is False

    def test_stan_is_component_only(self):
        assert LANGUAGE_REGISTRY["stan"]["is_component_only"] is True


# ---------------------------------------------------------------------------
# load_registry_extensions
# ---------------------------------------------------------------------------


class TestLoadRegistryExtensions:
    """Tests for load_registry_extensions function."""

    def test_returns_empty_dict_when_file_not_found(self, tmp_path):
        """Returns empty dict if language_registry_extensions.json does not exist."""
        result = load_registry_extensions(str(tmp_path))
        assert result == {}

    def test_returns_dict(self, tmp_path):
        result = load_registry_extensions(str(tmp_path))
        assert isinstance(result, dict)

    def test_loads_valid_extension_file(self, tmp_path):
        """Loads and returns extension entries from a valid JSON file."""
        extension_data = {
            "julia": {
                "id": "julia",
                "display_name": "Julia",
                "file_extension": ".jl",
                "is_component_only": False,
            }
        }
        ext_file = tmp_path / "language_registry_extensions.json"
        ext_file.write_text(json.dumps(extension_data))
        result = load_registry_extensions(str(tmp_path))
        assert "julia" in result
        assert result["julia"]["id"] == "julia"

    def test_returns_dict_of_extension_entries(self, tmp_path):
        extension_data = {
            "julia": {"id": "julia", "display_name": "Julia"},
            "rust": {"id": "rust", "display_name": "Rust"},
        }
        ext_file = tmp_path / "language_registry_extensions.json"
        ext_file.write_text(json.dumps(extension_data))
        result = load_registry_extensions(str(tmp_path))
        assert isinstance(result, dict)
        assert len(result) == 2
        assert "julia" in result
        assert "rust" in result

    def test_empty_extension_file_returns_empty_dict(self, tmp_path):
        """An extension file with an empty dict should return empty dict."""
        ext_file = tmp_path / "language_registry_extensions.json"
        ext_file.write_text("{}")
        result = load_registry_extensions(str(tmp_path))
        assert result == {}

    def test_extension_entries_are_dicts(self, tmp_path):
        extension_data = {
            "julia": {"id": "julia", "display_name": "Julia"},
        }
        ext_file = tmp_path / "language_registry_extensions.json"
        ext_file.write_text(json.dumps(extension_data))
        result = load_registry_extensions(str(tmp_path))
        for lang, entry in result.items():
            assert isinstance(entry, dict), f"Extension entry '{lang}' should be a dict"

    def test_nonexistent_directory_returns_empty_dict(self):
        """A path that does not exist should return empty dict (file not found)."""
        result = load_registry_extensions("/nonexistent/path/that/does/not/exist")
        assert result == {}


# ---------------------------------------------------------------------------
# Cross-entry consistency
# ---------------------------------------------------------------------------


class TestCrossEntryConsistency:
    """Tests for cross-entry consistency within LANGUAGE_REGISTRY."""

    def test_every_entry_has_id_matching_its_key(self):
        """Each registry entry's 'id' field must match its dict key."""
        for lang, entry in LANGUAGE_REGISTRY.items():
            assert entry["id"] == lang, (
                f"Entry key '{lang}' does not match id field '{entry['id']}'"
            )

    def test_full_entries_have_version_check_command(self):
        for lang, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                assert "version_check_command" in entry, (
                    f"Full entry '{lang}' missing version_check_command"
                )

    def test_component_hosts_are_valid_registry_keys(self):
        """Each compatible_host for a component should be a key in the registry."""
        for lang, entry in LANGUAGE_REGISTRY.items():
            if entry.get("is_component_only", False):
                for host in entry["compatible_hosts"]:
                    assert host in LANGUAGE_REGISTRY, (
                        f"Component '{lang}' has compatible_host '{host}' not in registry"
                    )

    def test_component_hosts_are_full_languages(self):
        """Each compatible host should be a full language, not another component."""
        for lang, entry in LANGUAGE_REGISTRY.items():
            if entry.get("is_component_only", False):
                for host in entry["compatible_hosts"]:
                    host_entry = LANGUAGE_REGISTRY[host]
                    assert not host_entry.get("is_component_only", False), (
                        f"Component '{lang}' has component-only host '{host}'"
                    )

    def test_full_entries_have_non_empty_authorized_write_dirs(self):
        for lang, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                assert len(entry["authorized_write_dirs"]) > 0, (
                    f"Full entry '{lang}' has empty authorized_write_dirs"
                )

    def test_full_entries_have_non_empty_collection_error_indicators(self):
        for lang, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                assert len(entry["collection_error_indicators"]) > 0, (
                    f"Full entry '{lang}' has empty collection_error_indicators"
                )

    def test_bridge_libraries_are_dicts(self):
        for lang, entry in LANGUAGE_REGISTRY.items():
            assert isinstance(entry.get("bridge_libraries", {}), dict), (
                f"Entry '{lang}' bridge_libraries is not a dict"
            )

    def test_python_and_r_bridge_libraries_are_reciprocal(self):
        """Python's bridge to R and R's bridge to Python should both exist."""
        py_bridges = LANGUAGE_REGISTRY["python"]["bridge_libraries"]
        r_bridges = LANGUAGE_REGISTRY["r"]["bridge_libraries"]
        assert any("r" in key for key in py_bridges), "Python should have a bridge to R"
        assert any("python" in key for key in r_bridges), (
            "R should have a bridge to Python"
        )


# ---------------------------------------------------------------------------
# Edge cases and type safety
# ---------------------------------------------------------------------------


class TestEdgeCasesAndTypeSafety:
    """Tests for edge cases and type correctness in registry entries."""

    def test_python_default_delivery_is_dict(self):
        assert isinstance(LANGUAGE_REGISTRY["python"]["default_delivery"], dict)

    def test_python_default_quality_is_dict(self):
        assert isinstance(LANGUAGE_REGISTRY["python"]["default_quality"], dict)

    def test_r_default_delivery_is_dict(self):
        assert isinstance(LANGUAGE_REGISTRY["r"]["default_delivery"], dict)

    def test_r_default_quality_is_dict(self):
        assert isinstance(LANGUAGE_REGISTRY["r"]["default_quality"], dict)

    def test_python_valid_linters_is_set(self):
        assert isinstance(LANGUAGE_REGISTRY["python"]["valid_linters"], set)

    def test_python_valid_formatters_is_set(self):
        assert isinstance(LANGUAGE_REGISTRY["python"]["valid_formatters"], set)

    def test_python_valid_type_checkers_is_set(self):
        assert isinstance(LANGUAGE_REGISTRY["python"]["valid_type_checkers"], set)

    def test_python_valid_source_layouts_is_list(self):
        assert isinstance(LANGUAGE_REGISTRY["python"]["valid_source_layouts"], list)

    def test_python_gitignore_patterns_is_list(self):
        assert isinstance(LANGUAGE_REGISTRY["python"]["gitignore_patterns"], list)

    def test_python_authorized_write_dirs_is_list(self):
        assert isinstance(LANGUAGE_REGISTRY["python"]["authorized_write_dirs"], list)

    def test_python_collection_error_indicators_is_list(self):
        assert isinstance(
            LANGUAGE_REGISTRY["python"]["collection_error_indicators"], list
        )

    def test_python_agent_prompts_is_dict(self):
        assert isinstance(LANGUAGE_REGISTRY["python"]["agent_prompts"], dict)

    def test_python_quality_config_mapping_is_dict(self):
        assert isinstance(LANGUAGE_REGISTRY["python"]["quality_config_mapping"], dict)

    def test_stan_compatible_hosts_is_list(self):
        assert isinstance(LANGUAGE_REGISTRY["stan"]["compatible_hosts"], list)

    def test_stan_required_dispatch_entries_is_list(self):
        assert isinstance(LANGUAGE_REGISTRY["stan"]["required_dispatch_entries"], list)

    def test_python_line_length_is_int(self):
        assert isinstance(
            LANGUAGE_REGISTRY["python"]["default_quality"]["line_length"], int
        )

    def test_r_line_length_is_int(self):
        assert isinstance(LANGUAGE_REGISTRY["r"]["default_quality"]["line_length"], int)

    def test_python_entry_points_is_bool(self):
        assert isinstance(
            LANGUAGE_REGISTRY["python"]["default_delivery"]["entry_points"], bool
        )

    def test_r_entry_points_is_bool(self):
        assert isinstance(
            LANGUAGE_REGISTRY["r"]["default_delivery"]["entry_points"], bool
        )

    def test_validate_registry_entry_returns_empty_list_for_valid_input(self):
        """Return type is specifically a list (not None, not tuple)."""
        result = validate_registry_entry(LANGUAGE_REGISTRY["python"])
        assert isinstance(result, list)

    def test_validate_component_entry_returns_empty_list_for_valid_input(self):
        result = validate_component_entry(LANGUAGE_REGISTRY["stan"])
        assert isinstance(result, list)

"""Tests for Unit 2: Language Registry.

Synthetic Data Assumptions:
- Python, R, and Stan are the three built-in language registry entries.
- Full-language entries (Python, R) have all keys enumerated in the Tier 3
  behavioral contracts. Component-only entries (Stan) have a subset plus
  required_dispatch_entries.
- The exact values for each registry key (display_name, file_extension,
  source_dir, etc.) are taken verbatim from the blueprint contracts.
- TestResult and QualityResult are NamedTuples with the exact fields and
  order specified in the Tier 2 signatures.
- get_language_config returns a deep copy, so mutations to the returned
  dict do not affect the registry.
- validate_registry_entry and validate_component_entry return empty lists
  for valid entries and non-empty lists of violation strings for invalid ones.
- load_registry_extensions returns empty dict when the file does not exist.
- FULL_REQUIRED_KEYS is the set of all keys present in a full-language entry.
- COMPONENT_REQUIRED_KEYS is FULL_REQUIRED_KEYS minus full-language-only keys,
  plus required_dispatch_entries.
"""

import copy
import json
import os
import tempfile
from typing import Any, Dict

import pytest

from language_registry import (
    COMPONENT_REQUIRED_KEYS,
    FULL_REQUIRED_KEYS,
    LANGUAGE_REGISTRY,
    QualityResult,
    TestResult,
    get_language_config,
    load_registry_extensions,
    validate_component_entry,
    validate_registry_entry,
)

# ---------------------------------------------------------------------------
# Expected key sets derived from the blueprint contracts
# ---------------------------------------------------------------------------

# All keys explicitly listed for a full-language entry (Python)
EXPECTED_FULL_KEYS = {
    "id",
    "display_name",
    "file_extension",
    "source_dir",
    "test_dir",
    "test_file_pattern",
    "toolchain_file",
    "environment_manager",
    "test_framework",
    "version_check_command",
    "stub_sentinel",
    "stub_generator_key",
    "test_output_parser_key",
    "quality_runner_key",
    "is_component_only",
    "compatible_hosts",
    "bridge_libraries",
    "collection_error_indicators",
    "authorized_write_dirs",
    "default_delivery",
    "default_quality",
    "valid_linters",
    "valid_formatters",
    "valid_type_checkers",
    "valid_source_layouts",
    "environment_file_name",
    "project_manifest_file",
    "gitignore_patterns",
    "entry_point_mechanism",
    "quality_config_mapping",
    "non_source_embedding",
    "agent_prompts",
}


# ============================================================================
# TestResult NamedTuple
# ============================================================================


class TestTestResult:
    """Tests for the TestResult named tuple."""

    def test_test_result_is_a_named_tuple(self):
        result = TestResult(
            status="TESTS_PASSED",
            passed=5,
            failed=0,
            errors=0,
            output="All passed",
            collection_error=False,
        )
        assert isinstance(result, tuple)

    def test_test_result_has_status_field(self):
        result = TestResult(
            status="TESTS_PASSED",
            passed=5,
            failed=0,
            errors=0,
            output="ok",
            collection_error=False,
        )
        assert result.status == "TESTS_PASSED"

    def test_test_result_has_passed_field(self):
        result = TestResult(
            status="TESTS_PASSED",
            passed=10,
            failed=0,
            errors=0,
            output="ok",
            collection_error=False,
        )
        assert result.passed == 10

    def test_test_result_has_failed_field(self):
        result = TestResult(
            status="TESTS_FAILED",
            passed=3,
            failed=2,
            errors=0,
            output="failures",
            collection_error=False,
        )
        assert result.failed == 2

    def test_test_result_has_errors_field(self):
        result = TestResult(
            status="TESTS_ERROR",
            passed=0,
            failed=0,
            errors=1,
            output="error",
            collection_error=False,
        )
        assert result.errors == 1

    def test_test_result_has_output_field(self):
        result = TestResult(
            status="TESTS_PASSED",
            passed=1,
            failed=0,
            errors=0,
            output="detailed output here",
            collection_error=False,
        )
        assert result.output == "detailed output here"

    def test_test_result_has_collection_error_field(self):
        result = TestResult(
            status="COLLECTION_ERROR",
            passed=0,
            failed=0,
            errors=0,
            output="import error",
            collection_error=True,
        )
        assert result.collection_error is True

    def test_test_result_field_order_matches_positional_access(self):
        result = TestResult("TESTS_PASSED", 5, 2, 1, "output", False)
        assert result[0] == "TESTS_PASSED"
        assert result[1] == 5
        assert result[2] == 2
        assert result[3] == 1
        assert result[4] == "output"
        assert result[5] is False

    def test_test_result_valid_status_values_are_accepted(self):
        for status in [
            "TESTS_PASSED",
            "TESTS_FAILED",
            "TESTS_ERROR",
            "COLLECTION_ERROR",
        ]:
            result = TestResult(
                status=status,
                passed=0,
                failed=0,
                errors=0,
                output="",
                collection_error=False,
            )
            assert result.status == status


# ============================================================================
# QualityResult NamedTuple
# ============================================================================


class TestQualityResult:
    """Tests for the QualityResult named tuple."""

    def test_quality_result_is_a_named_tuple(self):
        result = QualityResult(
            status="QUALITY_CLEAN",
            auto_fixed=False,
            residuals=[],
            report="clean",
        )
        assert isinstance(result, tuple)

    def test_quality_result_has_status_field(self):
        result = QualityResult(
            status="QUALITY_CLEAN",
            auto_fixed=False,
            residuals=[],
            report="ok",
        )
        assert result.status == "QUALITY_CLEAN"

    def test_quality_result_has_auto_fixed_field(self):
        result = QualityResult(
            status="QUALITY_AUTO_FIXED",
            auto_fixed=True,
            residuals=[],
            report="fixed",
        )
        assert result.auto_fixed is True

    def test_quality_result_has_residuals_field(self):
        result = QualityResult(
            status="QUALITY_RESIDUAL",
            auto_fixed=False,
            residuals=["line 10: unused import"],
            report="issues",
        )
        assert result.residuals == ["line 10: unused import"]

    def test_quality_result_has_report_field(self):
        result = QualityResult(
            status="QUALITY_CLEAN",
            auto_fixed=False,
            residuals=[],
            report="detailed report",
        )
        assert result.report == "detailed report"

    def test_quality_result_field_order_matches_positional_access(self):
        result = QualityResult("QUALITY_ERROR", True, ["err1"], "report text")
        assert result[0] == "QUALITY_ERROR"
        assert result[1] is True
        assert result[2] == ["err1"]
        assert result[3] == "report text"

    def test_quality_result_valid_status_values_are_accepted(self):
        for status in [
            "QUALITY_CLEAN",
            "QUALITY_AUTO_FIXED",
            "QUALITY_RESIDUAL",
            "QUALITY_ERROR",
        ]:
            result = QualityResult(
                status=status,
                auto_fixed=False,
                residuals=[],
                report="",
            )
            assert result.status == status


# ============================================================================
# LANGUAGE_REGISTRY structure
# ============================================================================


class TestLanguageRegistryStructure:
    """Tests that LANGUAGE_REGISTRY has the correct entries."""

    def test_registry_is_a_dict(self):
        assert isinstance(LANGUAGE_REGISTRY, dict)

    def test_registry_contains_python_entry(self):
        assert "python" in LANGUAGE_REGISTRY

    def test_registry_contains_r_entry(self):
        assert "r" in LANGUAGE_REGISTRY

    def test_registry_contains_stan_entry(self):
        assert "stan" in LANGUAGE_REGISTRY

    def test_registry_has_at_least_three_entries(self):
        assert len(LANGUAGE_REGISTRY) >= 3


# ============================================================================
# Python registry entry
# ============================================================================


class TestPythonRegistryEntry:
    """Tests for the Python full-language registry entry."""

    @pytest.fixture
    def python_entry(self) -> Dict[str, Any]:
        return LANGUAGE_REGISTRY["python"]

    def test_python_id(self, python_entry):
        assert python_entry["id"] == "python"

    def test_python_display_name(self, python_entry):
        assert python_entry["display_name"] == "Python"

    def test_python_file_extension(self, python_entry):
        assert python_entry["file_extension"] == ".py"

    def test_python_source_dir(self, python_entry):
        assert python_entry["source_dir"] == "src"

    def test_python_test_dir(self, python_entry):
        assert python_entry["test_dir"] == "tests"

    def test_python_test_file_pattern(self, python_entry):
        assert python_entry["test_file_pattern"] == "test_*.py"

    def test_python_toolchain_file(self, python_entry):
        assert python_entry["toolchain_file"] == "python_conda_pytest.json"

    def test_python_environment_manager(self, python_entry):
        assert python_entry["environment_manager"] == "conda"

    def test_python_test_framework(self, python_entry):
        assert python_entry["test_framework"] == "pytest"

    def test_python_version_check_command(self, python_entry):
        assert python_entry["version_check_command"] == "python --version"

    def test_python_stub_sentinel(self, python_entry):
        expected = "__SVP_STUB__ = True  # DO NOT DELIVER -- stub file generated by SVP"
        assert python_entry["stub_sentinel"] == expected

    def test_python_stub_generator_key(self, python_entry):
        assert python_entry["stub_generator_key"] == "python"

    def test_python_test_output_parser_key(self, python_entry):
        assert python_entry["test_output_parser_key"] == "python"

    def test_python_quality_runner_key(self, python_entry):
        assert python_entry["quality_runner_key"] == "python"

    def test_python_is_not_component_only(self, python_entry):
        assert python_entry["is_component_only"] is False

    def test_python_compatible_hosts_is_empty(self, python_entry):
        assert python_entry["compatible_hosts"] == []

    def test_python_bridge_libraries(self, python_entry):
        expected = {"python_r": {"library": "rpy2", "conda_package": "rpy2"}}
        assert python_entry["bridge_libraries"] == expected

    def test_python_collection_error_indicators(self, python_entry):
        expected = [
            "ERROR collecting",
            "ImportError",
            "ModuleNotFoundError",
            "SyntaxError",
            "no tests ran",
        ]
        assert python_entry["collection_error_indicators"] == expected

    def test_python_authorized_write_dirs(self, python_entry):
        assert python_entry["authorized_write_dirs"] == ["src", "tests", "."]

    def test_python_default_delivery(self, python_entry):
        dd = python_entry["default_delivery"]
        assert dd["environment_recommendation"] == "conda"
        assert dd["dependency_format"] == "environment.yml"
        assert dd["source_layout"] == "conventional"
        assert dd["entry_points"] is False

    def test_python_default_quality(self, python_entry):
        dq = python_entry["default_quality"]
        assert dq["linter"] == "ruff"
        assert dq["formatter"] == "ruff"
        assert dq["type_checker"] == "mypy"
        assert dq["import_sorter"] == "ruff"
        assert dq["line_length"] == 88

    def test_python_valid_linters(self, python_entry):
        assert python_entry["valid_linters"] == {"ruff", "flake8", "pylint", "none"}

    def test_python_valid_formatters(self, python_entry):
        assert python_entry["valid_formatters"] == {"ruff", "black", "autopep8", "none"}

    def test_python_valid_type_checkers(self, python_entry):
        assert python_entry["valid_type_checkers"] == {"mypy", "pyright", "none"}

    def test_python_valid_source_layouts(self, python_entry):
        assert python_entry["valid_source_layouts"] == [
            "conventional",
            "flat",
            "svp_native",
        ]

    def test_python_environment_file_name(self, python_entry):
        assert python_entry["environment_file_name"] == "environment.yml"

    def test_python_project_manifest_file(self, python_entry):
        assert python_entry["project_manifest_file"] == "pyproject.toml"

    def test_python_gitignore_patterns(self, python_entry):
        expected = [
            "__pycache__/",
            "*.pyc",
            ".mypy_cache/",
            "dist/",
            "*.egg-info/",
        ]
        assert python_entry["gitignore_patterns"] == expected

    def test_python_entry_point_mechanism(self, python_entry):
        assert python_entry["entry_point_mechanism"] == "pyproject_scripts"

    def test_python_quality_config_mapping(self, python_entry):
        expected = {
            "ruff": "ruff.toml",
            "black": "pyproject.toml [tool.black]",
            "flake8": ".flake8",
            "mypy": "pyproject.toml [tool.mypy]",
            "pyright": "pyproject.toml [tool.pyright]",
        }
        assert python_entry["quality_config_mapping"] == expected

    def test_python_non_source_embedding(self, python_entry):
        assert python_entry["non_source_embedding"] == "module_level_string"

    def test_python_agent_prompts_has_required_keys(self, python_entry):
        prompts = python_entry["agent_prompts"]
        assert "test_agent" in prompts
        assert "implementation_agent" in prompts
        assert "coverage_review_agent" in prompts

    def test_python_agent_prompts_values_are_strings(self, python_entry):
        prompts = python_entry["agent_prompts"]
        for key in ["test_agent", "implementation_agent", "coverage_review_agent"]:
            assert isinstance(prompts[key], str)

    def test_python_entry_has_all_full_required_keys(self, python_entry):
        missing = FULL_REQUIRED_KEYS - set(python_entry.keys())
        assert missing == set(), f"Python entry missing keys: {missing}"


# ============================================================================
# R registry entry
# ============================================================================


class TestRRegistryEntry:
    """Tests for the R full-language registry entry."""

    @pytest.fixture
    def r_entry(self) -> Dict[str, Any]:
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
        expected = (
            "# __SVP_STUB__ <- TRUE  # DO NOT DELIVER -- stub file generated by SVP"
        )
        assert r_entry["stub_sentinel"] == expected

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

    def test_r_bridge_libraries(self, r_entry):
        expected = {
            "r_python": {"library": "reticulate", "conda_package": "r-reticulate"}
        }
        assert r_entry["bridge_libraries"] == expected

    def test_r_collection_error_indicators(self, r_entry):
        expected = [
            "Error in library",
            "there is no package called",
            "could not find function",
        ]
        assert r_entry["collection_error_indicators"] == expected

    def test_r_authorized_write_dirs(self, r_entry):
        assert r_entry["authorized_write_dirs"] == ["R", "tests/testthat", "."]

    def test_r_default_delivery(self, r_entry):
        dd = r_entry["default_delivery"]
        assert dd["environment_recommendation"] == "renv"
        assert dd["dependency_format"] == "renv.lock"
        assert dd["source_layout"] == "package"
        assert dd["entry_points"] is False

    def test_r_default_quality(self, r_entry):
        dq = r_entry["default_quality"]
        assert dq["linter"] == "lintr"
        assert dq["formatter"] == "styler"
        assert dq["type_checker"] == "none"
        assert dq["line_length"] == 80

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

    def test_r_quality_config_mapping(self, r_entry):
        expected = {"lintr": ".lintr", "styler": ".styler.R"}
        assert r_entry["quality_config_mapping"] == expected

    def test_r_non_source_embedding(self, r_entry):
        assert r_entry["non_source_embedding"] == "toplevel_character"

    def test_r_agent_prompts_has_required_keys(self, r_entry):
        prompts = r_entry["agent_prompts"]
        assert "test_agent" in prompts
        assert "implementation_agent" in prompts
        assert "coverage_review_agent" in prompts

    def test_r_entry_has_all_full_required_keys(self, r_entry):
        missing = FULL_REQUIRED_KEYS - set(r_entry.keys())
        assert missing == set(), f"R entry missing keys: {missing}"


# ============================================================================
# Stan registry entry (component-only)
# ============================================================================


class TestStanRegistryEntry:
    """Tests for the Stan component-only registry entry."""

    @pytest.fixture
    def stan_entry(self) -> Dict[str, Any]:
        return LANGUAGE_REGISTRY["stan"]

    def test_stan_id(self, stan_entry):
        assert stan_entry["id"] == "stan"

    def test_stan_display_name(self, stan_entry):
        assert stan_entry["display_name"] == "Stan"

    def test_stan_file_extension(self, stan_entry):
        assert stan_entry["file_extension"] == ".stan"

    def test_stan_is_component_only(self, stan_entry):
        assert stan_entry["is_component_only"] is True

    def test_stan_compatible_hosts_contains_r_and_python(self, stan_entry):
        assert "r" in stan_entry["compatible_hosts"]
        assert "python" in stan_entry["compatible_hosts"]

    def test_stan_compatible_hosts_is_non_empty(self, stan_entry):
        assert len(stan_entry["compatible_hosts"]) > 0

    def test_stan_stub_generator_key(self, stan_entry):
        assert stan_entry["stub_generator_key"] == "stan_template"

    def test_stan_quality_runner_key(self, stan_entry):
        assert stan_entry["quality_runner_key"] == "stan_syntax_check"

    def test_stan_required_dispatch_entries(self, stan_entry):
        expected = ["stub_generator_key", "quality_runner_key"]
        assert stan_entry["required_dispatch_entries"] == expected

    def test_stan_bridge_libraries_is_empty(self, stan_entry):
        assert stan_entry["bridge_libraries"] == {}

    def test_stan_entry_has_all_component_required_keys(self, stan_entry):
        missing = COMPONENT_REQUIRED_KEYS - set(stan_entry.keys())
        assert missing == set(), f"Stan entry missing keys: {missing}"


# ============================================================================
# FULL_REQUIRED_KEYS constant
# ============================================================================


class TestFullRequiredKeys:
    """Tests for the FULL_REQUIRED_KEYS constant."""

    def test_full_required_keys_is_a_set(self):
        assert isinstance(FULL_REQUIRED_KEYS, set)

    def test_full_required_keys_is_not_empty(self):
        assert len(FULL_REQUIRED_KEYS) > 0

    def test_full_required_keys_contains_identity_fields(self):
        assert "id" in FULL_REQUIRED_KEYS
        assert "display_name" in FULL_REQUIRED_KEYS

    def test_full_required_keys_contains_filesystem_fields(self):
        assert "file_extension" in FULL_REQUIRED_KEYS
        assert "source_dir" in FULL_REQUIRED_KEYS
        assert "test_dir" in FULL_REQUIRED_KEYS
        assert "test_file_pattern" in FULL_REQUIRED_KEYS

    def test_full_required_keys_contains_toolchain_fields(self):
        assert "toolchain_file" in FULL_REQUIRED_KEYS
        assert "environment_manager" in FULL_REQUIRED_KEYS
        assert "test_framework" in FULL_REQUIRED_KEYS
        assert "version_check_command" in FULL_REQUIRED_KEYS

    def test_full_required_keys_contains_code_generation_fields(self):
        assert "stub_sentinel" in FULL_REQUIRED_KEYS
        assert "stub_generator_key" in FULL_REQUIRED_KEYS
        assert "test_output_parser_key" in FULL_REQUIRED_KEYS
        assert "quality_runner_key" in FULL_REQUIRED_KEYS

    def test_full_required_keys_contains_component_support_fields(self):
        assert "is_component_only" in FULL_REQUIRED_KEYS
        assert "compatible_hosts" in FULL_REQUIRED_KEYS

    def test_full_required_keys_contains_delivery_defaults(self):
        assert "default_delivery" in FULL_REQUIRED_KEYS
        assert "default_quality" in FULL_REQUIRED_KEYS

    def test_full_required_keys_contains_validation_sets(self):
        assert "valid_linters" in FULL_REQUIRED_KEYS
        assert "valid_formatters" in FULL_REQUIRED_KEYS
        assert "valid_type_checkers" in FULL_REQUIRED_KEYS
        assert "valid_source_layouts" in FULL_REQUIRED_KEYS

    def test_full_required_keys_contains_cross_language_support(self):
        assert "bridge_libraries" in FULL_REQUIRED_KEYS

    def test_full_required_keys_contains_error_detection(self):
        assert "collection_error_indicators" in FULL_REQUIRED_KEYS

    def test_full_required_keys_contains_delivery_structure(self):
        assert "environment_file_name" in FULL_REQUIRED_KEYS
        assert "project_manifest_file" in FULL_REQUIRED_KEYS
        assert "gitignore_patterns" in FULL_REQUIRED_KEYS
        assert "entry_point_mechanism" in FULL_REQUIRED_KEYS
        assert "quality_config_mapping" in FULL_REQUIRED_KEYS
        assert "non_source_embedding" in FULL_REQUIRED_KEYS

    def test_full_required_keys_contains_agent_prompts(self):
        assert "agent_prompts" in FULL_REQUIRED_KEYS

    def test_full_required_keys_contains_hook_configuration(self):
        assert "authorized_write_dirs" in FULL_REQUIRED_KEYS

    def test_full_required_keys_matches_expected_set(self):
        assert FULL_REQUIRED_KEYS == EXPECTED_FULL_KEYS


# ============================================================================
# COMPONENT_REQUIRED_KEYS constant
# ============================================================================


class TestComponentRequiredKeys:
    """Tests for the COMPONENT_REQUIRED_KEYS constant."""

    def test_component_required_keys_is_a_set(self):
        assert isinstance(COMPONENT_REQUIRED_KEYS, set)

    def test_component_required_keys_is_not_empty(self):
        assert len(COMPONENT_REQUIRED_KEYS) > 0

    def test_component_required_keys_includes_required_dispatch_entries(self):
        assert "required_dispatch_entries" in COMPONENT_REQUIRED_KEYS

    def test_component_required_keys_is_subset_of_full_plus_dispatch(self):
        # COMPONENT_REQUIRED_KEYS should be a subset of FULL_REQUIRED_KEYS
        # union {required_dispatch_entries}
        superset = FULL_REQUIRED_KEYS | {"required_dispatch_entries"}
        assert COMPONENT_REQUIRED_KEYS <= superset

    def test_component_required_keys_contains_identity_fields(self):
        assert "id" in COMPONENT_REQUIRED_KEYS
        assert "display_name" in COMPONENT_REQUIRED_KEYS
        assert "file_extension" in COMPONENT_REQUIRED_KEYS

    def test_component_required_keys_contains_component_fields(self):
        assert "is_component_only" in COMPONENT_REQUIRED_KEYS
        assert "compatible_hosts" in COMPONENT_REQUIRED_KEYS

    def test_component_required_keys_is_smaller_than_full(self):
        # Component keys should be fewer since they exclude full-language-only keys
        assert len(COMPONENT_REQUIRED_KEYS) < len(FULL_REQUIRED_KEYS)


# ============================================================================
# get_language_config
# ============================================================================


class TestGetLanguageConfig:
    """Tests for the get_language_config function."""

    def test_returns_config_for_python(self):
        config = get_language_config("python")
        assert config["id"] == "python"

    def test_returns_config_for_r(self):
        config = get_language_config("r")
        assert config["id"] == "r"

    def test_returns_config_for_stan(self):
        config = get_language_config("stan")
        assert config["id"] == "stan"

    def test_raises_key_error_for_unknown_language(self):
        with pytest.raises(KeyError, match="Unknown language: javascript"):
            get_language_config("javascript")

    def test_raises_key_error_for_empty_string(self):
        with pytest.raises(KeyError):
            get_language_config("")

    def test_returns_deep_copy_not_reference(self):
        config1 = get_language_config("python")
        config2 = get_language_config("python")
        assert config1 is not config2

    def test_mutation_of_returned_config_does_not_affect_registry(self):
        config = get_language_config("python")
        config["id"] = "MUTATED"
        original = get_language_config("python")
        assert original["id"] == "python"

    def test_mutation_of_nested_dict_does_not_affect_registry(self):
        config = get_language_config("python")
        config["default_delivery"]["source_layout"] = "MUTATED"
        original = get_language_config("python")
        assert original["default_delivery"]["source_layout"] == "conventional"

    def test_mutation_of_nested_list_does_not_affect_registry(self):
        config = get_language_config("python")
        config["collection_error_indicators"].append("MUTATED")
        original = get_language_config("python")
        assert "MUTATED" not in original["collection_error_indicators"]

    def test_returned_config_has_correct_type(self):
        config = get_language_config("python")
        assert isinstance(config, dict)

    def test_key_error_message_contains_language_name(self):
        with pytest.raises(KeyError) as exc_info:
            get_language_config("fortran")
        assert "fortran" in str(exc_info.value)


# ============================================================================
# validate_registry_entry
# ============================================================================


class TestValidateRegistryEntry:
    """Tests for the validate_registry_entry function."""

    def test_returns_empty_list_for_valid_python_entry(self):
        errors = validate_registry_entry(LANGUAGE_REGISTRY["python"])
        assert errors == []

    def test_returns_empty_list_for_valid_r_entry(self):
        errors = validate_registry_entry(LANGUAGE_REGISTRY["r"])
        assert errors == []

    def test_returns_list_type(self):
        errors = validate_registry_entry(LANGUAGE_REGISTRY["python"])
        assert isinstance(errors, list)

    def test_detects_missing_required_key(self):
        entry = dict(LANGUAGE_REGISTRY["python"])
        del entry["id"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0

    def test_detects_multiple_missing_required_keys(self):
        entry = dict(LANGUAGE_REGISTRY["python"])
        del entry["id"]
        del entry["display_name"]
        del entry["file_extension"]
        errors = validate_registry_entry(entry)
        assert len(errors) >= 1  # At least one error for missing keys

    def test_detects_missing_default_delivery_field(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_delivery"]["environment_recommendation"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0

    def test_detects_missing_default_delivery_dependency_format(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_delivery"]["dependency_format"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0

    def test_detects_missing_default_delivery_source_layout(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_delivery"]["source_layout"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0

    def test_detects_missing_default_delivery_entry_points(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_delivery"]["entry_points"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0

    def test_detects_missing_default_quality_linter(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_quality"]["linter"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0

    def test_detects_missing_default_quality_formatter(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_quality"]["formatter"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0

    def test_detects_missing_default_quality_type_checker(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_quality"]["type_checker"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0

    def test_detects_missing_default_quality_line_length(self):
        entry = copy.deepcopy(LANGUAGE_REGISTRY["python"])
        del entry["default_quality"]["line_length"]
        errors = validate_registry_entry(entry)
        assert len(errors) > 0

    def test_error_strings_are_descriptive(self):
        entry = dict(LANGUAGE_REGISTRY["python"])
        del entry["id"]
        errors = validate_registry_entry(entry)
        assert all(isinstance(e, str) for e in errors)
        assert all(len(e) > 0 for e in errors)

    def test_empty_entry_produces_errors(self):
        errors = validate_registry_entry({})
        assert len(errors) > 0


# ============================================================================
# validate_component_entry
# ============================================================================


class TestValidateComponentEntry:
    """Tests for the validate_component_entry function."""

    def test_returns_empty_list_for_valid_stan_entry(self):
        errors = validate_component_entry(LANGUAGE_REGISTRY["stan"])
        assert errors == []

    def test_returns_list_type(self):
        errors = validate_component_entry(LANGUAGE_REGISTRY["stan"])
        assert isinstance(errors, list)

    def test_detects_is_component_only_false(self):
        entry = dict(LANGUAGE_REGISTRY["stan"])
        entry["is_component_only"] = False
        errors = validate_component_entry(entry)
        assert len(errors) > 0

    def test_detects_empty_compatible_hosts(self):
        entry = dict(LANGUAGE_REGISTRY["stan"])
        entry["compatible_hosts"] = []
        errors = validate_component_entry(entry)
        assert len(errors) > 0

    def test_detects_missing_required_dispatch_entries(self):
        entry = dict(LANGUAGE_REGISTRY["stan"])
        del entry["required_dispatch_entries"]
        errors = validate_component_entry(entry)
        assert len(errors) > 0

    def test_detects_empty_required_dispatch_entries(self):
        entry = dict(LANGUAGE_REGISTRY["stan"])
        entry["required_dispatch_entries"] = []
        errors = validate_component_entry(entry)
        assert len(errors) > 0

    def test_detects_non_string_required_dispatch_entries(self):
        entry = dict(LANGUAGE_REGISTRY["stan"])
        entry["required_dispatch_entries"] = [123, 456]
        errors = validate_component_entry(entry)
        assert len(errors) > 0

    def test_detects_missing_component_required_key(self):
        entry = dict(LANGUAGE_REGISTRY["stan"])
        del entry["id"]
        errors = validate_component_entry(entry)
        assert len(errors) > 0

    def test_error_strings_are_descriptive(self):
        entry = dict(LANGUAGE_REGISTRY["stan"])
        entry["compatible_hosts"] = []
        errors = validate_component_entry(entry)
        assert all(isinstance(e, str) for e in errors)
        assert all(len(e) > 0 for e in errors)

    def test_empty_entry_produces_errors(self):
        errors = validate_component_entry({})
        assert len(errors) > 0


# ============================================================================
# load_registry_extensions
# ============================================================================


class TestLoadRegistryExtensions:
    """Tests for the load_registry_extensions function."""

    def test_returns_empty_dict_when_file_not_found(self):
        result = load_registry_extensions("/nonexistent/path/that/does/not/exist")
        assert result == {}

    def test_returns_dict_type(self):
        result = load_registry_extensions("/nonexistent/path")
        assert isinstance(result, dict)

    def test_loads_extensions_from_valid_json_file(self):
        extension_data = {
            "julia": {
                "id": "julia",
                "display_name": "Julia",
                "file_extension": ".jl",
                "is_component_only": True,
                "compatible_hosts": ["python"],
                "stub_generator_key": "julia_template",
                "quality_runner_key": "julia_check",
                "required_dispatch_entries": [
                    "stub_generator_key",
                    "quality_runner_key",
                ],
                "bridge_libraries": {},
            }
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            ext_path = os.path.join(tmpdir, "language_registry_extensions.json")
            with open(ext_path, "w") as f:
                json.dump(extension_data, f)
            result = load_registry_extensions(tmpdir)
            assert isinstance(result, dict)
            assert "julia" in result

    def test_returns_empty_dict_for_directory_without_extensions_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = load_registry_extensions(tmpdir)
            assert result == {}


# ============================================================================
# Import-time validation invariant
# ============================================================================


class TestImportTimeValidation:
    """Tests verifying that the module's import-time validation is sound.

    Since we successfully imported the module, all built-in entries must
    pass validation. These tests verify that the registry entries are
    consistent with their validators.
    """

    def test_all_full_language_entries_pass_validation(self):
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                errors = validate_registry_entry(entry)
                assert errors == [], (
                    f"Full-language entry '{lang_key}' has validation errors: {errors}"
                )

    def test_all_component_entries_pass_validation(self):
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if entry.get("is_component_only", False):
                errors = validate_component_entry(entry)
                assert errors == [], (
                    f"Component entry '{lang_key}' has validation errors: {errors}"
                )

    def test_python_and_r_are_full_languages(self):
        assert LANGUAGE_REGISTRY["python"]["is_component_only"] is False
        assert LANGUAGE_REGISTRY["r"]["is_component_only"] is False

    def test_stan_is_component_only(self):
        assert LANGUAGE_REGISTRY["stan"]["is_component_only"] is True


# ============================================================================
# Cross-cutting structural invariants
# ============================================================================


class TestRegistryStructuralInvariants:
    """Cross-cutting structural invariants for the language registry."""

    def test_every_entry_has_id_matching_its_key(self):
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            assert entry["id"] == lang_key, (
                f"Entry key '{lang_key}' does not match entry id '{entry.get('id')}'"
            )

    def test_every_full_language_entry_has_all_required_keys(self):
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                missing = FULL_REQUIRED_KEYS - set(entry.keys())
                assert missing == set(), (
                    f"Full-language '{lang_key}' missing keys: {missing}"
                )

    def test_every_component_entry_has_all_component_keys(self):
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if entry.get("is_component_only", False):
                missing = COMPONENT_REQUIRED_KEYS - set(entry.keys())
                assert missing == set(), (
                    f"Component '{lang_key}' missing keys: {missing}"
                )

    def test_component_hosts_reference_existing_full_languages(self):
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if entry.get("is_component_only", False):
                for host in entry["compatible_hosts"]:
                    assert host in LANGUAGE_REGISTRY, (
                        f"Component '{lang_key}' references unknown host '{host}'"
                    )
                    assert not LANGUAGE_REGISTRY[host].get(
                        "is_component_only", False
                    ), f"Component '{lang_key}' host '{host}' is not a full language"

    def test_full_language_entries_have_compatible_hosts_empty(self):
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                assert entry["compatible_hosts"] == [], (
                    f"Full-language '{lang_key}' should have empty compatible_hosts"
                )

    def test_default_delivery_has_all_required_subfields(self):
        required_subfields = {
            "environment_recommendation",
            "dependency_format",
            "source_layout",
            "entry_points",
        }
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                dd = entry["default_delivery"]
                missing = required_subfields - set(dd.keys())
                assert missing == set(), (
                    f"'{lang_key}' default_delivery missing: {missing}"
                )

    def test_default_quality_has_all_required_subfields(self):
        required_subfields = {"linter", "formatter", "type_checker", "line_length"}
        for lang_key, entry in LANGUAGE_REGISTRY.items():
            if not entry.get("is_component_only", False):
                dq = entry["default_quality"]
                missing = required_subfields - set(dq.keys())
                assert missing == set(), (
                    f"'{lang_key}' default_quality missing: {missing}"
                )

    def test_python_default_quality_has_import_sorter(self):
        # Python specifically requires import_sorter in default_quality
        dq = LANGUAGE_REGISTRY["python"]["default_quality"]
        assert "import_sorter" in dq

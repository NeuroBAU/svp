"""
Coverage gap tests for Unit 1: SVP Configuration.

These tests cover blueprint contracts (Tier 2 invariants and Tier 3 behavioral
contracts) that were not addressed by the original test_svp_configuration.py.

Identified gaps:
- discover_blueprint_files: no tests existed
- load_blueprint_content: no tests existed
- get_quality_gate_operations with unknown gate: ValueError not tested
- validate_config specific invariant checks (iteration_limit >= 1, etc.)
- detect_profile_contradictions with actual contradictory data
- load_profile deep merge at nested levels
- resolve_command with non-existent operation path
- DEFAULT_PROFILE key path regression test (spec Section 30)
- Config no-caching behavior (changes on disk take effect on next load)
- get_quality_gate_operations aliased name
- write_default_config idempotency
- get_effective_context_budget computation details
"""

import copy
import json

import pytest


# ---------------------------------------------------------------------------
# Section 0: discover_blueprint_files and load_blueprint_content
# ---------------------------------------------------------------------------


class TestDiscoverBlueprintFiles:
    def test_raises_file_not_found_when_directory_missing(self, tmp_path):
        from svp_config import discover_blueprint_files

        with pytest.raises(FileNotFoundError, match="not found"):
            discover_blueprint_files(tmp_path)

    def test_raises_file_not_found_when_no_md_files(self, tmp_path):
        from svp_config import discover_blueprint_files

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        # Put a non-md file in the directory
        (blueprint_dir / "notes.txt").write_text("not a markdown file")

        with pytest.raises(FileNotFoundError, match="No .md files"):
            discover_blueprint_files(tmp_path)

    def test_returns_sorted_list_of_paths(self, tmp_path):
        from svp_config import discover_blueprint_files

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "c_file.md").write_text("third")
        (blueprint_dir / "a_file.md").write_text("first")
        (blueprint_dir / "b_file.md").write_text("second")

        result = discover_blueprint_files(tmp_path)

        assert len(result) == 3
        names = [p.name for p in result]
        assert names == ["a_file.md", "b_file.md", "c_file.md"]

    def test_returns_path_objects(self, tmp_path):
        from pathlib import Path

        from svp_config import discover_blueprint_files

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint.md").write_text("content")

        result = discover_blueprint_files(tmp_path)

        assert all(isinstance(p, Path) for p in result)

    def test_handles_single_file(self, tmp_path):
        from svp_config import discover_blueprint_files

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint.md").write_text("single file content")

        result = discover_blueprint_files(tmp_path)

        assert len(result) == 1
        assert result[0].name == "blueprint.md"

    def test_handles_multiple_files(self, tmp_path):
        from svp_config import discover_blueprint_files

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text("prose")
        (blueprint_dir / "blueprint_contracts.md").write_text("contracts")

        result = discover_blueprint_files(tmp_path)

        assert len(result) == 2

    def test_ignores_non_md_files(self, tmp_path):
        from svp_config import discover_blueprint_files

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint.md").write_text("markdown")
        (blueprint_dir / "notes.txt").write_text("text file")
        (blueprint_dir / "data.json").write_text("{}")

        result = discover_blueprint_files(tmp_path)

        assert len(result) == 1
        assert result[0].name == "blueprint.md"


class TestLoadBlueprintContent:
    def test_loads_single_file_content(self, tmp_path):
        from svp_config import load_blueprint_content

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint.md").write_text("# Blueprint\n\nContent here.")

        result = load_blueprint_content(tmp_path)

        assert "# Blueprint" in result
        assert "Content here." in result

    def test_concatenates_multiple_files_with_separator(self, tmp_path):
        from svp_config import load_blueprint_content

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "a_first.md").write_text("First file content")
        (blueprint_dir / "b_second.md").write_text("Second file content")

        result = load_blueprint_content(tmp_path)

        assert "First file content" in result
        assert "Second file content" in result
        assert "\n\n---\n\n" in result

    def test_raises_file_not_found_when_directory_missing(self, tmp_path):
        from svp_config import load_blueprint_content

        with pytest.raises(FileNotFoundError):
            load_blueprint_content(tmp_path)

    def test_raises_file_not_found_when_no_md_files(self, tmp_path):
        from svp_config import load_blueprint_content

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()

        with pytest.raises(FileNotFoundError):
            load_blueprint_content(tmp_path)

    def test_files_are_ordered_alphabetically(self, tmp_path):
        from svp_config import load_blueprint_content

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "z_last.md").write_text("LAST")
        (blueprint_dir / "a_first.md").write_text("FIRST")

        result = load_blueprint_content(tmp_path)

        first_pos = result.index("FIRST")
        last_pos = result.index("LAST")
        assert first_pos < last_pos


# ---------------------------------------------------------------------------
# Section 1: validate_config -- specific invariant checks
# ---------------------------------------------------------------------------


class TestValidateConfigInvariants:
    def test_rejects_missing_iteration_limit(self):
        from svp_config import DEFAULT_CONFIG, validate_config

        config = {k: v for k, v in DEFAULT_CONFIG.items() if k != "iteration_limit"}
        errors = validate_config(config)
        assert any("iteration_limit" in e for e in errors)

    def test_rejects_iteration_limit_less_than_one(self):
        from svp_config import DEFAULT_CONFIG, validate_config

        config = DEFAULT_CONFIG.copy()
        config["iteration_limit"] = 0
        errors = validate_config(config)
        assert any("iteration_limit" in e for e in errors)

    def test_rejects_negative_iteration_limit(self):
        from svp_config import DEFAULT_CONFIG, validate_config

        config = DEFAULT_CONFIG.copy()
        config["iteration_limit"] = -5
        errors = validate_config(config)
        assert any("iteration_limit" in e for e in errors)

    def test_rejects_missing_models(self):
        from svp_config import DEFAULT_CONFIG, validate_config

        config = {k: v for k, v in DEFAULT_CONFIG.items() if k != "models"}
        errors = validate_config(config)
        assert any("models" in e for e in errors)

    def test_rejects_models_without_default_key(self):
        from svp_config import DEFAULT_CONFIG, validate_config

        config = DEFAULT_CONFIG.copy()
        config["models"] = {"test_agent": "claude-opus-4-6"}
        errors = validate_config(config)
        assert any("default" in e for e in errors)

    def test_rejects_context_budget_threshold_zero(self):
        from svp_config import DEFAULT_CONFIG, validate_config

        config = DEFAULT_CONFIG.copy()
        config["context_budget_threshold"] = 0
        errors = validate_config(config)
        assert any("context_budget_threshold" in e for e in errors)

    def test_rejects_context_budget_threshold_over_100(self):
        from svp_config import DEFAULT_CONFIG, validate_config

        config = DEFAULT_CONFIG.copy()
        config["context_budget_threshold"] = 101
        errors = validate_config(config)
        assert any("context_budget_threshold" in e for e in errors)

    def test_accepts_context_budget_threshold_in_range(self):
        from svp_config import DEFAULT_CONFIG, validate_config

        config = DEFAULT_CONFIG.copy()
        config["context_budget_threshold"] = 50
        errors = validate_config(config)
        assert not any("context_budget_threshold" in e for e in errors)

    def test_rejects_negative_compaction_threshold(self):
        from svp_config import DEFAULT_CONFIG, validate_config

        config = DEFAULT_CONFIG.copy()
        config["compaction_character_threshold"] = -1
        errors = validate_config(config)
        assert any("compaction_character_threshold" in e for e in errors)

    def test_rejects_non_boolean_skip_permissions(self):
        from svp_config import DEFAULT_CONFIG, validate_config

        config = DEFAULT_CONFIG.copy()
        config["skip_permissions"] = "yes"
        errors = validate_config(config)
        assert any("skip_permissions" in e for e in errors)


# ---------------------------------------------------------------------------
# Section 1: get_effective_context_budget computation details
# ---------------------------------------------------------------------------


class TestGetEffectiveContextBudgetDetails:
    def test_computes_from_smallest_model_window_minus_overhead(self):
        from svp_config import (
            _CONTEXT_OVERHEAD,
            _MODEL_CONTEXT_WINDOWS,
            get_effective_context_budget,
        )

        config = {
            "context_budget_override": None,
            "models": {
                "test_agent": "claude-opus-4-6",
                "default": "claude-opus-4-6",
            },
        }
        result = get_effective_context_budget(config)
        expected_window = _MODEL_CONTEXT_WINDOWS["claude-opus-4-6"]
        assert result == expected_window - _CONTEXT_OVERHEAD

    def test_picks_smallest_window_with_mixed_models(self):
        from svp_config import (
            _CONTEXT_OVERHEAD,
            get_effective_context_budget,
        )

        config = {
            "context_budget_override": None,
            "models": {
                "test_agent": "claude-opus-4-6",
                "help_agent": "claude-sonnet-4-5-20250514",
                "default": "claude-opus-4-6",
            },
        }
        result = get_effective_context_budget(config)
        # claude-sonnet-4-5-20250514 has 200000, which is smaller than 1000000
        assert result == 200000 - _CONTEXT_OVERHEAD

    def test_override_takes_precedence_over_computation(self):
        from svp_config import get_effective_context_budget

        config = {
            "context_budget_override": 42000,
            "models": {
                "default": "claude-opus-4-6",
            },
        }
        result = get_effective_context_budget(config)
        assert result == 42000


# ---------------------------------------------------------------------------
# Section 1: Config no-caching across invocations
# ---------------------------------------------------------------------------


class TestConfigNoCaching:
    def test_config_changes_on_disk_take_effect_on_next_load(self, tmp_path):
        from svp_config import load_config

        config_v1 = {"iteration_limit": 5}
        (tmp_path / "svp_config.json").write_text(json.dumps(config_v1))
        result1 = load_config(tmp_path)
        assert result1["iteration_limit"] == 5

        config_v2 = {"iteration_limit": 10}
        (tmp_path / "svp_config.json").write_text(json.dumps(config_v2))
        result2 = load_config(tmp_path)
        assert result2["iteration_limit"] == 10


# ---------------------------------------------------------------------------
# Section 2: load_profile deep merge
# ---------------------------------------------------------------------------


class TestLoadProfileDeepMerge:
    def test_deep_merge_fills_missing_nested_keys(self, tmp_path):
        from svp_config import DEFAULT_PROFILE, load_profile

        partial = {
            "pipeline_toolchain": "python_conda_pytest",
            "python_version": "3.12",
            "delivery": {
                "environment_recommendation": "venv",
                # Missing: dependency_format, source_layout, entry_points
            },
        }
        (tmp_path / "project_profile.json").write_text(json.dumps(partial))
        result = load_profile(tmp_path)

        # Overridden value preserved
        assert result["delivery"]["environment_recommendation"] == "venv"
        # Missing nested keys filled from defaults
        assert result["delivery"]["dependency_format"] == DEFAULT_PROFILE["delivery"]["dependency_format"]
        assert result["delivery"]["source_layout"] == DEFAULT_PROFILE["delivery"]["source_layout"]
        assert result["delivery"]["entry_points"] == DEFAULT_PROFILE["delivery"]["entry_points"]

    def test_deep_merge_fills_entire_missing_sections(self, tmp_path):
        from svp_config import DEFAULT_PROFILE, load_profile

        partial = {
            "pipeline_toolchain": "python_conda_pytest",
            "python_version": "3.11",
            # Missing: delivery, vcs, readme, testing, license, quality, fixed
        }
        (tmp_path / "project_profile.json").write_text(json.dumps(partial))
        result = load_profile(tmp_path)

        assert result["delivery"] == DEFAULT_PROFILE["delivery"]
        assert result["vcs"] == DEFAULT_PROFILE["vcs"]
        assert result["readme"] == DEFAULT_PROFILE["readme"]
        assert result["testing"] == DEFAULT_PROFILE["testing"]
        assert result["license"] == DEFAULT_PROFILE["license"]
        assert result["quality"] == DEFAULT_PROFILE["quality"]
        assert result["fixed"] == DEFAULT_PROFILE["fixed"]


# ---------------------------------------------------------------------------
# Section 2: detect_profile_contradictions specific scenarios
# ---------------------------------------------------------------------------


class TestDetectProfileContradictionsSpecific:
    def test_detects_env_recommendation_vs_pipeline_environment_conflict(self):
        from svp_config import DEFAULT_PROFILE, detect_profile_contradictions

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["delivery"]["environment_recommendation"] = "venv"
        profile["fixed"]["pipeline_environment"] = "conda"

        result = detect_profile_contradictions(profile)

        assert len(result) > 0
        assert any("environment_recommendation" in c for c in result)

    def test_no_contradiction_when_env_recommendation_is_none(self):
        from svp_config import DEFAULT_PROFILE, detect_profile_contradictions

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["delivery"]["environment_recommendation"] = "none"
        profile["fixed"]["pipeline_environment"] = "conda"

        result = detect_profile_contradictions(profile)

        env_contradictions = [
            c for c in result if "environment_recommendation" in c
        ]
        assert len(env_contradictions) == 0

    def test_no_contradiction_when_env_matches_pipeline(self):
        from svp_config import DEFAULT_PROFILE, detect_profile_contradictions

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["delivery"]["environment_recommendation"] = "conda"
        profile["fixed"]["pipeline_environment"] = "conda"

        result = detect_profile_contradictions(profile)

        env_contradictions = [
            c for c in result if "environment_recommendation" in c
        ]
        assert len(env_contradictions) == 0

    def test_detects_linter_none_vs_pipeline_tools_ruff(self):
        from svp_config import DEFAULT_PROFILE, detect_profile_contradictions

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["quality"]["linter"] = "none"
        profile["fixed"]["pipeline_quality_tools"] = "ruff_mypy"

        result = detect_profile_contradictions(profile)

        assert len(result) > 0
        assert any("linter" in c for c in result)

    def test_detects_type_checker_none_vs_pipeline_tools_mypy(self):
        from svp_config import DEFAULT_PROFILE, detect_profile_contradictions

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["quality"]["type_checker"] = "none"
        profile["fixed"]["pipeline_quality_tools"] = "ruff_mypy"

        result = detect_profile_contradictions(profile)

        assert len(result) > 0
        assert any("type_checker" in c for c in result)


# ---------------------------------------------------------------------------
# Section 2: validate_profile required sections
# ---------------------------------------------------------------------------


class TestValidateProfileRequiredSections:
    def test_rejects_missing_delivery_section(self):
        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = {k: v for k, v in DEFAULT_PROFILE.items() if k != "delivery"}
        errors = validate_profile(profile)
        assert any("delivery" in e.lower() for e in errors)

    def test_rejects_missing_vcs_section(self):
        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = {k: v for k, v in DEFAULT_PROFILE.items() if k != "vcs"}
        errors = validate_profile(profile)
        assert any("vcs" in e.lower() for e in errors)

    def test_rejects_missing_readme_section(self):
        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = {k: v for k, v in DEFAULT_PROFILE.items() if k != "readme"}
        errors = validate_profile(profile)
        assert any("readme" in e.lower() for e in errors)

    def test_rejects_missing_testing_section(self):
        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = {k: v for k, v in DEFAULT_PROFILE.items() if k != "testing"}
        errors = validate_profile(profile)
        assert any("testing" in e.lower() for e in errors)

    def test_rejects_missing_license_section(self):
        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = {k: v for k, v in DEFAULT_PROFILE.items() if k != "license"}
        errors = validate_profile(profile)
        assert any("license" in e.lower() for e in errors)

    def test_rejects_missing_quality_section(self):
        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = {k: v for k, v in DEFAULT_PROFILE.items() if k != "quality"}
        errors = validate_profile(profile)
        assert any("quality" in e.lower() for e in errors)

    def test_rejects_missing_fixed_section(self):
        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = {k: v for k, v in DEFAULT_PROFILE.items() if k != "fixed"}
        errors = validate_profile(profile)
        assert any("fixed" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# Section 3: get_quality_gate_operations -- error and alias
# ---------------------------------------------------------------------------


class TestGetQualityGateOperations:
    def test_raises_value_error_for_unknown_gate(self):
        from svp_config import get_gate_operations

        from tests.unit_1.test_svp_configuration import MINIMAL_VALID_TOOLCHAIN

        with pytest.raises(ValueError, match="Unknown quality gate"):
            get_gate_operations(MINIMAL_VALID_TOOLCHAIN, "gate_z")

    def test_alias_get_quality_gate_operations_works(self):
        from svp_config import get_quality_gate_operations

        from tests.unit_1.test_svp_configuration import MINIMAL_VALID_TOOLCHAIN

        result = get_quality_gate_operations(MINIMAL_VALID_TOOLCHAIN, "gate_a")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_alias_is_same_function(self):
        from svp_config import get_gate_operations, get_quality_gate_operations

        assert get_quality_gate_operations is get_gate_operations


# ---------------------------------------------------------------------------
# Section 3: resolve_command -- non-existent operation path
# ---------------------------------------------------------------------------


class TestResolveCommandEdgeCases:
    def test_raises_value_error_for_nonexistent_operation(self):
        from svp_config import resolve_command

        from tests.unit_1.test_svp_configuration import MINIMAL_VALID_TOOLCHAIN

        with pytest.raises(ValueError, match="not found"):
            resolve_command(MINIMAL_VALID_TOOLCHAIN, "nonexistent.path", {})

    def test_raises_value_error_when_operation_is_not_string(self):
        from svp_config import resolve_command

        from tests.unit_1.test_svp_configuration import MINIMAL_VALID_TOOLCHAIN

        with pytest.raises(ValueError):
            resolve_command(MINIMAL_VALID_TOOLCHAIN, "testing", {})

    def test_resolved_command_contains_no_braces(self):
        from svp_config import resolve_command

        from tests.unit_1.test_svp_configuration import MINIMAL_VALID_TOOLCHAIN

        result = resolve_command(
            MINIMAL_VALID_TOOLCHAIN,
            "environment.create",
            {"env_name": "myproject", "python_version": "3.11"},
        )
        assert "{" not in result
        assert "}" not in result

    def test_resolved_command_is_a_string(self):
        from svp_config import resolve_command

        from tests.unit_1.test_svp_configuration import MINIMAL_VALID_TOOLCHAIN

        result = resolve_command(
            MINIMAL_VALID_TOOLCHAIN,
            "environment.create",
            {"env_name": "myproject", "python_version": "3.11"},
        )
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Section 3: validate_toolchain -- unrecognized placeholder detection
# ---------------------------------------------------------------------------


class TestValidateToolchainPlaceholders:
    def test_detects_unrecognized_placeholder_in_template(self):
        from svp_config import validate_toolchain

        toolchain_with_bad_placeholder = {
            "environment": {
                "run_prefix": "conda run -n {env_name} --no-banner",
                "create": "conda create -n {env_name} python={bad_placeholder} -y",
            },
            "testing": {
                "run": "{run_prefix} pytest {target} {flags}",
                "framework_packages": ["pytest"],
                "collection_error_indicators": ["ERROR collecting"],
            },
            "packaging": {"build": "{run_prefix} python -m build"},
            "vcs": {"init": "git init"},
            "language": {"python_version_constraint": ">=3.11"},
            "file_structure": {"source_dir": "src"},
            "quality": {
                "packages": ["ruff"],
                "gate_a": ["{run_prefix} ruff check ."],
                "gate_b": ["{run_prefix} pytest"],
            },
        }
        errors = validate_toolchain(toolchain_with_bad_placeholder)
        assert any("bad_placeholder" in e for e in errors)


# ---------------------------------------------------------------------------
# Section 4: derive_env_name -- invariant post-conditions
# ---------------------------------------------------------------------------


class TestDeriveEnvNameInvariants:
    def test_result_contains_no_spaces(self):
        from svp_config import derive_env_name

        result = derive_env_name("My Cool Project Name")
        assert " " not in result

    def test_result_contains_no_hyphens(self):
        from svp_config import derive_env_name

        result = derive_env_name("my-cool-project-name")
        assert "-" not in result

    def test_result_is_lowercase(self):
        from svp_config import derive_env_name

        result = derive_env_name("MyPROJECT")
        assert result == result.lower()

    def test_canonical_derivation_formula(self):
        from svp_config import derive_env_name

        name = "My Cool-Project"
        expected = name.lower().replace(" ", "_").replace("-", "_")
        assert derive_env_name(name) == expected


# ---------------------------------------------------------------------------
# DEFAULT_PROFILE key path regression test (spec Section 30)
# ---------------------------------------------------------------------------


class TestDefaultProfileKeyPaths:
    """Verify every key path in DEFAULT_PROFILE matches the canonical schema."""

    def test_top_level_keys(self):
        from svp_config import DEFAULT_PROFILE

        expected_top_level = {
            "pipeline_toolchain",
            "python_version",
            "delivery",
            "vcs",
            "readme",
            "testing",
            "license",
            "quality",
            "pipeline",
            "fixed",
            "created_at",
        }
        assert set(DEFAULT_PROFILE.keys()) == expected_top_level

    def test_delivery_keys(self):
        from svp_config import DEFAULT_PROFILE

        expected = {
            "environment_recommendation",
            "dependency_format",
            "source_layout",
            "entry_points",
        }
        assert set(DEFAULT_PROFILE["delivery"].keys()) == expected

    def test_vcs_keys(self):
        from svp_config import DEFAULT_PROFILE

        expected = {
            "commit_style",
            "commit_template",
            "issue_references",
            "branch_strategy",
            "tagging",
            "conventions_notes",
            "changelog",
            "github",
        }
        assert set(DEFAULT_PROFILE["vcs"].keys()) == expected

    def test_readme_keys(self):
        from svp_config import DEFAULT_PROFILE

        expected = {
            "mode",
            "existing_path",
            "audience",
            "sections",
            "depth",
            "include_math_notation",
            "include_glossary",
            "include_data_formats",
            "include_code_examples",
            "code_example_focus",
            "custom_sections",
            "docstring_convention",
            "citation_file",
            "contributing_guide",
        }
        assert set(DEFAULT_PROFILE["readme"].keys()) == expected

    def test_testing_keys(self):
        from svp_config import DEFAULT_PROFILE

        expected = {
            "coverage_target",
            "readable_test_names",
            "readme_test_scenarios",
        }
        assert set(DEFAULT_PROFILE["testing"].keys()) == expected

    def test_license_keys(self):
        from svp_config import DEFAULT_PROFILE

        expected = {
            "type",
            "holder",
            "author",
            "year",
            "contact",
            "spdx_headers",
            "additional_metadata",
        }
        assert set(DEFAULT_PROFILE["license"].keys()) == expected

    def test_license_additional_metadata_keys(self):
        from svp_config import DEFAULT_PROFILE

        expected = {"citation", "funding", "acknowledgments"}
        assert set(DEFAULT_PROFILE["license"]["additional_metadata"].keys()) == expected

    def test_quality_keys(self):
        from svp_config import DEFAULT_PROFILE

        expected = {
            "linter",
            "formatter",
            "type_checker",
            "import_sorter",
            "line_length",
        }
        assert set(DEFAULT_PROFILE["quality"].keys()) == expected

    def test_fixed_keys(self):
        from svp_config import DEFAULT_PROFILE

        expected = {
            "language",
            "pipeline_environment",
            "test_framework",
            "build_backend",
            "vcs_system",
            "source_layout_during_build",
            "pipeline_quality_tools",
        }
        assert set(DEFAULT_PROFILE["fixed"].keys()) == expected


# ---------------------------------------------------------------------------
# Section 3: validate_python_version -- additional constraint operators
# ---------------------------------------------------------------------------


class TestValidatePythonVersionAdditional:
    def test_less_than_constraint(self):
        from svp_config import validate_python_version

        assert validate_python_version("3.10", "<3.11") is True
        assert validate_python_version("3.11", "<3.11") is False

    def test_equality_constraint(self):
        from svp_config import validate_python_version

        assert validate_python_version("3.11", "==3.11") is True
        assert validate_python_version("3.12", "==3.11") is False

    def test_less_than_or_equal_constraint(self):
        from svp_config import validate_python_version

        assert validate_python_version("3.11", "<=3.11") is True
        assert validate_python_version("3.12", "<=3.11") is False

    def test_not_equal_constraint(self):
        from svp_config import validate_python_version

        assert validate_python_version("3.10", "!=3.11") is True
        assert validate_python_version("3.11", "!=3.11") is False


# ---------------------------------------------------------------------------
# Section 1: write_default_config additional checks
# ---------------------------------------------------------------------------


class TestWriteDefaultConfigAdditional:
    def test_written_content_is_parseable_json(self, tmp_path):
        from svp_config import write_default_config

        result_path = write_default_config(tmp_path)
        content = result_path.read_text()
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_written_file_uses_artifact_filename(self, tmp_path):
        from svp_config import ARTIFACT_FILENAMES, write_default_config

        result_path = write_default_config(tmp_path)
        assert result_path.name == ARTIFACT_FILENAMES["svp_config"]


# ---------------------------------------------------------------------------
# load_config post-condition: result is always a dict with required keys
# ---------------------------------------------------------------------------


class TestLoadConfigPostConditions:
    def test_result_is_dict(self, tmp_path):
        from svp_config import load_config

        result = load_config(tmp_path)
        assert isinstance(result, dict)

    def test_result_contains_iteration_limit(self, tmp_path):
        from svp_config import load_config

        result = load_config(tmp_path)
        assert "iteration_limit" in result

    def test_result_contains_models(self, tmp_path):
        from svp_config import load_config

        result = load_config(tmp_path)
        assert "models" in result

    def test_result_iteration_limit_at_least_one(self, tmp_path):
        from svp_config import load_config

        result = load_config(tmp_path)
        assert result["iteration_limit"] >= 1

    def test_loaded_config_with_file_has_all_default_keys(self, tmp_path):
        from svp_config import DEFAULT_CONFIG, load_config

        (tmp_path / "svp_config.json").write_text(json.dumps({"iteration_limit": 7}))
        result = load_config(tmp_path)
        for key in DEFAULT_CONFIG:
            assert key in result, f"Missing key '{key}' after merge"


# ---------------------------------------------------------------------------
# load_profile post-conditions
# ---------------------------------------------------------------------------


class TestLoadProfilePostConditions:
    def test_result_contains_all_required_sections(self, tmp_path):
        from svp_config import DEFAULT_PROFILE, load_profile

        (tmp_path / "project_profile.json").write_text(json.dumps(DEFAULT_PROFILE))
        result = load_profile(tmp_path)
        for section in ["delivery", "vcs", "readme", "testing", "license", "quality", "fixed"]:
            assert section in result, f"Missing section '{section}'"

    def test_result_is_dict(self, tmp_path):
        from svp_config import DEFAULT_PROFILE, load_profile

        (tmp_path / "project_profile.json").write_text(json.dumps(DEFAULT_PROFILE))
        result = load_profile(tmp_path)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# load_profile error message includes path
# ---------------------------------------------------------------------------


class TestLoadProfileErrorMessages:
    def test_runtime_error_message_includes_resume_hint(self, tmp_path):
        from svp_config import load_profile

        with pytest.raises(RuntimeError, match="Resume from Stage 0"):
            load_profile(tmp_path)

    def test_malformed_json_raises_runtime_error(self, tmp_path):
        from svp_config import load_profile

        (tmp_path / "project_profile.json").write_text("{malformed json!!!")
        with pytest.raises(RuntimeError, match="not valid JSON"):
            load_profile(tmp_path)


# ---------------------------------------------------------------------------
# load_toolchain error messages
# ---------------------------------------------------------------------------


class TestLoadToolchainErrorMessages:
    def test_runtime_error_includes_reinstall_hint(self, tmp_path):
        from svp_config import load_toolchain

        with pytest.raises(RuntimeError, match="Re-run svp new"):
            load_toolchain(tmp_path)

    def test_malformed_json_raises_runtime_error(self, tmp_path):
        from svp_config import load_toolchain

        (tmp_path / "toolchain.json").write_text("{bad json content")
        with pytest.raises(RuntimeError, match="not valid JSON"):
            load_toolchain(tmp_path)

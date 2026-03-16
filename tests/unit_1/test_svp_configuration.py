"""
Tests for Unit 1: SVP Configuration.

Synthetic data generation assumptions:
- Config JSON files are created in tmp_path fixtures with known content.
- DEFAULT_CONFIG and DEFAULT_PROFILE constants are imported from the module under test.
- Toolchain JSON files use a minimal valid structure with all required sections:
  environment, testing, packaging, vcs, language, file_structure, quality.
- Profile JSON files use DEFAULT_PROFILE structure with selective overrides.
- All file I/O tests use pytest tmp_path to avoid filesystem side effects.
- Model context windows are assumed to follow standard Claude model sizes.
"""

import json

import pytest

# ---------------------------------------------------------------------------
# Section 0: ARTIFACT_FILENAMES
# ---------------------------------------------------------------------------


class TestArtifactFilenames:
    def test_artifact_filenames_contains_all_canonical_keys(self):
        from svp_config import ARTIFACT_FILENAMES

        expected_keys = {
            "stakeholder_spec",
            "blueprint_prose",
            "blueprint_contracts",
            "project_context",
            "project_profile",
            "toolchain",
            "ruff_config",
            "pipeline_state",
            "svp_config",
            "lessons_learned",
        }
        assert set(ARTIFACT_FILENAMES.keys()) == expected_keys

    def test_artifact_filenames_values_are_strings(self):
        from svp_config import ARTIFACT_FILENAMES

        for key, value in ARTIFACT_FILENAMES.items():
            assert isinstance(value, str), (
                f"ARTIFACT_FILENAMES['{key}'] is not a string"
            )

    def test_artifact_filenames_stakeholder_spec(self):
        from svp_config import ARTIFACT_FILENAMES

        assert ARTIFACT_FILENAMES["stakeholder_spec"] == "stakeholder_spec.md"

    def test_artifact_filenames_blueprint_prose(self):
        from svp_config import ARTIFACT_FILENAMES

        assert ARTIFACT_FILENAMES["blueprint_prose"] == "blueprint_prose.md"

    def test_artifact_filenames_blueprint_contracts(self):
        from svp_config import ARTIFACT_FILENAMES

        assert ARTIFACT_FILENAMES["blueprint_contracts"] == "blueprint_contracts.md"

    def test_artifact_filenames_project_profile(self):
        from svp_config import ARTIFACT_FILENAMES

        assert ARTIFACT_FILENAMES["project_profile"] == "project_profile.json"

    def test_artifact_filenames_toolchain(self):
        from svp_config import ARTIFACT_FILENAMES

        assert ARTIFACT_FILENAMES["toolchain"] == "toolchain.json"

    def test_artifact_filenames_pipeline_state(self):
        from svp_config import ARTIFACT_FILENAMES

        assert ARTIFACT_FILENAMES["pipeline_state"] == "pipeline_state.json"

    def test_artifact_filenames_svp_config(self):
        from svp_config import ARTIFACT_FILENAMES

        assert ARTIFACT_FILENAMES["svp_config"] == "svp_config.json"

    def test_artifact_filenames_lessons_learned(self):
        from svp_config import ARTIFACT_FILENAMES

        assert ARTIFACT_FILENAMES["lessons_learned"] == "svp_2_1_lessons_learned.md"

    def test_artifact_filenames_ruff_config(self):
        from svp_config import ARTIFACT_FILENAMES

        assert ARTIFACT_FILENAMES["ruff_config"] == "ruff.toml"

    def test_artifact_filenames_project_context(self):
        from svp_config import ARTIFACT_FILENAMES

        assert ARTIFACT_FILENAMES["project_context"] == "project_context.md"


# ---------------------------------------------------------------------------
# Section 1: SVP Configuration (svp_config.json)
# ---------------------------------------------------------------------------


class TestDefaultConfig:
    def test_default_config_has_iteration_limit(self):
        from svp_config import DEFAULT_CONFIG

        assert DEFAULT_CONFIG["iteration_limit"] == 3

    def test_default_config_has_models(self):
        from svp_config import DEFAULT_CONFIG

        assert "models" in DEFAULT_CONFIG
        assert DEFAULT_CONFIG["models"]["test_agent"] == "claude-opus-4-6"
        assert DEFAULT_CONFIG["models"]["implementation_agent"] == "claude-opus-4-6"
        assert DEFAULT_CONFIG["models"]["help_agent"] == "claude-sonnet-4-6"
        assert DEFAULT_CONFIG["models"]["default"] == "claude-opus-4-6"

    def test_default_config_context_budget_override_is_none(self):
        from svp_config import DEFAULT_CONFIG

        assert DEFAULT_CONFIG["context_budget_override"] is None

    def test_default_config_context_budget_threshold(self):
        from svp_config import DEFAULT_CONFIG

        assert DEFAULT_CONFIG["context_budget_threshold"] == 65

    def test_default_config_compaction_character_threshold(self):
        from svp_config import DEFAULT_CONFIG

        assert DEFAULT_CONFIG["compaction_character_threshold"] == 200

    def test_default_config_auto_save_is_true(self):
        from svp_config import DEFAULT_CONFIG

        assert DEFAULT_CONFIG["auto_save"] is True

    def test_default_config_skip_permissions_is_true(self):
        from svp_config import DEFAULT_CONFIG

        assert DEFAULT_CONFIG["skip_permissions"] is True


class TestLoadConfig:
    def test_load_config_returns_defaults_when_file_missing(self, tmp_path):
        from svp_config import DEFAULT_CONFIG, load_config

        result = load_config(tmp_path)
        assert result == DEFAULT_CONFIG

    def test_load_config_returns_defaults_copy_not_reference(self, tmp_path):
        from svp_config import DEFAULT_CONFIG, load_config

        result = load_config(tmp_path)
        assert result is not DEFAULT_CONFIG

    def test_load_config_merges_file_over_defaults(self, tmp_path):
        from svp_config import load_config

        config = {"iteration_limit": 5}
        (tmp_path / "svp_config.json").write_text(json.dumps(config))
        result = load_config(tmp_path)
        assert result["iteration_limit"] == 5
        # Missing keys filled from defaults
        assert "models" in result
        assert "auto_save" in result

    def test_load_config_file_values_override_defaults(self, tmp_path):
        from svp_config import load_config

        config = {"auto_save": False, "skip_permissions": False}
        (tmp_path / "svp_config.json").write_text(json.dumps(config))
        result = load_config(tmp_path)
        assert result["auto_save"] is False
        assert result["skip_permissions"] is False

    def test_load_config_missing_keys_filled_from_defaults(self, tmp_path):
        from svp_config import DEFAULT_CONFIG, load_config

        config = {"iteration_limit": 10}
        (tmp_path / "svp_config.json").write_text(json.dumps(config))
        result = load_config(tmp_path)
        assert (
            result["context_budget_threshold"]
            == DEFAULT_CONFIG["context_budget_threshold"]
        )
        assert (
            result["compaction_character_threshold"]
            == DEFAULT_CONFIG["compaction_character_threshold"]
        )


class TestValidateConfig:
    def test_validate_config_valid_returns_empty_list(self):
        from svp_config import DEFAULT_CONFIG, validate_config

        errors = validate_config(DEFAULT_CONFIG.copy())
        assert errors == []

    def test_validate_config_returns_list_of_strings_on_error(self):
        from svp_config import validate_config

        errors = validate_config({})
        assert isinstance(errors, list)
        if errors:
            for error in errors:
                assert isinstance(error, str)


class TestGetModelForAgent:
    def test_get_model_for_agent_returns_specific_model(self):
        from svp_config import DEFAULT_CONFIG, get_model_for_agent

        result = get_model_for_agent(DEFAULT_CONFIG, "test_agent")
        assert result == "claude-opus-4-6"

    def test_get_model_for_agent_returns_default_for_unknown_agent(self):
        from svp_config import DEFAULT_CONFIG, get_model_for_agent

        result = get_model_for_agent(DEFAULT_CONFIG, "nonexistent_agent")
        assert result == DEFAULT_CONFIG["models"]["default"]

    def test_get_model_for_agent_help_agent(self):
        from svp_config import DEFAULT_CONFIG, get_model_for_agent

        result = get_model_for_agent(DEFAULT_CONFIG, "help_agent")
        assert result == "claude-sonnet-4-6"

    def test_get_model_for_agent_implementation_agent(self):
        from svp_config import DEFAULT_CONFIG, get_model_for_agent

        result = get_model_for_agent(DEFAULT_CONFIG, "implementation_agent")
        assert result == "claude-opus-4-6"


class TestGetEffectiveContextBudget:
    def test_get_effective_context_budget_returns_override_when_set(self):
        from svp_config import DEFAULT_CONFIG, get_effective_context_budget

        config = DEFAULT_CONFIG.copy()
        config["context_budget_override"] = 50000
        result = get_effective_context_budget(config)
        assert result == 50000

    def test_get_effective_context_budget_computes_from_model_when_no_override(self):
        from svp_config import DEFAULT_CONFIG, get_effective_context_budget

        config = DEFAULT_CONFIG.copy()
        config["context_budget_override"] = None
        result = get_effective_context_budget(config)
        # Should compute from smallest model context window minus 20,000 overhead
        assert isinstance(result, int)
        assert result > 0


class TestWriteDefaultConfig:
    def test_write_default_config_creates_file(self, tmp_path):
        from svp_config import write_default_config

        result_path = write_default_config(tmp_path)
        assert result_path.exists()

    def test_write_default_config_returns_correct_path(self, tmp_path):
        from svp_config import write_default_config

        result_path = write_default_config(tmp_path)
        assert result_path == tmp_path / "svp_config.json"

    def test_write_default_config_content_matches_defaults(self, tmp_path):
        from svp_config import DEFAULT_CONFIG, write_default_config

        result_path = write_default_config(tmp_path)
        written = json.loads(result_path.read_text())
        assert written == DEFAULT_CONFIG

    def test_write_default_config_is_formatted_json(self, tmp_path):
        from svp_config import write_default_config

        result_path = write_default_config(tmp_path)
        content = result_path.read_text()
        # Formatted JSON should have newlines (not compact single-line)
        assert "\n" in content


# ---------------------------------------------------------------------------
# Section 2: Project Profile (project_profile.json)
# ---------------------------------------------------------------------------


class TestDefaultProfile:
    def test_default_profile_pipeline_toolchain(self):
        from svp_config import DEFAULT_PROFILE

        assert DEFAULT_PROFILE["pipeline_toolchain"] == "python_conda_pytest"

    def test_default_profile_python_version(self):
        from svp_config import DEFAULT_PROFILE

        assert DEFAULT_PROFILE["python_version"] == "3.11"

    def test_default_profile_has_delivery_section(self):
        from svp_config import DEFAULT_PROFILE

        assert "delivery" in DEFAULT_PROFILE
        assert DEFAULT_PROFILE["delivery"]["environment_recommendation"] == "conda"
        assert DEFAULT_PROFILE["delivery"]["dependency_format"] == "environment.yml"
        assert DEFAULT_PROFILE["delivery"]["source_layout"] == "conventional"
        assert DEFAULT_PROFILE["delivery"]["entry_points"] is False

    def test_default_profile_has_vcs_section(self):
        from svp_config import DEFAULT_PROFILE

        vcs = DEFAULT_PROFILE["vcs"]
        assert vcs["commit_style"] == "conventional"
        assert vcs["commit_template"] is None
        assert vcs["issue_references"] is False
        assert vcs["branch_strategy"] == "main-only"
        assert vcs["tagging"] == "semver"
        assert vcs["conventions_notes"] is None
        assert vcs["changelog"] == "none"

    def test_default_profile_has_readme_section(self):
        from svp_config import DEFAULT_PROFILE

        readme = DEFAULT_PROFILE["readme"]
        assert readme["audience"] == "domain expert"
        assert readme["depth"] == "standard"
        assert readme["include_math_notation"] is False
        assert readme["include_glossary"] is False
        assert readme["include_data_formats"] is False
        assert readme["include_code_examples"] is False
        assert readme["code_example_focus"] is None
        assert readme["custom_sections"] is None
        assert readme["docstring_convention"] == "google"
        assert readme["citation_file"] is False
        assert readme["contributing_guide"] is False

    def test_default_profile_readme_sections_list(self):
        from svp_config import DEFAULT_PROFILE

        expected_sections = [
            "Header",
            "What it does",
            "Who it's for",
            "Installation",
            "Configuration",
            "Usage",
            "Quick Tutorial",
            "Examples",
            "Project Structure",
            "License",
        ]
        assert DEFAULT_PROFILE["readme"]["sections"] == expected_sections

    def test_default_profile_has_testing_section(self):
        from svp_config import DEFAULT_PROFILE

        testing = DEFAULT_PROFILE["testing"]
        assert testing["coverage_target"] is None
        assert testing["readable_test_names"] is True
        assert testing["readme_test_scenarios"] is False

    def test_default_profile_has_license_section(self):
        from svp_config import DEFAULT_PROFILE

        lic = DEFAULT_PROFILE["license"]
        assert lic["type"] == "MIT"
        assert lic["holder"] == ""
        assert lic["author"] == ""
        assert lic["year"] == ""
        assert lic["contact"] is None
        assert lic["spdx_headers"] is False
        assert lic["additional_metadata"]["citation"] is None
        assert lic["additional_metadata"]["funding"] is None
        assert lic["additional_metadata"]["acknowledgments"] is None

    def test_default_profile_has_quality_section(self):
        from svp_config import DEFAULT_PROFILE

        quality = DEFAULT_PROFILE["quality"]
        assert quality["linter"] == "ruff"
        assert quality["formatter"] == "ruff"
        assert quality["type_checker"] == "none"
        assert quality["import_sorter"] == "ruff"
        assert quality["line_length"] == 88

    def test_default_profile_has_fixed_section(self):
        from svp_config import DEFAULT_PROFILE

        fixed = DEFAULT_PROFILE["fixed"]
        assert fixed["language"] == "python"
        assert fixed["pipeline_environment"] == "conda"
        assert fixed["test_framework"] == "pytest"
        assert fixed["build_backend"] == "setuptools"
        assert fixed["vcs_system"] == "git"
        assert fixed["source_layout_during_build"] == "svp_native"
        assert fixed["pipeline_quality_tools"] == "ruff_mypy"

    def test_default_profile_has_created_at(self):
        from svp_config import DEFAULT_PROFILE

        assert "created_at" in DEFAULT_PROFILE
        assert DEFAULT_PROFILE["created_at"] == ""


class TestCanonicalNamingInvariant:
    """Regression tests for canonical naming (Bug 22 fix, NEW IN 2.1)."""

    def test_profile_uses_delivery_not_packaging(self):
        from svp_config import DEFAULT_PROFILE

        assert "delivery" in DEFAULT_PROFILE
        assert "packaging" not in DEFAULT_PROFILE

    def test_profile_uses_license_not_licensing(self):
        from svp_config import DEFAULT_PROFILE

        assert "license" in DEFAULT_PROFILE
        assert "licensing" not in DEFAULT_PROFILE

    def test_profile_uses_audience_not_target_audience(self):
        from svp_config import DEFAULT_PROFILE

        assert "audience" in DEFAULT_PROFILE["readme"]
        assert "target_audience" not in DEFAULT_PROFILE["readme"]

    def test_profile_uses_environment_recommendation_not_environment(self):
        from svp_config import DEFAULT_PROFILE

        assert "environment_recommendation" in DEFAULT_PROFILE["delivery"]
        # "environment" could exist as a different field, but the canonical
        # field name for the recommendation is "environment_recommendation"

    def test_profile_has_quality_section_canonical(self):
        from svp_config import DEFAULT_PROFILE

        assert "quality" in DEFAULT_PROFILE


class TestLoadProfile:
    def test_load_profile_reads_valid_file(self, tmp_path):
        from svp_config import DEFAULT_PROFILE, load_profile

        profile_data = DEFAULT_PROFILE.copy()
        profile_data["created_at"] = "2026-03-15"
        (tmp_path / "project_profile.json").write_text(json.dumps(profile_data))
        result = load_profile(tmp_path)
        assert result["created_at"] == "2026-03-15"

    def test_load_profile_fills_missing_fields_from_defaults(self, tmp_path):
        from svp_config import load_profile

        partial = {
            "pipeline_toolchain": "python_conda_pytest",
            "python_version": "3.12",
        }
        (tmp_path / "project_profile.json").write_text(json.dumps(partial))
        result = load_profile(tmp_path)
        assert result["python_version"] == "3.12"
        # Missing fields filled from defaults
        assert "delivery" in result

    def test_load_profile_ignores_unknown_fields(self, tmp_path):
        from svp_config import DEFAULT_PROFILE, load_profile

        profile_data = DEFAULT_PROFILE.copy()
        profile_data["future_field"] = "some_value"
        (tmp_path / "project_profile.json").write_text(json.dumps(profile_data))
        load_profile(tmp_path)
        # Should not raise, unknown fields are ignored for forward compatibility

    def test_load_profile_raises_runtime_error_when_missing(self, tmp_path):
        from svp_config import load_profile

        with pytest.raises(RuntimeError, match="not found"):
            load_profile(tmp_path)

    def test_load_profile_raises_runtime_error_on_malformed_json(self, tmp_path):
        from svp_config import load_profile

        (tmp_path / "project_profile.json").write_text("{invalid json content")
        with pytest.raises((RuntimeError, json.JSONDecodeError)):
            load_profile(tmp_path)


class TestValidateProfile:
    def test_validate_profile_valid_returns_empty_list(self):
        from svp_config import DEFAULT_PROFILE, validate_profile

        errors = validate_profile(DEFAULT_PROFILE)
        assert errors == []

    def test_validate_profile_checks_delivery_environment_recommendation_enum(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["delivery"]["environment_recommendation"] = "invalid_env"
        errors = validate_profile(profile)
        assert len(errors) > 0

    def test_validate_profile_accepts_valid_environment_recommendations(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        for env in ["conda", "pyenv", "venv", "poetry", "none"]:
            profile = copy.deepcopy(DEFAULT_PROFILE)
            profile["delivery"]["environment_recommendation"] = env
            errors = validate_profile(profile)
            env_errors = [
                e for e in errors if "environment_recommendation" in e.lower()
            ]
            assert len(env_errors) == 0, (
                f"Unexpected error for env '{env}': {env_errors}"
            )

    def test_validate_profile_checks_source_layout_enum(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["delivery"]["source_layout"] = "bad_layout"
        errors = validate_profile(profile)
        assert len(errors) > 0

    def test_validate_profile_accepts_valid_source_layouts(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        for layout in ["conventional", "flat", "svp_native"]:
            profile = copy.deepcopy(DEFAULT_PROFILE)
            profile["delivery"]["source_layout"] = layout
            errors = validate_profile(profile)
            layout_errors = [e for e in errors if "source_layout" in e.lower()]
            assert len(layout_errors) == 0, f"Unexpected error for layout '{layout}'"

    def test_validate_profile_checks_commit_style_enum(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["vcs"]["commit_style"] = "bad_style"
        errors = validate_profile(profile)
        assert len(errors) > 0

    def test_validate_profile_accepts_valid_commit_styles(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        for style in ["conventional", "freeform", "custom"]:
            profile = copy.deepcopy(DEFAULT_PROFILE)
            profile["vcs"]["commit_style"] = style
            errors = validate_profile(profile)
            style_errors = [e for e in errors if "commit_style" in e.lower()]
            assert len(style_errors) == 0

    def test_validate_profile_checks_changelog_enum(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["vcs"]["changelog"] = "invalid_changelog"
        errors = validate_profile(profile)
        assert len(errors) > 0

    def test_validate_profile_accepts_valid_changelogs(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        for cl in ["keep_a_changelog", "conventional_changelog", "none"]:
            profile = copy.deepcopy(DEFAULT_PROFILE)
            profile["vcs"]["changelog"] = cl
            errors = validate_profile(profile)
            cl_errors = [e for e in errors if "changelog" in e.lower()]
            assert len(cl_errors) == 0

    def test_validate_profile_checks_readme_depth_enum(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["readme"]["depth"] = "ultra"
        errors = validate_profile(profile)
        assert len(errors) > 0

    def test_validate_profile_accepts_valid_readme_depths(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        for depth in ["minimal", "standard", "comprehensive"]:
            profile = copy.deepcopy(DEFAULT_PROFILE)
            profile["readme"]["depth"] = depth
            errors = validate_profile(profile)
            depth_errors = [e for e in errors if "depth" in e.lower()]
            assert len(depth_errors) == 0

    def test_validate_profile_checks_coverage_target_null_or_int_0_100(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        # None is valid
        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["testing"]["coverage_target"] = None
        errors = validate_profile(profile)
        cov_errors = [e for e in errors if "coverage_target" in e.lower()]
        assert len(cov_errors) == 0

        # Integer in range is valid
        profile["testing"]["coverage_target"] = 80
        errors = validate_profile(profile)
        cov_errors = [e for e in errors if "coverage_target" in e.lower()]
        assert len(cov_errors) == 0

        # 0 is valid
        profile["testing"]["coverage_target"] = 0
        errors = validate_profile(profile)
        cov_errors = [e for e in errors if "coverage_target" in e.lower()]
        assert len(cov_errors) == 0

        # 100 is valid
        profile["testing"]["coverage_target"] = 100
        errors = validate_profile(profile)
        cov_errors = [e for e in errors if "coverage_target" in e.lower()]
        assert len(cov_errors) == 0

    def test_validate_profile_rejects_coverage_target_out_of_range(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["testing"]["coverage_target"] = 101
        errors = validate_profile(profile)
        assert len(errors) > 0

        profile["testing"]["coverage_target"] = -1
        errors = validate_profile(profile)
        assert len(errors) > 0

    def test_validate_profile_checks_quality_linter_enum(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["quality"]["linter"] = "invalid_linter"
        errors = validate_profile(profile)
        assert len(errors) > 0

    def test_validate_profile_accepts_valid_linters(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        for linter in ["ruff", "flake8", "pylint", "none"]:
            profile = copy.deepcopy(DEFAULT_PROFILE)
            profile["quality"]["linter"] = linter
            errors = validate_profile(profile)
            linter_errors = [e for e in errors if "linter" in e.lower()]
            assert len(linter_errors) == 0

    def test_validate_profile_checks_quality_formatter_enum(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["quality"]["formatter"] = "yapf"
        errors = validate_profile(profile)
        assert len(errors) > 0

    def test_validate_profile_accepts_valid_formatters(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        for fmt in ["ruff", "black", "none"]:
            profile = copy.deepcopy(DEFAULT_PROFILE)
            profile["quality"]["formatter"] = fmt
            errors = validate_profile(profile)
            fmt_errors = [e for e in errors if "formatter" in e.lower()]
            assert len(fmt_errors) == 0

    def test_validate_profile_checks_quality_type_checker_enum(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["quality"]["type_checker"] = "invalid"
        errors = validate_profile(profile)
        assert len(errors) > 0

    def test_validate_profile_accepts_valid_type_checkers(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        for tc in ["mypy", "pyright", "none"]:
            profile = copy.deepcopy(DEFAULT_PROFILE)
            profile["quality"]["type_checker"] = tc
            errors = validate_profile(profile)
            tc_errors = [e for e in errors if "type_checker" in e.lower()]
            assert len(tc_errors) == 0

    def test_validate_profile_checks_quality_import_sorter_enum(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["quality"]["import_sorter"] = "autopep8"
        errors = validate_profile(profile)
        assert len(errors) > 0

    def test_validate_profile_accepts_valid_import_sorters(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        for sorter in ["ruff", "isort", "none"]:
            profile = copy.deepcopy(DEFAULT_PROFILE)
            profile["quality"]["import_sorter"] = sorter
            errors = validate_profile(profile)
            sorter_errors = [e for e in errors if "import_sorter" in e.lower()]
            assert len(sorter_errors) == 0

    def test_validate_profile_checks_quality_line_length_positive_int(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["quality"]["line_length"] = 0
        errors = validate_profile(profile)
        assert len(errors) > 0

        profile["quality"]["line_length"] = -10
        errors = validate_profile(profile)
        assert len(errors) > 0

    def test_validate_profile_accepts_valid_line_length(self):
        import copy

        from svp_config import DEFAULT_PROFILE, validate_profile

        profile = copy.deepcopy(DEFAULT_PROFILE)
        profile["quality"]["line_length"] = 120
        errors = validate_profile(profile)
        ll_errors = [e for e in errors if "line_length" in e.lower()]
        assert len(ll_errors) == 0


class TestGetProfileSection:
    def test_get_profile_section_returns_section(self):
        from svp_config import DEFAULT_PROFILE, get_profile_section

        result = get_profile_section(DEFAULT_PROFILE, "delivery")
        assert result == DEFAULT_PROFILE["delivery"]

    def test_get_profile_section_returns_testing_section(self):
        from svp_config import DEFAULT_PROFILE, get_profile_section

        result = get_profile_section(DEFAULT_PROFILE, "testing")
        assert result == DEFAULT_PROFILE["testing"]

    def test_get_profile_section_raises_key_error_for_missing(self):
        from svp_config import DEFAULT_PROFILE, get_profile_section

        with pytest.raises(KeyError):
            get_profile_section(DEFAULT_PROFILE, "nonexistent_section")


class TestDetectProfileContradictions:
    def test_detect_profile_contradictions_no_contradictions(self):
        from svp_config import DEFAULT_PROFILE, detect_profile_contradictions

        result = detect_profile_contradictions(DEFAULT_PROFILE)
        assert isinstance(result, list)

    def test_detect_profile_contradictions_returns_list(self):
        import copy

        from svp_config import DEFAULT_PROFILE, detect_profile_contradictions

        profile = copy.deepcopy(DEFAULT_PROFILE)
        result = detect_profile_contradictions(profile)
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, str)


# ---------------------------------------------------------------------------
# Section 3: Pipeline Toolchain (toolchain.json)
# ---------------------------------------------------------------------------


MINIMAL_VALID_TOOLCHAIN = {
    "environment": {
        "run_prefix": "conda run -n {env_name} --no-banner",
        "create": "conda create -n {env_name} python={python_version} -y",
        "install": "{run_prefix} pip install -e .",
    },
    "testing": {
        "run": "{run_prefix} pytest {target} {flags}",
        "framework_packages": ["pytest", "pytest-cov"],
        "collection_error_indicators": ["ERROR collecting", "ImportError"],
    },
    "packaging": {
        "build": "{run_prefix} python -m build",
    },
    "vcs": {
        "init": "git init",
    },
    "language": {
        "python_version_constraint": ">=3.11",
    },
    "file_structure": {
        "source_dir": "src",
    },
    "quality": {
        "packages": ["ruff", "mypy"],
        "gate_a": ["{run_prefix} ruff check ."],
        "gate_b": ["{run_prefix} ruff check .", "{run_prefix} pytest"],
    },
}


class TestLoadToolchain:
    def test_load_toolchain_reads_valid_file(self, tmp_path):
        from svp_config import load_toolchain

        (tmp_path / "toolchain.json").write_text(json.dumps(MINIMAL_VALID_TOOLCHAIN))
        result = load_toolchain(tmp_path)
        assert "environment" in result
        assert "testing" in result

    def test_load_toolchain_raises_runtime_error_when_missing(self, tmp_path):
        from svp_config import load_toolchain

        with pytest.raises(RuntimeError, match="not found"):
            load_toolchain(tmp_path)

    def test_load_toolchain_raises_on_malformed_json(self, tmp_path):
        from svp_config import load_toolchain

        (tmp_path / "toolchain.json").write_text("{bad json")
        with pytest.raises((RuntimeError, json.JSONDecodeError)):
            load_toolchain(tmp_path)

    def test_load_toolchain_no_fallback_to_hardcoded_values(self, tmp_path):
        from svp_config import load_toolchain

        # When file is missing, must raise -- no fallback
        with pytest.raises(RuntimeError):
            load_toolchain(tmp_path)


class TestValidateToolchain:
    def test_validate_toolchain_valid_returns_empty_list(self):
        from svp_config import validate_toolchain

        errors = validate_toolchain(MINIMAL_VALID_TOOLCHAIN)
        assert errors == []

    def test_validate_toolchain_missing_required_section(self):
        from svp_config import validate_toolchain

        incomplete = {
            k: v for k, v in MINIMAL_VALID_TOOLCHAIN.items() if k != "environment"
        }
        errors = validate_toolchain(incomplete)
        assert len(errors) > 0

    def test_validate_toolchain_checks_all_required_sections(self):
        from svp_config import validate_toolchain

        required_sections = [
            "environment",
            "testing",
            "packaging",
            "vcs",
            "language",
            "file_structure",
            "quality",
        ]
        for section in required_sections:
            incomplete = {
                k: v for k, v in MINIMAL_VALID_TOOLCHAIN.items() if k != section
            }
            errors = validate_toolchain(incomplete)
            assert len(errors) > 0, f"Expected error for missing section '{section}'"

    def test_validate_toolchain_returns_list_of_strings(self):
        from svp_config import validate_toolchain

        errors = validate_toolchain({})
        assert isinstance(errors, list)
        for error in errors:
            assert isinstance(error, str)


class TestResolveCommand:
    def test_resolve_command_substitutes_env_name(self):
        from svp_config import resolve_command

        result = resolve_command(
            MINIMAL_VALID_TOOLCHAIN,
            "environment.create",
            {"env_name": "myproject", "python_version": "3.11"},
        )
        assert "myproject" in result
        assert "3.11" in result

    def test_resolve_command_resolves_run_prefix_first(self):
        from svp_config import resolve_command

        result = resolve_command(
            MINIMAL_VALID_TOOLCHAIN,
            "testing.run",
            {"env_name": "myproject", "target": "tests/", "flags": "-v"},
        )
        assert "conda run -n myproject --no-banner" in result
        assert "pytest" in result
        assert "tests/" in result

    def test_resolve_command_strips_extra_whitespace(self):
        from svp_config import resolve_command

        result = resolve_command(
            MINIMAL_VALID_TOOLCHAIN,
            "testing.run",
            {"env_name": "myproject", "target": "tests/", "flags": ""},
        )
        # Should not have multiple consecutive spaces
        assert "  " not in result
        # Should not have leading/trailing whitespace
        assert result == result.strip()

    def test_resolve_command_raises_on_unresolved_placeholder(self):
        from svp_config import resolve_command

        with pytest.raises(ValueError, match="[Uu]nresolved"):
            resolve_command(
                MINIMAL_VALID_TOOLCHAIN,
                "environment.create",
                {},  # Missing required params
            )


class TestResolveRunPrefix:
    def test_resolve_run_prefix_substitutes_env_name(self):
        from svp_config import resolve_run_prefix

        result = resolve_run_prefix(MINIMAL_VALID_TOOLCHAIN, "myproject")
        assert "myproject" in result
        assert "{env_name}" not in result

    def test_resolve_run_prefix_returns_string(self):
        from svp_config import resolve_run_prefix

        result = resolve_run_prefix(MINIMAL_VALID_TOOLCHAIN, "test_env")
        assert isinstance(result, str)


class TestGetFrameworkPackages:
    def test_get_framework_packages_returns_list(self):
        from svp_config import get_framework_packages

        result = get_framework_packages(MINIMAL_VALID_TOOLCHAIN)
        assert isinstance(result, list)
        assert "pytest" in result
        assert "pytest-cov" in result


class TestGetQualityPackages:
    def test_get_quality_packages_returns_list(self):
        from svp_config import get_quality_packages

        result = get_quality_packages(MINIMAL_VALID_TOOLCHAIN)
        assert isinstance(result, list)
        assert "ruff" in result
        assert "mypy" in result


class TestGetCollectionErrorIndicators:
    def test_get_collection_error_indicators_returns_list(self):
        from svp_config import get_collection_error_indicators

        result = get_collection_error_indicators(MINIMAL_VALID_TOOLCHAIN)
        assert isinstance(result, list)
        assert "ERROR collecting" in result


class TestGetGateOperations:
    def test_get_gate_operations_returns_operations_for_gate_a(self):
        from svp_config import get_gate_operations

        result = get_gate_operations(MINIMAL_VALID_TOOLCHAIN, "gate_a")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_gate_operations_returns_operations_for_gate_b(self):
        from svp_config import get_gate_operations

        result = get_gate_operations(MINIMAL_VALID_TOOLCHAIN, "gate_b")
        assert isinstance(result, list)
        assert len(result) == 2


class TestValidatePythonVersion:
    def test_validate_python_version_satisfied(self):
        from svp_config import validate_python_version

        assert validate_python_version("3.11", ">=3.11") is True

    def test_validate_python_version_not_satisfied(self):
        from svp_config import validate_python_version

        assert validate_python_version("3.10", ">=3.11") is False

    def test_validate_python_version_exact_match(self):
        from svp_config import validate_python_version

        assert validate_python_version("3.12", ">=3.11") is True


# ---------------------------------------------------------------------------
# Section 4: Shared Utilities
# ---------------------------------------------------------------------------


class TestDeriveEnvName:
    def test_derive_env_name_lowercase(self):
        from svp_config import derive_env_name

        assert derive_env_name("MyProject") == "myproject"

    def test_derive_env_name_replaces_spaces_with_underscores(self):
        from svp_config import derive_env_name

        assert derive_env_name("My Project") == "my_project"

    def test_derive_env_name_replaces_hyphens_with_underscores(self):
        from svp_config import derive_env_name

        assert derive_env_name("my-project") == "my_project"

    def test_derive_env_name_combined_transformations(self):
        from svp_config import derive_env_name

        assert derive_env_name("My Cool-Project") == "my_cool_project"

    def test_derive_env_name_already_canonical(self):
        from svp_config import derive_env_name

        assert derive_env_name("simple") == "simple"

    def test_derive_env_name_empty_string(self):
        from svp_config import derive_env_name

        assert derive_env_name("") == ""


# ---------------------------------------------------------------------------
# Error Condition Tests
# ---------------------------------------------------------------------------


class TestErrorConditions:
    def test_load_config_malformed_json(self, tmp_path):
        from svp_config import load_config

        (tmp_path / "svp_config.json").write_text("not valid json{{{")
        with pytest.raises(json.JSONDecodeError):
            load_config(tmp_path)

    def test_load_profile_missing_raises_runtime_error_with_path(self, tmp_path):
        from svp_config import load_profile

        with pytest.raises(RuntimeError, match=str(tmp_path)):
            load_profile(tmp_path)

    def test_load_toolchain_missing_raises_runtime_error_with_path(self, tmp_path):
        from svp_config import load_toolchain

        with pytest.raises(RuntimeError, match=str(tmp_path)):
            load_toolchain(tmp_path)

    def test_resolve_command_unresolved_placeholder_message(self):
        from svp_config import resolve_command

        with pytest.raises(ValueError, match="placeholder"):
            resolve_command(
                MINIMAL_VALID_TOOLCHAIN,
                "environment.create",
                {},
            )

"""Tests for Unit 3: Profile Schema.

Synthetic Data Assumptions
--------------------------
- A "valid minimal profile" is a dict that contains the top-level keys specified in
  the blueprint contracts: archetype, language, delivery, quality, testing, readme,
  license, vcs, pipeline.  Delivery and quality are language-keyed dicts.
- The LANGUAGE_REGISTRY from Unit 2 (src/unit_2/stub.py) is used as the authoritative
  registry for validation tests.  We import it directly for use as the
  language_registry argument.
- A "flat" (SVP 2.1-style) delivery/quality section is one where the dict is NOT
  keyed by language name but instead contains delivery/quality fields directly
  (e.g., {"source_layout": "conventional", ...} instead of
  {"python": {"source_layout": "conventional", ...}}).
- Mixed archetype profiles require both languages in delivery and quality sections,
  language.secondary present, and language.communication populated.
- Valid archetypes are: "python_project", "r_project", "claude_code_plugin", "mixed",
  "svp_language_extension", "svp_architectural".
- For "svp_language_extension" and "svp_architectural" archetypes, load_profile sets
  is_svp_build=True and self_build_scope accordingly.
- For get_delivery_config / get_quality_config, the deep-merge uses registry defaults
  as the base and profile overrides on top (profile values win over defaults).
- project_profile.json is the filename read by load_profile (from Unit 1's
  ARTIFACT_FILENAMES).
- tmp_path fixtures create real filesystem directories for load_profile tests.
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from language_registry import LANGUAGE_REGISTRY
from profile_schema import (
    DEFAULT_PROFILE,
    get_delivery_config,
    get_quality_config,
    load_profile,
    validate_profile,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_ARCHETYPES = {
    "python_project",
    "r_project",
    "claude_code_plugin",
    "mixed",
    "svp_language_extension",
    "svp_architectural",
}

REQUIRED_TOP_LEVEL_KEYS = {
    "archetype",
    "language",
    "delivery",
    "quality",
    "testing",
    "readme",
    "license",
    "vcs",
    "pipeline",
}


def _make_valid_python_profile() -> Dict[str, Any]:
    """Build a minimal valid python_project profile for testing."""
    return {
        "archetype": "python_project",
        "language": {
            "primary": "python",
            "components": [],
            "communication": {},
            "notebooks": None,
        },
        "delivery": {
            "python": {
                "environment_recommendation": "conda",
                "dependency_format": "environment.yml",
                "source_layout": "conventional",
                "entry_points": False,
            },
        },
        "quality": {
            "python": {
                "linter": "ruff",
                "formatter": "ruff",
                "type_checker": "mypy",
                "import_sorter": "ruff",
                "line_length": 88,
            },
        },
        "testing": {"readable_test_names": True},
        "readme": {},
        "license": {},
        "vcs": {},
        "pipeline": {},
    }


def _make_valid_r_profile() -> Dict[str, Any]:
    """Build a minimal valid r_project profile for testing."""
    return {
        "archetype": "r_project",
        "language": {
            "primary": "r",
            "components": [],
            "communication": {},
            "notebooks": None,
        },
        "delivery": {
            "r": {
                "environment_recommendation": "renv",
                "dependency_format": "renv.lock",
                "source_layout": "package",
                "entry_points": False,
            },
        },
        "quality": {
            "r": {
                "linter": "lintr",
                "formatter": "styler",
                "type_checker": "none",
                "line_length": 80,
            },
        },
        "testing": {},
        "readme": {},
        "license": {},
        "vcs": {},
        "pipeline": {},
    }


def _make_valid_mixed_profile() -> Dict[str, Any]:
    """Build a minimal valid mixed archetype profile."""
    return {
        "archetype": "mixed",
        "language": {
            "primary": "python",
            "secondary": "r",
            "components": [],
            "communication": {"python_r": {"library": "rpy2"}},
            "notebooks": None,
        },
        "delivery": {
            "python": {
                "environment_recommendation": "conda",
                "dependency_format": "environment.yml",
                "source_layout": "conventional",
                "entry_points": False,
            },
            "r": {
                "environment_recommendation": "conda",
                "dependency_format": "environment.yml",
                "source_layout": "package",
                "entry_points": False,
            },
        },
        "quality": {
            "python": {
                "linter": "ruff",
                "formatter": "ruff",
                "type_checker": "mypy",
                "import_sorter": "ruff",
                "line_length": 88,
            },
            "r": {
                "linter": "lintr",
                "formatter": "styler",
                "type_checker": "none",
                "line_length": 80,
            },
        },
        "testing": {},
        "readme": {},
        "license": {},
        "vcs": {},
        "pipeline": {},
    }


def _write_profile(tmp_path: Path, profile: Dict[str, Any]) -> None:
    """Write a profile dict to project_profile.json in tmp_path."""
    profile_path = tmp_path / "project_profile.json"
    profile_path.write_text(json.dumps(profile, indent=2))


# ===========================================================================
# DEFAULT_PROFILE tests
# ===========================================================================


class TestDefaultProfile:
    """Tests for the DEFAULT_PROFILE constant."""

    def test_default_profile_contains_all_required_top_level_keys(self):
        """DEFAULT_PROFILE must contain all required top-level keys."""
        for key in REQUIRED_TOP_LEVEL_KEYS:
            assert key in DEFAULT_PROFILE, (
                f"DEFAULT_PROFILE missing required top-level key: {key}"
            )

    def test_default_profile_archetype_is_python_project(self):
        """DEFAULT_PROFILE archetype default is 'python_project'."""
        assert DEFAULT_PROFILE["archetype"] == "python_project"

    def test_default_profile_language_primary_is_python(self):
        """DEFAULT_PROFILE language.primary defaults to 'python'."""
        assert DEFAULT_PROFILE["language"]["primary"] == "python"

    def test_default_profile_language_has_components_empty_list(self):
        """DEFAULT_PROFILE language.components defaults to empty list."""
        assert DEFAULT_PROFILE["language"]["components"] == []

    def test_default_profile_language_has_communication_empty_dict(self):
        """DEFAULT_PROFILE language.communication defaults to empty dict."""
        assert DEFAULT_PROFILE["language"]["communication"] == {}

    def test_default_profile_language_has_notebooks_null(self):
        """DEFAULT_PROFILE language.notebooks defaults to None."""
        assert DEFAULT_PROFILE["language"]["notebooks"] is None

    def test_default_profile_delivery_is_language_keyed(self):
        """DEFAULT_PROFILE delivery must be language-keyed with 'python' key."""
        assert "python" in DEFAULT_PROFILE["delivery"]
        assert isinstance(DEFAULT_PROFILE["delivery"]["python"], dict)

    def test_default_profile_delivery_python_matches_registry_defaults(self):
        """DEFAULT_PROFILE delivery.python matches LANGUAGE_REGISTRY python default_delivery."""
        registry_defaults = LANGUAGE_REGISTRY["python"]["default_delivery"]
        profile_delivery = DEFAULT_PROFILE["delivery"]["python"]
        for key, value in registry_defaults.items():
            assert key in profile_delivery, (
                f"delivery.python missing key from registry: {key}"
            )
            assert profile_delivery[key] == value, (
                f"delivery.python[{key}] = {profile_delivery[key]}, "
                f"expected {value} from registry"
            )

    def test_default_profile_quality_is_language_keyed(self):
        """DEFAULT_PROFILE quality must be language-keyed with 'python' key."""
        assert "python" in DEFAULT_PROFILE["quality"]
        assert isinstance(DEFAULT_PROFILE["quality"]["python"], dict)

    def test_default_profile_quality_python_matches_registry_defaults(self):
        """DEFAULT_PROFILE quality.python matches LANGUAGE_REGISTRY python default_quality."""
        registry_defaults = LANGUAGE_REGISTRY["python"]["default_quality"]
        profile_quality = DEFAULT_PROFILE["quality"]["python"]
        for key, value in registry_defaults.items():
            assert key in profile_quality, (
                f"quality.python missing key from registry: {key}"
            )
            assert profile_quality[key] == value, (
                f"quality.python[{key}] = {profile_quality[key]}, "
                f"expected {value} from registry"
            )

    def test_default_profile_is_a_dict(self):
        """DEFAULT_PROFILE must be a dict."""
        assert isinstance(DEFAULT_PROFILE, dict)

    def test_default_profile_no_unexpected_archetype(self):
        """DEFAULT_PROFILE archetype must be one of the valid archetypes."""
        assert DEFAULT_PROFILE["archetype"] in VALID_ARCHETYPES


# ===========================================================================
# load_profile tests
# ===========================================================================


class TestLoadProfile:
    """Tests for the load_profile function."""

    def test_load_profile_reads_project_profile_json(self, tmp_path):
        """load_profile reads project_profile.json from project_root."""
        profile_data = _make_valid_python_profile()
        _write_profile(tmp_path, profile_data)
        result = load_profile(tmp_path)
        assert isinstance(result, dict)

    def test_load_profile_raises_file_not_found_error_when_file_absent(self, tmp_path):
        """load_profile raises FileNotFoundError if project_profile.json is absent."""
        with pytest.raises(FileNotFoundError):
            load_profile(tmp_path)

    def test_load_profile_deep_merges_with_default_profile(self, tmp_path):
        """load_profile deep-merges user profile with DEFAULT_PROFILE; defaults fill gaps."""
        # Write a minimal profile that omits some top-level keys
        partial_profile = {
            "archetype": "python_project",
            "language": {"primary": "python"},
        }
        _write_profile(tmp_path, partial_profile)
        result = load_profile(tmp_path)
        # Keys from DEFAULT_PROFILE should be present
        for key in REQUIRED_TOP_LEVEL_KEYS:
            assert key in result, f"Merged profile missing default key: {key}"

    def test_load_profile_user_values_override_defaults(self, tmp_path):
        """load_profile user profile values override DEFAULT_PROFILE values."""
        profile_data = _make_valid_python_profile()
        profile_data["archetype"] = "r_project"
        profile_data["language"]["primary"] = "r"
        profile_data["delivery"] = {
            "r": {
                "environment_recommendation": "renv",
                "dependency_format": "renv.lock",
                "source_layout": "package",
                "entry_points": False,
            }
        }
        _write_profile(tmp_path, profile_data)
        result = load_profile(tmp_path)
        assert result["archetype"] == "r_project"
        assert result["language"]["primary"] == "r"

    def test_load_profile_svp21_migration_flat_delivery_to_language_keyed(
        self, tmp_path
    ):
        """load_profile migrates flat delivery dict to language-keyed format."""
        # SVP 2.1 style: delivery is flat, not language-keyed
        flat_profile = {
            "archetype": "python_project",
            "language": {"primary": "python"},
            "delivery": {
                "environment_recommendation": "conda",
                "dependency_format": "environment.yml",
                "source_layout": "conventional",
                "entry_points": False,
            },
        }
        _write_profile(tmp_path, flat_profile)
        result = load_profile(tmp_path)
        # After migration, delivery should be language-keyed
        assert "python" in result["delivery"]
        assert isinstance(result["delivery"]["python"], dict)
        assert result["delivery"]["python"]["source_layout"] == "conventional"

    def test_load_profile_svp21_migration_flat_quality_to_language_keyed(
        self, tmp_path
    ):
        """load_profile migrates flat quality dict to language-keyed format."""
        flat_profile = {
            "archetype": "python_project",
            "language": {"primary": "python"},
            "quality": {
                "linter": "ruff",
                "formatter": "ruff",
                "type_checker": "mypy",
                "import_sorter": "ruff",
                "line_length": 88,
            },
        }
        _write_profile(tmp_path, flat_profile)
        result = load_profile(tmp_path)
        # After migration, quality should be language-keyed
        assert "python" in result["quality"]
        assert isinstance(result["quality"]["python"], dict)
        assert result["quality"]["python"]["linter"] == "ruff"

    def test_load_profile_svp21_migration_uses_primary_language_as_key(self, tmp_path):
        """SVP 2.1 migration wraps flat sections under language.primary key."""
        flat_profile = {
            "archetype": "r_project",
            "language": {"primary": "r"},
            "delivery": {
                "environment_recommendation": "renv",
                "dependency_format": "renv.lock",
                "source_layout": "package",
                "entry_points": False,
            },
            "quality": {
                "linter": "lintr",
                "formatter": "styler",
                "type_checker": "none",
                "line_length": 80,
            },
        }
        _write_profile(tmp_path, flat_profile)
        result = load_profile(tmp_path)
        assert "r" in result["delivery"]
        assert "r" in result["quality"]

    def test_load_profile_already_language_keyed_delivery_is_unchanged(self, tmp_path):
        """load_profile preserves already language-keyed delivery sections."""
        profile_data = _make_valid_python_profile()
        _write_profile(tmp_path, profile_data)
        result = load_profile(tmp_path)
        assert "python" in result["delivery"]
        assert result["delivery"]["python"]["source_layout"] == "conventional"

    def test_load_profile_svp_language_extension_sets_is_svp_build(self, tmp_path):
        """load_profile sets is_svp_build=True for svp_language_extension archetype."""
        profile_data = _make_valid_python_profile()
        profile_data["archetype"] = "svp_language_extension"
        _write_profile(tmp_path, profile_data)
        result = load_profile(tmp_path)
        assert result.get("is_svp_build") is True

    def test_load_profile_svp_architectural_sets_is_svp_build(self, tmp_path):
        """load_profile sets is_svp_build=True for svp_architectural archetype."""
        profile_data = _make_valid_python_profile()
        profile_data["archetype"] = "svp_architectural"
        _write_profile(tmp_path, profile_data)
        result = load_profile(tmp_path)
        assert result.get("is_svp_build") is True

    def test_load_profile_svp_language_extension_sets_self_build_scope(self, tmp_path):
        """load_profile sets self_build_scope for svp_language_extension archetype."""
        profile_data = _make_valid_python_profile()
        profile_data["archetype"] = "svp_language_extension"
        _write_profile(tmp_path, profile_data)
        result = load_profile(tmp_path)
        assert "self_build_scope" in result

    def test_load_profile_svp_architectural_sets_self_build_scope(self, tmp_path):
        """load_profile sets self_build_scope for svp_architectural archetype."""
        profile_data = _make_valid_python_profile()
        profile_data["archetype"] = "svp_architectural"
        _write_profile(tmp_path, profile_data)
        result = load_profile(tmp_path)
        assert "self_build_scope" in result

    def test_load_profile_non_svp_archetype_no_is_svp_build(self, tmp_path):
        """load_profile does not set is_svp_build for regular archetypes."""
        profile_data = _make_valid_python_profile()
        _write_profile(tmp_path, profile_data)
        result = load_profile(tmp_path)
        # is_svp_build should be absent or False
        assert not result.get("is_svp_build", False)

    def test_load_profile_is_svp_build_derived_from_archetype_not_independent(
        self, tmp_path
    ):
        """is_svp_build is derived from archetype, never set independently.

        If a user profile has is_svp_build=True but archetype is python_project,
        the derived value should reflect the archetype, not the user-set field.
        """
        profile_data = _make_valid_python_profile()
        profile_data["is_svp_build"] = True  # user tries to set it independently
        _write_profile(tmp_path, profile_data)
        result = load_profile(tmp_path)
        # For python_project, is_svp_build should not be True
        assert not result.get("is_svp_build", False)

    def test_load_profile_returns_dict(self, tmp_path):
        """load_profile returns a dict."""
        profile_data = _make_valid_python_profile()
        _write_profile(tmp_path, profile_data)
        result = load_profile(tmp_path)
        assert isinstance(result, dict)

    def test_load_profile_deep_merge_preserves_nested_defaults(self, tmp_path):
        """Deep merge fills in missing nested keys from defaults."""
        # Only provide archetype, let defaults fill in language, delivery, etc.
        minimal = {"archetype": "python_project"}
        _write_profile(tmp_path, minimal)
        result = load_profile(tmp_path)
        assert result["language"]["primary"] == "python"
        assert result["language"]["components"] == []


# ===========================================================================
# validate_profile tests
# ===========================================================================


class TestValidateProfile:
    """Tests for the validate_profile function."""

    def test_validate_profile_returns_empty_list_for_valid_python_profile(self):
        """validate_profile returns empty list for a valid python_project profile."""
        profile = _make_valid_python_profile()
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

    def test_validate_profile_returns_empty_list_for_valid_r_profile(self):
        """validate_profile returns empty list for a valid r_project profile."""
        profile = _make_valid_r_profile()
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

    def test_validate_profile_returns_empty_list_for_valid_mixed_profile(self):
        """validate_profile returns empty list for a valid mixed archetype profile."""
        profile = _make_valid_mixed_profile()
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

    def test_validate_profile_returns_list_type(self):
        """validate_profile always returns a list."""
        profile = _make_valid_python_profile()
        result = validate_profile(profile, LANGUAGE_REGISTRY)
        assert isinstance(result, list)

    def test_validate_profile_invalid_archetype_returns_error(self):
        """validate_profile returns error for an invalid archetype value."""
        profile = _make_valid_python_profile()
        profile["archetype"] = "nonexistent_archetype"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert len(errors) > 0
        assert any("archetype" in e.lower() for e in errors)

    def test_validate_profile_invalid_primary_language_returns_error(self):
        """validate_profile returns error when language.primary is not in registry."""
        profile = _make_valid_python_profile()
        profile["language"]["primary"] = "cobol"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert len(errors) > 0

    def test_validate_profile_invalid_linter_returns_error(self):
        """validate_profile returns error when linter not in registry valid_linters."""
        profile = _make_valid_python_profile()
        profile["quality"]["python"]["linter"] = "nonexistent_linter"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert len(errors) > 0

    def test_validate_profile_invalid_formatter_returns_error(self):
        """validate_profile returns error when formatter not in registry valid_formatters."""
        profile = _make_valid_python_profile()
        profile["quality"]["python"]["formatter"] = "nonexistent_formatter"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert len(errors) > 0

    def test_validate_profile_invalid_type_checker_returns_error(self):
        """validate_profile returns error when type_checker not in valid_type_checkers."""
        profile = _make_valid_python_profile()
        profile["quality"]["python"]["type_checker"] = "nonexistent_checker"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert len(errors) > 0

    def test_validate_profile_valid_linter_ruff_accepted(self):
        """validate_profile accepts 'ruff' as a valid Python linter."""
        profile = _make_valid_python_profile()
        profile["quality"]["python"]["linter"] = "ruff"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

    def test_validate_profile_valid_linter_flake8_accepted(self):
        """validate_profile accepts 'flake8' as a valid Python linter."""
        profile = _make_valid_python_profile()
        profile["quality"]["python"]["linter"] = "flake8"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

    def test_validate_profile_valid_linter_pylint_accepted(self):
        """validate_profile accepts 'pylint' as a valid Python linter."""
        profile = _make_valid_python_profile()
        profile["quality"]["python"]["linter"] = "pylint"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

    def test_validate_profile_valid_linter_none_accepted(self):
        """validate_profile accepts 'none' as a valid Python linter."""
        profile = _make_valid_python_profile()
        profile["quality"]["python"]["linter"] = "none"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

    def test_validate_profile_valid_formatter_black_accepted(self):
        """validate_profile accepts 'black' as a valid Python formatter."""
        profile = _make_valid_python_profile()
        profile["quality"]["python"]["formatter"] = "black"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

    def test_validate_profile_valid_type_checker_pyright_accepted(self):
        """validate_profile accepts 'pyright' as a valid Python type_checker."""
        profile = _make_valid_python_profile()
        profile["quality"]["python"]["type_checker"] = "pyright"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

    def test_validate_profile_r_quality_invalid_linter_returns_error(self):
        """validate_profile returns error for invalid R linter."""
        profile = _make_valid_r_profile()
        profile["quality"]["r"]["linter"] = "ruff"  # ruff is not valid for R
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert len(errors) > 0

    def test_validate_profile_r_quality_valid_linter_accepted(self):
        """validate_profile accepts 'lintr' as a valid R linter."""
        profile = _make_valid_r_profile()
        profile["quality"]["r"]["linter"] = "lintr"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

    def test_validate_profile_mixed_archetype_missing_secondary_delivery_returns_error(
        self,
    ):
        """Mixed archetype must have both languages in delivery section."""
        profile = _make_valid_mixed_profile()
        del profile["delivery"]["r"]  # Remove secondary language from delivery
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert len(errors) > 0

    def test_validate_profile_mixed_archetype_missing_secondary_quality_returns_error(
        self,
    ):
        """Mixed archetype must have both languages in quality section."""
        profile = _make_valid_mixed_profile()
        del profile["quality"]["r"]  # Remove secondary language from quality
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert len(errors) > 0

    def test_validate_profile_mixed_archetype_forces_conda_environment(self):
        """Mixed archetype: both environment_recommendation must be 'conda'."""
        profile = _make_valid_mixed_profile()
        profile["delivery"]["r"]["environment_recommendation"] = "renv"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert len(errors) > 0

    def test_validate_profile_mixed_archetype_forces_environment_yml_format(self):
        """Mixed archetype: both dependency_format must be 'environment.yml'."""
        profile = _make_valid_mixed_profile()
        profile["delivery"]["r"]["dependency_format"] = "renv.lock"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert len(errors) > 0

    def test_validate_profile_mixed_archetype_both_languages_conda_passes(self):
        """Mixed archetype passes when both languages use conda/environment.yml."""
        profile = _make_valid_mixed_profile()
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

    def test_validate_profile_mixed_archetype_primary_not_conda_returns_error(self):
        """Mixed archetype: primary language environment_recommendation not conda is error."""
        profile = _make_valid_mixed_profile()
        profile["delivery"]["python"]["environment_recommendation"] = "venv"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert len(errors) > 0

    def test_validate_profile_mixed_archetype_primary_not_env_yml_returns_error(self):
        """Mixed archetype: primary language dependency_format not environment.yml is error."""
        profile = _make_valid_mixed_profile()
        profile["delivery"]["python"]["dependency_format"] = "requirements.txt"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert len(errors) > 0

    def test_validate_profile_component_language_must_have_host(self):
        """A component language in delivery/quality must have a compatible host."""
        profile = _make_valid_python_profile()
        # Add stan to delivery without a host language (stan is component-only)
        profile["delivery"]["stan"] = {}
        profile["quality"]["stan"] = {}
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        # Should detect that stan is component-only and needs a host
        assert len(errors) > 0

    def test_validate_profile_errors_are_strings(self):
        """All validation errors are strings."""
        profile = _make_valid_python_profile()
        profile["archetype"] = "invalid"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        for error in errors:
            assert isinstance(error, str)

    def test_validate_profile_multiple_errors_accumulated(self):
        """validate_profile can return multiple error strings at once."""
        profile = _make_valid_python_profile()
        profile["archetype"] = "invalid_archetype"
        profile["language"]["primary"] = "cobol"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert len(errors) >= 2

    def test_validate_profile_each_valid_archetype_accepted(self):
        """All valid archetypes are accepted by validate_profile (non-mixed, non-svp)."""
        for archetype in ["python_project", "r_project", "claude_code_plugin"]:
            if archetype == "r_project":
                profile = _make_valid_r_profile()
            else:
                profile = _make_valid_python_profile()
            profile["archetype"] = archetype
            errors = validate_profile(profile, LANGUAGE_REGISTRY)
            # Filter out errors that are not about archetype
            archetype_errors = [e for e in errors if "archetype" in e.lower()]
            assert archetype_errors == [], (
                f"Archetype '{archetype}' should be accepted but got: {archetype_errors}"
            )

    def test_validate_profile_validates_delivery_tool_choices_against_registry(self):
        """validate_profile checks delivery source_layout against valid_source_layouts."""
        profile = _make_valid_python_profile()
        profile["delivery"]["python"]["source_layout"] = "nonexistent_layout"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert len(errors) > 0

    def test_validate_profile_valid_source_layout_conventional_accepted(self):
        """validate_profile accepts 'conventional' as valid Python source_layout."""
        profile = _make_valid_python_profile()
        profile["delivery"]["python"]["source_layout"] = "conventional"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

    def test_validate_profile_valid_source_layout_flat_accepted(self):
        """validate_profile accepts 'flat' as valid Python source_layout."""
        profile = _make_valid_python_profile()
        profile["delivery"]["python"]["source_layout"] = "flat"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

    def test_validate_profile_valid_source_layout_svp_native_accepted(self):
        """validate_profile accepts 'svp_native' as valid Python source_layout."""
        profile = _make_valid_python_profile()
        profile["delivery"]["python"]["source_layout"] = "svp_native"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

    def test_validate_profile_r_valid_source_layout_package_accepted(self):
        """validate_profile accepts 'package' as valid R source_layout."""
        profile = _make_valid_r_profile()
        profile["delivery"]["r"]["source_layout"] = "package"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert errors == []

    def test_validate_profile_r_invalid_source_layout_returns_error(self):
        """validate_profile returns error for invalid R source_layout."""
        profile = _make_valid_r_profile()
        profile["delivery"]["r"]["source_layout"] = "conventional"
        errors = validate_profile(profile, LANGUAGE_REGISTRY)
        assert len(errors) > 0


# ===========================================================================
# get_delivery_config tests
# ===========================================================================


class TestGetDeliveryConfig:
    """Tests for the get_delivery_config function."""

    def test_get_delivery_config_returns_dict(self):
        """get_delivery_config returns a dict."""
        profile = _make_valid_python_profile()
        result = get_delivery_config(profile, "python", LANGUAGE_REGISTRY)
        assert isinstance(result, dict)

    def test_get_delivery_config_returns_python_delivery_section(self):
        """get_delivery_config returns the python delivery section from profile."""
        profile = _make_valid_python_profile()
        result = get_delivery_config(profile, "python", LANGUAGE_REGISTRY)
        assert result["source_layout"] == "conventional"
        assert result["environment_recommendation"] == "conda"

    def test_get_delivery_config_returns_r_delivery_section(self):
        """get_delivery_config returns the R delivery section from profile."""
        profile = _make_valid_r_profile()
        result = get_delivery_config(profile, "r", LANGUAGE_REGISTRY)
        assert result["source_layout"] == "package"
        assert result["environment_recommendation"] == "renv"

    def test_get_delivery_config_merges_with_registry_defaults(self):
        """get_delivery_config deep-merges profile delivery with registry defaults."""
        profile = _make_valid_python_profile()
        # Remove a field from profile delivery to test that registry default fills it
        del profile["delivery"]["python"]["entry_points"]
        result = get_delivery_config(profile, "python", LANGUAGE_REGISTRY)
        # entry_points should come from registry default
        assert "entry_points" in result

    def test_get_delivery_config_profile_values_override_registry_defaults(self):
        """get_delivery_config profile values win over registry defaults."""
        profile = _make_valid_python_profile()
        profile["delivery"]["python"]["source_layout"] = "flat"
        result = get_delivery_config(profile, "python", LANGUAGE_REGISTRY)
        assert result["source_layout"] == "flat"

    def test_get_delivery_config_raises_key_error_for_unknown_language(self):
        """get_delivery_config raises KeyError if language not in registry."""
        profile = _make_valid_python_profile()
        with pytest.raises(KeyError):
            get_delivery_config(profile, "cobol", LANGUAGE_REGISTRY)

    def test_get_delivery_config_all_registry_default_fields_present(self):
        """get_delivery_config result contains all fields from registry default_delivery."""
        profile = _make_valid_python_profile()
        result = get_delivery_config(profile, "python", LANGUAGE_REGISTRY)
        registry_defaults = LANGUAGE_REGISTRY["python"]["default_delivery"]
        for key in registry_defaults:
            assert key in result, (
                f"get_delivery_config result missing registry default key: {key}"
            )

    def test_get_delivery_config_empty_profile_delivery_gets_all_defaults(self):
        """get_delivery_config fills all fields from defaults when profile section is empty."""
        profile = _make_valid_python_profile()
        profile["delivery"]["python"] = {}
        result = get_delivery_config(profile, "python", LANGUAGE_REGISTRY)
        registry_defaults = LANGUAGE_REGISTRY["python"]["default_delivery"]
        for key, value in registry_defaults.items():
            assert result[key] == value

    def test_get_delivery_config_mixed_profile_python_language(self):
        """get_delivery_config works for python in a mixed profile."""
        profile = _make_valid_mixed_profile()
        result = get_delivery_config(profile, "python", LANGUAGE_REGISTRY)
        assert result["environment_recommendation"] == "conda"

    def test_get_delivery_config_mixed_profile_r_language(self):
        """get_delivery_config works for R in a mixed profile."""
        profile = _make_valid_mixed_profile()
        result = get_delivery_config(profile, "r", LANGUAGE_REGISTRY)
        assert isinstance(result, dict)
        assert "source_layout" in result


# ===========================================================================
# get_quality_config tests
# ===========================================================================


class TestGetQualityConfig:
    """Tests for the get_quality_config function."""

    def test_get_quality_config_returns_dict(self):
        """get_quality_config returns a dict."""
        profile = _make_valid_python_profile()
        result = get_quality_config(profile, "python", LANGUAGE_REGISTRY)
        assert isinstance(result, dict)

    def test_get_quality_config_returns_python_quality_section(self):
        """get_quality_config returns the python quality section from profile."""
        profile = _make_valid_python_profile()
        result = get_quality_config(profile, "python", LANGUAGE_REGISTRY)
        assert result["linter"] == "ruff"
        assert result["formatter"] == "ruff"
        assert result["type_checker"] == "mypy"

    def test_get_quality_config_returns_r_quality_section(self):
        """get_quality_config returns the R quality section from profile."""
        profile = _make_valid_r_profile()
        result = get_quality_config(profile, "r", LANGUAGE_REGISTRY)
        assert result["linter"] == "lintr"
        assert result["formatter"] == "styler"

    def test_get_quality_config_merges_with_registry_defaults(self):
        """get_quality_config deep-merges profile quality with registry defaults."""
        profile = _make_valid_python_profile()
        # Remove a field to verify registry default fills it
        del profile["quality"]["python"]["line_length"]
        result = get_quality_config(profile, "python", LANGUAGE_REGISTRY)
        assert "line_length" in result
        # Should get default from registry
        assert (
            result["line_length"]
            == LANGUAGE_REGISTRY["python"]["default_quality"]["line_length"]
        )

    def test_get_quality_config_profile_values_override_registry_defaults(self):
        """get_quality_config profile values win over registry defaults."""
        profile = _make_valid_python_profile()
        profile["quality"]["python"]["line_length"] = 120
        result = get_quality_config(profile, "python", LANGUAGE_REGISTRY)
        assert result["line_length"] == 120

    def test_get_quality_config_raises_key_error_for_unknown_language(self):
        """get_quality_config raises KeyError if language not in registry."""
        profile = _make_valid_python_profile()
        with pytest.raises(KeyError):
            get_quality_config(profile, "cobol", LANGUAGE_REGISTRY)

    def test_get_quality_config_all_registry_default_fields_present(self):
        """get_quality_config result contains all fields from registry default_quality."""
        profile = _make_valid_python_profile()
        result = get_quality_config(profile, "python", LANGUAGE_REGISTRY)
        registry_defaults = LANGUAGE_REGISTRY["python"]["default_quality"]
        for key in registry_defaults:
            assert key in result, (
                f"get_quality_config result missing registry default key: {key}"
            )

    def test_get_quality_config_empty_profile_quality_gets_all_defaults(self):
        """get_quality_config fills all fields from defaults when profile section is empty."""
        profile = _make_valid_python_profile()
        profile["quality"]["python"] = {}
        result = get_quality_config(profile, "python", LANGUAGE_REGISTRY)
        registry_defaults = LANGUAGE_REGISTRY["python"]["default_quality"]
        for key, value in registry_defaults.items():
            assert result[key] == value

    def test_get_quality_config_mixed_profile_python_language(self):
        """get_quality_config works for python in a mixed profile."""
        profile = _make_valid_mixed_profile()
        result = get_quality_config(profile, "python", LANGUAGE_REGISTRY)
        assert result["linter"] == "ruff"

    def test_get_quality_config_mixed_profile_r_language(self):
        """get_quality_config works for R in a mixed profile."""
        profile = _make_valid_mixed_profile()
        result = get_quality_config(profile, "r", LANGUAGE_REGISTRY)
        assert result["linter"] == "lintr"

    def test_get_quality_config_python_import_sorter_included(self):
        """get_quality_config for python includes import_sorter field."""
        profile = _make_valid_python_profile()
        result = get_quality_config(profile, "python", LANGUAGE_REGISTRY)
        assert "import_sorter" in result

    def test_get_quality_config_profile_override_linter_to_flake8(self):
        """get_quality_config returns overridden linter value from profile."""
        profile = _make_valid_python_profile()
        profile["quality"]["python"]["linter"] = "flake8"
        result = get_quality_config(profile, "python", LANGUAGE_REGISTRY)
        assert result["linter"] == "flake8"


# ===========================================================================
# Integration / cross-function tests
# ===========================================================================


class TestProfileIntegration:
    """Integration tests verifying cross-function behavior."""

    def test_load_then_validate_default_profile_is_valid(self, tmp_path):
        """Loading a profile that matches DEFAULT_PROFILE should validate clean."""
        # Write a profile that matches defaults
        profile_data = _make_valid_python_profile()
        _write_profile(tmp_path, profile_data)
        loaded = load_profile(tmp_path)
        errors = validate_profile(loaded, LANGUAGE_REGISTRY)
        assert errors == []

    def test_load_then_get_delivery_config_round_trip(self, tmp_path):
        """Load a profile then get_delivery_config returns expected values."""
        profile_data = _make_valid_python_profile()
        _write_profile(tmp_path, profile_data)
        loaded = load_profile(tmp_path)
        delivery = get_delivery_config(loaded, "python", LANGUAGE_REGISTRY)
        assert delivery["source_layout"] == "conventional"
        assert delivery["environment_recommendation"] == "conda"

    def test_load_then_get_quality_config_round_trip(self, tmp_path):
        """Load a profile then get_quality_config returns expected values."""
        profile_data = _make_valid_python_profile()
        _write_profile(tmp_path, profile_data)
        loaded = load_profile(tmp_path)
        quality = get_quality_config(loaded, "python", LANGUAGE_REGISTRY)
        assert quality["linter"] == "ruff"
        assert quality["formatter"] == "ruff"

    def test_svp21_migrated_profile_validates_clean(self, tmp_path):
        """An SVP 2.1 flat profile, after load_profile migration, validates clean."""
        flat_profile = {
            "archetype": "python_project",
            "language": {"primary": "python"},
            "delivery": {
                "environment_recommendation": "conda",
                "dependency_format": "environment.yml",
                "source_layout": "conventional",
                "entry_points": False,
            },
            "quality": {
                "linter": "ruff",
                "formatter": "ruff",
                "type_checker": "mypy",
                "import_sorter": "ruff",
                "line_length": 88,
            },
        }
        _write_profile(tmp_path, flat_profile)
        loaded = load_profile(tmp_path)
        errors = validate_profile(loaded, LANGUAGE_REGISTRY)
        assert errors == []

    def test_svp21_migrated_profile_delivery_config_accessible(self, tmp_path):
        """After SVP 2.1 migration, get_delivery_config can access the language-keyed section."""
        flat_profile = {
            "archetype": "python_project",
            "language": {"primary": "python"},
            "delivery": {
                "environment_recommendation": "conda",
                "dependency_format": "environment.yml",
                "source_layout": "conventional",
                "entry_points": False,
            },
        }
        _write_profile(tmp_path, flat_profile)
        loaded = load_profile(tmp_path)
        delivery = get_delivery_config(loaded, "python", LANGUAGE_REGISTRY)
        assert delivery["source_layout"] == "conventional"

    def test_empty_profile_loads_with_all_defaults(self, tmp_path):
        """An empty JSON object loads successfully with all defaults."""
        _write_profile(tmp_path, {})
        loaded = load_profile(tmp_path)
        assert loaded["archetype"] == "python_project"
        assert loaded["language"]["primary"] == "python"
        for key in REQUIRED_TOP_LEVEL_KEYS:
            assert key in loaded

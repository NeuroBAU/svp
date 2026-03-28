"""
Tests for Unit 1: Core Configuration

Synthetic Data Assumptions:
- ARTIFACT_FILENAMES is expected to contain at least 15 specific keys as defined
  in the Tier 3 contracts. Each value is a relative path string from project root.
- DEFAULT_CONFIG contains 7 keys with specific default values as specified in
  the behavioral contracts.
- svp_config.json files used in tests are synthetic JSON with known key/value
  pairs to exercise deep-merge behavior, file I/O, and error conditions.
- Project root paths are constructed using pytest's tmp_path fixture to avoid
  filesystem side effects.
- Model precedence tests use synthetic config and profile dicts with known
  agent keys and model identifiers.
- derive_env_name tests use synthetic Path objects with known .name attributes.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

import pytest

from svp_config import (
    ARTIFACT_FILENAMES,
    DEFAULT_CONFIG,
    derive_env_name,
    get_blueprint_dir,
    get_model_for_agent,
    load_config,
    save_config,
)

# ---------------------------------------------------------------------------
# ARTIFACT_FILENAMES constant tests
# ---------------------------------------------------------------------------


class TestArtifactFilenames:
    """Tests for the ARTIFACT_FILENAMES module-level constant."""

    def test_artifact_filenames_is_a_dict(self):
        assert isinstance(ARTIFACT_FILENAMES, dict)

    def test_artifact_filenames_contains_pipeline_state_key(self):
        assert "pipeline_state" in ARTIFACT_FILENAMES

    def test_artifact_filenames_contains_project_profile_key(self):
        assert "project_profile" in ARTIFACT_FILENAMES

    def test_artifact_filenames_contains_toolchain_key(self):
        assert "toolchain" in ARTIFACT_FILENAMES

    def test_artifact_filenames_contains_stakeholder_spec_key(self):
        assert "stakeholder_spec" in ARTIFACT_FILENAMES

    def test_artifact_filenames_contains_blueprint_dir_key(self):
        assert "blueprint_dir" in ARTIFACT_FILENAMES

    def test_artifact_filenames_contains_blueprint_prose_key(self):
        assert "blueprint_prose" in ARTIFACT_FILENAMES

    def test_artifact_filenames_contains_blueprint_contracts_key(self):
        assert "blueprint_contracts" in ARTIFACT_FILENAMES

    def test_artifact_filenames_contains_build_log_key(self):
        assert "build_log" in ARTIFACT_FILENAMES

    def test_artifact_filenames_contains_task_prompt_key(self):
        assert "task_prompt" in ARTIFACT_FILENAMES

    def test_artifact_filenames_contains_gate_prompt_key(self):
        assert "gate_prompt" in ARTIFACT_FILENAMES

    def test_artifact_filenames_contains_last_status_key(self):
        assert "last_status" in ARTIFACT_FILENAMES

    def test_artifact_filenames_contains_svp_config_key(self):
        assert "svp_config" in ARTIFACT_FILENAMES

    def test_artifact_filenames_contains_assembly_map_key(self):
        assert "assembly_map" in ARTIFACT_FILENAMES

    def test_artifact_filenames_contains_triage_result_key(self):
        assert "triage_result" in ARTIFACT_FILENAMES

    def test_artifact_filenames_contains_oracle_run_ledger_key(self):
        assert "oracle_run_ledger" in ARTIFACT_FILENAMES

    def test_artifact_filenames_has_at_least_fifteen_entries(self):
        assert len(ARTIFACT_FILENAMES) >= 15

    def test_artifact_filenames_values_are_all_strings(self):
        for key, value in ARTIFACT_FILENAMES.items():
            assert isinstance(value, str), (
                f"Value for key '{key}' should be str, got {type(value)}"
            )

    def test_artifact_filenames_values_are_relative_paths(self):
        """Every value must be a relative path (not absolute)."""
        for key, value in ARTIFACT_FILENAMES.items():
            assert not os.path.isabs(value), (
                f"Value for key '{key}' should be relative, got absolute: {value}"
            )

    def test_artifact_filenames_keys_are_all_strings(self):
        for key in ARTIFACT_FILENAMES:
            assert isinstance(key, str), f"Key should be str, got {type(key)}: {key}"


# ---------------------------------------------------------------------------
# DEFAULT_CONFIG constant tests
# ---------------------------------------------------------------------------


class TestDefaultConfig:
    """Tests for the DEFAULT_CONFIG module-level constant."""

    def test_default_config_is_a_dict(self):
        assert isinstance(DEFAULT_CONFIG, dict)

    def test_default_config_contains_iteration_limit(self):
        assert "iteration_limit" in DEFAULT_CONFIG

    def test_default_config_iteration_limit_is_three(self):
        assert DEFAULT_CONFIG["iteration_limit"] == 3

    def test_default_config_iteration_limit_is_int(self):
        assert isinstance(DEFAULT_CONFIG["iteration_limit"], int)

    def test_default_config_contains_models(self):
        assert "models" in DEFAULT_CONFIG

    def test_default_config_models_is_dict(self):
        assert isinstance(DEFAULT_CONFIG["models"], dict)

    def test_default_config_models_has_default_key(self):
        assert "default" in DEFAULT_CONFIG["models"]

    def test_default_config_models_default_is_claude_opus_4_6(self):
        assert DEFAULT_CONFIG["models"]["default"] == "claude-opus-4-6"

    def test_default_config_contains_context_budget_override(self):
        assert "context_budget_override" in DEFAULT_CONFIG

    def test_default_config_context_budget_override_is_null(self):
        assert DEFAULT_CONFIG["context_budget_override"] is None

    def test_default_config_contains_context_budget_threshold(self):
        assert "context_budget_threshold" in DEFAULT_CONFIG

    def test_default_config_context_budget_threshold_is_65(self):
        assert DEFAULT_CONFIG["context_budget_threshold"] == 65

    def test_default_config_context_budget_threshold_is_int(self):
        assert isinstance(DEFAULT_CONFIG["context_budget_threshold"], int)

    def test_default_config_contains_compaction_character_threshold(self):
        assert "compaction_character_threshold" in DEFAULT_CONFIG

    def test_default_config_compaction_character_threshold_is_200(self):
        assert DEFAULT_CONFIG["compaction_character_threshold"] == 200

    def test_default_config_compaction_character_threshold_is_int(self):
        assert isinstance(DEFAULT_CONFIG["compaction_character_threshold"], int)

    def test_default_config_contains_auto_save(self):
        assert "auto_save" in DEFAULT_CONFIG

    def test_default_config_auto_save_is_true(self):
        assert DEFAULT_CONFIG["auto_save"] is True

    def test_default_config_auto_save_is_bool(self):
        assert isinstance(DEFAULT_CONFIG["auto_save"], bool)

    def test_default_config_contains_skip_permissions(self):
        assert "skip_permissions" in DEFAULT_CONFIG

    def test_default_config_skip_permissions_is_true(self):
        assert DEFAULT_CONFIG["skip_permissions"] is True

    def test_default_config_skip_permissions_is_bool(self):
        assert isinstance(DEFAULT_CONFIG["skip_permissions"], bool)

    def test_default_config_has_all_seven_keys(self):
        expected_keys = {
            "iteration_limit",
            "models",
            "context_budget_override",
            "context_budget_threshold",
            "compaction_character_threshold",
            "auto_save",
            "skip_permissions",
        }
        assert expected_keys.issubset(set(DEFAULT_CONFIG.keys()))


# ---------------------------------------------------------------------------
# load_config tests
# ---------------------------------------------------------------------------


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_returns_dict(self, tmp_path: Path):
        config_data = {"iteration_limit": 5}
        config_file = tmp_path / "svp_config.json"
        config_file.write_text(json.dumps(config_data))
        result = load_config(tmp_path)
        assert isinstance(result, dict)

    def test_load_config_reads_svp_config_json_from_project_root(self, tmp_path: Path):
        config_data = {"iteration_limit": 10}
        config_file = tmp_path / "svp_config.json"
        config_file.write_text(json.dumps(config_data))
        result = load_config(tmp_path)
        assert result["iteration_limit"] == 10

    def test_load_config_deep_merges_with_defaults(self, tmp_path: Path):
        """User values override defaults; missing keys get default values."""
        config_data = {"iteration_limit": 7}
        config_file = tmp_path / "svp_config.json"
        config_file.write_text(json.dumps(config_data))
        result = load_config(tmp_path)
        # User-specified value overrides default
        assert result["iteration_limit"] == 7
        # Default values fill in for missing keys
        assert result["auto_save"] is True
        assert result["skip_permissions"] is True
        assert result["context_budget_threshold"] == 65

    def test_load_config_user_overrides_nested_models(self, tmp_path: Path):
        """Deep merge should handle nested dicts like models."""
        config_data = {
            "models": {
                "default": "claude-sonnet-4-20250514",
                "test_agent": "claude-opus-4-6",
            }
        }
        config_file = tmp_path / "svp_config.json"
        config_file.write_text(json.dumps(config_data))
        result = load_config(tmp_path)
        assert result["models"]["default"] == "claude-sonnet-4-20250514"
        assert result["models"]["test_agent"] == "claude-opus-4-6"

    def test_load_config_preserves_all_default_keys_when_file_is_empty_object(
        self, tmp_path: Path
    ):
        config_file = tmp_path / "svp_config.json"
        config_file.write_text("{}")
        result = load_config(tmp_path)
        # All defaults should be present
        assert result["iteration_limit"] == 3
        assert result["models"]["default"] == "claude-opus-4-6"
        assert result["context_budget_override"] is None
        assert result["context_budget_threshold"] == 65
        assert result["compaction_character_threshold"] == 200
        assert result["auto_save"] is True
        assert result["skip_permissions"] is True

    def test_load_config_raises_file_not_found_error_when_file_absent(
        self, tmp_path: Path
    ):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path)

    def test_load_config_raises_file_not_found_for_nonexistent_directory(self):
        nonexistent = Path("/tmp/svp_test_nonexistent_dir_abc123xyz")
        with pytest.raises(FileNotFoundError):
            load_config(nonexistent)

    def test_load_config_returns_merged_dict_not_just_user_data(self, tmp_path: Path):
        """The returned dict must contain both user overrides and defaults."""
        config_data = {"auto_save": False}
        config_file = tmp_path / "svp_config.json"
        config_file.write_text(json.dumps(config_data))
        result = load_config(tmp_path)
        assert result["auto_save"] is False
        assert "iteration_limit" in result
        assert "models" in result

    def test_load_config_deep_merges_does_not_lose_default_models_default(
        self, tmp_path: Path
    ):
        """When user provides agent-specific model but no default, default model
        should still come from DEFAULT_CONFIG."""
        config_data = {"models": {"blueprint_agent": "claude-haiku-3"}}
        config_file = tmp_path / "svp_config.json"
        config_file.write_text(json.dumps(config_data))
        result = load_config(tmp_path)
        assert result["models"]["default"] == "claude-opus-4-6"
        assert result["models"]["blueprint_agent"] == "claude-haiku-3"


# ---------------------------------------------------------------------------
# save_config tests
# ---------------------------------------------------------------------------


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_config_creates_svp_config_json_file(self, tmp_path: Path):
        config = {"iteration_limit": 5, "auto_save": False}
        save_config(tmp_path, config)
        config_file = tmp_path / "svp_config.json"
        assert config_file.exists()

    def test_save_config_writes_valid_json(self, tmp_path: Path):
        config = {"iteration_limit": 5, "models": {"default": "claude-opus-4-6"}}
        save_config(tmp_path, config)
        config_file = tmp_path / "svp_config.json"
        loaded = json.loads(config_file.read_text())
        assert loaded == config

    def test_save_config_writes_formatted_json(self, tmp_path: Path):
        """The output should be formatted (indented), not a single-line dump."""
        config = {"iteration_limit": 5, "auto_save": True}
        save_config(tmp_path, config)
        config_file = tmp_path / "svp_config.json"
        content = config_file.read_text()
        # Formatted JSON should contain newlines (not a single line)
        assert "\n" in content

    def test_save_config_overwrites_existing_file(self, tmp_path: Path):
        config_file = tmp_path / "svp_config.json"
        config_file.write_text(json.dumps({"old_key": "old_value"}))
        new_config = {"new_key": "new_value"}
        save_config(tmp_path, new_config)
        loaded = json.loads(config_file.read_text())
        assert loaded == new_config
        assert "old_key" not in loaded

    def test_save_config_returns_none(self, tmp_path: Path):
        result = save_config(tmp_path, {"iteration_limit": 3})
        assert result is None

    def test_save_config_roundtrip_with_load_config(self, tmp_path: Path):
        """save_config followed by load_config should preserve user values."""
        config = {
            "iteration_limit": 10,
            "models": {"default": "claude-sonnet-4-20250514"},
            "auto_save": False,
            "skip_permissions": False,
            "context_budget_override": 80,
            "context_budget_threshold": 50,
            "compaction_character_threshold": 300,
        }
        save_config(tmp_path, config)
        loaded = load_config(tmp_path)
        # All user-specified values should survive the roundtrip
        assert loaded["iteration_limit"] == 10
        assert loaded["models"]["default"] == "claude-sonnet-4-20250514"
        assert loaded["auto_save"] is False

    def test_save_config_atomic_write_does_not_leave_partial_file(self, tmp_path: Path):
        """After save_config completes, the config file should be fully written.
        The contract specifies atomic write (write to temp, rename)."""
        config = {"iteration_limit": 42}
        save_config(tmp_path, config)
        config_file = tmp_path / "svp_config.json"
        # The file should contain the complete, valid JSON
        loaded = json.loads(config_file.read_text())
        assert loaded["iteration_limit"] == 42

    def test_save_config_preserves_nested_dict_structure(self, tmp_path: Path):
        config = {
            "models": {
                "default": "claude-opus-4-6",
                "test_agent": "claude-haiku-3",
                "impl_agent": "claude-sonnet-4-20250514",
            }
        }
        save_config(tmp_path, config)
        config_file = tmp_path / "svp_config.json"
        loaded = json.loads(config_file.read_text())
        assert loaded["models"]["test_agent"] == "claude-haiku-3"
        assert loaded["models"]["impl_agent"] == "claude-sonnet-4-20250514"

    def test_save_config_atomic_write_leaves_no_temp_files(self, tmp_path: Path):
        """Contract: atomic write (write to temp, rename). After successful
        completion, no temporary files should remain in project_root."""
        files_before = set(tmp_path.iterdir())
        config = {"iteration_limit": 99, "auto_save": False}
        save_config(tmp_path, config)
        files_after = set(tmp_path.iterdir())
        # The only new file should be svp_config.json itself
        new_files = files_after - files_before
        assert new_files == {tmp_path / "svp_config.json"}, (
            f"Expected only svp_config.json, but found extra files: "
            f"{[f.name for f in new_files if f.name != 'svp_config.json']}"
        )


# ---------------------------------------------------------------------------
# derive_env_name tests
# ---------------------------------------------------------------------------


class TestDeriveEnvName:
    """Tests for derive_env_name function."""

    def test_derive_env_name_returns_string(self, tmp_path: Path):
        result = derive_env_name(tmp_path)
        assert isinstance(result, str)

    def test_derive_env_name_prefixes_with_svp_dash(self, tmp_path: Path):
        result = derive_env_name(tmp_path)
        assert result.startswith("svp-")

    def test_derive_env_name_uses_project_root_name(self):
        project_root = Path("/home/user/my-project")
        result = derive_env_name(project_root)
        assert result == "svp-my-project"

    def test_derive_env_name_deterministic_same_input_same_output(self):
        project_root = Path("/some/path/cool-project")
        result1 = derive_env_name(project_root)
        result2 = derive_env_name(project_root)
        assert result1 == result2

    def test_derive_env_name_different_inputs_different_outputs(self):
        root_a = Path("/path/to/project-alpha")
        root_b = Path("/path/to/project-beta")
        assert derive_env_name(root_a) != derive_env_name(root_b)

    def test_derive_env_name_with_simple_directory_name(self):
        result = derive_env_name(Path("/workspace/svp2.2"))
        assert result == "svp-svp2.2"

    def test_derive_env_name_format_matches_f_string_pattern(self):
        """Contract: returns f'svp-{project_root.name}'."""
        project_root = Path("/var/projects/test-repo")
        expected = f"svp-{project_root.name}"
        assert derive_env_name(project_root) == expected

    def test_derive_env_name_with_hyphenated_project_name(self):
        result = derive_env_name(Path("/tmp/my-cool-project"))
        assert result == "svp-my-cool-project"

    def test_derive_env_name_with_underscored_project_name(self):
        result = derive_env_name(Path("/tmp/my_cool_project"))
        assert result == "svp-my_cool_project"


# ---------------------------------------------------------------------------
# get_blueprint_dir tests
# ---------------------------------------------------------------------------


class TestGetBlueprintDir:
    """Tests for get_blueprint_dir function."""

    def test_get_blueprint_dir_returns_path_object(self, tmp_path: Path):
        result = get_blueprint_dir(tmp_path)
        assert isinstance(result, Path)

    def test_get_blueprint_dir_returns_project_root_joined_with_artifact_filename(
        self, tmp_path: Path
    ):
        """Contract: returns project_root / ARTIFACT_FILENAMES['blueprint_dir']."""
        result = get_blueprint_dir(tmp_path)
        expected = tmp_path / ARTIFACT_FILENAMES["blueprint_dir"]
        assert result == expected

    def test_get_blueprint_dir_is_under_project_root(self, tmp_path: Path):
        result = get_blueprint_dir(tmp_path)
        # The blueprint dir should be a child of project_root
        assert str(result).startswith(str(tmp_path))

    def test_get_blueprint_dir_uses_blueprint_dir_key_from_artifact_filenames(
        self, tmp_path: Path
    ):
        """Verify the path uses specifically the 'blueprint_dir' key."""
        result = get_blueprint_dir(tmp_path)
        blueprint_dir_value = ARTIFACT_FILENAMES.get("blueprint_dir", "")
        assert result == tmp_path / blueprint_dir_value


# ---------------------------------------------------------------------------
# get_model_for_agent tests
# ---------------------------------------------------------------------------


class TestGetModelForAgent:
    """Tests for get_model_for_agent function."""

    def test_get_model_for_agent_returns_string(self):
        config = {"models": {"default": "claude-opus-4-6"}}
        profile: Dict[str, Any] = {}
        result = get_model_for_agent("test_agent", config, profile)
        assert isinstance(result, str)

    def test_get_model_for_agent_never_returns_none(self):
        """Contract: never returns None."""
        config = {"models": {"default": "claude-opus-4-6"}}
        profile: Dict[str, Any] = {}
        result = get_model_for_agent("nonexistent_agent", config, profile)
        assert result is not None

    def test_get_model_for_agent_falls_back_to_config_models_default(self):
        """When no agent-specific override exists, use config models.default."""
        config = {"models": {"default": "claude-opus-4-6"}}
        profile: Dict[str, Any] = {}
        result = get_model_for_agent("some_agent", config, profile)
        assert result == "claude-opus-4-6"

    def test_get_model_for_agent_config_agent_specific_overrides_default(self):
        """config['models'][agent_key] overrides config['models']['default']."""
        config = {
            "models": {
                "default": "claude-opus-4-6",
                "test_agent": "claude-sonnet-4-20250514",
            }
        }
        profile: Dict[str, Any] = {}
        result = get_model_for_agent("test_agent", config, profile)
        assert result == "claude-sonnet-4-20250514"

    def test_get_model_for_agent_profile_overrides_config_agent_specific(self):
        """profile['pipeline']['agent_models'][agent_key] overrides
        config['models'][agent_key]."""
        config = {
            "models": {
                "default": "claude-opus-4-6",
                "test_agent": "claude-sonnet-4-20250514",
            }
        }
        profile = {
            "pipeline": {
                "agent_models": {
                    "test_agent": "claude-haiku-3",
                }
            }
        }
        result = get_model_for_agent("test_agent", config, profile)
        assert result == "claude-haiku-3"

    def test_get_model_for_agent_profile_overrides_config_default(self):
        """profile agent_models overrides config default when no config
        agent-specific exists."""
        config = {"models": {"default": "claude-opus-4-6"}}
        profile = {
            "pipeline": {
                "agent_models": {
                    "impl_agent": "claude-haiku-3",
                }
            }
        }
        result = get_model_for_agent("impl_agent", config, profile)
        assert result == "claude-haiku-3"

    def test_get_model_for_agent_precedence_profile_is_highest(self):
        """Full precedence: profile > config agent-specific > config default.
        Profile should win when all three are present."""
        config = {
            "models": {
                "default": "model-default",
                "blueprint_agent": "model-config-specific",
            }
        }
        profile = {
            "pipeline": {
                "agent_models": {
                    "blueprint_agent": "model-profile-specific",
                }
            }
        }
        result = get_model_for_agent("blueprint_agent", config, profile)
        assert result == "model-profile-specific"

    def test_get_model_for_agent_config_agent_key_used_when_no_profile_match(self):
        """When profile has agent_models but not for this agent,
        config agent-specific should be used."""
        config = {
            "models": {
                "default": "model-default",
                "test_agent": "model-config-test",
            }
        }
        profile = {
            "pipeline": {
                "agent_models": {
                    "other_agent": "model-profile-other",
                }
            }
        }
        result = get_model_for_agent("test_agent", config, profile)
        assert result == "model-config-test"

    def test_get_model_for_agent_empty_profile_uses_config(self):
        config = {
            "models": {
                "default": "claude-opus-4-6",
                "setup_agent": "claude-sonnet-4-20250514",
            }
        }
        profile: Dict[str, Any] = {}
        result = get_model_for_agent("setup_agent", config, profile)
        assert result == "claude-sonnet-4-20250514"

    def test_get_model_for_agent_profile_without_pipeline_key_uses_config(self):
        config = {"models": {"default": "claude-opus-4-6"}}
        profile = {"some_other_key": "value"}
        result = get_model_for_agent("test_agent", config, profile)
        assert result == "claude-opus-4-6"

    def test_get_model_for_agent_profile_pipeline_without_agent_models_uses_config(
        self,
    ):
        config = {"models": {"default": "claude-opus-4-6"}}
        profile = {"pipeline": {"some_setting": True}}
        result = get_model_for_agent("test_agent", config, profile)
        assert result == "claude-opus-4-6"

    def test_get_model_for_agent_returns_default_for_unknown_agent(self):
        """An agent key not in config or profile should fall back to default."""
        config = {"models": {"default": "claude-opus-4-6"}}
        profile = {"pipeline": {"agent_models": {}}}
        result = get_model_for_agent("totally_unknown_agent", config, profile)
        assert result == "claude-opus-4-6"

    def test_get_model_for_agent_never_returns_none_with_empty_models(self):
        """Contract: never returns None. This must hold even when the config
        models dict has no 'default' key and no agent-specific entry, and the
        profile provides no override."""
        config: Dict[str, Any] = {"models": {}}
        profile: Dict[str, Any] = {}
        result = get_model_for_agent("any_agent", config, profile)
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

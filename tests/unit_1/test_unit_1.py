"""
Test suite for Unit 1: Core Configuration.

Synthetic data assumptions:
- Project roots are created as temporary directories via tmp_path fixtures.
- svp_config.json files are written with known JSON content for load/save tests.
- Config dicts use simple key-value pairs sufficient to exercise merge behavior.
- Agent keys ("test_agent", "impl_agent", "unknown_agent") are synthetic identifiers
  not tied to any real agent registry.
- Profile dicts simulate the nested pipeline.agent_models structure from the spec.
- The DEFAULT_CONFIG values tested against are those specified in the blueprint:
  iteration_limit=3, models.default="claude-opus-4-6", context_budget_override=None,
  context_budget_threshold=65, compaction_character_threshold=200, auto_save=True,
  skip_permissions=True.
- ARTIFACT_FILENAMES keys tested are the minimum set from the blueprint contracts.
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from src.unit_1.stub import (
    ARTIFACT_FILENAMES,
    DEFAULT_CONFIG,
    derive_env_name,
    get_blueprint_dir,
    get_model_for_agent,
    load_config,
    save_config,
)

# ---------------------------------------------------------------------------
# ARTIFACT_FILENAMES registry
# ---------------------------------------------------------------------------


class TestArtifactFilenamesRegistry:
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

    def test_artifact_filenames_all_minimum_keys_present(self):
        required_keys = {
            "pipeline_state",
            "project_profile",
            "toolchain",
            "stakeholder_spec",
            "blueprint_dir",
            "blueprint_prose",
            "blueprint_contracts",
            "build_log",
            "task_prompt",
            "gate_prompt",
            "last_status",
            "svp_config",
            "assembly_map",
            "triage_result",
            "oracle_run_ledger",
        }
        assert required_keys.issubset(set(ARTIFACT_FILENAMES.keys()))

    def test_artifact_filenames_values_are_all_strings(self):
        for key, value in ARTIFACT_FILENAMES.items():
            assert isinstance(value, str), (
                f"Value for key '{key}' is not a string: {value!r}"
            )

    def test_artifact_filenames_values_are_relative_paths(self):
        for key, value in ARTIFACT_FILENAMES.items():
            assert not Path(value).is_absolute(), (
                f"Value for key '{key}' is an absolute path: {value!r}"
            )


# ---------------------------------------------------------------------------
# DEFAULT_CONFIG
# ---------------------------------------------------------------------------


class TestDefaultConfig:
    """Tests for the DEFAULT_CONFIG module-level constant."""

    def test_default_config_is_a_dict(self):
        assert isinstance(DEFAULT_CONFIG, dict)

    def test_default_config_iteration_limit_is_3(self):
        assert DEFAULT_CONFIG["iteration_limit"] == 3

    def test_default_config_iteration_limit_is_int(self):
        assert isinstance(DEFAULT_CONFIG["iteration_limit"], int)

    def test_default_config_models_contains_default_key(self):
        assert "default" in DEFAULT_CONFIG["models"]

    def test_default_config_models_default_is_claude_opus(self):
        assert DEFAULT_CONFIG["models"]["default"] == "claude-opus-4-6"

    def test_default_config_context_budget_override_is_none(self):
        assert DEFAULT_CONFIG["context_budget_override"] is None

    def test_default_config_context_budget_threshold_is_65(self):
        assert DEFAULT_CONFIG["context_budget_threshold"] == 65

    def test_default_config_context_budget_threshold_is_int(self):
        assert isinstance(DEFAULT_CONFIG["context_budget_threshold"], int)

    def test_default_config_compaction_character_threshold_is_200(self):
        assert DEFAULT_CONFIG["compaction_character_threshold"] == 200

    def test_default_config_compaction_character_threshold_is_int(self):
        assert isinstance(DEFAULT_CONFIG["compaction_character_threshold"], int)

    def test_default_config_auto_save_is_true(self):
        assert DEFAULT_CONFIG["auto_save"] is True

    def test_default_config_auto_save_is_bool(self):
        assert isinstance(DEFAULT_CONFIG["auto_save"], bool)

    def test_default_config_skip_permissions_is_true(self):
        assert DEFAULT_CONFIG["skip_permissions"] is True

    def test_default_config_skip_permissions_is_bool(self):
        assert isinstance(DEFAULT_CONFIG["skip_permissions"], bool)

    def test_default_config_has_all_required_keys(self):
        required_keys = {
            "iteration_limit",
            "models",
            "context_budget_override",
            "context_budget_threshold",
            "compaction_character_threshold",
            "auto_save",
            "skip_permissions",
        }
        assert required_keys.issubset(set(DEFAULT_CONFIG.keys()))


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    """Tests for load_config(project_root)."""

    def test_load_config_reads_svp_config_json(self, tmp_path):
        config_data = {"iteration_limit": 5, "models": {"default": "custom-model"}}
        (tmp_path / "svp_config.json").write_text(json.dumps(config_data))
        result = load_config(tmp_path)
        assert result["iteration_limit"] == 5

    def test_load_config_returns_dict(self, tmp_path):
        config_data = {"iteration_limit": 10}
        (tmp_path / "svp_config.json").write_text(json.dumps(config_data))
        result = load_config(tmp_path)
        assert isinstance(result, dict)

    def test_load_config_deep_merges_with_defaults(self, tmp_path):
        config_data = {"iteration_limit": 7}
        (tmp_path / "svp_config.json").write_text(json.dumps(config_data))
        result = load_config(tmp_path)
        # User override takes effect
        assert result["iteration_limit"] == 7
        # Default keys still present
        assert "auto_save" in result
        assert "skip_permissions" in result
        assert "context_budget_threshold" in result

    def test_load_config_user_values_override_defaults(self, tmp_path):
        config_data = {
            "auto_save": False,
            "context_budget_threshold": 80,
        }
        (tmp_path / "svp_config.json").write_text(json.dumps(config_data))
        result = load_config(tmp_path)
        assert result["auto_save"] is False
        assert result["context_budget_threshold"] == 80

    def test_load_config_defaults_fill_missing_keys(self, tmp_path):
        config_data = {"iteration_limit": 2}
        (tmp_path / "svp_config.json").write_text(json.dumps(config_data))
        result = load_config(tmp_path)
        assert result["models"]["default"] == DEFAULT_CONFIG["models"]["default"]
        assert (
            result["compaction_character_threshold"]
            == DEFAULT_CONFIG["compaction_character_threshold"]
        )
        assert result["skip_permissions"] == DEFAULT_CONFIG["skip_permissions"]

    def test_load_config_deep_merges_nested_models_dict(self, tmp_path):
        config_data = {
            "models": {"test_agent": "model-a"},
        }
        (tmp_path / "svp_config.json").write_text(json.dumps(config_data))
        result = load_config(tmp_path)
        # User's agent-specific model is preserved
        assert result["models"]["test_agent"] == "model-a"
        # Default model key is still present from deep merge
        assert result["models"]["default"] == DEFAULT_CONFIG["models"]["default"]

    def test_load_config_raises_file_not_found_when_absent(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path)

    def test_load_config_empty_json_object_returns_all_defaults(self, tmp_path):
        (tmp_path / "svp_config.json").write_text("{}")
        result = load_config(tmp_path)
        assert result["iteration_limit"] == DEFAULT_CONFIG["iteration_limit"]
        assert result["models"]["default"] == DEFAULT_CONFIG["models"]["default"]
        assert result["auto_save"] == DEFAULT_CONFIG["auto_save"]
        assert result["skip_permissions"] == DEFAULT_CONFIG["skip_permissions"]
        assert (
            result["context_budget_threshold"]
            == DEFAULT_CONFIG["context_budget_threshold"]
        )
        assert (
            result["compaction_character_threshold"]
            == DEFAULT_CONFIG["compaction_character_threshold"]
        )
        assert (
            result["context_budget_override"]
            == DEFAULT_CONFIG["context_budget_override"]
        )

    def test_load_config_preserves_extra_user_keys(self, tmp_path):
        config_data = {"iteration_limit": 3, "custom_key": "custom_value"}
        (tmp_path / "svp_config.json").write_text(json.dumps(config_data))
        result = load_config(tmp_path)
        assert result["custom_key"] == "custom_value"


# ---------------------------------------------------------------------------
# save_config
# ---------------------------------------------------------------------------


class TestSaveConfig:
    """Tests for save_config(project_root, config)."""

    def test_save_config_writes_svp_config_json(self, tmp_path):
        config = {"iteration_limit": 5, "models": {"default": "test-model"}}
        save_config(tmp_path, config)
        written_path = tmp_path / "svp_config.json"
        assert written_path.exists()

    def test_save_config_writes_valid_json(self, tmp_path):
        config = {"iteration_limit": 5, "auto_save": True}
        save_config(tmp_path, config)
        content = (tmp_path / "svp_config.json").read_text()
        parsed = json.loads(content)
        assert parsed == config

    def test_save_config_writes_formatted_json(self, tmp_path):
        config = {"iteration_limit": 5, "models": {"default": "test-model"}}
        save_config(tmp_path, config)
        content = (tmp_path / "svp_config.json").read_text()
        # Formatted JSON has newlines (not compact single-line)
        assert "\n" in content

    def test_save_config_returns_none(self, tmp_path):
        config = {"iteration_limit": 1}
        result = save_config(tmp_path, config)
        assert result is None

    def test_save_config_overwrites_existing_file(self, tmp_path):
        config_v1 = {"iteration_limit": 1}
        config_v2 = {"iteration_limit": 99}
        save_config(tmp_path, config_v1)
        save_config(tmp_path, config_v2)
        content = json.loads((tmp_path / "svp_config.json").read_text())
        assert content["iteration_limit"] == 99

    def test_save_config_atomic_write_does_not_leave_partial_file(self, tmp_path):
        """Atomic write implies write-to-temp-then-rename. After save, only
        the final file should exist -- no leftover temp files."""
        config = {"iteration_limit": 3}
        save_config(tmp_path, config)
        # Only svp_config.json should exist (no temp files left behind)
        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) == 1
        assert json_files[0].name == "svp_config.json"

    def test_save_config_round_trip_with_load_config(self, tmp_path):
        original = {
            "iteration_limit": 42,
            "models": {"default": "round-trip-model", "agent_x": "special-model"},
            "auto_save": False,
            "skip_permissions": False,
            "context_budget_override": 100,
            "context_budget_threshold": 50,
            "compaction_character_threshold": 300,
        }
        save_config(tmp_path, original)
        loaded = load_config(tmp_path)
        # Every key from original should be present and match
        for key in original:
            assert loaded[key] == original[key], f"Mismatch on key '{key}'"


# ---------------------------------------------------------------------------
# derive_env_name
# ---------------------------------------------------------------------------


class TestDeriveEnvName:
    """Tests for derive_env_name(project_root)."""

    def test_derive_env_name_returns_string(self, tmp_path):
        result = derive_env_name(tmp_path)
        assert isinstance(result, str)

    def test_derive_env_name_format_is_svp_dash_dirname(self, tmp_path):
        result = derive_env_name(tmp_path)
        expected = f"svp-{tmp_path.name}"
        assert result == expected

    def test_derive_env_name_uses_project_root_name(self):
        project_root = Path("/some/path/my-cool-project")
        result = derive_env_name(project_root)
        assert result == "svp-my-cool-project"

    def test_derive_env_name_is_deterministic(self, tmp_path):
        result_1 = derive_env_name(tmp_path)
        result_2 = derive_env_name(tmp_path)
        assert result_1 == result_2

    def test_derive_env_name_different_roots_produce_different_names(self):
        root_a = Path("/path/to/project-alpha")
        root_b = Path("/path/to/project-beta")
        assert derive_env_name(root_a) != derive_env_name(root_b)

    def test_derive_env_name_with_simple_name(self):
        project_root = Path("/workspace/myproject")
        result = derive_env_name(project_root)
        assert result == "svp-myproject"

    def test_derive_env_name_with_dotted_name(self):
        project_root = Path("/workspace/svp2.2")
        result = derive_env_name(project_root)
        assert result == "svp-svp2.2"


# ---------------------------------------------------------------------------
# get_blueprint_dir
# ---------------------------------------------------------------------------


class TestGetBlueprintDir:
    """Tests for get_blueprint_dir(project_root)."""

    def test_get_blueprint_dir_returns_path(self, tmp_path):
        result = get_blueprint_dir(tmp_path)
        assert isinstance(result, Path)

    def test_get_blueprint_dir_uses_artifact_filenames_blueprint_dir(self, tmp_path):
        expected = tmp_path / ARTIFACT_FILENAMES["blueprint_dir"]
        result = get_blueprint_dir(tmp_path)
        assert result == expected

    def test_get_blueprint_dir_is_under_project_root(self, tmp_path):
        result = get_blueprint_dir(tmp_path)
        # The result should start with project_root
        assert str(result).startswith(str(tmp_path))

    def test_get_blueprint_dir_different_roots_produce_different_paths(self, tmp_path):
        root_a = tmp_path / "project_a"
        root_b = tmp_path / "project_b"
        root_a.mkdir()
        root_b.mkdir()
        result_a = get_blueprint_dir(root_a)
        result_b = get_blueprint_dir(root_b)
        assert result_a != result_b

    def test_get_blueprint_dir_is_deterministic(self, tmp_path):
        result_1 = get_blueprint_dir(tmp_path)
        result_2 = get_blueprint_dir(tmp_path)
        assert result_1 == result_2


# ---------------------------------------------------------------------------
# get_model_for_agent
# ---------------------------------------------------------------------------


class TestGetModelForAgent:
    """Tests for get_model_for_agent(agent_key, config, profile)."""

    def _make_config(self, **overrides) -> Dict[str, Any]:
        """Helper to build a config dict with a models section."""
        config: Dict[str, Any] = {
            "models": {"default": "default-model"},
        }
        config["models"].update(overrides)
        return config

    def _make_profile(self, agent_models: Dict[str, str] = None) -> Dict[str, Any]:
        """Helper to build a profile dict with optional agent_models."""
        profile: Dict[str, Any] = {"pipeline": {}}
        if agent_models is not None:
            profile["pipeline"]["agent_models"] = agent_models
        return profile

    def test_get_model_for_agent_returns_string(self):
        config = self._make_config()
        profile = self._make_profile()
        result = get_model_for_agent("test_agent", config, profile)
        assert isinstance(result, str)

    def test_get_model_for_agent_never_returns_none(self):
        config = self._make_config()
        profile = self._make_profile()
        result = get_model_for_agent("nonexistent_agent", config, profile)
        assert result is not None

    def test_get_model_for_agent_falls_back_to_config_models_default(self):
        config = self._make_config()
        profile = self._make_profile()
        result = get_model_for_agent("some_agent", config, profile)
        assert result == "default-model"

    def test_get_model_for_agent_config_agent_key_overrides_default(self):
        config = self._make_config(test_agent="config-agent-model")
        profile = self._make_profile()
        result = get_model_for_agent("test_agent", config, profile)
        assert result == "config-agent-model"

    def test_get_model_for_agent_profile_overrides_config_agent_key(self):
        config = self._make_config(test_agent="config-agent-model")
        profile = self._make_profile(agent_models={"test_agent": "profile-agent-model"})
        result = get_model_for_agent("test_agent", config, profile)
        assert result == "profile-agent-model"

    def test_get_model_for_agent_profile_overrides_config_default(self):
        config = self._make_config()
        profile = self._make_profile(agent_models={"impl_agent": "profile-impl-model"})
        result = get_model_for_agent("impl_agent", config, profile)
        assert result == "profile-impl-model"

    def test_get_model_for_agent_precedence_profile_over_config_over_default(self):
        """Full three-tier precedence test:
        profile > config[agent_key] > config[default]"""
        config = {
            "models": {
                "default": "tier-3-default",
                "test_agent": "tier-2-config",
            }
        }
        profile = {
            "pipeline": {
                "agent_models": {
                    "test_agent": "tier-1-profile",
                }
            }
        }
        result = get_model_for_agent("test_agent", config, profile)
        assert result == "tier-1-profile"

    def test_get_model_for_agent_missing_from_profile_falls_to_config(self):
        config = self._make_config(test_agent="config-level")
        profile = self._make_profile(agent_models={"other_agent": "profile-other"})
        result = get_model_for_agent("test_agent", config, profile)
        assert result == "config-level"

    def test_get_model_for_agent_missing_from_both_falls_to_default(self):
        config = self._make_config(other_agent="config-other")
        profile = self._make_profile(agent_models={"yet_another": "profile-yet"})
        result = get_model_for_agent("unknown_agent", config, profile)
        assert result == "default-model"

    def test_get_model_for_agent_empty_profile_agent_models(self):
        config = self._make_config()
        profile = self._make_profile(agent_models={})
        result = get_model_for_agent("test_agent", config, profile)
        assert result == "default-model"

    def test_get_model_for_agent_no_agent_models_key_in_profile(self):
        config = self._make_config(test_agent="config-model")
        profile = {"pipeline": {}}
        result = get_model_for_agent("test_agent", config, profile)
        assert result == "config-model"

    def test_get_model_for_agent_empty_pipeline_in_profile(self):
        config = self._make_config()
        profile = {"pipeline": {}}
        result = get_model_for_agent("agent_x", config, profile)
        assert result == "default-model"


# ---------------------------------------------------------------------------
# No hardcoded paths outside ARTIFACT_FILENAMES
# ---------------------------------------------------------------------------


class TestNoHardcodedPaths:
    """The contract states no hardcoded paths exist outside ARTIFACT_FILENAMES.
    This test verifies that the functions consistently use ARTIFACT_FILENAMES
    for path resolution rather than embedding literal path strings."""

    def test_get_blueprint_dir_path_matches_artifact_registry(self, tmp_path):
        """get_blueprint_dir must derive its path from ARTIFACT_FILENAMES,
        not from a hardcoded string."""
        result = get_blueprint_dir(tmp_path)
        expected_suffix = ARTIFACT_FILENAMES["blueprint_dir"]
        assert str(result).endswith(expected_suffix)

    def test_load_config_uses_svp_config_artifact_name(self, tmp_path):
        """load_config reads from the filename registered in ARTIFACT_FILENAMES
        for svp_config."""
        svp_config_name = ARTIFACT_FILENAMES["svp_config"]
        config_path = tmp_path / svp_config_name
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({"iteration_limit": 99}))
        result = load_config(tmp_path)
        assert result["iteration_limit"] == 99

    def test_save_config_writes_to_svp_config_artifact_name(self, tmp_path):
        """save_config writes to the filename registered in ARTIFACT_FILENAMES
        for svp_config."""
        svp_config_name = ARTIFACT_FILENAMES["svp_config"]
        config = {"iteration_limit": 77}
        save_config(tmp_path, config)
        written = json.loads((tmp_path / svp_config_name).read_text())
        assert written["iteration_limit"] == 77

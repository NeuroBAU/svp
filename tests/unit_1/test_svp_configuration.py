"""
Test suite for Unit 1: SVP Configuration

Tests cover:
- DEFAULT_CONFIG data contract
- load_config: merging, defaults fallback, error handling
- validate_config: valid configs, structural violations
- get_model_for_agent: agent-specific and fallback behavior
- get_effective_context_budget: override vs computed behavior
- write_default_config: file creation and content
- All invariants from the blueprint
- All error conditions from the blueprint

Synthetic Data Assumptions:
==========================================================================
DATA ASSUMPTION: Project roots are temporary directories created via
tmp_path, representing valid filesystem directories.

DATA ASSUMPTION: Config JSON content uses small integer values for
iteration_limit (1-10) and context_budget_threshold (1-100), representing
typical tunable parameters.

DATA ASSUMPTION: Agent role strings like "test_agent",
"implementation_agent", "help_agent" are the known roles from
DEFAULT_CONFIG. "unknown_agent" represents a role not explicitly
configured.

DATA ASSUMPTION: Malformed JSON is represented by a string with invalid
JSON syntax (e.g., missing closing brace). This is a standard edge case.

DATA ASSUMPTION: context_budget_override values (e.g., 50000) represent
token counts in a plausible LLM context window range.
==========================================================================
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any

from svp.scripts.svp_config import (
    DEFAULT_CONFIG,
    load_config,
    validate_config,
    get_model_for_agent,
    get_effective_context_budget,
    write_default_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_config(project_root: Path, config_dict: Dict[str, Any]) -> Path:
    """Helper: write a config dict as JSON to svp_config.json in project_root."""
    config_path = project_root / "svp_config.json"
    config_path.write_text(json.dumps(config_dict, indent=2))
    return config_path


# ===========================================================================
# 1. DEFAULT_CONFIG data contract
# ===========================================================================


class TestDefaultConfig:
    """Verify that the module-level DEFAULT_CONFIG matches the blueprint schema."""

    def test_default_config_is_dict(self):
        assert isinstance(DEFAULT_CONFIG, dict), "DEFAULT_CONFIG must be a dict"

    def test_default_config_has_iteration_limit(self):
        assert "iteration_limit" in DEFAULT_CONFIG
        assert DEFAULT_CONFIG["iteration_limit"] == 3

    def test_default_config_has_models(self):
        assert "models" in DEFAULT_CONFIG
        assert isinstance(DEFAULT_CONFIG["models"], dict)

    def test_default_config_models_keys(self):
        # DATA ASSUMPTION: The four model keys specified in the blueprint.
        expected_keys = {"test_agent", "implementation_agent", "help_agent", "default"}
        assert expected_keys.issubset(set(DEFAULT_CONFIG["models"].keys()))

    def test_default_config_model_values(self):
        models = DEFAULT_CONFIG["models"]
        assert models["test_agent"] == "claude-opus-4-6"
        assert models["implementation_agent"] == "claude-opus-4-6"
        assert models["help_agent"] == "claude-sonnet-4-6"
        assert models["default"] == "claude-opus-4-6"

    def test_default_config_context_budget_override_is_none(self):
        assert DEFAULT_CONFIG["context_budget_override"] is None

    def test_default_config_context_budget_threshold(self):
        assert DEFAULT_CONFIG["context_budget_threshold"] == 65

    def test_default_config_compaction_character_threshold(self):
        assert DEFAULT_CONFIG["compaction_character_threshold"] == 200

    def test_default_config_auto_save(self):
        assert DEFAULT_CONFIG["auto_save"] is True

    def test_default_config_skip_permissions(self):
        assert DEFAULT_CONFIG["skip_permissions"] is True


# ===========================================================================
# 2. load_config
# ===========================================================================


class TestLoadConfig:
    """Tests for load_config: merging, defaults fallback, error handling."""

    def test_load_config_returns_defaults_when_file_absent(self, tmp_path):
        """Contract: load_config on a non-existent file returns a copy of
        DEFAULT_CONFIG without error."""
        result = load_config(tmp_path)
        assert result == DEFAULT_CONFIG
        # Must be a copy, not the same object
        assert result is not DEFAULT_CONFIG

    def test_load_config_returns_dict(self, tmp_path):
        """Invariant: Config must be a dict."""
        result = load_config(tmp_path)
        assert isinstance(result, dict)

    def test_load_config_result_has_iteration_limit(self, tmp_path):
        """Invariant: Config must contain iteration_limit."""
        result = load_config(tmp_path)
        assert "iteration_limit" in result

    def test_load_config_result_has_models(self, tmp_path):
        """Invariant: Config must contain models section."""
        result = load_config(tmp_path)
        assert "models" in result

    def test_load_config_iteration_limit_at_least_1(self, tmp_path):
        """Invariant: Iteration limit must be at least 1."""
        result = load_config(tmp_path)
        assert result["iteration_limit"] >= 1

    def test_load_config_budget_threshold_in_range(self, tmp_path):
        """Invariant: Budget threshold must be 1-100."""
        result = load_config(tmp_path)
        assert 0 < result["context_budget_threshold"] <= 100

    def test_load_config_compaction_threshold_non_negative(self, tmp_path):
        """Invariant: Compaction threshold must be non-negative."""
        result = load_config(tmp_path)
        assert result["compaction_character_threshold"] >= 0

    def test_load_config_skip_permissions_is_bool(self, tmp_path):
        """Invariant: skip_permissions must be a boolean."""
        result = load_config(tmp_path)
        assert isinstance(result["skip_permissions"], bool)

    def test_load_config_merges_file_over_defaults(self, tmp_path):
        """Contract: load_config returns the merged result of file content
        over defaults -- missing keys in the file are filled from DEFAULT_CONFIG."""
        # DATA ASSUMPTION: Partial config with only iteration_limit overridden to 5.
        partial_config = {"iteration_limit": 5}
        _write_config(tmp_path, partial_config)

        result = load_config(tmp_path)

        # Overridden value should come from file
        assert result["iteration_limit"] == 5
        # Missing keys should come from defaults
        assert result["models"] == DEFAULT_CONFIG["models"]
        assert result["context_budget_threshold"] == DEFAULT_CONFIG["context_budget_threshold"]
        assert result["auto_save"] == DEFAULT_CONFIG["auto_save"]
        assert result["skip_permissions"] == DEFAULT_CONFIG["skip_permissions"]

    def test_load_config_merges_nested_models(self, tmp_path):
        """Contract: Merging should handle nested 'models' dict."""
        # DATA ASSUMPTION: Partial models dict with only one key overridden.
        partial_config = {
            "models": {
                "help_agent": "claude-opus-4-6"
            }
        }
        _write_config(tmp_path, partial_config)

        result = load_config(tmp_path)
        assert "models" in result
        # The help_agent should be overridden
        assert result["models"]["help_agent"] == "claude-opus-4-6"

    def test_load_config_full_file(self, tmp_path):
        """Load a fully specified config file -- all values from file."""
        # DATA ASSUMPTION: A complete config with all keys present, values
        # different from defaults to verify file content takes precedence.
        full_config = {
            "iteration_limit": 7,
            "models": {
                "test_agent": "custom-model-a",
                "implementation_agent": "custom-model-b",
                "help_agent": "custom-model-c",
                "default": "custom-model-d",
            },
            "context_budget_override": 50000,
            "context_budget_threshold": 80,
            "compaction_character_threshold": 500,
            "auto_save": False,
            "skip_permissions": False,
        }
        _write_config(tmp_path, full_config)

        result = load_config(tmp_path)
        assert result["iteration_limit"] == 7
        assert result["models"]["test_agent"] == "custom-model-a"
        assert result["context_budget_override"] == 50000
        assert result["context_budget_threshold"] == 80
        assert result["compaction_character_threshold"] == 500
        assert result["auto_save"] is False
        assert result["skip_permissions"] is False

    def test_load_config_malformed_json_raises(self, tmp_path):
        """Error condition: json.JSONDecodeError when file is not valid JSON."""
        config_path = tmp_path / "svp_config.json"
        # DATA ASSUMPTION: Malformed JSON with missing closing brace.
        config_path.write_text('{"iteration_limit": 3,')

        with pytest.raises(json.JSONDecodeError):
            load_config(tmp_path)

    def test_load_config_no_caching_across_invocations(self, tmp_path):
        """Contract: Config changes made by the human take effect on next load
        -- no caching across invocations."""
        # First load with defaults
        result1 = load_config(tmp_path)
        assert result1["iteration_limit"] == DEFAULT_CONFIG["iteration_limit"]

        # Write a config file
        # DATA ASSUMPTION: iteration_limit=10 represents a human-modified value.
        _write_config(tmp_path, {"iteration_limit": 10})

        # Second load should pick up the change
        result2 = load_config(tmp_path)
        assert result2["iteration_limit"] == 10

    def test_load_config_project_root_must_be_dir(self):
        """Invariant: project_root must be an existing directory."""
        non_existent = Path("/nonexistent_svp_test_dir_abc123")
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            load_config(non_existent)


# ===========================================================================
# 3. validate_config
# ===========================================================================


class TestValidateConfig:
    """Tests for validate_config: valid configs and violation detection."""

    def test_valid_config_returns_empty_list(self):
        """Contract: validate_config returns an empty list when config is valid."""
        # Use a copy of DEFAULT_CONFIG which is known-valid
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        errors = validate_config(config)
        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_returns_list_type(self):
        """validate_config always returns a list."""
        errors = validate_config(DEFAULT_CONFIG)
        assert isinstance(errors, list)

    def test_missing_iteration_limit(self):
        """Error: missing required key iteration_limit."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        del config["iteration_limit"]
        errors = validate_config(config)
        assert isinstance(errors, list)
        assert len(errors) > 0
        # Contract: human-readable error strings
        assert all(isinstance(e, str) for e in errors)

    def test_missing_models(self):
        """Error: missing required key models."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        del config["models"]
        errors = validate_config(config)
        assert len(errors) > 0
        assert all(isinstance(e, str) for e in errors)

    def test_wrong_type_iteration_limit(self):
        """Error: iteration_limit is not an integer."""
        # DATA ASSUMPTION: A string value for iteration_limit is a type violation.
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["iteration_limit"] = "three"
        errors = validate_config(config)
        assert len(errors) > 0

    def test_iteration_limit_less_than_1(self):
        """Invariant: iteration_limit must be at least 1."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["iteration_limit"] = 0
        errors = validate_config(config)
        assert len(errors) > 0

    def test_context_budget_threshold_out_of_range_zero(self):
        """Invariant: budget threshold must be > 0."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["context_budget_threshold"] = 0
        errors = validate_config(config)
        assert len(errors) > 0

    def test_context_budget_threshold_out_of_range_over_100(self):
        """Invariant: budget threshold must be <= 100."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["context_budget_threshold"] = 101
        errors = validate_config(config)
        assert len(errors) > 0

    def test_negative_compaction_threshold(self):
        """Invariant: compaction_character_threshold must be non-negative."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["compaction_character_threshold"] = -1
        errors = validate_config(config)
        assert len(errors) > 0

    def test_skip_permissions_not_bool(self):
        """Invariant: skip_permissions must be a boolean."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["skip_permissions"] = "yes"
        errors = validate_config(config)
        assert len(errors) > 0

    def test_multiple_violations_reported(self):
        """Contract: returns a list of error strings for each violation found."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["iteration_limit"] = 0
        config["context_budget_threshold"] = 0
        config["compaction_character_threshold"] = -5
        errors = validate_config(config)
        # Should report at least one error for each violation
        assert len(errors) >= 2

    def test_error_strings_are_human_readable(self):
        """Contract: error strings are human-readable."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["iteration_limit"] = -1
        errors = validate_config(config)
        assert len(errors) > 0
        for e in errors:
            assert isinstance(e, str)
            assert len(e) > 0  # Non-empty string

    def test_models_wrong_type(self):
        """Error: models is not a dict."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["models"] = "not-a-dict"
        errors = validate_config(config)
        assert len(errors) > 0


# ===========================================================================
# 4. get_model_for_agent
# ===========================================================================


class TestGetModelForAgent:
    """Tests for get_model_for_agent: agent-specific and fallback behavior."""

    def test_returns_specific_model_for_test_agent(self):
        """Contract: returns the agent-specific model if configured."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        result = get_model_for_agent(config, "test_agent")
        assert result == "claude-opus-4-6"

    def test_returns_specific_model_for_help_agent(self):
        """Contract: returns the agent-specific model if configured."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        result = get_model_for_agent(config, "help_agent")
        assert result == "claude-sonnet-4-6"

    def test_returns_specific_model_for_implementation_agent(self):
        """Contract: returns the agent-specific model if configured."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        result = get_model_for_agent(config, "implementation_agent")
        assert result == "claude-opus-4-6"

    def test_returns_default_for_unknown_agent(self):
        """Contract: returns the models.default value when agent role is not
        explicitly configured."""
        # DATA ASSUMPTION: "unknown_agent" is a role not present in the models dict.
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        result = get_model_for_agent(config, "unknown_agent")
        assert result == config["models"]["default"]

    def test_returns_string(self):
        """Return type is str."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        result = get_model_for_agent(config, "test_agent")
        assert isinstance(result, str)

    def test_custom_model_for_agent(self):
        """When a custom model is configured for an agent, it is returned."""
        # DATA ASSUMPTION: "custom-fast-model" is a hypothetical custom model string.
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["models"]["test_agent"] = "custom-fast-model"
        result = get_model_for_agent(config, "test_agent")
        assert result == "custom-fast-model"

    def test_custom_default_model_for_unknown_agent(self):
        """Fallback uses models.default, which may be customized."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["models"]["default"] = "custom-default-model"
        result = get_model_for_agent(config, "some_new_agent")
        assert result == "custom-default-model"


# ===========================================================================
# 5. get_effective_context_budget
# ===========================================================================


class TestGetEffectiveContextBudget:
    """Tests for get_effective_context_budget: override vs computed behavior."""

    def test_returns_override_when_set(self):
        """Contract: returns the context_budget_override when set and non-null."""
        # DATA ASSUMPTION: 50000 tokens as a plausible override value.
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["context_budget_override"] = 50000
        result = get_effective_context_budget(config)
        assert result == 50000

    def test_returns_int(self):
        """Return type should be int."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        result = get_effective_context_budget(config)
        assert isinstance(result, int)

    def test_returns_computed_when_override_is_none(self):
        """Contract: when override is None, computes from the smallest model
        context window minus 20,000 tokens overhead."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        assert config["context_budget_override"] is None
        result = get_effective_context_budget(config)
        # The result should be a positive integer (computed from model windows)
        assert isinstance(result, int)
        assert result > 0

    def test_computed_value_is_positive(self):
        """The computed context budget should always be positive."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["context_budget_override"] = None
        result = get_effective_context_budget(config)
        assert result > 0

    def test_override_zero_is_respected(self):
        """Contract: override is returned when set, even if zero or unusual.
        (Note: Zero may not be practical but the contract says 'when set and
        non-null'.)"""
        # DATA ASSUMPTION: 0 is a non-null value, so it counts as an override.
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["context_budget_override"] = 0
        result = get_effective_context_budget(config)
        assert result == 0

    def test_override_large_value(self):
        """Contract: large override values are returned as-is."""
        # DATA ASSUMPTION: 200000 tokens as a large override value.
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["context_budget_override"] = 200000
        result = get_effective_context_budget(config)
        assert result == 200000


# ===========================================================================
# 6. write_default_config
# ===========================================================================


class TestWriteDefaultConfig:
    """Tests for write_default_config: file creation and content."""

    def test_writes_file_and_returns_path(self, tmp_path):
        """Contract: writes DEFAULT_CONFIG as formatted JSON and returns the path."""
        result_path = write_default_config(tmp_path)
        assert isinstance(result_path, Path)
        assert result_path.exists()
        assert result_path.name == "svp_config.json"

    def test_returned_path_is_in_project_root(self, tmp_path):
        """The returned path should be {project_root}/svp_config.json."""
        result_path = write_default_config(tmp_path)
        assert result_path == tmp_path / "svp_config.json"

    def test_file_content_matches_default_config(self, tmp_path):
        """Contract: writes DEFAULT_CONFIG as formatted JSON."""
        write_default_config(tmp_path)
        config_path = tmp_path / "svp_config.json"
        content = json.loads(config_path.read_text())
        assert content == DEFAULT_CONFIG

    def test_file_is_formatted_json(self, tmp_path):
        """Contract: writes formatted (indented) JSON."""
        write_default_config(tmp_path)
        config_path = tmp_path / "svp_config.json"
        raw = config_path.read_text()
        # Formatted JSON should have newlines (not a single-line dump)
        assert "\n" in raw

    def test_written_config_is_loadable(self, tmp_path):
        """The written config should be loadable by load_config."""
        write_default_config(tmp_path)
        result = load_config(tmp_path)
        assert result == DEFAULT_CONFIG

    def test_project_root_must_be_dir(self):
        """Invariant: project_root must be an existing directory."""
        non_existent = Path("/nonexistent_svp_test_dir_xyz789")
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            write_default_config(non_existent)


# ===========================================================================
# 7. Signature verification
# ===========================================================================


class TestSignatures:
    """Verify function signatures match the blueprint."""

    def test_load_config_accepts_path_returns_dict(self, tmp_path):
        """load_config(project_root: Path) -> Dict[str, Any]"""
        result = load_config(tmp_path)
        assert isinstance(result, dict)

    def test_validate_config_accepts_dict_returns_list(self):
        """validate_config(config: Dict[str, Any]) -> list[str]"""
        result = validate_config(DEFAULT_CONFIG)
        assert isinstance(result, list)

    def test_get_model_for_agent_accepts_dict_and_str_returns_str(self):
        """get_model_for_agent(config: Dict[str, Any], agent_role: str) -> str"""
        result = get_model_for_agent(DEFAULT_CONFIG, "test_agent")
        assert isinstance(result, str)

    def test_get_effective_context_budget_accepts_dict_returns_int(self):
        """get_effective_context_budget(config: Dict[str, Any]) -> int"""
        result = get_effective_context_budget(DEFAULT_CONFIG)
        assert isinstance(result, int)

    def test_write_default_config_accepts_path_returns_path(self, tmp_path):
        """write_default_config(project_root: Path) -> Path"""
        result = write_default_config(tmp_path)
        assert isinstance(result, Path)


# ===========================================================================
# 8. Integration-style scenarios
# ===========================================================================


class TestIntegrationScenarios:
    """End-to-end scenarios combining multiple functions."""

    def test_write_then_load_roundtrip(self, tmp_path):
        """Write defaults, load them back, validate -- full cycle."""
        written_path = write_default_config(tmp_path)
        assert written_path.exists()

        loaded = load_config(tmp_path)
        assert loaded == DEFAULT_CONFIG

        errors = validate_config(loaded)
        assert errors == []

    def test_load_modify_validate(self, tmp_path):
        """Load defaults, modify a value, validate."""
        config = load_config(tmp_path)
        config["iteration_limit"] = 5
        errors = validate_config(config)
        assert errors == []

    def test_load_corrupt_validate(self, tmp_path):
        """Load defaults, corrupt a value, validate catches it."""
        config = load_config(tmp_path)
        config["iteration_limit"] = -1
        errors = validate_config(config)
        assert len(errors) > 0

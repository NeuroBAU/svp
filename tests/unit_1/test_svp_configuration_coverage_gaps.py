"""
Coverage gap tests for Unit 1: SVP Configuration

These tests cover behavioral contracts and error conditions from the blueprint
that were not exercised by the original test suite.

Gaps addressed:
1. load_config raises ValueError when file contains structurally invalid config
   values (e.g., iteration_limit=0). The blueprint Tier 3 error condition
   states: ValueError: "Invalid config: {details}" -- when validate_config
   finds a structural problem.
2. load_config raises ValueError when the JSON file contains a valid JSON
   value that is not a dict (e.g., a JSON array). This is a structural
   problem caught during loading.
3. Deep merge of nested models dict preserves non-overridden default keys.
   The contract says "missing keys in the file are filled from DEFAULT_CONFIG"
   and this must hold for nested dicts like models.
4. get_effective_context_budget computed value verifies the formula:
   smallest model context window minus 20,000 tokens overhead. Existing
   tests only checked result > 0.
5. validate_config reports exactly one error per violation (3 violations
   produce at least 3 errors).

Synthetic Data Assumptions:
==========================================================================
DATA ASSUMPTION: A config file with iteration_limit=0 represents a
structurally invalid config that should cause load_config to raise ValueError.

DATA ASSUMPTION: A JSON array "[1, 2, 3]" is valid JSON but not a valid
config structure (must be a dict/object).

DATA ASSUMPTION: Overriding only "help_agent" in the models section means
that "test_agent", "implementation_agent", and "default" must be preserved
from DEFAULT_CONFIG.

DATA ASSUMPTION: The computed context budget with default models (all having
200,000 token windows) is 200,000 - 20,000 = 180,000. This value derives
from the blueprint's formula: smallest model context window minus 20,000
tokens overhead.
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


def _write_raw_config(project_root: Path, raw_text: str) -> Path:
    """Helper: write raw text to svp_config.json in project_root."""
    config_path = project_root / "svp_config.json"
    config_path.write_text(raw_text)
    return config_path


# ===========================================================================
# Gap 1: load_config raises ValueError for structurally invalid config
# ===========================================================================


class TestLoadConfigValueError:
    """Blueprint Tier 3 error condition: ValueError: 'Invalid config: {details}'
    when validate_config finds a structural problem during load_config."""

    def test_load_config_raises_valueerror_for_invalid_iteration_limit(self, tmp_path):
        """load_config should raise ValueError when the merged config has
        iteration_limit=0, which violates the invariant iteration_limit >= 1."""
        # DATA ASSUMPTION: iteration_limit=0 is structurally invalid per blueprint.
        _write_config(tmp_path, {"iteration_limit": 0})
        with pytest.raises(ValueError, match="Invalid config"):
            load_config(tmp_path)

    def test_load_config_raises_valueerror_for_negative_compaction(self, tmp_path):
        """load_config should raise ValueError when compaction_character_threshold
        is negative, violating the non-negative invariant."""
        _write_config(tmp_path, {"compaction_character_threshold": -10})
        with pytest.raises(ValueError, match="Invalid config"):
            load_config(tmp_path)

    def test_load_config_raises_valueerror_for_bad_threshold(self, tmp_path):
        """load_config should raise ValueError when context_budget_threshold
        is out of the valid 1-100 range."""
        _write_config(tmp_path, {"context_budget_threshold": 0})
        with pytest.raises(ValueError, match="Invalid config"):
            load_config(tmp_path)

    def test_load_config_raises_valueerror_for_string_iteration_limit(self, tmp_path):
        """load_config should raise ValueError when iteration_limit has a wrong
        type (string instead of int)."""
        _write_config(tmp_path, {"iteration_limit": "five"})
        with pytest.raises(ValueError, match="Invalid config"):
            load_config(tmp_path)

    def test_load_config_raises_valueerror_for_non_bool_skip_permissions(self, tmp_path):
        """load_config should raise ValueError when skip_permissions is not a boolean."""
        _write_config(tmp_path, {"skip_permissions": "yes"})
        with pytest.raises(ValueError, match="Invalid config"):
            load_config(tmp_path)


# ===========================================================================
# Gap 2: load_config raises ValueError for non-dict JSON top-level value
# ===========================================================================


class TestLoadConfigNonDictJson:
    """Blueprint error condition: ValueError for structural problems. A JSON file
    containing a valid JSON value that is not a dict (e.g., an array or string)
    is a structural problem."""

    def test_load_config_raises_valueerror_for_json_array(self, tmp_path):
        """A JSON file containing a JSON array is valid JSON but not a valid
        config structure."""
        # DATA ASSUMPTION: "[1, 2, 3]" is valid JSON but not a JSON object.
        _write_raw_config(tmp_path, "[1, 2, 3]")
        with pytest.raises(ValueError):
            load_config(tmp_path)

    def test_load_config_raises_valueerror_for_json_string(self, tmp_path):
        """A JSON file containing a JSON string is valid JSON but not a valid
        config structure."""
        _write_raw_config(tmp_path, '"just a string"')
        with pytest.raises(ValueError):
            load_config(tmp_path)

    def test_load_config_raises_valueerror_for_json_number(self, tmp_path):
        """A JSON file containing a JSON number is valid JSON but not a valid
        config structure."""
        _write_raw_config(tmp_path, "42")
        with pytest.raises(ValueError):
            load_config(tmp_path)


# ===========================================================================
# Gap 3: Deep merge preserves non-overridden keys in nested models dict
# ===========================================================================


class TestDeepMergeNestedModels:
    """Blueprint contract: 'missing keys in the file are filled from
    DEFAULT_CONFIG.' This must hold for nested dicts like models -- when only
    one model key is overridden, all other default model keys must be preserved."""

    def test_nested_merge_preserves_default_model_keys(self, tmp_path):
        """When only 'help_agent' is overridden in models, the other default
        model keys (test_agent, implementation_agent, default) must be
        preserved from DEFAULT_CONFIG."""
        # DATA ASSUMPTION: Overriding only help_agent in models section.
        partial_config = {
            "models": {
                "help_agent": "claude-opus-4-6"
            }
        }
        _write_config(tmp_path, partial_config)

        result = load_config(tmp_path)

        # Overridden key
        assert result["models"]["help_agent"] == "claude-opus-4-6"
        # Non-overridden keys must come from DEFAULT_CONFIG
        assert result["models"]["test_agent"] == DEFAULT_CONFIG["models"]["test_agent"]
        assert result["models"]["implementation_agent"] == DEFAULT_CONFIG["models"]["implementation_agent"]
        assert result["models"]["default"] == DEFAULT_CONFIG["models"]["default"]

    def test_nested_merge_preserves_all_four_model_keys(self, tmp_path):
        """When only one model key is provided, all four expected model keys
        must be present in the result."""
        partial_config = {
            "models": {
                "default": "custom-model"
            }
        }
        _write_config(tmp_path, partial_config)

        result = load_config(tmp_path)
        expected_keys = {"test_agent", "implementation_agent", "help_agent", "default"}
        assert expected_keys.issubset(set(result["models"].keys()))


# ===========================================================================
# Gap 4: get_effective_context_budget computed formula verification
# ===========================================================================


class TestGetEffectiveContextBudgetFormula:
    """Blueprint contract: 'computes from the smallest model context window
    minus 20,000 tokens overhead.' The existing tests only checked result > 0.
    These tests verify the actual computed value."""

    def test_computed_value_with_default_config(self):
        """With default models (claude-opus-4-6 at 200k, claude-sonnet-4-6
        at 200k), the smallest window is 200,000 and the computed result
        should be 200,000 - 20,000 = 180,000."""
        # DATA ASSUMPTION: Default config models all have 200,000 token windows.
        # The formula is: smallest_window - 20,000 overhead = 180,000.
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        assert config["context_budget_override"] is None
        result = get_effective_context_budget(config)
        assert result == 180_000

    def test_computed_value_accounts_for_overhead(self):
        """The computed value must reflect the 20,000 token overhead deduction.
        With default config, the result must be strictly less than the smallest
        model context window."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["context_budget_override"] = None
        result = get_effective_context_budget(config)
        # The result must be less than 200,000 (the smallest window)
        # by exactly 20,000
        assert result < 200_000
        assert result == 200_000 - 20_000


# ===========================================================================
# Gap 5: validate_config reports one error per violation
# ===========================================================================


class TestValidateConfigPerViolationErrors:
    """Blueprint contract: 'returns a list of human-readable error strings for
    each violation found.' Three independent violations should produce at least
    three error strings."""

    def test_three_violations_produce_at_least_three_errors(self):
        """Three independent violations (iteration_limit, budget_threshold,
        compaction_threshold) should produce at least three error strings."""
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config["iteration_limit"] = 0         # violation 1
        config["context_budget_threshold"] = 0  # violation 2
        config["compaction_character_threshold"] = -5  # violation 3
        errors = validate_config(config)
        assert len(errors) >= 3
        assert all(isinstance(e, str) for e in errors)

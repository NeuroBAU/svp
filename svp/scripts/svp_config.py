"""SVP Configuration -- loading, validating, and accessing tunable parameters."""

import copy
import json
from typing import Optional, Dict, Any
from pathlib import Path

# --- Data contract: configuration schema ---

DEFAULT_CONFIG: Dict[str, Any] = {
    "iteration_limit": 3,
    "models": {
        "test_agent": "claude-opus-4-6",
        "implementation_agent": "claude-opus-4-6",
        "help_agent": "claude-sonnet-4-6",
        "default": "claude-opus-4-6",
    },
    "context_budget_override": None,
    "context_budget_threshold": 65,
    "compaction_character_threshold": 200,
    "auto_save": True,
    "skip_permissions": True,
}

# Known model context windows (in tokens) for computing effective context budget.
_MODEL_CONTEXT_WINDOWS: Dict[str, int] = {
    "claude-opus-4-6": 200_000,
    "claude-sonnet-4-6": 200_000,
}

_CONTEXT_BUDGET_OVERHEAD: int = 20_000


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge *override* into a copy of *base*.

    For nested dicts the merge recurses; for all other types the override
    value wins.  Keys present in *base* but absent in *override* are kept.
    """
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_config(project_root: Path) -> Dict[str, Any]:
    """Load configuration from ``svp_config.json`` under *project_root*.

    If the file does not exist, a copy of ``DEFAULT_CONFIG`` is returned
    without raising an error.  Missing keys in the file are filled from
    ``DEFAULT_CONFIG`` (deep merge).

    Raises
    ------
    json.JSONDecodeError
        If the file exists but contains invalid JSON.
    ValueError
        If the loaded configuration fails structural validation.
    """
    assert project_root.is_dir(), "Project root must be an existing directory"

    config_path = project_root / "svp_config.json"

    if not config_path.exists():
        return copy.deepcopy(DEFAULT_CONFIG)

    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except Exception:
        raise

    try:
        file_config = json.loads(raw_text)
    except json.JSONDecodeError:
        raise

    if not isinstance(file_config, dict):
        raise ValueError("Invalid config: top-level value must be a JSON object")

    merged = _deep_merge(DEFAULT_CONFIG, file_config)

    errors = validate_config(merged)
    if errors:
        raise ValueError(f"Invalid config: {'; '.join(errors)}")

    return merged


def validate_config(config: Dict[str, Any]) -> list[str]:
    """Validate a configuration dictionary.

    Returns an empty list when the config is valid, otherwise returns a
    list of human-readable error strings -- one for each violation found.
    """
    errors: list[str] = []

    # Required top-level keys and expected types
    if "iteration_limit" not in config:
        errors.append("Missing required key: iteration_limit")
    else:
        if not isinstance(config["iteration_limit"], int):
            errors.append("iteration_limit must be an integer")
        elif config["iteration_limit"] < 1:
            errors.append("iteration_limit must be at least 1")

    if "models" not in config:
        errors.append("Missing required key: models")
    else:
        if not isinstance(config["models"], dict):
            errors.append("models must be a dict")
        else:
            if "default" not in config["models"]:
                errors.append("models must contain a 'default' key")

    if "context_budget_threshold" in config:
        cbt = config["context_budget_threshold"]
        if not isinstance(cbt, (int, float)):
            errors.append("context_budget_threshold must be a number")
        elif not (0 < cbt <= 100):
            errors.append("context_budget_threshold must be between 1 and 100")

    if "compaction_character_threshold" in config:
        cct = config["compaction_character_threshold"]
        if not isinstance(cct, (int, float)):
            errors.append("compaction_character_threshold must be a number")
        elif cct < 0:
            errors.append("compaction_character_threshold must be non-negative")

    if "skip_permissions" in config:
        if not isinstance(config["skip_permissions"], bool):
            errors.append("skip_permissions must be a boolean")

    return errors


def get_model_for_agent(config: Dict[str, Any], agent_role: str) -> str:
    """Return the model identifier for *agent_role*.

    If an agent-specific model is configured under ``config["models"]``,
    that value is returned.  Otherwise the ``models.default`` value is
    returned.
    """
    models = config.get("models", {})
    return models.get(agent_role, models.get("default", DEFAULT_CONFIG["models"]["default"]))


def get_effective_context_budget(config: Dict[str, Any]) -> int:
    """Return the effective context-budget in tokens.

    If ``context_budget_override`` is set (non-``None``), that value is
    returned directly.  Otherwise the budget is computed as the smallest
    context window among all configured models minus 20 000 tokens of
    overhead.
    """
    override = config.get("context_budget_override")
    if override is not None:
        return int(override)

    models_section = config.get("models", DEFAULT_CONFIG["models"])
    # Gather all model names from the models section.
    model_names = list(models_section.values())

    if not model_names:
        # Fallback: use the default model's window.
        default_model = DEFAULT_CONFIG["models"]["default"]
        return _MODEL_CONTEXT_WINDOWS.get(default_model, 200_000) - _CONTEXT_BUDGET_OVERHEAD

    # Find the smallest context window among the configured models.
    smallest_window: Optional[int] = None
    for model_name in model_names:
        window = _MODEL_CONTEXT_WINDOWS.get(model_name, 200_000)
        if smallest_window is None or window < smallest_window:
            smallest_window = window

    assert smallest_window is not None
    return smallest_window - _CONTEXT_BUDGET_OVERHEAD


def write_default_config(project_root: Path) -> Path:
    """Write ``DEFAULT_CONFIG`` as formatted JSON to ``svp_config.json``.

    Returns the ``Path`` to the written file.
    """
    assert project_root.is_dir(), "Project root must be an existing directory"

    config_path = project_root / "svp_config.json"
    config_path.write_text(
        json.dumps(DEFAULT_CONFIG, indent=2) + "\n",
        encoding="utf-8",
    )
    return config_path

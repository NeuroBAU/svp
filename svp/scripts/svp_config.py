import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

# Module-level constants

ARTIFACT_FILENAMES: Dict[str, str] = {
    "pipeline_state": "pipeline_state.json",
    "project_profile": "project_profile.json",
    "toolchain": "toolchain.json",
    "stakeholder_spec": "specs/stakeholder_spec.md",
    "blueprint_dir": "blueprint",
    "blueprint_prose": "blueprint/blueprint_prose.md",
    "blueprint_contracts": "blueprint/blueprint_contracts.md",
    "build_log": ".svp/build_log.jsonl",
    "task_prompt": ".svp/task_prompt.md",
    "gate_prompt": ".svp/gate_prompt.md",
    "last_status": ".svp/last_status.txt",
    "svp_config": "svp_config.json",
    "assembly_map": ".svp/assembly_map.json",
    "triage_result": ".svp/triage_result.json",
    "oracle_run_ledger": ".svp/oracle_run_ledger.json",
    "lessons_learned": "references/svp_2_1_lessons_learned.md",
}

DEFAULT_CONFIG: Dict[str, Any] = {
    "iteration_limit": 3,
    "models": {
        "default": "claude-opus-4-6",
    },
    "context_budget_override": None,
    "context_budget_threshold": 65,
    "compaction_character_threshold": 200,
    "auto_save": True,
    "skip_permissions": True,
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-merge override into a copy of base. Override values win."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config(project_root: Path) -> Dict[str, Any]:
    """Read svp_config.json from project_root, deep-merge with DEFAULT_CONFIG.

    Raises FileNotFoundError if the config file is absent.
    """
    config_path = project_root / "svp_config.json"
    with open(config_path, "r") as f:
        user_config = json.load(f)
    return _deep_merge(DEFAULT_CONFIG, user_config)


def save_config(project_root: Path, config: Dict[str, Any]) -> None:
    """Write config to svp_config.json at project_root as formatted JSON.

    Uses atomic write (write to temp file, then rename).
    """
    config_path = project_root / "svp_config.json"
    fd, tmp_path = tempfile.mkstemp(
        dir=str(project_root), suffix=".tmp", prefix=".svp_config_"
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(config, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, str(config_path))
    except BaseException:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def derive_env_name(project_root: Path) -> str:
    """Return the environment name derived from the project root directory name."""
    return f"svp-{project_root.name}"


def get_blueprint_dir(project_root: Path) -> Path:
    """Return project_root / ARTIFACT_FILENAMES['blueprint_dir']."""
    return project_root / ARTIFACT_FILENAMES["blueprint_dir"]


def get_model_for_agent(
    agent_key: str,
    config: Dict[str, Any],
    profile: Dict[str, Any],
) -> str:
    """Return the model identifier for the given agent key.

    Precedence:
      1. profile["pipeline"]["agent_models"][agent_key]
      2. config["models"][agent_key]
      3. config["models"]["default"]
      4. Hardcoded fallback: "claude-opus-4-6"

    Never returns None.
    """
    # Check profile first (highest precedence)
    try:
        model = profile["pipeline"]["agent_models"][agent_key]
        if model is not None:
            return model
    except (KeyError, TypeError):
        pass

    # Check config agent-specific
    models = config.get("models", {})
    if agent_key in models and models[agent_key] is not None:
        return models[agent_key]

    # Check config default
    default_model = models.get("default")
    if default_model is not None:
        return default_model

    # Hardcoded fallback
    return "claude-opus-4-6"

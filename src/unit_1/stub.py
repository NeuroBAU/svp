import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

ARTIFACT_FILENAMES: Dict[str, str] = {
    "pipeline_state": ".svp/pipeline_state.json",
    "project_profile": "project_profile.json",
    "toolchain": "toolchain.json",
    "stakeholder_spec": "spec/stakeholder_spec.md",
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
    """Deep-merge override into base. Override values take precedence."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config(project_root: Path) -> Dict[str, Any]:
    config_path = project_root / ARTIFACT_FILENAMES["svp_config"]
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        user_config = json.load(f)
    return _deep_merge(DEFAULT_CONFIG, user_config)


def save_config(project_root: Path, config: Dict[str, Any]) -> None:
    config_path = project_root / ARTIFACT_FILENAMES["svp_config"]
    config_path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write: write to temp file in same directory, then rename
    fd, tmp_path = tempfile.mkstemp(
        dir=config_path.parent, suffix=".tmp", prefix=".svp_config_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, config_path)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def derive_env_name(project_root: Path) -> str:
    return f"svp-{project_root.name}"


def get_blueprint_dir(project_root: Path) -> Path:
    return project_root / ARTIFACT_FILENAMES["blueprint_dir"]


def get_model_for_agent(
    agent_key: str, config: Dict[str, Any], profile: Dict[str, Any]
) -> str:
    # Tier 1: profile["pipeline"]["agent_models"][agent_key]
    try:
        model = profile["pipeline"]["agent_models"][agent_key]
        if model is not None:
            return model
    except (KeyError, TypeError):
        pass

    # Tier 2: config["models"][agent_key]
    try:
        model = config["models"][agent_key]
        if model is not None:
            return model
    except (KeyError, TypeError):
        pass

    # Tier 3: config["models"]["default"]
    return config["models"]["default"]

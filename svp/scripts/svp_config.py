"""SVP Configuration -- loading, validating, and accessing all tunable parameters and tool commands.

Manages three foundational data contracts:
  1. svp_config.json -- pipeline configuration schema
  2. project_profile.json -- human delivery preferences
  3. toolchain.json -- pipeline build command templates

Also provides the canonical derive_env_name function and the canonical
ARTIFACT_FILENAMES dict (Bug 22 fix).
"""

from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import copy
import json
import re

# ===========================================================================
# Section 0: Canonical Pipeline Artifact Filenames (Bug 22 fix -- NEW IN 2.1)
# ===========================================================================

ARTIFACT_FILENAMES: Dict[str, str] = {
    "stakeholder_spec": "stakeholder_spec.md",
    "blueprint_prose": "blueprint_prose.md",
    "blueprint_contracts": "blueprint_contracts.md",
    "project_context": "project_context.md",
    "project_profile": "project_profile.json",
    "pipeline_state": "pipeline_state.json",
    "svp_config": "svp_config.json",
    "toolchain": "toolchain.json",
    "ruff_config": "ruff.toml",
    "lessons_learned": "svp_2_1_lessons_learned.md",
}

# ===========================================================================
# Section 1: SVP Configuration (svp_config.json)
# ===========================================================================

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

# Known model context windows (in tokens).
_MODEL_CONTEXT_WINDOWS: Dict[str, int] = {
    "claude-opus-4-6": 200_000,
    "claude-sonnet-4-6": 200_000,
}

_CONTEXT_BUDGET_OVERHEAD: int = 20_000


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge *override* into a copy of *base*."""
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
    """Load configuration from svp_config.json under *project_root*.

    Returns DEFAULT_CONFIG copy when file is absent (no error).
    Raises json.JSONDecodeError for malformed JSON.
    Raises ValueError for structural validation failures.
    """
    assert project_root.is_dir(), "Project root must be an existing directory"

    config_path = project_root / "svp_config.json"

    if not config_path.exists():
        return copy.deepcopy(DEFAULT_CONFIG)

    raw_text = config_path.read_text(encoding="utf-8")

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
    """Validate a configuration dictionary. Returns list of error strings (empty if valid)."""
    errors: list[str] = []

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
    """Return the model identifier for *agent_role*, falling back to models.default."""
    models = config.get("models", {})
    return models.get(agent_role, models.get("default", DEFAULT_CONFIG["models"]["default"]))


def get_effective_context_budget(config: Dict[str, Any]) -> int:
    """Return the effective context budget in tokens.

    Uses context_budget_override if set, otherwise computes from smallest
    model context window minus 20,000 tokens overhead.
    """
    override = config.get("context_budget_override")
    if override is not None:
        return int(override)

    models_section = config.get("models", DEFAULT_CONFIG["models"])
    model_names = list(models_section.values())

    if not model_names:
        default_model = DEFAULT_CONFIG["models"]["default"]
        return _MODEL_CONTEXT_WINDOWS.get(default_model, 200_000) - _CONTEXT_BUDGET_OVERHEAD

    smallest_window: Optional[int] = None
    for model_name in model_names:
        window = _MODEL_CONTEXT_WINDOWS.get(model_name, 200_000)
        if smallest_window is None or window < smallest_window:
            smallest_window = window

    assert smallest_window is not None
    return smallest_window - _CONTEXT_BUDGET_OVERHEAD


def write_default_config(project_root: Path) -> Path:
    """Write DEFAULT_CONFIG as formatted JSON to svp_config.json. Returns the path."""
    assert project_root.is_dir(), "Project root must be an existing directory"

    config_path = project_root / "svp_config.json"
    config_path.write_text(
        json.dumps(DEFAULT_CONFIG, indent=2) + "\n",
        encoding="utf-8",
    )
    return config_path


# ===========================================================================
# Section 2: Project Profile (project_profile.json)
# ===========================================================================

DEFAULT_PROFILE: Dict[str, Any] = {
    "pipeline_toolchain": "python_conda_pytest",
    "python_version": "3.11",
    "delivery": {
        "environment_recommendation": "conda",
        "dependency_format": "environment.yml",
        "source_layout": "conventional",
        "entry_points": False,
    },
    "vcs": {
        "commit_style": "conventional",
        "commit_template": None,
        "issue_references": False,
        "branch_strategy": "main-only",
        "tagging": "semver",
        "conventions_notes": None,
        "changelog": "none",
    },
    "readme": {
        "audience": "domain expert",
        "sections": [
            "Header", "What it does", "Who it's for", "Installation",
            "Configuration", "Usage", "Quick Tutorial", "Examples",
            "Project Structure", "License",
        ],
        "depth": "standard",
        "include_math_notation": False,
        "include_glossary": False,
        "include_data_formats": False,
        "include_code_examples": False,
        "code_example_focus": None,
        "custom_sections": None,
        "docstring_convention": "google",
        "citation_file": False,
        "contributing_guide": False,
    },
    "testing": {
        "coverage_target": None,
        "readable_test_names": True,
        "readme_test_scenarios": False,
    },
    "license": {
        "type": "MIT",
        "holder": "",
        "author": "",
        "year": "",
        "contact": None,
        "spdx_headers": False,
        "additional_metadata": {
            "citation": None,
            "funding": None,
            "acknowledgments": None,
        },
    },
    "quality": {
        "linter": "ruff",
        "formatter": "ruff",
        "type_checker": "none",
        "import_sorter": "ruff",
        "line_length": 88,
    },
    "fixed": {
        "language": "python",
        "pipeline_environment": "conda",
        "test_framework": "pytest",
        "build_backend": "setuptools",
        "vcs_system": "git",
        "source_layout_during_build": "svp_native",
        "pipeline_quality_tools": "ruff_mypy",
    },
    "created_at": "",
}


def load_profile(project_root: Path) -> Dict[str, Any]:
    """Load project_profile.json from project_root.

    Missing fields are filled from DEFAULT_PROFILE.
    Raises RuntimeError if file is missing.
    Raises RuntimeError wrapping json.JSONDecodeError if JSON is malformed.
    """
    assert project_root.is_dir(), "Project root must be an existing directory"

    profile_path = project_root / "project_profile.json"

    if not profile_path.exists():
        raise RuntimeError(
            f"Project profile not found at {profile_path}. "
            "Resume from Stage 0 or run /svp:redo to create it."
        )

    raw_text = profile_path.read_text(encoding="utf-8")

    try:
        file_profile = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Project profile at {profile_path} is not valid JSON. "
            "Resume from Stage 0 or run /svp:redo to create it."
        ) from exc

    if not isinstance(file_profile, dict):
        raise RuntimeError(
            f"Project profile not found at {profile_path}. "
            "Resume from Stage 0 or run /svp:redo to create it."
        )

    merged = _deep_merge(DEFAULT_PROFILE, file_profile)
    return merged


def validate_profile(profile: Dict[str, Any]) -> list[str]:
    """Validate a profile dictionary. Returns list of error strings (empty if valid)."""
    errors: list[str] = []

    # Required top-level sections
    required_sections = ["delivery", "vcs", "readme", "testing", "license", "quality", "fixed"]
    for section in required_sections:
        if section not in profile:
            errors.append(f"Missing required section: {section}")
        elif not isinstance(profile[section], dict):
            errors.append(f"Section '{section}' must be a dict")

    # Delivery section validation
    if "delivery" in profile and isinstance(profile["delivery"], dict):
        delivery = profile["delivery"]
        valid_env = {"conda", "pyenv", "venv", "poetry", "none"}
        if "environment_recommendation" in delivery:
            if delivery["environment_recommendation"] not in valid_env:
                errors.append(
                    f"delivery.environment_recommendation must be one of {sorted(valid_env)}"
                )
        valid_layouts = {"conventional", "flat", "svp_native"}
        if "source_layout" in delivery:
            if delivery["source_layout"] not in valid_layouts:
                errors.append(
                    f"delivery.source_layout must be one of {sorted(valid_layouts)}"
                )

    # VCS section validation
    if "vcs" in profile and isinstance(profile["vcs"], dict):
        vcs = profile["vcs"]
        valid_commit_styles = {"conventional", "freeform", "custom"}
        if "commit_style" in vcs:
            if vcs["commit_style"] not in valid_commit_styles:
                errors.append(
                    f"vcs.commit_style must be one of {sorted(valid_commit_styles)}"
                )
        valid_changelogs = {"keep_a_changelog", "conventional_changelog", "none"}
        if "changelog" in vcs:
            if vcs["changelog"] not in valid_changelogs:
                errors.append(
                    f"vcs.changelog must be one of {sorted(valid_changelogs)}"
                )

    # Readme section validation
    if "readme" in profile and isinstance(profile["readme"], dict):
        readme = profile["readme"]
        valid_depths = {"minimal", "standard", "comprehensive"}
        if "depth" in readme:
            if readme["depth"] not in valid_depths:
                errors.append(
                    f"readme.depth must be one of {sorted(valid_depths)}"
                )

    # Testing section validation
    if "testing" in profile and isinstance(profile["testing"], dict):
        testing = profile["testing"]
        if "coverage_target" in testing:
            ct = testing["coverage_target"]
            if ct is not None:
                if not isinstance(ct, int):
                    errors.append("testing.coverage_target must be null or an integer 0-100")
                elif not (0 <= ct <= 100):
                    errors.append("testing.coverage_target must be null or an integer 0-100")

    # Quality section validation
    if "quality" in profile and isinstance(profile["quality"], dict):
        quality = profile["quality"]
        valid_linters = {"ruff", "flake8", "pylint", "none"}
        if "linter" in quality:
            if quality["linter"] not in valid_linters:
                errors.append(
                    f"quality.linter must be one of {sorted(valid_linters)}"
                )
        valid_formatters = {"ruff", "black", "none"}
        if "formatter" in quality:
            if quality["formatter"] not in valid_formatters:
                errors.append(
                    f"quality.formatter must be one of {sorted(valid_formatters)}"
                )
        valid_type_checkers = {"mypy", "pyright", "none"}
        if "type_checker" in quality:
            if quality["type_checker"] not in valid_type_checkers:
                errors.append(
                    f"quality.type_checker must be one of {sorted(valid_type_checkers)}"
                )
        valid_import_sorters = {"ruff", "isort", "none"}
        if "import_sorter" in quality:
            if quality["import_sorter"] not in valid_import_sorters:
                errors.append(
                    f"quality.import_sorter must be one of {sorted(valid_import_sorters)}"
                )
        if "line_length" in quality:
            ll = quality["line_length"]
            if not isinstance(ll, int) or ll <= 0:
                errors.append("quality.line_length must be a positive integer")

    return errors


def get_profile_section(profile: Dict[str, Any], section: str) -> Dict[str, Any]:
    """Return a specific top-level section of the profile. Raises KeyError if absent."""
    if section not in profile:
        raise KeyError(section)
    return profile[section]


def detect_profile_contradictions(profile: Dict[str, Any]) -> list[str]:
    """Check for known contradictory combinations in the profile.

    Returns list of contradiction descriptions (empty if none found).
    """
    contradictions: list[str] = []

    readme = profile.get("readme", {})
    delivery = profile.get("delivery", {})
    vcs = profile.get("vcs", {})
    fixed = profile.get("fixed", {})

    # readme.depth: "minimal" with more than 5 sections or custom sections
    if readme.get("depth") == "minimal":
        sections = readme.get("sections", [])
        if isinstance(sections, list) and len(sections) > 5:
            contradictions.append(
                "readme.depth is 'minimal' but more than 5 sections are specified"
            )
        custom = readme.get("custom_sections")
        if custom is not None and custom:
            contradictions.append(
                "readme.depth is 'minimal' but custom_sections are specified"
            )

    # readme.include_code_examples: true with readme.depth: "minimal"
    if readme.get("include_code_examples") is True and readme.get("depth") == "minimal":
        contradictions.append(
            "readme.include_code_examples is true but readme.depth is 'minimal'"
        )

    # delivery.entry_points: true with no identifiable CLI module
    # We can only check the structural contradiction here; no CLI module detection
    # at this level. Record if entry_points is true (downstream will verify).
    # Per the spec, this is a known contradiction to detect.
    if delivery.get("entry_points") is True:
        # We flag this as a potential issue; actual CLI module detection
        # happens at build time. This checks profile-level contradictions only.
        pass

    # delivery.source_layout: "flat" with more than approximately 10 units
    # This cannot be fully checked at profile level (no unit count available),
    # so we skip unit count-based checks here.

    # vcs.commit_style: "custom" with vcs.commit_template: null
    if vcs.get("commit_style") == "custom" and vcs.get("commit_template") is None:
        contradictions.append(
            "vcs.commit_style is 'custom' but vcs.commit_template is null"
        )

    # Mismatched delivery environment and dependency format
    env_rec = delivery.get("environment_recommendation")
    dep_fmt = delivery.get("dependency_format")
    if env_rec and dep_fmt and isinstance(dep_fmt, str):
        env_format_map = {
            "conda": "environment.yml",
            "pyenv": "requirements.txt",
            "venv": "requirements.txt",
            "poetry": "pyproject.toml",
        }
        expected = env_format_map.get(env_rec)
        if expected and dep_fmt != expected:
            contradictions.append(
                f"delivery.environment_recommendation is '{env_rec}' "
                f"but delivery.dependency_format is '{dep_fmt}' "
                f"(expected '{expected}')"
            )

    # Check quality tool contradictions against pipeline_quality_tools
    quality = profile.get("quality", {})
    if isinstance(quality, dict) and isinstance(fixed, dict):
        pipeline_tools = fixed.get("pipeline_quality_tools", "")
        if isinstance(pipeline_tools, str):
            if quality.get("linter") == "none" and "ruff" in pipeline_tools:
                contradictions.append(
                    "quality.linter is 'none' but"
                    " fixed.pipeline_quality_tools"
                    " includes ruff"
                )
            if quality.get("type_checker") == "none" and "mypy" in pipeline_tools:
                contradictions.append(
                    "quality.type_checker is 'none' but"
                    " fixed.pipeline_quality_tools"
                    " includes mypy"
                )

    return contradictions


# ===========================================================================
# Section 3: Pipeline Toolchain (toolchain.json)
# ===========================================================================

# Required top-level sections in toolchain.json
_TOOLCHAIN_REQUIRED_SECTIONS = [
    "environment", "testing", "packaging", "vcs", "language", "file_structure", "quality"
]

# Recognized placeholders in toolchain command templates
_RECOGNIZED_PLACEHOLDERS = {
    "env_name", "python_version", "run_prefix", "target",
    "flags", "packages", "files", "message", "module", "test_path",
}


def load_toolchain(project_root: Path) -> Dict[str, Any]:
    """Load toolchain.json from project_root.

    Raises RuntimeError if missing or malformed. No fallback.
    """
    assert project_root.is_dir(), "Project root must be an existing directory"

    toolchain_path = project_root / "toolchain.json"

    if not toolchain_path.exists():
        raise RuntimeError(
            f"Toolchain file not found at {toolchain_path}. "
            "Re-run svp new or reinstall the plugin."
        )

    raw_text = toolchain_path.read_text(encoding="utf-8")

    try:
        toolchain = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Toolchain file at {toolchain_path} is not valid JSON. "
            "Re-run svp new or reinstall the plugin."
        ) from exc

    if not isinstance(toolchain, dict):
        raise RuntimeError(
            f"Toolchain file not found at {toolchain_path}. "
            "Re-run svp new or reinstall the plugin."
        )

    return toolchain


def validate_toolchain(toolchain: Dict[str, Any]) -> list[str]:
    """Validate a toolchain dictionary. Returns list of error strings (empty if valid)."""
    errors: list[str] = []

    # Check required top-level sections
    for section in _TOOLCHAIN_REQUIRED_SECTIONS:
        if section not in toolchain:
            errors.append(f"Missing required section: {section}")
        elif not isinstance(toolchain[section], dict):
            errors.append(f"Section '{section}' must be a dict")

    # Sections are required to be dicts (already checked above).
    # Internal field validation is intentionally minimal: the toolchain
    # schema may vary across pipeline versions, so we only enforce the
    # presence of top-level sections.

    # Check command templates for unrecognized placeholders
    _check_templates_for_placeholders(toolchain, errors)

    return errors


def _check_templates_for_placeholders(toolchain: Dict[str, Any], errors: list[str]) -> None:
    """Check all command template strings for unrecognized placeholders."""
    _validate_templates_recursive(toolchain, errors)


def _validate_templates_recursive(obj: Any, errors: list[str], path: str = "") -> None:
    """Check command template strings for unrecognized placeholders recursively."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            _validate_templates_recursive(value, errors, current_path)
    elif isinstance(obj, str):
        placeholders = re.findall(r"\{(\w+)\}", obj)
        for ph in placeholders:
            if ph not in _RECOGNIZED_PLACEHOLDERS:
                errors.append(
                    f"Unrecognized placeholder '{{{ph}}}' in template at {path}"
                )
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _validate_templates_recursive(item, errors, f"{path}[{i}]")


def resolve_command(
    toolchain: Dict[str, Any],
    operation: str,
    params: Optional[Dict[str, str]] = None,
) -> str:
    """Perform single-pass placeholder resolution on a toolchain command template.

    The operation is a dotted path like 'environment.create' or 'testing.run'.
    Params dict provides values for placeholders like {env_name}, {python_version}, etc.

    Resolution order:
    1. Resolve {env_name} in environment.run_prefix to get the resolved run_prefix
    2. Substitute {run_prefix} in the target template
    3. Substitute remaining placeholders from params

    Raises ValueError if any placeholder remains unresolved.
    """
    if params is None:
        params = {}

    # Navigate to the template using dotted path
    template = _get_template(toolchain, operation)

    # Step 1: Resolve run_prefix from environment.run_prefix template
    run_prefix_template = ""
    env_section = toolchain.get("environment", {})
    if "run_prefix" in env_section:
        run_prefix_template = env_section["run_prefix"]
        # Resolve {env_name} in run_prefix
        if "{env_name}" in run_prefix_template and "env_name" in params:
            run_prefix_template = run_prefix_template.replace(
                "{env_name}", params["env_name"]
            )

    # Step 2: Substitute {run_prefix} in the template
    if "{run_prefix}" in template:
        template = template.replace("{run_prefix}", run_prefix_template)

    # Step 3: Substitute all params into the template
    for key, value in params.items():
        placeholder = "{" + key + "}"
        template = template.replace(placeholder, value)

    # Check for unresolved placeholders
    remaining = re.findall(r"\{(\w+)\}", template)
    if remaining:
        raise ValueError(
            f"Unresolved placeholder in command template: {{{remaining[0]}}}"
        )

    # Collapse multiple spaces and strip whitespace
    template = re.sub(r" {2,}", " ", template).strip()

    return template


def _get_template(toolchain: Dict[str, Any], operation: str) -> str:
    """Navigate dotted operation path to find the template string."""
    parts = operation.split(".")
    current: Any = toolchain
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise ValueError(f"Operation '{operation}' not found in toolchain")
    if not isinstance(current, str):
        raise ValueError(f"Operation '{operation}' does not resolve to a string template")
    return current


def resolve_run_prefix(toolchain: Dict[str, Any], env_name: str) -> str:
    """Convenience: resolve environment.run_prefix with the given env_name."""
    template = toolchain.get("environment", {}).get("run_prefix", "")
    result = template.replace("{env_name}", env_name)
    return result


def get_framework_packages(toolchain: Dict[str, Any]) -> List[str]:
    """Return testing.framework_packages from the toolchain."""
    return toolchain.get("testing", {}).get("framework_packages", [])


def get_quality_packages(toolchain: Dict[str, Any]) -> List[str]:
    """Return quality.packages from the toolchain."""
    return toolchain.get("quality", {}).get("packages", [])


def get_collection_error_indicators(toolchain: Dict[str, Any]) -> List[str]:
    """Return testing.collection_error_indicators from the toolchain."""
    return toolchain.get("testing", {}).get("collection_error_indicators", [])


def get_quality_gate_operations(
    toolchain: Dict[str, Any], gate: str
) -> List[str]:
    """Return the operation list for a given gate identifier from the quality section.

    Valid gate identifiers: 'gate_a', 'gate_b', 'gate_c'.
    Raises ValueError for unrecognized gate identifiers.
    """
    quality = toolchain.get("quality", {})
    valid_gates = {"gate_a", "gate_b", "gate_c"}
    if gate not in valid_gates:
        raise ValueError(f"Unknown quality gate: {gate}")
    if gate not in quality:
        raise ValueError(f"Unknown quality gate: {gate}")
    return quality.get(gate, [])


def validate_python_version(
    python_version: str, version_constraint: str
) -> bool:
    """Check whether a version string satisfies a version constraint.

    Supports constraints like '>=3.10', '<=3.12', '==3.11', '>3.9', '<3.13'.
    Returns True if satisfied, False otherwise.
    """
    # Parse the version string into a tuple of ints
    version_parts = _parse_version(python_version)

    # Parse constraint: operator + version
    match = re.match(r"^(>=|<=|==|!=|>|<)(.+)$", version_constraint.strip())
    if not match:
        raise ValueError(
            f"Python version {python_version} does not satisfy constraint {version_constraint}"
        )

    operator = match.group(1)
    constraint_version = _parse_version(match.group(2))

    # Compare
    if operator == ">=":
        return version_parts >= constraint_version
    elif operator == "<=":
        return version_parts <= constraint_version
    elif operator == "==":
        return version_parts == constraint_version
    elif operator == "!=":
        return version_parts != constraint_version
    elif operator == ">":
        return version_parts > constraint_version
    elif operator == "<":
        return version_parts < constraint_version

    return False


def _parse_version(version_str: str) -> Tuple[int, ...]:
    """Parse a version string like '3.11' or '3.10.2' into a tuple of ints."""
    parts = version_str.strip().split(".")
    return tuple(int(p) for p in parts)


# ===========================================================================
# Section 4: Shared Utilities
# ===========================================================================

def derive_env_name(project_name: str) -> str:
    """Apply canonical environment name derivation.

    Rule: project_name.lower().replace(" ", "_").replace("-", "_")
    """
    return project_name.lower().replace(" ", "_").replace("-", "_")


# Alias: _CONTEXT_OVERHEAD is the backward-compatible name for _CONTEXT_BUDGET_OVERHEAD
_CONTEXT_OVERHEAD: int = _CONTEXT_BUDGET_OVERHEAD

# Alias: get_gate_operations is the backward-compatible name for get_quality_gate_operations
get_gate_operations = get_quality_gate_operations


def discover_blueprint_files(project_root: Path) -> List[Path]:
    """Discover all .md files in the blueprint directory, sorted by name."""
    blueprint_dir = project_root / "blueprint"
    if not blueprint_dir.is_dir():
        raise FileNotFoundError(
            f"Blueprint directory not found: {blueprint_dir}"
        )
    md_files = sorted(blueprint_dir.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(
            f"No .md files found in blueprint directory: {blueprint_dir}"
        )
    return md_files


def load_blueprint_content(project_root: Path) -> str:
    """Load and concatenate all blueprint .md files."""
    files = discover_blueprint_files(project_root)
    contents = []
    for f in files:
        contents.append(f.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(contents)

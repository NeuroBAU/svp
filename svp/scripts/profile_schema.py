"""Unit 3: Profile Schema.

Manages the language-keyed project profile schema, profile loading/validation
lifecycle, and language-aware accessor functions.
"""

import copy
import json
from pathlib import Path
from typing import Any, Dict, List

from svp_config import ARTIFACT_FILENAMES
from language_registry import LANGUAGE_REGISTRY

# ---------------------------------------------------------------------------
# Valid archetypes
# ---------------------------------------------------------------------------

VALID_ARCHETYPES = {
    "python_project",
    "r_project",
    "claude_code_plugin",
    "mixed",
    "svp_language_extension",
    "svp_architectural",
}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_PROFILE: Dict[str, Any] = {
    "pipeline_toolchain": "python_conda_pytest",
    "archetype": "python_project",
    "language": {
        "primary": "python",
        "components": [],
        "communication": {},
        "notebooks": None,
    },
    # Bug S3-164: project-level capability flag controlling whether downstream
    # agents are primed for statistical / data-analysis rigor. Drives Stage 1
    # stakeholder primer, Stage 2 blueprint primer + specialist reviewer
    # dispatch, and Stage 3 test-agent primer. Silent default to False keeps
    # backward compatibility for profiles that pre-date this field.
    "requires_statistical_analysis": False,
    "delivery": {
        "python": copy.deepcopy(LANGUAGE_REGISTRY["python"]["default_delivery"]),
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
        "type": "Apache-2.0",
        "holder": "",
        "author": "",
        "year": "",
        "contact": None,
        "spdx_headers": True,
        "additional_metadata": {
            "citation": None,
            "funding": None,
            "acknowledgments": None,
        },
    },
    "quality": {
        "python": copy.deepcopy(LANGUAGE_REGISTRY["python"]["default_quality"]),
    },
    "pipeline": {
        "agent_models": {},
        "context_budget_override": None,
        "context_budget_threshold": 65,
    },
    "fixed": {
        "pipeline_environment": "conda",
        "test_framework": "pytest",
        "build_backend": "setuptools",
        "vcs_system": "git",
        "source_layout_during_build": "svp_native",
        "pipeline_quality_tools": "ruff_mypy",
    },
    "created_at": "",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-merge override into a copy of base. Override values win."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _is_flat_section(section: Any) -> bool:
    """Check if a delivery/quality section is flat (not language-keyed).

    A flat section is a dict where at least one value is NOT a dict,
    indicating it contains tool settings directly rather than being
    keyed by language name.
    """
    if not isinstance(section, dict):
        return False
    if not section:
        return False
    # If any value is not a dict, the section is flat (not language-keyed)
    return any(not isinstance(v, dict) for v in section.values())


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def load_profile(project_root: Path) -> Dict[str, Any]:
    """Read project_profile.json from project_root, deep-merge with DEFAULT_PROFILE.

    SVP 2.1 migration: if delivery or quality sections are flat (not
    language-keyed), wraps them under {primary_language}.

    Derives is_svp_build and self_build_scope from archetype.

    Raises FileNotFoundError if the profile file is absent.
    """
    profile_path = project_root / ARTIFACT_FILENAMES["project_profile"]
    with open(profile_path, "r") as f:
        user_profile = json.load(f)

    # SVP 2.1 migration: wrap flat delivery/quality under primary language key
    primary_language = (
        user_profile.get("language", {}).get("primary", None)
        or DEFAULT_PROFILE["language"]["primary"]
    )

    if "delivery" in user_profile and _is_flat_section(user_profile["delivery"]):
        user_profile["delivery"] = {primary_language: user_profile["delivery"]}

    if "quality" in user_profile and _is_flat_section(user_profile["quality"]):
        user_profile["quality"] = {primary_language: user_profile["quality"]}

    # Deep-merge with defaults
    profile = _deep_merge(DEFAULT_PROFILE, user_profile)

    # Derive is_svp_build and self_build_scope from archetype
    archetype = profile.get("archetype", "python_project")
    if archetype == "svp_language_extension":
        profile["is_svp_build"] = True
        profile["self_build_scope"] = "language_extension"
    elif archetype == "svp_architectural":
        profile["is_svp_build"] = True
        profile["self_build_scope"] = "architectural"
    else:
        profile["is_svp_build"] = False
        profile["self_build_scope"] = None

    return profile


def validate_profile(
    profile: Dict[str, Any],
    language_registry: Dict[str, Dict[str, Any]],
) -> List[str]:
    """Validate a profile against the language registry.

    Checks archetype validity, language.primary in registry, tool choices
    against registry valid sets, mixed-archetype constraints, and plugin
    constraints.

    Returns a list of violation strings (empty if valid).
    """
    errors: List[str] = []

    # Check archetype in valid set
    archetype = profile.get("archetype")
    if archetype not in VALID_ARCHETYPES:
        errors.append(f"Invalid archetype: {archetype}")

    # Check language.primary is in registry
    language = profile.get("language", {})
    primary = language.get("primary")
    if primary not in language_registry:
        errors.append(f"Unknown primary language: {primary}")

    # Collect all project languages (primary + secondary if present)
    project_langs = set()
    if primary:
        project_langs.add(primary)
    secondary = language.get("secondary")
    if secondary:
        project_langs.add(secondary)

    # Validate tool choices in delivery sections against registry
    delivery = profile.get("delivery", {})
    for lang_key, lang_delivery in delivery.items():
        if lang_key not in language_registry:
            continue
        reg = language_registry[lang_key]

        # Component-only languages should not have delivery configs
        if reg.get("is_component_only", False):
            errors.append(
                f"Component language {lang_key} cannot have delivery configuration"
            )
            continue

        if not isinstance(lang_delivery, dict):
            continue

        # Validate source_layout
        if "source_layout" in lang_delivery and "valid_source_layouts" in reg:
            if lang_delivery["source_layout"] not in reg["valid_source_layouts"]:
                errors.append(
                    f"Invalid source_layout for {lang_key}: "
                    f"{lang_delivery['source_layout']}"
                )

    # Validate tool choices in quality sections against registry
    quality = profile.get("quality", {})
    for lang_key, lang_quality in quality.items():
        if lang_key not in language_registry:
            continue
        reg = language_registry[lang_key]

        # Component-only languages should not have quality configs
        if reg.get("is_component_only", False):
            errors.append(
                f"Component language {lang_key} cannot have quality configuration"
            )
            continue

        if not isinstance(lang_quality, dict):
            continue

        # Validate linter
        if "linter" in lang_quality and "valid_linters" in reg:
            if lang_quality["linter"] not in reg["valid_linters"]:
                errors.append(
                    f"Invalid linter for {lang_key}: {lang_quality['linter']}"
                )

        # Validate formatter
        if "formatter" in lang_quality and "valid_formatters" in reg:
            if lang_quality["formatter"] not in reg["valid_formatters"]:
                errors.append(
                    f"Invalid formatter for {lang_key}: {lang_quality['formatter']}"
                )

        # Validate type_checker
        if "type_checker" in lang_quality and "valid_type_checkers" in reg:
            if lang_quality["type_checker"] not in reg["valid_type_checkers"]:
                errors.append(
                    f"Invalid type_checker for {lang_key}: "
                    f"{lang_quality['type_checker']}"
                )

    # Mixed archetype constraints
    if archetype == "mixed":
        # Collect all language keys from delivery and quality sections
        all_lang_keys = set(delivery.keys()) | set(quality.keys())
        # Filter to only those that are in the language registry and not component-only
        full_lang_keys = {
            k
            for k in all_lang_keys
            if k in language_registry
            and not language_registry[k].get("is_component_only", False)
        }

        if len(full_lang_keys) < 2:
            errors.append("Mixed archetype requires at least two languages")
        else:
            # Both languages must be in delivery and quality
            for lang in sorted(full_lang_keys):
                if lang not in delivery:
                    errors.append(
                        f"Mixed archetype: missing delivery config for language {lang}"
                    )
                if lang not in quality:
                    errors.append(
                        f"Mixed archetype: missing quality config for language {lang}"
                    )

            # Hard constraints: conda forced for both languages
            for lang in sorted(full_lang_keys):
                if lang in delivery:
                    lang_del = delivery[lang]
                    if isinstance(lang_del, dict):
                        env_rec = lang_del.get("environment_recommendation")
                        if env_rec is not None and env_rec != "conda":
                            errors.append(
                                f"Mixed archetype: {lang} "
                                f"environment_recommendation must be 'conda', "
                                f"got '{env_rec}'"
                            )
                        dep_fmt = lang_del.get("dependency_format")
                        if dep_fmt is not None and dep_fmt != "environment.yml":
                            errors.append(
                                f"Mixed archetype: {lang} "
                                f"dependency_format must be 'environment.yml', "
                                f"got '{dep_fmt}'"
                            )

    # Component language must have a host -- check language.components
    components = language.get("components", [])
    for comp in components:
        if comp in language_registry:
            comp_entry = language_registry[comp]
            if comp_entry.get("is_component_only", False):
                compatible = comp_entry.get("compatible_hosts", [])
                # Check that primary or secondary is a valid host
                has_host = any(lang in compatible for lang in project_langs)
                if not has_host:
                    errors.append(
                        f"Component language {comp} has no compatible host "
                        f"among project languages"
                    )

    return errors


def get_delivery_config(
    profile: Dict[str, Any],
    language: str,
    language_registry: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Return the delivery config for a specific language.

    Returns profile["delivery"][language] deep-merged with
    language_registry[language]["default_delivery"].

    Raises KeyError if language not in registry.
    """
    if language not in language_registry:
        raise KeyError(f"Unknown language: {language}")

    reg_defaults = language_registry[language].get("default_delivery", {})
    profile_delivery = profile.get("delivery", {}).get(language, {})

    return _deep_merge(reg_defaults, profile_delivery)


def get_quality_config(
    profile: Dict[str, Any],
    language: str,
    language_registry: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Return the quality config for a specific language.

    Returns profile["quality"][language] deep-merged with
    language_registry[language]["default_quality"].

    Raises KeyError if language not in registry.
    """
    if language not in language_registry:
        raise KeyError(f"Unknown language: {language}")

    reg_defaults = language_registry[language].get("default_quality", {})
    profile_quality = profile.get("quality", {}).get(language, {})

    return _deep_merge(reg_defaults, profile_quality)

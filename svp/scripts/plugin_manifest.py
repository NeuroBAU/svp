import json
from typing import Dict, Any, List
from pathlib import Path

# Plugin manifest schema
PLUGIN_JSON: Dict[str, Any] = {
    "name": "svp",
    "version": "1.2.0",
    "description": "Stratified Verification Pipeline - deterministically orchestrated software development",
}

# Marketplace catalog schema -- must match Claude Code's required format exactly.
# Required top-level fields: name (str), owner (obj), plugins (array).
# Each plugin entry requires: name, source (relative path with ./), description, version, author.
MARKETPLACE_JSON: Dict[str, Any] = {
    "name": "svp",
    "owner": {"name": "SVP"},
    "plugins": [
        {
            "name": "svp",
            "source": "./svp",
            "description": "Stratified Verification Pipeline \u2014 deterministically orchestrated, sequentially gated development for domain experts",
            "version": "1.2.0",
            "author": {"name": "SVP"},
        }
    ],
}


def validate_plugin_structure(repo_root: Path) -> List[str]:
    """Validate the plugin directory structure per spec Section 12.3.

    Checks:
    - marketplace.json exists at repo_root/.claude-plugin/marketplace.json
    - plugin.json exists at repo_root/svp/.claude-plugin/plugin.json
    - All component directories (agents, commands, hooks, scripts, skills)
      exist at repo_root/svp/ level
    - No component directories exist at repo_root/ level

    Returns a list of violation strings. If there are violations, raises
    ValueError with all violations listed.
    """
    violations: List[str] = []

    # Check marketplace.json at repository root
    marketplace_path = repo_root / ".claude-plugin" / "marketplace.json"
    if not marketplace_path.exists():
        violations.append(
            "Repository root must contain .claude-plugin/marketplace.json"
        )

    # Check plugin.json at plugin subdirectory
    plugin_path = repo_root / "svp" / ".claude-plugin" / "plugin.json"
    if not plugin_path.exists():
        violations.append(
            "Plugin subdirectory must contain .claude-plugin/plugin.json"
        )

    # Check component directories at plugin subdirectory root level
    components = ["agents", "commands", "hooks", "scripts", "skills"]
    for component in components:
        plugin_component = repo_root / "svp" / component
        if not plugin_component.is_dir():
            violations.append(
                f"{component}/ must be at svp/ root level"
            )

        root_component = repo_root / component
        if root_component.is_dir():
            violations.append(
                f"{component}/ must NOT be at repository root level"
            )

    return violations


# Deliverable content constants (written by Stage 5 assembly)
PLUGIN_JSON_CONTENT: str = json.dumps(PLUGIN_JSON, indent=2)
MARKETPLACE_JSON_CONTENT: str = json.dumps(MARKETPLACE_JSON, indent=2)

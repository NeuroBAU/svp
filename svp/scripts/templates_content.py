"""Template content constants for SVP project creation and tests.

These constants are used both for creating new SVP project workspace files
and as reference data in tests. They correspond to the template files in
the templates/ and toolchain_defaults/ directories plus bundled example content.
"""
from pathlib import Path
import json

_SCRIPTS_DIR = Path(__file__).parent
_REPO_ROOT = _SCRIPTS_DIR.parent

# Template file path constants
DEFAULT_CONFIG_TEMPLATE: str = "templates/svp_config_default.json"
INITIAL_STATE_TEMPLATE: str = "templates/pipeline_state_initial.json"
README_SVP_TEMPLATE: str = "templates/readme_svp.txt"
TOOLCHAIN_DEFAULT_TEMPLATE: str = "toolchain_defaults/python_conda_pytest.json"
RUFF_CONFIG_TEMPLATE: str = "toolchain_defaults/ruff.toml"


# --- File loaders ---

def _load_template(rel_path: str) -> str:
    """Load a template file from the scripts directory."""
    path = _SCRIPTS_DIR / rel_path
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _load_gol(filename: str) -> str:
    """Load a Game of Life example file."""
    # Try relative to _REPO_ROOT (workspace layout: src/unit_22/../examples/)
    gol_path = _REPO_ROOT / "examples" / "game-of-life" / filename
    if gol_path.exists():
        return gol_path.read_text(encoding="utf-8")
    # Try relative to repo root (delivered layout: svp/scripts/../../examples/)
    repo_root_path = _REPO_ROOT.parent / "examples" / "game-of-life" / filename
    if repo_root_path.exists():
        return repo_root_path.read_text(encoding="utf-8")
    return ""


# --- Deliverable content constants ---

# claude_md.py content
CLAUDE_MD_PY_CONTENT: str = _load_template("templates/claude_md.py")

# svp_config_default.json content
SVP_CONFIG_DEFAULT_JSON_CONTENT: str = _load_template("templates/svp_config_default.json")

# pipeline_state_initial.json content
PIPELINE_STATE_INITIAL_JSON_CONTENT: str = _load_template("templates/pipeline_state_initial.json")

# readme_svp.txt content
README_SVP_TXT_CONTENT: str = _load_template("templates/readme_svp.txt")

# Toolchain default JSON content
TOOLCHAIN_DEFAULT_JSON_CONTENT: str = _load_template("toolchain_defaults/python_conda_pytest.json")

# Ruff configuration TOML content (NEW IN 2.1)
RUFF_CONFIG_TOML_CONTENT: str = _load_template("toolchain_defaults/ruff.toml")

# Game of Life bundled example content
GOL_STAKEHOLDER_SPEC_CONTENT: str = _load_gol("stakeholder_spec.md")
GOL_BLUEPRINT_CONTENT: str = _load_gol("blueprint.md")
GOL_PROJECT_CONTEXT_CONTENT: str = _load_gol("project_context.md")

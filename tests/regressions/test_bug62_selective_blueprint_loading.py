"""Regression tests for Bug 62: selective blueprint loading per spec Section 3.16.

Verifies that:
- load_blueprint_contracts_only returns only contracts file content
- load_blueprint_prose_only returns only prose file content
- integration_test_author receives contracts only (not prose)
- git_repo_agent receives contracts only (not prose)
- help_agent receives prose only (not contracts)
- blueprint_checker still receives both files
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Ensure scripts/ is importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import prepare_task  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROSE_CONTENT = "# Blueprint Prose\nThis is the prose section."
CONTRACTS_CONTENT = "# Blueprint Contracts\nThese are the contract signatures."


@pytest.fixture
def blueprint_dir(tmp_path):
    """Create a temporary project with both blueprint files."""
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir()
    (bp_dir / "blueprint_prose.md").write_text(PROSE_CONTENT, encoding="utf-8")
    (bp_dir / "blueprint_contracts.md").write_text(CONTRACTS_CONTENT, encoding="utf-8")
    # Create minimal required files for _assemble_sections_for_agent
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    (specs_dir / "stakeholder_spec.md").write_text("# Spec", encoding="utf-8")
    (tmp_path / "project_context.md").write_text("# Context", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Tests for selective loading functions
# ---------------------------------------------------------------------------


def test_load_blueprint_contracts_only_returns_contracts(blueprint_dir):
    """Bug 62: load_blueprint_contracts_only must return only contracts."""
    result = prepare_task.load_blueprint_contracts_only(blueprint_dir)
    assert result == CONTRACTS_CONTENT
    assert "Prose" not in result


def test_load_blueprint_prose_only_returns_prose(blueprint_dir):
    """Bug 62: load_blueprint_prose_only must return only prose."""
    result = prepare_task.load_blueprint_prose_only(blueprint_dir)
    assert result == PROSE_CONTENT
    assert "Contracts" not in result


def test_load_blueprint_contracts_only_missing_file(tmp_path):
    """Returns empty string when contracts file does not exist."""
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir()
    (bp_dir / "blueprint_prose.md").write_text("prose only", encoding="utf-8")
    result = prepare_task.load_blueprint_contracts_only(tmp_path)
    assert result == ""


def test_load_blueprint_prose_only_missing_file(tmp_path):
    """Returns empty string when prose file does not exist."""
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir()
    (bp_dir / "blueprint_contracts.md").write_text("contracts only", encoding="utf-8")
    result = prepare_task.load_blueprint_prose_only(tmp_path)
    assert result == ""


# ---------------------------------------------------------------------------
# Tests for agent wiring
# ---------------------------------------------------------------------------


def test_integration_test_author_receives_contracts_only(blueprint_dir):
    """Bug 62: integration_test_author receives contracts, not prose."""
    sections = prepare_task._assemble_sections_for_agent(
        project_root=blueprint_dir,
        agent_type="integration_test_author",
        unit_number=None,
        ladder_position=None,
        hint_content=None,
        gate_id=None,
        extra_context=None,
        revision_mode=None,
    )
    assert "contract_signatures" in sections
    assert sections["contract_signatures"] == CONTRACTS_CONTENT
    # Must NOT contain prose content in any section
    for key, val in sections.items():
        if key != "stakeholder_spec":
            assert PROSE_CONTENT not in val, (
                f"Section '{key}' unexpectedly contains prose content"
            )


def test_git_repo_agent_receives_contracts_only(blueprint_dir):
    """Bug 62: git_repo_agent receives contracts only for blueprint."""
    # Need pipeline_state.json for delivered_repo_path
    import json
    state = {"delivered_repo_path": "/tmp/fake"}
    (blueprint_dir / "pipeline_state.json").write_text(
        json.dumps(state), encoding="utf-8"
    )
    sections = prepare_task._assemble_sections_for_agent(
        project_root=blueprint_dir,
        agent_type="git_repo_agent",
        unit_number=None,
        ladder_position=None,
        hint_content=None,
        gate_id=None,
        extra_context=None,
        revision_mode=None,
    )
    assert "blueprint" in sections
    assert sections["blueprint"] == CONTRACTS_CONTENT
    assert PROSE_CONTENT not in sections["blueprint"]


def test_help_agent_receives_prose_only(blueprint_dir):
    """Bug 62: help_agent receives prose only for blueprint."""
    sections = prepare_task._assemble_sections_for_agent(
        project_root=blueprint_dir,
        agent_type="help_agent",
        unit_number=None,
        ladder_position=None,
        hint_content=None,
        gate_id=None,
        extra_context=None,
        revision_mode=None,
    )
    assert "blueprint" in sections
    assert sections["blueprint"] == PROSE_CONTENT
    assert CONTRACTS_CONTENT not in sections["blueprint"]


def test_blueprint_checker_receives_both(blueprint_dir):
    """Bug 62: blueprint_checker must still receive both files."""
    sections = prepare_task._assemble_sections_for_agent(
        project_root=blueprint_dir,
        agent_type="blueprint_checker",
        unit_number=None,
        ladder_position=None,
        hint_content=None,
        gate_id=None,
        extra_context=None,
        revision_mode=None,
    )
    assert "blueprint" in sections
    # Both files should be present
    assert "Prose" in sections["blueprint"]
    assert "Contracts" in sections["blueprint"]

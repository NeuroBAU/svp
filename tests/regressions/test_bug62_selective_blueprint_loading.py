"""Regression tests for Bug 62: selective blueprint loading per spec Section 3.16.

Verifies that:
- load_blueprint_contracts_only returns only contracts file content
- load_blueprint_prose_only returns only prose file content
- integration_test_author receives contracts only (not prose)
- git_repo_agent receives contracts only (not prose)
- help_agent receives prose only (not contracts)
- blueprint_checker still receives both files

SVP 2.2 adaptation:
- _assemble_sections_for_agent removed from scripts/prepare_task.py;
  agent wiring tests are skipped (agent wiring is internal to
  src.unit_9.stub / src.unit_14.stub in SVP 2.2).
- load_blueprint_contracts_only / load_blueprint_prose_only take
  blueprint_dir (the blueprint/ directory itself, not project root).
"""

import sys
from pathlib import Path
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
    """Create a temporary project with both blueprint files.
    Returns the blueprint/ directory itself (not project root)."""
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir()
    (bp_dir / "blueprint_prose.md").write_text(PROSE_CONTENT, encoding="utf-8")
    (bp_dir / "blueprint_contracts.md").write_text(CONTRACTS_CONTENT, encoding="utf-8")
    return bp_dir


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
    result = prepare_task.load_blueprint_contracts_only(bp_dir)
    assert result == ""


def test_load_blueprint_prose_only_missing_file(tmp_path):
    """Returns empty string when prose file does not exist."""
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir()
    (bp_dir / "blueprint_contracts.md").write_text("contracts only", encoding="utf-8")
    result = prepare_task.load_blueprint_prose_only(bp_dir)
    assert result == ""



"""Regression tests for Bug 52: version_document() not wired into dispatch_gate_response.

Verifies that version_document() is actually called during REVISE gate dispatches,
creating history files in docs/history/.
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import copy

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from pipeline_state import PipelineState
from routing import dispatch_gate_response


def _make_state(stage="1", sub_stage=None):
    """Create a minimal PipelineState for testing."""
    return PipelineState.from_dict({
        "stage": stage,
        "sub_stage": sub_stage,
        "current_unit": 1,
        "total_units": 24,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iteration": 0,
        "verified_units": [],
        "pass_history": [],
        "log_references": {},
        "project_name": "test_project",
        "last_action": "",
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00",
    })


@pytest.fixture
def project_root(tmp_path):
    """Create a project root with spec and blueprint files."""
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    (specs_dir / "stakeholder_spec.md").write_text("# Spec v1\nOriginal content")

    blueprints_dir = tmp_path / "blueprints"
    blueprints_dir.mkdir()
    (blueprints_dir / "blueprint_prose.md").write_text("# Blueprint Prose v1")
    (blueprints_dir / "blueprint_contracts.md").write_text("# Blueprint Contracts v1")

    history_dir = tmp_path / "docs" / "history"
    history_dir.mkdir(parents=True)

    # Create .svp dir with last_status.txt
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir()
    (svp_dir / "last_status.txt").write_text("")

    # Create svp_config.json
    import json
    (tmp_path / "svp_config.json").write_text(json.dumps({"iteration_limit": 3}))

    # Create pipeline_state.json
    (tmp_path / "pipeline_state.json").write_text(json.dumps({
        "stage": "1", "sub_stage": None, "current_unit": 1,
        "total_units": 24, "fix_ladder_position": None,
        "red_run_retries": 0, "alignment_iteration": 0,
        "verified_units": [], "pass_history": [], "log_references": {},
        "project_name": "test", "last_action": "",
        "debug_session": None, "debug_history": [],
        "redo_triggered_from": None, "delivered_repo_path": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00",
    }))

    return tmp_path


class TestGate11SpecRevise:
    """Gate 1.1 REVISE must version stakeholder_spec.md."""

    def test_revise_creates_history_file(self, project_root):
        state = _make_state(stage="1")
        dispatch_gate_response(state, "gate_1_1_spec_draft", "REVISE", project_root)
        history_dir = project_root / "docs" / "history"
        versioned = list(history_dir.glob("stakeholder_spec_v*.md"))
        assert len(versioned) >= 1, "REVISE should create a versioned copy of the spec"

    def test_revise_creates_diff_file(self, project_root):
        state = _make_state(stage="1")
        dispatch_gate_response(state, "gate_1_1_spec_draft", "REVISE", project_root)
        history_dir = project_root / "docs" / "history"
        diffs = list(history_dir.glob("stakeholder_spec_v*_diff.md"))
        assert len(diffs) >= 1, "REVISE should create a diff summary"


class TestGate12SpecRevise:
    """Gate 1.2 REVISE must version stakeholder_spec.md."""

    def test_revise_creates_history_file(self, project_root):
        state = _make_state(stage="1")
        dispatch_gate_response(state, "gate_1_2_spec_post_review", "REVISE", project_root)
        history_dir = project_root / "docs" / "history"
        versioned = list(history_dir.glob("stakeholder_spec_v*.md"))
        assert len(versioned) >= 1


class TestGate21BlueprintRevise:
    """Gate 2.1 REVISE must version blueprint prose and contracts."""

    def test_revise_versions_both_blueprint_files(self, project_root):
        state = _make_state(stage="2")
        dispatch_gate_response(state, "gate_2_1_blueprint_approval", "REVISE", project_root)
        history_dir = project_root / "docs" / "history"
        prose = list(history_dir.glob("blueprint_prose_v*.md"))
        contracts = list(history_dir.glob("blueprint_contracts_v*.md"))
        assert len(prose) >= 1, "REVISE should version blueprint_prose.md"
        assert len(contracts) >= 1, "REVISE should version blueprint_contracts.md"


class TestGate22BlueprintRevise:
    """Gate 2.2 REVISE must version blueprint prose and contracts."""

    def test_revise_versions_both_blueprint_files(self, project_root):
        state = _make_state(stage="2")
        dispatch_gate_response(state, "gate_2_2_blueprint_post_review", "REVISE", project_root)
        history_dir = project_root / "docs" / "history"
        prose = list(history_dir.glob("blueprint_prose_v*.md"))
        contracts = list(history_dir.glob("blueprint_contracts_v*.md"))
        assert len(prose) >= 1
        assert len(contracts) >= 1


class TestGate23ReviseSpec:
    """Gate 2.3 REVISE SPEC must version stakeholder_spec.md."""

    def test_revise_spec_creates_history(self, project_root):
        state = _make_state(stage="2")
        dispatch_gate_response(state, "gate_2_3_alignment_exhausted", "REVISE SPEC", project_root)
        history_dir = project_root / "docs" / "history"
        versioned = list(history_dir.glob("stakeholder_spec_v*.md"))
        assert len(versioned) >= 1


class TestGate32FixBlueprint:
    """Gate 3.2 FIX BLUEPRINT must version blueprint files."""

    def test_fix_blueprint_versions_blueprint(self, project_root):
        state = _make_state(stage="3")
        dispatch_gate_response(state, "gate_3_2_diagnostic_decision", "FIX BLUEPRINT", project_root)
        history_dir = project_root / "docs" / "history"
        prose = list(history_dir.glob("blueprint_prose_v*.md"))
        assert len(prose) >= 1

    def test_fix_spec_versions_spec(self, project_root):
        state = _make_state(stage="3")
        dispatch_gate_response(state, "gate_3_2_diagnostic_decision", "FIX SPEC", project_root)
        history_dir = project_root / "docs" / "history"
        versioned = list(history_dir.glob("stakeholder_spec_v*.md"))
        assert len(versioned) >= 1


class TestGate41FixBlueprint:
    """Gate 4.1 FIX BLUEPRINT/SPEC must version the appropriate document."""

    def test_fix_blueprint_versions_blueprint(self, project_root):
        state = _make_state(stage="4")
        dispatch_gate_response(state, "gate_4_1_integration_failure", "FIX BLUEPRINT", project_root)
        history_dir = project_root / "docs" / "history"
        prose = list(history_dir.glob("blueprint_prose_v*.md"))
        assert len(prose) >= 1

    def test_fix_spec_versions_spec(self, project_root):
        state = _make_state(stage="4")
        dispatch_gate_response(state, "gate_4_1_integration_failure", "FIX SPEC", project_root)
        history_dir = project_root / "docs" / "history"
        versioned = list(history_dir.glob("stakeholder_spec_v*.md"))
        assert len(versioned) >= 1


class TestGate62FixBlueprint:
    """Gate 6.2 FIX BLUEPRINT/SPEC must version the appropriate document."""

    def test_fix_blueprint_versions_blueprint(self, project_root):
        state = _make_state(stage="6", sub_stage="debug_triage")
        state.debug_session = MagicMock()
        dispatch_gate_response(state, "gate_6_2_debug_classification", "FIX BLUEPRINT", project_root)
        history_dir = project_root / "docs" / "history"
        prose = list(history_dir.glob("blueprint_prose_v*.md"))
        assert len(prose) >= 1

    def test_fix_spec_versions_spec(self, project_root):
        state = _make_state(stage="6", sub_stage="debug_triage")
        state.debug_session = MagicMock()
        dispatch_gate_response(state, "gate_6_2_debug_classification", "FIX SPEC", project_root)
        history_dir = project_root / "docs" / "history"
        versioned = list(history_dir.glob("stakeholder_spec_v*.md"))
        assert len(versioned) >= 1


class TestVersionIncrements:
    """Multiple REVISE calls should create incrementing version numbers."""

    def test_multiple_revises_increment_version(self, project_root):
        state = _make_state(stage="1")
        dispatch_gate_response(state, "gate_1_1_spec_draft", "REVISE", project_root)
        dispatch_gate_response(state, "gate_1_1_spec_draft", "REVISE", project_root)
        history_dir = project_root / "docs" / "history"
        versioned = sorted(history_dir.glob("stakeholder_spec_v*.md"))
        # Filter out diff files
        versioned = [f for f in versioned if "_diff" not in f.name]
        assert len(versioned) == 2, "Two REVISE calls should create v1 and v2"
        assert "v1" in versioned[0].name
        assert "v2" in versioned[1].name


class TestImportPresent:
    """version_document must be imported in routing.py."""

    def test_version_document_importable_from_routing(self):
        """Verify the import is present -- the core wiring bug."""
        from routing import _version_spec, _version_blueprint
        assert callable(_version_spec)
        assert callable(_version_blueprint)

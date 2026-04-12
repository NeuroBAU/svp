"""Regression tests for Bug 52: version_document() wiring verification.

In SVP 2.2, version_document is a standalone transition function in
src.unit_6.stub. It is NOT automatically called from dispatch_gate_response
during REVISE flows -- versioning is handled differently in the new architecture.

Adapted for SVP 2.2 API:
- dispatch_gate_response(state, gate_id, response, project_root) -- 4 args
- PipelineState is a dataclass from pipeline_state
- version_document is in state_transitions (standalone function)
- Tests for automatic versioning during REVISE are skipped (not wired in SVP 2.2)
- Tests for REVISE gate dispatch behavior are preserved
"""

import json
import tempfile
from pathlib import Path

import pytest

from pipeline_state import PipelineState, save_state
from state_transitions import version_document
from routing import dispatch_gate_response
from svp_config import ARTIFACT_FILENAMES


def _make_state(stage="1", sub_stage=None):
    """Create a minimal PipelineState for testing."""
    return PipelineState(
        stage=stage,
        sub_stage=sub_stage,
        current_unit=1 if stage == "3" else None,
        total_units=24,
    )


def _dispatch_with_config(state, gate_id, response, project_root):
    """Call dispatch_gate_response with config in place."""
    if not (project_root / "svp_config.json").exists():
        (project_root / "svp_config.json").write_text(
            json.dumps({"iteration_limit": 3}), encoding="utf-8"
        )
    return dispatch_gate_response(state, gate_id, response, project_root)


@pytest.fixture
def project_root(tmp_path):
    """Create a project root with spec and blueprint files."""
    spec_path = tmp_path / ARTIFACT_FILENAMES["stakeholder_spec"]
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text("# Spec v1\nOriginal content")

    blueprint_dir = tmp_path / "blueprint"
    blueprint_dir.mkdir()
    (blueprint_dir / "blueprint_prose.md").write_text("# Blueprint Prose v1")
    (blueprint_dir / "blueprint_contracts.md").write_text("# Blueprint Contracts v1")

    # Create .svp dir with last_status.txt
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir()
    (svp_dir / "last_status.txt").write_text("")

    # Create svp_config.json
    (tmp_path / "svp_config.json").write_text(json.dumps({"iteration_limit": 3}))

    return tmp_path


class TestGate11SpecRevise:
    """Gate 1.1 REVISE dispatch returns valid state."""

    def test_revise_returns_valid_state(self, project_root):
        state = _make_state(stage="1")
        result = _dispatch_with_config(
            state, "gate_1_1_spec_draft", "REVISE", project_root
        )
        # REVISE returns a copy of state (for re-invocation of stakeholder dialog)
        assert result is not state
        assert result.stage == "1"

class TestGate12SpecRevise:
    """Gate 1.2 REVISE dispatch returns valid state."""

    def test_revise_returns_valid_state(self, project_root):
        state = _make_state(stage="1")
        result = _dispatch_with_config(
            state, "gate_1_2_spec_post_review", "REVISE", project_root
        )
        assert result is not state
        assert result.stage == "1"


class TestGate21BlueprintRevise:
    """Gate 2.1 REVISE dispatch."""

    def test_revise_sets_blueprint_dialog_sub_stage(self, project_root):
        state = _make_state(stage="2")
        result = _dispatch_with_config(
            state, "gate_2_1_blueprint_approval", "REVISE", project_root
        )
        assert result.sub_stage == "blueprint_dialog"


class TestGate22BlueprintRevise:
    """Gate 2.2 REVISE dispatch."""

    def test_revise_sets_blueprint_dialog_sub_stage(self, project_root):
        state = _make_state(stage="2")
        result = _dispatch_with_config(
            state, "gate_2_2_blueprint_post_review", "REVISE", project_root
        )
        assert result.sub_stage == "blueprint_dialog"


class TestGate23ReviseSpec:
    """Gate 2.3 REVISE SPEC dispatch."""

    def test_revise_spec_sets_targeted_spec_revision(self, project_root):
        state = _make_state(stage="2")
        result = _dispatch_with_config(
            state, "gate_2_3_alignment_exhausted", "REVISE SPEC", project_root
        )
        assert result.sub_stage == "targeted_spec_revision"


class TestGate32FixBlueprint:
    """Gate 3.2 FIX BLUEPRINT dispatch."""

    def test_fix_blueprint_restarts_to_stage_2(self, project_root):
        state = _make_state(stage="3", sub_stage="stub_generation")
        result = _dispatch_with_config(
            state, "gate_3_2_diagnostic_decision", "FIX BLUEPRINT", project_root
        )
        assert result.stage == "2"

    def test_fix_spec_restarts_to_stage_1(self, project_root):
        state = _make_state(stage="3", sub_stage="stub_generation")
        result = _dispatch_with_config(
            state, "gate_3_2_diagnostic_decision", "FIX SPEC", project_root
        )
        assert result.stage == "1"


class TestGate41FixBlueprint:
    """Gate 4.1 FIX BLUEPRINT/SPEC dispatch."""

    def test_fix_blueprint_restarts_to_stage_2(self, project_root):
        state = _make_state(stage="4")
        result = _dispatch_with_config(
            state, "gate_4_1_integration_failure", "FIX BLUEPRINT", project_root
        )
        assert result.stage == "2"

    def test_fix_spec_restarts_to_stage_1(self, project_root):
        state = _make_state(stage="4")
        result = _dispatch_with_config(
            state, "gate_4_1_integration_failure", "FIX SPEC", project_root
        )
        assert result.stage == "1"


class TestGate62FixBlueprint:
    """Gate 6.2 FIX BLUEPRINT/SPEC dispatch."""

    def test_fix_blueprint_restarts_to_stage_2(self, project_root):
        ds = {
            "bug_number": 1, "classification": None, "affected_units": [],
            "phase": "triage", "authorized": True,
            "repair_retry_count": 0, "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(stage="5")
        state.debug_session = ds
        result = _dispatch_with_config(
            state, "gate_6_2_debug_classification", "FIX BLUEPRINT", project_root
        )
        assert result.stage == "2"

    def test_fix_spec_restarts_to_stage_1(self, project_root):
        ds = {
            "bug_number": 1, "classification": None, "affected_units": [],
            "phase": "triage", "authorized": True,
            "repair_retry_count": 0, "triage_refinement_count": 0,
            "ledger_path": None,
        }
        state = _make_state(stage="5")
        state.debug_session = ds
        result = _dispatch_with_config(
            state, "gate_6_2_debug_classification", "FIX SPEC", project_root
        )
        assert result.stage == "1"


class TestVersionDocumentStandalone:
    """Test that version_document works as a standalone function."""

    def test_version_document_copies_file(self, project_root):
        """version_document copies document to history directory."""
        state = _make_state(stage="1")
        doc_path = str(project_root / ARTIFACT_FILENAMES["stakeholder_spec"])
        result = version_document(state, doc_path)
        # Check that pass_history was updated
        assert len(result.pass_history) == 1
        assert result.pass_history[0]["document"] == doc_path
        # Check that history file was created
        history_dir = project_root / Path(ARTIFACT_FILENAMES["stakeholder_spec"]).parent / "history"
        assert history_dir.exists()

    def test_multiple_versions_increment(self, project_root):
        """Multiple version_document calls create incrementing versions."""
        state = _make_state(stage="1")
        doc_path = str(project_root / ARTIFACT_FILENAMES["stakeholder_spec"])
        s1 = version_document(state, doc_path)
        s2 = version_document(s1, doc_path)
        assert len(s2.pass_history) == 2
        assert s2.pass_history[0]["version"] == 1
        assert s2.pass_history[1]["version"] == 2


class TestImportPresent:
    """version_document must be importable."""

    def test_version_document_importable(self):
        """Verify the function is importable from state_transitions."""
        from state_transitions import version_document as vd
        assert callable(vd)

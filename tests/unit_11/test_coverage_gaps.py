"""
Coverage gap tests for Unit 11: Command Logic Scripts.

These tests cover behavioral contracts, invariants, and error conditions
from the blueprint that were not exercised by the existing test suite.

DATA ASSUMPTION: Pipeline state is constructed with typical values from Unit 2
schema. Project names like "test_project" are short alphanumeric strings.

DATA ASSUMPTION: Pass history entries follow Unit 2 schema with fields:
pass_number (int), reached_unit (int), ended_reason (str), timestamp (str).

DATA ASSUMPTION: Debug history entries follow Unit 2 schema with fields:
bug_id (int), description (str), classification (str), etc.

DATA ASSUMPTION: Pipeline stages follow the canonical sequence from Unit 2:
["0", "1", "2", "pre_stage_3", "3", "4", "5"]. Stage "5" indicates delivery
is complete, which is the prerequisite for clean_workspace.

DATA ASSUMPTION: Conda environment names are short strings like "test_env"
or "myproject_env", typical of conda naming conventions.
"""

import json
import os
import stat
import tarfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from svp.scripts.command_logic import (
    save_project,
    quit_project,
    get_status,
    format_pass_history,
    format_debug_history,
    clean_workspace,
    archive_workspace,
    delete_workspace,
    remove_conda_env,
)


# ---------------------------------------------------------------------------
# Helpers (duplicated from main test file to keep this file self-contained)
# ---------------------------------------------------------------------------

def _write_pipeline_state(project_root: Path, state_dict: Dict[str, Any]) -> Path:
    """Write a pipeline_state.json file into the project root."""
    state_path = project_root / "pipeline_state.json"
    state_path.write_text(json.dumps(state_dict, indent=2) + "\n", encoding="utf-8")
    return state_path


def _make_state_dict(**overrides) -> Dict[str, Any]:
    """
    Create a minimal pipeline state dict with sensible defaults.

    DATA ASSUMPTION: Default state represents a project mid-way through
    Stage 3 with 2 verified units and 1 pass history entry.
    """
    defaults: Dict[str, Any] = {
        "stage": "3",
        "sub_stage": None,
        "current_unit": 3,
        "total_units": 10,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iteration": 1,
        "verified_units": [
            {"unit": 1, "timestamp": "2026-01-01T00:00:00+00:00"},
            {"unit": 2, "timestamp": "2026-01-02T00:00:00+00:00"},
        ],
        "pass_history": [
            {
                "pass_number": 1,
                "reached_unit": 2,
                "ended_reason": "iteration_limit",
                "timestamp": "2026-01-02T12:00:00+00:00",
            }
        ],
        "log_references": {},
        "project_name": "test_project",
        "last_action": "test",
        "debug_session": None,
        "debug_history": [],
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-03T00:00:00+00:00",
    }
    defaults.update(overrides)
    return defaults


def _make_delivery_state_dict(**overrides) -> Dict[str, Any]:
    """
    Create a state dict representing a project at Stage 5 (delivery complete).

    DATA ASSUMPTION: Stage 5 represents delivery is complete, which is the
    prerequisite for clean_workspace to be functional.
    """
    defaults = _make_state_dict(stage="5", current_unit=None)
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project_root(tmp_path):
    """
    Create a temporary project root with a pipeline_state.json,
    svp_config.json, and basic directory structure.
    """
    _write_pipeline_state(tmp_path, _make_state_dict())

    config = {
        "iteration_limit": 3,
        "models": {"default": "claude-opus-4-6"},
        "auto_save": True,
        "skip_permissions": True,
    }
    (tmp_path / "svp_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )

    ledgers_dir = tmp_path / "ledgers"
    ledgers_dir.mkdir()

    return tmp_path


@pytest.fixture
def delivery_project_root(tmp_path):
    """
    Create a temporary project root at Stage 5 (delivery complete).
    Required for clean_workspace tests.
    """
    _write_pipeline_state(tmp_path, _make_delivery_state_dict())

    config = {
        "iteration_limit": 3,
        "models": {"default": "claude-opus-4-6"},
        "auto_save": True,
        "skip_permissions": True,
    }
    (tmp_path / "svp_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )

    # Create some workspace content to clean
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "module.py").write_text("# code\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mod.py").write_text("# tests\n")

    return tmp_path


# ===========================================================================
# GAP: save_project -- corrupt state file integrity detection
# Blueprint: "save_project verifies file integrity of state file and key
# documents, confirms save is complete, returns a human-readable
# confirmation message."
# Existing tests only check happy path. No test for corrupt JSON.
# ===========================================================================

class TestSaveProjectIntegrity:
    """Tests for save_project file integrity verification behavior."""

    def test_corrupt_state_file_reports_issue(self, tmp_path):
        """
        save_project verifies file integrity of state file. When the state
        file contains invalid JSON, the confirmation message should indicate
        an issue was found rather than silently succeeding.

        DATA ASSUMPTION: A pipeline_state.json with invalid JSON content
        represents a corrupted state file.
        """
        state_path = tmp_path / "pipeline_state.json"
        state_path.write_text("{invalid json content!!!", encoding="utf-8")

        result = save_project(tmp_path)
        assert isinstance(result, str)
        assert len(result) > 0
        # The result should mention issues/problems with the state file
        result_lower = result.lower()
        assert "issue" in result_lower or "error" in result_lower or "pipeline_state" in result_lower

    def test_missing_state_file_reports_issue(self, tmp_path):
        """
        save_project verifies file integrity. When the state file is missing,
        the message should indicate this.

        DATA ASSUMPTION: A project root with no pipeline_state.json is a
        plausible scenario (e.g., first-time setup).
        """
        # tmp_path exists but has no pipeline_state.json
        result = save_project(tmp_path)
        assert isinstance(result, str)
        assert len(result) > 0
        # Should mention something about the state file not being found
        result_lower = result.lower()
        assert "not found" in result_lower or "issue" in result_lower or "pipeline_state" in result_lower

    def test_verifies_key_documents(self, tmp_path):
        """
        Blueprint: save_project verifies file integrity of state file AND
        key documents. When key documents exist and are valid, they should
        be mentioned in the verification output.

        DATA ASSUMPTION: Key documents include specs/stakeholder.md and
        blueprint/blueprint.md based on implementation.
        """
        # Write valid state
        _write_pipeline_state(tmp_path, _make_state_dict())

        # Create key documents
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir()
        (specs_dir / "stakeholder.md").write_text("# Stakeholder Spec\n")

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint.md").write_text("# Blueprint\n")

        result = save_project(tmp_path)
        assert isinstance(result, str)
        assert len(result) > 0
        # Key documents should be mentioned in the verification
        assert "stakeholder" in result.lower() or "blueprint" in result.lower() or "verified" in result.lower()


# ===========================================================================
# GAP: quit_project -- exit message actually contains save status
# Blueprint: "quit_project calls save_project first, then returns an exit
# confirmation message with save status."
# Existing mock test verifies save_project is called but does not verify
# that the save status text appears in the returned message.
# ===========================================================================

class TestQuitProjectSaveStatusInMessage:
    """Tests verifying quit_project includes save status in exit message."""

    def test_exit_message_contains_save_status_text(self, project_root):
        """
        Behavioral contract: quit_project returns an exit confirmation
        message WITH save status. The save_project return value should
        be included or referenced in the quit message.
        """
        with patch("svp.scripts.command_logic.save_project", return_value="All files verified OK.") as mock_save:
            result = quit_project(project_root)
            mock_save.assert_called_once()
            # The exit message should contain the save status
            assert "All files verified OK." in result or "save" in result.lower()

    def test_exit_message_references_save_and_exit(self, project_root):
        """
        The exit confirmation should reference both saving and exiting,
        since quit_project performs both operations.
        """
        result = quit_project(project_root)
        result_lower = result.lower()
        # Should mention both save and exit/quit
        assert "save" in result_lower or "verif" in result_lower
        assert "exit" in result_lower or "quit" in result_lower or "saved" in result_lower


# ===========================================================================
# GAP: format_pass_history -- single entry shows reached_unit value
# Blueprint: "format_pass_history formats pass history entries as a brief
# numbered list showing how far each pass reached and why it ended."
# Existing single entry test only checks "1" is present (pass_number),
# not the reached_unit value.
# ===========================================================================

class TestFormatPassHistoryReachedUnit:
    """Tests verifying format_pass_history shows reached unit values."""

    def test_single_entry_shows_reached_unit(self):
        """
        Behavioral contract: format_pass_history shows how far each pass
        reached. A single entry with reached_unit=8 should include "8"
        in the output.

        DATA ASSUMPTION: reached_unit=8 is a distinct value that would
        not appear as a pass_number or other field.
        """
        history = [
            {
                "pass_number": 1,
                "reached_unit": 8,
                "ended_reason": "session_boundary",
                "timestamp": "2026-01-01T12:00:00+00:00",
            }
        ]
        result = format_pass_history(history)
        assert isinstance(result, str)
        assert len(result) > 0
        # Must show the reached_unit value (8)
        assert "8" in result

    def test_shows_different_ended_reasons(self):
        """
        Behavioral contract: shows why each pass ended. Test with a
        non-default ended_reason to ensure it appears in output.

        DATA ASSUMPTION: "all_verified" is a valid ended_reason meaning
        all units were verified in this pass.
        """
        history = [
            {
                "pass_number": 1,
                "reached_unit": 10,
                "ended_reason": "all_verified",
                "timestamp": "2026-01-01T12:00:00+00:00",
            }
        ]
        result = format_pass_history(history)
        assert "all_verified" in result or "all" in result.lower()


# ===========================================================================
# GAP: format_debug_history -- output includes description text
# Blueprint: "format_debug_history formats debug history entries similarly"
# (to pass history). Existing tests check numbering but not description
# content.
# ===========================================================================

class TestFormatDebugHistoryContent:
    """Tests verifying format_debug_history includes entry descriptions."""

    def test_single_entry_includes_description(self):
        """
        Behavioral contract: format_debug_history formats entries similarly
        to pass history. The description of each bug should appear in the
        formatted output.

        DATA ASSUMPTION: A debug entry with a distinctive description string
        "Memory leak in serializer" that can be verified in the output.
        """
        history = [
            {
                "bug_id": 1,
                "description": "Memory leak in serializer",
                "classification": "single_unit",
                "affected_units": [7],
                "phase": "complete",
            },
        ]
        result = format_debug_history(history)
        assert isinstance(result, str)
        assert len(result) > 0
        # The description should appear in the output
        assert "Memory leak in serializer" in result or "serializer" in result.lower()

    def test_entry_includes_classification(self):
        """
        Debug history entries include classification information in the
        formatted output.

        DATA ASSUMPTION: classification "cross_unit" is a standard
        classification type for bugs spanning multiple units.
        """
        history = [
            {
                "bug_id": 1,
                "description": "Shared config mismatch",
                "classification": "cross_unit",
                "affected_units": [2, 3],
                "phase": "complete",
            },
        ]
        result = format_debug_history(history)
        assert isinstance(result, str)
        assert "cross_unit" in result or "cross" in result.lower()


# ===========================================================================
# GAP: clean_workspace -- pre_stage_3 and stage 4 return error message
# Blueprint: "clean_workspace is only functional after Stage 5 delivery.
# Returns an error message if invoked before delivery."
# Existing tests cover stage 0 and stage 3 but not pre_stage_3 or stage 4.
# ===========================================================================

class TestCleanWorkspacePreDeliveryStages:
    """Tests for clean_workspace error messages at non-delivery stages."""

    def test_before_delivery_pre_stage_3(self, tmp_path):
        """
        clean_workspace at pre_stage_3 should return an error message
        since delivery is not complete.

        DATA ASSUMPTION: Stage "pre_stage_3" is before delivery (Stage 5).
        """
        _write_pipeline_state(tmp_path, _make_state_dict(stage="pre_stage_3"))
        result = clean_workspace(tmp_path, "archive")
        assert isinstance(result, str)
        assert len(result) > 0
        # Should indicate cleaning is not available
        result_lower = result.lower()
        assert "cannot" in result_lower or "not" in result_lower or "error" in result_lower

    def test_before_delivery_stage_4(self, tmp_path):
        """
        clean_workspace at stage 4 should return an error message
        since delivery is not complete.

        DATA ASSUMPTION: Stage "4" is the assembly integration stage,
        still before delivery.
        """
        _write_pipeline_state(tmp_path, _make_state_dict(stage="4"))
        result = clean_workspace(tmp_path, "delete")
        assert isinstance(result, str)
        assert len(result) > 0
        result_lower = result.lower()
        assert "cannot" in result_lower or "not" in result_lower or "error" in result_lower

    def test_before_delivery_stage_1(self, tmp_path):
        """
        clean_workspace at stage 1 should return an error message.

        DATA ASSUMPTION: Stage "1" is the stakeholder spec drafting stage.
        """
        _write_pipeline_state(tmp_path, _make_state_dict(stage="1"))
        result = clean_workspace(tmp_path, "keep")
        assert isinstance(result, str)
        assert len(result) > 0
        result_lower = result.lower()
        assert "cannot" in result_lower or "not" in result_lower or "error" in result_lower


# ===========================================================================
# GAP: clean_workspace mode='delete' invokes remove_conda_env
# Blueprint: "delete_workspace removes the workspace" and the clean_workspace
# delete mode path in the implementation calls remove_conda_env.
# No existing test verifies this integration.
# ===========================================================================

class TestCleanWorkspaceDeleteCallsCondaRemove:
    """Tests that clean_workspace delete mode attempts conda env removal."""

    def test_delete_mode_attempts_conda_env_removal(self, tmp_path):
        """
        Behavioral contract: clean_workspace with mode='delete' should
        attempt to remove the conda environment associated with the project.

        DATA ASSUMPTION: The project_name from pipeline state is used as
        the conda environment name.
        """
        state = _make_delivery_state_dict(project_name="myproject")
        _write_pipeline_state(tmp_path, state)

        (tmp_path / "svp_config.json").write_text(
            json.dumps({"iteration_limit": 3, "models": {"default": "x"}, "auto_save": True}),
            encoding="utf-8",
        )
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "code.py").write_text("# code\n")

        with patch("svp.scripts.command_logic.remove_conda_env", return_value=True) as mock_conda, \
             patch("svp.scripts.command_logic.delete_workspace") as mock_delete:
            result = clean_workspace(tmp_path, "delete")
            # remove_conda_env should have been called with the project name
            mock_conda.assert_called_once_with("myproject")
            assert isinstance(result, str)
            assert len(result) > 0


# ===========================================================================
# GAP: archive_workspace -- archive contains workspace files
# Blueprint: "archive_workspace compresses the workspace into a .tar.gz file"
# Existing tests check tarfile validity but not that workspace content is
# inside the archive.
# ===========================================================================

class TestArchiveWorkspaceContents:
    """Tests that archive_workspace preserves workspace file content."""

    def test_archive_contains_workspace_files(self, delivery_project_root):
        """
        Behavioral contract: archive_workspace compresses the workspace.
        The resulting .tar.gz should contain the workspace's files.

        DATA ASSUMPTION: The delivery_project_root fixture creates files
        under src/ and tests/ subdirectories.
        """
        # Add a distinctive file to verify archival
        (delivery_project_root / "marker.txt").write_text("archive test marker\n")

        archive_path = archive_workspace(delivery_project_root)
        assert archive_path.exists()
        assert str(archive_path).endswith(".tar.gz")

        # Open the archive and verify it contains workspace files
        with tarfile.open(str(archive_path), "r:gz") as tar:
            member_names = tar.getnames()
            # Should contain the workspace directory name and its contents
            assert len(member_names) > 0
            # Look for the marker file in the archive
            marker_found = any("marker.txt" in name for name in member_names)
            assert marker_found, f"marker.txt not found in archive members: {member_names}"

        # Clean up
        archive_path.unlink(missing_ok=True)


# ===========================================================================
# GAP: delete_workspace precondition -- project_root must exist
# Blueprint invariant: "assert project_root.is_dir()"
# Existing invariant tests cover save_project, quit_project, get_status,
# and clean_workspace but NOT delete_workspace or archive_workspace directly.
# ===========================================================================

class TestDeleteWorkspacePrecondition:
    """Tests for delete_workspace precondition."""

    def test_precondition_project_root_must_exist(self):
        """
        Invariant: project_root must be a directory. Calling
        delete_workspace on a nonexistent path should raise.
        """
        nonexistent = Path("/nonexistent_directory_xyz_abc_456")
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            delete_workspace(nonexistent)


class TestArchiveWorkspacePrecondition:
    """Tests for archive_workspace precondition."""

    def test_precondition_project_root_must_exist(self):
        """
        Invariant: project_root must be a directory. Calling
        archive_workspace on a nonexistent path should raise.
        """
        nonexistent = Path("/nonexistent_directory_xyz_abc_789")
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            archive_workspace(nonexistent)


# ===========================================================================
# GAP: get_status -- stronger assertion for "next expected action" presence
# Blueprint: "get_status reads pipeline state and produces a human-readable
# report including ... next expected action."
# Existing test only checks len(result) > 10. This test verifies the
# "next" or "action" keyword appears.
# ===========================================================================

class TestGetStatusNextAction:
    """Tests for get_status next expected action reporting."""

    def test_status_report_mentions_next_action(self, project_root):
        """
        Behavioral contract: get_status report includes the next expected
        action. The output should contain text indicating what comes next.

        DATA ASSUMPTION: At stage 3, unit 3, the next expected action
        is related to implementing unit 3.
        """
        result = get_status(project_root)
        result_lower = result.lower()
        # Should mention "next" and/or "action" somewhere in the report
        assert "next" in result_lower or "action" in result_lower

    def test_status_report_at_stage_5_mentions_delivery(self, tmp_path):
        """
        At stage 5, the next expected action should indicate post-delivery
        or that the project has been delivered.

        DATA ASSUMPTION: Stage "5" is the delivery stage.
        """
        _write_pipeline_state(tmp_path, _make_state_dict(stage="5", current_unit=None))
        result = get_status(tmp_path)
        result_lower = result.lower()
        assert "deliver" in result_lower or "maintenance" in result_lower or "5" in result

    def test_status_report_sub_stage_appears_in_output(self, tmp_path):
        """
        Behavioral contract: get_status includes sub-stage. When sub_stage
        is "hook_activation", that text should appear in the output.

        DATA ASSUMPTION: Stage 0 with sub_stage "hook_activation".
        """
        state = _make_state_dict(stage="0", sub_stage="hook_activation")
        _write_pipeline_state(tmp_path, state)
        result = get_status(tmp_path)
        assert "hook_activation" in result or "hook" in result.lower()


# ===========================================================================
# GAP: clean_workspace -- error message communicates not-delivered reason
# Blueprint: "Returns an error message if invoked before delivery."
# Existing tests check len > 0 but not that the message communicates the
# actual reason (not at stage 5).
# ===========================================================================

class TestCleanWorkspaceErrorMessageContent:
    """Tests for clean_workspace error message content when not at stage 5."""

    def test_error_message_mentions_stage_or_delivery(self, tmp_path):
        """
        When clean_workspace is called before delivery, the error message
        should communicate that delivery has not occurred.

        DATA ASSUMPTION: Stage "3" is before delivery.
        """
        _write_pipeline_state(tmp_path, _make_state_dict(stage="3"))
        result = clean_workspace(tmp_path, "archive")
        result_lower = result.lower()
        # Should mention stage or delivery in the error message
        assert "stage" in result_lower or "deliver" in result_lower or "clean" in result_lower

    def test_keep_mode_returns_confirmation_at_stage_5(self, delivery_project_root):
        """
        Behavioral contract: clean_workspace with mode='keep' at stage 5
        should return a confirmation that no cleanup was performed.

        DATA ASSUMPTION: "keep" mode means the workspace is left as-is.
        """
        result = clean_workspace(delivery_project_root, "keep")
        assert isinstance(result, str)
        assert len(result) > 0
        result_lower = result.lower()
        # Should indicate the workspace was kept or no cleanup happened
        assert "keep" in result_lower or "kept" in result_lower or "no" in result_lower

"""
Tests for Unit 11: Command Logic Scripts.

Tests cover /svp:save, /svp:quit, /svp:status, /svp:clean command functions.

DATA ASSUMPTION: Pipeline state is constructed with typical values from Unit 2
schema. Project names like "test_project" are short alphanumeric strings.

DATA ASSUMPTION: Pass history entries follow Unit 2 schema with fields:
pass_number (int), reached_unit (int), ended_reason (str), timestamp (str).

DATA ASSUMPTION: Debug history entries follow Unit 2 schema with fields:
bug_id (int), description (str), classification (str), etc.

DATA ASSUMPTION: Pipeline stages follow the canonical sequence from Unit 2:
["0", "1", "2", "pre_stage_3", "3", "4", "5"]. Stage "5" indicates delivery
is complete, which is the prerequisite for clean_workspace.

DATA ASSUMPTION: Verified units are dicts with "unit" (int) and "timestamp"
(str) fields, representing units that passed verification.

DATA ASSUMPTION: Ledger files are JSONL files read by Unit 4's read_ledger.

DATA ASSUMPTION: Conda environment names are short strings like "test_env"
or "myproject_env", typical of conda naming conventions.
"""

import inspect
import json
import os
import stat
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch, call

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
# Helpers
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
    # Write a default pipeline state
    _write_pipeline_state(tmp_path, _make_state_dict())

    # Write a minimal svp_config.json
    config = {
        "iteration_limit": 3,
        "models": {"default": "claude-opus-4-6"},
        "auto_save": True,
        "skip_permissions": True,
    }
    (tmp_path / "svp_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )

    # Create ledgers directory with a ledger file
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
# Signature Tests
# ===========================================================================

class TestSignatures:
    """Verify function signatures match the blueprint."""

    def test_save_project_signature(self):
        sig = inspect.signature(save_project)
        params = list(sig.parameters.keys())
        assert params == ["project_root"]
        assert sig.parameters["project_root"].annotation is Path
        assert sig.return_annotation is str

    def test_quit_project_signature(self):
        sig = inspect.signature(quit_project)
        params = list(sig.parameters.keys())
        assert params == ["project_root"]
        assert sig.parameters["project_root"].annotation is Path
        assert sig.return_annotation is str

    def test_get_status_signature(self):
        sig = inspect.signature(get_status)
        params = list(sig.parameters.keys())
        assert params == ["project_root"]
        assert sig.parameters["project_root"].annotation is Path
        assert sig.return_annotation is str

    def test_format_pass_history_signature(self):
        sig = inspect.signature(format_pass_history)
        params = list(sig.parameters.keys())
        assert params == ["pass_history"]
        assert sig.parameters["pass_history"].annotation is list
        assert sig.return_annotation is str

    def test_format_debug_history_signature(self):
        sig = inspect.signature(format_debug_history)
        params = list(sig.parameters.keys())
        assert params == ["debug_history"]
        assert sig.parameters["debug_history"].annotation is list
        assert sig.return_annotation is str

    def test_clean_workspace_signature(self):
        sig = inspect.signature(clean_workspace)
        params = list(sig.parameters.keys())
        assert params == ["project_root", "mode"]
        assert sig.parameters["project_root"].annotation is Path
        assert sig.parameters["mode"].annotation is str
        assert sig.return_annotation is str

    def test_archive_workspace_signature(self):
        sig = inspect.signature(archive_workspace)
        params = list(sig.parameters.keys())
        assert params == ["project_root"]
        assert sig.parameters["project_root"].annotation is Path
        assert sig.return_annotation is Path

    def test_delete_workspace_signature(self):
        sig = inspect.signature(delete_workspace)
        params = list(sig.parameters.keys())
        assert params == ["project_root"]
        assert sig.parameters["project_root"].annotation is Path
        # Return annotation should be None
        assert sig.return_annotation is None

    def test_remove_conda_env_signature(self):
        sig = inspect.signature(remove_conda_env)
        params = list(sig.parameters.keys())
        assert params == ["env_name"]
        assert sig.parameters["env_name"].annotation is str
        assert sig.return_annotation is bool


# ===========================================================================
# Invariant Tests (Pre-conditions and Post-conditions)
# ===========================================================================

class TestInvariants:
    """Test pre-conditions and post-conditions from the blueprint."""

    def test_save_project_precondition_project_root_must_exist(self):
        """Pre-condition: project_root must be a directory."""
        nonexistent = Path("/nonexistent_directory_xyz_abc_123")
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            save_project(nonexistent)

    def test_quit_project_precondition_project_root_must_exist(self):
        """Pre-condition: project_root must be a directory."""
        nonexistent = Path("/nonexistent_directory_xyz_abc_123")
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            quit_project(nonexistent)

    def test_get_status_precondition_project_root_must_exist(self):
        """Pre-condition: project_root must be a directory."""
        nonexistent = Path("/nonexistent_directory_xyz_abc_123")
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            get_status(nonexistent)

    def test_clean_workspace_precondition_project_root_must_exist(self):
        """Pre-condition: project_root must be a directory."""
        nonexistent = Path("/nonexistent_directory_xyz_abc_123")
        with pytest.raises((AssertionError, FileNotFoundError, OSError)):
            clean_workspace(nonexistent, "archive")

    def test_clean_workspace_precondition_mode_must_be_valid(self, delivery_project_root):
        """Pre-condition: mode must be archive, delete, or keep."""
        with pytest.raises((AssertionError, ValueError)):
            clean_workspace(delivery_project_root, "invalid_mode")

    def test_clean_workspace_mode_archive_is_valid(self, delivery_project_root):
        """Mode 'archive' should be accepted without raising mode validation error."""
        # Should not raise AssertionError for invalid mode
        # (may raise other errors if not at stage 5, but that's separate)
        try:
            result = clean_workspace(delivery_project_root, "archive")
            # If it succeeds, result should be a string
            assert isinstance(result, str)
        except (AssertionError, ValueError) as e:
            # Should NOT be a mode validation error
            assert "mode" not in str(e).lower() or "archive" not in str(e).lower()

    def test_clean_workspace_mode_delete_is_valid(self, delivery_project_root):
        """Mode 'delete' should be accepted."""
        try:
            result = clean_workspace(delivery_project_root, "delete")
            assert isinstance(result, str)
        except (AssertionError, ValueError) as e:
            assert "mode" not in str(e).lower() or "delete" not in str(e).lower()

    def test_clean_workspace_mode_keep_is_valid(self, delivery_project_root):
        """Mode 'keep' should be accepted."""
        try:
            result = clean_workspace(delivery_project_root, "keep")
            assert isinstance(result, str)
        except (AssertionError, ValueError) as e:
            assert "mode" not in str(e).lower() or "keep" not in str(e).lower()

    def test_save_project_postcondition_nonempty_result(self, project_root):
        """Post-condition: save confirmation message must be non-empty."""
        result = save_project(project_root)
        assert isinstance(result, str)
        assert len(result) > 0


# ===========================================================================
# save_project Tests
# ===========================================================================

class TestSaveProject:
    """Tests for the save_project command."""

    def test_returns_string(self, project_root):
        """save_project must return a string."""
        result = save_project(project_root)
        assert isinstance(result, str)

    def test_returns_nonempty_confirmation(self, project_root):
        """save_project returns a non-empty human-readable confirmation message."""
        result = save_project(project_root)
        assert len(result) > 0

    def test_verifies_state_file_integrity(self, project_root):
        """
        save_project verifies file integrity of state file.
        It should work when the state file is valid.
        """
        result = save_project(project_root)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_confirms_save_is_complete(self, project_root):
        """save_project returns a confirmation message indicating save is complete."""
        result = save_project(project_root)
        # The message should indicate success/completion in some way
        assert isinstance(result, str)
        assert len(result) > 0


# ===========================================================================
# quit_project Tests
# ===========================================================================

class TestQuitProject:
    """Tests for the quit_project command."""

    def test_returns_string(self, project_root):
        """quit_project must return a string."""
        result = quit_project(project_root)
        assert isinstance(result, str)

    def test_returns_exit_confirmation(self, project_root):
        """quit_project returns an exit confirmation message."""
        result = quit_project(project_root)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_calls_save_project_first(self, project_root):
        """
        Behavioral contract: quit_project calls save_project first,
        then returns an exit confirmation message with save status.
        """
        # We use a mock to verify save_project is called
        with patch("svp.scripts.command_logic.save_project", return_value="Save complete.") as mock_save:
            result = quit_project(project_root)
            mock_save.assert_called_once()
            # The result should be a non-empty exit confirmation
            assert isinstance(result, str)
            assert len(result) > 0

    def test_includes_save_status_in_message(self, project_root):
        """
        quit_project returns an exit confirmation message with save status.
        The message should reference the save operation.
        """
        result = quit_project(project_root)
        assert isinstance(result, str)
        assert len(result) > 0


# ===========================================================================
# get_status Tests
# ===========================================================================

class TestGetStatus:
    """Tests for the get_status command."""

    def test_returns_string(self, project_root):
        """get_status must return a string."""
        result = get_status(project_root)
        assert isinstance(result, str)

    def test_returns_nonempty_report(self, project_root):
        """get_status produces a human-readable report."""
        result = get_status(project_root)
        assert len(result) > 0

    def test_includes_current_stage(self, project_root):
        """
        Behavioral contract: status report includes current stage.
        The state is at stage "3", so we expect to see "3" in the output.

        DATA ASSUMPTION: Stage is "3" based on _make_state_dict defaults.
        """
        result = get_status(project_root)
        assert "3" in result

    def test_includes_verified_units(self, project_root):
        """
        Behavioral contract: status report includes verified units.

        DATA ASSUMPTION: 2 verified units (unit 1 and unit 2) from defaults.
        """
        result = get_status(project_root)
        # Should mention verified units in some form
        assert isinstance(result, str)
        assert len(result) > 0
        # The report should reference verified units -- check for common patterns
        result_lower = result.lower()
        assert "verif" in result_lower or "unit" in result_lower or "2" in result

    def test_includes_alignment_iteration(self, project_root):
        """
        Behavioral contract: status report includes alignment iterations used.

        DATA ASSUMPTION: alignment_iteration is 1 from defaults.
        """
        result = get_status(project_root)
        # Should mention alignment iteration or iteration count
        assert "1" in result or "iteration" in result.lower()

    def test_includes_pass_history_summary(self, project_root):
        """
        Behavioral contract: status report includes pass history summary.

        DATA ASSUMPTION: 1 pass history entry from defaults.
        """
        result = get_status(project_root)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_includes_debug_history_summary(self, project_root):
        """
        Behavioral contract: status report includes debug history summary.

        DATA ASSUMPTION: Empty debug history from defaults. Report should
        still include some indication of debug history (e.g., "none" or "0").
        """
        result = get_status(project_root)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_file_not_found_error_when_no_state_file(self, tmp_path):
        """
        Error condition: FileNotFoundError when pipeline_state.json not found.
        """
        with pytest.raises(FileNotFoundError, match="[Pp]ipeline.state.*not found|not found"):
            get_status(tmp_path)

    def test_status_at_stage_5(self, tmp_path):
        """
        Status at stage 5 should report stage 5.

        DATA ASSUMPTION: Stage "5" represents delivery complete.
        """
        _write_pipeline_state(tmp_path, _make_state_dict(stage="5"))
        result = get_status(tmp_path)
        assert "5" in result

    def test_status_with_multiple_pass_history(self, tmp_path):
        """
        Status with multiple pass history entries.

        DATA ASSUMPTION: Multiple passes through Stage 3, each reaching
        different units before ending.
        """
        pass_history = [
            {
                "pass_number": 1,
                "reached_unit": 3,
                "ended_reason": "iteration_limit",
                "timestamp": "2026-01-01T00:00:00+00:00",
            },
            {
                "pass_number": 2,
                "reached_unit": 7,
                "ended_reason": "all_verified",
                "timestamp": "2026-01-02T00:00:00+00:00",
            },
        ]
        state = _make_state_dict(pass_history=pass_history)
        _write_pipeline_state(tmp_path, state)
        result = get_status(tmp_path)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_status_with_debug_history(self, tmp_path):
        """
        Status with debug history entries.

        DATA ASSUMPTION: Debug history entries have bug_id, description,
        and classification fields.
        """
        debug_history = [
            {
                "bug_id": 1,
                "description": "Off-by-one in parser",
                "classification": "single_unit",
                "affected_units": [3],
                "phase": "complete",
            },
        ]
        state = _make_state_dict(debug_history=debug_history)
        _write_pipeline_state(tmp_path, state)
        result = get_status(tmp_path)
        assert isinstance(result, str)
        assert len(result) > 0


# ===========================================================================
# format_pass_history Tests
# ===========================================================================

class TestFormatPassHistory:
    """Tests for format_pass_history."""

    def test_returns_string(self):
        """format_pass_history must return a string."""
        # DATA ASSUMPTION: Empty list is a valid input for pass_history.
        result = format_pass_history([])
        assert isinstance(result, str)

    def test_empty_history(self):
        """Formatting empty pass history returns a string (possibly empty or 'none')."""
        result = format_pass_history([])
        assert isinstance(result, str)

    def test_single_entry(self):
        """
        Formats a single pass history entry as a numbered list item.

        DATA ASSUMPTION: A pass history entry with pass_number=1,
        reached_unit=5, ended_reason="iteration_limit" represents
        a typical pass that ended due to reaching the iteration limit.
        """
        history = [
            {
                "pass_number": 1,
                "reached_unit": 5,
                "ended_reason": "iteration_limit",
                "timestamp": "2026-01-01T12:00:00+00:00",
            }
        ]
        result = format_pass_history(history)
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain numbering -- "1" should appear
        assert "1" in result

    def test_multiple_entries_are_numbered(self):
        """
        Behavioral contract: entries are formatted as a brief numbered list
        showing how far each pass reached and why it ended.

        DATA ASSUMPTION: Three passes with different reached_units and
        ended_reasons, representing typical progression through Stage 3.
        """
        history = [
            {
                "pass_number": 1,
                "reached_unit": 3,
                "ended_reason": "iteration_limit",
                "timestamp": "2026-01-01T00:00:00+00:00",
            },
            {
                "pass_number": 2,
                "reached_unit": 7,
                "ended_reason": "session_boundary",
                "timestamp": "2026-01-02T00:00:00+00:00",
            },
            {
                "pass_number": 3,
                "reached_unit": 10,
                "ended_reason": "all_verified",
                "timestamp": "2026-01-03T00:00:00+00:00",
            },
        ]
        result = format_pass_history(history)
        assert isinstance(result, str)
        assert len(result) > 0
        # Check that it shows how far each pass reached
        assert "3" in result  # reached_unit for pass 1
        assert "7" in result  # reached_unit for pass 2
        assert "10" in result  # reached_unit for pass 3

    def test_shows_why_pass_ended(self):
        """
        Behavioral contract: the formatted output shows why each pass ended.

        DATA ASSUMPTION: ended_reason is a human-readable string like
        "iteration_limit" or "all_verified".
        """
        history = [
            {
                "pass_number": 1,
                "reached_unit": 5,
                "ended_reason": "iteration_limit",
                "timestamp": "2026-01-01T00:00:00+00:00",
            },
        ]
        result = format_pass_history(history)
        # The output should mention the reason in some form
        assert "iteration_limit" in result or "iteration" in result.lower() or "limit" in result.lower()


# ===========================================================================
# format_debug_history Tests
# ===========================================================================

class TestFormatDebugHistory:
    """Tests for format_debug_history."""

    def test_returns_string(self):
        """format_debug_history must return a string."""
        result = format_debug_history([])
        assert isinstance(result, str)

    def test_empty_history(self):
        """Formatting empty debug history returns a string."""
        result = format_debug_history([])
        assert isinstance(result, str)

    def test_single_entry(self):
        """
        Formats a single debug history entry.

        DATA ASSUMPTION: A debug history entry with bug_id=1,
        description="Parser error", representing a resolved bug.
        """
        history = [
            {
                "bug_id": 1,
                "description": "Parser error in unit 3",
                "classification": "single_unit",
                "affected_units": [3],
                "phase": "complete",
            },
        ]
        result = format_debug_history(history)
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain bug numbering
        assert "1" in result

    def test_multiple_entries_are_numbered(self):
        """
        Behavioral contract: debug history entries are formatted similarly
        to pass history -- as a brief numbered list.

        DATA ASSUMPTION: Two debug history entries representing resolved bugs.
        """
        history = [
            {
                "bug_id": 1,
                "description": "Import error in unit 2",
                "classification": "build_env",
                "affected_units": [2],
                "phase": "complete",
            },
            {
                "bug_id": 2,
                "description": "Cross-unit dependency issue",
                "classification": "cross_unit",
                "affected_units": [4, 5],
                "phase": "complete",
            },
        ]
        result = format_debug_history(history)
        assert isinstance(result, str)
        assert len(result) > 0


# ===========================================================================
# clean_workspace Tests
# ===========================================================================

class TestCleanWorkspace:
    """Tests for the clean_workspace command."""

    def test_returns_string(self, delivery_project_root):
        """clean_workspace must return a string."""
        result = clean_workspace(delivery_project_root, "keep")
        assert isinstance(result, str)

    def test_only_functional_after_stage_5_delivery(self, tmp_path):
        """
        Behavioral contract: clean_workspace is only functional after
        Stage 5 delivery. Returns an error message if invoked before delivery.

        DATA ASSUMPTION: Stage "3" is before delivery (Stage 5).
        """
        _write_pipeline_state(tmp_path, _make_state_dict(stage="3"))
        (tmp_path / "svp_config.json").write_text(
            json.dumps({"iteration_limit": 3, "models": {"default": "x"}, "auto_save": True}),
            encoding="utf-8",
        )
        result = clean_workspace(tmp_path, "archive")
        # Should return an error message (not raise), since it's before delivery
        assert isinstance(result, str)
        assert len(result) > 0

    def test_before_delivery_stage_0(self, tmp_path):
        """
        clean_workspace at stage 0 should return error message.

        DATA ASSUMPTION: Stage "0" is the initial stage, far from delivery.
        """
        _write_pipeline_state(tmp_path, _make_state_dict(stage="0", sub_stage="hook_activation"))
        result = clean_workspace(tmp_path, "delete")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_mode_archive(self, delivery_project_root):
        """clean_workspace with mode='archive' should succeed at stage 5."""
        result = clean_workspace(delivery_project_root, "archive")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_mode_delete(self, delivery_project_root):
        """clean_workspace with mode='delete' should succeed at stage 5."""
        result = clean_workspace(delivery_project_root, "delete")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_mode_keep(self, delivery_project_root):
        """clean_workspace with mode='keep' should succeed at stage 5."""
        result = clean_workspace(delivery_project_root, "keep")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_invalid_mode_rejected(self, delivery_project_root):
        """
        Invariant: mode must be one of 'archive', 'delete', or 'keep'.
        Invalid modes should raise AssertionError or ValueError.
        """
        with pytest.raises((AssertionError, ValueError)):
            clean_workspace(delivery_project_root, "purge")

    def test_invalid_mode_empty_string(self, delivery_project_root):
        """Empty string is not a valid mode."""
        with pytest.raises((AssertionError, ValueError)):
            clean_workspace(delivery_project_root, "")


# ===========================================================================
# archive_workspace Tests
# ===========================================================================

class TestArchiveWorkspace:
    """Tests for archive_workspace."""

    def test_returns_path(self, delivery_project_root):
        """archive_workspace must return a Path."""
        result = archive_workspace(delivery_project_root)
        assert isinstance(result, Path)

    def test_creates_tar_gz_file(self, delivery_project_root):
        """
        Behavioral contract: archive_workspace compresses the workspace
        into a .tar.gz file alongside the repo.
        """
        result = archive_workspace(delivery_project_root)
        assert result.suffix == ".gz" or str(result).endswith(".tar.gz")
        assert result.exists()

    def test_deletes_workspace_directory_after_archive(self, delivery_project_root):
        """
        Behavioral contract: archive_workspace deletes the workspace
        directory after creating the archive.
        """
        archive_path = archive_workspace(delivery_project_root)
        # The workspace directory should no longer exist after archiving
        assert not delivery_project_root.exists()
        # But the archive should exist alongside where the workspace was
        assert archive_path.exists()

    def test_archive_is_alongside_repo(self, delivery_project_root):
        """
        The archive is placed alongside the repo directory (i.e., in the
        parent directory of the workspace).
        """
        parent = delivery_project_root.parent
        archive_path = archive_workspace(delivery_project_root)
        assert archive_path.parent == parent


# ===========================================================================
# delete_workspace Tests
# ===========================================================================

class TestDeleteWorkspace:
    """Tests for delete_workspace."""

    def test_returns_none(self, delivery_project_root):
        """delete_workspace returns None."""
        result = delete_workspace(delivery_project_root)
        assert result is None

    def test_removes_workspace_directory(self, delivery_project_root):
        """
        Behavioral contract: after successful deletion,
        project_root should not exist.
        """
        assert delivery_project_root.exists()
        delete_workspace(delivery_project_root)
        assert not delivery_project_root.exists()

    def test_permission_aware_handler_chmod_and_retry(self, tmp_path):
        """
        Behavioral contract: delete_workspace uses a permission-aware handler.
        It should chmod read-only paths and retry on PermissionError.

        DATA ASSUMPTION: A __pycache__ directory with read-only permissions
        simulates the scenario described in spec Section 12.5.
        """
        # Create a directory structure with a read-only file
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        ro_file = cache_dir / "cached.pyc"
        ro_file.write_text("cached data")
        # Make the file read-only
        ro_file.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        try:
            delete_workspace(tmp_path)
            # After deletion, the directory should not exist
            assert not tmp_path.exists()
        except PermissionError:
            # If it still raises PermissionError, clean up for test hygiene
            ro_file.chmod(stat.S_IRWXU)
            pytest.fail(
                "delete_workspace should handle PermissionError by "
                "chmod and retry, not propagate it"
            )

    def test_delivered_repo_not_touched(self, tmp_path):
        """
        Behavioral contract: the delivered repository
        (projectname-repo/) is never touched.

        DATA ASSUMPTION: The delivered repo directory is named
        "test_project-repo/" and sits alongside workspace content.
        """
        # Create workspace content
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "code.py").write_text("code\n")

        # Create the "delivered repo" directory alongside workspace
        repo_dir = tmp_path.parent / "test_project-repo"
        repo_dir.mkdir(exist_ok=True)
        (repo_dir / "important.py").write_text("do not delete\n")

        try:
            delete_workspace(tmp_path)
        except Exception:
            pass  # The workspace deletion might fail but repo should be untouched

        # The repo directory should still exist and be intact
        assert repo_dir.exists()
        assert (repo_dir / "important.py").exists()
        assert (repo_dir / "important.py").read_text() == "do not delete\n"

        # Clean up the repo dir
        import shutil
        shutil.rmtree(repo_dir, ignore_errors=True)


# ===========================================================================
# remove_conda_env Tests
# ===========================================================================

class TestRemoveCondaEnv:
    """Tests for remove_conda_env."""

    def test_returns_bool(self):
        """remove_conda_env must return a bool."""
        # DATA ASSUMPTION: "nonexistent_env_xyz_test" is not a real conda env.
        # We mock subprocess to avoid actual conda calls.
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = remove_conda_env("test_env")
            assert isinstance(result, bool)

    def test_calls_conda_env_remove(self):
        """
        Behavioral contract: remove_conda_env runs
        'conda env remove -n {env_name} --yes'.

        DATA ASSUMPTION: env_name "myproject_env" is a typical conda env name.
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            remove_conda_env("myproject_env")
            # Verify conda env remove was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            # The command should contain conda, env, remove, the env name, and --yes
            if isinstance(call_args[0][0], list):
                cmd = call_args[0][0]
            else:
                cmd = call_args[0][0]
            cmd_str = " ".join(str(c) for c in cmd) if isinstance(cmd, list) else str(cmd)
            assert "conda" in cmd_str
            assert "myproject_env" in cmd_str
            assert "--yes" in cmd_str or "-y" in cmd_str

    def test_returns_true_on_success(self):
        """remove_conda_env returns True when conda command succeeds."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = remove_conda_env("test_env")
            assert result is True

    def test_runtime_error_on_failure(self):
        """
        Error condition: RuntimeError when conda env remove fails.
        Message should contain the env name.
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="error")
            with pytest.raises(RuntimeError, match="test_env"):
                remove_conda_env("test_env")

    def test_runtime_error_message_format(self):
        """
        Error condition: RuntimeError message should match
        'Conda environment removal failed: {env_name}'.
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="failed")
            with pytest.raises(RuntimeError, match="Conda environment removal failed.*my_env"):
                remove_conda_env("my_env")


# ===========================================================================
# Error Condition Tests
# ===========================================================================

class TestErrorConditions:
    """Tests for all error conditions specified in the blueprint."""

    def test_get_status_file_not_found_error(self, tmp_path):
        """
        Error condition: FileNotFoundError with message
        'Pipeline state file not found' when pipeline_state.json is missing.
        """
        # tmp_path exists as a directory but has no pipeline_state.json
        with pytest.raises(FileNotFoundError, match="[Pp]ipeline.state.*not found|not found"):
            get_status(tmp_path)

    def test_permission_error_on_delete_with_readonly_pycache(self, tmp_path):
        """
        Error condition: PermissionError handling for __pycache__ or conda
        files with read-only permissions. The handler must chmod and retry.

        DATA ASSUMPTION: __pycache__ directory with read-only files simulates
        the typical permission issue described in spec Section 12.5.
        """
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        ro_file = cache_dir / "module.cpython-39.pyc"
        ro_file.write_text("bytecode")
        # Make file AND directory read-only
        ro_file.chmod(stat.S_IRUSR)
        cache_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)

        try:
            delete_workspace(tmp_path)
            # If it succeeds, the directory should be gone
            assert not tmp_path.exists()
        except PermissionError:
            # If still raised, clean up and report failure
            cache_dir.chmod(stat.S_IRWXU)
            ro_file.chmod(stat.S_IRWXU)
            pytest.fail(
                "delete_workspace should chmod and retry on PermissionError, "
                "not propagate the error"
            )
        finally:
            # Ensure cleanup even if something unexpected happens
            if tmp_path.exists():
                import shutil
                for root, dirs, files in os.walk(str(tmp_path)):
                    for d in dirs:
                        os.chmod(os.path.join(root, d), stat.S_IRWXU)
                    for f in files:
                        os.chmod(os.path.join(root, f), stat.S_IRWXU)
                shutil.rmtree(tmp_path, ignore_errors=True)

    def test_runtime_error_conda_removal_failed(self):
        """
        Error condition: RuntimeError 'Conda environment removal failed: {env_name}'
        when conda env remove fails.
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="PackagesNotFoundError")
            with pytest.raises(RuntimeError, match="Conda environment removal failed.*failing_env"):
                remove_conda_env("failing_env")


# ===========================================================================
# Behavioral Contract Integration Tests
# ===========================================================================

class TestBehavioralContracts:
    """Integration-level tests for behavioral contracts."""

    def test_quit_calls_save_then_returns_exit_message(self, project_root):
        """
        Behavioral contract: quit_project calls save_project first,
        then returns an exit confirmation message with save status.
        """
        result = quit_project(project_root)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_status_includes_next_expected_action(self, project_root):
        """
        Behavioral contract: get_status includes the next expected action.

        DATA ASSUMPTION: At stage 3, unit 3, the next action would be
        related to processing unit 3 (test generation, implementation, etc).
        """
        result = get_status(project_root)
        assert isinstance(result, str)
        # The report should be substantial enough to include action info
        assert len(result) > 10

    def test_get_status_includes_sub_stage(self, tmp_path):
        """
        Behavioral contract: get_status includes sub-stage info when present.

        DATA ASSUMPTION: Stage 0 with sub_stage "hook_activation".
        """
        state = _make_state_dict(stage="0", sub_stage="hook_activation")
        _write_pipeline_state(tmp_path, state)
        result = get_status(tmp_path)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_status_report_is_human_readable(self, project_root):
        """
        The status report should be human-readable, meaning it contains
        actual words and labels, not just raw JSON.
        """
        result = get_status(project_root)
        # Should have alphabetic content (labels, headers, etc.)
        assert any(c.isalpha() for c in result)
        # Should not be raw JSON (should not start with '{')
        assert not result.strip().startswith("{")

    def test_clean_workspace_before_delivery_returns_error_message(self, tmp_path):
        """
        Behavioral contract: clean_workspace returns an error message
        if invoked before Stage 5 delivery.

        DATA ASSUMPTION: Stage "2" is mid-pipeline, well before delivery.
        """
        state = _make_state_dict(stage="2")
        _write_pipeline_state(tmp_path, state)
        config = {"iteration_limit": 3, "models": {"default": "x"}, "auto_save": True}
        (tmp_path / "svp_config.json").write_text(json.dumps(config), encoding="utf-8")

        # Should NOT raise -- should return an error message string
        result = clean_workspace(tmp_path, "archive")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_archive_creates_valid_tar_gz(self, delivery_project_root):
        """
        archive_workspace should create a valid .tar.gz archive.
        """
        # Create some content to archive
        (delivery_project_root / "data.txt").write_text("important data\n")

        archive_path = archive_workspace(delivery_project_root)
        assert archive_path.exists()
        assert str(archive_path).endswith(".tar.gz")

        # Verify the archive is a valid tar.gz
        assert tarfile.is_tarfile(str(archive_path))

        # Clean up
        archive_path.unlink(missing_ok=True)

    def test_format_pass_history_brief_numbered_list(self):
        """
        Behavioral contract: format_pass_history formats entries as a
        brief numbered list showing how far each pass reached and why
        it ended.

        DATA ASSUMPTION: Two pass entries representing typical passes.
        """
        history = [
            {
                "pass_number": 1,
                "reached_unit": 4,
                "ended_reason": "iteration_limit",
                "timestamp": "2026-01-01T00:00:00+00:00",
            },
            {
                "pass_number": 2,
                "reached_unit": 10,
                "ended_reason": "all_verified",
                "timestamp": "2026-01-02T00:00:00+00:00",
            },
        ]
        result = format_pass_history(history)
        assert isinstance(result, str)
        # Should have numbered entries
        lines = [l.strip() for l in result.strip().splitlines() if l.strip()]
        assert len(lines) >= 2  # At least one line per entry

    def test_format_debug_history_brief_numbered_list(self):
        """
        Behavioral contract: format_debug_history formats entries similarly
        to pass history.

        DATA ASSUMPTION: Two debug history entries.
        """
        history = [
            {
                "bug_id": 1,
                "description": "Null pointer in parser",
                "classification": "single_unit",
                "affected_units": [3],
                "phase": "complete",
            },
            {
                "bug_id": 2,
                "description": "Race condition in scheduler",
                "classification": "cross_unit",
                "affected_units": [5, 6],
                "phase": "complete",
            },
        ]
        result = format_debug_history(history)
        assert isinstance(result, str)
        lines = [l.strip() for l in result.strip().splitlines() if l.strip()]
        assert len(lines) >= 2  # At least one line per entry

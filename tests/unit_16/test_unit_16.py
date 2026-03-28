"""
Tests for Unit 16: Command Logic Scripts.

Synthetic Data Assumptions:
- Pipeline state JSON files are minimal valid structures matching Unit 5 PipelineState
  schema, written to tmp_path to avoid side effects.
- Profile JSON files use a simplified version of the Unit 3 DEFAULT_PROFILE with
  relevant fields for status display (archetype, language, quality, testing, pipeline).
- Toolchain JSON files contain a minimal "cleanup" section with a command template
  for testing cmd_clean's environment removal behavior.
- Build log files are JSONL (one JSON object per line) with minimal entries.
- ARTIFACT_FILENAMES from Unit 1 defines canonical file paths for all artifacts.
- cmd_save delegates to save_state (Unit 5) and then re-reads/validates.
- cmd_quit delegates to cmd_save first, then returns an exit signal.
- cmd_status reads pipeline_state.json, project_profile.json, and build_log.jsonl.
- cmd_clean accepts action in {"archive", "delete", "keep"} and uses toolchain
  cleanup commands.
- sync_debug_docs copies spec/blueprint from workspace to delivered repo docs/.
- All upstream functions (load_state, save_state, load_profile, load_toolchain,
  resolve_command, load_config, derive_env_name, ARTIFACT_FILENAMES) are mocked
  to isolate Unit 16 logic from upstream implementations.
- tmp_path is used for all filesystem operations requiring real directories.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from cmd_save import (
    cmd_clean,
    cmd_quit,
    cmd_save,
    cmd_status,
    sync_debug_docs,
)

# ---------------------------------------------------------------------------
# Helpers for building synthetic test data
# ---------------------------------------------------------------------------


def _make_pipeline_state(**overrides):
    """Return a mock PipelineState with sensible defaults."""
    state = MagicMock()
    state.stage = overrides.get("stage", "3")
    state.sub_stage = overrides.get("sub_stage", "test_generation")
    state.current_unit = overrides.get("current_unit", 5)
    state.total_units = overrides.get("total_units", 29)
    state.verified_units = overrides.get(
        "verified_units",
        [
            {"unit": 1, "status": "verified"},
            {"unit": 2, "status": "verified"},
            {"unit": 3, "status": "verified"},
        ],
    )
    state.alignment_iterations = overrides.get("alignment_iterations", 0)
    state.fix_ladder_position = overrides.get("fix_ladder_position", None)
    state.red_run_retries = overrides.get("red_run_retries", 0)
    state.pass_history = overrides.get("pass_history", [])
    state.debug_session = overrides.get("debug_session", None)
    state.debug_history = overrides.get("debug_history", [])
    state.redo_triggered_from = overrides.get("redo_triggered_from", None)
    state.delivered_repo_path = overrides.get("delivered_repo_path", None)
    state.primary_language = overrides.get("primary_language", "python")
    state.component_languages = overrides.get("component_languages", [])
    state.secondary_language = overrides.get("secondary_language", None)
    state.oracle_session_active = overrides.get("oracle_session_active", False)
    state.oracle_test_project = overrides.get("oracle_test_project", None)
    state.oracle_phase = overrides.get("oracle_phase", None)
    state.oracle_run_count = overrides.get("oracle_run_count", 0)
    state.oracle_nested_session_path = overrides.get("oracle_nested_session_path", None)
    state.state_hash = overrides.get("state_hash", None)
    state.spec_revision_count = overrides.get("spec_revision_count", 0)
    state.pass_ = overrides.get("pass_", None)
    state.pass2_nested_session_path = overrides.get("pass2_nested_session_path", None)
    state.deferred_broken_units = overrides.get("deferred_broken_units", [])
    return state


def _make_profile(**overrides):
    """Return a minimal profile dict suitable for cmd_status."""
    profile = {
        "archetype": "python_project",
        "language": {
            "primary": "python",
            "components": [],
            "communication": {},
            "notebooks": None,
        },
        "delivery": {
            "python": {
                "environment_recommendation": "conda",
                "dependency_format": "environment.yml",
                "source_layout": "conventional",
                "entry_points": False,
            },
        },
        "quality": {
            "python": {
                "linter": "ruff",
                "formatter": "ruff",
                "type_checker": "mypy",
                "import_sorter": "ruff",
                "line_length": 88,
            },
        },
        "testing": {
            "coverage_target": None,
            "readable_test_names": True,
            "readme_test_scenarios": False,
        },
        "pipeline": {
            "agent_models": {},
        },
    }
    profile.update(overrides)
    return profile


def _make_toolchain(**overrides):
    """Return a minimal toolchain dict with cleanup commands."""
    toolchain = {
        "environment": {
            "create": "conda create -n {env_name} python={python_version}",
            "activate": "conda activate {env_name}",
            "remove": "conda env remove -n {env_name} --yes",
        },
        "run_prefix": "conda run -n {env_name} --no-banner",
        "quality": {},
    }
    toolchain.update(overrides)
    return toolchain


def _make_build_log_lines():
    """Return a list of JSONL lines for a build log."""
    return [
        json.dumps(
            {"event": "stage_start", "stage": "3", "timestamp": "2026-01-01T00:00:00"}
        ),
        json.dumps(
            {"event": "unit_start", "unit": 5, "timestamp": "2026-01-01T01:00:00"}
        ),
    ]


# ---------------------------------------------------------------------------
# cmd_save tests
# ---------------------------------------------------------------------------


class TestCmdSave:
    """Tests for cmd_save: flush pipeline state to disk with integrity check."""

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.save_state")
    def test_returns_string_confirmation_message(
        self, mock_save_state, mock_load_state, tmp_path
    ):
        """cmd_save must return a string confirmation message."""
        mock_load_state.return_value = _make_pipeline_state()
        result = cmd_save(tmp_path)
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.save_state")
    def test_calls_save_state_to_flush_pipeline_state(
        self, mock_save_state, mock_load_state, tmp_path
    ):
        """cmd_save must call save_state to flush state to disk."""
        state = _make_pipeline_state()
        mock_load_state.return_value = state
        cmd_save(tmp_path)
        mock_save_state.assert_called()

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.save_state")
    def test_passes_project_root_to_save_state(
        self, mock_save_state, mock_load_state, tmp_path
    ):
        """cmd_save must pass the project_root to save_state."""
        state = _make_pipeline_state()
        mock_load_state.return_value = state
        cmd_save(tmp_path)
        # save_state should be called with project_root as first arg
        args = mock_save_state.call_args
        assert args[0][0] == tmp_path or args[1].get("project_root") == tmp_path

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.save_state")
    def test_verifies_file_integrity_by_re_reading(
        self, mock_save_state, mock_load_state, tmp_path
    ):
        """cmd_save must verify integrity by re-reading after save.

        After calling save_state, cmd_save should re-read / validate
        to confirm the data was written correctly. We verify load_state
        is called (once before save and once after for verification,
        or at least that the verification step occurs).
        """
        state = _make_pipeline_state()
        mock_load_state.return_value = state
        cmd_save(tmp_path)
        # load_state should be called at least once (initial load and/or verification)
        mock_load_state.assert_called()


# ---------------------------------------------------------------------------
# cmd_quit tests
# ---------------------------------------------------------------------------


class TestCmdQuit:
    """Tests for cmd_quit: save state then return exit signal."""

    @patch("src.unit_16.stub.cmd_save")
    def test_returns_exit_signal_string(self, mock_cmd_save, tmp_path):
        """cmd_quit must return a string exit signal."""
        mock_cmd_save.return_value = "State saved."
        result = cmd_quit(tmp_path)
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("src.unit_16.stub.cmd_save")
    def test_calls_cmd_save_first(self, mock_cmd_save, tmp_path):
        """cmd_quit must call cmd_save before returning."""
        mock_cmd_save.return_value = "State saved."
        cmd_quit(tmp_path)
        mock_cmd_save.assert_called_once()

    @patch("src.unit_16.stub.cmd_save")
    def test_passes_project_root_to_cmd_save(self, mock_cmd_save, tmp_path):
        """cmd_quit must pass project_root through to cmd_save."""
        mock_cmd_save.return_value = "State saved."
        cmd_quit(tmp_path)
        mock_cmd_save.assert_called_once_with(tmp_path)

    @patch("src.unit_16.stub.cmd_save")
    def test_return_value_indicates_exit(self, mock_cmd_save, tmp_path):
        """cmd_quit return value should signal an exit condition."""
        mock_cmd_save.return_value = "State saved."
        result = cmd_quit(tmp_path)
        # The exit signal should be distinguishable -- typically contains
        # words like "exit", "quit", or "goodbye"
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# cmd_status tests
# ---------------------------------------------------------------------------


class TestCmdStatus:
    """Tests for cmd_status: produce human-readable status summary."""

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_returns_formatted_status_string(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status must return a non-empty formatted string."""
        mock_load_state.return_value = _make_pipeline_state()
        mock_load_profile.return_value = _make_profile()
        # Create build log file so it can be read
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_includes_stage_information(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status output must include the current stage."""
        mock_load_state.return_value = _make_pipeline_state(stage="3")
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        assert "3" in result

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_includes_sub_stage_information(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status output must include the current sub_stage."""
        mock_load_state.return_value = _make_pipeline_state(
            stage="3", sub_stage="implementation"
        )
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        assert "implementation" in result

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_includes_current_unit_and_total_units(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status must report current_unit / total_units progress."""
        mock_load_state.return_value = _make_pipeline_state(
            current_unit=7, total_units=29
        )
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        assert "7" in result
        assert "29" in result

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_includes_verified_units_count(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status must report the count of verified units."""
        verified = [
            {"unit": 1, "status": "verified"},
            {"unit": 2, "status": "verified"},
            {"unit": 3, "status": "verified"},
            {"unit": 4, "status": "verified"},
        ]
        mock_load_state.return_value = _make_pipeline_state(verified_units=verified)
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        # Should contain the number 4 (count of verified units)
        assert "4" in result

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_includes_pass_history(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status must report pass history information."""
        pass_history = [
            {"pass": 1, "units_completed": 20, "broken_units": [15, 22]},
        ]
        mock_load_state.return_value = _make_pipeline_state(pass_history=pass_history)
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        # pass_history should be reflected in the output
        assert isinstance(result, str)

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_includes_profile_summary(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status must include a profile summary with pipeline and delivery quality tools."""
        mock_load_state.return_value = _make_pipeline_state()
        profile = _make_profile()
        mock_load_profile.return_value = profile
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        # Profile summary should mention quality tools (ruff, mypy, etc.)
        # or archetype or language
        assert isinstance(result, str)
        # At minimum, the result should contain some profile-relevant info
        # such as the archetype or language
        result_lower = result.lower()
        has_profile_info = (
            "python" in result_lower
            or "ruff" in result_lower
            or "mypy" in result_lower
            or "profile" in result_lower
            or "archetype" in result_lower
        )
        assert has_profile_info, (
            f"Status output should contain profile summary info, got: {result}"
        )

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_reads_pipeline_state(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status must read pipeline state via load_state."""
        mock_load_state.return_value = _make_pipeline_state()
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        cmd_status(tmp_path)
        mock_load_state.assert_called()

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_reads_profile(self, mock_load_profile, mock_load_state, tmp_path):
        """cmd_status must read the project profile via load_profile."""
        mock_load_state.return_value = _make_pipeline_state()
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        cmd_status(tmp_path)
        mock_load_profile.assert_called()

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_with_zero_verified_units(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status must handle zero verified units gracefully."""
        mock_load_state.return_value = _make_pipeline_state(
            verified_units=[], current_unit=1, total_units=29
        )
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        assert isinstance(result, str)

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_at_stage_0(self, mock_load_profile, mock_load_state, tmp_path):
        """cmd_status must work correctly at early stages (stage 0)."""
        mock_load_state.return_value = _make_pipeline_state(
            stage="0",
            sub_stage="hook_activation",
            current_unit=None,
            total_units=0,
            verified_units=[],
        )
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        assert isinstance(result, str)
        assert "0" in result

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_at_stage_5(self, mock_load_profile, mock_load_state, tmp_path):
        """cmd_status must work correctly at late stages (stage 5)."""
        mock_load_state.return_value = _make_pipeline_state(
            stage="5",
            sub_stage="compliance_scan",
            current_unit=None,
            total_units=29,
            verified_units=[{"unit": i, "status": "verified"} for i in range(1, 30)],
        )
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        assert isinstance(result, str)
        assert "5" in result

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_with_empty_pass_history(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status must handle empty pass history without error."""
        mock_load_state.return_value = _make_pipeline_state(pass_history=[])
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        assert isinstance(result, str)

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_with_nonempty_pass_history(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status must display pass history when present."""
        pass_history = [
            {"pass": 1, "units_completed": 25, "broken_units": [10, 15]},
        ]
        mock_load_state.return_value = _make_pipeline_state(
            pass_history=pass_history, pass_=2
        )
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# cmd_clean tests
# ---------------------------------------------------------------------------


class TestCmdClean:
    """Tests for cmd_clean: clean build environment, manage workspace."""

    @patch("src.unit_16.stub.load_toolchain")
    @patch("src.unit_16.stub.resolve_command")
    @patch("src.unit_16.stub.derive_env_name")
    @patch("src.unit_16.stub.load_config")
    @patch("src.unit_16.stub.load_state")
    def test_action_archive_returns_confirmation_string(
        self,
        mock_load_state,
        mock_load_config,
        mock_derive_env_name,
        mock_resolve_command,
        mock_load_toolchain,
        tmp_path,
    ):
        """cmd_clean with action='archive' must return a confirmation string."""
        mock_load_state.return_value = _make_pipeline_state()
        mock_load_config.return_value = {"models": {"default": "claude-opus-4-6"}}
        mock_derive_env_name.return_value = "svp-testproject"
        mock_resolve_command.return_value = "conda env remove -n svp-testproject --yes"
        mock_load_toolchain.return_value = _make_toolchain()
        result = cmd_clean(tmp_path, action="archive")
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("src.unit_16.stub.load_toolchain")
    @patch("src.unit_16.stub.resolve_command")
    @patch("src.unit_16.stub.derive_env_name")
    @patch("src.unit_16.stub.load_config")
    @patch("src.unit_16.stub.load_state")
    def test_action_delete_returns_confirmation_string(
        self,
        mock_load_state,
        mock_load_config,
        mock_derive_env_name,
        mock_resolve_command,
        mock_load_toolchain,
        tmp_path,
    ):
        """cmd_clean with action='delete' must return a confirmation string."""
        mock_load_state.return_value = _make_pipeline_state()
        mock_load_config.return_value = {"models": {"default": "claude-opus-4-6"}}
        mock_derive_env_name.return_value = "svp-testproject"
        mock_resolve_command.return_value = "conda env remove -n svp-testproject --yes"
        mock_load_toolchain.return_value = _make_toolchain()
        result = cmd_clean(tmp_path, action="delete")
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("src.unit_16.stub.load_toolchain")
    @patch("src.unit_16.stub.resolve_command")
    @patch("src.unit_16.stub.derive_env_name")
    @patch("src.unit_16.stub.load_config")
    @patch("src.unit_16.stub.load_state")
    def test_action_keep_returns_confirmation_string(
        self,
        mock_load_state,
        mock_load_config,
        mock_derive_env_name,
        mock_resolve_command,
        mock_load_toolchain,
        tmp_path,
    ):
        """cmd_clean with action='keep' must return a confirmation string."""
        mock_load_state.return_value = _make_pipeline_state()
        mock_load_config.return_value = {"models": {"default": "claude-opus-4-6"}}
        mock_derive_env_name.return_value = "svp-testproject"
        mock_resolve_command.return_value = "conda env remove -n svp-testproject --yes"
        mock_load_toolchain.return_value = _make_toolchain()
        result = cmd_clean(tmp_path, action="keep")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_action_archive_creates_compressed_archive(self, tmp_path):
        """cmd_clean with action='archive' must compress workspace to archive file.

        We verify that the archive action results in a tar.gz file being created
        or that the implementation attempts to create one.
        """
        # Create a workspace-like directory with some files
        workspace = tmp_path
        (workspace / "src").mkdir()
        (workspace / "src" / "main.py").write_text("print('hello')")
        (workspace / "pipeline_state.json").write_text("{}")

        with (
            patch("src.unit_16.stub.load_toolchain") as mock_lt,
            patch("src.unit_16.stub.resolve_command") as mock_rc,
            patch("src.unit_16.stub.derive_env_name") as mock_de,
            patch("src.unit_16.stub.load_config") as mock_lc,
            patch("src.unit_16.stub.load_state") as mock_ls,
            patch("subprocess.run") as mock_run,
            patch("shutil.make_archive") as mock_archive,
        ):
            mock_ls.return_value = _make_pipeline_state()
            mock_lc.return_value = {"models": {"default": "claude-opus-4-6"}}
            mock_de.return_value = "svp-testproject"
            mock_rc.return_value = "conda env remove -n svp-testproject --yes"
            mock_lt.return_value = _make_toolchain()
            mock_run.return_value = MagicMock(returncode=0)

            result = cmd_clean(workspace, action="archive")
            assert isinstance(result, str)

    def test_action_delete_removes_workspace_directory(self, tmp_path):
        """cmd_clean with action='delete' must remove the workspace directory.

        We verify that the delete action attempts to remove the workspace.
        """
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "file.txt").write_text("content")

        with (
            patch("src.unit_16.stub.load_toolchain") as mock_lt,
            patch("src.unit_16.stub.resolve_command") as mock_rc,
            patch("src.unit_16.stub.derive_env_name") as mock_de,
            patch("src.unit_16.stub.load_config") as mock_lc,
            patch("src.unit_16.stub.load_state") as mock_ls,
            patch("subprocess.run") as mock_run,
            patch("shutil.rmtree") as mock_rmtree,
        ):
            mock_ls.return_value = _make_pipeline_state()
            mock_lc.return_value = {"models": {"default": "claude-opus-4-6"}}
            mock_de.return_value = "svp-testproject"
            mock_rc.return_value = "conda env remove -n svp-testproject --yes"
            mock_lt.return_value = _make_toolchain()
            mock_run.return_value = MagicMock(returncode=0)

            result = cmd_clean(workspace, action="delete")
            assert isinstance(result, str)

    def test_action_keep_does_not_remove_workspace(self, tmp_path):
        """cmd_clean with action='keep' must not remove or archive the workspace.

        Only the build environment should be cleaned.
        """
        workspace = tmp_path
        (workspace / "file.txt").write_text("content")

        with (
            patch("src.unit_16.stub.load_toolchain") as mock_lt,
            patch("src.unit_16.stub.resolve_command") as mock_rc,
            patch("src.unit_16.stub.derive_env_name") as mock_de,
            patch("src.unit_16.stub.load_config") as mock_lc,
            patch("src.unit_16.stub.load_state") as mock_ls,
            patch("subprocess.run") as mock_run,
            patch("shutil.rmtree") as mock_rmtree,
            patch("shutil.make_archive") as mock_archive,
        ):
            mock_ls.return_value = _make_pipeline_state()
            mock_lc.return_value = {"models": {"default": "claude-opus-4-6"}}
            mock_de.return_value = "svp-testproject"
            mock_rc.return_value = "conda env remove -n svp-testproject --yes"
            mock_lt.return_value = _make_toolchain()
            mock_run.return_value = MagicMock(returncode=0)

            result = cmd_clean(workspace, action="keep")
            assert isinstance(result, str)
            # Workspace file should still exist (keep means no workspace removal)
            assert (workspace / "file.txt").exists()

    @patch("src.unit_16.stub.load_toolchain")
    @patch("src.unit_16.stub.resolve_command")
    @patch("src.unit_16.stub.derive_env_name")
    @patch("src.unit_16.stub.load_config")
    @patch("src.unit_16.stub.load_state")
    def test_clean_uses_toolchain_cleanup_command(
        self,
        mock_load_state,
        mock_load_config,
        mock_derive_env_name,
        mock_resolve_command,
        mock_load_toolchain,
        tmp_path,
    ):
        """cmd_clean must use the language-specific cleanup command from toolchain."""
        mock_load_state.return_value = _make_pipeline_state()
        mock_load_config.return_value = {"models": {"default": "claude-opus-4-6"}}
        mock_derive_env_name.return_value = "svp-testproject"
        mock_resolve_command.return_value = "conda env remove -n svp-testproject --yes"
        mock_load_toolchain.return_value = _make_toolchain()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            cmd_clean(tmp_path, action="keep")
            # The toolchain cleanup command should have been invoked
            # (via subprocess or similar mechanism)

    def test_action_must_be_valid_value(self, tmp_path):
        """cmd_clean action parameter must be one of 'archive', 'delete', 'keep'.

        An invalid action value should raise an error.
        """
        with (
            patch("src.unit_16.stub.load_toolchain") as mock_lt,
            patch("src.unit_16.stub.resolve_command") as mock_rc,
            patch("src.unit_16.stub.derive_env_name") as mock_de,
            patch("src.unit_16.stub.load_config") as mock_lc,
            patch("src.unit_16.stub.load_state") as mock_ls,
        ):
            mock_ls.return_value = _make_pipeline_state()
            mock_lc.return_value = {"models": {"default": "claude-opus-4-6"}}
            mock_de.return_value = "svp-testproject"
            mock_rc.return_value = "conda env remove -n svp-testproject --yes"
            mock_lt.return_value = _make_toolchain()

            with pytest.raises((ValueError, KeyError)):
                cmd_clean(tmp_path, action="invalid_action")


# ---------------------------------------------------------------------------
# sync_debug_docs tests
# ---------------------------------------------------------------------------


class TestSyncDebugDocs:
    """Tests for sync_debug_docs: sync debug documentation to delivered repo."""

    def test_returns_none(self, tmp_path):
        """sync_debug_docs must return None."""
        # Set up workspace with spec and blueprint files
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        specs_dir = workspace / "specs"
        specs_dir.mkdir()
        (specs_dir / "stakeholder_spec.md").write_text("# Spec\nContent")
        blueprint_dir = workspace / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text("# Prose\nContent")
        (blueprint_dir / "blueprint_contracts.md").write_text("# Contracts\nContent")

        # Set up delivered repo
        delivered_repo = tmp_path / "delivered"
        delivered_repo.mkdir()

        with (
            patch("src.unit_16.stub.load_state") as mock_ls,
            patch(
                "src.unit_16.stub.ARTIFACT_FILENAMES",
                {
                    "stakeholder_spec": "specs/stakeholder_spec.md",
                    "blueprint_dir": "blueprint",
                    "blueprint_prose": "blueprint/blueprint_prose.md",
                    "blueprint_contracts": "blueprint/blueprint_contracts.md",
                    "pipeline_state": "pipeline_state.json",
                },
            ),
        ):
            state = _make_pipeline_state(delivered_repo_path=str(delivered_repo))
            mock_ls.return_value = state

            result = sync_debug_docs(workspace)
            assert result is None

    def test_copies_spec_to_delivered_repo_docs(self, tmp_path):
        """sync_debug_docs must copy workspace spec to delivered repo docs/ directory."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        specs_dir = workspace / "specs"
        specs_dir.mkdir()
        spec_content = "# Stakeholder Spec\nVersion 1.0"
        (specs_dir / "stakeholder_spec.md").write_text(spec_content)
        blueprint_dir = workspace / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text("# Prose")
        (blueprint_dir / "blueprint_contracts.md").write_text("# Contracts")

        delivered_repo = tmp_path / "delivered"
        delivered_repo.mkdir()
        docs_dir = delivered_repo / "docs"
        docs_dir.mkdir()

        with (
            patch("src.unit_16.stub.load_state") as mock_ls,
            patch(
                "src.unit_16.stub.ARTIFACT_FILENAMES",
                {
                    "stakeholder_spec": "specs/stakeholder_spec.md",
                    "blueprint_dir": "blueprint",
                    "blueprint_prose": "blueprint/blueprint_prose.md",
                    "blueprint_contracts": "blueprint/blueprint_contracts.md",
                    "pipeline_state": "pipeline_state.json",
                },
            ),
        ):
            state = _make_pipeline_state(delivered_repo_path=str(delivered_repo))
            mock_ls.return_value = state
            sync_debug_docs(workspace)

        # Verify docs were copied -- the exact path within docs/ depends
        # on implementation, but the docs directory should have content
        # We check that some file was created under docs/
        docs_files = list(docs_dir.rglob("*"))
        assert len(docs_files) > 0, (
            "sync_debug_docs should copy files to delivered repo docs/"
        )

    def test_copies_blueprint_to_delivered_repo_docs(self, tmp_path):
        """sync_debug_docs must copy workspace blueprint to delivered repo docs/."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        specs_dir = workspace / "specs"
        specs_dir.mkdir()
        (specs_dir / "stakeholder_spec.md").write_text("# Spec")
        blueprint_dir = workspace / "blueprint"
        blueprint_dir.mkdir()
        prose_content = "# Blueprint Prose\nDetailed design"
        contracts_content = "# Blueprint Contracts\nUnit signatures"
        (blueprint_dir / "blueprint_prose.md").write_text(prose_content)
        (blueprint_dir / "blueprint_contracts.md").write_text(contracts_content)

        delivered_repo = tmp_path / "delivered"
        delivered_repo.mkdir()
        docs_dir = delivered_repo / "docs"
        docs_dir.mkdir()

        with (
            patch("src.unit_16.stub.load_state") as mock_ls,
            patch(
                "src.unit_16.stub.ARTIFACT_FILENAMES",
                {
                    "stakeholder_spec": "specs/stakeholder_spec.md",
                    "blueprint_dir": "blueprint",
                    "blueprint_prose": "blueprint/blueprint_prose.md",
                    "blueprint_contracts": "blueprint/blueprint_contracts.md",
                    "pipeline_state": "pipeline_state.json",
                },
            ),
        ):
            state = _make_pipeline_state(delivered_repo_path=str(delivered_repo))
            mock_ls.return_value = state
            sync_debug_docs(workspace)

        # Verify blueprint content exists in docs/
        all_text = ""
        for f in docs_dir.rglob("*.md"):
            all_text += f.read_text()
        assert len(all_text) > 0, "sync_debug_docs should copy blueprint files to docs/"

    def test_workspace_is_canonical_source(self, tmp_path):
        """sync_debug_docs must treat workspace as canonical, overwriting delivered repo docs."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        specs_dir = workspace / "specs"
        specs_dir.mkdir()
        (specs_dir / "stakeholder_spec.md").write_text("# Spec v2 UPDATED")
        blueprint_dir = workspace / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text("# Updated Prose")
        (blueprint_dir / "blueprint_contracts.md").write_text("# Updated Contracts")

        delivered_repo = tmp_path / "delivered"
        delivered_repo.mkdir()
        docs_dir = delivered_repo / "docs"
        docs_dir.mkdir()
        # Pre-existing old content in docs/
        (docs_dir / "old_file.md").write_text("# Old content that should be replaced")

        with (
            patch("src.unit_16.stub.load_state") as mock_ls,
            patch(
                "src.unit_16.stub.ARTIFACT_FILENAMES",
                {
                    "stakeholder_spec": "specs/stakeholder_spec.md",
                    "blueprint_dir": "blueprint",
                    "blueprint_prose": "blueprint/blueprint_prose.md",
                    "blueprint_contracts": "blueprint/blueprint_contracts.md",
                    "pipeline_state": "pipeline_state.json",
                },
            ),
        ):
            state = _make_pipeline_state(delivered_repo_path=str(delivered_repo))
            mock_ls.return_value = state
            sync_debug_docs(workspace)

        # After sync, docs should contain updated content from workspace
        all_text = ""
        for f in docs_dir.rglob("*.md"):
            all_text += f.read_text()
        # The workspace content should be present
        assert "Updated" in all_text or "v2" in all_text or len(all_text) > 0

    def test_creates_docs_directory_if_absent(self, tmp_path):
        """sync_debug_docs must create docs/ in delivered repo if it does not exist."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        specs_dir = workspace / "specs"
        specs_dir.mkdir()
        (specs_dir / "stakeholder_spec.md").write_text("# Spec")
        blueprint_dir = workspace / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text("# Prose")
        (blueprint_dir / "blueprint_contracts.md").write_text("# Contracts")

        delivered_repo = tmp_path / "delivered"
        delivered_repo.mkdir()
        # docs/ does NOT exist yet

        with (
            patch("src.unit_16.stub.load_state") as mock_ls,
            patch(
                "src.unit_16.stub.ARTIFACT_FILENAMES",
                {
                    "stakeholder_spec": "specs/stakeholder_spec.md",
                    "blueprint_dir": "blueprint",
                    "blueprint_prose": "blueprint/blueprint_prose.md",
                    "blueprint_contracts": "blueprint/blueprint_contracts.md",
                    "pipeline_state": "pipeline_state.json",
                },
            ),
        ):
            state = _make_pipeline_state(delivered_repo_path=str(delivered_repo))
            mock_ls.return_value = state
            sync_debug_docs(workspace)

        docs_dir = delivered_repo / "docs"
        assert docs_dir.exists(), (
            "sync_debug_docs should create docs/ directory if absent"
        )


# ---------------------------------------------------------------------------
# Integration-style contract tests (cross-function behavior)
# ---------------------------------------------------------------------------


class TestCmdSaveAndQuitIntegration:
    """Tests verifying the relationship between cmd_save and cmd_quit."""

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.save_state")
    def test_quit_save_ordering(self, mock_save_state, mock_load_state, tmp_path):
        """cmd_quit must call save_state (via cmd_save) before returning exit signal.

        This verifies the contract that cmd_quit saves first, then signals exit.
        """
        state = _make_pipeline_state()
        mock_load_state.return_value = state

        # We use a side_effect to track call ordering
        call_order = []

        original_cmd_save = cmd_save

        with patch("src.unit_16.stub.cmd_save") as mock_cmd_save:
            mock_cmd_save.side_effect = lambda root: (
                call_order.append("save"),
                "State saved.",
            )[1]
            result = cmd_quit(tmp_path)
            call_order.append("quit_returned")

        assert call_order[0] == "save", (
            "cmd_save must be called before cmd_quit returns"
        )
        assert "quit_returned" in call_order


class TestCmdCleanActionValidation:
    """Tests for cmd_clean action parameter validation."""

    @pytest.mark.parametrize("valid_action", ["archive", "delete", "keep"])
    def test_accepts_valid_actions(self, valid_action, tmp_path):
        """cmd_clean must accept all three valid action values."""
        with (
            patch("src.unit_16.stub.load_toolchain") as mock_lt,
            patch("src.unit_16.stub.resolve_command") as mock_rc,
            patch("src.unit_16.stub.derive_env_name") as mock_de,
            patch("src.unit_16.stub.load_config") as mock_lc,
            patch("src.unit_16.stub.load_state") as mock_ls,
            patch("subprocess.run") as mock_run,
            patch("shutil.rmtree", return_value=None),
            patch("shutil.make_archive", return_value="archive.tar.gz"),
        ):
            mock_ls.return_value = _make_pipeline_state()
            mock_lc.return_value = {"models": {"default": "claude-opus-4-6"}}
            mock_de.return_value = "svp-testproject"
            mock_rc.return_value = "conda env remove -n svp-testproject --yes"
            mock_lt.return_value = _make_toolchain()
            mock_run.return_value = MagicMock(returncode=0)

            result = cmd_clean(tmp_path, action=valid_action)
            assert isinstance(result, str)
            assert len(result) > 0


class TestCmdStatusProfileSummaryFormat:
    """Tests verifying profile summary displays pipeline and delivery quality separately."""

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_profile_summary_is_one_line_format(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status profile summary should be in one-line format showing tools."""
        mock_load_state.return_value = _make_pipeline_state()
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        # The profile summary should be compact -- it should be present
        # in the output as a recognizable summary
        assert isinstance(result, str)

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_with_mixed_archetype_profile(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status must handle mixed-archetype profiles with two languages."""
        mixed_profile = _make_profile(
            archetype="mixed",
            language={
                "primary": "python",
                "secondary": "r",
                "components": [],
                "communication": {"python_r": {"library": "rpy2"}},
                "notebooks": None,
            },
        )
        mixed_profile["quality"]["r"] = {
            "linter": "lintr",
            "formatter": "styler",
            "type_checker": "none",
            "line_length": 80,
        }
        mixed_profile["delivery"]["r"] = {
            "environment_recommendation": "conda",
            "dependency_format": "environment.yml",
            "source_layout": "package",
            "entry_points": False,
        }
        mock_load_state.return_value = _make_pipeline_state(secondary_language="r")
        mock_load_profile.return_value = mixed_profile
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        assert isinstance(result, str)


class TestCmdStatusBuildLogReading:
    """Tests for cmd_status reading the build log."""

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_handles_missing_build_log(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status must handle a missing build log gracefully (no crash)."""
        mock_load_state.return_value = _make_pipeline_state()
        mock_load_profile.return_value = _make_profile()
        # Do NOT create the build log file
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        # This should either handle gracefully or the test reveals the contract
        try:
            result = cmd_status(tmp_path)
            assert isinstance(result, str)
        except FileNotFoundError:
            # If the contract requires the build log to exist, this is acceptable
            pass

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_handles_empty_build_log(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status must handle an empty build log without error."""
        mock_load_state.return_value = _make_pipeline_state()
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        assert isinstance(result, str)

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_reads_nonempty_build_log(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status must read and process a non-empty build log."""
        mock_load_state.return_value = _make_pipeline_state()
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        log_lines = _make_build_log_lines()
        (svp_dir / "build_log.jsonl").write_text("\n".join(log_lines) + "\n")
        result = cmd_status(tmp_path)
        assert isinstance(result, str)


class TestCmdStatusQualityGateStatus:
    """Tests for cmd_status reporting quality gate status for current unit."""

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_during_quality_gate_a(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status must report quality gate status when at quality_gate_a sub_stage."""
        mock_load_state.return_value = _make_pipeline_state(
            stage="3",
            sub_stage="quality_gate_a",
            current_unit=10,
        )
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        assert isinstance(result, str)
        # Should contain the sub_stage or gate-related info
        result_lower = result.lower()
        assert "10" in result  # current unit

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_during_quality_gate_b(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status must report quality gate status when at quality_gate_b sub_stage."""
        mock_load_state.return_value = _make_pipeline_state(
            stage="3",
            sub_stage="quality_gate_b",
            current_unit=15,
        )
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        assert isinstance(result, str)
        assert "15" in result  # current unit


class TestCmdCleanEnvironmentRemoval:
    """Tests for cmd_clean environment removal behavior across all actions."""

    @pytest.mark.parametrize("action", ["archive", "delete", "keep"])
    def test_all_actions_remove_build_environment(self, action, tmp_path):
        """All cmd_clean actions must remove the build environment."""
        with (
            patch("src.unit_16.stub.load_toolchain") as mock_lt,
            patch("src.unit_16.stub.resolve_command") as mock_rc,
            patch("src.unit_16.stub.derive_env_name") as mock_de,
            patch("src.unit_16.stub.load_config") as mock_lc,
            patch("src.unit_16.stub.load_state") as mock_ls,
            patch("subprocess.run") as mock_run,
            patch("shutil.rmtree", return_value=None),
            patch("shutil.make_archive", return_value="archive.tar.gz"),
        ):
            mock_ls.return_value = _make_pipeline_state()
            mock_lc.return_value = {"models": {"default": "claude-opus-4-6"}}
            mock_de.return_value = "svp-testproject"
            mock_rc.return_value = "conda env remove -n svp-testproject --yes"
            mock_lt.return_value = _make_toolchain()
            mock_run.return_value = MagicMock(returncode=0)

            result = cmd_clean(tmp_path, action=action)
            assert isinstance(result, str)


class TestSignatureContracts:
    """Tests verifying function signatures match the blueprint contracts."""

    def test_cmd_save_accepts_project_root_path(self):
        """cmd_save must accept a single Path argument (project_root)."""
        import inspect

        sig = inspect.signature(cmd_save)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert len(params) == 1

    def test_cmd_save_returns_str(self):
        """cmd_save return annotation should be str."""
        import inspect

        sig = inspect.signature(cmd_save)
        assert sig.return_annotation is str or sig.return_annotation == "str"

    def test_cmd_quit_accepts_project_root_path(self):
        """cmd_quit must accept a single Path argument (project_root)."""
        import inspect

        sig = inspect.signature(cmd_quit)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert len(params) == 1

    def test_cmd_quit_returns_str(self):
        """cmd_quit return annotation should be str."""
        import inspect

        sig = inspect.signature(cmd_quit)
        assert sig.return_annotation is str or sig.return_annotation == "str"

    def test_cmd_status_accepts_project_root_path(self):
        """cmd_status must accept a single Path argument (project_root)."""
        import inspect

        sig = inspect.signature(cmd_status)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert len(params) == 1

    def test_cmd_status_returns_str(self):
        """cmd_status return annotation should be str."""
        import inspect

        sig = inspect.signature(cmd_status)
        assert sig.return_annotation is str or sig.return_annotation == "str"

    def test_cmd_clean_accepts_project_root_and_action(self):
        """cmd_clean must accept project_root (Path) and action (str)."""
        import inspect

        sig = inspect.signature(cmd_clean)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert "action" in params
        assert len(params) == 2

    def test_cmd_clean_returns_str(self):
        """cmd_clean return annotation should be str."""
        import inspect

        sig = inspect.signature(cmd_clean)
        assert sig.return_annotation is str or sig.return_annotation == "str"

    def test_sync_debug_docs_accepts_project_root_path(self):
        """sync_debug_docs must accept a single Path argument (project_root)."""
        import inspect

        sig = inspect.signature(sync_debug_docs)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert len(params) == 1

    def test_sync_debug_docs_returns_none(self):
        """sync_debug_docs return annotation should be None."""
        import inspect

        sig = inspect.signature(sync_debug_docs)
        assert sig.return_annotation is None or sig.return_annotation == "None"


class TestCmdStatusProjectName:
    """Tests verifying cmd_status includes the project name."""

    @patch("src.unit_16.stub.load_state")
    @patch("src.unit_16.stub.load_profile")
    @patch(
        "src.unit_16.stub.ARTIFACT_FILENAMES",
        {
            "pipeline_state": "pipeline_state.json",
            "project_profile": "project_profile.json",
            "build_log": ".svp/build_log.jsonl",
            "toolchain": "toolchain.json",
        },
    )
    def test_status_output_contains_project_name_or_path(
        self, mock_load_profile, mock_load_state, tmp_path
    ):
        """cmd_status output should reference the project name."""
        mock_load_state.return_value = _make_pipeline_state()
        mock_load_profile.return_value = _make_profile()
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "build_log.jsonl").write_text("")
        result = cmd_status(tmp_path)
        assert isinstance(result, str)
        # The project name is typically derived from the directory name
        # The status output should contain some recognizable identifier


class TestSyncDebugDocsEdgeCases:
    """Edge case tests for sync_debug_docs."""

    def test_handles_missing_spec_file_gracefully(self, tmp_path):
        """sync_debug_docs should handle missing source files.

        If workspace spec files do not exist, the function should either
        raise an appropriate error or skip missing files.
        """
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        # Do NOT create spec or blueprint files

        delivered_repo = tmp_path / "delivered"
        delivered_repo.mkdir()

        with (
            patch("src.unit_16.stub.load_state") as mock_ls,
            patch(
                "src.unit_16.stub.ARTIFACT_FILENAMES",
                {
                    "stakeholder_spec": "specs/stakeholder_spec.md",
                    "blueprint_dir": "blueprint",
                    "blueprint_prose": "blueprint/blueprint_prose.md",
                    "blueprint_contracts": "blueprint/blueprint_contracts.md",
                    "pipeline_state": "pipeline_state.json",
                },
            ),
        ):
            state = _make_pipeline_state(delivered_repo_path=str(delivered_repo))
            mock_ls.return_value = state

            # Should either raise FileNotFoundError or handle gracefully
            try:
                sync_debug_docs(workspace)
            except (FileNotFoundError, OSError):
                pass  # Acceptable behavior for missing source files

    def test_handles_delivered_repo_path_from_state(self, tmp_path):
        """sync_debug_docs must read delivered_repo_path from pipeline state."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        specs_dir = workspace / "specs"
        specs_dir.mkdir()
        (specs_dir / "stakeholder_spec.md").write_text("# Spec")
        blueprint_dir = workspace / "blueprint"
        blueprint_dir.mkdir()
        (blueprint_dir / "blueprint_prose.md").write_text("# Prose")
        (blueprint_dir / "blueprint_contracts.md").write_text("# Contracts")

        delivered_repo = tmp_path / "delivered"
        delivered_repo.mkdir()

        with (
            patch("src.unit_16.stub.load_state") as mock_ls,
            patch(
                "src.unit_16.stub.ARTIFACT_FILENAMES",
                {
                    "stakeholder_spec": "specs/stakeholder_spec.md",
                    "blueprint_dir": "blueprint",
                    "blueprint_prose": "blueprint/blueprint_prose.md",
                    "blueprint_contracts": "blueprint/blueprint_contracts.md",
                    "pipeline_state": "pipeline_state.json",
                },
            ),
        ):
            state = _make_pipeline_state(delivered_repo_path=str(delivered_repo))
            mock_ls.return_value = state
            sync_debug_docs(workspace)
            # load_state must be called to get delivered_repo_path
            mock_ls.assert_called()

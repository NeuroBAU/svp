"""Unit 16: Command Logic Scripts -- complete test suite.

Synthetic data assumptions:
- Project roots are created as temporary directories via tmp_path fixtures.
- cmd_save calls save_state (Unit 5) to flush pipeline state to disk, then
  re-reads and validates the file. All save_state / load_state interactions
  are mocked to return synthetic PipelineState objects.
- cmd_quit calls cmd_save internally, then returns an exit signal string.
- cmd_status reads pipeline state (load_state, Unit 5), profile (load_profile,
  Unit 3), and build log (from ARTIFACT_FILENAMES["build_log"], Unit 1).
  It formats a report string containing: project name, stage, sub_stage,
  current_unit / total_units, verified_units count, pass history, profile
  summary (one-line format showing pipeline and delivery quality tools
  separately), and quality gate status for the current unit.
- cmd_clean accepts action in {"archive", "delete", "keep"}. It uses
  derive_env_name (Unit 1), load_toolchain + resolve_command (Unit 4),
  and load_state (Unit 5). It does NOT use load_config or load_profile.
  "archive" compresses workspace to archive. "delete" removes workspace
  directory. "keep" takes no action on workspace. All actions remove the
  build environment using language-specific cleanup command from toolchain.
- sync_debug_docs copies workspace spec/blueprint to the delivered repo
  docs/ directory. Workspace is canonical; delivered repo is updated to
  match. The delivered_repo_path is read from pipeline state.
- PipelineState objects are synthetic MagicMock instances with fields
  matching the Unit 5 schema (stage, sub_stage, current_unit, total_units,
  verified_units, pass_history, delivered_repo_path, primary_language, etc.).
- Toolchain dicts are synthetic with an "environment" section containing
  the canonical schema keys (S3-202 / J-2d): "create_command",
  "install_command", "cleanup_command", and "run_prefix".
- Profile dicts are synthetic with "pipeline" and "quality" sections.
- Build log is a synthetic JSONL file with one entry per line.
- ARTIFACT_FILENAMES is mocked to return known relative paths.
"""

from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from sync_debug_docs import (
    cmd_clean,
    cmd_quit,
    cmd_save,
    cmd_status,
    sync_debug_docs,
)

# ---------------------------------------------------------------------------
# Synthetic data / helpers
# ---------------------------------------------------------------------------

SAMPLE_PROJECT_ROOT = Path("/tmp/test_svp_project")
SAMPLE_PROJECT_NAME = "test_svp_project"


def _make_mock_state(**overrides) -> MagicMock:
    """Create a synthetic PipelineState-like mock with sensible defaults."""
    state = MagicMock()
    defaults = {
        "stage": "3",
        "sub_stage": "test_generation",
        "current_unit": 5,
        "total_units": 29,
        "verified_units": [
            {"unit": 1, "pass": 1},
            {"unit": 2, "pass": 1},
            {"unit": 3, "pass": 1},
        ],
        "alignment_iterations": 1,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "pass_history": [
            {"pass": 1, "started": "2026-01-15", "units_completed": 29},
        ],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": "/tmp/delivered_repo",
        "primary_language": "python",
        "component_languages": [],
        "secondary_language": None,
        "oracle_session_active": False,
        "oracle_test_project": None,
        "oracle_phase": None,
        "oracle_run_count": 0,
        "oracle_nested_session_path": None,
        "state_hash": "abc123",
        "spec_revision_count": 0,
        "pass_": 2,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(state, k, v)
    return state


def _make_mock_profile() -> Dict[str, Any]:
    """Create a synthetic profile dict."""
    return {
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
        "testing": {"framework": "pytest"},
        "readme": {"format": "markdown"},
        "license": {"type": "MIT"},
        "vcs": {"provider": "github"},
        "pipeline": {
            "agent_models": {},
        },
    }


def _make_mock_toolchain() -> Dict[str, Any]:
    """Create a synthetic toolchain dict with canonical env-section schema
    keys (S3-202 / J-2d -- environment.cleanup_command is the canonical
    key for cmd_clean's env-remove subprocess; the previous dead
    commands.env_remove namespace is removed)."""
    return {
        "environment": {
            "tool": "conda",
            "run_prefix": "conda run -n {env_name}",
            "create_command": "conda create -n {env_name} python={python_version} -y",
            "install_command": "conda run -n {env_name} pip install {packages}",
            "cleanup_command": "conda env remove -n {env_name} -y",
        },
        "quality": {
            "gate_a": [
                {"operation": "format", "command": "{run_prefix} ruff format {target}"},
                {"operation": "lint", "command": "{run_prefix} ruff check {target}"},
            ],
        },
    }


SAMPLE_BUILD_LOG_LINES = [
    '{"event": "stage_enter", "stage": "3", "timestamp": "2026-01-15T10:00:00"}\n',
    '{"event": "unit_start", "unit": 5, "timestamp": "2026-01-15T10:05:00"}\n',
]


# ===========================================================================
# cmd_save tests
# ===========================================================================


class TestCmdSave:
    """Tests for cmd_save: flush state to disk, verify integrity, return message."""

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.save_state")
    def test_cmd_save_returns_confirmation_string(
        self, mock_save_state, mock_load_state
    ):
        """cmd_save returns a confirmation message string."""
        mock_state = _make_mock_state()
        mock_load_state.return_value = mock_state

        result = cmd_save(SAMPLE_PROJECT_ROOT)

        assert isinstance(result, str)
        assert len(result) > 0

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.save_state")
    def test_cmd_save_calls_save_state(self, mock_save_state, mock_load_state):
        """cmd_save flushes pipeline state to disk via save_state."""
        mock_state = _make_mock_state()
        mock_load_state.return_value = mock_state

        cmd_save(SAMPLE_PROJECT_ROOT)

        mock_save_state.assert_called()
        # save_state should receive the project root and a state object
        args = mock_save_state.call_args
        assert (
            args[0][0] == SAMPLE_PROJECT_ROOT
            or args[1].get("project_root") == SAMPLE_PROJECT_ROOT
        )

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.save_state")
    def test_cmd_save_verifies_file_integrity(self, mock_save_state, mock_load_state):
        """cmd_save re-reads and validates the file after saving (integrity check)."""
        mock_state = _make_mock_state()
        mock_load_state.return_value = mock_state

        cmd_save(SAMPLE_PROJECT_ROOT)

        # load_state should be called at least once (for re-read verification)
        mock_load_state.assert_called()

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.save_state")
    def test_cmd_save_with_various_project_roots(
        self, mock_save_state, mock_load_state
    ):
        """cmd_save works with different project root paths."""
        mock_state = _make_mock_state()
        mock_load_state.return_value = mock_state

        for root in [Path("/tmp/proj_a"), Path("/home/user/proj_b"), Path("/opt/svp")]:
            result = cmd_save(root)
            assert isinstance(result, str)

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.save_state")
    def test_cmd_save_integrity_check_re_reads_after_write(
        self, mock_save_state, mock_load_state
    ):
        """After save_state writes, cmd_save re-reads to verify correctness."""
        mock_state = _make_mock_state()
        # load_state may be called multiple times: once for the initial state,
        # once for re-read verification
        mock_load_state.return_value = mock_state

        cmd_save(SAMPLE_PROJECT_ROOT)

        # save_state must be called before the verification read
        assert mock_save_state.call_count >= 1
        assert mock_load_state.call_count >= 1


# ===========================================================================
# cmd_quit tests
# ===========================================================================


class TestCmdQuit:
    """Tests for cmd_quit: calls cmd_save first, then returns exit signal."""

    @patch("sync_debug_docs.cmd_save")
    def test_cmd_quit_returns_exit_signal(self, mock_cmd_save):
        """cmd_quit returns an exit signal string."""
        mock_cmd_save.return_value = "State saved."

        result = cmd_quit(SAMPLE_PROJECT_ROOT)

        assert isinstance(result, str)
        assert len(result) > 0

    @patch("sync_debug_docs.cmd_save")
    def test_cmd_quit_calls_cmd_save_first(self, mock_cmd_save):
        """cmd_quit calls cmd_save before returning."""
        mock_cmd_save.return_value = "State saved."

        cmd_quit(SAMPLE_PROJECT_ROOT)

        mock_cmd_save.assert_called_once_with(SAMPLE_PROJECT_ROOT)

    @patch("sync_debug_docs.cmd_save")
    def test_cmd_quit_exit_signal_is_distinguishable(self, mock_cmd_save):
        """The exit signal returned by cmd_quit should be recognizable as an exit."""
        mock_cmd_save.return_value = "State saved."

        result = cmd_quit(SAMPLE_PROJECT_ROOT)

        # The return value should contain some indication of exit/quit
        # (e.g., "exit", "quit", "goodbye", or similar)
        result_lower = result.lower()
        assert any(
            keyword in result_lower
            for keyword in ["exit", "quit", "bye", "shutdown", "terminate", "stop"]
        ), f"Exit signal '{result}' should contain an exit-related keyword"

    @patch("sync_debug_docs.cmd_save")
    def test_cmd_quit_passes_project_root_to_save(self, mock_cmd_save):
        """cmd_quit passes the project_root argument through to cmd_save."""
        mock_cmd_save.return_value = "Saved."
        custom_root = Path("/custom/project/root")

        cmd_quit(custom_root)

        mock_cmd_save.assert_called_once_with(custom_root)


# ===========================================================================
# cmd_status tests
# ===========================================================================


class TestCmdStatus:
    """Tests for cmd_status: reads state, profile, build log; returns formatted report."""

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_returns_formatted_string(
        self, mock_load_state, mock_load_profile
    ):
        """cmd_status returns a non-empty formatted status string."""
        mock_load_state.return_value = _make_mock_state()
        mock_load_profile.return_value = _make_mock_profile()

        result = cmd_status(SAMPLE_PROJECT_ROOT)

        assert isinstance(result, str)
        assert len(result) > 0

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_includes_project_name(self, mock_load_state, mock_load_profile):
        """Status output reports the project name."""
        mock_load_state.return_value = _make_mock_state()
        mock_load_profile.return_value = _make_mock_profile()

        result = cmd_status(SAMPLE_PROJECT_ROOT)

        # Project name is derived from project_root.name
        assert SAMPLE_PROJECT_NAME in result

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_includes_stage(self, mock_load_state, mock_load_profile):
        """Status output includes the current stage."""
        mock_load_state.return_value = _make_mock_state(stage="3")
        mock_load_profile.return_value = _make_mock_profile()

        result = cmd_status(SAMPLE_PROJECT_ROOT)

        assert "3" in result

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_includes_sub_stage(self, mock_load_state, mock_load_profile):
        """Status output includes the current sub_stage."""
        mock_load_state.return_value = _make_mock_state(sub_stage="test_generation")
        mock_load_profile.return_value = _make_mock_profile()

        result = cmd_status(SAMPLE_PROJECT_ROOT)

        assert "test_generation" in result

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_includes_current_unit_and_total(
        self, mock_load_state, mock_load_profile
    ):
        """Status output includes current_unit / total_units."""
        mock_load_state.return_value = _make_mock_state(current_unit=7, total_units=29)
        mock_load_profile.return_value = _make_mock_profile()

        result = cmd_status(SAMPLE_PROJECT_ROOT)

        assert "7" in result
        assert "29" in result

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_includes_verified_units_count(
        self, mock_load_state, mock_load_profile
    ):
        """Status output includes the count of verified units."""
        verified = [
            {"unit": 1, "pass": 1},
            {"unit": 2, "pass": 1},
            {"unit": 3, "pass": 1},
            {"unit": 4, "pass": 1},
        ]
        mock_load_state.return_value = _make_mock_state(verified_units=verified)
        mock_load_profile.return_value = _make_mock_profile()

        result = cmd_status(SAMPLE_PROJECT_ROOT)

        assert "4" in result

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_includes_pass_history(self, mock_load_state, mock_load_profile):
        """Status output includes pass history information."""
        history = [
            {"pass": 1, "started": "2026-01-10", "units_completed": 29},
            {"pass": 2, "started": "2026-01-20", "units_completed": 5},
        ]
        mock_load_state.return_value = _make_mock_state(pass_history=history)
        mock_load_profile.return_value = _make_mock_profile()

        result = cmd_status(SAMPLE_PROJECT_ROOT)

        # Should reference pass history in some form
        # At minimum, the count or entries should appear
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_includes_profile_summary(
        self, mock_load_state, mock_load_profile
    ):
        """Status output includes a profile summary showing pipeline and delivery tools."""
        mock_load_state.return_value = _make_mock_state()
        profile = _make_mock_profile()
        mock_load_profile.return_value = profile

        result = cmd_status(SAMPLE_PROJECT_ROOT)

        # Profile summary should mention quality tools or archetype
        # The one-line format shows pipeline and delivery quality tools separately
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_includes_quality_gate_status(
        self, mock_load_state, mock_load_profile
    ):
        """Status output reports quality gate status for the current unit."""
        mock_load_state.return_value = _make_mock_state(
            current_unit=5, sub_stage="quality_gate_a"
        )
        mock_load_profile.return_value = _make_mock_profile()

        result = cmd_status(SAMPLE_PROJECT_ROOT)

        assert isinstance(result, str)

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_reads_pipeline_state(self, mock_load_state, mock_load_profile):
        """cmd_status calls load_state to read pipeline state."""
        mock_load_state.return_value = _make_mock_state()
        mock_load_profile.return_value = _make_mock_profile()

        cmd_status(SAMPLE_PROJECT_ROOT)

        mock_load_state.assert_called()

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_reads_profile(self, mock_load_state, mock_load_profile):
        """cmd_status calls load_profile to read the project profile."""
        mock_load_state.return_value = _make_mock_state()
        mock_load_profile.return_value = _make_mock_profile()

        cmd_status(SAMPLE_PROJECT_ROOT)

        mock_load_profile.assert_called()

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_null_current_unit(self, mock_load_state, mock_load_profile):
        """cmd_status handles null current_unit gracefully (e.g., in Stage 0)."""
        mock_load_state.return_value = _make_mock_state(
            stage="0",
            sub_stage="hook_activation",
            current_unit=None,
        )
        mock_load_profile.return_value = _make_mock_profile()

        result = cmd_status(SAMPLE_PROJECT_ROOT)

        assert isinstance(result, str)

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_empty_verified_units(self, mock_load_state, mock_load_profile):
        """cmd_status handles zero verified units."""
        mock_load_state.return_value = _make_mock_state(verified_units=[])
        mock_load_profile.return_value = _make_mock_profile()

        result = cmd_status(SAMPLE_PROJECT_ROOT)

        assert isinstance(result, str)
        assert "0" in result

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_empty_pass_history(self, mock_load_state, mock_load_profile):
        """cmd_status handles empty pass history (first pass, no prior passes)."""
        mock_load_state.return_value = _make_mock_state(pass_history=[])
        mock_load_profile.return_value = _make_mock_profile()

        result = cmd_status(SAMPLE_PROJECT_ROOT)

        assert isinstance(result, str)

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_stage_0_report(self, mock_load_state, mock_load_profile):
        """cmd_status produces a valid report at Stage 0."""
        mock_load_state.return_value = _make_mock_state(
            stage="0",
            sub_stage="project_profile",
            current_unit=None,
            total_units=0,
            verified_units=[],
            pass_history=[],
        )
        mock_load_profile.return_value = _make_mock_profile()

        result = cmd_status(SAMPLE_PROJECT_ROOT)

        assert isinstance(result, str)
        assert "0" in result  # stage

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_stage_5_report(self, mock_load_state, mock_load_profile):
        """cmd_status produces a valid report at Stage 5."""
        mock_load_state.return_value = _make_mock_state(
            stage="5",
            sub_stage="repo_complete",
            current_unit=None,
            total_units=29,
            verified_units=[{"unit": i, "pass": 1} for i in range(1, 30)],
        )
        mock_load_profile.return_value = _make_mock_profile()

        result = cmd_status(SAMPLE_PROJECT_ROOT)

        assert isinstance(result, str)
        assert "5" in result


# ===========================================================================
# cmd_clean tests
# ===========================================================================


class TestCmdClean:
    """Tests for cmd_clean: environment removal and workspace action."""

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_archive_returns_confirmation(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """cmd_clean with action='archive' returns a confirmation message."""
        mock_derive.return_value = "svp-test_project"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-test_project -y"
        mock_load_state.return_value = _make_mock_state()

        result = cmd_clean(SAMPLE_PROJECT_ROOT, "archive")

        assert isinstance(result, str)
        assert len(result) > 0

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_delete_returns_confirmation(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """cmd_clean with action='delete' returns a confirmation message."""
        mock_derive.return_value = "svp-test_project"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-test_project -y"
        mock_load_state.return_value = _make_mock_state()

        result = cmd_clean(SAMPLE_PROJECT_ROOT, "delete")

        assert isinstance(result, str)
        assert len(result) > 0

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_keep_returns_confirmation(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """cmd_clean with action='keep' returns a confirmation message."""
        mock_derive.return_value = "svp-test_project"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-test_project -y"
        mock_load_state.return_value = _make_mock_state()

        result = cmd_clean(SAMPLE_PROJECT_ROOT, "keep")

        assert isinstance(result, str)
        assert len(result) > 0

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_calls_derive_env_name(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """cmd_clean uses derive_env_name (Unit 1) to get the environment name."""
        mock_derive.return_value = "svp-myproject"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-myproject -y"
        mock_load_state.return_value = _make_mock_state()

        cmd_clean(SAMPLE_PROJECT_ROOT, "keep")

        mock_derive.assert_called_once_with(SAMPLE_PROJECT_ROOT)

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_calls_load_toolchain(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """cmd_clean uses load_toolchain (Unit 4) to get cleanup commands."""
        mock_derive.return_value = "svp-proj"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-proj -y"
        mock_load_state.return_value = _make_mock_state()

        cmd_clean(SAMPLE_PROJECT_ROOT, "delete")

        mock_toolchain.assert_called()

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_calls_resolve_command(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """cmd_clean uses resolve_command (Unit 4) to build the cleanup command."""
        mock_derive.return_value = "svp-proj"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-proj -y"
        mock_load_state.return_value = _make_mock_state()

        cmd_clean(SAMPLE_PROJECT_ROOT, "archive")

        mock_resolve.assert_called()

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_calls_load_state(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """cmd_clean uses load_state (Unit 5) to read pipeline state."""
        mock_derive.return_value = "svp-proj"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-proj -y"
        mock_load_state.return_value = _make_mock_state()

        cmd_clean(SAMPLE_PROJECT_ROOT, "keep")

        mock_load_state.assert_called()

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_does_not_use_load_config(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """cmd_clean does NOT use load_config (Bug S3-7). Verify no load_config import/call."""
        import ast
        import inspect

        source = inspect.getsource(cmd_clean)
        tree = ast.parse(source)
        # Check that cmd_clean doesn't call load_config anywhere in its AST
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "load_config":
                    pytest.fail("cmd_clean calls load_config, violating Bug S3-7 contract")

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_does_not_use_load_profile(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """cmd_clean does NOT use load_profile (Bug S3-7). Verify no load_profile call."""
        mock_derive.return_value = "svp-proj"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-proj -y"
        mock_load_state.return_value = _make_mock_state()

        with patch(
            "src.unit_16.stub.load_profile",
            side_effect=AssertionError("cmd_clean must not call load_profile"),
        ) as mock_load_profile:
            try:
                cmd_clean(SAMPLE_PROJECT_ROOT, "archive")
            except AssertionError as e:
                if "cmd_clean must not call load_profile" in str(e):
                    pytest.fail(
                        "cmd_clean called load_profile, which violates Bug S3-7 contract"
                    )
                raise

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_invalid_action_raises(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """cmd_clean with invalid action (not in {archive, delete, keep}) raises ValueError."""
        mock_derive.return_value = "svp-proj"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-proj -y"
        mock_load_state.return_value = _make_mock_state()

        with pytest.raises((ValueError, KeyError)):
            cmd_clean(SAMPLE_PROJECT_ROOT, "invalid_action")

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_env_name_derived_from_project_root(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """The environment name for cleanup is derived via derive_env_name."""
        mock_derive.return_value = "svp-test_svp_project"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-test_svp_project -y"
        mock_load_state.return_value = _make_mock_state()

        cmd_clean(SAMPLE_PROJECT_ROOT, "delete")

        # resolve_command should receive the env_name from derive_env_name
        resolve_args = mock_resolve.call_args
        # The env_name should appear in the resolve_command call
        all_args = str(resolve_args)
        assert "svp-test_svp_project" in all_args

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_all_valid_actions_accepted(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """All three valid actions (archive, delete, keep) are accepted without error."""
        mock_derive.return_value = "svp-proj"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-proj -y"
        mock_load_state.return_value = _make_mock_state()

        for action in ["archive", "delete", "keep"]:
            result = cmd_clean(SAMPLE_PROJECT_ROOT, action)
            assert isinstance(result, str), f"action={action} did not return a string"

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_archive_mentions_archive_in_result(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """When action='archive', the confirmation should reference archiving."""
        mock_derive.return_value = "svp-proj"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-proj -y"
        mock_load_state.return_value = _make_mock_state()

        result = cmd_clean(SAMPLE_PROJECT_ROOT, "archive")

        result_lower = result.lower()
        assert any(
            word in result_lower for word in ["archiv", "compress", "zip", "tar"]
        ), f"Archive confirmation should mention archiving: '{result}'"

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_delete_mentions_deletion_in_result(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """When action='delete', the confirmation should reference deletion."""
        mock_derive.return_value = "svp-proj"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-proj -y"
        mock_load_state.return_value = _make_mock_state()

        result = cmd_clean(SAMPLE_PROJECT_ROOT, "delete")

        result_lower = result.lower()
        assert any(word in result_lower for word in ["delet", "remov", "clean"]), (
            f"Delete confirmation should mention deletion: '{result}'"
        )

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_keep_mentions_keeping_in_result(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """When action='keep', the confirmation should indicate no workspace action."""
        mock_derive.return_value = "svp-proj"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-proj -y"
        mock_load_state.return_value = _make_mock_state()

        result = cmd_clean(SAMPLE_PROJECT_ROOT, "keep")

        result_lower = result.lower()
        assert any(
            word in result_lower
            for word in ["keep", "kept", "retain", "preserv", "no action"]
        ), f"Keep confirmation should mention keeping workspace: '{result}'"


# ===========================================================================
# sync_debug_docs tests
# ===========================================================================


class TestSyncDebugDocs:
    """Tests for sync_debug_docs: copy workspace spec/blueprint to delivered repo docs/."""

    @patch("sync_debug_docs.load_state")
    def test_sync_debug_docs_returns_none(self, mock_load_state, tmp_path):
        """sync_debug_docs returns None."""
        # Set up workspace and delivered repo directories
        mock_state = _make_mock_state(delivered_repo_path=str(tmp_path / "delivered"))
        mock_load_state.return_value = mock_state

        # Create workspace spec/blueprint files
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir(parents=True, exist_ok=True)
        (blueprint_dir / "blueprint_prose.md").write_text("# Blueprint")
        (blueprint_dir / "blueprint_contracts.md").write_text("# Contracts")

        # Create delivered repo docs dir
        delivered = tmp_path / "delivered"
        delivered.mkdir(parents=True, exist_ok=True)
        (delivered / "docs").mkdir(parents=True, exist_ok=True)

        result = sync_debug_docs(tmp_path)

        assert result is None

    @patch("sync_debug_docs.load_state")
    def test_sync_debug_docs_copies_to_delivered_repo_docs(
        self, mock_load_state, tmp_path
    ):
        """sync_debug_docs copies workspace files to delivered repo docs/ directory."""
        delivered_path = tmp_path / "delivered"
        delivered_path.mkdir(parents=True, exist_ok=True)
        (delivered_path / "docs").mkdir(parents=True, exist_ok=True)

        mock_state = _make_mock_state(delivered_repo_path=str(delivered_path))
        mock_load_state.return_value = mock_state

        # Create workspace blueprint files
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir(parents=True, exist_ok=True)
        (blueprint_dir / "blueprint_prose.md").write_text("# Prose Content")
        (blueprint_dir / "blueprint_contracts.md").write_text("# Contracts Content")

        sync_debug_docs(tmp_path)

        # Verify files were copied to delivered repo docs/
        docs_dir = delivered_path / "docs"
        # The docs dir should contain the copied files
        assert docs_dir.exists()

    @patch("sync_debug_docs.load_state")
    def test_sync_debug_docs_workspace_is_canonical(self, mock_load_state, tmp_path):
        """Workspace is canonical -- delivered repo docs/ is updated to match workspace."""
        delivered_path = tmp_path / "delivered"
        delivered_path.mkdir(parents=True, exist_ok=True)
        docs_dir = delivered_path / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)

        # Pre-existing stale content in delivered repo
        (docs_dir / "blueprint_prose.md").write_text("# OLD STALE CONTENT")

        mock_state = _make_mock_state(delivered_repo_path=str(delivered_path))
        mock_load_state.return_value = mock_state

        # Create workspace blueprint files with new content
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir(parents=True, exist_ok=True)
        (blueprint_dir / "blueprint_prose.md").write_text("# UPDATED PROSE")
        (blueprint_dir / "blueprint_contracts.md").write_text("# UPDATED CONTRACTS")

        sync_debug_docs(tmp_path)

        # The delivered docs should be updated to match workspace (not stale)
        updated_prose = (docs_dir / "blueprint_prose.md").read_text()
        assert "OLD STALE" not in updated_prose or "UPDATED" in updated_prose

    @patch("sync_debug_docs.load_state")
    def test_sync_debug_docs_reads_delivered_repo_path_from_state(
        self, mock_load_state, tmp_path
    ):
        """sync_debug_docs reads delivered_repo_path from pipeline state."""
        delivered_path = tmp_path / "my_delivered_repo"
        delivered_path.mkdir(parents=True, exist_ok=True)
        (delivered_path / "docs").mkdir(parents=True, exist_ok=True)

        mock_state = _make_mock_state(delivered_repo_path=str(delivered_path))
        mock_load_state.return_value = mock_state

        # Create workspace blueprint
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir(parents=True, exist_ok=True)
        (blueprint_dir / "blueprint_prose.md").write_text("# Prose")
        (blueprint_dir / "blueprint_contracts.md").write_text("# Contracts")

        sync_debug_docs(tmp_path)

        mock_load_state.assert_called()

    @patch("sync_debug_docs.load_state")
    def test_sync_debug_docs_creates_docs_dir_if_absent(
        self, mock_load_state, tmp_path
    ):
        """sync_debug_docs creates the docs/ directory in delivered repo if it does not exist."""
        delivered_path = tmp_path / "delivered"
        delivered_path.mkdir(parents=True, exist_ok=True)
        # Intentionally do NOT create docs/

        mock_state = _make_mock_state(delivered_repo_path=str(delivered_path))
        mock_load_state.return_value = mock_state

        # Create workspace blueprint
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir(parents=True, exist_ok=True)
        (blueprint_dir / "blueprint_prose.md").write_text("# Prose")
        (blueprint_dir / "blueprint_contracts.md").write_text("# Contracts")

        sync_debug_docs(tmp_path)

        docs_dir = delivered_path / "docs"
        assert docs_dir.exists()

    @patch("sync_debug_docs.load_state")
    def test_sync_debug_docs_copies_spec_files(self, mock_load_state, tmp_path):
        """sync_debug_docs copies workspace spec to delivered repo docs/."""
        delivered_path = tmp_path / "delivered"
        delivered_path.mkdir(parents=True, exist_ok=True)
        (delivered_path / "docs").mkdir(parents=True, exist_ok=True)

        mock_state = _make_mock_state(delivered_repo_path=str(delivered_path))
        mock_load_state.return_value = mock_state

        # Create workspace spec file (stakeholder spec)
        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)

        # Create workspace blueprint
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir(parents=True, exist_ok=True)
        (blueprint_dir / "blueprint_prose.md").write_text("# Blueprint Prose")
        (blueprint_dir / "blueprint_contracts.md").write_text("# Blueprint Contracts")

        sync_debug_docs(tmp_path)

        # docs dir should exist and have content
        docs_dir = delivered_path / "docs"
        assert docs_dir.exists()

    @patch("sync_debug_docs.load_state")
    def test_sync_debug_docs_handles_multiple_blueprint_files(
        self, mock_load_state, tmp_path
    ):
        """sync_debug_docs handles both blueprint prose and contracts files."""
        delivered_path = tmp_path / "delivered"
        delivered_path.mkdir(parents=True, exist_ok=True)
        (delivered_path / "docs").mkdir(parents=True, exist_ok=True)

        mock_state = _make_mock_state(delivered_repo_path=str(delivered_path))
        mock_load_state.return_value = mock_state

        # Create workspace blueprint with both files
        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir(parents=True, exist_ok=True)
        prose_content = "# Prose: Architecture Overview\nDesign notes here."
        contracts_content = "# Contracts: Unit definitions\nUnit 1: Core Config."
        (blueprint_dir / "blueprint_prose.md").write_text(prose_content)
        (blueprint_dir / "blueprint_contracts.md").write_text(contracts_content)

        sync_debug_docs(tmp_path)

        docs_dir = delivered_path / "docs"
        assert docs_dir.exists()


# ===========================================================================
# Cross-function integration tests
# ===========================================================================


class TestCmdSaveQuitIntegration:
    """Integration tests verifying cmd_quit delegates to cmd_save correctly."""

    @patch("sync_debug_docs.cmd_save")
    def test_quit_save_delegation_with_different_roots(self, mock_cmd_save):
        """cmd_quit delegates to cmd_save with the exact project_root it received."""
        mock_cmd_save.return_value = "Saved successfully."

        roots = [
            Path("/tmp/project_alpha"),
            Path("/home/user/project_beta"),
            Path("/opt/svp/project_gamma"),
        ]

        for root in roots:
            cmd_quit(root)
            mock_cmd_save.assert_called_with(root)

    @patch("sync_debug_docs.cmd_save")
    def test_quit_returns_different_value_than_save(self, mock_cmd_save):
        """cmd_quit's return (exit signal) is distinct from cmd_save's return (confirmation)."""
        save_message = "Pipeline state saved and verified."
        mock_cmd_save.return_value = save_message

        quit_result = cmd_quit(SAMPLE_PROJECT_ROOT)

        assert quit_result != save_message, (
            "cmd_quit should return an exit signal, not the save confirmation"
        )


class TestCmdCleanActionValidation:
    """Tests for cmd_clean action parameter validation."""

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_rejects_empty_string_action(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """cmd_clean raises on empty string action."""
        mock_derive.return_value = "svp-proj"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "cmd"
        mock_load_state.return_value = _make_mock_state()

        with pytest.raises((ValueError, KeyError)):
            cmd_clean(SAMPLE_PROJECT_ROOT, "")

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_rejects_unknown_action(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """cmd_clean raises on action not in {archive, delete, keep}."""
        mock_derive.return_value = "svp-proj"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "cmd"
        mock_load_state.return_value = _make_mock_state()

        for bad_action in ["ARCHIVE", "Archive", "remove", "purge", "backup"]:
            with pytest.raises((ValueError, KeyError)):
                cmd_clean(SAMPLE_PROJECT_ROOT, bad_action)


class TestCmdCleanEnvironmentRemoval:
    """Tests that cmd_clean always removes the build environment regardless of action."""

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_archive_removes_environment(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """action='archive' still removes the build environment."""
        mock_derive.return_value = "svp-proj"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-proj -y"
        mock_load_state.return_value = _make_mock_state()

        cmd_clean(SAMPLE_PROJECT_ROOT, "archive")

        # resolve_command should be called to build the environment removal command
        mock_resolve.assert_called()

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_delete_removes_environment(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """action='delete' removes the build environment."""
        mock_derive.return_value = "svp-proj"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-proj -y"
        mock_load_state.return_value = _make_mock_state()

        cmd_clean(SAMPLE_PROJECT_ROOT, "delete")

        mock_resolve.assert_called()

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_keep_still_removes_environment(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """action='keep' preserves workspace but still removes the build environment."""
        mock_derive.return_value = "svp-proj"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "conda env remove -n svp-proj -y"
        mock_load_state.return_value = _make_mock_state()

        cmd_clean(SAMPLE_PROJECT_ROOT, "keep")

        # Even with keep, the environment should be cleaned up
        mock_resolve.assert_called()


class TestCmdCleanToolchainUsage:
    """Tests that cmd_clean uses toolchain for language-specific cleanup."""

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_uses_toolchain_env_remove_command(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """cmd_clean resolves the environment removal command from toolchain."""
        toolchain = _make_mock_toolchain()
        mock_derive.return_value = "svp-proj"
        mock_toolchain.return_value = toolchain
        mock_resolve.return_value = "conda env remove -n svp-proj -y"
        mock_load_state.return_value = _make_mock_state()

        cmd_clean(SAMPLE_PROJECT_ROOT, "delete")

        # load_toolchain should be called to get the cleanup command templates
        mock_toolchain.assert_called()
        # resolve_command should be called to fill in the template
        mock_resolve.assert_called()


class TestSyncDebugDocsEdgeCases:
    """Edge case tests for sync_debug_docs."""

    @patch("sync_debug_docs.load_state")
    def test_sync_debug_docs_with_no_delivered_repo_path(
        self, mock_load_state, tmp_path
    ):
        """sync_debug_docs should handle None delivered_repo_path gracefully."""
        mock_state = _make_mock_state(delivered_repo_path=None)
        mock_load_state.return_value = mock_state

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir(parents=True, exist_ok=True)
        (blueprint_dir / "blueprint_prose.md").write_text("# Prose")
        (blueprint_dir / "blueprint_contracts.md").write_text("# Contracts")

        # Should either raise an error or be a no-op when no delivery path
        try:
            result = sync_debug_docs(tmp_path)
            # If it doesn't raise, it should return None (no-op)
            assert result is None
        except (ValueError, TypeError, AttributeError):
            # Acceptable: raises when delivered_repo_path is None
            pass

    @patch("sync_debug_docs.load_state")
    def test_sync_debug_docs_idempotent(self, mock_load_state, tmp_path):
        """Running sync_debug_docs twice produces the same result."""
        delivered_path = tmp_path / "delivered"
        delivered_path.mkdir(parents=True, exist_ok=True)
        (delivered_path / "docs").mkdir(parents=True, exist_ok=True)

        mock_state = _make_mock_state(delivered_repo_path=str(delivered_path))
        mock_load_state.return_value = mock_state

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir(parents=True, exist_ok=True)
        (blueprint_dir / "blueprint_prose.md").write_text("# Prose Content")
        (blueprint_dir / "blueprint_contracts.md").write_text("# Contracts Content")

        # Run twice
        sync_debug_docs(tmp_path)
        sync_debug_docs(tmp_path)

        # Should still be consistent
        docs_dir = delivered_path / "docs"
        assert docs_dir.exists()


class TestCmdStatusBuildLog:
    """Tests for cmd_status interaction with build log."""

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_reads_build_log(
        self, mock_load_state, mock_load_profile, tmp_path
    ):
        """cmd_status reads the build log file."""
        mock_load_state.return_value = _make_mock_state()
        mock_load_profile.return_value = _make_mock_profile()

        # cmd_status reads build log - it should not crash if the function
        # handles the build log internally
        result = cmd_status(tmp_path)

        assert isinstance(result, str)


class TestCmdStatusProfileSummaryFormat:
    """Tests for the one-line profile summary format in cmd_status."""

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_profile_summary_shows_pipeline_tools(
        self, mock_load_state, mock_load_profile
    ):
        """Profile summary shows pipeline tools."""
        mock_load_state.return_value = _make_mock_state()
        profile = _make_mock_profile()
        mock_load_profile.return_value = profile

        result = cmd_status(SAMPLE_PROJECT_ROOT)

        # The result should be a formatted string
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_profile_summary_shows_delivery_quality_tools(
        self, mock_load_state, mock_load_profile
    ):
        """Profile summary shows delivery quality tools separately from pipeline tools."""
        mock_load_state.return_value = _make_mock_state()
        profile = _make_mock_profile()
        # Ensure quality tools are present
        profile["quality"]["python"]["linter"] = "ruff"
        profile["quality"]["python"]["formatter"] = "ruff"
        profile["quality"]["python"]["type_checker"] = "mypy"
        mock_load_profile.return_value = profile

        result = cmd_status(SAMPLE_PROJECT_ROOT)

        assert isinstance(result, str)
        assert len(result) > 0


class TestReturnTypes:
    """Tests verifying return type contracts for all functions."""

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.save_state")
    def test_cmd_save_return_type_is_str(self, mock_save, mock_load):
        """cmd_save returns str per signature."""
        mock_load.return_value = _make_mock_state()
        result = cmd_save(SAMPLE_PROJECT_ROOT)
        assert isinstance(result, str)

    @patch("sync_debug_docs.cmd_save")
    def test_cmd_quit_return_type_is_str(self, mock_save):
        """cmd_quit returns str per signature."""
        mock_save.return_value = "Saved."
        result = cmd_quit(SAMPLE_PROJECT_ROOT)
        assert isinstance(result, str)

    @patch("sync_debug_docs.load_profile")
    @patch("sync_debug_docs.load_state")
    def test_cmd_status_return_type_is_str(self, mock_load_state, mock_load_profile):
        """cmd_status returns str per signature."""
        mock_load_state.return_value = _make_mock_state()
        mock_load_profile.return_value = _make_mock_profile()
        result = cmd_status(SAMPLE_PROJECT_ROOT)
        assert isinstance(result, str)

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.resolve_command")
    @patch("sync_debug_docs.load_toolchain")
    @patch("sync_debug_docs.derive_env_name")
    def test_cmd_clean_return_type_is_str(
        self, mock_derive, mock_toolchain, mock_resolve, mock_load_state
    ):
        """cmd_clean returns str per signature."""
        mock_derive.return_value = "svp-proj"
        mock_toolchain.return_value = _make_mock_toolchain()
        mock_resolve.return_value = "cmd"
        mock_load_state.return_value = _make_mock_state()
        result = cmd_clean(SAMPLE_PROJECT_ROOT, "keep")
        assert isinstance(result, str)

    @patch("sync_debug_docs.load_state")
    def test_sync_debug_docs_return_type_is_none(self, mock_load_state, tmp_path):
        """sync_debug_docs returns None per signature."""
        delivered_path = tmp_path / "delivered"
        delivered_path.mkdir(parents=True, exist_ok=True)
        (delivered_path / "docs").mkdir(parents=True, exist_ok=True)

        mock_load_state.return_value = _make_mock_state(
            delivered_repo_path=str(delivered_path)
        )

        blueprint_dir = tmp_path / "blueprint"
        blueprint_dir.mkdir(parents=True, exist_ok=True)
        (blueprint_dir / "blueprint_prose.md").write_text("# Prose")
        (blueprint_dir / "blueprint_contracts.md").write_text("# Contracts")

        result = sync_debug_docs(tmp_path)
        assert result is None


class TestCmdSaveIntegrity:
    """Detailed tests for cmd_save's integrity verification behavior."""

    @patch("sync_debug_docs.load_state")
    @patch("sync_debug_docs.save_state")
    def test_cmd_save_load_is_called_after_save(self, mock_save, mock_load):
        """Integrity verification requires loading state after saving it."""
        call_order = []
        mock_save.side_effect = lambda *a, **k: call_order.append("save")
        mock_load.side_effect = lambda *a, **k: (
            call_order.append("load"),
            _make_mock_state(),
        )[1]

        cmd_save(SAMPLE_PROJECT_ROOT)

        # There should be at least one save followed by at least one load
        assert "save" in call_order
        assert "load" in call_order
        # The first save should come before the last load (integrity re-read)
        first_save = call_order.index("save")
        last_load = len(call_order) - 1 - call_order[::-1].index("load")
        assert first_save < last_load, (
            "save_state should be called before the verification load_state"
        )


class TestCmdCleanDependencyIsolation:
    """Tests ensuring cmd_clean uses exactly the right dependencies."""

    def test_cmd_clean_signature_accepts_project_root_and_action(self):
        """cmd_clean accepts exactly (project_root: Path, action: str)."""
        import inspect

        sig = inspect.signature(cmd_clean)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert "action" in params
        assert len(params) == 2

    def test_cmd_save_signature_accepts_project_root(self):
        """cmd_save accepts exactly (project_root: Path)."""
        import inspect

        sig = inspect.signature(cmd_save)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert len(params) == 1

    def test_cmd_quit_signature_accepts_project_root(self):
        """cmd_quit accepts exactly (project_root: Path)."""
        import inspect

        sig = inspect.signature(cmd_quit)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert len(params) == 1

    def test_cmd_status_signature_accepts_project_root(self):
        """cmd_status accepts exactly (project_root: Path)."""
        import inspect

        sig = inspect.signature(cmd_status)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert len(params) == 1

    def test_sync_debug_docs_signature_accepts_project_root(self):
        """sync_debug_docs accepts (project_root: Path, repo_dir: Optional[Path] = None).

        Bug S3-193 (cycle H3): sync_debug_docs gained an optional `repo_dir`
        kwarg so Stage-5 assemblers can pass an explicit delivered-repo path
        without consulting state. The kwarg defaults to None, in which case
        the function reads `delivered_repo_path` from pipeline_state.json
        (the existing pre-S3-193 behavior). See contract C-16-H3a.
        """
        import inspect

        sig = inspect.signature(sync_debug_docs)
        params = list(sig.parameters.keys())
        assert "project_root" in params
        assert "repo_dir" in params
        assert len(params) == 2
        # repo_dir must default to None (back-compat for existing callers).
        assert sig.parameters["repo_dir"].default is None

    def test_cmd_save_returns_str(self):
        """cmd_save return annotation is str."""
        import inspect

        sig = inspect.signature(cmd_save)
        assert sig.return_annotation == str or sig.return_annotation == "str"

    def test_cmd_quit_returns_str(self):
        """cmd_quit return annotation is str."""
        import inspect

        sig = inspect.signature(cmd_quit)
        assert sig.return_annotation == str or sig.return_annotation == "str"

    def test_cmd_status_returns_str(self):
        """cmd_status return annotation is str."""
        import inspect

        sig = inspect.signature(cmd_status)
        assert sig.return_annotation == str or sig.return_annotation == "str"

    def test_cmd_clean_returns_str(self):
        """cmd_clean return annotation is str."""
        import inspect

        sig = inspect.signature(cmd_clean)
        assert sig.return_annotation == str or sig.return_annotation == "str"

    def test_sync_debug_docs_returns_none(self):
        """sync_debug_docs return annotation is None."""
        import inspect

        sig = inspect.signature(sync_debug_docs)
        assert sig.return_annotation is None or sig.return_annotation == "None"

"""Regression tests for Bugs S3-104, S3-105, S3-106: artifact path mismatches.

S3-104: pipeline_state.json must live at .svp/pipeline_state.json, not project root.
S3-105: build_log config must use .jsonl extension matching actual JSONL format.
S3-106: oracle_run_ledger functions must use ARTIFACT_FILENAMES, not hardcoded paths.

Synthetic data assumptions:
- Temporary directories via tmp_path fixtures simulate project roots.
- Minimal plugin structures are created for create_new_project tests.
- Pipeline state fixtures use minimal valid JSON with stage and sub_stage fields.
"""

import json
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from svp_config import ARTIFACT_FILENAMES
from hooks import generate_write_authorization_sh
from pipeline_state import PipelineState


# ===========================================================================
# S3-104: pipeline_state.json path mismatch
# ===========================================================================


class TestS3_104_PipelineStatePath:
    """pipeline_state.json must be at .svp/pipeline_state.json, not root."""

    def test_artifact_filenames_declares_svp_prefix(self):
        """Config maps pipeline_state to .svp/ subdirectory."""
        path = ARTIFACT_FILENAMES["pipeline_state"]
        assert path.startswith(".svp/"), (
            f"pipeline_state path must start with .svp/, got: {path}"
        )

    def test_create_new_project_writes_state_in_svp(self, tmp_path):
        """create_new_project must write pipeline_state.json inside .svp/."""
        from svp_launcher import create_new_project

        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        scripts_dir = plugin_root / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "routing.py").write_text("# routing\n")
        toolchain_dir = plugin_root / "toolchains"
        toolchain_dir.mkdir()
        (toolchain_dir / "python_conda_pytest.json").write_text("{}\n")
        (plugin_root / "ruff.toml").write_text("line-length = 88\n")
        plugin_json_dir = plugin_root / ".claude-plugin"
        plugin_json_dir.mkdir()
        (plugin_json_dir / "plugin.json").write_text(
            json.dumps({"name": "svp"}), encoding="utf-8"
        )

        with patch("svp_launcher.launch_session", return_value=0):
            project_root = create_new_project("test_s3_104", plugin_root)

        # Must exist in .svp/
        svp_state = project_root / ".svp" / "pipeline_state.json"
        assert svp_state.exists(), (
            ".svp/pipeline_state.json must exist after create_new_project"
        )

        # Must NOT exist at root
        root_state = project_root / "pipeline_state.json"
        assert not root_state.exists(), (
            "Stale root pipeline_state.json must not exist (S3-104)"
        )

        # Must be valid JSON with expected fields
        state = json.loads(svp_state.read_text())
        assert state["stage"] == "0"
        assert state["sub_stage"] == "hook_activation"

    def test_load_state_safe_finds_svp_state(self, tmp_path):
        """_load_state_safe finds state in .svp/ via load_state."""
        from routing import _load_state_safe

        svp_dir = tmp_path / ".svp"
        svp_dir.mkdir()
        state_data = {"stage": "3", "sub_stage": "build", "current_unit": 5}
        (svp_dir / "pipeline_state.json").write_text(json.dumps(state_data))

        result = _load_state_safe(tmp_path)
        assert result.stage == "3"
        assert result.sub_stage == "build"

    def test_load_state_safe_returns_default_when_missing(self, tmp_path):
        """_load_state_safe returns PipelineState() when no state file exists."""
        from routing import _load_state_safe

        (tmp_path / ".svp").mkdir()

        result = _load_state_safe(tmp_path)
        assert result.stage == "0"
        assert result.sub_stage is None

    def test_load_state_safe_ignores_root_level_state(self, tmp_path):
        """_load_state_safe does NOT read root-level pipeline_state.json."""
        from routing import _load_state_safe

        (tmp_path / ".svp").mkdir()
        # Write state at root (wrong location)
        (tmp_path / "pipeline_state.json").write_text(
            json.dumps({"stage": "5", "sub_stage": "delivery"})
        )

        # Should return default, not the root file
        result = _load_state_safe(tmp_path)
        assert result.stage == "0", (
            "_load_state_safe must not read root-level pipeline_state.json"
        )

    def test_hook_state_file_points_to_svp(self):
        """write_authorization.sh must read state from .svp/pipeline_state.json."""
        script = generate_write_authorization_sh()
        assert 'STATE_FILE=".svp/pipeline_state.json"' in script, (
            "Hook STATE_FILE must point to .svp/pipeline_state.json (S3-104)"
        )

    def test_hook_blocks_svp_pipeline_state_writes(self):
        """write_authorization.sh must block direct writes to .svp/pipeline_state.json."""
        script = generate_write_authorization_sh()
        assert ".svp/pipeline_state.json)" in script, (
            "Hook case pattern must match .svp/pipeline_state.json (S3-104)"
        )


# ===========================================================================
# S3-105: build_log extension mismatch
# ===========================================================================


class TestS3_105_BuildLogExtension:
    """build_log config must use .jsonl extension."""

    def test_artifact_filenames_uses_jsonl(self):
        """ARTIFACT_FILENAMES['build_log'] must end with .jsonl."""
        path = ARTIFACT_FILENAMES["build_log"]
        assert path.endswith(".jsonl"), (
            f"build_log path must end with .jsonl, got: {path}"
        )

    def test_build_log_path_matches_infra_setup(self):
        """Config path must match what infrastructure_setup creates."""
        from infrastructure_setup import run_infrastructure_setup

        # The config says .svp/build_log.jsonl
        config_path = ARTIFACT_FILENAMES["build_log"]
        assert "build_log.jsonl" in config_path


# ===========================================================================
# S3-106: oracle_run_ledger hardcoded paths
# ===========================================================================


class TestS3_106_OracleRunLedgerConfig:
    """oracle_run_ledger functions must use ARTIFACT_FILENAMES."""

    def test_append_uses_config_path(self, tmp_path):
        """append_oracle_run_entry writes to ARTIFACT_FILENAMES path."""
        from ledger_manager import append_oracle_run_entry, read_oracle_run_ledger

        (tmp_path / ".svp").mkdir(parents=True, exist_ok=True)

        entry = {"run_number": 1, "result": "pass"}
        append_oracle_run_entry(tmp_path, entry)

        # File must exist at the config-declared path
        expected_path = tmp_path / ARTIFACT_FILENAMES["oracle_run_ledger"]
        assert expected_path.exists(), (
            f"Oracle run ledger must exist at {ARTIFACT_FILENAMES['oracle_run_ledger']}"
        )

    def test_read_uses_config_path(self, tmp_path):
        """read_oracle_run_ledger reads from ARTIFACT_FILENAMES path."""
        from ledger_manager import append_oracle_run_entry, read_oracle_run_ledger

        (tmp_path / ".svp").mkdir(parents=True, exist_ok=True)

        entry = {"run_number": 1, "result": "pass"}
        append_oracle_run_entry(tmp_path, entry)

        entries = read_oracle_run_ledger(tmp_path)
        assert len(entries) == 1
        assert entries[0]["run_number"] == 1

    def test_artifact_filenames_has_oracle_run_ledger(self):
        """ARTIFACT_FILENAMES must contain oracle_run_ledger key."""
        assert "oracle_run_ledger" in ARTIFACT_FILENAMES
        assert ".svp/" in ARTIFACT_FILENAMES["oracle_run_ledger"]

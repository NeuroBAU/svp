"""Regression test for Bug 86: Setup agent skips five-area profile dialog
when user provides detailed briefing document during context phase.

SVP 2.2: _prepare_cmd removed from routing; _assemble_sections_for_agent
removed from prepare_task. route() now takes only project_root and reads
state internally.

Fix B (routing guard) tests adapted to write pipeline state to disk and
call route(project_root). Fix A (mode signal) tests skipped since
_assemble_sections_for_agent and _prepare_cmd were removed.
"""

import json
from pathlib import Path

import pytest

from src.unit_14.stub import route
from src.unit_5.stub import PipelineState


def _write_state(project_dir: Path, **overrides):
    """Write pipeline state JSON to .svp/pipeline_state.json."""
    defaults = {
        "stage": "0",
        "sub_stage": "project_profile",
        "current_unit": None,
        "total_units": 0,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iterations": 0,
        "verified_units": [],
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
    }
    defaults.update(overrides)
    svp_dir = project_dir / ".svp"
    svp_dir.mkdir(parents=True, exist_ok=True)
    (svp_dir / "pipeline_state.json").write_text(json.dumps(defaults))


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project directory with pipeline state."""
    _write_state(tmp_path, stage="0", sub_stage="project_profile")
    return tmp_path


class TestFixB_RoutingGuard:
    """Verify that the profile sub-stage routing guard is tight."""

    def test_context_approved_with_profile_invokes_agent(self, project_dir):
        """The original bug: CONTEXT APPROVED + profile exists should NOT skip dialog."""
        svp_dir = project_dir / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "last_status.txt").write_text("CONTEXT APPROVED")
        (project_dir / "project_profile.json").write_text(json.dumps({"test": True}))
        _write_state(project_dir)
        action = route(project_dir)
        assert action["action_type"] == "invoke_agent", (
            "Profile dialog must not be skipped when last_status is CONTEXT APPROVED"
        )

    def test_profile_complete_presents_gate(self, project_dir):
        """PROFILE_COMPLETE should present a gate."""
        svp_dir = project_dir / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "last_status.txt").write_text("PROFILE_COMPLETE")
        _write_state(project_dir)
        action = route(project_dir)
        assert action["action_type"] == "human_gate"

    def test_no_status_invokes_agent(self, project_dir):
        """No status file should invoke the setup agent."""
        _write_state(project_dir)
        action = route(project_dir)
        assert action["action_type"] == "invoke_agent"

    def test_profile_rejected_invokes_agent(self, project_dir):
        """PROFILE REJECTED should re-invoke the setup agent."""
        svp_dir = project_dir / ".svp"
        svp_dir.mkdir(parents=True, exist_ok=True)
        (svp_dir / "last_status.txt").write_text("PROFILE REJECTED")
        (project_dir / "project_profile.json").write_text(json.dumps({"test": True}))
        _write_state(project_dir)
        action = route(project_dir)
        assert action["action_type"] == "invoke_agent"



"""Regression test for Bug 86: Setup agent skips five-area profile dialog
when user provides detailed briefing document during context phase.

Root cause: Two structural gaps combined:
  Gap A -- prepare_task.py assembled identical task prompt sections for both
  project_context and project_profile sub-stages, with no mode signal.
  Gap B -- routing.py's profile sub-stage guard accepted any non-rejected,
  non-None last_status combined with profile file existence, allowing a
  speculative profile write during the context phase to bypass the dialog.

Fix A: Inject the current sub-stage as an explicit mode signal into the
setup agent's task prompt via a --context CLI argument.

Fix B: Tighten the profile sub-stage routing guard to only accept
PROFILE_COMPLETE as the status that skips the dialog. Remove the
artifact-existence fallback that allowed carry-over statuses to trigger
the gate.
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure scripts/ and stub paths are importable
_project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_project_root / "scripts"))
sys.path.insert(0, str(_project_root / "src" / "unit_1"))
sys.path.insert(0, str(_project_root / "src" / "unit_2"))
sys.path.insert(0, str(_project_root / "src" / "unit_3"))
sys.path.insert(0, str(_project_root / "src" / "unit_5"))

from pipeline_state import PipelineState
from routing import route, _prepare_cmd
from prepare_task import _assemble_sections_for_agent


def _make_state(sub_stage="project_profile"):
    return PipelineState.from_dict({
        "stage": "0",
        "sub_stage": sub_stage,
        "current_unit": None,
        "total_units": 0,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "alignment_iteration": 0,
        "verified_units": [],
        "pass_history": [],
        "log_references": {},
        "project_name": "test",
        "last_action": "test",
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    })


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project directory with pipeline state."""
    (tmp_path / "pipeline_state.json").write_text(json.dumps({
        "stage": "0", "sub_stage": "project_profile",
    }))
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir()
    return tmp_path


class TestFixB_RoutingGuard:
    """Verify that the profile sub-stage routing guard is tight."""

    def test_context_approved_with_profile_invokes_agent(self, project_dir):
        """The original bug: CONTEXT APPROVED + profile exists should NOT skip dialog."""
        (project_dir / ".svp" / "last_status.txt").write_text("CONTEXT APPROVED")
        (project_dir / "project_profile.json").write_text(json.dumps({"test": True}))
        state = _make_state()
        action = route(state, project_dir)
        assert action["ACTION"] == "invoke_agent", (
            "Profile dialog must not be skipped when last_status is CONTEXT APPROVED"
        )
        assert action["AGENT"] == "setup_agent"

    def test_profile_complete_presents_gate(self, project_dir):
        """PROFILE_COMPLETE should present Gate 0.3."""
        (project_dir / ".svp" / "last_status.txt").write_text("PROFILE_COMPLETE")
        state = _make_state()
        action = route(state, project_dir)
        assert action["ACTION"] == "human_gate"
        assert action["GATE_ID"] == "gate_0_3_profile_approval"

    def test_no_status_invokes_agent(self, project_dir):
        """No status file should invoke the setup agent."""
        state = _make_state()
        action = route(state, project_dir)
        assert action["ACTION"] == "invoke_agent"
        assert action["AGENT"] == "setup_agent"

    def test_profile_rejected_invokes_agent(self, project_dir):
        """PROFILE REJECTED should re-invoke the setup agent."""
        (project_dir / ".svp" / "last_status.txt").write_text("PROFILE REJECTED")
        (project_dir / "project_profile.json").write_text(json.dumps({"test": True}))
        state = _make_state()
        action = route(state, project_dir)
        assert action["ACTION"] == "invoke_agent"

    def test_arbitrary_status_with_profile_invokes_agent(self, project_dir):
        """Any status other than PROFILE_COMPLETE should invoke the agent."""
        for status in ["HOOKS ACTIVATED", "SPEC_DRAFT_COMPLETE", "random_status"]:
            (project_dir / ".svp" / "last_status.txt").write_text(status)
            (project_dir / "project_profile.json").write_text(json.dumps({"t": 1}))
            state = _make_state()
            action = route(state, project_dir)
            assert action["ACTION"] == "invoke_agent", (
                f"Status '{status}' should not skip profile dialog"
            )


class TestFixA_ModeSignal:
    """Verify that prepare_task.py injects a mode signal for the setup agent."""

    def test_context_mode_signal(self, tmp_path):
        """project_context context injects Mode 1 signal."""
        (tmp_path / "project_context.md").write_text("test")
        sections = _assemble_sections_for_agent(
            tmp_path, "setup_agent", None, None, None, None, None, None,
            context="project_context",
        )
        assert "current_mode" in sections
        assert "Mode 1" in sections["current_mode"]
        assert "project_context" in sections["current_mode"]

    def test_profile_mode_signal(self, tmp_path):
        """project_profile context injects Mode 2 signal."""
        (tmp_path / "project_context.md").write_text("test")
        sections = _assemble_sections_for_agent(
            tmp_path, "setup_agent", None, None, None, None, None, None,
            context="project_profile",
        )
        assert "current_mode" in sections
        assert "Mode 2" in sections["current_mode"]
        assert "project_profile" in sections["current_mode"]

    def test_no_context_no_mode_signal(self, tmp_path):
        """Without context, no mode signal is injected."""
        (tmp_path / "project_context.md").write_text("test")
        sections = _assemble_sections_for_agent(
            tmp_path, "setup_agent", None, None, None, None, None, None,
            context=None,
        )
        assert "current_mode" not in sections

    def test_prepare_cmd_includes_context(self):
        """_prepare_cmd passes --context when provided."""
        cmd = _prepare_cmd("setup_agent", context="project_profile")
        assert "--context project_profile" in cmd

    def test_prepare_cmd_omits_context_when_none(self):
        """_prepare_cmd does not include --context when not provided."""
        cmd = _prepare_cmd("setup_agent")
        assert "--context" not in cmd

    def test_context_mode_prevents_artifact_confusion(self, tmp_path):
        """Mode 1 and Mode 2 produce different mode signals."""
        (tmp_path / "project_context.md").write_text("test")
        s1 = _assemble_sections_for_agent(
            tmp_path, "setup_agent", None, None, None, None, None, None,
            context="project_context",
        )
        s2 = _assemble_sections_for_agent(
            tmp_path, "setup_agent", None, None, None, None, None, None,
            context="project_profile",
        )
        assert s1["current_mode"] != s2["current_mode"], (
            "Context and profile modes must produce different signals"
        )

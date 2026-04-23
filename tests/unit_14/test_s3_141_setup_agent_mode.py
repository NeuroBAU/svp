"""Tests for Bug S3-141: setup_agent --mode threading.

Verifies that (a) _agent_prepare_cmd emits `--mode <value>` when a mode is
supplied, and (b) _route_stage_0 passes the correct mode at each setup_agent
invocation site (project_context and project_profile sub_stages).

The redo sub_stage call site intentionally does NOT pass --mode per the
spec follow-up note in §24.154; a separate future cycle will handle that
when setup_agent.py's mode vocabulary is extended to cover redo cases.
"""

import json
from pathlib import Path

from pipeline_state import PipelineState, save_state
from routing import _agent_prepare_cmd, route


def _seed_stage_0_state(project_root: Path, sub_stage: str) -> None:
    """Write a pipeline_state.json positioning routing at Stage 0 / <sub_stage>."""
    (project_root / ".svp").mkdir(parents=True, exist_ok=True)
    state = PipelineState(stage="0", sub_stage=sub_stage)
    save_state(project_root, state)


def _clear_last_status(project_root: Path) -> None:
    (project_root / ".svp" / "last_status.txt").write_text("")


# ---------------------------------------------------------------------------
# Direct _agent_prepare_cmd signature tests
# ---------------------------------------------------------------------------


def test_agent_prepare_cmd_without_mode_has_no_mode_flag():
    """Backward-compat: omitted mode produces no `--mode` in cmd."""
    cmd = _agent_prepare_cmd("setup_agent")
    assert "--mode" not in cmd


def test_agent_prepare_cmd_with_mode_appends_mode_flag():
    """Supplied mode is appended as `--mode <value>`."""
    cmd = _agent_prepare_cmd("setup_agent", mode="project_context")
    assert "--mode project_context" in cmd


def test_agent_prepare_cmd_mode_and_unit_coexist():
    """Both unit and mode survive together, in the expected order."""
    cmd = _agent_prepare_cmd("test_agent", unit=3, mode="revision")
    assert "--unit 3" in cmd
    assert "--mode revision" in cmd


# ---------------------------------------------------------------------------
# Routing-level tests: PREPARE cmd carries the right mode per sub_stage
# ---------------------------------------------------------------------------


def test_route_stage_0_project_context_passes_mode_project_context(tmp_path):
    """Routing at stage=0 / sub_stage=project_context emits --mode project_context."""
    _seed_stage_0_state(tmp_path, "project_context")
    _clear_last_status(tmp_path)

    action = route(tmp_path)

    assert action.get("action_type") == "invoke_agent"
    assert action.get("agent_type") == "setup_agent"
    prepare = action.get("prepare", "")
    assert "--mode project_context" in prepare, (
        f"Expected --mode project_context in PREPARE cmd; got: {prepare}"
    )


def test_route_stage_0_project_profile_passes_mode_project_profile(tmp_path):
    """Routing at stage=0 / sub_stage=project_profile emits --mode project_profile."""
    _seed_stage_0_state(tmp_path, "project_profile")
    _clear_last_status(tmp_path)

    action = route(tmp_path)

    assert action.get("action_type") == "invoke_agent"
    assert action.get("agent_type") == "setup_agent"
    prepare = action.get("prepare", "")
    assert "--mode project_profile" in prepare, (
        f"Expected --mode project_profile in PREPARE cmd; got: {prepare}"
    )


def test_route_stage_0_redo_does_not_pass_mode(tmp_path):
    """Known gap per §24.154 follow-up: redo sub_stages don't pass --mode yet.

    This test pins the current behavior so a future cycle addressing the
    redo case can consciously break and update it.
    """
    _seed_stage_0_state(tmp_path, "redo_profile_delivery")
    _clear_last_status(tmp_path)

    action = route(tmp_path)

    assert action.get("action_type") == "invoke_agent"
    assert action.get("agent_type") == "setup_agent"
    prepare = action.get("prepare", "")
    assert "--mode" not in prepare, (
        "Redo site was expected to NOT pass --mode (see §24.154 follow-up); "
        f"got: {prepare}"
    )

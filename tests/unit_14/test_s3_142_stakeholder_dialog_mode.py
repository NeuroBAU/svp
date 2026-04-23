"""Tests for Bug S3-142: stakeholder_dialog --mode threading.

Verifies that routing passes mode="targeted_revision" when invoking
stakeholder_dialog at the two targeted_spec_revision sub_stages (one in
Stage 1, one in Stage 2). The Stage 1 main fall-through site is
intentionally left without --mode per spec §24.155 scope note; the third
test pins that behavior as a regression anchor for the future cycle that
will introduce a state-level distinguisher between initial and post-REVISE
rerun.
"""

from pathlib import Path

from pipeline_state import PipelineState, save_state
from routing import route


def _seed_state(
    project_root: Path, stage: str, sub_stage: str | None, **extra
) -> None:
    (project_root / ".svp").mkdir(parents=True, exist_ok=True)
    state = PipelineState(stage=stage, sub_stage=sub_stage, **extra)
    save_state(project_root, state)


def _clear_last_status(project_root: Path) -> None:
    (project_root / ".svp" / "last_status.txt").write_text("")


def test_stage1_targeted_spec_revision_passes_mode_targeted_revision(tmp_path):
    """_route_stage_1 at sub=targeted_spec_revision emits --mode targeted_revision."""
    _seed_state(tmp_path, stage="1", sub_stage="targeted_spec_revision")
    _clear_last_status(tmp_path)

    action = route(tmp_path)

    assert action.get("action_type") == "invoke_agent"
    assert action.get("agent_type") == "stakeholder_dialog"
    prepare = action.get("prepare", "")
    assert "--mode targeted_revision" in prepare, (
        f"Expected --mode targeted_revision in PREPARE; got: {prepare}"
    )


def test_stage2_targeted_spec_revision_passes_mode_targeted_revision(tmp_path):
    """_route_stage_2 at sub=targeted_spec_revision emits --mode targeted_revision."""
    _seed_state(tmp_path, stage="2", sub_stage="targeted_spec_revision")
    _clear_last_status(tmp_path)

    action = route(tmp_path)

    assert action.get("action_type") == "invoke_agent"
    assert action.get("agent_type") == "stakeholder_dialog"
    prepare = action.get("prepare", "")
    assert "--mode targeted_revision" in prepare, (
        f"Expected --mode targeted_revision in PREPARE; got: {prepare}"
    )


def test_stage1_main_fallthrough_still_passes_no_mode(tmp_path):
    """Regression anchor: Stage 1 main fall-through still emits no --mode.

    Per §24.155 scope note, this site conflates initial-dialog and post-REVISE
    rerun. A future cycle will add a state-level distinguisher; this test
    pins the current behavior so that cycle consciously breaks and updates it.
    """
    _seed_state(tmp_path, stage="1", sub_stage=None)
    _clear_last_status(tmp_path)

    action = route(tmp_path)

    assert action.get("action_type") == "invoke_agent"
    assert action.get("agent_type") == "stakeholder_dialog"
    prepare = action.get("prepare", "")
    assert "--mode" not in prepare, (
        "Stage 1 main fall-through was expected to NOT pass --mode "
        f"(see §24.155 scope note); got: {prepare}"
    )

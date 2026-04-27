"""Anchor tests for Bug S3-143: blueprint_author --mode deferred.

Per spec §24.156, neither blueprint_author call site in `_route_stage_2`
currently passes `--mode`. A cosmetic-only mode-threading fix (adding
`mode="revision"` without threading `context`) would not materially
improve the agent's information; and neither site can unambiguously
detect revision without a state-level distinguisher that routing
currently lacks.

This file pins the current no-`--mode` behavior as a regression anchor.
When the future cycle lands the state-level distinguisher AND the
context-threading fix, it will need to consciously break and update
these tests.
"""

from pathlib import Path

from pipeline_state import PipelineState, save_state
from routing import route


def _seed_state(project_root: Path, stage: str, sub_stage: str | None) -> None:
    (project_root / ".svp").mkdir(parents=True, exist_ok=True)
    state = PipelineState(stage=stage, sub_stage=sub_stage)
    save_state(project_root, state)


def _clear_last_status(project_root: Path) -> None:
    (project_root / ".svp" / "last_status.txt").write_text("")


def test_blueprint_dialog_fallthrough_passes_explicit_mode(tmp_path):
    """Bug S3-159 (was S3-143 deferral anchor): _route_stage_2 at
    sub=blueprint_dialog now emits an explicit --mode (draft when no
    blueprint files exist yet, revision when they do — see
    _blueprint_author_mode in routing).
    """
    _seed_state(tmp_path, stage="2", sub_stage="blueprint_dialog")
    _clear_last_status(tmp_path)

    action = route(tmp_path)

    assert action.get("action_type") == "invoke_agent"
    assert action.get("agent_type") == "blueprint_author"
    prepare = action.get("prepare", "")
    # No blueprint files in tmp_path → mode resolves to "draft".
    assert "--mode draft" in prepare, (
        "blueprint_dialog (no existing blueprint) was expected to pass "
        f"--mode draft per Bug S3-159; got: {prepare}"
    )


def test_route_stage_2_end_fallthrough_passes_explicit_mode(tmp_path):
    """Bug S3-159 (was S3-143 deferral anchor): _route_stage_2
    end-of-function fall-through now emits an explicit --mode for
    blueprint_author too (mirrors blueprint_dialog handling).
    """
    # sub_stage=None lands at the end-of-function fall-through
    _seed_state(tmp_path, stage="2", sub_stage=None)
    _clear_last_status(tmp_path)

    action = route(tmp_path)

    if (
        action.get("action_type") == "invoke_agent"
        and action.get("agent_type") == "blueprint_author"
    ):
        prepare = action.get("prepare", "")
        # No blueprint files in tmp_path → mode resolves to "draft".
        assert "--mode draft" in prepare, (
            "Stage 2 fall-through blueprint_author was expected to pass "
            f"--mode draft per Bug S3-159; got: {prepare}"
        )

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


def test_blueprint_dialog_fallthrough_passes_no_mode(tmp_path):
    """Anchor: _route_stage_2 at sub=blueprint_dialog fall-through emits no --mode.

    Per §24.156, this site conflates initial-authoring and post-REVISE rerun.
    The future cycle that distinguishes them via a pipeline-state field will
    need to break this test and update routing.
    """
    _seed_state(tmp_path, stage="2", sub_stage="blueprint_dialog")
    _clear_last_status(tmp_path)

    action = route(tmp_path)

    assert action.get("action_type") == "invoke_agent"
    assert action.get("agent_type") == "blueprint_author"
    prepare = action.get("prepare", "")
    assert "--mode" not in prepare, (
        "blueprint_dialog fall-through was expected to NOT pass --mode per "
        f"§24.156 deferral; got: {prepare}"
    )


def test_route_stage_2_end_fallthrough_passes_no_mode(tmp_path):
    """Anchor: _route_stage_2 end-of-function fall-through emits no --mode.

    Reached when no other sub_stage match triggers. Same ambiguity class as
    blueprint_dialog fall-through. Pin current behavior as regression anchor.
    """
    # sub_stage=None lands at the end-of-function fall-through
    _seed_state(tmp_path, stage="2", sub_stage=None)
    _clear_last_status(tmp_path)

    action = route(tmp_path)

    # Depending on routing semantics for sub_stage=None at stage=2, this may
    # invoke blueprint_author or advance sub_stage first. Either way, if an
    # invoke_agent for blueprint_author surfaces, it must not carry --mode.
    if (
        action.get("action_type") == "invoke_agent"
        and action.get("agent_type") == "blueprint_author"
    ):
        prepare = action.get("prepare", "")
        assert "--mode" not in prepare, (
            "Stage 2 fall-through blueprint_author was expected to NOT "
            f"pass --mode per §24.156 deferral; got: {prepare}"
        )

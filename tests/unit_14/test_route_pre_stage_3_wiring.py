"""Tests for _route_pre_stage_3 wiring — Bug S3-136.

Verifies that when routing transitions from Stage 2 to Stage 3, it calls
ensure_pipeline_toolchain and run_infrastructure_setup so that total_units
is populated from the blueprint before Stage 3's per-unit build loop runs.

Prior to Bug S3-136, the `if state.total_units > 0` branch was dead code:
nothing ever populated total_units, so _validate_stage3_completion
immediately emitted gate_3_completion_failure.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import routing
from pipeline_state import PipelineState, save_state


def _write_initial_state(project_root: Path, total_units: int) -> PipelineState:
    """Seed pipeline_state.json with a post-Stage-2 state."""
    (project_root / ".svp").mkdir(parents=True, exist_ok=True)
    state = PipelineState(stage="2", total_units=total_units)
    save_state(project_root, state)
    return state


def _fake_infra_setup_writes_units(total_units: int):
    """Return a fake run_infrastructure_setup that writes total_units to state."""
    def _fake(project_root: Path, **kwargs: Any) -> None:
        from pipeline_state import load_state, save_state as _save
        s = load_state(project_root)
        s.total_units = total_units
        _save(project_root, s)
    return _fake


def test_route_pre_stage_3_invokes_infra_setup_when_total_units_zero(
    tmp_path, monkeypatch
):
    """With total_units=0, _route_pre_stage_3 calls run_infrastructure_setup."""
    state = _write_initial_state(tmp_path, total_units=0)

    calls: List[Dict[str, Any]] = []

    def fake_ensure(project_root: Path) -> None:
        calls.append({"fn": "ensure_pipeline_toolchain", "project_root": project_root})

    def fake_run(**kwargs: Any) -> None:
        calls.append({"fn": "run_infrastructure_setup", **kwargs})
        _fake_infra_setup_writes_units(22)(kwargs["project_root"])

    # Shim profile and toolchain loaders so they don't need real files on disk.
    monkeypatch.setattr(routing, "ensure_pipeline_toolchain", fake_ensure)
    monkeypatch.setattr(routing, "run_infrastructure_setup", fake_run)
    monkeypatch.setattr(
        routing, "load_profile", lambda p: {"language": {"primary": "python"}}
    )
    monkeypatch.setattr(
        routing, "load_toolchain", lambda p: {"toolchain_id": "python_conda_pytest"}
    )
    monkeypatch.setattr(routing, "get_blueprint_dir", lambda p: p / "blueprint")

    # Swallow the downstream route() call — we only test pre_stage_3's own body.
    monkeypatch.setattr(routing, "route", lambda p: {"action_type": "noop"})

    routing._route_pre_stage_3(state, tmp_path, "")

    fns_called = [c["fn"] for c in calls]
    assert "ensure_pipeline_toolchain" in fns_called
    assert "run_infrastructure_setup" in fns_called

    # Verify run_infrastructure_setup received the right kwargs.
    infra_call = next(c for c in calls if c["fn"] == "run_infrastructure_setup")
    assert infra_call["project_root"] == tmp_path
    assert "profile" in infra_call
    assert "toolchain" in infra_call
    assert "language_registry" in infra_call
    assert "blueprint_dir" in infra_call


def test_route_pre_stage_3_skips_infra_setup_when_total_units_nonzero(
    tmp_path, monkeypatch
):
    """With total_units>0, the infra-setup block is skipped (idempotency)."""
    state = _write_initial_state(tmp_path, total_units=22)

    calls: List[str] = []
    monkeypatch.setattr(
        routing,
        "ensure_pipeline_toolchain",
        lambda p: calls.append("ensure_pipeline_toolchain"),
    )
    monkeypatch.setattr(
        routing,
        "run_infrastructure_setup",
        lambda **kw: calls.append("run_infrastructure_setup"),
    )
    monkeypatch.setattr(routing, "route", lambda p: {"action_type": "noop"})

    routing._route_pre_stage_3(state, tmp_path, "")

    assert "ensure_pipeline_toolchain" not in calls
    assert "run_infrastructure_setup" not in calls

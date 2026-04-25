"""Tests for Bug S3-149: Stage 5 retry-loop safety net.

Verifies the minimal fix:
  - assembly_retries field on PipelineState (default 0, JSON round-trip,
    backward-compat with old state files)
  - gate_5_1_repo_test TESTS FAILED below limit increments counter, keeps
    sub_stage None
  - gate_5_1_repo_test TESTS FAILED at limit transitions to gate_5_2
  - gate_5_2_assembly_exhausted RETRY ASSEMBLY resets counter and clears
    sub_stage (preventing gate-re-emit)
"""

import json
from pathlib import Path

from pipeline_state import PipelineState, load_state, save_state
from routing import dispatch_gate_response


def _seed_config(project_root: Path, iteration_limit: int = 3) -> None:
    """Write a minimal config so dispatch_gate_response can read it."""
    svp = project_root / ".svp"
    svp.mkdir(parents=True, exist_ok=True)
    (svp / "svp_config.json").write_text(
        json.dumps({"iteration_limit": iteration_limit})
    )


def _save(project_root: Path, state: PipelineState) -> None:
    (project_root / ".svp").mkdir(parents=True, exist_ok=True)
    save_state(project_root, state)


# ---------------------------------------------------------------------------
# (a) default value
# ---------------------------------------------------------------------------


def test_assembly_retries_defaults_to_zero():
    state = PipelineState()
    assert state.assembly_retries == 0


# ---------------------------------------------------------------------------
# (b) JSON round-trip preserves the field
# ---------------------------------------------------------------------------


def test_assembly_retries_json_round_trip(tmp_path):
    state = PipelineState(stage="5", assembly_retries=2)
    _save(tmp_path, state)
    loaded = load_state(tmp_path)
    assert loaded.assembly_retries == 2


# ---------------------------------------------------------------------------
# (c) backward compat: state file without the field
# ---------------------------------------------------------------------------


def test_old_state_file_without_assembly_retries_loads_with_zero(tmp_path):
    """A state file written before this fix exists has no assembly_retries
    key. load_state must default to 0 instead of raising."""
    svp = tmp_path / ".svp"
    svp.mkdir()
    legacy_state = {
        "stage": "5",
        "sub_stage": "repo_test",
        "current_unit": None,
        "total_units": 22,
        # NO assembly_retries key
    }
    (svp / "pipeline_state.json").write_text(json.dumps(legacy_state))

    loaded = load_state(tmp_path)
    assert loaded.assembly_retries == 0
    assert loaded.stage == "5"  # other fields still load correctly


# ---------------------------------------------------------------------------
# (d) TESTS FAILED below limit: counter +1, sub_stage None
# ---------------------------------------------------------------------------


def test_tests_failed_below_limit_increments_and_keeps_substage_none(tmp_path):
    _seed_config(tmp_path, iteration_limit=3)
    state = PipelineState(stage="5", sub_stage="repo_test", assembly_retries=0)
    _save(tmp_path, state)

    new = dispatch_gate_response(state, "gate_5_1_repo_test", "TESTS FAILED", tmp_path)

    assert new.assembly_retries == 1
    assert new.sub_stage is None  # falls through to re-invoke agent


def test_tests_failed_below_limit_increments_at_two_of_three(tmp_path):
    _seed_config(tmp_path, iteration_limit=3)
    state = PipelineState(stage="5", sub_stage="repo_test", assembly_retries=1)
    _save(tmp_path, state)

    new = dispatch_gate_response(state, "gate_5_1_repo_test", "TESTS FAILED", tmp_path)

    assert new.assembly_retries == 2
    assert new.sub_stage is None


# ---------------------------------------------------------------------------
# (e) TESTS FAILED at limit: transitions to gate_5_2
# ---------------------------------------------------------------------------


def test_tests_failed_at_limit_transitions_to_gate_5_2(tmp_path):
    _seed_config(tmp_path, iteration_limit=3)
    # State has 2 retries already; this TESTS FAILED brings it to 3 (limit).
    state = PipelineState(stage="5", sub_stage="repo_test", assembly_retries=2)
    _save(tmp_path, state)

    new = dispatch_gate_response(state, "gate_5_1_repo_test", "TESTS FAILED", tmp_path)

    assert new.assembly_retries == 3
    assert new.sub_stage == "gate_5_2", (
        "At iteration_limit, dispatch must transition to gate_5_2 instead "
        "of falling through to re-invoke the agent forever (Bug S3-149)."
    )


# ---------------------------------------------------------------------------
# (f) RETRY ASSEMBLY resets counter AND clears sub_stage
# ---------------------------------------------------------------------------


def test_retry_assembly_resets_counter_and_clears_substage(tmp_path):
    _seed_config(tmp_path, iteration_limit=3)
    state = PipelineState(stage="5", sub_stage="gate_5_2", assembly_retries=3)
    _save(tmp_path, state)

    new = dispatch_gate_response(
        state, "gate_5_2_assembly_exhausted", "RETRY ASSEMBLY", tmp_path
    )

    assert new.assembly_retries == 0, (
        "RETRY ASSEMBLY must reset the counter so the next batch of retries "
        "is fresh."
    )
    assert new.sub_stage is None, (
        "RETRY ASSEMBLY must clear sub_stage so routing falls through to "
        "re-invoke git_repo_agent. Without this reset, sub_stage stays "
        "gate_5_2 and routing re-emits the gate (Bug S3-149)."
    )

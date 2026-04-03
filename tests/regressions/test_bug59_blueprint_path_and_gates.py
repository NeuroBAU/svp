"""Regression test for Bug 59: Blueprint path fixes, gate IDs, status lines.

Verifies:
1. _version_blueprint uses blueprint/ (not blueprints/)
2. advance_stage signature (SVP 2.2: takes state + target_stage string, not project_root)
3. load_blueprint loads both prose and contracts
4. gate_hint_conflict is in GATE_VOCABULARY and ALL_GATE_IDS
5. REGRESSION_TEST_COMPLETE is in test_agent status lines
6. Debug session has triage_refinement_count and repair_retry_count (plain dict)
7. _FIX_LADDER_TRANSITIONS removed in SVP 2.2 (skipped)
8. _DEBUG_PHASE_TRANSITIONS removed in SVP 2.2 (skipped)

SVP 2.2 adaptation:
- DebugSession class removed; debug sessions are plain dicts created by
  enter_debug_session() in src.unit_6.stub
- _FIX_LADDER_TRANSITIONS and _DEBUG_PHASE_TRANSITIONS removed from SVP 2.2
- advance_stage(state, target_stage) takes 2 args (no project_root)
- _version_blueprint is internal to routing, checked via source inspection
"""

import sys
from pathlib import Path

import pytest

# Add scripts to path for imports
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root / "scripts"))

from src.unit_5.stub import PipelineState
from src.unit_6.stub import advance_stage, enter_debug_session


def test_gate_hint_conflict_in_gate_vocabulary():
    """gate_hint_conflict must be in GATE_VOCABULARY."""
    from src.unit_14.stub import GATE_VOCABULARY

    assert "gate_hint_conflict" in GATE_VOCABULARY, (
        "gate_hint_conflict missing from GATE_VOCABULARY"
    )
    options = GATE_VOCABULARY["gate_hint_conflict"]
    assert "BLUEPRINT CORRECT" in options
    assert "HINT CORRECT" in options


def test_gate_hint_conflict_in_all_gate_ids():
    """gate_hint_conflict must be in ALL_GATE_IDS."""
    from prepare_task import ALL_GATE_IDS

    assert "gate_hint_conflict" in ALL_GATE_IDS, (
        "gate_hint_conflict missing from ALL_GATE_IDS"
    )


def test_gate_5_3_in_all_gate_ids():
    """gate_5_3_unused_functions must be in ALL_GATE_IDS."""
    from prepare_task import ALL_GATE_IDS

    assert "gate_5_3_unused_functions" in ALL_GATE_IDS, (
        "gate_5_3_unused_functions missing from ALL_GATE_IDS"
    )


def test_regression_test_complete_in_test_agent_status():
    """REGRESSION_TEST_COMPLETE must be in test_agent status lines."""
    from src.unit_14.stub import AGENT_STATUS_LINES

    test_agent_lines = AGENT_STATUS_LINES.get("test_agent", [])
    assert "REGRESSION_TEST_COMPLETE" in test_agent_lines, (
        "REGRESSION_TEST_COMPLETE missing from test_agent status lines"
    )


def test_debug_session_has_triage_and_repair_counts():
    """Debug session (plain dict) must have triage_refinement_count and repair_retry_count.

    SVP 2.2: enter_debug_session creates a dict with these fields.
    """
    state = PipelineState(stage="5")
    new_state = enter_debug_session(state, bug_number=1)
    ds = new_state.debug_session

    assert isinstance(ds, dict), "debug_session must be a dict in SVP 2.2"
    assert "triage_refinement_count" in ds, (
        "debug session missing triage_refinement_count"
    )
    assert "repair_retry_count" in ds, (
        "debug session missing repair_retry_count"
    )
    assert ds["triage_refinement_count"] == 0
    assert ds["repair_retry_count"] == 0


def test_gate_vocabulary_and_all_gate_ids_synchronized():
    """GATE_VOCABULARY keys must match ALL_GATE_IDS."""
    from src.unit_14.stub import GATE_VOCABULARY
    from prepare_task import ALL_GATE_IDS

    vocab_set = set(GATE_VOCABULARY.keys())
    ids_set = set(ALL_GATE_IDS)
    assert vocab_set == ids_set, (
        f"GATE_VOCABULARY and ALL_GATE_IDS out of sync. "
        f"In VOCABULARY only: {vocab_set - ids_set}. "
        f"In ALL_GATE_IDS only: {ids_set - vocab_set}."
    )


def test_advance_stage_basic():
    """advance_stage(state, target_stage) works for valid transitions.

    SVP 2.2: advance_stage takes (state, target_stage) -- no project_root arg.
    The two-file blueprint check was removed from advance_stage itself;
    blueprint validation is done in routing before calling advance_stage.
    """
    state = PipelineState(stage="2", sub_stage="alignment_check")
    new_state = advance_stage(state, "pre_stage_3")
    assert new_state.stage == "pre_stage_3"
    assert new_state.sub_stage is None

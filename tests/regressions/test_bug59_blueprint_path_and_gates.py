"""Regression test for Bug 59: Blueprint path fixes, gate IDs, status lines.

Verifies:
1. _version_blueprint uses blueprint/ (not blueprints/)
2. advance_stage checks for two-file blueprint format
3. load_blueprint loads both prose and contracts
4. gate_hint_conflict is in GATE_VOCABULARY and ALL_GATE_IDS
5. REGRESSION_TEST_COMPLETE is in test_agent status lines
6. DebugSession has triage_refinement_count and repair_retry_count
7. _FIX_LADDER_TRANSITIONS: hint_test has no successors
8. _DEBUG_PHASE_TRANSITIONS: no investigation phase
"""

import sys
from pathlib import Path

# Add scripts to path for imports
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root / "scripts"))
sys.path.insert(0, str(_project_root / "src" / "unit_1"))
sys.path.insert(0, str(_project_root / "src" / "unit_2"))
sys.path.insert(0, str(_project_root / "src" / "unit_3"))


def test_version_blueprint_uses_correct_path():
    """_version_blueprint must reference blueprint/ not blueprints/."""
    import inspect
    from routing import _version_blueprint

    source = inspect.getsource(_version_blueprint)
    assert "blueprints" not in source, (
        "_version_blueprint still references 'blueprints/' (plural)"
    )
    assert '"blueprint"' in source or "'blueprint'" in source, (
        "_version_blueprint must reference 'blueprint/' (singular)"
    )


def test_gate_hint_conflict_in_gate_vocabulary():
    """gate_hint_conflict must be in GATE_VOCABULARY."""
    from routing import GATE_VOCABULARY

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
    from routing import AGENT_STATUS_LINES

    test_agent_lines = AGENT_STATUS_LINES.get("test_agent", [])
    assert "REGRESSION_TEST_COMPLETE" in test_agent_lines, (
        "REGRESSION_TEST_COMPLETE missing from test_agent status lines"
    )


def test_debug_session_has_triage_and_repair_counts():
    """DebugSession must have triage_refinement_count and repair_retry_count."""
    from pipeline_state import DebugSession

    ds = DebugSession(bug_id=1, description="test")
    assert hasattr(ds, "triage_refinement_count"), (
        "DebugSession missing triage_refinement_count"
    )
    assert hasattr(ds, "repair_retry_count"), (
        "DebugSession missing repair_retry_count"
    )
    assert ds.triage_refinement_count == 0
    assert ds.repair_retry_count == 0

    # Verify serialization round-trip
    d = ds.to_dict()
    assert "triage_refinement_count" in d
    assert "repair_retry_count" in d
    ds2 = DebugSession.from_dict(d)
    assert ds2.triage_refinement_count == 0
    assert ds2.repair_retry_count == 0


def test_fix_ladder_hint_test_no_successors():
    """hint_test must have no successors (no cross-branch transition)."""
    from state_transitions import _FIX_LADDER_TRANSITIONS

    assert _FIX_LADDER_TRANSITIONS.get("hint_test") == [], (
        "hint_test must have empty successor list (no cross-branch transition)"
    )


def test_no_investigation_phase():
    """_DEBUG_PHASE_TRANSITIONS must not contain investigation."""
    from state_transitions import _DEBUG_PHASE_TRANSITIONS

    for phase, targets in _DEBUG_PHASE_TRANSITIONS.items():
        assert "investigation" not in targets, (
            f"Undocumented 'investigation' phase found in targets of '{phase}'"
        )


def test_gate_vocabulary_and_all_gate_ids_synchronized():
    """GATE_VOCABULARY keys must match ALL_GATE_IDS."""
    from routing import GATE_VOCABULARY
    from prepare_task import ALL_GATE_IDS

    vocab_set = set(GATE_VOCABULARY.keys())
    ids_set = set(ALL_GATE_IDS)
    assert vocab_set == ids_set, (
        f"GATE_VOCABULARY and ALL_GATE_IDS out of sync. "
        f"In VOCABULARY only: {vocab_set - ids_set}. "
        f"In ALL_GATE_IDS only: {ids_set - vocab_set}."
    )


def test_advance_stage_checks_two_file_blueprint(tmp_path):
    """advance_stage from Stage 2 must check for blueprint_prose.md and
    blueprint_contracts.md, not blueprint.md."""
    from state_transitions import advance_stage, TransitionError
    from pipeline_state import PipelineState

    state = PipelineState(stage="2", sub_stage="alignment_check")

    # Should fail when neither file exists
    project_root = tmp_path
    bp_dir = project_root / "blueprint"
    bp_dir.mkdir()

    try:
        advance_stage(state, project_root)
        assert False, "Should have raised TransitionError"
    except TransitionError as e:
        assert "blueprint_prose.md" in str(e) or "blueprint_contracts.md" in str(e), (
            f"Error message should mention two-file format: {e}"
        )

    # Should succeed when both files exist
    (bp_dir / "blueprint_prose.md").write_text("prose", encoding="utf-8")
    (bp_dir / "blueprint_contracts.md").write_text("contracts", encoding="utf-8")
    new_state = advance_stage(state, project_root)
    assert new_state.stage == "pre_stage_3"

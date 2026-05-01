"""Cycle K-3 (S3-205) -- implementation_agent honest test-layer escalation.

The implementation_agent previously had only two terminal statuses --
IMPLEMENTATION_COMPLETE and HINT_BLUEPRINT_CONFLICT -- and no honest path
to escalate "the tests are flawed, not my implementation." When tests
failed for genuine test-author reasons, the agent's only options were lie
(declare COMPLETE despite failures, classifying them as "test design
flaw") or wrong-scoped escalate (HINT_BLUEPRINT_CONFLICT, whose downstream
gate routes to a different problem).

K-3 added:
  * Terminal status TESTS_FLAWED: [details]
  * Gate gate_3_3_test_layer_review with four responses
    (TESTS WRONG / IMPLEMENTATION WRONG / BLUEPRINT WRONG / ABANDON UNIT)
  * State field test_layer_review_count (advisory only)
  * Routing dispatch + agent-prompt amendments forbidding lying

Pattern reference: P90 (Honest escalation paths > false completion).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import pipeline_state
import prepare_task
import routing
import state_transitions

from construction_agents import IMPLEMENTATION_AGENT_DEFINITION


# ---------------------------------------------------------------------------
# Vocabulary + state-field assertions
# ---------------------------------------------------------------------------


def test_k3_all_gate_ids_includes_test_layer_review():
    """C-13-K3a: ALL_GATE_IDS contains the new gate exactly once."""
    assert prepare_task.ALL_GATE_IDS.count("gate_3_3_test_layer_review") == 1


def test_k3_gate_response_options_match_gate_vocabulary():
    """C-13-K3a / C-14-K3a: _GATE_RESPONSE_OPTIONS (Unit 13) matches
    GATE_VOCABULARY (Unit 14) character-identical for the new gate."""
    expected = ["TESTS WRONG", "IMPLEMENTATION WRONG", "BLUEPRINT WRONG", "ABANDON UNIT"]
    assert prepare_task._GATE_RESPONSE_OPTIONS["gate_3_3_test_layer_review"] == expected
    assert routing.GATE_VOCABULARY["gate_3_3_test_layer_review"] == expected


def test_k3_gate_vocabulary_includes_test_layer_review():
    """C-14-K3a: GATE_VOCABULARY has the new gate."""
    assert "gate_3_3_test_layer_review" in routing.GATE_VOCABULARY


def test_k3_gate_id_consistency_invariant():
    """Section 3.6: ALL_GATE_IDS (Unit 13) == GATE_VOCABULARY keys (Unit 14)."""
    u13_set = set(prepare_task.ALL_GATE_IDS)
    u14_set = set(routing.GATE_VOCABULARY.keys())
    assert u13_set == u14_set, f"In u13 only: {u13_set - u14_set}; in u14 only: {u14_set - u13_set}"


def test_k3_implementation_agent_allowed_statuses_includes_tests_flawed():
    """C-14-K3a: implementation_agent allowed-statuses includes TESTS_FLAWED
    alongside IMPLEMENTATION_COMPLETE and HINT_BLUEPRINT_CONFLICT."""
    statuses = routing.AGENT_STATUS_LINES["implementation_agent"]
    assert "TESTS_FLAWED" in statuses
    assert "IMPLEMENTATION_COMPLETE" in statuses
    assert "HINT_BLUEPRINT_CONFLICT" in statuses


def test_k3_pipeline_state_default_test_layer_review_count_is_zero():
    """C-5-K3a: PipelineState.test_layer_review_count defaults to 0."""
    s = pipeline_state.PipelineState()
    assert s.test_layer_review_count == 0


def test_k3_pipeline_state_test_layer_review_count_round_trips(tmp_path: Path):
    """C-5-K3a: field round-trips through save_state / load_state with
    defensive default for pre-K-3 state files lacking the field."""
    s = pipeline_state.PipelineState()
    s.test_layer_review_count = 7
    pipeline_state.save_state(tmp_path, s)
    loaded = pipeline_state.load_state(tmp_path)
    assert loaded.test_layer_review_count == 7
    # Defensive fallback: write a legacy-style state file lacking the field.
    state_file = tmp_path / ".svp" / "pipeline_state.json"
    raw = json.loads(state_file.read_text())
    del raw["test_layer_review_count"]
    state_file.write_text(json.dumps(raw))
    legacy_loaded = pipeline_state.load_state(tmp_path)
    assert legacy_loaded.test_layer_review_count == 0


# ---------------------------------------------------------------------------
# dispatch_agent_status TESTS_FLAWED branch
# ---------------------------------------------------------------------------


def test_k3_dispatch_agent_status_increments_test_layer_review_count(tmp_path: Path):
    """C-14-K3b: TESTS_FLAWED dispatch increments the counter."""
    s = pipeline_state.PipelineState()
    s.test_layer_review_count = 2
    s.sub_stage = "implementation"
    new = routing.dispatch_agent_status(
        s,
        "implementation_agent",
        "TESTS_FLAWED: details about test fixture bug",
        tmp_path,
    )
    assert new.test_layer_review_count == 3
    assert new.sub_stage == "implementation"  # unchanged


def test_k3_dispatch_agent_status_implementation_complete_does_not_touch_counter(
    tmp_path: Path,
):
    """C-14-K3b symmetry: IMPLEMENTATION_COMPLETE leaves test_layer_review_count alone."""
    s = pipeline_state.PipelineState()
    s.test_layer_review_count = 2
    s.sub_stage = "implementation"
    new = routing.dispatch_agent_status(
        s, "implementation_agent", "IMPLEMENTATION_COMPLETE", tmp_path
    )
    assert new.test_layer_review_count == 2


# ---------------------------------------------------------------------------
# Routing: TESTS_FLAWED -> gate_3_3_test_layer_review
# ---------------------------------------------------------------------------


def _seed_state_for_implementation(tmp_path: Path, last_status: str) -> None:
    """Write a minimal pipeline_state.json + last_status.txt for a Stage 3 implementation routing pass."""
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(parents=True, exist_ok=True)
    s = pipeline_state.PipelineState()
    s.stage = "3"
    s.sub_stage = "implementation"
    s.current_unit = 5
    s.total_units = 15
    s.test_layer_review_count = 1
    pipeline_state.save_state(tmp_path, s)
    (svp_dir / "last_status.txt").write_text(last_status)


def test_k3_route_implementation_with_tests_flawed_presents_gate_3_3(tmp_path: Path):
    """C-14-K3b: routing for sub_stage='implementation' with last_status
    starting with 'TESTS_FLAWED' presents gate_3_3_test_layer_review."""
    _seed_state_for_implementation(
        tmp_path, "TESTS_FLAWED: 5/74 tests fail; fixture uses IID normal"
    )
    block = routing.route(tmp_path)
    assert block["action_type"] == "human_gate"
    assert block["gate_id"] == "gate_3_3_test_layer_review"
    # Gate prompt should surface test_layer_review_count for human context.
    assert "test_layer_review_count" in block["reminder"]


def test_k3_route_implementation_with_implementation_complete_advances_normally(
    tmp_path: Path,
):
    """The K-3 branch must NOT interfere with the existing
    IMPLEMENTATION_COMPLETE -> quality_gate_b path."""
    _seed_state_for_implementation(tmp_path, "IMPLEMENTATION_COMPLETE")
    block = routing.route(tmp_path)
    # Normal advance: routing pushes through to quality_gate_b run_command.
    assert block["action_type"] in ("run_command", "human_gate")
    assert block.get("gate_id") != "gate_3_3_test_layer_review"


# ---------------------------------------------------------------------------
# dispatch_gate_response gate_3_3 four branches
# ---------------------------------------------------------------------------


def _state_at_gate_3_3(tmp_path: Path) -> pipeline_state.PipelineState:
    s = pipeline_state.PipelineState()
    s.stage = "3"
    s.sub_stage = "implementation"
    s.current_unit = 5
    s.total_units = 15
    s.test_layer_review_count = 2
    pipeline_state.save_state(tmp_path, s)
    (tmp_path / ".svp" / "last_status.txt").write_text("TESTS_FLAWED: details")
    return s


def test_k3_dispatch_gate_3_3_tests_wrong_resets_to_test_generation(tmp_path: Path):
    """C-14-K3c TESTS WRONG: sub_stage -> test_generation; counter
    preserved (not yet a unit advance)."""
    s = _state_at_gate_3_3(tmp_path)
    new = routing.dispatch_gate_response(
        s, "gate_3_3_test_layer_review", "TESTS WRONG", project_root=tmp_path
    )
    assert new.sub_stage == "test_generation"
    assert new.test_layer_review_count == 2  # not yet an advance
    # last_status cleared.
    assert not (tmp_path / ".svp" / "last_status.txt").read_text().strip()


def test_k3_dispatch_gate_3_3_implementation_wrong_keeps_implementation_sub_stage(
    tmp_path: Path,
):
    """C-14-K3c IMPLEMENTATION WRONG: keep sub_stage='implementation';
    routing re-invokes implementation_agent."""
    s = _state_at_gate_3_3(tmp_path)
    new = routing.dispatch_gate_response(
        s, "gate_3_3_test_layer_review", "IMPLEMENTATION WRONG", project_root=tmp_path
    )
    assert new.sub_stage == "implementation"
    assert not (tmp_path / ".svp" / "last_status.txt").read_text().strip()


def test_k3_dispatch_gate_3_3_blueprint_wrong_returns_to_stage_2(tmp_path: Path):
    """C-14-K3c BLUEPRINT WRONG: stage='2', sub_stage='blueprint_dialog'
    (mirrors gate_6_2 FIX BLUEPRINT)."""
    s = _state_at_gate_3_3(tmp_path)
    new = routing.dispatch_gate_response(
        s, "gate_3_3_test_layer_review", "BLUEPRINT WRONG", project_root=tmp_path
    )
    assert new.stage == "2"
    assert new.sub_stage == "blueprint_dialog"


def test_k3_dispatch_gate_3_3_abandon_unit_appends_to_deferred_and_advances(
    tmp_path: Path,
):
    """C-14-K3c ABANDON UNIT: append current_unit to deferred_broken_units,
    advance to next unit, reset counter."""
    s = _state_at_gate_3_3(tmp_path)
    abandoned_unit = s.current_unit
    new = routing.dispatch_gate_response(
        s, "gate_3_3_test_layer_review", "ABANDON UNIT", project_root=tmp_path
    )
    assert abandoned_unit in new.deferred_broken_units
    assert new.test_layer_review_count == 0
    # Advance to next unit.
    assert new.current_unit == abandoned_unit + 1
    assert new.sub_stage == "test_generation"


def test_k3_dispatch_gate_3_3_abandon_unit_at_last_unit_ends_pipeline(tmp_path: Path):
    """C-14-K3c ABANDON UNIT at last unit: current_unit -> None, sub_stage -> None."""
    s = pipeline_state.PipelineState()
    s.stage = "3"
    s.sub_stage = "implementation"
    s.current_unit = 5
    s.total_units = 5  # last unit
    s.test_layer_review_count = 1
    pipeline_state.save_state(tmp_path, s)
    (tmp_path / ".svp" / "last_status.txt").write_text("TESTS_FLAWED: details")

    new = routing.dispatch_gate_response(
        s, "gate_3_3_test_layer_review", "ABANDON UNIT", project_root=tmp_path
    )
    assert 5 in new.deferred_broken_units
    assert new.current_unit is None
    assert new.sub_stage is None


# ---------------------------------------------------------------------------
# Unit advance resets test_layer_review_count
# ---------------------------------------------------------------------------


def test_k3_test_layer_review_count_resets_when_current_unit_advances():
    """C-14-K3d: complete_unit (Unit 6) resets test_layer_review_count."""
    s = pipeline_state.PipelineState()
    s.current_unit = 3
    s.total_units = 10
    s.sub_stage = "unit_completion"
    s.test_layer_review_count = 4
    new = state_transitions.complete_unit(s)
    assert new.test_layer_review_count == 0
    assert new.current_unit == 4


# ---------------------------------------------------------------------------
# Agent prompt string-lints (C-20-K3a + C-20-K3b)
# ---------------------------------------------------------------------------


def test_k3_implementation_agent_definition_forbids_lying_about_completion():
    """C-20-K3a: the rendered IMPLEMENTATION_AGENT_DEFINITION must contain
    explicit text forbidding declaring IMPLEMENTATION_COMPLETE while tests
    fail and forbidding agent-side classification of failures as 'test
    design flaw'."""
    text = IMPLEMENTATION_AGENT_DEFINITION
    # Forbiddance is explicit (case-insensitive scan for the lie pattern).
    lower = text.lower()
    assert "test design flaw" in lower or "test design flaws" in lower, (
        "Definition must explicitly mention the 'test design flaw' anti-pattern."
    )
    # The strict definition: ALL tests must pass.
    assert "all tests" in lower and ("pass" in lower)
    # The "lying" framing.
    assert "lying" in lower or "lie" in lower


def test_k3_implementation_agent_definition_lists_three_mutually_exclusive_statuses():
    """C-20-K3a: definition lists three mutually-exclusive terminal statuses."""
    text = IMPLEMENTATION_AGENT_DEFINITION
    assert "IMPLEMENTATION_COMPLETE" in text
    assert "TESTS_FLAWED" in text
    assert "HINT_BLUEPRINT_CONFLICT" in text
    assert "mutually exclusive" in text.lower()


def test_k3_implementation_agent_definition_documents_tests_flawed_status():
    """C-20-K3b: definition documents TESTS_FLAWED with structured-details
    requirement and scope guidance."""
    text = IMPLEMENTATION_AGENT_DEFINITION
    assert "TESTS_FLAWED: [details]" in text
    # Structured details required.
    assert "REQUIRED" in text or "required" in text
    # The four gate response options surfaced in the prompt.
    for opt in ("TESTS WRONG", "IMPLEMENTATION WRONG", "BLUEPRINT WRONG", "ABANDON UNIT"):
        assert opt in text, f"Missing gate response option {opt!r} in agent prompt"


def test_k3_implementation_agent_definition_distinguishes_tests_flawed_from_hint_blueprint_conflict():
    """C-20-K3b: definition explicitly contrasts TESTS_FLAWED with
    HINT_BLUEPRINT_CONFLICT (test-layer suspicion vs hint-vs-blueprint
    conflict)."""
    text = IMPLEMENTATION_AGENT_DEFINITION
    # Both statuses appear with their distinct scopes mentioned together.
    lower = text.lower()
    assert "test-layer" in lower or "test layer" in lower
    assert "hint" in lower
    assert "not a fallback" in lower

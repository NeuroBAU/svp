"""Cycle K-5 (S3-207) -- cross-pattern P90 audit: test_agent +
coverage_review_agent honest upstream-broken escalations.

K-3 (S3-205) closed the P90 (Honest escalation paths > false completion)
gap for the implementation_agent. WGCNA's bug report Section 7 closing
paragraph flagged that the other Stage-3 agents likely had the same
shape. K-5 confirmed both gaps and shipped two parallel fixes:

  * test_agent gains TEST_GENERATION_BLOCKED: [details] -> dispatched to
    gate_3_4_test_generation_blocked with response options
    RETRY STUB / FIX BLUEPRINT / FIX SPEC / ABANDON UNIT.

  * coverage_review_agent gains COVERAGE_AMBIGUOUS: [details] ->
    dispatched to gate_3_5_coverage_ambiguous with response options
    RETRY REVIEW / FIX BLUEPRINT / FIX SPEC / OVERRIDE.

Pattern reference: P90 (existing -- Honest escalation paths > false
completion). K-5 is a P90 audit-and-broaden cycle, not a new pattern.
"""

from __future__ import annotations

from pathlib import Path

import pipeline_state
import prepare_task
import routing

from construction_agents import (
    COVERAGE_REVIEW_AGENT_DEFINITION,
    TEST_AGENT_DEFINITION,
)


# ---------------------------------------------------------------------------
# Vocabulary assertions
# ---------------------------------------------------------------------------


def test_k5_all_gate_ids_includes_new_gates():
    """C-13-K5a: ALL_GATE_IDS contains both new gates exactly once each."""
    assert prepare_task.ALL_GATE_IDS.count("gate_3_4_test_generation_blocked") == 1
    assert prepare_task.ALL_GATE_IDS.count("gate_3_5_coverage_ambiguous") == 1


def test_k5_gate_response_options_match_gate_vocabulary_for_both_new_gates():
    """C-13-K5a / C-14-K5a: _GATE_RESPONSE_OPTIONS (Unit 13) matches
    GATE_VOCABULARY (Unit 14) character-identical for both new gates."""
    expected_3_4 = ["RETRY STUB", "FIX BLUEPRINT", "FIX SPEC", "ABANDON UNIT"]
    expected_3_5 = ["RETRY REVIEW", "FIX BLUEPRINT", "FIX SPEC", "OVERRIDE"]
    assert prepare_task._GATE_RESPONSE_OPTIONS["gate_3_4_test_generation_blocked"] == expected_3_4
    assert routing.GATE_VOCABULARY["gate_3_4_test_generation_blocked"] == expected_3_4
    assert prepare_task._GATE_RESPONSE_OPTIONS["gate_3_5_coverage_ambiguous"] == expected_3_5
    assert routing.GATE_VOCABULARY["gate_3_5_coverage_ambiguous"] == expected_3_5


def test_k5_gate_vocabulary_includes_new_gates():
    """C-14-K5a: GATE_VOCABULARY contains both new gates."""
    assert "gate_3_4_test_generation_blocked" in routing.GATE_VOCABULARY
    assert "gate_3_5_coverage_ambiguous" in routing.GATE_VOCABULARY


def test_k5_gate_id_consistency_invariant_holds():
    """Section 3.6: ALL_GATE_IDS (Unit 13) == GATE_VOCABULARY keys (Unit 14)
    after K-5 additions."""
    u13_set = set(prepare_task.ALL_GATE_IDS)
    u14_set = set(routing.GATE_VOCABULARY.keys())
    assert u13_set == u14_set


def test_k5_test_agent_allowed_statuses_includes_blocked():
    """C-14-K5a: test_agent allowed-statuses includes TEST_GENERATION_BLOCKED."""
    statuses = routing.AGENT_STATUS_LINES["test_agent"]
    assert "TEST_GENERATION_BLOCKED" in statuses
    # Existing statuses preserved.
    assert "TEST_GENERATION_COMPLETE" in statuses
    assert "REGRESSION_TEST_COMPLETE" in statuses
    assert "HINT_BLUEPRINT_CONFLICT" in statuses


def test_k5_coverage_review_agent_allowed_statuses_includes_ambiguous():
    """C-14-K5a: coverage_review_agent allowed-statuses includes COVERAGE_AMBIGUOUS."""
    statuses = routing.AGENT_STATUS_LINES["coverage_review_agent"]
    assert "COVERAGE_AMBIGUOUS" in statuses
    # Existing statuses preserved.
    assert "COVERAGE_COMPLETE: no gaps" in statuses
    assert "COVERAGE_COMPLETE: tests added" in statuses
    assert "HINT_BLUEPRINT_CONFLICT" in statuses


# ---------------------------------------------------------------------------
# dispatch_agent_status branches
# ---------------------------------------------------------------------------


def test_k5_dispatch_test_agent_blocked_does_not_advance(tmp_path: Path):
    """C-14-K5b: TEST_GENERATION_BLOCKED leaves sub_stage at test_generation."""
    s = pipeline_state.PipelineState()
    s.sub_stage = "test_generation"
    new = routing.dispatch_agent_status(
        s,
        "test_agent",
        "TEST_GENERATION_BLOCKED: stub for unit_2 fails to import (NameError)",
        tmp_path,
    )
    assert new.sub_stage == "test_generation"


def test_k5_dispatch_coverage_review_ambiguous_does_not_advance(tmp_path: Path):
    """C-14-K5b: COVERAGE_AMBIGUOUS leaves sub_stage at coverage_review."""
    s = pipeline_state.PipelineState()
    s.sub_stage = "coverage_review"
    new = routing.dispatch_agent_status(
        s,
        "coverage_review_agent",
        "COVERAGE_AMBIGUOUS: contract clause `returns the result` lacks shape spec",
        tmp_path,
    )
    assert new.sub_stage == "coverage_review"


# ---------------------------------------------------------------------------
# Routing branches
# ---------------------------------------------------------------------------


def _seed_state(tmp_path: Path, sub_stage: str, last_status: str) -> None:
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(parents=True, exist_ok=True)
    s = pipeline_state.PipelineState()
    s.stage = "3"
    s.sub_stage = sub_stage
    s.current_unit = 2
    s.total_units = 15
    pipeline_state.save_state(tmp_path, s)
    (svp_dir / "last_status.txt").write_text(last_status)


def test_k5_route_test_generation_with_blocked_presents_gate_3_4(tmp_path: Path):
    """C-14-K5c: routing for sub_stage='test_generation' with last_status
    starting with 'TEST_GENERATION_BLOCKED' presents gate_3_4."""
    _seed_state(
        tmp_path,
        "test_generation",
        "TEST_GENERATION_BLOCKED: stub fails to import",
    )
    block = routing.route(tmp_path)
    assert block["action_type"] == "human_gate"
    assert block["gate_id"] == "gate_3_4_test_generation_blocked"


def test_k5_route_coverage_review_with_ambiguous_presents_gate_3_5(tmp_path: Path):
    """C-14-K5c: routing for sub_stage='coverage_review' with last_status
    starting with 'COVERAGE_AMBIGUOUS' presents gate_3_5."""
    _seed_state(
        tmp_path,
        "coverage_review",
        "COVERAGE_AMBIGUOUS: contract clause is silent on edge case",
    )
    block = routing.route(tmp_path)
    assert block["action_type"] == "human_gate"
    assert block["gate_id"] == "gate_3_5_coverage_ambiguous"


# ---------------------------------------------------------------------------
# dispatch_gate_response gate_3_4 four branches
# ---------------------------------------------------------------------------


def _state_at_gate_3_4(tmp_path: Path) -> pipeline_state.PipelineState:
    s = pipeline_state.PipelineState()
    s.stage = "3"
    s.sub_stage = "test_generation"
    s.current_unit = 2
    s.total_units = 15
    pipeline_state.save_state(tmp_path, s)
    (tmp_path / ".svp" / "last_status.txt").write_text("TEST_GENERATION_BLOCKED: x")
    return s


def test_k5_dispatch_gate_3_4_retry_stub_resets_to_stub_generation(tmp_path: Path):
    """C-14-K5d RETRY STUB: sub_stage -> stub_generation."""
    s = _state_at_gate_3_4(tmp_path)
    new = routing.dispatch_gate_response(
        s, "gate_3_4_test_generation_blocked", "RETRY STUB", project_root=tmp_path
    )
    assert new.sub_stage == "stub_generation"
    assert not (tmp_path / ".svp" / "last_status.txt").read_text().strip()


def test_k5_dispatch_gate_3_4_fix_blueprint_returns_to_stage_2(tmp_path: Path):
    """C-14-K5d FIX BLUEPRINT: stage -> 2 (mirrors gate_6_2 FIX BLUEPRINT)."""
    s = _state_at_gate_3_4(tmp_path)
    new = routing.dispatch_gate_response(
        s, "gate_3_4_test_generation_blocked", "FIX BLUEPRINT", project_root=tmp_path
    )
    assert new.stage == "2"


def test_k5_dispatch_gate_3_4_fix_spec_returns_to_stage_1(tmp_path: Path):
    """C-14-K5d FIX SPEC: stage -> 1."""
    s = _state_at_gate_3_4(tmp_path)
    new = routing.dispatch_gate_response(
        s, "gate_3_4_test_generation_blocked", "FIX SPEC", project_root=tmp_path
    )
    assert new.stage == "1"


def test_k5_dispatch_gate_3_4_abandon_unit_appends_to_deferred(tmp_path: Path):
    """C-14-K5d ABANDON UNIT: append current_unit to deferred_broken_units."""
    s = _state_at_gate_3_4(tmp_path)
    abandoned = s.current_unit
    new = routing.dispatch_gate_response(
        s, "gate_3_4_test_generation_blocked", "ABANDON UNIT", project_root=tmp_path
    )
    assert abandoned in new.deferred_broken_units
    assert new.current_unit == abandoned + 1
    assert new.sub_stage == "test_generation"


# ---------------------------------------------------------------------------
# dispatch_gate_response gate_3_5 four branches
# ---------------------------------------------------------------------------


def _state_at_gate_3_5(tmp_path: Path) -> pipeline_state.PipelineState:
    s = pipeline_state.PipelineState()
    s.stage = "3"
    s.sub_stage = "coverage_review"
    s.current_unit = 2
    s.total_units = 15
    pipeline_state.save_state(tmp_path, s)
    (tmp_path / ".svp" / "last_status.txt").write_text("COVERAGE_AMBIGUOUS: x")
    return s


def test_k5_dispatch_gate_3_5_retry_review_keeps_coverage_review_sub_stage(tmp_path: Path):
    """C-14-K5e RETRY REVIEW: sub_stage stays at coverage_review."""
    s = _state_at_gate_3_5(tmp_path)
    new = routing.dispatch_gate_response(
        s, "gate_3_5_coverage_ambiguous", "RETRY REVIEW", project_root=tmp_path
    )
    assert new.sub_stage == "coverage_review"
    assert not (tmp_path / ".svp" / "last_status.txt").read_text().strip()


def test_k5_dispatch_gate_3_5_fix_blueprint_returns_to_stage_2(tmp_path: Path):
    """C-14-K5e FIX BLUEPRINT: stage -> 2."""
    s = _state_at_gate_3_5(tmp_path)
    new = routing.dispatch_gate_response(
        s, "gate_3_5_coverage_ambiguous", "FIX BLUEPRINT", project_root=tmp_path
    )
    assert new.stage == "2"


def test_k5_dispatch_gate_3_5_fix_spec_returns_to_stage_1(tmp_path: Path):
    """C-14-K5e FIX SPEC: stage -> 1."""
    s = _state_at_gate_3_5(tmp_path)
    new = routing.dispatch_gate_response(
        s, "gate_3_5_coverage_ambiguous", "FIX SPEC", project_root=tmp_path
    )
    assert new.stage == "1"


def test_k5_dispatch_gate_3_5_override_advances_to_unit_completion(tmp_path: Path):
    """C-14-K5e OVERRIDE: sub_stage -> unit_completion (the unit's tests
    already pass at coverage_review; we accept the unmet coverage concern
    and complete the unit)."""
    s = _state_at_gate_3_5(tmp_path)
    new = routing.dispatch_gate_response(
        s, "gate_3_5_coverage_ambiguous", "OVERRIDE", project_root=tmp_path
    )
    assert new.sub_stage == "unit_completion"


# ---------------------------------------------------------------------------
# Agent prompt string-lints (C-20-K5a + C-20-K5b)
# ---------------------------------------------------------------------------


def test_k5_test_agent_definition_documents_blocked_status():
    """C-20-K5a: TEST_AGENT_DEFINITION documents TEST_GENERATION_BLOCKED with
    structured-details requirement and gate response options."""
    text = TEST_AGENT_DEFINITION
    assert "TEST_GENERATION_BLOCKED: [details]" in text
    # Structured details requirement.
    assert "REQUIRED" in text or "required" in text
    # Four gate response options surfaced.
    for opt in ("RETRY STUB", "FIX BLUEPRINT", "FIX SPEC", "ABANDON UNIT"):
        assert opt in text


def test_k5_test_agent_definition_forbids_sys_modules_workarounds():
    """C-20-K5a: prompt explicitly forbids sys.modules synthetic-injection
    workarounds (the WGCNA bug report Section 5.2 antipattern)."""
    text = TEST_AGENT_DEFINITION
    assert "sys.modules" in text
    # And forbidden context.
    lower = text.lower()
    assert "forbidden" in lower or "do not" in lower or "must not" in lower


def test_k5_test_agent_definition_lists_three_mutually_exclusive_statuses():
    """C-20-K5a: definition clarifies the three terminal statuses are
    mutually exclusive."""
    text = TEST_AGENT_DEFINITION
    assert "TEST_GENERATION_COMPLETE" in text
    assert "TEST_GENERATION_BLOCKED" in text
    assert "HINT_BLUEPRINT_CONFLICT" in text
    assert "mutually exclusive" in text.lower()


def test_k5_coverage_review_agent_definition_documents_ambiguous_status():
    """C-20-K5b: COVERAGE_REVIEW_AGENT_DEFINITION documents
    COVERAGE_AMBIGUOUS with structured-details requirement and gate
    response options."""
    text = COVERAGE_REVIEW_AGENT_DEFINITION
    assert "COVERAGE_AMBIGUOUS: [details]" in text
    for opt in ("RETRY REVIEW", "FIX BLUEPRINT", "FIX SPEC", "OVERRIDE"):
        assert opt in text


def test_k5_coverage_review_agent_definition_forbids_synthesizing_from_guesses():
    """C-20-K5b: prompt forbids synthesizing tests from guessed contract
    semantics."""
    text = COVERAGE_REVIEW_AGENT_DEFINITION
    lower = text.lower()
    assert "guess" in lower
    assert "forbidden" in lower or "do not" in lower or "must not" in lower

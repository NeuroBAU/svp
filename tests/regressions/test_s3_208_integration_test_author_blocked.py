"""Cycle K-6 (S3-208) -- integration_test_author honest upstream-defect
escalation.

K-3 (S3-205) closed the P90 (Honest escalation paths > false completion)
gap for the implementation_agent. K-5 (S3-207) extended to test_agent and
coverage_review_agent (Stage-3 audit). WGCNA bug report Section 8
documented a third instance recurring on a fourth agent type at the
Stage 3->4 boundary: integration_test_author declared
INTEGRATION_TESTS_COMPLETE while 2/72 tests failed, lying with the
"pre-existing failures" excuse pattern.

K-6 added (P90 Stage-4 audit):

  * INTEGRATION_TESTS_BLOCKED: [details] for integration_test_author.
  * gate_4_4_integration_tests_blocked with response options
    FIX UNIT / FIX BLUEPRINT / FIX SPEC / OVERRIDE.
  * INTEGRATION_TEST_AUTHOR_DEFINITION amended: forbids the
    "pre-existing failures" lie pattern; documents BLOCKED with
    structured-details requirement.

Pattern reference: P90 (existing -- Honest escalation paths > false
completion). K-6 is a P90 audit-and-broaden Stage-4 cycle, not a new
pattern.
"""

from __future__ import annotations

from pathlib import Path

import pipeline_state
import prepare_task
import routing

from construction_agents import INTEGRATION_TEST_AUTHOR_DEFINITION


# ---------------------------------------------------------------------------
# Vocabulary assertions
# ---------------------------------------------------------------------------


def test_k6_all_gate_ids_includes_new_gate():
    """C-13-K6a: ALL_GATE_IDS contains the new gate exactly once."""
    assert prepare_task.ALL_GATE_IDS.count("gate_4_4_integration_tests_blocked") == 1


def test_k6_gate_response_options_match_gate_vocabulary():
    """C-13-K6a / C-14-K6a: _GATE_RESPONSE_OPTIONS (Unit 13) matches
    GATE_VOCABULARY (Unit 14) character-identical for the new gate."""
    expected = ["FIX UNIT", "FIX BLUEPRINT", "FIX SPEC", "OVERRIDE"]
    assert prepare_task._GATE_RESPONSE_OPTIONS["gate_4_4_integration_tests_blocked"] == expected
    assert routing.GATE_VOCABULARY["gate_4_4_integration_tests_blocked"] == expected


def test_k6_gate_vocabulary_includes_new_gate():
    """C-14-K6a: GATE_VOCABULARY contains the new gate."""
    assert "gate_4_4_integration_tests_blocked" in routing.GATE_VOCABULARY


def test_k6_gate_id_consistency_invariant_holds():
    """Section 3.6: ALL_GATE_IDS (Unit 13) == GATE_VOCABULARY keys (Unit 14)."""
    assert set(prepare_task.ALL_GATE_IDS) == set(routing.GATE_VOCABULARY.keys())


def test_k6_integration_test_author_allowed_statuses_includes_blocked():
    """C-14-K6a: integration_test_author allowed-statuses includes BLOCKED."""
    statuses = routing.AGENT_STATUS_LINES["integration_test_author"]
    assert "INTEGRATION_TESTS_BLOCKED" in statuses
    assert "INTEGRATION_TESTS_COMPLETE" in statuses


def test_k6_integration_test_author_does_not_have_hint_blueprint_conflict():
    """C-14-K6a / preserved exclusion: integration_test_author does NOT
    receive human hints; HINT_BLUEPRINT_CONFLICT is intentionally absent."""
    statuses = routing.AGENT_STATUS_LINES["integration_test_author"]
    assert "HINT_BLUEPRINT_CONFLICT" not in statuses


# ---------------------------------------------------------------------------
# dispatch_agent_status branch
# ---------------------------------------------------------------------------


def test_k6_dispatch_integration_tests_blocked_does_not_advance(tmp_path: Path):
    """C-14-K6b: INTEGRATION_TESTS_BLOCKED leaves state alone (no sub_stage advance)."""
    s = pipeline_state.PipelineState()
    s.stage = "4"
    s.sub_stage = "integration"
    new = routing.dispatch_agent_status(
        s,
        "integration_test_author",
        "INTEGRATION_TESTS_BLOCKED: 2/72 tests fail; Unit 7 NaN handling missing",
        tmp_path,
    )
    assert new.stage == "4"
    assert new.sub_stage == "integration"


# ---------------------------------------------------------------------------
# Routing branch
# ---------------------------------------------------------------------------


def _seed_state(tmp_path: Path, last_status: str) -> None:
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(parents=True, exist_ok=True)
    s = pipeline_state.PipelineState()
    s.stage = "4"
    s.sub_stage = "integration"
    s.current_unit = None
    s.total_units = 15
    pipeline_state.save_state(tmp_path, s)
    (svp_dir / "last_status.txt").write_text(last_status)


def test_k6_route_with_blocked_presents_gate_4_4(tmp_path: Path):
    """C-14-K6c: routing for sub_stage='integration' with last_status starting
    with 'INTEGRATION_TESTS_BLOCKED' presents gate_4_4."""
    _seed_state(
        tmp_path,
        "INTEGRATION_TESTS_BLOCKED: 2/72 tests fail; Unit 7 NaN handling missing",
    )
    block = routing.route(tmp_path)
    assert block["action_type"] == "human_gate"
    assert block["gate_id"] == "gate_4_4_integration_tests_blocked"


# ---------------------------------------------------------------------------
# dispatch_gate_response gate_4_4 four branches
# ---------------------------------------------------------------------------


def _state_at_gate_4_4(tmp_path: Path) -> pipeline_state.PipelineState:
    s = pipeline_state.PipelineState()
    s.stage = "4"
    s.sub_stage = "integration"
    s.current_unit = None
    s.total_units = 15
    pipeline_state.save_state(tmp_path, s)
    (tmp_path / ".svp" / "last_status.txt").write_text("INTEGRATION_TESTS_BLOCKED: x")
    return s


def test_k6_dispatch_gate_4_4_fix_unit_enters_debug_session(tmp_path: Path):
    """C-14-K6d FIX UNIT: creates a debug_session (mirrors
    gate_3_completion_failure INVESTIGATE -- enter_debug_session creates
    an unauthorized session; gate_6_0 then authorizes it on the next
    routing pass)."""
    s = _state_at_gate_4_4(tmp_path)
    assert s.debug_session is None  # pre-condition
    new = routing.dispatch_gate_response(
        s, "gate_4_4_integration_tests_blocked", "FIX UNIT", project_root=tmp_path
    )
    # debug_session is created (no longer None); authorization happens at
    # gate_6_0_debug_permission on the next routing pass.
    assert new.debug_session is not None
    assert new.debug_session.get("phase") == "triage"


def test_k6_dispatch_gate_4_4_fix_blueprint_returns_to_stage_2(tmp_path: Path):
    """C-14-K6d FIX BLUEPRINT: stage -> 2 (mirrors gate_3_3 BLUEPRINT WRONG /
    gate_3_4 FIX BLUEPRINT)."""
    s = _state_at_gate_4_4(tmp_path)
    new = routing.dispatch_gate_response(
        s, "gate_4_4_integration_tests_blocked", "FIX BLUEPRINT", project_root=tmp_path
    )
    assert new.stage == "2"


def test_k6_dispatch_gate_4_4_fix_spec_returns_to_stage_1(tmp_path: Path):
    """C-14-K6d FIX SPEC: stage -> 1."""
    s = _state_at_gate_4_4(tmp_path)
    new = routing.dispatch_gate_response(
        s, "gate_4_4_integration_tests_blocked", "FIX SPEC", project_root=tmp_path
    )
    assert new.stage == "1"


def test_k6_dispatch_gate_4_4_override_advances_to_stage_5(tmp_path: Path):
    """C-14-K6d OVERRIDE: stage -> 5 (acknowledge failures and advance to
    Stage 5; mirrors gate_3_5 OVERRIDE in spirit)."""
    s = _state_at_gate_4_4(tmp_path)
    new = routing.dispatch_gate_response(
        s, "gate_4_4_integration_tests_blocked", "OVERRIDE", project_root=tmp_path
    )
    assert new.stage == "5"


# ---------------------------------------------------------------------------
# Agent prompt string-lints (C-20-K6a)
# ---------------------------------------------------------------------------


def test_k6_integration_test_author_definition_documents_blocked_status():
    """C-20-K6a: INTEGRATION_TEST_AUTHOR_DEFINITION documents
    INTEGRATION_TESTS_BLOCKED with structured-details requirement."""
    text = INTEGRATION_TEST_AUTHOR_DEFINITION
    assert "INTEGRATION_TESTS_BLOCKED: [details]" in text
    assert "REQUIRED" in text or "required" in text
    # Four gate response options surfaced.
    for opt in ("FIX UNIT", "FIX BLUEPRINT", "FIX SPEC", "OVERRIDE"):
        assert opt in text


def test_k6_integration_test_author_definition_forbids_pre_existing_failures_lie():
    """C-20-K6a: prompt explicitly forbids the WGCNA Section 8 antipattern
    ("pre-existing failures" excuse)."""
    text = INTEGRATION_TEST_AUTHOR_DEFINITION
    assert "pre-existing" in text
    lower = text.lower()
    assert "forbidden" in lower or "do not" in lower or "must not" in lower or "must" in lower


def test_k6_integration_test_author_definition_lists_two_mutually_exclusive_statuses():
    """C-20-K6a: definition clarifies the two terminal statuses are mutually
    exclusive (no third HINT_BLUEPRINT_CONFLICT for this agent)."""
    text = INTEGRATION_TEST_AUTHOR_DEFINITION
    assert "INTEGRATION_TESTS_COMPLETE" in text
    assert "INTEGRATION_TESTS_BLOCKED" in text
    assert "mutually exclusive" in text.lower()

"""Regression: HINT_BLUEPRINT_CONFLICT must reach a human gate.

Audit 2026-07-06 (P2): no router consumed the status (the emitting agent
was re-invoked forever, re-detecting the same conflict) and both
gate_hint_conflict handler branches were placeholder no-ops.
"""

from tests.regressions.helpers import make_state, write_status

from ledger_manager import get_ledger_path
from routing import dispatch_gate_response, route


def test_hint_conflict_status_presents_gate(project_root):
    make_state(
        project_root,
        stage="3",
        sub_stage="implementation",
        current_unit=1,
        total_units=1,
    )
    write_status(project_root, "HINT_BLUEPRINT_CONFLICT: hint says use asyncio")

    action = route(project_root)

    assert action["action_type"] == "human_gate"
    assert action["gate_id"] == "gate_hint_conflict"


def test_blueprint_correct_discards_hint_ledger(project_root):
    state = make_state(
        project_root,
        stage="3",
        sub_stage="implementation",
        current_unit=1,
        total_units=1,
    )
    hint_path = get_ledger_path(project_root, "hint")
    hint_path.parent.mkdir(parents=True, exist_ok=True)
    hint_path.write_text('{"role": "human", "content": "use asyncio"}\n')

    new = dispatch_gate_response(
        state, "gate_hint_conflict", "BLUEPRINT CORRECT", project_root
    )

    assert not hint_path.exists()
    assert new.sub_stage == "implementation"  # flow resumes in place


def test_hint_correct_restarts_from_stage_2(project_root):
    state = make_state(
        project_root,
        stage="3",
        sub_stage="implementation",
        current_unit=1,
        total_units=1,
    )

    new = dispatch_gate_response(
        state, "gate_hint_conflict", "HINT CORRECT", project_root
    )

    assert new.stage == "2"
    assert new.current_unit is None

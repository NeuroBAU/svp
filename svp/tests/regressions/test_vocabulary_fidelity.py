"""Regression: Blueprint Vocabulary Fidelity cross-check (P5, 2026-07-07).

Near-miss identifier coinage (gate_5_5, DIAGNOSTIC_COMPLETE vs
DIAGNOSIS_COMPLETE) is the empirically dominant blueprint confabulation
class; it survived self-review and one cold review three times in the
SVP 2.3 self-build. The deterministic cross-check makes it a gate.
"""

from tests.regressions.helpers import make_state, write_status

from routing import _check_blueprint_vocabulary_fidelity, route


SPEC = """
## 18.1 Statuses
DIAGNOSIS_COMPLETE PROBE_COMPLETE TESTS_PASSED
## 18.4 Gates
gate_3_2_diagnostic_decision gate_hint_conflict
"""


def _write_project(root, contracts):
    (root / "specs").mkdir()
    (root / "specs" / "stakeholder_spec.md").write_text(SPEC, encoding="utf-8")
    (root / "blueprint").mkdir()
    (root / "blueprint" / "blueprint_contracts.md").write_text(
        contracts, encoding="utf-8"
    )


def test_invented_gate_and_status_are_caught(project_root):
    _write_project(
        project_root,
        'advance to gate_5_5 when `last_agent_status == "DIAGNOSTIC_COMPLETE"`\n'
        "TERMINAL_STATUS_HARDENING_PROBE_COMPLETE: str\n",
    )

    violations = _check_blueprint_vocabulary_fidelity(project_root)

    joined = "\n".join(violations)
    assert "gate_5_5" in joined
    assert "DIAGNOSTIC_COMPLETE" in joined
    assert "HARDENING_PROBE_COMPLETE" in joined
    assert len(violations) == 3


def test_spec_transcribed_vocabulary_passes(project_root):
    _write_project(
        project_root,
        'present gate_3_2_diagnostic_decision on "DIAGNOSIS_COMPLETE"; '
        'probe emits "PROBE_COMPLETE"; generic gate_id and gate_name '
        "parameters are exempt.\n",
    )

    assert _check_blueprint_vocabulary_fidelity(project_root) == []


def test_vocabulary_violation_holds_pipeline_before_gate_2_1(project_root, monkeypatch):
    import blueprint_extractor
    import structural_check

    monkeypatch.setattr(
        blueprint_extractor, "validate_unit_heading_format", lambda d: []
    )
    monkeypatch.setattr(
        structural_check, "audit_blueprint_contracts", lambda root: []
    )
    _write_project(project_root, "routing presents gate_9_9_totally_invented\n")
    make_state(project_root, stage="2", sub_stage="blueprint_dialog")
    write_status(project_root, "BLUEPRINT_DRAFT_COMPLETE")

    action = route(project_root)

    assert action["action_type"] == "pipeline_held"
    assert "gate_9_9_totally_invented" in action.get("message", "")

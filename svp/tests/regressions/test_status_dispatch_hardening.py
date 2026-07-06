"""Regression: status parsing and update_state CLI hardening.

Audit 2026-07-06 (P2): --phase without --status was a silent no-op logged
as a successful transition; a bare TRIAGE_COMPLETE crashed routing with
IndexError (eager dict.get default); exact-tuple status matching silently
re-invoked agents on near-miss suffixes; an unrecognized stage was masked
as pipeline_complete.
"""

import json

import pytest

from tests.regressions.helpers import make_state, read_state_dict, write_status

from pipeline_state import PipelineState
from routing import dispatch_agent_status, route, update_state_main


def test_phase_without_status_is_a_hard_error(project_root):
    make_state(project_root, stage="1", sub_stage=None)

    with pytest.raises(SystemExit) as exc:
        update_state_main(
            ["--phase", "redo", "--project-root", str(project_root)]
        )

    assert exc.value.code == 1


def test_bare_triage_complete_does_not_crash_routing(project_root):
    make_state(
        project_root,
        stage="5",
        sub_stage=None,
        debug_session={
            "authorized": True,
            "source": "bug_entry",
            "phase": "triage",
        },
    )
    (project_root / ".svp" / "triage_result.json").write_text(
        json.dumps({"classification": "single_unit", "affected_units": [1]}),
        encoding="utf-8",
    )
    write_status(project_root, "TRIAGE_COMPLETE")

    action = route(project_root)  # previously IndexError

    assert action["action_type"] == "human_gate"
    assert action["gate_id"] == "gate_6_2_debug_classification"
    saved = read_state_dict(project_root)
    assert saved["debug_session"]["classification"] == "single_unit"


def test_coverage_complete_suffix_variants_advance_unit(project_root):
    make_state(
        project_root,
        stage="3",
        sub_stage="coverage_review",
        current_unit=1,
        total_units=1,
    )
    write_status(project_root, "COVERAGE_COMPLETE: 2 tests added")

    route(project_root)

    assert read_state_dict(project_root)["sub_stage"] == "unit_completion"


def test_help_session_complete_suffix_variants_dispatch(project_root):
    state = PipelineState(stage="1")

    new = dispatch_agent_status(
        state,
        "help_agent",
        "HELP_SESSION_COMPLETE: hint forwarded to test agent",
        project_root,
    )

    assert new is not None


def test_unrecognized_stage_holds_instead_of_completing(project_root):
    make_state(project_root, stage="9", sub_stage=None)
    write_status(project_root, "")

    action = route(project_root)

    assert action["action_type"] == "pipeline_held"

"""Cycle H5 (S3-195) -- verify CLI completeness fixes:
(a) PHASE_TO_AGENT contains git_repo_agent and oracle_agent entries (IMPROV-30);
(b) compliance_scan_main prints COMPLIANCE_SCAN_SUCCEEDED on success (IMPROV-31).

Per S3-103, all module imports are flat (workspace `scripts/` path) -- the
sync workflow rewrites `from src.unit_N.stub` imports to flat `routing` /
`structural_check` references when deriving the runtime `scripts/*.py`.
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from routing import PHASE_TO_AGENT, dispatch_command_status
from structural_check import compliance_scan_main
from pipeline_state import PipelineState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_state(**overrides) -> PipelineState:
    """Build a minimal PipelineState with sane defaults for testing."""
    defaults = {
        "stage": "5",
        "sub_stage": "compliance_scan",
        "current_unit": None,
        "total_units": 10,
        "verified_units": [],
        "alignment_iterations": 0,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "pass_history": [],
        "debug_session": None,
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": None,
        "primary_language": "python",
        "component_languages": [],
        "secondary_language": None,
        "oracle_session_active": False,
        "oracle_test_project": None,
        "oracle_phase": None,
        "oracle_run_count": 0,
        "oracle_nested_session_path": None,
        "oracle_modification_count": 0,
        "state_hash": None,
        "spec_revision_count": 0,
        "pass_": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    defaults.update(overrides)
    return PipelineState(**defaults)


def _minimal_python_profile() -> dict:
    """Minimal profile triggering the python language path."""
    return {
        "name": "test-plugin",
        "description": "A test plugin for SVP",
        "version": "1.0.0",
        "author": "Test Author",
        "archetype": "claude_code_plugin",
        "language": {"primary": "python", "components": []},
    }


def _make_clean_project(tmp_path: Path) -> Path:
    """Construct a workspace with no compliance findings: minimal profile,
    empty src and tests directories. delivered_repo_path is unset so
    validate_delivered_repo_contents silently returns []."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    src_dir = project_root / "src"
    src_dir.mkdir()
    tests_dir = project_root / "tests"
    tests_dir.mkdir()
    (project_root / "project_profile.json").write_text(
        json.dumps(_minimal_python_profile())
    )
    (project_root / "svp_config.json").write_text(json.dumps({}))
    return project_root


# ---------------------------------------------------------------------------
# IMPROV-30 -- PHASE_TO_AGENT entries
# ---------------------------------------------------------------------------


def test_h5_phase_to_agent_includes_git_repo_agent():
    """IMPROV-30: PHASE_TO_AGENT MUST have git_repo_agent -> git_repo_agent mapping."""
    assert "git_repo_agent" in PHASE_TO_AGENT
    assert PHASE_TO_AGENT["git_repo_agent"] == "git_repo_agent"


def test_h5_phase_to_agent_includes_oracle_agent():
    """IMPROV-30: PHASE_TO_AGENT MUST have oracle_agent -> oracle_agent mapping
    (canonical form alongside the existing 'oracle' short-form key)."""
    assert "oracle_agent" in PHASE_TO_AGENT
    assert PHASE_TO_AGENT["oracle_agent"] == "oracle_agent"


def test_h5_existing_phase_to_agent_entries_unchanged():
    """Regression guard: original 8 entries still present with same mappings.

    The H5 cycle adds only `oracle_agent` and `git_repo_agent` keys; every
    pre-existing entry MUST be preserved bit-for-bit.
    """
    expected = {
        "help": "help_agent",
        "hint": "hint_agent",
        "reference_indexing": "reference_indexing",
        "redo": "redo_agent",
        "bug_triage": "bug_triage_agent",
        "oracle": "oracle_agent",
        "checklist_generation": "checklist_generation",
        "regression_adaptation": "regression_adaptation",
    }
    for k, v in expected.items():
        assert PHASE_TO_AGENT.get(k) == v, (
            f"PHASE_TO_AGENT[{k!r}] changed unexpectedly: "
            f"expected {v!r}, got {PHASE_TO_AGENT.get(k)!r}"
        )


# ---------------------------------------------------------------------------
# IMPROV-31 -- compliance_scan_main SUCCEEDED token
# ---------------------------------------------------------------------------


def test_h5_compliance_scan_main_prints_SUCCEEDED_on_success(tmp_path):
    """IMPROV-31: compliance_scan_main MUST print COMPLIANCE_SCAN_SUCCEEDED
    on the no-findings success path (non-JSON output mode)."""
    project_root = _make_clean_project(tmp_path)
    src_dir = project_root / "src"
    tests_dir = project_root / "tests"

    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            compliance_scan_main(
                [
                    "--project-root",
                    str(project_root),
                    "--src-dir",
                    str(src_dir),
                    "--tests-dir",
                    str(tests_dir),
                ]
            )
    except SystemExit:
        pass  # strict mode may exit; non-strict default exits 0 implicitly

    captured = buf.getvalue()
    assert "COMPLIANCE_SCAN_SUCCEEDED" in captured, (
        "compliance_scan_main MUST print COMPLIANCE_SCAN_SUCCEEDED on the "
        f"no-findings success path. Captured stdout: {captured!r}"
    )


def test_h5_dispatch_command_status_compliance_scan_accepts_SUCCEEDED_token(tmp_path):
    """Regression: simulate orchestrator writing 'COMPLIANCE_SCAN_SUCCEEDED'
    to last_status.txt; call dispatch_command_status; assert routing advances
    to repo_complete sub-stage (the existing compliance_scan branch matches
    'SUCCEEDED' as a substring -- the H5 token form satisfies that match)."""
    state = _make_state(stage="5", sub_stage="compliance_scan")
    result = dispatch_command_status(
        state,
        "compliance_scan",
        "COMPLIANCE_SCAN_SUCCEEDED",
        sub_stage="compliance_scan",
    )
    assert result.sub_stage == "repo_complete", (
        "dispatch_command_status compliance_scan branch MUST advance to "
        f"repo_complete on COMPLIANCE_SCAN_SUCCEEDED; got sub_stage={result.sub_stage!r}"
    )


def test_h5_compliance_scan_main_human_message_preserved(tmp_path):
    """Regression guard: 'No compliance violations found.' still appears in
    stdout (alongside the new SUCCEEDED token). The H5 cycle adds the token
    AFTER the human message; the human message MUST NOT be removed."""
    project_root = _make_clean_project(tmp_path)
    src_dir = project_root / "src"
    tests_dir = project_root / "tests"

    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            compliance_scan_main(
                [
                    "--project-root",
                    str(project_root),
                    "--src-dir",
                    str(src_dir),
                    "--tests-dir",
                    str(tests_dir),
                ]
            )
    except SystemExit:
        pass

    captured = buf.getvalue()
    assert "No compliance violations found." in captured, (
        "Human-readable message 'No compliance violations found.' MUST be "
        f"preserved on the success path. Captured stdout: {captured!r}"
    )
    assert "COMPLIANCE_SCAN_SUCCEEDED" in captured, (
        "COMPLIANCE_SCAN_SUCCEEDED token MUST also appear alongside the "
        f"human message. Captured stdout: {captured!r}"
    )

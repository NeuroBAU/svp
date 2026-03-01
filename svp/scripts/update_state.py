"""
update_state.py — CLI wrapper and phase dispatcher for SVP state transitions.

Called as the POST command after every agent invocation, gate response,
or run_command result. Reads the status file written by the main session,
dispatches to the appropriate state transition based on the phase, and
saves the updated state.

Usage:
    python scripts/update_state.py --phase PHASE --status-file PATH
                                   [--unit N] [--project-root PATH]
"""

from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
import argparse
import copy
import sys


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="SVP State Updater — POST command handler."
    )
    parser.add_argument("--phase", type=str, required=True)
    parser.add_argument("--status-file", type=str, required=True)
    parser.add_argument("--unit", type=int, default=None)
    parser.add_argument("--project-root", type=str, default=None)
    return parser.parse_args(argv)


def _count_units_from_blueprint(project_root: Path) -> int:
    """Count the number of units defined in blueprint.md by scanning for ## Unit N headings."""
    import re
    blueprint_path = project_root / "blueprint" / "blueprint.md"
    if not blueprint_path.exists():
        return 0
    try:
        text = blueprint_path.read_text(encoding="utf-8")
        units = re.findall(r"^## Unit (\d+)", text, re.MULTILINE)
        return max(int(n) for n in units) if units else 0
    except Exception:
        return 0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clone(state):
    from svp.scripts.pipeline_state import PipelineState
    return PipelineState.from_dict(copy.deepcopy(state.to_dict()))


def _tmp_status_file(project_root: Path, status: str) -> Path:
    tmp = project_root / ".svp" / "_tmp_status.txt"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(status, encoding="utf-8")
    return tmp


def main(argv=None) -> int:
    args = parse_args(argv)
    project_root = Path(args.project_root) if args.project_root else Path.cwd()
    status_file = Path(args.status_file)
    if not status_file.is_absolute():
        status_file = project_root / status_file

    scripts_dir = project_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    try:
        from svp.scripts.pipeline_state import load_state, save_state
        from state_transitions import (
            advance_stage, advance_sub_stage, advance_fix_ladder,
            restart_from_stage, update_state_from_status,
        )
    except ImportError as e:
        print(f"ERROR: Failed to import SVP modules: {e}", file=sys.stderr)
        return 1

    if not status_file.exists():
        print(f"ERROR: Status file not found: {status_file}", file=sys.stderr)
        return 1

    try:
        state = load_state(project_root)
    except Exception as e:
        print(f"ERROR: Failed to load state: {e}", file=sys.stderr)
        return 1

    status = status_file.read_text(encoding="utf-8").strip()

    try:
        new_state = _dispatch(args.phase, status, state, args.unit, project_root,
                              advance_stage, advance_sub_stage, advance_fix_ladder,
                              restart_from_stage, update_state_from_status)
    except Exception as e:
        print(f"ERROR: State transition failed for phase '{args.phase}': {e}", file=sys.stderr)
        return 1

    try:
        save_state(new_state, project_root)
    except Exception as e:
        print(f"ERROR: Failed to save state: {e}", file=sys.stderr)
        return 1

    return 0


def _dispatch(phase, status, state, unit, project_root,
              advance_stage, advance_sub_stage, advance_fix_ladder,
              restart_from_stage, update_state_from_status):
    s = status.upper()

    # Stage 0
    if phase == "hook_activation":
        new = advance_sub_stage(state, "project_context", project_root)
        new.last_action = "Hooks activated by human"
        new.updated_at = _now_iso()
        return new

    if phase == "project_context":
        new = advance_stage(state, project_root)
        new = advance_sub_stage(new, "stakeholder_dialog", project_root)
        new.last_action = "Project context created; starting stakeholder dialog"
        new.updated_at = _now_iso()
        return new

    # Stage 1
    if phase == "stakeholder_dialog":
        if "DIALOG_COMPLETE" in s:
            new = advance_sub_stage(state, "spec_draft", project_root)
            new.last_action = "Stakeholder dialog complete; drafting spec"
        else:
            new = _clone(state)
            new.last_action = f"Stakeholder dialog turn: {status}"
        new.updated_at = _now_iso()
        return new

    if phase == "stakeholder_draft":
        new = advance_sub_stage(state, "approval", project_root)
        new.last_action = "Stakeholder spec drafted; awaiting approval"
        new.updated_at = _now_iso()
        return new

    if phase == "spec_approval":
        if s.startswith("APPROVE"):
            new = advance_stage(state, project_root)
            new = advance_sub_stage(new, "blueprint_dialog", project_root)
            new.last_action = "Stakeholder spec approved; starting blueprint"
        elif s.startswith("REVISE"):
            new = advance_sub_stage(state, "spec_revision", project_root)
            new.last_action = "Spec revision requested"
        elif "FRESH REVIEW" in s:
            new = advance_sub_stage(state, "fresh_review", project_root)
            new.last_action = "Fresh spec review requested"
        else:
            new = _clone(state)
            new.last_action = f"Spec approval: {status}"
        new.updated_at = _now_iso()
        return new

    if phase == "spec_review":
        new = advance_sub_stage(state, "approval", project_root)
        new.last_action = "Spec review complete; returning to approval gate"
        new.updated_at = _now_iso()
        return new

    if phase == "spec_revision":
        new = advance_sub_stage(state, "approval", project_root)
        new.last_action = "Spec revision complete; returning to approval gate"
        new.updated_at = _now_iso()
        return new

    # Stage 2
    if phase == "blueprint_dialog":
        if "DIALOG_COMPLETE" in s:
            new = advance_sub_stage(state, "alignment_check", project_root)
            new.last_action = "Blueprint dialog complete; running alignment check"
        else:
            new = _clone(state)
            new.last_action = f"Blueprint dialog turn: {status}"
        new.updated_at = _now_iso()
        return new

    if phase == "alignment_check":
        return update_state_from_status(state, _tmp_status_file(project_root, status),
                                        unit, phase, project_root)

    if phase == "blueprint_approval":
        if s.startswith("APPROVE"):
            new = advance_stage(state, project_root)
            new.last_action = "Blueprint approved; starting infrastructure setup"
        elif s.startswith("REVISE"):
            new = advance_sub_stage(state, "blueprint_dialog", project_root)
            new.last_action = "Blueprint revision requested"
        elif "FRESH REVIEW" in s:
            new = advance_sub_stage(state, "fresh_review", project_root)
            new.last_action = "Fresh blueprint review requested"
        else:
            new = _clone(state)
            new.last_action = f"Blueprint approval: {status}"
        new.updated_at = _now_iso()
        return new

    if phase == "blueprint_review":
        new = advance_sub_stage(state, "approval", project_root)
        new.last_action = "Blueprint review complete; returning to approval gate"
        new.updated_at = _now_iso()
        return new

    if phase == "iteration_limit":
        if "REVISE SPEC" in s:
            new = advance_sub_stage(state, "spec_revision", project_root)
            new.last_action = "Iteration limit: spec revision requested"
        elif "FULL SPEC RESTART" in s:
            new = restart_from_stage(state, "1", "iteration limit: full restart", project_root)
        else:
            new = _clone(state)
            new.last_action = f"Iteration limit: {status}"
        new.updated_at = _now_iso()
        return new

    if phase == "spec_revision_stage2":
        new = advance_sub_stage(state, "blueprint_dialog", project_root)
        new.last_action = "Spec revision complete (Stage 2); restarting blueprint dialog"
        new.updated_at = _now_iso()
        return new

    # Pre-Stage-3
    if phase == "infrastructure_setup":
        new = advance_stage(state, project_root)
        new = advance_sub_stage(new, "test_generation", project_root)
        if new.current_unit is None:
            new.current_unit = 1
        new.last_action = "Infrastructure setup complete; starting unit verification"
        new.updated_at = _now_iso()
        return new

    # Stage 3 — handle sub_stage advancement explicitly
    # (state_transitions handlers update last_action but don't advance sub_stage)

    if phase == "red_run":
        new = _clone(state)
        if s.startswith("TESTS_FAILED:"):
            # Expected: tests fail against stub — advance to implementation
            new.red_run_retries = 0
            new = advance_sub_stage(new, "implementation", project_root)
            new.last_action = f"Red run passed (tests correctly failed) for unit {unit}; starting implementation"
        elif s.startswith("TESTS_PASSED:"):
            # Defective: some tests passed against stub — retry test generation
            new.red_run_retries = getattr(state, "red_run_retries", 0) + 1
            new = advance_sub_stage(new, "test_generation", project_root)
            new.last_action = f"Red run failed (tests passed against stub) for unit {unit}; retrying test generation"
        else:
            # Error — stay on red_run
            new.red_run_retries = getattr(state, "red_run_retries", 0) + 1
            new.last_action = f"Red run errored for unit {unit}: {s}"
        new.updated_at = _now_iso()
        return new

    if phase == "green_run":
        if s.startswith("TESTS_PASSED:"):
            new = _clone(state)
            new = advance_sub_stage(new, "coverage_review", project_root)
            new.fix_ladder_position = None
            new.last_action = f"Green run passed for unit {unit}; starting coverage review"
        elif s.startswith("TESTS_FAILED:"):
            # Advance fix ladder based on current position
            current_pos = state.fix_ladder_position
            if current_pos is None:
                # First failure: enter the implementation ladder
                new = advance_fix_ladder(state, "fresh_impl")
                new = advance_sub_stage(new, "implementation", project_root)
                new.last_action = f"Green run failed for unit {unit}; advancing fix ladder to fresh_impl"
            elif current_pos == "fresh_impl":
                # Second failure: escalate to diagnostic
                new = advance_fix_ladder(state, "diagnostic")
                new = advance_sub_stage(new, "diagnostic", project_root)
                new.last_action = f"Green run failed for unit {unit}; advancing fix ladder to diagnostic"
            elif current_pos == "diagnostic":
                # Third failure: escalate to diagnostic_impl
                new = advance_fix_ladder(state, "diagnostic_impl")
                new = advance_sub_stage(new, "implementation", project_root)
                new.last_action = f"Green run failed for unit {unit}; advancing fix ladder to diagnostic_impl"
            else:
                # Ladder exhausted (diagnostic_impl or unknown) — cannot recover automatically
                new = _clone(state)
                new.last_action = (
                    f"Green run failed for unit {unit}; fix ladder exhausted at {current_pos} — "
                    f"requires human intervention"
                )
        else:
            new = _clone(state)
            new.last_action = f"Green run errored for unit {unit}: {s}"
        new.updated_at = _now_iso()
        return new

    if phase == "implementation":
        new = _clone(state)
        if s.startswith("IMPLEMENTATION_COMPLETE"):
            new = advance_sub_stage(new, "green_run", project_root)
            new.last_action = f"Implementation complete for unit {unit}; running green run"
        else:
            new.last_action = f"Implementation status for unit {unit}: {s}"
        new.updated_at = _now_iso()
        return new

    if phase == "coverage_review":
        new = _clone(state)
        if s.startswith("COVERAGE_COMPLETE"):
            new = advance_sub_stage(new, "unit_completion", project_root)
            new.last_action = f"Coverage review complete for unit {unit}; completing unit"
        else:
            new.last_action = f"Coverage review status for unit {unit}: {s}"
        new.updated_at = _now_iso()
        return new

    if phase == "unit_completion":
        # complete_unit advances current_unit but not sub_stage
        # After completion: start next unit's test_generation, or advance to stage 4
        #
        # Note: we let TransitionError propagate here.  A previous version
        # had a bare `except Exception` that cloned the state unchanged and
        # fell through to set sub_stage="test_generation", silently looping
        # the unit forever.  If complete_unit() fails, that is a real error
        # and must surface to the caller.
        new = update_state_from_status(state, _tmp_status_file(project_root, status),
                                       unit, phase, project_root)

        # Resolve total_units from state or by counting units in blueprint
        total = new.total_units or state.total_units or 0
        if not total:
            total = _count_units_from_blueprint(project_root)
            new.total_units = total

        completed_unit = unit or state.current_unit
        if completed_unit and total and completed_unit >= total:
            # All units done — advance to stage 4
            new = advance_stage(new, project_root)
            new = advance_sub_stage(new, "integration_test_generation", project_root)
            new.last_action = f"All {total} units complete; starting integration tests"
        else:
            # More units remain — start test_generation for next unit
            new = advance_sub_stage(new, "test_generation", project_root)
            new.last_action = f"Unit {completed_unit} complete; starting unit {new.current_unit} test generation"
        new.updated_at = _now_iso()
        return new

    if phase == "diagnostic":
        new = _clone(state)
        if s.startswith("DIAGNOSIS_COMPLETE"):
            new = advance_sub_stage(new, "diagnostic_gate", project_root)
            new.last_action = f"Diagnostic complete for unit {unit}; awaiting gate decision"
        else:
            new.last_action = f"Diagnostic status for unit {unit}: {s}"
        new.updated_at = _now_iso()
        return new

    if phase == "test_generation":
        new = advance_sub_stage(state, "stub_generation", project_root)
        new.last_action = f"Tests generated for unit {unit}; generating stubs"
        new.updated_at = _now_iso()
        return new

    if phase == "stub_generation":
        new = advance_sub_stage(state, "red_run", project_root)
        new.last_action = f"Stubs generated for unit {unit}; running red run"
        new.updated_at = _now_iso()
        return new

    if phase == "test_validation":
        if "TEST CORRECT" in s:
            new = advance_fix_ladder(state, "fresh_impl")
            new.last_action = f"Test correct; starting implementation fix ladder (unit {unit})"
        elif "TEST WRONG" in s:
            new = advance_fix_ladder(state, "fresh_test")
            new.last_action = f"Test wrong; starting test fix ladder (unit {unit})"
        else:
            new = _clone(state)
            new.last_action = f"Test validation: {status}"
        new.updated_at = _now_iso()
        return new

    if phase == "diagnostic_gate":
        if "FIX IMPLEMENTATION" in s:
            new = advance_fix_ladder(state, "fresh_impl")
            new.last_action = f"Diagnostic gate: implementation fix (unit {unit})"
        elif "FIX DOCUMENT" in s:
            new = advance_sub_stage(state, "doc_revision", project_root)
            new.last_action = f"Diagnostic gate: document fix (unit {unit})"
        else:
            new = _clone(state)
            new.last_action = f"Diagnostic gate: {status}"
        new.updated_at = _now_iso()
        return new

    if phase == "diagnostic_escalation":
        new = advance_fix_ladder(state, "diagnostic_impl")
        new.last_action = f"Diagnostic escalation; proceeding to diagnostic impl (unit {unit})"
        new.updated_at = _now_iso()
        return new

    if phase in ("fresh_test", "hint_test"):
        new = advance_sub_stage(state, "red_run", project_root)
        new.last_action = f"Test fix ({phase}) complete; re-running red run (unit {unit})"
        new.updated_at = _now_iso()
        return new

    if phase in ("fresh_impl", "diagnostic_impl"):
        new = advance_sub_stage(state, "green_run", project_root)
        new.last_action = f"Impl fix ({phase}) complete; re-running green run (unit {unit})"
        new.updated_at = _now_iso()
        return new

    if phase == "doc_revision_stage3":
        new = advance_sub_stage(state, "restart_stage2", project_root)
        new.last_action = f"Document revision complete (Stage 3, unit {unit})"
        new.updated_at = _now_iso()
        return new

    # Stage 4
    if phase == "integration_test_generation":
        new = advance_sub_stage(state, "integration_run", project_root)
        new.last_action = "Integration tests generated"
        new.updated_at = _now_iso()
        return new

    if phase == "integration_run":
        if s.startswith("TESTS_PASSED"):
            new = advance_stage(state, project_root)
            new = advance_sub_stage(new, "repo_assembly", project_root)
            new.last_action = "Integration tests passed; starting repository delivery"
        else:
            new = advance_sub_stage(state, "failure_gate", project_root)
            new.last_action = f"Integration tests failed: {status}"
        new.updated_at = _now_iso()
        return new

    if phase == "integration_failure_gate":
        if "ASSEMBLY FIX" in s:
            new = advance_sub_stage(state, "assembly_fix", project_root)
            new.last_action = "Integration failure: assembly fix"
        elif "DOCUMENT FIX" in s:
            new = advance_sub_stage(state, "doc_revision", project_root)
            new.last_action = "Integration failure: document fix"
        else:
            new = _clone(state)
            new.last_action = f"Integration failure gate: {status}"
        new.updated_at = _now_iso()
        return new

    if phase == "assembly_fix":
        new = advance_sub_stage(state, "assembly_retest_unit", project_root)
        new.last_action = "Assembly fix complete; re-running unit tests"
        new.updated_at = _now_iso()
        return new

    if phase == "assembly_retest_unit":
        if s.startswith("TESTS_PASSED"):
            new = advance_sub_stage(state, "assembly_retest_integration", project_root)
            new.last_action = "Unit tests passed after assembly fix"
        else:
            new = advance_sub_stage(state, "failure_gate", project_root)
            new.last_action = f"Unit tests failed after assembly fix: {status}"
        new.updated_at = _now_iso()
        return new

    if phase == "assembly_retest_integration":
        if s.startswith("TESTS_PASSED"):
            new = advance_stage(state, project_root)
            new = advance_sub_stage(new, "repo_assembly", project_root)
            new.last_action = "Integration tests passed after assembly fix"
        else:
            new = advance_sub_stage(state, "failure_gate", project_root)
            new.last_action = f"Integration tests still failing: {status}"
        new.updated_at = _now_iso()
        return new

    if phase == "doc_revision_stage4":
        new = advance_sub_stage(state, "restart_stage2", project_root)
        new.last_action = "Document revision complete (Stage 4)"
        new.updated_at = _now_iso()
        return new

    # Stage 5
    if phase == "repo_assembly":
        new = advance_sub_stage(state, "test_gate", project_root)
        new.last_action = "Repository assembled; awaiting test verification"
        new.updated_at = _now_iso()
        return new

    if phase == "repo_test_gate":
        if "TESTS PASSED" in s:
            new = advance_sub_stage(state, "complete", project_root)
            new.last_action = "Repository tests passed; pipeline complete"
        elif "TESTS FAILED" in s:
            new = advance_sub_stage(state, "fix_cycle", project_root)
            new.last_action = f"Repository tests failed: {status}"
        else:
            new = _clone(state)
            new.last_action = f"Repo test gate: {status}"
        new.updated_at = _now_iso()
        return new

    if phase == "repo_fix":
        new = advance_sub_stage(state, "test_gate", project_root)
        new.last_action = "Repository fix complete; re-running tests"
        new.updated_at = _now_iso()
        return new

    # Delegated phases
    if phase in ("stage_advance", "sub_stage_advance", "fix_ladder_advance", "restart", "redo"):
        return update_state_from_status(state, _tmp_status_file(project_root, status),
                                        unit, phase, project_root)

    # Unknown phase
    new = _clone(state)
    new.last_action = f"Unrecognized phase '{phase}': {status}"
    new.updated_at = _now_iso()
    return new


if __name__ == "__main__":
    sys.exit(main())

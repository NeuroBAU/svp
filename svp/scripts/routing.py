"""Unit 14: Routing and Test Execution.

Provides routing logic, test output parsing, gate/agent/command dispatch,
and CLI entry points for the SVP 2.2 pipeline.
"""

import argparse
import copy
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_scripts_dir = str(Path(__file__).resolve().parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from svp_config import (
    ARTIFACT_FILENAMES,
    DEFAULT_CONFIG,
    derive_env_name,
    load_config,
)
from language_registry import LANGUAGE_REGISTRY, RunResult
from toolchain_reader import load_toolchain, resolve_command
from pipeline_state import PipelineState, load_state, save_state
from state_transitions import (
    abandon_debug_session,
    abandon_oracle_session,
    advance_fix_ladder,
    advance_stage,
    advance_sub_stage,
    authorize_debug_session,
    complete_debug_session,
    complete_oracle_session,
    complete_redo_profile_revision,
    complete_unit,
    enter_debug_session,
    enter_oracle_session,
    enter_pass_2,
    enter_redo_profile_revision,
    increment_alignment_iteration,
    increment_red_run_retries,
    restart_from_stage,
    rollback_to_unit,
    set_debug_classification,
    update_debug_phase,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GATE_VOCABULARY: Dict[str, List[str]] = {
    "gate_0_1_hook_activation": ["HOOKS ACTIVATED", "HOOKS FAILED"],
    "gate_0_2_context_approval": [
        "CONTEXT APPROVED",
        "CONTEXT REJECTED",
        "CONTEXT NOT READY",
    ],
    "gate_0_3_profile_approval": ["PROFILE APPROVED", "PROFILE REJECTED"],
    "gate_0_3r_profile_revision": ["PROFILE APPROVED", "PROFILE REJECTED"],
    "gate_1_1_spec_draft": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_1_2_spec_post_review": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_2_1_blueprint_approval": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_2_2_blueprint_post_review": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_2_3_alignment_exhausted": [
        "REVISE SPEC",
        "RESTART SPEC",
        "RETRY BLUEPRINT",
    ],
    "gate_3_1_test_validation": ["TEST CORRECT", "TEST WRONG"],
    "gate_3_2_diagnostic_decision": [
        "FIX IMPLEMENTATION",
        "FIX BLUEPRINT",
        "FIX SPEC",
    ],
    "gate_3_completion_failure": [
        "INVESTIGATE",
        "FORCE ADVANCE",
        "RESTART STAGE 3",
    ],
    "gate_4_1_integration_failure": ["ASSEMBLY FIX", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_4_1a": ["HUMAN FIX", "ESCALATE"],
    "gate_4_2_assembly_exhausted": ["FIX BLUEPRINT", "FIX SPEC"],
    "gate_4_3_adaptation_review": [
        "ACCEPT ADAPTATIONS",
        "MODIFY TEST",
        "REMOVE TEST",
    ],
    "gate_5_1_repo_test": ["TESTS PASSED", "TESTS FAILED"],
    "gate_5_2_assembly_exhausted": ["RETRY ASSEMBLY", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_5_3_unused_functions": ["FIX SPEC", "OVERRIDE CONTINUE"],
    "gate_6_0_debug_permission": ["AUTHORIZE DEBUG", "ABANDON DEBUG"],
    "gate_6_1_regression_test": ["TEST CORRECT", "TEST WRONG"],
    "gate_6_1a_divergence_warning": ["PROCEED", "FIX DIVERGENCE", "ABANDON DEBUG"],
    "gate_6_2_debug_classification": [
        "FIX UNIT",
        "FIX BLUEPRINT",
        "FIX SPEC",
        "FIX IN PLACE",
    ],
    "gate_6_3_repair_exhausted": [
        "RETRY REPAIR",
        "RECLASSIFY BUG",
        "ABANDON DEBUG",
    ],
    "gate_6_4_non_reproducible": ["RETRY TRIAGE", "ABANDON DEBUG"],
    "gate_6_5_debug_commit": ["COMMIT APPROVED", "COMMIT REJECTED"],
    "gate_hint_conflict": ["BLUEPRINT CORRECT", "HINT CORRECT"],
    "gate_7_a_trajectory_review": [
        "APPROVE TRAJECTORY",
        "MODIFY TRAJECTORY",
        "ABORT",
    ],
    "gate_7_b_fix_plan_review": ["APPROVE FIX", "ABORT"],
    "gate_pass_transition_post_pass1": ["PROCEED TO PASS 2", "FIX BUGS"],
    "gate_pass_transition_post_pass2": ["FIX BUGS", "RUN ORACLE"],
}

# Alias for backward compatibility
GATE_RESPONSES: Dict[str, List[str]] = GATE_VOCABULARY

PHASE_TO_AGENT: Dict[str, str] = {
    "help": "help_agent",
    "hint": "hint_agent",
    "reference_indexing": "reference_indexing",
    "redo": "redo_agent",
    "bug_triage": "bug_triage",
    "oracle": "oracle_agent",
    "checklist_generation": "checklist_generation",
    "regression_adaptation": "regression_adaptation",
}

AGENT_STATUS_LINES: Dict[str, List[str]] = {
    "setup_agent": [
        "PROJECT_CONTEXT_COMPLETE",
        "PROJECT_CONTEXT_REJECTED",
        "PROFILE_COMPLETE",
    ],
    "stakeholder_dialog": [
        "SPEC_DRAFT_COMPLETE",
        "SPEC_REVISION_COMPLETE",
    ],
    "stakeholder_reviewer": [
        "REVIEW_COMPLETE",
    ],
    "blueprint_author": [
        "BLUEPRINT_DRAFT_COMPLETE",
        "BLUEPRINT_REVISION_COMPLETE",
    ],
    "blueprint_reviewer": [
        "REVIEW_COMPLETE",
    ],
    "blueprint_checker": [
        "ALIGNMENT_CONFIRMED",
        "ALIGNMENT_FAILED: blueprint",
        "ALIGNMENT_FAILED: spec",
    ],
    "checklist_generation": [
        "CHECKLISTS_COMPLETE",
    ],
    "test_agent": [
        "TEST_GENERATION_COMPLETE",
        "REGRESSION_TEST_COMPLETE",
        "HINT_BLUEPRINT_CONFLICT",
    ],
    "implementation_agent": [
        "IMPLEMENTATION_COMPLETE",
        "HINT_BLUEPRINT_CONFLICT",
    ],
    "coverage_review_agent": [
        "COVERAGE_COMPLETE: no gaps",
        "COVERAGE_COMPLETE: tests added",
        "HINT_BLUEPRINT_CONFLICT",
    ],
    "diagnostic_agent": [
        "DIAGNOSIS_COMPLETE",
        "HINT_BLUEPRINT_CONFLICT",
    ],
    "integration_test_author": [
        "INTEGRATION_TESTS_COMPLETE",
    ],
    "regression_adaptation": [
        "ADAPTATION_COMPLETE",
        "ADAPTATION_NEEDS_REVIEW",
    ],
    "git_repo_agent": [
        "REPO_ASSEMBLY_COMPLETE",
    ],
    "bug_triage_agent": [
        "TRIAGE_COMPLETE: single_unit",
        "TRIAGE_COMPLETE: cross_unit",
        "TRIAGE_COMPLETE: build_env",
        "TRIAGE_NON_REPRODUCIBLE",
        "TRIAGE_NEEDS_REFINEMENT",
    ],
    "repair_agent": [
        "REPAIR_COMPLETE",
        "REPAIR_RECLASSIFY",
        "REPAIR_FAILED",
    ],
    "oracle_agent": [
        "ORACLE_DRY_RUN_COMPLETE",
        "ORACLE_FIX_APPLIED",
        "ORACLE_ALL_CLEAR",
        "ORACLE_HUMAN_ABORT",
    ],
    "help_agent": [
        "HELP_SESSION_COMPLETE: no hint",
        "HELP_SESSION_COMPLETE: hint forwarded",
    ],
    "hint_agent": [
        "HINT_ANALYSIS_COMPLETE",
        "HINT_BLUEPRINT_CONFLICT",
    ],
    "reference_indexing": [
        "INDEXING_COMPLETE",
    ],
    "redo_agent": [
        "REDO_CLASSIFIED: spec",
        "REDO_CLASSIFIED: blueprint",
        "REDO_CLASSIFIED: gate",
        "REDO_CLASSIFIED: profile_delivery",
        "REDO_CLASSIFIED: profile_blueprint",
    ],
}


# ---------------------------------------------------------------------------
# Test output parsers
# ---------------------------------------------------------------------------


def _parse_pytest_output(
    output: str, language: str, exit_code: int, context: Dict[str, Any]
) -> RunResult:
    """Parse pytest stdout for pass/fail/error counts."""
    try:
        collection_error_indicators = context.get(
            "collection_error_indicators",
            LANGUAGE_REGISTRY.get("python", {}).get("collection_error_indicators", []),
        )
        has_collection_error = any(
            indicator in output for indicator in collection_error_indicators
        )

        if has_collection_error:
            passed, failed, errors = 0, 0, 0
            m = re.search(r"(\d+)\s+passed", output)
            if m:
                passed = int(m.group(1))
            m = re.search(r"(\d+)\s+failed", output)
            if m:
                failed = int(m.group(1))
            m = re.search(r"(\d+)\s+error", output)
            if m:
                errors = int(m.group(1))
            return RunResult(
                status="TESTS_ERROR",
                passed=passed,
                failed=failed,
                errors=max(errors, 1),
                output=output,
                collection_error=True,
            )

        passed = 0
        failed = 0
        errors = 0

        m = re.search(r"(\d+)\s+passed", output)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+)\s+failed", output)
        if m:
            failed = int(m.group(1))
        m = re.search(r"(\d+)\s+error", output)
        if m:
            errors = int(m.group(1))

        if "no tests ran" in output:
            return RunResult(
                status="TESTS_ERROR",
                passed=0,
                failed=0,
                errors=1,
                output=output,
                collection_error=False,
            )

        if errors > 0:
            status = "TESTS_ERROR"
        elif failed > 0:
            status = "TESTS_FAILED"
        elif passed > 0:
            status = "TESTS_PASSED"
        else:
            status = "TESTS_ERROR"

        return RunResult(
            status=status,
            passed=passed,
            failed=failed,
            errors=errors,
            output=output,
            collection_error=False,
        )
    except Exception:
        return RunResult(
            status="TESTS_ERROR",
            passed=0,
            failed=0,
            errors=0,
            output=output,
            collection_error=False,
        )


def _parse_testthat_output(
    output: str, language: str, exit_code: int, context: Dict[str, Any]
) -> RunResult:
    """Parse testthat output for OK/Failed/Warnings counts."""
    try:
        collection_error_indicators = context.get(
            "collection_error_indicators",
            LANGUAGE_REGISTRY.get("r", {}).get("collection_error_indicators", []),
        )
        has_collection_error = any(
            indicator in output for indicator in collection_error_indicators
        )

        if has_collection_error:
            return RunResult(
                status="TESTS_ERROR",
                passed=0,
                failed=0,
                errors=1,
                output=output,
                collection_error=True,
            )

        passed = 0
        failed = 0
        errors = 0

        m = re.search(r"OK:\s*(\d+)", output)
        if m:
            passed = int(m.group(1))
        m = re.search(r"Failed:\s*(\d+)", output)
        if m:
            failed = int(m.group(1))
        m = re.search(r"Warnings?:\s*(\d+)", output)
        if m:
            errors = int(m.group(1))

        if failed > 0:
            status = "TESTS_FAILED"
        elif errors > 0:
            status = "TESTS_ERROR"
        elif passed > 0:
            status = "TESTS_PASSED"
        else:
            status = "TESTS_ERROR"

        return RunResult(
            status=status,
            passed=passed,
            failed=failed,
            errors=errors,
            output=output,
            collection_error=False,
        )
    except Exception:
        return RunResult(
            status="TESTS_ERROR",
            passed=0,
            failed=0,
            errors=0,
            output=output,
            collection_error=False,
        )


def _parse_markdown_lint_output(
    output: str, language: str, exit_code: int, context: Dict[str, Any]
) -> RunResult:
    """Parse markdown lint output."""
    try:
        stripped = output.strip()
        if stripped == "" or exit_code == 0:
            return RunResult(
                status="TESTS_PASSED",
                passed=1,
                failed=0,
                errors=0,
                output=output,
                collection_error=False,
            )
        else:
            error_count = len([line for line in stripped.split("\n") if line.strip()])
            return RunResult(
                status="TESTS_FAILED",
                passed=0,
                failed=max(error_count, 1),
                errors=0,
                output=output,
                collection_error=False,
            )
    except Exception:
        return RunResult(
            status="TESTS_ERROR",
            passed=0,
            failed=0,
            errors=0,
            output=output,
            collection_error=False,
        )


def _parse_bash_syntax_output(
    output: str, language: str, exit_code: int, context: Dict[str, Any]
) -> RunResult:
    """Parse bash -n syntax check output."""
    try:
        stripped = output.strip()
        if stripped == "" or exit_code == 0:
            return RunResult(
                status="TESTS_PASSED",
                passed=1,
                failed=0,
                errors=0,
                output=output,
                collection_error=False,
            )
        else:
            error_count = len([line for line in stripped.split("\n") if line.strip()])
            return RunResult(
                status="TESTS_FAILED",
                passed=0,
                failed=max(error_count, 1),
                errors=0,
                output=output,
                collection_error=False,
            )
    except Exception:
        return RunResult(
            status="TESTS_ERROR",
            passed=0,
            failed=0,
            errors=0,
            output=output,
            collection_error=False,
        )


def _parse_json_validation_output(
    output: str, language: str, exit_code: int, context: Dict[str, Any]
) -> RunResult:
    """Parse JSON validation output."""
    try:
        if exit_code == 0:
            return RunResult(
                status="TESTS_PASSED",
                passed=1,
                failed=0,
                errors=0,
                output=output,
                collection_error=False,
            )
        else:
            return RunResult(
                status="TESTS_FAILED",
                passed=0,
                failed=1,
                errors=0,
                output=output,
                collection_error=False,
            )
    except Exception:
        return RunResult(
            status="TESTS_ERROR",
            passed=0,
            failed=0,
            errors=0,
            output=output,
            collection_error=False,
        )


TEST_OUTPUT_PARSERS: Dict[str, Callable[[str, str, int, Dict[str, Any]], RunResult]] = {
    "python": _parse_pytest_output,
    "r": _parse_testthat_output,
    "plugin_markdown": _parse_markdown_lint_output,
    "plugin_bash": _parse_bash_syntax_output,
    "plugin_json": _parse_json_validation_output,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _copy(state: Any) -> Any:
    """Return a deep copy of state. Works with PipelineState and MagicMock."""
    return copy.deepcopy(state)


def _bootstrap_oracle_nested_session(
    state: Any, project_root: Path
) -> Any:
    """Create a nested session workspace for oracle green_run execution.

    Creates workspace directory, copies project files, stores path in state.
    """
    import shutil

    run_count = state.oracle_run_count or 1
    workspace_name = f"oracle-session-{run_count}"
    workspace = project_root.parent / workspace_name

    # Clean up existing workspace
    if workspace.exists():
        shutil.rmtree(str(workspace))

    workspace.mkdir(parents=True)

    # Copy essential files for the nested session
    for item in ["specs", "blueprint", ".svp"]:
        src = project_root / item
        if src.exists():
            if src.is_dir():
                shutil.copytree(str(src), str(workspace / item))
            else:
                shutil.copy2(str(src), str(workspace / item))

    # Copy project_profile.json and svp_config.json
    for fname in ["project_profile.json", "svp_config.json", "project_context.md"]:
        src = project_root / fname
        if src.is_file():
            shutil.copy2(str(src), str(workspace / fname))

    # Update state with nested session path
    new = _copy(state)
    new.oracle_nested_session_path = str(workspace)
    return new


def _read_last_status(project_root: Path) -> str:
    """Read the last_status.txt file, returning empty string if absent."""
    status_path = project_root / ARTIFACT_FILENAMES["last_status"]
    try:
        return status_path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return ""


def _clear_last_status(project_root: Path) -> None:
    """Clear the last_status.txt file."""
    status_path = project_root / ARTIFACT_FILENAMES["last_status"]
    try:
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text("", encoding="utf-8")
    except OSError:
        pass


def _load_config_safe(project_root: Path) -> Dict[str, Any]:
    """Load config, returning defaults on failure."""
    try:
        return load_config(project_root)
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_CONFIG)


def _get_iteration_limit(project_root: Path) -> int:
    """Get iteration_limit from config."""
    config = _load_config_safe(project_root)
    return config.get("iteration_limit", 3)


def _make_action_block(
    action_type: str,
    agent_type: Optional[str] = None,
    command: Optional[str] = None,
    gate_id: Optional[str] = None,
    prepare: Optional[str] = None,
    post: Optional[str] = None,
    reminder: str = "",
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an action block dict with standard keys."""
    block: Dict[str, Any] = {
        "action_type": action_type,
        "reminder": reminder,
    }
    if agent_type is not None:
        block["agent_type"] = agent_type
    if command is not None:
        block["command"] = command
    if gate_id is not None:
        block["gate_id"] = gate_id
    if prepare is not None:
        block["prepare"] = prepare
    if post is not None:
        block["post"] = post
    if message is not None:
        block["message"] = message
    return block


def _agent_prepare_cmd(agent_type: str, unit: Optional[int] = None) -> str:
    """Build the prepare_task.py command for an invoke_agent action block."""
    cmd = (
        f"python scripts/prepare_task.py --agent {agent_type} "
        f"--project-root . --output .svp/task_prompt.md"
    )
    if unit is not None:
        cmd += f" --unit {unit}"
    return cmd


def _append_build_log(
    project_root: Path, source: str, event_type: str, **extra: Any
) -> None:
    """Append a JSONL line to the build log."""
    log_path = project_root / ARTIFACT_FILENAMES["build_log"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "event_type": event_type,
    }
    entry.update(extra)
    line = json.dumps(entry, ensure_ascii=False)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _load_state_from_dict(data: Dict[str, Any]) -> PipelineState:
    """Construct PipelineState from a JSON-loaded dict."""
    pass_val = data.pop("pass", None)
    return PipelineState(
        stage=data.get("stage", "0"),
        sub_stage=data.get("sub_stage", None),
        current_unit=data.get("current_unit", None),
        total_units=data.get("total_units", 0),
        verified_units=data.get("verified_units", []),
        alignment_iterations=data.get("alignment_iterations", 0),
        fix_ladder_position=data.get("fix_ladder_position", None),
        red_run_retries=data.get("red_run_retries", 0),
        pass_history=data.get("pass_history", []),
        debug_session=data.get("debug_session", None),
        debug_history=data.get("debug_history", []),
        redo_triggered_from=data.get("redo_triggered_from", None),
        delivered_repo_path=data.get("delivered_repo_path", None),
        primary_language=data.get("primary_language", "python"),
        component_languages=data.get("component_languages", []),
        secondary_language=data.get("secondary_language", None),
        oracle_session_active=data.get("oracle_session_active", False),
        oracle_test_project=data.get("oracle_test_project", None),
        oracle_phase=data.get("oracle_phase", None),
        oracle_run_count=data.get("oracle_run_count", 0),
        oracle_nested_session_path=data.get("oracle_nested_session_path", None),
        oracle_modification_count=data.get("oracle_modification_count", 0),
        state_hash=data.get("state_hash", None),
        spec_revision_count=data.get("spec_revision_count", 0),
        pass_=pass_val,
        pass2_nested_session_path=data.get("pass2_nested_session_path", None),
        deferred_broken_units=data.get("deferred_broken_units", []),
    )


def _load_state_safe(project_root: Path) -> PipelineState:
    """Load state from pipeline_state.json, trying multiple locations.

    Searches: project_root/pipeline_state.json, then project_root/.svp/pipeline_state.json.
    Returns default PipelineState() if neither exists.
    """
    # Try primary location via Unit 5 load_state
    try:
        return load_state(project_root)
    except FileNotFoundError:
        pass

    # Try .svp/ location (used by routing script infrastructure)
    svp_state_path = project_root / ".svp" / ARTIFACT_FILENAMES["pipeline_state"]
    try:
        with open(svp_state_path, "r") as f:
            data = json.load(f)
        return _load_state_from_dict(data)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    return PipelineState()


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def _validate_stage3_completion(
    state: PipelineState, project_root: Path
) -> Optional[str]:
    """Validate Stage 3 completion requirements.

    Returns None if valid, or an error message if validation fails.
    """
    if state.total_units == 0:
        return "No units defined (total_units is 0)"

    verified_unit_numbers = {vu.get("unit") for vu in state.verified_units}
    for i in range(1, state.total_units + 1):
        if i not in verified_unit_numbers:
            return f"Unit {i} not verified"

    return None


def route(project_root: Path) -> Dict[str, Any]:
    """Route the pipeline based on current state and last status.

    Returns action block dict with keys: action_type, agent_type (optional),
    command (optional), gate_id (optional), prepare (optional), post (optional),
    reminder (str).
    """
    project_root = Path(project_root)
    state = _load_state_safe(project_root)
    last_status = _read_last_status(project_root)
    config = _load_config_safe(project_root)
    iteration_limit = config.get("iteration_limit", 3)

    # Debug session routing takes highest priority (including oracle-initiated debug)
    if state.debug_session is not None:
        return _route_debug(state, project_root, last_status, iteration_limit)

    # Oracle routing (resumes after debug completes since oracle_session_active persists)
    if state.oracle_session_active:
        return _route_oracle(state, project_root, last_status, iteration_limit)

    # Pass 2 routing
    if state.sub_stage == "pass2_active":
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="pass2_nested",
            reminder="Pass 2 nested session active.",
        )

    stage = state.stage
    sub_stage = state.sub_stage

    # Stage 0
    if stage == "0":
        return _route_stage_0(state, project_root, last_status)

    # Stage 1
    if stage == "1":
        return _route_stage_1(state, project_root, last_status)

    # Stage 2
    if stage == "2":
        return _route_stage_2(state, project_root, last_status, iteration_limit)

    # pre_stage_3
    if stage == "pre_stage_3":
        return _route_pre_stage_3(state, project_root, last_status)

    # Stage 3
    if stage == "3":
        return _route_stage_3(state, project_root, last_status, iteration_limit)

    # Stage 4
    if stage == "4":
        return _route_stage_4(state, project_root, last_status, iteration_limit)

    # Stage 5
    if stage == "5":
        return _route_stage_5(state, project_root, last_status, iteration_limit)

    return _make_action_block(
        action_type="pipeline_complete",
        reminder="Pipeline is in an unrecognized stage.",
    )


def _route_oracle(
    state: PipelineState,
    project_root: Path,
    last_status: str,
    iteration_limit: int,
) -> Dict[str, Any]:
    """Route oracle session phases."""
    phase = state.oracle_phase

    if phase == "dry_run":
        if not state.oracle_test_project:
            # Bug S3-76 + S3-77: build the complete test project list
            # deterministically and include the post command + mapping.
            e_dirs: List[Path] = []
            e_display: List[str] = []
            examples_dir = project_root / "examples"
            if examples_dir.is_dir():
                for d in sorted(examples_dir.iterdir()):
                    if not d.is_dir():
                        continue
                    e_dirs.append(d)
                    manifest = d / "oracle_manifest.json"
                    if manifest.is_file():
                        try:
                            data = json.loads(manifest.read_text(encoding="utf-8"))
                            name = data.get("name", d.name)
                            desc = data.get("description", "")
                            mode = data.get("oracle_mode", "product")
                            tag = "E-mode" if mode == "product" else "F-mode"
                            e_display.append(
                                f"{name} ({d.name}/) \u2014 {desc} [{tag}]"
                            )
                        except (json.JSONDecodeError, OSError):
                            e_display.append(
                                f"{d.name} \u2014 [no manifest \u2014 mode unknown]"
                            )
                    else:
                        e_display.append(
                            f"{d.name} \u2014 [no manifest \u2014 mode unknown]"
                        )

            # Build the display list
            lines = ["Available test projects for /svp:oracle:", ""]
            lines.append("  F-mode (Machinery Testing):")
            lines.append(
                "  1. SVP Pipeline \u2014 Machinery testing: "
                "rebuilds the SVP project itself. [F-mode]"
            )
            lines.append("")
            lines.append("  E-mode (Product Testing):")
            for i, entry in enumerate(e_display, start=2):
                lines.append(f"  {i}. {entry}")
            total = 1 + len(e_display)
            lines.append("")
            lines.append(
                f"Select a test project (1\u2013{total}), or ask a question:"
            )
            project_list = "\n".join(lines)

            # Bug S3-77: build the number-to-path mapping
            mapping = ["", "After the human selects a number, write the "
                       "corresponding PATH to .svp/last_status.txt, "
                       "then run the POST command.", ""]
            mapping.append("  Number-to-path mapping:")
            mapping.append("  1 \u2192 docs/")
            for i, d in enumerate(e_dirs, start=2):
                mapping.append(f"  {i} \u2192 examples/{d.name}/")
            mapping_text = "\n".join(mapping)

            return _make_action_block(
                action_type="oracle_select_test_project",
                reminder=(
                    "Present the test project list below to the human "
                    "verbatim. Do NOT modify it, scan directories, or "
                    "add your own analysis.\n\n"
                    + project_list + mapping_text
                ),
                post=(
                    "python scripts/update_state.py "
                    "--command oracle_test_project_selection "
                    "--project-root ."
                ),
            )
        if last_status.startswith("ORACLE_DRY_RUN_COMPLETE"):
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_7_a_trajectory_review",
                reminder="Review oracle trajectory plan.",
                post=(
                    "python scripts/update_state.py "
                    "--command oracle_gate_7a "
                    "--project-root ."
                ),
            )
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="oracle_agent",
            prepare=_agent_prepare_cmd("oracle_agent"),
            reminder="Oracle dry run.",
        )

    if phase == "gate_a":
        mod_count = getattr(state, "oracle_modification_count", 0)
        reminder = "Review oracle trajectory plan."
        if mod_count >= 3:
            reminder += (
                f" WARNING: Modification count is {mod_count} (limit: 3)."
                " Consider approving or aborting rather than modifying again."
            )
        return _make_action_block(
            action_type="human_gate",
            gate_id="gate_7_a_trajectory_review",
            reminder=reminder,
            post=(
                "python scripts/update_state.py "
                "--command oracle_gate_7a "
                "--project-root ."
            ),
        )

    if phase == "green_run":
        if not state.oracle_nested_session_path:
            # Bootstrap nested session on first green_run entry
            state = _bootstrap_oracle_nested_session(state, project_root)
            save_state(project_root, state)

        # Check if we just completed a fix (debug_session was active, now cleared)
        if state.oracle_nested_session_path and last_status.startswith(
            "REPO_ASSEMBLY_COMPLETE"
        ):
            # Tear down stale nested session and recreate with fixed code
            import shutil

            stale_path = Path(state.oracle_nested_session_path)
            if stale_path.exists():
                shutil.rmtree(str(stale_path))
            state = _bootstrap_oracle_nested_session(state, project_root)
            save_state(project_root, state)

        if last_status == "ORACLE_ALL_CLEAR":
            state = complete_oracle_session(state, "all_clear")
            save_state(project_root, state)
            return _make_action_block(
                action_type="pipeline_complete",
                reminder="Oracle all clear - no issues found.",
            )
        if last_status == "ORACLE_FIX_APPLIED":
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_7_b_fix_plan_review",
                reminder="Review oracle fix plan.",
                post=(
                    "python scripts/update_state.py "
                    "--command oracle_gate_7b "
                    "--project-root ."
                ),
            )
        if last_status == "ORACLE_HUMAN_ABORT":
            state = abandon_oracle_session(state)
            save_state(project_root, state)
            try:
                from ledger_manager import append_oracle_run_entry

                append_oracle_run_entry(
                    project_root,
                    {
                        "run_number": state.oracle_run_count,
                        "test_project": state.oracle_test_project,
                        "exit_reason": "abort",
                        "oracle_phase": phase,
                    },
                )
            except (ImportError, Exception):
                pass
            return _make_action_block(
                action_type="pipeline_complete",
                reminder="Oracle session aborted by human.",
            )
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="oracle_agent",
            prepare=_agent_prepare_cmd("oracle_agent"),
            reminder="Oracle green run.",
        )

    if phase == "gate_b":
        return _make_action_block(
            action_type="human_gate",
            gate_id="gate_7_b_fix_plan_review",
            reminder="Review oracle fix plan.",
            post=(
                "python scripts/update_state.py "
                "--command oracle_gate_7b "
                "--project-root ."
            ),
        )

    if phase == "exit":
        # Clean up nested session workspace (unless E-mode keeps artifacts)
        if state.oracle_nested_session_path:
            nested_path = Path(state.oracle_nested_session_path)
            test_project = state.oracle_test_project or ""
            # E-mode: keep GoL project for human inspection
            # F-mode: clean up (SVP docs are disposable)
            if "examples/" not in test_project and nested_path.exists():
                import shutil

                shutil.rmtree(str(nested_path))

        # Record run in oracle run ledger
        try:
            from ledger_manager import append_oracle_run_entry

            append_oracle_run_entry(
                project_root,
                {
                    "run_number": state.oracle_run_count,
                    "test_project": state.oracle_test_project,
                    "exit_reason": "complete",
                    "oracle_phase": "exit",
                },
            )
        except (ImportError, Exception):
            pass  # Best-effort ledger recording

        # Complete oracle session via Unit 6
        state = complete_oracle_session(state, "exit")
        save_state(project_root, state)
        return _make_action_block(
            action_type="pipeline_complete",
            reminder="Oracle session complete. Stage 6 and Stage 7 available.",
        )

    return _make_action_block(
        action_type="pipeline_held",
        message="Unknown oracle phase.",
        reminder="Oracle session in unknown phase.",
    )


def _route_debug(
    state: PipelineState,
    project_root: Path,
    last_status: str,
    iteration_limit: int,
) -> Dict[str, Any]:
    """Route debug session phases."""
    ds = state.debug_session
    if ds is None:
        return _make_action_block(
            action_type="pipeline_held",
            message="No debug session active.",
            reminder="",
        )

    if not ds.get("authorized"):
        return _make_action_block(
            action_type="human_gate",
            gate_id="gate_6_0_debug_permission",
            reminder="Authorize debug session.",
        )

    phase = ds.get("phase", "triage")

    if phase == "triage":
        if last_status.startswith("TRIAGE_COMPLETE"):
            if last_status == "TRIAGE_COMPLETE: build_env":
                return _make_action_block(
                    action_type="invoke_agent",
                    agent_type="repair_agent",
                    prepare=_agent_prepare_cmd("repair_agent"),
                    reminder="Fast path: build_env triage to repair.",
                )
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_6_2_debug_classification",
                reminder="Classify bug for debug.",
            )
        if last_status == "TRIAGE_NON_REPRODUCIBLE":
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_6_4_non_reproducible",
                reminder="Bug not reproducible.",
            )
        if last_status == "TRIAGE_NEEDS_REFINEMENT":
            triage_count = ds.get("triage_refinement_count", 0)
            if triage_count >= iteration_limit:
                return _make_action_block(
                    action_type="human_gate",
                    gate_id="gate_6_4_non_reproducible",
                    reminder="Triage refinement limit reached.",
                )
            return _make_action_block(
                action_type="invoke_agent",
                agent_type="bug_triage_agent",
                prepare=_agent_prepare_cmd("bug_triage_agent"),
                reminder="Re-invoke triage agent.",
            )
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="bug_triage_agent",
            prepare=_agent_prepare_cmd("bug_triage_agent"),
            reminder="Invoke triage agent.",
        )

    if phase == "regression_test":
        if last_status == "REGRESSION_TEST_COMPLETE":
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_6_1_regression_test",
                reminder="Review regression test.",
            )
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="test_agent",
            prepare=_agent_prepare_cmd("test_agent", unit=state.current_unit),
            reminder="Generate regression test.",
        )

    if phase == "repair":
        if last_status == "REPAIR_COMPLETE":
            new_state = update_debug_phase(state, "reassembly")
            save_state(project_root, new_state)
            return _route_debug(new_state, project_root, "", iteration_limit)
        if last_status == "REPAIR_RECLASSIFY":
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_6_3_repair_exhausted",
                reminder="Repair reclassify.",
            )
        if last_status == "REPAIR_FAILED":
            repair_count = ds.get("repair_retry_count", 0)
            if repair_count >= iteration_limit:
                return _make_action_block(
                    action_type="human_gate",
                    gate_id="gate_6_3_repair_exhausted",
                    reminder="Repair limit reached.",
                )
            return _make_action_block(
                action_type="invoke_agent",
                agent_type="repair_agent",
                prepare=_agent_prepare_cmd("repair_agent"),
                reminder="Re-invoke repair agent.",
            )
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="repair_agent",
            prepare=_agent_prepare_cmd("repair_agent"),
            reminder="Invoke repair agent.",
        )

    if phase == "stage3_rebuild_active":
        return _route_stage_3(state, project_root, last_status, iteration_limit)

    if phase == "stage3_reentry":
        return _make_action_block(
            action_type="run_command",
            command="stage3_reentry",
            reminder="Re-entering Stage 3 for affected unit.",
        )

    if phase == "lessons_learned":
        return _make_action_block(
            action_type="run_command",
            command="lessons_learned",
            reminder="Recording lessons learned.",
        )

    if phase == "reassembly":
        if last_status == "REPO_ASSEMBLY_COMPLETE":
            new_state = update_debug_phase(state, "regression_test")
            save_state(project_root, new_state)
            return _route_debug(new_state, project_root, "", iteration_limit)
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="git_repo_agent",
            prepare=_agent_prepare_cmd("git_repo_agent"),
            reminder="Debug reassembly.",
        )

    if phase == "commit":
        if last_status == "COMMIT APPROVED":
            return _make_action_block(
                action_type="run_command",
                command="debug_commit",
                reminder="Committing debug changes.",
            )
        return _make_action_block(
            action_type="human_gate",
            gate_id="gate_6_5_debug_commit",
            reminder="Review debug commit.",
        )

    return _make_action_block(
        action_type="pipeline_held",
        message="Unknown debug phase.",
        reminder="",
    )


def _route_stage_0(
    state: PipelineState, project_root: Path, last_status: str
) -> Dict[str, Any]:
    """Route Stage 0 sub-stages."""
    sub = state.sub_stage

    # Handle redo profile sub-stages
    if sub in ("redo_profile_delivery", "redo_profile_blueprint"):
        if last_status == "PROFILE_COMPLETE":
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_0_3r_profile_revision",
                reminder="Review redo profile revision.",
            )
        redo_mode = "delivery" if sub == "redo_profile_delivery" else "blueprint"
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="setup_agent",
            prepare=_agent_prepare_cmd("setup_agent"),
            reminder=f"Setup agent in redo-{redo_mode} mode.",
        )

    if sub == "hook_activation" or sub is None:
        return _make_action_block(
            action_type="human_gate",
            gate_id="gate_0_1_hook_activation",
            reminder="Activate hooks.",
        )

    if sub == "project_context":
        if last_status == "PROJECT_CONTEXT_COMPLETE":
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_0_2_context_approval",
                reminder="Review project context.",
            )
        if last_status == "PROJECT_CONTEXT_REJECTED":
            return _make_action_block(
                action_type="pipeline_held",
                message="Project context rejected. Return when requirements are ready.",
                reminder="Context rejected.",
            )
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="setup_agent",
            prepare=_agent_prepare_cmd("setup_agent"),
            reminder="Setup agent for project context.",
        )

    if sub == "project_profile":
        if last_status == "PROFILE_COMPLETE":
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_0_3_profile_approval",
                reminder="Review project profile.",
            )
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="setup_agent",
            prepare=_agent_prepare_cmd("setup_agent"),
            reminder="Setup agent for project profile.",
        )

    return _make_action_block(
        action_type="pipeline_held",
        message=f"Unknown Stage 0 sub-stage: {sub}",
        reminder="",
    )


def _route_stage_1(
    state: PipelineState, project_root: Path, last_status: str
) -> Dict[str, Any]:
    """Route Stage 1 sub-stages."""
    sub = state.sub_stage

    if sub == "targeted_spec_revision":
        if last_status in ("SPEC_DRAFT_COMPLETE", "SPEC_REVISION_COMPLETE"):
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_1_1_spec_draft",
                reminder="Review targeted spec revision.",
            )
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="stakeholder_dialog",
            prepare=_agent_prepare_cmd("stakeholder_dialog"),
            reminder="Targeted spec revision.",
        )

    if sub == "checklist_generation":
        if last_status == "CHECKLISTS_COMPLETE":
            state = advance_stage(state, "2")
            state = advance_sub_stage(state, "blueprint_dialog")
            save_state(project_root, state)
            return route(project_root)
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="checklist_generation",
            prepare=_agent_prepare_cmd("checklist_generation"),
            reminder="Generate checklists.",
        )

    # Main Stage 1 flow
    if last_status in ("SPEC_DRAFT_COMPLETE", "SPEC_REVISION_COMPLETE"):
        return _make_action_block(
            action_type="human_gate",
            gate_id="gate_1_1_spec_draft",
            reminder="Review spec draft.",
        )

    if last_status == "REVIEW_COMPLETE":
        return _make_action_block(
            action_type="human_gate",
            gate_id="gate_1_2_spec_post_review",
            reminder="Review spec post-review.",
        )

    return _make_action_block(
        action_type="invoke_agent",
        agent_type="stakeholder_dialog",
        prepare=_agent_prepare_cmd("stakeholder_dialog"),
        reminder="Start stakeholder dialog.",
    )


def _route_stage_2(
    state: PipelineState,
    project_root: Path,
    last_status: str,
    iteration_limit: int,
) -> Dict[str, Any]:
    """Route Stage 2 sub-stages."""
    sub = state.sub_stage

    if sub == "targeted_spec_revision":
        if last_status in ("SPEC_DRAFT_COMPLETE", "SPEC_REVISION_COMPLETE"):
            state = advance_sub_stage(state, "blueprint_dialog")
            save_state(project_root, state)
            return route(project_root)
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="stakeholder_dialog",
            prepare=_agent_prepare_cmd("stakeholder_dialog"),
            reminder="Targeted spec revision for alignment.",
        )

    if sub == "blueprint_dialog":
        if last_status in ("BLUEPRINT_DRAFT_COMPLETE", "BLUEPRINT_REVISION_COMPLETE"):
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_2_1_blueprint_approval",
                reminder="Review blueprint draft.",
            )
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="blueprint_author",
            prepare=_agent_prepare_cmd("blueprint_author"),
            reminder="Blueprint authoring.",
        )

    if sub == "alignment_check":
        if last_status == "ALIGNMENT_CONFIRMED":
            state = advance_sub_stage(state, "alignment_confirmed")
            save_state(project_root, state)
            return route(project_root)
        if last_status and last_status.startswith("ALIGNMENT_FAILED"):
            if state.alignment_iterations >= iteration_limit:
                return _make_action_block(
                    action_type="human_gate",
                    gate_id="gate_2_3_alignment_exhausted",
                    reminder="Alignment iterations exhausted.",
                )
            return route(project_root)
        if last_status == "REVIEW_COMPLETE":
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_2_2_blueprint_post_review",
                reminder="Review blueprint post-review.",
            )
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="blueprint_checker",
            prepare=_agent_prepare_cmd("blueprint_checker"),
            reminder="Alignment check.",
        )

    if sub == "alignment_confirmed":
        if last_status == "REVIEW_COMPLETE":
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_2_2_blueprint_post_review",
                reminder="Review blueprint after alignment confirmed.",
            )
        return _make_action_block(
            action_type="human_gate",
            gate_id="gate_2_2_blueprint_post_review",
            reminder="Blueprint alignment confirmed. Human review.",
        )

    return _make_action_block(
        action_type="invoke_agent",
        agent_type="blueprint_author",
        prepare=_agent_prepare_cmd("blueprint_author"),
        reminder="Blueprint authoring.",
    )


def _route_pre_stage_3(
    state: PipelineState, project_root: Path, last_status: str
) -> Dict[str, Any]:
    """Route pre-Stage 3."""
    state = advance_stage(state, "3")
    if state.total_units > 0 and state.current_unit is None:
        state.current_unit = 1
        state.sub_stage = "stub_generation"
    save_state(project_root, state)
    return route(project_root)


def _route_stage_3(
    state: PipelineState,
    project_root: Path,
    last_status: str,
    iteration_limit: int,
) -> Dict[str, Any]:
    """Route Stage 3 (per-unit build loop)."""
    sub = state.sub_stage

    # Check if all units done
    if state.current_unit is None and sub is None:
        validation_error = _validate_stage3_completion(state, project_root)
        if validation_error:
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_3_completion_failure",
                message=validation_error,
                reminder="Stage 3 completion validation failed.",
            )
        state = advance_stage(state, "4")
        save_state(project_root, state)
        return route(project_root)

    if sub is None and state.current_unit is not None:
        state.sub_stage = "stub_generation"
        save_state(project_root, state)
        return route(project_root)

    if sub == "stub_generation":
        return _make_action_block(
            action_type="run_command",
            command="stub_generation",
            post="python scripts/update_state.py --command stub_generation --project-root .",
            reminder=f"Generate stub for unit {state.current_unit}.",
        )

    if sub == "test_generation":
        if last_status == "TEST_GENERATION_COMPLETE":
            state = advance_sub_stage(state, "quality_gate_a")
            save_state(project_root, state)
            return route(project_root)
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="test_agent",
            prepare=_agent_prepare_cmd("test_agent", unit=state.current_unit),
            reminder=f"Generate tests for unit {state.current_unit}.",
        )

    if sub in ("quality_gate_a", "quality_gate_a_retry"):
        return _make_action_block(
            action_type="run_command",
            command="quality_gate",
            post="python scripts/update_state.py --command quality_gate --project-root .",
            reminder=f"Run quality gate A for unit {state.current_unit}.",
        )

    if sub == "red_run":
        return _make_action_block(
            action_type="run_command",
            command="test_execution",
            post="python scripts/update_state.py --command test_execution --project-root .",
            reminder=f"Red run for unit {state.current_unit}.",
        )

    if sub == "implementation":
        if last_status == "IMPLEMENTATION_COMPLETE":
            state = advance_sub_stage(state, "quality_gate_b")
            save_state(project_root, state)
            return route(project_root)
        fl = state.fix_ladder_position
        if fl == "diagnostic":
            if last_status == "DIAGNOSIS_COMPLETE":
                return _make_action_block(
                    action_type="human_gate",
                    gate_id="gate_3_2_diagnostic_decision",
                    reminder=f"Diagnostic decision for unit {state.current_unit}.",
                )
            return _make_action_block(
                action_type="invoke_agent",
                agent_type="diagnostic_agent",
                prepare=_agent_prepare_cmd("diagnostic_agent", unit=state.current_unit),
                reminder=f"Diagnose failures for unit {state.current_unit}.",
            )
        if fl == "exhausted":
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_3_2_diagnostic_decision",
                reminder=f"Fix ladder exhausted for unit {state.current_unit}.",
            )
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="implementation_agent",
            prepare=_agent_prepare_cmd("implementation_agent", unit=state.current_unit),
            reminder=f"Implement unit {state.current_unit}.",
        )

    if sub in ("quality_gate_b", "quality_gate_b_retry"):
        return _make_action_block(
            action_type="run_command",
            command="quality_gate",
            post="python scripts/update_state.py --command quality_gate --project-root .",
            reminder=f"Run quality gate B for unit {state.current_unit}.",
        )

    if sub == "green_run":
        return _make_action_block(
            action_type="run_command",
            command="test_execution",
            post="python scripts/update_state.py --command test_execution --project-root .",
            reminder=f"Green run for unit {state.current_unit}.",
        )

    if sub == "coverage_review":
        if last_status in (
            "COVERAGE_COMPLETE: no gaps",
            "COVERAGE_COMPLETE: tests added",
        ):
            state = advance_sub_stage(state, "unit_completion")
            save_state(project_root, state)
            return route(project_root)
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="coverage_review_agent",
            prepare=_agent_prepare_cmd("coverage_review_agent", unit=state.current_unit),
            reminder=f"Review coverage for unit {state.current_unit}.",
        )

    if sub == "unit_completion":
        return _make_action_block(
            action_type="run_command",
            command="unit_completion",
            post="python scripts/update_state.py --command unit_completion --project-root .",
            reminder=f"Complete unit {state.current_unit}.",
        )

    if sub == "pass_transition":
        if state.pass_ == 1:
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_pass_transition_post_pass1",
                reminder="Pass 1 complete. Choose next action.",
            )
        if state.pass_ == 2:
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_pass_transition_post_pass2",
                reminder="Pass 2 complete. Choose next action.",
            )
        return _make_action_block(
            action_type="pipeline_complete",
            reminder="Pass transition without pass number.",
        )

    return _make_action_block(
        action_type="pipeline_held",
        message=f"Unknown Stage 3 sub-stage: {sub}",
        reminder="",
    )


def _route_stage_4(
    state: PipelineState,
    project_root: Path,
    last_status: str,
    iteration_limit: int,
) -> Dict[str, Any]:
    """Route Stage 4 (integration tests)."""
    sub = state.sub_stage

    if sub == "regression_adaptation":
        if last_status == "ADAPTATION_COMPLETE":
            state = advance_stage(state, "5")
            save_state(project_root, state)
            return route(project_root)
        if last_status == "ADAPTATION_NEEDS_REVIEW":
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_4_3_adaptation_review",
                reminder="Review adaptation.",
            )
        return _make_action_block(
            action_type="invoke_agent",
            agent_type="regression_adaptation",
            prepare=_agent_prepare_cmd("regression_adaptation"),
            reminder="Run regression adaptation.",
        )

    if sub == "gate_4_1":
        return _make_action_block(
            action_type="human_gate",
            gate_id="gate_4_1_integration_failure",
            reminder="Integration test failure.",
        )

    if sub == "gate_4_1a":
        return _make_action_block(
            action_type="human_gate",
            gate_id="gate_4_1a",
            reminder="Human fix or escalate.",
        )

    if sub == "gate_4_2":
        return _make_action_block(
            action_type="human_gate",
            gate_id="gate_4_2_assembly_exhausted",
            reminder="Assembly retries exhausted.",
        )

    if last_status == "INTEGRATION_TESTS_COMPLETE":
        return _make_action_block(
            action_type="run_command",
            command="test_execution",
            post="python scripts/update_state.py --command test_execution --project-root .",
            reminder="Run integration tests.",
        )

    return _make_action_block(
        action_type="invoke_agent",
        agent_type="integration_test_author",
        prepare=_agent_prepare_cmd("integration_test_author"),
        reminder="Author integration tests.",
    )


def _route_stage_5(
    state: PipelineState,
    project_root: Path,
    last_status: str,
    iteration_limit: int,
) -> Dict[str, Any]:
    """Route Stage 5 (repository assembly)."""
    sub = state.sub_stage

    if sub == "repo_complete":
        pass_val = getattr(state, 'pass_', None)
        if pass_val in (1, 2):
            new = advance_sub_stage(state, "pass_transition")
            save_state(project_root, new)
            return route(project_root)
        return _make_action_block(
            action_type="pipeline_complete",
            reminder="Repository assembly complete.",
        )

    if sub == "compliance_scan":
        return _make_action_block(
            action_type="run_command",
            command="compliance_scan",
            post="python scripts/update_state.py --command compliance_scan --project-root .",
            reminder="Run compliance scan.",
        )

    if sub == "repo_test":
        return _make_action_block(
            action_type="human_gate",
            gate_id="gate_5_1_repo_test",
            reminder="Review repository test results.",
        )

    if sub == "gate_5_2":
        return _make_action_block(
            action_type="human_gate",
            gate_id="gate_5_2_assembly_exhausted",
            reminder="Assembly retries exhausted.",
        )

    if sub == "gate_5_3":
        return _make_action_block(
            action_type="human_gate",
            gate_id="gate_5_3_unused_functions",
            reminder="Unused functions detected.",
        )

    # Bug S3-54: pass_transition must be handled in Stage 5, not only Stage 3
    if sub == "pass_transition":
        if state.pass_ == 1:
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_pass_transition_post_pass1",
                reminder="Pass 1 complete. Choose next action.",
            )
        if state.pass_ == 2:
            # Bug S3-55: sync Pass 1 artifacts before presenting gate
            from sync_debug_docs import sync_pass1_artifacts
            sync_result = sync_pass1_artifacts(project_root)
            reminder = "Pass 2 complete. Choose next action."
            if sync_result["synced_files"] or sync_result["merged_files"]:
                n = len(sync_result["synced_files"]) + len(sync_result["merged_files"])
                reminder += f" (Synced {n} artifacts from Pass 1.)"
            return _make_action_block(
                action_type="human_gate",
                gate_id="gate_pass_transition_post_pass2",
                reminder=reminder,
            )
        return _make_action_block(
            action_type="pipeline_complete",
            reminder="Pass transition without pass number.",
        )

    if last_status == "REPO_ASSEMBLY_COMPLETE":
        return _make_action_block(
            action_type="human_gate",
            gate_id="gate_5_1_repo_test",
            reminder="Review repository test results.",
        )

    return _make_action_block(
        action_type="invoke_agent",
        agent_type="git_repo_agent",
        prepare=_agent_prepare_cmd("git_repo_agent"),
        reminder="Assemble repository.",
    )


# ---------------------------------------------------------------------------
# Dispatch functions
# ---------------------------------------------------------------------------


def dispatch_gate_response(
    state: Any,
    gate_id: str,
    response: str,
    project_root: Path,
) -> Any:
    """Dispatch a gate response to the appropriate state transition.

    For ALL 31 gates and all response options, produces specific state transitions.
    Uses Unit 6 transition functions (Bug S3-8 fix) instead of direct field assignment.
    No bare return state for main pipeline gates.
    """
    project_root = Path(project_root)
    config = _load_config_safe(project_root)
    iteration_limit = config.get("iteration_limit", 3)

    if gate_id not in GATE_VOCABULARY:
        raise ValueError(f"Unknown gate_id: {gate_id}")
    if response not in GATE_VOCABULARY[gate_id]:
        raise ValueError(
            f"Invalid response '{response}' for gate '{gate_id}'. "
            f"Valid: {GATE_VOCABULARY[gate_id]}"
        )

    # Gate 0.1: Hook activation
    if gate_id == "gate_0_1_hook_activation":
        if response == "HOOKS ACTIVATED":
            new = advance_sub_stage(state, "project_context")
        else:  # HOOKS FAILED
            new = _copy(state)
            new.sub_stage = "hook_activation"
        return new

    # Gate 0.2: Context approval
    if gate_id == "gate_0_2_context_approval":
        if response == "CONTEXT APPROVED":
            new = advance_sub_stage(state, "project_profile")
        elif response == "CONTEXT REJECTED":
            _clear_last_status(project_root)
            new = advance_sub_stage(state, "project_context")
        else:  # CONTEXT NOT READY
            _clear_last_status(project_root)
            new = advance_sub_stage(state, "project_context")
        return new

    # Gate 0.3: Profile approval
    if gate_id == "gate_0_3_profile_approval":
        if response == "PROFILE APPROVED":
            new = advance_stage(state, "1")
        else:  # PROFILE REJECTED
            _clear_last_status(project_root)
            new = advance_sub_stage(state, "project_profile")
        return new

    # Gate 0.3r: Redo profile revision
    if gate_id == "gate_0_3r_profile_revision":
        if response == "PROFILE APPROVED":
            if hasattr(state, "redo_triggered_from") and state.redo_triggered_from:
                new = complete_redo_profile_revision(state)
            else:
                new = _copy(state)
        else:  # PROFILE REJECTED
            _clear_last_status(project_root)
            new = _copy(state)
            # Stay in same sub_stage for re-invoke
        return new

    # Gate 1.1: Spec draft
    if gate_id == "gate_1_1_spec_draft":
        if response == "APPROVE":
            new = advance_sub_stage(state, "checklist_generation")
        elif response == "REVISE":
            _clear_last_status(project_root)
            new = _copy(state)
            # Re-invoke stakeholder dialog in revision mode (stay in stage 1)
        else:  # FRESH REVIEW
            _clear_last_status(project_root)
            new = advance_sub_stage(state, "spec_review")
        return new

    # Gate 1.2: Spec post-review
    if gate_id == "gate_1_2_spec_post_review":
        if response == "APPROVE":
            new = advance_sub_stage(state, "checklist_generation")
        elif response == "REVISE":
            _clear_last_status(project_root)
            new = _copy(state)
            # version_document for spec
        else:  # FRESH REVIEW
            _clear_last_status(project_root)
            new = advance_sub_stage(state, "spec_review")
        return new

    # Gate 2.1: Blueprint approval
    if gate_id == "gate_2_1_blueprint_approval":
        if response == "APPROVE":
            new = advance_sub_stage(state, "alignment_check")
        elif response == "REVISE":
            _clear_last_status(project_root)
            new = advance_sub_stage(state, "blueprint_dialog")
        else:  # FRESH REVIEW
            _clear_last_status(project_root)
            new = advance_sub_stage(state, "alignment_check")
        return new

    # Gate 2.2: Blueprint post-review
    if gate_id == "gate_2_2_blueprint_post_review":
        if response == "APPROVE":
            new = advance_stage(state, "pre_stage_3")
        elif response == "REVISE":
            _clear_last_status(project_root)
            new = advance_sub_stage(state, "blueprint_dialog")
        else:  # FRESH REVIEW
            _clear_last_status(project_root)
            new = advance_sub_stage(state, "alignment_check")
        return new

    # Gate 2.3: Alignment exhausted
    if gate_id == "gate_2_3_alignment_exhausted":
        if response == "REVISE SPEC":
            new = advance_sub_stage(state, "targeted_spec_revision")
            new.alignment_iterations = 0
        elif response == "RESTART SPEC":
            new = advance_stage(state, "1")
        else:  # RETRY BLUEPRINT
            _clear_last_status(project_root)
            new = advance_sub_stage(state, "blueprint_dialog")
        return new

    # Gate 3.1: Test validation (autonomous)
    if gate_id == "gate_3_1_test_validation":
        new = _copy(state)
        if response == "TEST CORRECT":
            pass  # Continue normal flow
        else:  # TEST WRONG
            new.sub_stage = "test_generation"
        return new

    # Gate 3.2: Diagnostic decision
    if gate_id == "gate_3_2_diagnostic_decision":
        if response == "FIX IMPLEMENTATION":
            new = advance_sub_stage(state, "implementation")
        elif response == "FIX BLUEPRINT":
            new = restart_from_stage(state, "2")
        else:  # FIX SPEC
            new = advance_stage(state, "1")
        return new

    # Gate 3 completion failure
    if gate_id == "gate_3_completion_failure":
        if response == "INVESTIGATE":
            new = enter_debug_session(state, 0)
        elif response == "FORCE ADVANCE":
            new = advance_stage(state, "4")
        else:  # RESTART STAGE 3
            new = restart_from_stage(state, "3")
        return new

    # Gate 4.1: Integration failure
    if gate_id == "gate_4_1_integration_failure":
        if response == "ASSEMBLY FIX":
            new = _copy(state)
            # Re-invoke integration test author with fix context
        elif response == "FIX BLUEPRINT":
            new = restart_from_stage(state, "2")
        else:  # FIX SPEC
            new = restart_from_stage(state, "1")
        return new

    # Gate 4.1a
    if gate_id == "gate_4_1a":
        if response == "HUMAN FIX":
            new = _copy(state)
            new.sub_stage = None
            new.red_run_retries = 0
        else:  # ESCALATE
            new = advance_sub_stage(state, "gate_4_2")
        return new

    # Gate 4.2: Assembly exhausted
    if gate_id == "gate_4_2_assembly_exhausted":
        if response == "FIX BLUEPRINT":
            new = restart_from_stage(state, "2")
        else:  # FIX SPEC
            new = restart_from_stage(state, "1")
        return new

    # Gate 4.3: Adaptation review
    if gate_id == "gate_4_3_adaptation_review":
        if response == "ACCEPT ADAPTATIONS":
            new = advance_stage(state, "5")
        elif response == "MODIFY TEST":
            _clear_last_status(project_root)
            new = advance_sub_stage(state, "regression_adaptation")
        else:  # REMOVE TEST
            new = advance_stage(state, "5")
        return new

    # Gate 5.1: Repo test
    if gate_id == "gate_5_1_repo_test":
        if response == "TESTS PASSED":
            new = advance_sub_stage(state, "compliance_scan")
        else:  # TESTS FAILED
            new = _copy(state)
            new.sub_stage = None
        return new

    # Gate 5.2: Assembly exhausted
    if gate_id == "gate_5_2_assembly_exhausted":
        if response == "RETRY ASSEMBLY":
            _clear_last_status(project_root)
            new = _copy(state)
            # Re-invoke git repo agent
        elif response == "FIX BLUEPRINT":
            new = restart_from_stage(state, "2")
        else:  # FIX SPEC
            new = restart_from_stage(state, "1")
        return new

    # Gate 5.3: Unused functions
    if gate_id == "gate_5_3_unused_functions":
        if response == "FIX SPEC":
            new = advance_stage(state, "1")
        else:  # OVERRIDE CONTINUE
            new = advance_sub_stage(state, "repo_complete")
        return new

    # Gate 6.0: Debug permission
    if gate_id == "gate_6_0_debug_permission":
        if response == "AUTHORIZE DEBUG":
            if (
                state.debug_session is not None
                and state.debug_session.get("authorized") is False
            ):
                new = authorize_debug_session(state)
            else:
                new = _copy(state)
        else:  # ABANDON DEBUG
            if state.debug_session is not None:
                new = abandon_debug_session(state)
            else:
                new = _copy(state)
        return new

    # Gate 6.1: Regression test
    if gate_id == "gate_6_1_regression_test":
        if response == "TEST CORRECT":
            if state.debug_session is not None:
                new = update_debug_phase(state, "lessons_learned")
            else:
                new = _copy(state)
        else:  # TEST WRONG
            _clear_last_status(project_root)
            new = _copy(state)
            # Re-invoke test agent in regression mode
        return new

    # Gate 6.1a: Divergence warning
    if gate_id == "gate_6_1a_divergence_warning":
        if response == "PROCEED":
            new = _copy(state)
        elif response == "FIX DIVERGENCE":
            _clear_last_status(project_root)
            new = _copy(state)
            # Re-invoke git repo agent for sync
        else:  # ABANDON DEBUG
            if state.debug_session is not None:
                new = abandon_debug_session(state)
            else:
                new = _copy(state)
        return new

    # Gate 6.2: Debug classification
    if gate_id == "gate_6_2_debug_classification":
        if response == "FIX UNIT":
            if state.debug_session is not None:
                affected = state.debug_session.get("affected_units", [])
                new = set_debug_classification(state, "single_unit", affected)
                new = update_debug_phase(new, "stage3_reentry")
                if affected:
                    new = rollback_to_unit(new, affected[0])
            else:
                new = _copy(state)
        elif response == "FIX BLUEPRINT":
            new = restart_from_stage(state, "2")
        elif response == "FIX SPEC":
            new = restart_from_stage(state, "1")
        else:  # FIX IN PLACE
            if state.debug_session is not None:
                new = update_debug_phase(state, "repair")
            else:
                new = _copy(state)
        return new

    # Gate 6.3: Repair exhausted
    if gate_id == "gate_6_3_repair_exhausted":
        new = _copy(state)
        if response == "RETRY REPAIR":
            if hasattr(new, "debug_session") and new.debug_session:
                new.debug_session = dict(new.debug_session)
                new.debug_session["repair_retry_count"] = 0
        elif response == "RECLASSIFY BUG":
            if state.debug_session is not None:
                triage_count = state.debug_session.get("triage_refinement_count", 0)
                new = _copy(state)
                new.debug_session = dict(new.debug_session)
                new.debug_session["triage_refinement_count"] = triage_count + 1
                if triage_count < iteration_limit:
                    _clear_last_status(project_root)
                    new.debug_session["phase"] = "triage"
        else:  # ABANDON DEBUG
            if state.debug_session is not None:
                new = abandon_debug_session(state)
        return new

    # Gate 6.4: Non-reproducible
    if gate_id == "gate_6_4_non_reproducible":
        if response == "RETRY TRIAGE":
            if state.debug_session is not None:
                new = _copy(state)
                new.debug_session = dict(new.debug_session)
                new.debug_session["triage_refinement_count"] = (
                    new.debug_session.get("triage_refinement_count", 0) + 1
                )
                new.debug_session["phase"] = "triage"
            else:
                new = _copy(state)
        else:  # ABANDON DEBUG
            if state.debug_session is not None:
                new = abandon_debug_session(state)
            else:
                new = _copy(state)
        return new

    # Gate 6.5: Debug commit
    if gate_id == "gate_6_5_debug_commit":
        if response == "COMMIT APPROVED":
            if state.debug_session is not None and state.debug_session.get(
                "authorized"
            ):
                new = complete_debug_session(state)
            else:
                new = _copy(state)
                if hasattr(new, "debug_session") and new.debug_session:
                    if not hasattr(new, "debug_history"):
                        new.debug_history = []
                    new.debug_history = list(new.debug_history) + [new.debug_session]
                    new.debug_session = None
        else:  # COMMIT REJECTED
            new = _copy(state)
        return new

    # Gate hint conflict
    if gate_id == "gate_hint_conflict":
        new = _copy(state)
        if response == "BLUEPRINT CORRECT":
            pass  # Discard hint, continue
        else:  # HINT CORRECT
            pass  # Version appropriate document, restart
        return new

    # Gate 7a: Trajectory review
    if gate_id == "gate_7_a_trajectory_review":
        if response == "APPROVE TRAJECTORY":
            new = _copy(state)
            new.oracle_phase = "green_run"
        elif response == "MODIFY TRAJECTORY":
            new = _copy(state)
            new.oracle_phase = "dry_run"
            new.oracle_modification_count = getattr(state, "oracle_modification_count", 0) + 1
        else:  # ABORT
            new = abandon_oracle_session(state)
            try:
                from ledger_manager import append_oracle_run_entry

                append_oracle_run_entry(
                    project_root,
                    {
                        "run_number": state.oracle_run_count,
                        "test_project": state.oracle_test_project,
                        "exit_reason": "abort",
                        "oracle_phase": state.oracle_phase,
                    },
                )
            except (ImportError, Exception):
                pass
        return new

    # Gate 7b: Fix plan review
    if gate_id == "gate_7_b_fix_plan_review":
        if response == "APPROVE FIX":
            # Enter debug session — oracle "pauses" while /svp:bug runs
            new = enter_debug_session(state, state.oracle_run_count or 1)
            # oracle_session_active stays True — after debug completes,
            # routing returns to _route_oracle
        else:  # ABORT
            new = abandon_oracle_session(state)
            try:
                from ledger_manager import append_oracle_run_entry

                append_oracle_run_entry(
                    project_root,
                    {
                        "run_number": state.oracle_run_count,
                        "test_project": state.oracle_test_project,
                        "exit_reason": "abort",
                        "oracle_phase": state.oracle_phase,
                    },
                )
            except (ImportError, Exception):
                pass
        return new

    # Gate pass transition post pass1
    if gate_id == "gate_pass_transition_post_pass1":
        if response == "PROCEED TO PASS 2":
            deferred = getattr(state, "deferred_broken_units", [])
            if deferred:
                raise ValueError(
                    f"Cannot proceed to Pass 2 with deferred broken units: {deferred}"
                )
            nested_path = str(project_root / ".svp" / "pass2_session")
            new = enter_pass_2(state, nested_path)
        else:  # FIX BUGS
            new = enter_debug_session(state, 0)
        return new

    # Gate pass transition post pass2
    if gate_id == "gate_pass_transition_post_pass2":
        if response == "FIX BUGS":
            new = enter_debug_session(state, 0)
        else:  # RUN ORACLE
            new = enter_oracle_session(state, "")
        return new

    # Fallback
    raise ValueError(f"Unhandled gate response: gate={gate_id}, response={response}")


def dispatch_agent_status(
    state: Any,
    agent_type: str,
    status_line: str,
    project_root: Path,
) -> Any:
    """Dispatch an agent status line to the appropriate state transition.

    For ALL agent types and status lines, produces specific state transitions.
    Uses Unit 6 transition functions (Bug S3-8 fix) instead of direct field assignment.
    No bare return state for main pipeline agents.
    """
    project_root = Path(project_root)
    config = _load_config_safe(project_root)
    iteration_limit = config.get("iteration_limit", 3)

    # setup_agent
    if agent_type == "setup_agent":
        if status_line in (
            "PROJECT_CONTEXT_COMPLETE",
            "PROJECT_CONTEXT_REJECTED",
            "PROFILE_COMPLETE",
        ):
            return _copy(state)  # Two-branch in route
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # stakeholder_dialog
    if agent_type == "stakeholder_dialog":
        if status_line in ("SPEC_DRAFT_COMPLETE", "SPEC_REVISION_COMPLETE"):
            return _copy(state)  # Two-branch in route
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # stakeholder_reviewer
    if agent_type == "stakeholder_reviewer":
        if status_line == "REVIEW_COMPLETE":
            return _copy(state)
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # blueprint_author
    if agent_type == "blueprint_author":
        if status_line in ("BLUEPRINT_DRAFT_COMPLETE", "BLUEPRINT_REVISION_COMPLETE"):
            return _copy(state)
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # blueprint_reviewer
    if agent_type == "blueprint_reviewer":
        if status_line == "REVIEW_COMPLETE":
            return _copy(state)
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # blueprint_checker
    if agent_type == "blueprint_checker":
        if status_line == "ALIGNMENT_CONFIRMED":
            new = advance_sub_stage(state, "alignment_confirmed")
            return new
        if status_line == "ALIGNMENT_FAILED: blueprint":
            new = increment_alignment_iteration(state)
            if new.alignment_iterations >= iteration_limit:
                return new  # Route will present gate_2_3
            new = advance_sub_stage(new, "blueprint_dialog")
            return new
        if status_line == "ALIGNMENT_FAILED: spec":
            new = increment_alignment_iteration(state)
            if new.alignment_iterations >= iteration_limit:
                return new  # Route will present gate_2_3
            new = advance_sub_stage(new, "targeted_spec_revision")
            return new
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # checklist_generation
    if agent_type == "checklist_generation":
        if status_line == "CHECKLISTS_COMPLETE":
            return _copy(state)
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # test_agent
    if agent_type == "test_agent":
        if status_line in ("TEST_GENERATION_COMPLETE", "REGRESSION_TEST_COMPLETE"):
            return _copy(state)
        if status_line.startswith("HINT_BLUEPRINT_CONFLICT"):
            return _copy(state)
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # implementation_agent
    if agent_type == "implementation_agent":
        if status_line == "IMPLEMENTATION_COMPLETE":
            return _copy(state)
        if status_line.startswith("HINT_BLUEPRINT_CONFLICT"):
            return _copy(state)
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # coverage_review_agent
    if agent_type == "coverage_review_agent":
        if status_line in (
            "COVERAGE_COMPLETE: no gaps",
            "COVERAGE_COMPLETE: tests added",
        ):
            return _copy(state)
        if status_line.startswith("HINT_BLUEPRINT_CONFLICT"):
            return _copy(state)
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # diagnostic_agent
    if agent_type == "diagnostic_agent":
        if status_line.startswith("DIAGNOSIS_COMPLETE"):
            return _copy(state)
        if status_line.startswith("HINT_BLUEPRINT_CONFLICT"):
            return _copy(state)
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # integration_test_author
    if agent_type == "integration_test_author":
        if status_line == "INTEGRATION_TESTS_COMPLETE":
            return _copy(state)
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # regression_adaptation
    if agent_type == "regression_adaptation":
        if status_line in ("ADAPTATION_COMPLETE", "ADAPTATION_NEEDS_REVIEW"):
            return _copy(state)
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # git_repo_agent
    if agent_type == "git_repo_agent":
        if status_line == "REPO_ASSEMBLY_COMPLETE":
            return _copy(state)
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # bug_triage_agent
    if agent_type == "bug_triage_agent":
        if status_line in (
            "TRIAGE_COMPLETE: single_unit",
            "TRIAGE_COMPLETE: cross_unit",
        ):
            return _copy(state)  # Two-branch routes to gate_6_2
        if status_line == "TRIAGE_COMPLETE: build_env":
            if state.debug_session is not None:
                new = update_debug_phase(state, "repair")
            else:
                new = _copy(state)
            return new
        if status_line == "TRIAGE_NON_REPRODUCIBLE":
            return _copy(state)
        if status_line == "TRIAGE_NEEDS_REFINEMENT":
            new = _copy(state)
            if hasattr(new, "debug_session") and new.debug_session:
                new.debug_session = dict(new.debug_session)
                new.debug_session["triage_refinement_count"] = (
                    new.debug_session.get("triage_refinement_count", 0) + 1
                )
            return new
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # repair_agent
    if agent_type == "repair_agent":
        if status_line == "REPAIR_COMPLETE":
            return _copy(state)
        if status_line == "REPAIR_RECLASSIFY":
            return _copy(state)
        if status_line == "REPAIR_FAILED":
            new = _copy(state)
            if hasattr(new, "debug_session") and new.debug_session:
                new.debug_session = dict(new.debug_session)
                new.debug_session["repair_retry_count"] = (
                    new.debug_session.get("repair_retry_count", 0) + 1
                )
            return new
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # oracle_agent
    if agent_type == "oracle_agent":
        if status_line == "ORACLE_DRY_RUN_COMPLETE":
            return _copy(state)
        if status_line == "ORACLE_ALL_CLEAR":
            new = _copy(state)
            new.oracle_phase = "exit"
            return new
        if status_line == "ORACLE_FIX_APPLIED":
            new = _copy(state)
            new.oracle_phase = "gate_b"
            return new
        if status_line == "ORACLE_HUMAN_ABORT":
            new = abandon_oracle_session(state)
            try:
                from ledger_manager import append_oracle_run_entry

                append_oracle_run_entry(
                    project_root,
                    {
                        "run_number": state.oracle_run_count,
                        "test_project": state.oracle_test_project,
                        "exit_reason": "abort",
                        "oracle_phase": state.oracle_phase,
                    },
                )
            except (ImportError, Exception):
                pass
            return new
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # help_agent
    if agent_type == "help_agent":
        if status_line in (
            "HELP_SESSION_COMPLETE: no hint",
            "HELP_SESSION_COMPLETE: hint forwarded",
        ):
            return _copy(state)
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # hint_agent
    if agent_type == "hint_agent":
        if status_line == "HINT_ANALYSIS_COMPLETE":
            return _copy(state)
        if status_line.startswith("HINT_BLUEPRINT_CONFLICT"):
            return _copy(state)
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # reference_indexing
    if agent_type == "reference_indexing":
        if status_line == "INDEXING_COMPLETE":
            return _copy(state)
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    # redo_agent
    if agent_type == "redo_agent":
        if status_line == "REDO_CLASSIFIED: spec":
            new = advance_sub_stage(state, "targeted_spec_revision")
            return new
        if status_line == "REDO_CLASSIFIED: blueprint":
            new = restart_from_stage(state, "2")
            return new
        if status_line == "REDO_CLASSIFIED: gate":
            # rollback_to_unit for affected unit
            new = _copy(state)
            return new
        if status_line == "REDO_CLASSIFIED: profile_delivery":
            new = enter_redo_profile_revision(state, "delivery")
            return new
        if status_line == "REDO_CLASSIFIED: profile_blueprint":
            new = enter_redo_profile_revision(state, "blueprint")
            return new
        raise ValueError(f"Unknown status for {agent_type}: {status_line}")

    raise ValueError(f"Unknown agent_type: {agent_type}")


def dispatch_command_status(
    state: Any,
    command_type: str,
    status_line: str,
    sub_stage: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> Any:
    """Dispatch a command status to the appropriate state transition.

    Handles Stage 3 (red_run, green_run, quality gates, unit_completion)
    and Stage 4 (integration tests).
    Uses Unit 6 transition functions (Bug S3-8 fix).
    No bare return state for any entry.
    """
    effective_sub_stage = (
        sub_stage if sub_stage is not None else getattr(state, "sub_stage", None)
    )

    # stub_generation
    if command_type == "stub_generation":
        if status_line == "COMMAND_SUCCEEDED":
            new = advance_sub_stage(state, "test_generation")
        elif status_line == "COMMAND_FAILED":
            new = _copy(state)
            # Present error to human -- state still changes (new copy)
        else:
            raise ValueError(f"Unknown status for {command_type}: {status_line}")
        return new

    # test_execution
    if command_type == "test_execution":
        stage = getattr(state, "stage", "3")

        # Stage 4 integration tests
        if stage == "4":
            if status_line == "TESTS_PASSED":
                new = advance_sub_stage(state, "regression_adaptation")
                return new
            if status_line == "TESTS_FAILED":
                new = increment_red_run_retries(state)
                if new.red_run_retries >= 3:
                    new = advance_sub_stage(new, "gate_4_2")
                else:
                    new = advance_sub_stage(new, "gate_4_1")
                return new
            if status_line == "TESTS_ERROR":
                new = increment_red_run_retries(state)
                if new.red_run_retries >= 3:
                    new = advance_sub_stage(new, "gate_4_2")
                else:
                    new.sub_stage = None
                return new
            raise ValueError(
                f"Unknown status for test_execution at Stage 4: {status_line}"
            )

        # Stage 3 red_run
        if effective_sub_stage == "red_run":
            if status_line == "TESTS_FAILED":
                new = advance_sub_stage(state, "implementation")
            elif status_line in ("TESTS_PASSED", "TESTS_ERROR"):
                new = increment_red_run_retries(state)
                limit = 3
                if new.red_run_retries >= limit:
                    new = advance_sub_stage(new, "implementation")
                else:
                    new = advance_sub_stage(new, "test_generation")
            else:
                raise ValueError(
                    f"Unknown status for test_execution at red_run: {status_line}"
                )
            return new

        # Stage 3 green_run
        if effective_sub_stage == "green_run":
            if status_line == "TESTS_PASSED":
                new = advance_sub_stage(state, "coverage_review")
            elif status_line in ("TESTS_FAILED", "TESTS_ERROR"):
                new = advance_fix_ladder(state)
            else:
                raise ValueError(
                    f"Unknown status for test_execution at green_run: {status_line}"
                )
            return new

        raise ValueError(f"Unknown sub_stage for test_execution: {effective_sub_stage}")

    # quality_gate
    if command_type == "quality_gate":
        if effective_sub_stage == "quality_gate_a":
            if status_line == "COMMAND_SUCCEEDED":
                new = advance_sub_stage(state, "red_run")
            elif status_line == "COMMAND_FAILED":
                new = advance_sub_stage(state, "quality_gate_a_retry")
            else:
                raise ValueError(
                    f"Unknown status for quality_gate at quality_gate_a: {status_line}"
                )
            return new

        if effective_sub_stage == "quality_gate_b":
            if status_line == "COMMAND_SUCCEEDED":
                new = advance_sub_stage(state, "green_run")
            elif status_line == "COMMAND_FAILED":
                new = advance_sub_stage(state, "quality_gate_b_retry")
            else:
                raise ValueError(
                    f"Unknown status for quality_gate at quality_gate_b: {status_line}"
                )
            return new

        if effective_sub_stage == "quality_gate_a_retry":
            if status_line == "COMMAND_SUCCEEDED":
                new = advance_sub_stage(state, "red_run")
            elif status_line == "COMMAND_FAILED":
                new = advance_fix_ladder(state)
            else:
                raise ValueError(
                    f"Unknown status for quality_gate at quality_gate_a_retry: {status_line}"
                )
            return new

        if effective_sub_stage == "quality_gate_b_retry":
            if status_line == "COMMAND_SUCCEEDED":
                new = advance_sub_stage(state, "green_run")
            elif status_line == "COMMAND_FAILED":
                new = advance_fix_ladder(state)
            else:
                raise ValueError(
                    f"Unknown status for quality_gate at quality_gate_b_retry: {status_line}"
                )
            return new

        raise ValueError(f"Unknown sub_stage for quality_gate: {effective_sub_stage}")

    # unit_completion
    if command_type == "unit_completion":
        if status_line == "COMMAND_SUCCEEDED":
            new = complete_unit(state)
        elif status_line == "COMMAND_FAILED":
            new = _copy(state)
        else:
            raise ValueError(f"Unknown status for {command_type}: {status_line}")
        return new

    # compliance_scan
    if command_type == "compliance_scan":
        if "SUCCEEDED" in status_line:
            new = advance_sub_stage(state, "repo_complete")
        elif "FAILED" in status_line:
            new = _copy(state)
            new.sub_stage = None
        else:
            raise ValueError(f"Unknown status for {command_type}: {status_line}")
        return new

    # structural_check
    if command_type == "structural_check":
        if "SUCCEEDED" in status_line:
            new = advance_sub_stage(state, "compliance_scan")
        elif "FAILED" in status_line:
            new = _copy(state)
        else:
            raise ValueError(f"Unknown status for {command_type}: {status_line}")
        return new

    # lessons_learned
    if command_type == "lessons_learned":
        if "SUCCEEDED" in status_line:
            new = _copy(state)
            if new.debug_session:
                new.debug_session = dict(new.debug_session)
                new.debug_session["phase"] = "commit"
        elif "FAILED" in status_line:
            new = _copy(state)
        else:
            raise ValueError(f"Unknown status for {command_type}: {status_line}")
        return new

    # debug_commit
    if command_type == "debug_commit":
        if "SUCCEEDED" in status_line:
            return complete_debug_session(state)
        elif "FAILED" in status_line:
            return _copy(state)
        else:
            raise ValueError(f"Unknown status for {command_type}: {status_line}")

    # stage3_reentry
    if command_type == "stage3_reentry":
        if "SUCCEEDED" in status_line:
            new = _copy(state)
            if new.debug_session:
                new.debug_session = dict(new.debug_session)
                new.debug_session["phase"] = "stage3_rebuild_active"
            new.sub_stage = "stub_generation"
        elif "FAILED" in status_line:
            new = _copy(state)
        else:
            raise ValueError(f"Unknown status for {command_type}: {status_line}")
        return new

    # oracle_start
    if command_type == "oracle_start":
        # The test_project path is passed via the status_line (written by the command skill).
        # Bug S3-79: allow empty test_project so _route_oracle() handles selection.
        # Bug S3-81: command writes "ORACLE_REQUESTED" sentinel — normalize to empty
        # so the routing script's deterministic selection gate fires.
        test_project = status_line.strip()
        if test_project == "ORACLE_REQUESTED":
            test_project = ""
        new = enter_oracle_session(state, test_project)
        return new

    # oracle_test_project_selection
    if command_type == "oracle_test_project_selection":
        # status_line contains the selected test project path
        new = _copy(state)
        new.oracle_test_project = status_line.strip()
        return new

    # oracle_gate_7a — Bug S3-82: process Gate 7.A response via dispatch_gate_response
    if command_type == "oracle_gate_7a":
        return dispatch_gate_response(
            state, "gate_7_a_trajectory_review", status_line.strip(), project_root
        )

    # oracle_gate_7b — Bug S3-82: process Gate 7.B response via dispatch_gate_response
    if command_type == "oracle_gate_7b":
        return dispatch_gate_response(
            state, "gate_7_b_fix_plan_review", status_line.strip(), project_root
        )

    raise ValueError(f"Unknown command_type: {command_type}")


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------


def run_tests_main(argv: list = None) -> None:
    """CLI entry point for run_tests.py."""
    parser = argparse.ArgumentParser(description="Run tests for a unit")
    parser.add_argument("--unit", type=int, required=True)
    parser.add_argument("--language", type=str, required=True)
    parser.add_argument("--project-root", type=str, default=".")
    parser.add_argument("--sub-stage", type=str, default="red_run")

    args = parser.parse_args(argv)
    project_root = Path(args.project_root).resolve()

    lang_config = LANGUAGE_REGISTRY.get(args.language)
    if lang_config is None:
        print("TESTS_ERROR")
        return

    try:
        toolchain = load_toolchain(project_root)
    except (FileNotFoundError, KeyError):
        try:
            toolchain = load_toolchain(project_root, language=args.language)
        except (FileNotFoundError, KeyError):
            print("TESTS_ERROR")
            return

    test_cmd_template = toolchain.get("test", {}).get("command", "")
    if not test_cmd_template:
        print("TESTS_ERROR")
        return

    env_name = derive_env_name(project_root)
    run_prefix = toolchain.get("run_prefix", "")
    test_dir = lang_config.get("test_dir", "tests")
    unit_test_target = f"{test_dir}/unit_{args.unit}"

    test_cmd = resolve_command(
        test_cmd_template,
        env_name=env_name,
        run_prefix=run_prefix,
        target=unit_test_target,
    )

    try:
        result = subprocess.run(
            test_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(project_root),
        )
        output = result.stdout + result.stderr
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        print("TESTS_ERROR")
        return
    except Exception:
        print("TESTS_ERROR")
        return

    parser_key = lang_config.get("test_output_parser_key", args.language)
    test_parser = TEST_OUTPUT_PARSERS.get(parser_key)
    if test_parser is None:
        print("TESTS_ERROR")
        return

    context = {
        "collection_error_indicators": lang_config.get(
            "collection_error_indicators", []
        ),
    }
    test_result = test_parser(output, args.language, exit_code, context)

    status = test_result.status
    if status == "COLLECTION_ERROR":
        status = "TESTS_ERROR"

    print(status)


def update_state_main(argv: list = None) -> None:
    """CLI entry point for update_state.py."""
    parser = argparse.ArgumentParser(description="Update pipeline state")
    parser.add_argument("--phase", type=str, default=None)
    parser.add_argument("--project-root", type=str, default=".")
    parser.add_argument("--status", type=str, default=None)
    parser.add_argument("--gate-id", type=str, default=None)
    parser.add_argument("--unit", type=int, default=None)
    parser.add_argument("--command", type=str, default=None)

    args = parser.parse_args(argv)
    project_root = Path(args.project_root).resolve()

    # --command path: dispatch command status
    if args.command:
        state = load_state(project_root)
        last_status = _read_last_status(project_root)
        new_state = dispatch_command_status(
            state, args.command, last_status, project_root=project_root
        )
        save_state(project_root, new_state)
        _append_build_log(
            project_root,
            source="update_state",
            event_type="command_dispatch",
            command=args.command,
            status=last_status,
        )
        return

    if args.phase is None:
        print("ERROR: --phase or --command required", file=sys.stderr)
        sys.exit(1)

    if args.phase not in PHASE_TO_AGENT:
        print(f"ERROR: Unknown phase '{args.phase}'", file=sys.stderr)
        sys.exit(1)

    agent_type = PHASE_TO_AGENT[args.phase]
    state = load_state(project_root)

    if args.gate_id:
        if args.status is None:
            print("ERROR: --status required with --gate-id", file=sys.stderr)
            sys.exit(1)
        new_state = dispatch_gate_response(
            state, args.gate_id, args.status, project_root
        )
    elif args.status:
        new_state = dispatch_agent_status(state, agent_type, args.status, project_root)
    else:
        new_state = state

    save_state(project_root, new_state)

    _append_build_log(
        project_root,
        source="update_state",
        event_type="state_transition",
        phase=args.phase,
        agent_type=agent_type,
        status=args.status,
    )


def main(argv: list = None) -> None:
    """CLI entry point for routing.py."""
    parser = argparse.ArgumentParser(description="SVP routing")
    parser.add_argument("--project-root", type=str, default=".")

    args = parser.parse_args(argv)
    project_root = Path(args.project_root).resolve()

    action_block = route(project_root)

    print(json.dumps(action_block, indent=2))

    _append_build_log(
        project_root,
        source="routing",
        event_type="action_emitted",
        action_type=action_block.get("action_type", ""),
    )


if __name__ == "__main__":
    main()

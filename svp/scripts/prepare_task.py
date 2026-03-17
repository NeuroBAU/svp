"""Unit 9: Preparation Script

Assembles task prompt files for agent invocations and gate prompt files
for human decision gates.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import argparse
import json
import sys


# ---------------------------------------------------------------------------
# Bug 22 fix: import ARTIFACT_FILENAMES from Unit 1
# ---------------------------------------------------------------------------

try:
    from svp_config import ARTIFACT_FILENAMES, load_profile
except ImportError:
    # Fallback if svp_config is not on the path yet
    ARTIFACT_FILENAMES: Dict[str, str] = {
        "stakeholder_spec": "stakeholder_spec.md",
        "blueprint_dir": "blueprint",
        "project_context": "project_context.md",
        "project_profile": "project_profile.json",
        "pipeline_state": "pipeline_state.json",
        "svp_config": "svp_config.json",
        "toolchain": "toolchain.json",
        "ruff_config": "ruff.toml",
        "docs_dir": "docs",
    }
    load_profile = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# All recognized agent types (cross-unit contract with Unit 10)
# ---------------------------------------------------------------------------

KNOWN_AGENT_TYPES: List[str] = [
    "setup_agent",
    "stakeholder_dialog",
    "stakeholder_reviewer",
    "blueprint_author",
    "blueprint_checker",
    "blueprint_reviewer",
    "test_agent",
    "implementation_agent",
    "coverage_review",
    "diagnostic_agent",
    "integration_test_author",
    "git_repo_agent",
    "help_agent",
    "hint_agent",
    "redo_agent",
    "bug_triage",
    "repair_agent",
    "reference_indexing",
]

# Backward compatibility alias
ALL_AGENT_TYPES = KNOWN_AGENT_TYPES

# Agents that REQUIRE a unit_number
UNIT_REQUIRING_AGENTS = [
    "test_agent",
    "implementation_agent",
    "coverage_review",
    "diagnostic_agent",
]

# All recognized gate IDs
ALL_GATE_IDS = [
    "gate_0_1_hook_activation",
    "gate_0_2_context_approval",
    "gate_0_3_profile_approval",
    "gate_0_3r_profile_revision",
    "gate_1_1_spec_draft",
    "gate_1_2_spec_post_review",
    "gate_2_1_blueprint_approval",
    "gate_2_2_blueprint_post_review",
    "gate_2_3_alignment_exhausted",
    "gate_3_1_test_validation",
    "gate_3_2_diagnostic_decision",
    "gate_4_1_integration_failure",
    "gate_4_2_assembly_exhausted",
    "gate_5_1_repo_test",
    "gate_5_2_assembly_exhausted",
    "gate_5_3_unused_functions",
    "gate_6_0_debug_permission",
    "gate_6_1_regression_test",
    "gate_6_2_debug_classification",
    "gate_6_3_repair_exhausted",
    "gate_6_4_non_reproducible",
    "gate_6_5_debug_commit",
    "gate_hint_conflict",
]


# ---------------------------------------------------------------------------
# Document loaders
# ---------------------------------------------------------------------------


def load_stakeholder_spec(project_root: Path) -> str:
    """Load the stakeholder specification document.

    Bug 22 fix: uses ARTIFACT_FILENAMES from Unit 1.
    """
    path = project_root / "specs" / ARTIFACT_FILENAMES["stakeholder_spec"]
    if not path.exists():
        raise FileNotFoundError(f"Required document not found: {path}")
    return path.read_text(encoding="utf-8")


def load_blueprint(project_root: Path) -> str:
    """Load the blueprint document (both prose and contracts files).

    Bug 59 fix: loads blueprint_prose.md and blueprint_contracts.md from
    the blueprint/ directory instead of the old single-file blueprint.md.
    """
    blueprint_dir = project_root / "blueprint"
    prose_path = blueprint_dir / "blueprint_prose.md"
    contracts_path = blueprint_dir / "blueprint_contracts.md"
    parts = []
    for path in [prose_path, contracts_path]:
        if path.exists():
            parts.append(path.read_text(encoding="utf-8"))
    if not parts:
        # Fallback: try old single-file format
        old_path = blueprint_dir / "blueprint.md"
        if old_path.exists():
            return old_path.read_text(encoding="utf-8")
        raise FileNotFoundError(
            f"Required blueprint documents not found in {blueprint_dir}"
        )
    return "\n\n---\n\n".join(parts)


def load_reference_summaries(project_root: Path) -> str:
    """Load reference summaries."""
    path = project_root / "references" / "summaries.md"
    if not path.exists():
        raise FileNotFoundError(f"Required document not found: {path}")
    return path.read_text(encoding="utf-8")


def load_project_context(project_root: Path) -> str:
    """Load project context document."""
    path = project_root / ARTIFACT_FILENAMES.get(
        "project_context", "project_context.md"
    )
    if not path.exists():
        raise FileNotFoundError(f"Required document not found: {path}")
    return path.read_text(encoding="utf-8")


def load_ledger_content(project_root: Path, ledger_name: str) -> str:
    """Load ledger content by name."""
    path = project_root / "ledgers" / f"{ledger_name}.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Required document not found: {path}")
    return path.read_text(encoding="utf-8")


def load_quality_report(project_root: Path, gate: str) -> str:
    """Load the quality gate report from .svp/quality_report.md.

    Returns empty string if no report file exists. The gate parameter is used
    for contextual framing in the returned string, not for file path selection.
    There is a single report file overwritten on each gate execution.

    NEW IN 2.1.
    """
    report_path = project_root / ".svp" / "quality_report.md"
    if not report_path.exists():
        return ""
    raw_content = report_path.read_text(encoding="utf-8")
    # Contextual framing using the gate parameter
    return f"### Quality Report ({gate})\n\n{raw_content}"


def load_profile_sections(project_root: Path, sections: List[str]) -> str:
    """Load specific sections from the project profile.

    Gracefully handles missing profile (returns empty string with a note).
    """
    if not sections:
        return ""

    try:
        from svp_config import load_profile as _load_profile

        profile = _load_profile(project_root)
    except (RuntimeError, FileNotFoundError, Exception):
        return "(Profile not yet available.)"

    parts = []
    for section_name in sections:
        if section_name in profile:
            section_data = profile[section_name]
            parts.append(f"### {section_name}")
            parts.append("")
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    parts.append(f"- **{key}**: {value}")
            else:
                parts.append(str(section_data))
            parts.append("")

    return "\n".join(parts)


def load_full_profile(project_root: Path) -> str:
    """Load the entire project profile as a formatted string."""
    try:
        from svp_config import load_profile as _load_profile

        profile = _load_profile(project_root)
    except (RuntimeError, FileNotFoundError, Exception):
        return "(Profile not yet available.)"

    parts = []
    parts.append("## Project Profile")
    parts.append("")
    for key, value in profile.items():
        if isinstance(value, dict):
            parts.append(f"### {key}")
            parts.append("")
            for k, v in value.items():
                parts.append(f"- **{k}**: {v}")
            parts.append("")
        else:
            parts.append(f"- **{key}**: {value}")
    parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Task prompt content builder
# ---------------------------------------------------------------------------


def build_task_prompt_content(
    agent_type: str,
    sections: Dict[str, str],
    hint_block: Optional[str] = None,
) -> str:
    """Assemble task prompt from agent type, sections dict, and optional hint block."""
    parts = []
    parts.append(f"# Task Prompt: {agent_type}")
    parts.append("")

    for section_name, section_content in sections.items():
        parts.append(f"## {section_name}")
        parts.append("")
        parts.append(section_content)
        parts.append("")

    if hint_block:
        parts.append(hint_block)
        parts.append("")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Agent-specific section assembly
# ---------------------------------------------------------------------------


def _safe_load_project_context(project_root: Path) -> Optional[str]:
    """Load project context if it exists, return None otherwise."""
    try:
        return load_project_context(project_root)
    except FileNotFoundError:
        return None


def _safe_load_ledger(project_root: Path, name: str) -> Optional[str]:
    """Load ledger if it exists, return None otherwise."""
    try:
        return load_ledger_content(project_root, name)
    except FileNotFoundError:
        return None


def _safe_load_blueprint(project_root: Path) -> Optional[str]:
    """Load blueprint if it exists, return None otherwise."""
    try:
        return load_blueprint(project_root)
    except FileNotFoundError:
        return None


def _safe_load_spec(project_root: Path) -> Optional[str]:
    """Load stakeholder spec if it exists, return None otherwise."""
    try:
        return load_stakeholder_spec(project_root)
    except FileNotFoundError:
        return None


def _safe_load_reference_summaries(project_root: Path) -> Optional[str]:
    """Load reference summaries if they exist, return None otherwise."""
    try:
        return load_reference_summaries(project_root)
    except FileNotFoundError:
        return None


def _get_unit_context(project_root: Path, unit_number: int) -> str:
    """Get unit context via Unit 5 blueprint extractor."""
    try:
        from blueprint_extractor import build_unit_context

        bp_path = project_root / ARTIFACT_FILENAMES.get("blueprint_dir", "blueprint")
        return build_unit_context(bp_path, unit_number)
    except Exception:
        return f"(Unit {unit_number} context not available.)"


def _assemble_sections_for_agent(
    project_root: Path,
    agent_type: str,
    unit_number: Optional[int],
    ladder_position: Optional[str],
    hint_content: Optional[str],
    gate_id: Optional[str],
    extra_context: Optional[Dict[str, str]],
    revision_mode: Optional[str],
) -> Dict[str, str]:
    """Build the sections dict for the given agent type."""
    sections: Dict[str, str] = {}

    if agent_type == "setup_agent":
        ctx = _safe_load_project_context(project_root)
        if ctx:
            sections["project_context"] = ctx
        ledger = _safe_load_ledger(project_root, "dialog")
        if ledger:
            sections["ledger"] = ledger
        if revision_mode in ("profile_delivery", "profile_blueprint"):
            profile_str = load_full_profile(project_root)
            sections["current_profile"] = profile_str
            sections["revision_mode"] = f"Revision mode: {revision_mode}"

    elif agent_type == "stakeholder_dialog":
        ledger = _safe_load_ledger(project_root, "dialog")
        if ledger:
            sections["ledger"] = ledger
        refs = _safe_load_reference_summaries(project_root)
        if refs:
            sections["reference_summaries"] = refs
        ctx = _safe_load_project_context(project_root)
        if ctx:
            sections["project_context"] = ctx
        if revision_mode:
            spec = _safe_load_spec(project_root)
            if spec:
                sections["current_spec"] = spec
            sections["revision_mode"] = f"Revision mode: {revision_mode}"

    elif agent_type == "blueprint_author":
        sections["stakeholder_spec"] = load_stakeholder_spec(project_root)
        refs = _safe_load_reference_summaries(project_root)
        if refs:
            sections["reference_summaries"] = refs
        ledger = _safe_load_ledger(project_root, "dialog")
        if ledger:
            sections["ledger"] = ledger
        # Checker feedback if available
        checker_path = project_root / ".svp" / "checker_feedback.md"
        if checker_path.exists():
            sections["checker_feedback"] = checker_path.read_text(encoding="utf-8")
        # Profile sections: readme, vcs, delivery, quality (CHANGED IN 2.1 -- adds quality)
        profile_sections = load_profile_sections(
            project_root, ["readme", "vcs", "delivery", "quality"]
        )
        if profile_sections:
            sections["profile_sections"] = profile_sections

    elif agent_type == "blueprint_checker":
        sections["stakeholder_spec"] = load_stakeholder_spec(project_root)
        sections["blueprint"] = load_blueprint(project_root)
        refs = _safe_load_reference_summaries(project_root)
        if refs:
            sections["reference_summaries"] = refs
        # Full profile for Layer 2 preference coverage validation (including quality section)
        full_profile = load_full_profile(project_root)
        if full_profile:
            sections["full_profile"] = full_profile

    elif agent_type == "blueprint_reviewer":
        bp = _safe_load_blueprint(project_root)
        if bp:
            sections["blueprint"] = bp
        spec = _safe_load_spec(project_root)
        if spec:
            sections["stakeholder_spec"] = spec
        ctx = _safe_load_project_context(project_root)
        if ctx:
            sections["project_context"] = ctx
        refs = _safe_load_reference_summaries(project_root)
        if refs:
            sections["reference_summaries"] = refs

    elif agent_type == "stakeholder_reviewer":
        spec = _safe_load_spec(project_root)
        if spec:
            sections["stakeholder_spec"] = spec
        ctx = _safe_load_project_context(project_root)
        if ctx:
            sections["project_context"] = ctx
        refs = _safe_load_reference_summaries(project_root)
        if refs:
            sections["reference_summaries"] = refs

    elif agent_type == "test_agent":
        if unit_number is not None:
            sections["unit_context"] = _get_unit_context(project_root, unit_number)
        # testing.readable_test_names from profile
        profile_sections = load_profile_sections(project_root, ["testing"])
        if profile_sections:
            sections["testing_profile"] = profile_sections
        # NEW IN 2.1: In quality gate retry (quality_gate_a_retry): add quality report
        if ladder_position == "quality_gate_a_retry":
            qr = load_quality_report(project_root, "gate_a")
            if qr:
                sections["quality_report"] = qr

    elif agent_type == "implementation_agent":
        if unit_number is not None:
            sections["unit_context"] = _get_unit_context(project_root, unit_number)
        # In fix ladder positions: add diagnostic guidance, prior failure output
        if ladder_position:
            diag_path = project_root / ".svp" / "diagnostic_guidance.md"
            if diag_path.exists():
                sections["diagnostic_guidance"] = diag_path.read_text(encoding="utf-8")
            failure_path = project_root / ".svp" / "failure_output.txt"
            if failure_path.exists():
                sections["prior_failure_output"] = failure_path.read_text(
                    encoding="utf-8"
                )
        # NEW IN 2.1: In quality gate retry (quality_gate_b_retry): add quality report
        if ladder_position == "quality_gate_b_retry":
            qr = load_quality_report(project_root, "gate_b")
            if qr:
                sections["quality_report"] = qr

    elif agent_type == "coverage_review":
        if unit_number is not None:
            sections["unit_context"] = _get_unit_context(project_root, unit_number)
        # Passing tests
        tests_path = project_root / ".svp" / "passing_tests.txt"
        if tests_path.exists():
            sections["passing_tests"] = tests_path.read_text(encoding="utf-8")

    elif agent_type == "diagnostic_agent":
        spec = _safe_load_spec(project_root)
        if spec:
            sections["stakeholder_spec"] = spec
        if unit_number is not None:
            sections["unit_context"] = _get_unit_context(project_root, unit_number)
        # Failing tests, error output, failing implementations
        failing_tests_path = project_root / ".svp" / "failing_tests.txt"
        if failing_tests_path.exists():
            sections["failing_tests"] = failing_tests_path.read_text(encoding="utf-8")
        error_path = project_root / ".svp" / "error_output.txt"
        if error_path.exists():
            sections["error_output"] = error_path.read_text(encoding="utf-8")
        impl_path = project_root / ".svp" / "failing_implementation.py"
        if impl_path.exists():
            sections["failing_implementation"] = impl_path.read_text(encoding="utf-8")

    elif agent_type == "integration_test_author":
        spec = _safe_load_spec(project_root)
        if spec:
            sections["stakeholder_spec"] = spec
        bp = _safe_load_blueprint(project_root)
        if bp:
            sections["contract_signatures"] = bp

    elif agent_type == "git_repo_agent":
        # All verified artifacts, reference documents
        spec = _safe_load_spec(project_root)
        if spec:
            sections["stakeholder_spec"] = spec
        bp = _safe_load_blueprint(project_root)
        if bp:
            sections["blueprint"] = bp
        refs = _safe_load_reference_summaries(project_root)
        if refs:
            sections["reference_summaries"] = refs
        # Full profile
        full_profile = load_full_profile(project_root)
        if full_profile:
            sections["full_profile"] = full_profile
        # Reference README for carry-forward (Mode A / additive treatment)
        refs_dir = project_root / "references"
        if refs_dir.is_dir():
            readme_files = sorted(refs_dir.glob("README_v*.md"))
            if readme_files:
                # Use the most recent version as the carry-forward base
                ref_readme = readme_files[-1]
                sections["reference_readme"] = (
                    f"## Reference README (carry-forward base: {ref_readme.name})\n\n"
                    "If the project profile has `readme.treatment: additive`, "
                    "you MUST preserve the full content of this reference README "
                    "and extend it with new sections for the current release. "
                    "Do NOT rewrite, reorganize, or summarize existing content.\n\n"
                    + ref_readme.read_text(encoding="utf-8")
                )
        # Fix cycle error output
        error_path = project_root / ".svp" / "error_output.txt"
        if error_path.exists():
            sections["error_output"] = error_path.read_text(encoding="utf-8")

    elif agent_type == "help_agent":
        # Project summary, stakeholder spec, blueprint
        ctx = _safe_load_project_context(project_root)
        if ctx:
            sections["project_summary"] = ctx
        spec = _safe_load_spec(project_root)
        if spec:
            sections["stakeholder_spec"] = spec
        bp = _safe_load_blueprint(project_root)
        if bp:
            sections["blueprint"] = bp
        # Gate invocation mode
        if gate_id:
            sections["gate_flag"] = f"Gate invocation mode: {gate_id}"

    elif agent_type == "hint_agent":
        # logs, documents, stakeholder spec, blueprint
        ledger = _safe_load_ledger(project_root, "dialog")
        if ledger:
            sections["logs"] = ledger
        ctx = _safe_load_project_context(project_root)
        if ctx:
            sections["documents"] = ctx
        spec = _safe_load_spec(project_root)
        if spec:
            sections["stakeholder_spec"] = spec
        bp = _safe_load_blueprint(project_root)
        if bp:
            sections["blueprint"] = bp

    elif agent_type == "redo_agent":
        # Pipeline state summary, human error description
        state_path = project_root / ARTIFACT_FILENAMES.get(
            "pipeline_state", "pipeline_state.json"
        )
        if state_path.exists():
            sections["pipeline_state"] = state_path.read_text(encoding="utf-8")
        # Current unit definition (optional -- only when unit_number is provided)
        if unit_number is not None:
            sections["unit_context"] = _get_unit_context(project_root, unit_number)

    elif agent_type == "reference_indexing":
        # Full reference document
        refs = _safe_load_reference_summaries(project_root)
        if refs:
            sections["reference_document"] = refs
        else:
            sections["reference_document"] = "(No reference documents available.)"

    elif agent_type == "bug_triage":
        spec = _safe_load_spec(project_root)
        if spec:
            sections["stakeholder_spec"] = spec
        bp = _safe_load_blueprint(project_root)
        if bp:
            sections["blueprint"] = bp
        # Source code paths, test suite paths
        sections["source_paths"] = "(Source code paths determined at runtime.)"
        sections["test_paths"] = "(Test suite paths determined at runtime.)"
        ledger = _safe_load_ledger(project_root, "dialog")
        if ledger:
            sections["ledger"] = ledger
        # NEW IN 2.1: Include delivered_repo_path from pipeline state
        state_path = project_root / ARTIFACT_FILENAMES.get(
            "pipeline_state", "pipeline_state.json"
        )
        if state_path.exists():
            try:
                state_data = json.loads(state_path.read_text(encoding="utf-8"))
                delivered_path = state_data.get("delivered_repo_path")
                if delivered_path:
                    sections["delivered_repo_path"] = str(delivered_path)
            except (json.JSONDecodeError, KeyError):
                pass

    elif agent_type == "repair_agent":
        # Build/environment error diagnosis, environment state
        error_path = project_root / ".svp" / "error_output.txt"
        if error_path.exists():
            sections["error_diagnosis"] = error_path.read_text(encoding="utf-8")
        else:
            sections["error_diagnosis"] = "(No error output available.)"
        sections["environment_state"] = "(Environment state determined at runtime.)"

    # Add extra context if provided
    if extra_context:
        for key, value in extra_context.items():
            sections[f"extra_{key}"] = value

    return sections


# ---------------------------------------------------------------------------
# Main preparation functions
# ---------------------------------------------------------------------------


def prepare_agent_task(
    project_root: Path,
    agent_type: str,
    unit_number: Optional[int] = None,
    ladder_position: Optional[str] = None,
    hint_content: Optional[str] = None,
    gate_id: Optional[str] = None,
    extra_context: Optional[Dict[str, str]] = None,
    revision_mode: Optional[str] = None,
) -> Path:
    """Assemble a task prompt file at .svp/task_prompt.md and return its path."""
    # Pre-conditions
    assert project_root.is_dir(), "Project root must exist"

    # Validate agent type
    if agent_type not in KNOWN_AGENT_TYPES:
        raise ValueError(f"Unknown agent type: {agent_type}")

    # Validate unit number requirement
    if agent_type in UNIT_REQUIRING_AGENTS and unit_number is None:
        raise ValueError(f"Unit number required for agent type {agent_type}")

    # Assemble sections
    sections = _assemble_sections_for_agent(
        project_root=project_root,
        agent_type=agent_type,
        unit_number=unit_number,
        ladder_position=ladder_position,
        hint_content=hint_content,
        gate_id=gate_id,
        extra_context=extra_context,
        revision_mode=revision_mode,
    )

    # Handle hint content via Unit 8
    hint_block = None
    if hint_content:
        try:
            from hint_prompt_assembler import assemble_hint_prompt

            # Map agent_type to Unit 8's valid agent types
            agent_type_map = {
                "test_agent": "test",
                "implementation_agent": "implementation",
                "blueprint_author": "blueprint_author",
                "stakeholder_dialog": "stakeholder_dialog",
                "diagnostic_agent": "diagnostic",
            }
            mapped_type = agent_type_map.get(agent_type, "other")
            hint_block = assemble_hint_prompt(
                hint_content=hint_content,
                gate_id=gate_id or "",
                agent_type=mapped_type,
                ladder_position=ladder_position,
                unit_number=unit_number,
                stage="",
            )
        except Exception:
            # Fallback: include hint directly
            hint_block = f"## Human Domain Hint\n\n{hint_content}"

    # Build the content
    content = build_task_prompt_content(
        agent_type=agent_type,
        sections=sections,
        hint_block=hint_block,
    )

    # Write to .svp/task_prompt.md
    svp_dir = project_root / ".svp"
    svp_dir.mkdir(exist_ok=True)
    output_path = svp_dir / "task_prompt.md"
    output_path.write_text(content, encoding="utf-8")

    # Post-conditions
    assert output_path.exists(), "Task prompt file must exist after preparation"
    assert output_path.stat().st_size > 0, "Task prompt file must not be empty"

    return output_path


def prepare_gate_prompt(
    project_root: Path,
    gate_id: str,
    unit_number: Optional[int] = None,
    extra_context: Optional[Dict[str, str]] = None,
) -> Path:
    """Assemble a gate prompt file at .svp/gate_prompt.md and return its path."""
    # Pre-conditions
    assert project_root.is_dir(), "Project root must exist"

    # Validate gate ID
    if gate_id not in ALL_GATE_IDS:
        raise ValueError(f"Unknown gate ID: {gate_id}")

    # Build gate prompt content
    parts = []

    if gate_id == "gate_0_1_hook_activation":
        parts.append("# Gate 0.1: Hook Activation")
        parts.append("")
        parts.append("Confirm that SVP hooks have been activated for this project.")
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **HOOKS ACTIVATED**: Hooks are set up and ready.")
        parts.append("- **HOOKS FAILED**: Hook activation failed or was not completed.")

    elif gate_id == "gate_0_3_profile_approval":
        parts.append("# Gate 0.3: Profile Approval")
        parts.append("")
        parts.append(
            "Review the project profile below and decide whether to approve it."
        )
        parts.append("")
        # Include profile summary
        profile_str = load_full_profile(project_root)
        parts.append(profile_str)
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **APPROVE**: Accept the profile as-is.")
        parts.append("- **REVISE**: Request changes to the profile.")
        parts.append("- **REJECT**: Reject the profile entirely.")

    elif gate_id == "gate_0_3r_profile_revision":
        parts.append("# Gate 0.3r: Profile Revision Review")
        parts.append("")
        parts.append(
            "Review the modified project profile below and decide whether to approve the changes."
        )
        parts.append("")
        # Include modified profile summary
        profile_str = load_full_profile(project_root)
        parts.append(profile_str)
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **APPROVE**: Accept the revised profile.")
        parts.append("- **REVISE**: Request further changes.")
        parts.append("- **REJECT**: Reject the revised profile.")

    elif gate_id == "gate_0_2_context_approval":
        parts.append("# Gate 0.2: Context Approval")
        parts.append("")
        parts.append(
            "Review the project context document and decide whether to approve it."
        )
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **CONTEXT APPROVED**: Accept the project context.")
        parts.append("- **CONTEXT REJECTED**: Reject and request changes.")
        parts.append("- **CONTEXT NOT READY**: Context needs more work.")

    elif gate_id == "gate_1_1_spec_draft":
        parts.append("# Gate 1.1: Spec Draft Approval")
        parts.append("")
        parts.append(
            "Review the stakeholder specification draft and decide whether to approve it."
        )
        parts.append("")
        # Include the spec if available
        spec = _safe_load_spec(project_root)
        if spec:
            parts.append("## Stakeholder Specification")
            parts.append("")
            parts.append(spec)
            parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **APPROVE**: Accept the spec and advance to Stage 2.")
        parts.append("- **REVISE**: Request changes to the spec.")
        parts.append(
            "- **FRESH REVIEW**: Request a cold review by a separate reviewer agent."
        )

    elif gate_id == "gate_1_2_spec_post_review":
        parts.append("# Gate 1.2: Spec Post-Review")
        parts.append("")
        parts.append("A fresh reviewer has examined the stakeholder specification.")
        parts.append("Review the critique and decide how to proceed.")
        parts.append("")
        # Include the spec if available
        spec = _safe_load_spec(project_root)
        if spec:
            parts.append("## Stakeholder Specification")
            parts.append("")
            parts.append(spec)
            parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **APPROVE**: Accept the spec as-is despite the critique.")
        parts.append("- **REVISE**: Take the critique to revision.")
        parts.append("- **FRESH REVIEW**: Request another cold review.")

    elif gate_id == "gate_2_1_blueprint_approval":
        parts.append("# Gate 2.1: Blueprint Approval")
        parts.append("")
        parts.append("Review the blueprint draft and decide whether to approve it.")
        parts.append("")
        # Include both blueprint files
        prose_path = project_root / "blueprint" / "blueprint_prose.md"
        contracts_path = project_root / "blueprint" / "blueprint_contracts.md"
        if prose_path.exists():
            parts.append("## Blueprint Prose (Tier 1)")
            parts.append("")
            parts.append(prose_path.read_text(encoding="utf-8"))
            parts.append("")
        if contracts_path.exists():
            parts.append("## Blueprint Contracts (Tiers 2 & 3)")
            parts.append("")
            parts.append(contracts_path.read_text(encoding="utf-8"))
            parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append(
            "- **APPROVE**: Accept the blueprint and advance to alignment check."
        )
        parts.append("- **REVISE**: Request changes to the blueprint.")
        parts.append(
            "- **FRESH REVIEW**: Request a cold review by a separate reviewer agent."
        )

    elif gate_id == "gate_2_2_blueprint_post_review":
        parts.append("# Gate 2.2: Blueprint Post-Review")
        parts.append("")
        parts.append(
            "A fresh reviewer has examined the blueprint, or alignment has been confirmed."
        )
        parts.append("Review and decide how to proceed.")
        parts.append("")
        # Include both blueprint files
        prose_path = project_root / "blueprint" / "blueprint_prose.md"
        contracts_path = project_root / "blueprint" / "blueprint_contracts.md"
        if prose_path.exists():
            parts.append("## Blueprint Prose (Tier 1)")
            parts.append("")
            parts.append(prose_path.read_text(encoding="utf-8"))
            parts.append("")
        if contracts_path.exists():
            parts.append("## Blueprint Contracts (Tiers 2 & 3)")
            parts.append("")
            parts.append(contracts_path.read_text(encoding="utf-8"))
            parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **APPROVE**: Accept the blueprint and advance to Pre-Stage-3.")
        parts.append("- **REVISE**: Take the critique to revision.")
        parts.append("- **FRESH REVIEW**: Request another cold review.")

    elif gate_id == "gate_2_3_alignment_exhausted":
        parts.append("# Gate 2.3: Alignment Exhausted")
        parts.append("")
        parts.append("The blueprint checker has exhausted its alignment iterations.")
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append(
            "- **REVISE SPEC**: Revise the stakeholder spec to resolve alignment issues."
        )
        parts.append("- **RESTART SPEC**: Restart the stakeholder spec from scratch.")
        parts.append("- **RETRY BLUEPRINT**: Retry the blueprint with fresh context.")

    elif gate_id == "gate_3_1_test_validation":
        parts.append("# Gate 3.1: Test Validation")
        parts.append("")
        parts.append("Review the generated tests and decide whether they are correct.")
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **TEST CORRECT**: The tests are correct.")
        parts.append("- **TEST WRONG**: The tests are incorrect.")

    elif gate_id == "gate_3_2_diagnostic_decision":
        parts.append("# Gate 3.2: Diagnostic Decision")
        parts.append("")
        parts.append("Diagnosis is complete. Decide the classification for the fix.")
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **FIX IMPLEMENTATION**: Fix the implementation.")
        parts.append("- **FIX BLUEPRINT**: The problem is in the blueprint.")
        parts.append("- **FIX SPEC**: The problem is in the stakeholder spec.")

    elif gate_id == "gate_5_1_repo_test":
        parts.append("# Gate 5.1: Repository Test")
        parts.append("")
        parts.append(
            "Run the test suite in the delivered repository and report results."
        )
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **TESTS PASSED**: All tests pass in the delivered repo.")
        parts.append("- **TESTS FAILED**: Tests failed (paste output).")

    elif gate_id == "gate_5_2_assembly_exhausted":
        parts.append("# Gate 5.2: Assembly Exhausted")
        parts.append("")
        parts.append(
            "The repo assembly bounded fix cycle has been exhausted (3 attempts)."
        )
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **RETRY ASSEMBLY**: Reset retries and try assembly again.")
        parts.append("- **FIX BLUEPRINT**: The problem is in the blueprint.")
        parts.append("- **FIX SPEC**: The problem is in the stakeholder spec.")

    elif gate_id == "gate_4_1_integration_failure":
        parts.append("# Gate 4.1: Integration Test Failure")
        parts.append("")
        parts.append("Integration tests have failed. Decide how to proceed.")
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **ASSEMBLY FIX**: Attempt to fix the assembly.")
        parts.append("- **FIX BLUEPRINT**: The problem is in the blueprint.")
        parts.append("- **FIX SPEC**: The problem is in the stakeholder spec.")

    elif gate_id == "gate_4_2_assembly_exhausted":
        parts.append("# Gate 4.2: Assembly Exhausted")
        parts.append("")
        parts.append("Integration test fix attempts have been exhausted.")
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **FIX BLUEPRINT**: The problem is in the blueprint.")
        parts.append("- **FIX SPEC**: The problem is in the stakeholder spec.")

    elif gate_id == "gate_6_0_debug_permission":
        parts.append("# Gate 6.0: Debug Permission")
        parts.append("")
        parts.append("A bug has been detected. Authorize or abandon the debug session.")
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **AUTHORIZE DEBUG**: Authorize the debug session.")
        parts.append("- **ABANDON DEBUG**: Abandon the debug session.")

    elif gate_id == "gate_6_1_regression_test":
        parts.append("# Gate 6.1: Regression Test")
        parts.append("")
        parts.append("Review the regression test and decide whether it is correct.")
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **TEST CORRECT**: The regression test is correct.")
        parts.append("- **TEST WRONG**: The regression test is incorrect.")

    elif gate_id == "gate_6_2_debug_classification":
        parts.append("# Gate 6.2: Debug Classification")
        parts.append("")
        parts.append("Bug triage is complete. Decide the classification for the fix.")
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **FIX UNIT**: Fix the bug at the unit level.")
        parts.append("- **FIX BLUEPRINT**: The problem is in the blueprint.")
        parts.append("- **FIX SPEC**: The problem is in the stakeholder spec.")

    elif gate_id == "gate_6_3_repair_exhausted":
        parts.append("# Gate 6.3: Repair Exhausted")
        parts.append("")
        parts.append("Repair attempts have been exhausted. Decide how to proceed.")
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **RETRY REPAIR**: Retry the repair.")
        parts.append(
            "- **RECLASSIFY BUG**: Reclassify the bug for a different approach."
        )
        parts.append("- **ABANDON DEBUG**: Abandon the debug session.")

    elif gate_id == "gate_6_4_non_reproducible":
        parts.append("# Gate 6.4: Non-Reproducible Bug")
        parts.append("")
        parts.append("The bug could not be reproduced. Decide how to proceed.")
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **RETRY TRIAGE**: Retry the triage process.")
        parts.append("- **ABANDON DEBUG**: Abandon the debug session.")

    elif gate_id == "gate_6_5_debug_commit":
        # NEW IN 2.1: Gate 6.5 for debug commit
        parts.append("# Gate 6.5: Debug Commit")
        parts.append("")
        parts.append(
            "Review the debug commit details below and decide whether to proceed."
        )
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **APPROVE**: Accept the debug commit.")
        parts.append("- **REJECT**: Reject the debug commit.")

    elif gate_id == "gate_hint_conflict":
        parts.append("# Gate H.1: Hint-Blueprint Conflict")
        parts.append("")
        parts.append(
            "A human domain hint contradicts the blueprint contract. "
            "Decide which is correct."
        )
        parts.append("")
        parts.append("## Response Options")
        parts.append("")
        parts.append("- **BLUEPRINT CORRECT**: Discard the hint.")
        parts.append("- **HINT CORRECT**: Revise the blueprint to match the hint.")

    # Add extra context
    if extra_context:
        parts.append("")
        parts.append("## Additional Context")
        parts.append("")
        for key, value in extra_context.items():
            parts.append(f"### {key}")
            parts.append("")
            parts.append(value)
            parts.append("")

    content = "\n".join(parts)

    # Write to .svp/gate_prompt.md
    svp_dir = project_root / ".svp"
    svp_dir.mkdir(exist_ok=True)
    output_path = svp_dir / "gate_prompt.md"
    output_path.write_text(content, encoding="utf-8")

    # Post-conditions
    assert output_path.exists(), "Gate prompt file must exist after preparation"
    assert output_path.stat().st_size > 0, "Gate prompt file must not be empty"

    return output_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for the preparation script."""
    parser = argparse.ArgumentParser(description="SVP Preparation Script")
    parser.add_argument(
        "--project-root", type=str, default=".", help="Project root directory"
    )
    parser.add_argument("--agent", type=str, default=None, help="Agent type")
    parser.add_argument("--gate", type=str, default=None, help="Gate ID")
    parser.add_argument("--unit", type=int, default=None, help="Unit number")
    parser.add_argument("--ladder", type=str, default=None, help="Ladder position")
    parser.add_argument("--revision-mode", type=str, default=None, help="Revision mode")
    parser.add_argument(
        "--quality-report",
        type=str,
        default=None,
        help="Quality report path or gate name",
    )
    parser.add_argument("--output", type=str, default=None, help="Override output path")

    args = parser.parse_args()
    project_root = Path(args.project_root)

    if args.agent:
        result = prepare_agent_task(
            project_root=project_root,
            agent_type=args.agent,
            unit_number=args.unit,
            ladder_position=args.ladder,
            revision_mode=args.revision_mode,
        )
    elif args.gate:
        result = prepare_gate_prompt(
            project_root=project_root,
            gate_id=args.gate,
            unit_number=args.unit,
        )
    else:
        parser.error("Must specify either --agent or --gate")
        return

    # If output override is specified, copy the file (unless it's already at that path)
    if args.output:
        import shutil

        output_path = Path(args.output)
        if output_path.resolve() != result.resolve():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(result, output_path)
            result = output_path

    print(str(result))


if __name__ == "__main__":
    main()

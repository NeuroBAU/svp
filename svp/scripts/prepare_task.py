"""Unit 9: Preparation Script

Assembles task prompt files for agent invocations and gate prompt files
for human decision gates. Takes the agent type (or gate identifier),
unit number, ladder position, and other parameters as input and produces
a ready-to-use file at a specified path.

Implements spec Section 3.7 (explicit context loading) and Section 17.1
(PREPARE command).
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import argparse
import json
import sys

# ---------------------------------------------------------------------------
# Upstream contract imports
# ---------------------------------------------------------------------------
# Unit 2: Pipeline State Schema
from pipeline_state import load_state, PipelineState

# Unit 4: Ledger Manager
from ledger_manager import read_ledger, LedgerEntry

# Unit 5: Blueprint Extractor
from blueprint_extractor import (
    extract_unit,
    extract_upstream_contracts,
    build_unit_context,
    parse_blueprint,
    UnitDefinition,
)

# Unit 8: Hint Prompt Assembler
from hint_assembler import assemble_hint_prompt


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KNOWN_AGENT_TYPES: List[str] = [
    "setup_agent",
    "stakeholder_dialog",
    "blueprint_author",
    "blueprint_checker",
    "blueprint_reviewer",
    "stakeholder_reviewer",
    "test_agent",
    "implementation_agent",
    "coverage_review",
    "diagnostic_agent",
    "integration_test_author",
    "git_repo_agent",
    "help_agent",
    "hint_agent",
    "redo_agent",
    "reference_indexing",
    "bug_triage",
    "repair_agent",
]

# Agent types that require a unit_number parameter
UNIT_REQUIRED_AGENTS: List[str] = [
    "test_agent",
    "implementation_agent",
    "coverage_review",
    "diagnostic_agent",
]

# Known gate IDs -- using the long-form gate_N_N_description convention
KNOWN_GATE_IDS: List[str] = [
    "gate_0_1_hook_activation",
    "gate_0_2_context_approval",
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
    "gate_6_0_debug_permission",
    "gate_6_1_regression_test",
    "gate_6_2_debug_classification",
    "gate_6_3_repair_exhausted",
    "gate_6_4_non_reproducible",
]

# Map long-form gate IDs to gate categories for assembler dispatch
_GATE_CATEGORY_MAP: Dict[str, str] = {
    "gate_0_1_hook_activation": "hook_activation",
    "gate_0_2_context_approval": "context_approval",
    "gate_1_1_spec_draft": "spec_approval",
    "gate_1_2_spec_post_review": "spec_approval",
    "gate_2_1_blueprint_approval": "blueprint_approval",
    "gate_2_2_blueprint_post_review": "blueprint_approval",
    "gate_2_3_alignment_exhausted": "diagnostic",
    "gate_3_1_test_validation": "test_validation",
    "gate_3_2_diagnostic_decision": "diagnostic",
    "gate_4_1_integration_failure": "integration_failure",
    "gate_4_2_assembly_exhausted": "diagnostic",
    "gate_5_1_repo_test": "repo_test",
    "gate_5_2_assembly_exhausted": "diagnostic",
    "gate_6_0_debug_permission": "debug_permission",
    "gate_6_1_regression_test": "regression_test",
    "gate_6_2_debug_classification": "debug_classification",
    "gate_6_3_repair_exhausted": "diagnostic",
    "gate_6_4_non_reproducible": "diagnostic",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_file(path: Path) -> str:
    """Read a file and return its content. Raises FileNotFoundError."""
    if not path.exists():
        raise FileNotFoundError(f"Required document not found: {path}")
    return path.read_text(encoding="utf-8")



def _extract_unit_checked(blueprint_path: Path, unit_number: int) -> UnitDefinition:
    """Wrapper around extract_unit that converts error messages to contract format."""
    try:
        return extract_unit(blueprint_path, unit_number)
    except FileNotFoundError:
        raise FileNotFoundError(f"Required document not found: {blueprint_path}")


def _extract_upstream_checked(blueprint_path: Path, unit_number: int) -> List[Dict[str, str]]:
    """Wrapper around extract_upstream_contracts that converts error messages."""
    try:
        return extract_upstream_contracts(blueprint_path, unit_number)
    except FileNotFoundError:
        raise FileNotFoundError(f"Required document not found: {blueprint_path}")


def _read_file_optional(path: Path) -> str:
    """Read a file if it exists, return empty string otherwise."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _try_load_state(project_root: Path) -> Optional[PipelineState]:
    """Attempt to load pipeline state. Returns None on any error."""
    try:
        return load_state(project_root)
    except Exception:
        return None


def _load_ledger_as_text(ledger_path: Path) -> str:
    """Load a JSONL ledger and format entries as readable text."""
    if not ledger_path.exists():
        return ""
    try:
        entries = read_ledger(ledger_path)
    except Exception:
        return ""
    if not entries:
        return ""
    lines = []
    for entry in entries:
        role_label = entry.role.upper()
        lines.append(f"[{role_label}] {entry.content}")
    return "\n\n".join(lines)


def _build_project_summary(state: PipelineState) -> str:
    """Build a human-readable project summary from pipeline state."""
    parts: List[str] = []
    if state.project_name:
        parts.append(f"**Project:** {state.project_name}")
    parts.append(f"**Current Stage:** {state.stage}")
    if state.sub_stage:
        parts.append(f"**Sub-stage:** {state.sub_stage}")
    if state.current_unit is not None:
        total = state.total_units or "?"
        parts.append(f"**Current Unit:** {state.current_unit} of {total}")
    if state.fix_ladder_position:
        parts.append(f"**Fix Ladder Position:** {state.fix_ladder_position}")
    verified_count = len(state.verified_units)
    parts.append(f"**Verified Units:** {verified_count}")
    if state.pass_history:
        current_pass = len(state.pass_history) + 1
        parts.append(f"**Current Pass:** {current_pass}")
    if state.last_action:
        parts.append(f"**Last Action:** {state.last_action}")
    return "\n".join(parts)


def _format_unit_definition(unit_def: UnitDefinition) -> str:
    """Format a UnitDefinition into a markdown section."""
    parts: List[str] = []
    parts.append(f"## Unit {unit_def.unit_number}: {unit_def.unit_name}")
    parts.append("")

    if unit_def.description:
        parts.append("### Tier 1 -- Description")
        parts.append("")
        parts.append(unit_def.description)
        parts.append("")

    if unit_def.signatures:
        parts.append("### Tier 2 -- Signatures")
        parts.append("")
        parts.append("```python")
        parts.append(unit_def.signatures)
        parts.append("```")
        parts.append("")

    if unit_def.invariants:
        parts.append("### Tier 2 -- Invariants")
        parts.append("")
        parts.append("```python")
        parts.append(unit_def.invariants)
        parts.append("```")
        parts.append("")

    if unit_def.error_conditions:
        parts.append("### Tier 3 -- Error Conditions")
        parts.append("")
        parts.append(unit_def.error_conditions)
        parts.append("")

    if unit_def.behavioral_contracts:
        parts.append("### Tier 3 -- Behavioral Contracts")
        parts.append("")
        parts.append(unit_def.behavioral_contracts)
        parts.append("")

    return "\n".join(parts)


def _format_upstream_contracts(upstream: List[Dict[str, str]]) -> str:
    """Format upstream contract signatures into a markdown section."""
    if not upstream:
        return ""
    parts: List[str] = []
    parts.append("## Upstream Contract Signatures")
    parts.append("")
    for contract in upstream:
        parts.append(f"### Unit {contract['unit_number']}: {contract['unit_name']}")
        parts.append("")
        if contract.get("signatures", ""):
            parts.append("```python")
            parts.append(contract["signatures"])
            parts.append("```")
            parts.append("")
    return "\n".join(parts)


def _inject_hint(
    prompt: str,
    hint_content: Optional[str],
    agent_type: str,
    gate_id: Optional[str] = None,
    ladder_position: Optional[str] = None,
    unit_number: Optional[int] = None,
    stage: str = "",
) -> str:
    """Append a hint section to the prompt using Unit 8."""
    if not hint_content:
        return prompt

    # Map agent_type to Unit 8's recognized agent types
    agent_type_map = {
        "test_agent": "test",
        "implementation_agent": "implementation",
        "blueprint_author": "blueprint_author",
        "stakeholder_dialog": "stakeholder_dialog",
        "diagnostic_agent": "diagnostic",
    }
    mapped_type = agent_type_map.get(agent_type, "other")

    hint_section = assemble_hint_prompt(
        hint_content=hint_content,
        gate_id=gate_id or "unknown",
        agent_type=mapped_type,
        ladder_position=ladder_position,
        unit_number=unit_number,
        stage=stage,
    )
    return prompt + "\n\n" + hint_section


def _append_extra_context(sections: List[str], extra_context: Optional[Dict[str, str]]) -> None:
    """Append any unrecognized extra_context keys as additional sections."""
    if not extra_context:
        return
    # Keys that are already handled by specific assemblers should be listed here
    # so they are not duplicated. Each assembler handles its own known keys.
    # Generic/unknown keys get added as extra sections.
    for key, value in extra_context.items():
        if value:
            # Format the key nicely: replace underscores with spaces, title case
            heading = key.replace("_", " ").title()
            sections.append(f"## {heading}\n")
            sections.append(value)


# ---------------------------------------------------------------------------
# Public loader functions
# ---------------------------------------------------------------------------

def load_stakeholder_spec(project_root: Path) -> str:
    """Load the stakeholder spec from specs/stakeholder_spec.md or specs/stakeholder.md."""
    assert project_root.is_dir(), "Project root must exist"

    # Try standard paths
    path1 = project_root / "specs" / "stakeholder_spec.md"
    path2 = project_root / "specs" / "stakeholder.md"

    if path1.exists():
        return path1.read_text(encoding="utf-8")
    if path2.exists():
        return path2.read_text(encoding="utf-8")

    raise FileNotFoundError(f"Required document not found: {path1}")


def load_blueprint(project_root: Path) -> str:
    """Load the blueprint from blueprint/blueprint.md."""
    assert project_root.is_dir(), "Project root must exist"
    path = project_root / "blueprint" / "blueprint.md"
    if not path.exists():
        raise FileNotFoundError(f"Required document not found: {path}")
    return path.read_text(encoding="utf-8")


def load_reference_summaries(project_root: Path) -> str:
    """Load all reference summaries from references/index/."""
    assert project_root.is_dir(), "Project root must exist"
    index_dir = project_root / "references" / "index"
    if not index_dir.is_dir():
        return ""
    summaries: List[str] = []
    for summary_file in sorted(index_dir.iterdir()):
        if summary_file.is_file():
            content = summary_file.read_text(encoding="utf-8")
            summaries.append(f"### Reference: {summary_file.stem}\n\n{content}")
    if not summaries:
        return ""
    return "## Reference Document Summaries\n\n" + "\n\n---\n\n".join(summaries)


def load_project_context(project_root: Path) -> str:
    """Load project context from .svp/project_context.md or project_context.md."""
    assert project_root.is_dir(), "Project root must exist"

    # Try multiple paths
    paths = [
        project_root / ".svp" / "project_context.md",
        project_root / "project_context.md",
    ]
    for path in paths:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""


def load_ledger_content(project_root: Path, ledger_name: str) -> str:
    """Load and format a ledger file by name from ledgers/.

    The ledger_name can be either a bare name (e.g. 'conversation') or
    a full filename (e.g. 'conversation.jsonl'). If the name doesn't end
    with .jsonl, the extension is appended automatically.
    """
    assert project_root.is_dir(), "Project root must exist"
    if not ledger_name.endswith(".jsonl"):
        ledger_name = ledger_name + ".jsonl"
    ledger_path = project_root / "ledgers" / ledger_name
    return _load_ledger_as_text(ledger_path)


def build_task_prompt_content(
    agent_type: str,
    sections: Dict[str, str],
    hint_block: Optional[str] = None,
) -> str:
    """Build the final task prompt content from sections and optional hint.

    Sections is a dict of section_name -> section_content.
    The sections are joined in order with markdown formatting.

    Raises ValueError if agent_type is not recognized.
    """
    if agent_type not in KNOWN_AGENT_TYPES:
        raise ValueError(f"Unknown agent type: {agent_type}")

    parts: List[str] = []
    parts.append(f"# {agent_type} Task Prompt\n")

    for section_name, section_content in sections.items():
        if section_content:
            parts.append(f"## {section_name}\n")
            parts.append(section_content)

    prompt = "\n\n".join(parts)

    if hint_block:
        prompt = prompt + "\n\n" + hint_block

    return prompt


# ---------------------------------------------------------------------------
# Agent-specific assemblers
# ---------------------------------------------------------------------------

def _assemble_setup_agent(
    project_root: Path,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for setup_agent."""
    sections: List[str] = []
    sections.append("# Setup Agent Task Prompt\n")

    # Project context (may already exist partially)
    project_context = load_project_context(project_root)
    if project_context:
        sections.append("## Existing Project Context\n")
        sections.append(project_context)

    # Ledger content
    ledger_text = load_ledger_content(project_root, "setup_dialog")
    if ledger_text:
        sections.append("## Conversation History\n")
        sections.append(ledger_text)

    # Reference summaries
    ref_summaries = load_reference_summaries(project_root)
    if ref_summaries:
        sections.append(ref_summaries)

    # Include any extra context entries
    _append_extra_context(sections, extra_context)

    return "\n\n".join(sections)


def _assemble_stakeholder_dialog(
    project_root: Path,
    hint_content: Optional[str] = None,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for stakeholder_dialog."""
    extra = extra_context or {}
    revision_mode = bool(extra.get("revision_mode", False))
    critique = extra.get("critique", "")

    sections: List[str] = []
    sections.append("# Stakeholder Dialog Task Prompt\n")

    if revision_mode:
        sections.append("**MODE: REVISION** -- This is a targeted revision of an existing spec.\n")

    # Project context
    project_context = load_project_context(project_root)
    if project_context:
        sections.append("## Project Context\n")
        sections.append(project_context)

    # Reference summaries
    ref_summaries = load_reference_summaries(project_root)
    if ref_summaries:
        sections.append(ref_summaries)

    # Revision mode additions
    if revision_mode:
        try:
            spec_content = load_stakeholder_spec(project_root)
            sections.append("## Current Stakeholder Spec\n")
            sections.append(spec_content)
        except FileNotFoundError:
            pass

        if critique:
            sections.append("## Critique Triggering This Revision\n")
            sections.append(critique)

    # Ledger
    ledger_text = load_ledger_content(project_root, "stakeholder_dialog")
    if ledger_text:
        sections.append("## Conversation History\n")
        sections.append(ledger_text)

    # Extra context (excluding already-handled keys)
    _append_extra_context(
        sections,
        {k: v for k, v in extra.items()
         if k not in ("revision_mode", "critique", "current_spec")},
    )

    prompt = "\n\n".join(sections)

    # Inject hint
    if hint_content:
        state = _try_load_state(project_root)
        prompt = _inject_hint(
            prompt, hint_content, agent_type="stakeholder_dialog",
            gate_id="spec_revision" if revision_mode else "stakeholder_dialog",
            stage=state.stage if state else "1",
        )

    return prompt


def _assemble_blueprint_author(
    project_root: Path,
    hint_content: Optional[str] = None,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for blueprint_author."""
    extra = extra_context or {}
    checker_feedback = extra.get("checker_feedback", "")
    revision_mode = extra.get("revision_mode", False)

    sections: List[str] = []
    if revision_mode:
        sections.append("# Blueprint Author Task Prompt (Revision Mode)\n")
        sections.append(
            "You are revising an existing blueprint based on human feedback. "
            "Address the identified issues without reopening settled topics. "
            "Your terminal status line must be: BLUEPRINT_REVISION_COMPLETE\n"
        )
    else:
        sections.append("# Blueprint Author Task Prompt\n")

    # Stakeholder spec -- required for blueprint_author
    spec_content = load_stakeholder_spec(project_root)
    sections.append("## Stakeholder Spec\n")
    sections.append(spec_content)

    # Reference summaries
    ref_summaries = load_reference_summaries(project_root)
    if ref_summaries:
        sections.append(ref_summaries)

    # In revision mode, include the current blueprint being revised
    if revision_mode:
        blueprint_path = project_root / "blueprint" / "blueprint.md"
        if blueprint_path.exists():
            sections.append("## Current Blueprint (to revise)\n")
            sections.append(blueprint_path.read_text(encoding="utf-8"))

    # Checker feedback
    if checker_feedback:
        sections.append("## Checker Feedback\n")
        sections.append(checker_feedback)

    # Ledger
    ledger_text = load_ledger_content(project_root, "blueprint_dialog")
    if ledger_text:
        sections.append("## Conversation History\n")
        sections.append(ledger_text)

    # Extra context (excluding already-handled keys)
    _append_extra_context(
        sections,
        {k: v for k, v in extra.items() if k not in ("checker_feedback",)},
    )

    prompt = "\n\n".join(sections)

    # Inject hint
    if hint_content:
        state = _try_load_state(project_root)
        prompt = _inject_hint(
            prompt, hint_content, agent_type="blueprint_author",
            gate_id="blueprint_authoring",
            stage=state.stage if state else "2",
        )

    return prompt


def _assemble_blueprint_checker(
    project_root: Path,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for blueprint_checker."""
    sections: List[str] = []
    sections.append("# Blueprint Alignment Check Task Prompt\n")

    # Stakeholder spec (with working notes)
    try:
        spec_content = load_stakeholder_spec(project_root)
        sections.append("## Stakeholder Spec\n")
        sections.append(spec_content)
    except FileNotFoundError:
        pass

    # Blueprint -- required for blueprint_checker
    blueprint_content = load_blueprint(project_root)
    sections.append("## Blueprint\n")
    sections.append(blueprint_content)

    # Reference summaries
    ref_summaries = load_reference_summaries(project_root)
    if ref_summaries:
        sections.append(ref_summaries)

    # Extra context
    _append_extra_context(sections, extra_context)

    return "\n\n".join(sections)


def _assemble_blueprint_reviewer(
    project_root: Path,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for blueprint_reviewer."""
    sections: List[str] = []
    sections.append("# Blueprint Review Task Prompt\n")

    # Blueprint
    blueprint_path = project_root / "blueprint" / "blueprint.md"
    if blueprint_path.exists():
        sections.append("## Blueprint\n")
        sections.append(_read_file(blueprint_path))

    # Stakeholder spec
    try:
        spec_content = load_stakeholder_spec(project_root)
        sections.append("## Stakeholder Spec\n")
        sections.append(spec_content)
    except FileNotFoundError:
        pass

    # Project context
    project_context = load_project_context(project_root)
    if project_context:
        sections.append("## Project Context\n")
        sections.append(project_context)

    # Reference summaries
    ref_summaries = load_reference_summaries(project_root)
    if ref_summaries:
        sections.append(ref_summaries)

    # Extra context
    _append_extra_context(sections, extra_context)

    return "\n\n".join(sections)


def _assemble_stakeholder_reviewer(
    project_root: Path,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for stakeholder_reviewer."""
    sections: List[str] = []
    sections.append("# Stakeholder Spec Review Task Prompt\n")

    # Stakeholder spec
    try:
        spec_content = load_stakeholder_spec(project_root)
        sections.append("## Stakeholder Spec\n")
        sections.append(spec_content)
    except FileNotFoundError:
        pass

    # Project context
    project_context = load_project_context(project_root)
    if project_context:
        sections.append("## Project Context\n")
        sections.append(project_context)

    # Reference summaries
    ref_summaries = load_reference_summaries(project_root)
    if ref_summaries:
        sections.append(ref_summaries)

    # Extra context
    _append_extra_context(sections, extra_context)

    return "\n\n".join(sections)


def _assemble_test_agent(
    project_root: Path,
    unit_number: int,
    hint_content: Optional[str] = None,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for test_agent."""
    sections: List[str] = []
    sections.append(f"# Test Agent Task Prompt -- Unit {unit_number}\n")

    blueprint_path = project_root / "blueprint" / "blueprint.md"

    # Unit definition (will raise FileNotFoundError if blueprint missing)
    unit_def = _extract_unit_checked(blueprint_path, unit_number)
    sections.append("## Unit Definition\n")
    sections.append(_format_unit_definition(unit_def))

    # Upstream contracts
    upstream = _extract_upstream_checked(blueprint_path, unit_number)
    if upstream:
        sections.append(_format_upstream_contracts(upstream))

    # Extra context
    _append_extra_context(sections, extra_context)

    prompt = "\n\n".join(sections)

    # Inject hint
    if hint_content:
        state = _try_load_state(project_root)
        prompt = _inject_hint(
            prompt, hint_content, agent_type="test_agent",
            gate_id="test_generation",
            ladder_position=state.fix_ladder_position if state else None,
            unit_number=unit_number,
            stage=state.stage if state else "3",
        )

    return prompt


def _assemble_implementation_agent(
    project_root: Path,
    unit_number: int,
    ladder_position: Optional[str] = None,
    hint_content: Optional[str] = None,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for implementation_agent."""
    extra = extra_context or {}

    sections: List[str] = []
    sections.append(f"# Implementation Agent Task Prompt -- Unit {unit_number}\n")

    if ladder_position:
        sections.append(f"**Fix Ladder Position:** {ladder_position}\n")

    blueprint_path = project_root / "blueprint" / "blueprint.md"

    # Unit definition
    unit_def = _extract_unit_checked(blueprint_path, unit_number)
    sections.append("## Unit Definition\n")
    sections.append(_format_unit_definition(unit_def))

    # Upstream contracts
    upstream = _extract_upstream_checked(blueprint_path, unit_number)
    if upstream:
        sections.append(_format_upstream_contracts(upstream))

    # At fix ladder positions, include failure context
    if ladder_position:
        # Diagnostic guidance (try multiple key names)
        diagnostic_output = extra.get("diagnostic_output", "") or extra.get("diagnostic_guidance", "")
        if diagnostic_output:
            sections.append("## Diagnostic Analysis\n")
            sections.append(diagnostic_output)

        # Prior failure output (try multiple key names)
        error_output = extra.get("error_output", "") or extra.get("prior_failure_output", "")
        if error_output:
            sections.append("## Test Failure Output\n")
            sections.append(f"```\n{error_output}\n```")

    # Extra context (excluding already-handled keys)
    handled_keys = {"diagnostic_output", "diagnostic_guidance", "error_output", "prior_failure_output"}
    _append_extra_context(
        sections,
        {k: v for k, v in extra.items() if k not in handled_keys},
    )

    prompt = "\n\n".join(sections)

    # Inject hint
    if hint_content:
        prompt = _inject_hint(
            prompt, hint_content, agent_type="implementation_agent",
            gate_id="implementation_fix",
            ladder_position=ladder_position,
            unit_number=unit_number,
            stage="3",
        )

    return prompt


def _assemble_coverage_review(
    project_root: Path,
    unit_number: int,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for coverage_review."""
    extra = extra_context or {}

    sections: List[str] = []
    sections.append(f"# Coverage Review Task Prompt -- Unit {unit_number}\n")

    blueprint_path = project_root / "blueprint" / "blueprint.md"

    # Unit definition
    unit_def = _extract_unit_checked(blueprint_path, unit_number)
    sections.append("## Unit Definition\n")
    sections.append(_format_unit_definition(unit_def))

    # Upstream contracts
    upstream = _extract_upstream_checked(blueprint_path, unit_number)
    if upstream:
        sections.append(_format_upstream_contracts(upstream))

    # Passing tests from extra_context
    passing_tests = extra.get("passing_tests", "")
    if passing_tests:
        sections.append("## Passing Tests\n")
        sections.append(passing_tests)

    # Also try loading tests from project structure
    test_dir = project_root / "tests" / f"unit_{unit_number}"
    if test_dir.is_dir():
        test_files = sorted(test_dir.glob("test_*.py"))
        if test_files:
            sections.append("## Current Test Suite (passing)\n")
            for tf in test_files:
                sections.append(f"### {tf.name}\n")
                sections.append(f"```python\n{tf.read_text(encoding='utf-8')}\n```")

    # Extra context (excluding already-handled keys)
    _append_extra_context(
        sections,
        {k: v for k, v in extra.items() if k not in ("passing_tests",)},
    )

    return "\n\n".join(sections)


def _assemble_diagnostic_agent(
    project_root: Path,
    unit_number: int,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for diagnostic_agent."""
    extra = extra_context or {}

    sections: List[str] = []
    sections.append(f"# Diagnostic Agent Task Prompt -- Unit {unit_number}\n")

    # Stakeholder spec
    try:
        spec_content = load_stakeholder_spec(project_root)
        sections.append("## Stakeholder Spec\n")
        sections.append(spec_content)
    except FileNotFoundError:
        pass

    # Unit blueprint section
    blueprint_path = project_root / "blueprint" / "blueprint.md"
    unit_def = _extract_unit_checked(blueprint_path, unit_number)
    sections.append("## Unit Definition (from Blueprint)\n")
    sections.append(_format_unit_definition(unit_def))

    # Upstream contracts
    upstream = _extract_upstream_checked(blueprint_path, unit_number)
    if upstream:
        sections.append(_format_upstream_contracts(upstream))

    # Failing tests
    test_code = extra.get("test_code", "") or extra.get("failing_tests", "")
    if test_code:
        sections.append("## Test Code\n")
        sections.append(f"```python\n{test_code}\n```")
    else:
        test_dir = project_root / "tests" / f"unit_{unit_number}"
        if test_dir.is_dir():
            test_files = sorted(test_dir.glob("test_*.py"))
            if test_files:
                sections.append("## Test Code\n")
                for tf in test_files:
                    sections.append(f"### {tf.name}\n")
                    sections.append(f"```python\n{tf.read_text(encoding='utf-8')}\n```")

    # Error output
    error_output = extra.get("error_output", "")
    if error_output:
        sections.append("## Error Output from Test Run\n")
        sections.append(f"```\n{error_output}\n```")

    # Failing implementation
    impl_code = extra.get("impl_code", "") or extra.get("failing_implementations", "")
    if impl_code:
        sections.append("## Failing Implementation Code\n")
        sections.append(f"```python\n{impl_code}\n```")
    else:
        impl_dir = project_root / "src" / f"unit_{unit_number}"
        if impl_dir.is_dir():
            impl_files = sorted(impl_dir.glob("*.py"))
            if impl_files:
                sections.append("## Failing Implementation Code\n")
                for f in impl_files:
                    sections.append(f"### {f.name}\n")
                    sections.append(f"```python\n{f.read_text(encoding='utf-8')}\n```")

    # Extra context (excluding already-handled keys)
    handled_keys = {"test_code", "failing_tests", "error_output", "impl_code", "failing_implementations"}
    _append_extra_context(
        sections,
        {k: v for k, v in extra.items() if k not in handled_keys},
    )

    return "\n\n".join(sections)


def _assemble_integration_test_author(
    project_root: Path,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for integration_test_author."""
    sections: List[str] = []
    sections.append("# Integration Test Author Task Prompt\n")

    # Stakeholder spec
    try:
        spec_content = load_stakeholder_spec(project_root)
        sections.append("## Stakeholder Spec\n")
        sections.append(spec_content)
    except FileNotFoundError:
        pass

    # Contract signatures from all units
    blueprint_path = project_root / "blueprint" / "blueprint.md"
    if blueprint_path.exists():
        try:
            all_units = parse_blueprint(blueprint_path)
            sections.append("## All Unit Contract Signatures\n")
            for unit_def in all_units:
                sections.append(
                    f"### Unit {unit_def.unit_number}: {unit_def.unit_name}\n"
                )
                if unit_def.signatures:
                    sections.append(f"```python\n{unit_def.signatures}\n```")
        except (ValueError, FileNotFoundError):
            pass

    # Extra context
    _append_extra_context(sections, extra_context)

    return "\n\n".join(sections)


def _assemble_git_repo_agent(
    project_root: Path,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for git_repo_agent."""
    extra = extra_context or {}

    sections: List[str] = []
    sections.append("# Git Repo Agent Task Prompt\n")

    # All verified artifacts - stakeholder spec
    try:
        spec_content = load_stakeholder_spec(project_root)
        sections.append("## Stakeholder Spec\n")
        sections.append(spec_content)
    except FileNotFoundError:
        pass

    # Blueprint
    blueprint_path = project_root / "blueprint" / "blueprint.md"
    if blueprint_path.exists():
        sections.append("## Blueprint\n")
        sections.append(_read_file(blueprint_path))

    # Project context
    project_context = load_project_context(project_root)
    if project_context:
        sections.append("## Project Context\n")
        sections.append(project_context)

    # Reference documents
    ref_summaries = load_reference_summaries(project_root)
    if ref_summaries:
        sections.append(ref_summaries)

    # Pipeline state summary
    state = _try_load_state(project_root)
    if state:
        sections.append("## Project Summary\n")
        sections.append(_build_project_summary(state))

    # Error output (fix cycle)
    error_output = extra.get("error_output", "")
    if error_output:
        sections.append("## Error Output from Prior Assembly Attempt\n")
        sections.append(f"```\n{error_output}\n```")

    # Extra context (excluding already-handled keys)
    _append_extra_context(
        sections,
        {k: v for k, v in extra.items() if k not in ("error_output",)},
    )

    return "\n\n".join(sections)


def _assemble_help_agent(
    project_root: Path,
    gate_id: Optional[str] = None,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for help_agent."""
    extra = extra_context or {}
    gate_invocation = bool(extra.get("gate_invocation", False))
    extra_gate_id = extra.get("gate_id")

    sections: List[str] = []
    sections.append("# Help Agent Task Prompt\n")

    # Project summary
    state = _try_load_state(project_root)
    if state:
        sections.append("## Project Summary\n")
        sections.append(_build_project_summary(state))

    # Stakeholder spec
    sections.append("## Stakeholder Spec\n")
    try:
        spec_content = load_stakeholder_spec(project_root)
        sections.append(spec_content)
    except FileNotFoundError:
        sections.append("*Stakeholder spec not yet created.*")

    # Blueprint
    sections.append("## Blueprint\n")
    blueprint_path = project_root / "blueprint" / "blueprint.md"
    if blueprint_path.exists():
        sections.append(_read_file(blueprint_path))
    else:
        sections.append("*Blueprint not yet created.*")

    # Gate-invocation mode extras (from gate_id parameter or extra_context)
    effective_gate_id = gate_id or extra_gate_id
    if gate_invocation or effective_gate_id:
        sections.append("## Gate Invocation Context\n")
        sections.append("**This help session was invoked at a decision gate.**")
        if effective_gate_id:
            sections.append(f"**Gate ID:** {effective_gate_id}")

    # Extra context (excluding already-handled keys)
    _append_extra_context(
        sections,
        {k: v for k, v in extra.items() if k not in ("gate_invocation", "gate_id")},
    )

    return "\n\n".join(sections)


def _assemble_hint_agent(
    project_root: Path,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for hint_agent."""
    sections: List[str] = []
    sections.append("# Hint Agent Task Prompt\n")

    # Logs (ledger content)
    ledger_text = load_ledger_content(project_root, "hint_session")
    if ledger_text:
        sections.append("## Hint Session History\n")
        sections.append(ledger_text)

    # Documents and spec
    try:
        spec_content = load_stakeholder_spec(project_root)
        sections.append("## Stakeholder Spec\n")
        sections.append(spec_content)
    except FileNotFoundError:
        pass

    # Blueprint
    blueprint_path = project_root / "blueprint" / "blueprint.md"
    if blueprint_path.exists():
        sections.append("## Blueprint\n")
        sections.append(_read_file(blueprint_path))

    # Extra context
    _append_extra_context(sections, extra_context)

    return "\n\n".join(sections)


def _assemble_redo_agent(
    project_root: Path,
    unit_number: Optional[int] = None,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for redo_agent."""
    extra = extra_context or {}
    human_description = extra.get("human_description", "") or extra.get("human_error_description", "")

    sections: List[str] = []
    sections.append("# Redo Agent Task Prompt\n")

    # Pipeline state summary
    state = _try_load_state(project_root)
    if state:
        sections.append("## Current Pipeline State\n")
        sections.append(_build_project_summary(state))

    # Human error description
    if human_description:
        sections.append("## Human Description\n")
        sections.append(human_description)

    # Current unit definition
    if unit_number is not None and unit_number >= 1:
        blueprint_path = project_root / "blueprint" / "blueprint.md"
        if blueprint_path.exists():
            try:
                unit_def = _extract_unit_checked(blueprint_path, unit_number)
                sections.append(f"## Unit {unit_number} Definition\n")
                sections.append(_format_unit_definition(unit_def))
            except (ValueError, FileNotFoundError):
                pass

    # Extra context (excluding already-handled keys)
    _append_extra_context(
        sections,
        {k: v for k, v in extra.items()
         if k not in ("human_description", "human_error_description")},
    )

    return "\n\n".join(sections)


def _assemble_reference_indexing(
    project_root: Path,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for reference_indexing."""
    extra = extra_context or {}
    reference_path = extra.get("reference_path", "") or extra.get("reference_document", "")
    reference_type = extra.get("reference_type", "text")

    sections: List[str] = []
    sections.append("# Reference Indexing Task Prompt\n")

    if reference_path:
        sections.append(f"**Reference Path:** {reference_path}")
        sections.append(f"**Reference Type:** {reference_type}")

        ref_path = Path(reference_path)
        if ref_path.exists() and reference_type in ("markdown", "text"):
            try:
                content = ref_path.read_text(encoding="utf-8")
                sections.append("## Document Content\n")
                sections.append(content)
            except (UnicodeDecodeError, OSError):
                pass

    # Extra context (excluding already-handled keys)
    _append_extra_context(
        sections,
        {k: v for k, v in extra.items()
         if k not in ("reference_path", "reference_document", "reference_type")},
    )

    return "\n\n".join(sections)


def _assemble_bug_triage(
    project_root: Path,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for bug_triage."""
    extra = extra_context or {}

    sections: List[str] = []
    sections.append("# Bug Triage Task Prompt\n")

    # Stakeholder spec
    try:
        spec_content = load_stakeholder_spec(project_root)
        sections.append("## Stakeholder Spec\n")
        sections.append(spec_content)
    except FileNotFoundError:
        pass

    # Blueprint
    blueprint_path = project_root / "blueprint" / "blueprint.md"
    if blueprint_path.exists():
        sections.append("## Blueprint\n")
        sections.append(_read_file(blueprint_path))

    # Source code paths
    src_dir = project_root / "src"
    if src_dir.is_dir():
        src_paths = sorted(str(p) for p in src_dir.rglob("*.py") if p.is_file())
        if src_paths:
            sections.append("## Source Code Paths\n")
            sections.append("\n".join(f"- `{p}`" for p in src_paths))

    # Test suite paths
    tests_dir = project_root / "tests"
    if tests_dir.is_dir():
        test_paths = sorted(str(p) for p in tests_dir.rglob("*.py") if p.is_file())
        if test_paths:
            sections.append("## Test Suite Paths\n")
            sections.append("\n".join(f"- `{p}`" for p in test_paths))

    # Ledger
    ledger_text = load_ledger_content(project_root, "bug_triage")
    if ledger_text:
        sections.append("## Bug Triage Ledger\n")
        sections.append(ledger_text)

    # Extra context (excluding already-handled keys)
    _append_extra_context(
        sections,
        {k: v for k, v in extra.items()
         if k not in ("source_code_paths", "test_suite_paths")},
    )

    return "\n\n".join(sections)


def _assemble_repair_agent(
    project_root: Path,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble task prompt for repair_agent."""
    extra = extra_context or {}

    sections: List[str] = []
    sections.append("# Repair Agent Task Prompt\n")

    # Build/environment error diagnosis
    error_output = extra.get("error_output", "") or extra.get("error_diagnosis", "")
    if error_output:
        sections.append("## Build/Environment Error Diagnosis\n")
        sections.append(f"```\n{error_output}\n```")

    # Environment state
    env_state = extra.get("environment_state", "")
    if env_state:
        sections.append("## Environment State\n")
        sections.append(env_state)

    state = _try_load_state(project_root)
    if state:
        sections.append("## Pipeline State\n")
        sections.append(_build_project_summary(state))

    # Extra context (excluding already-handled keys)
    _append_extra_context(
        sections,
        {k: v for k, v in extra.items()
         if k not in ("error_output", "error_diagnosis", "environment_state")},
    )

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Gate-specific assemblers
# ---------------------------------------------------------------------------

def _assemble_test_validation_gate(
    project_root: Path,
    gate_id: str,
    unit_number: Optional[int] = None,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble gate prompt for test_validation gates."""
    extra = extra_context or {}
    diagnostic_output = extra.get("diagnostic_output", "") or extra.get("diagnostic_analysis", "")

    sections: List[str] = []
    unit_label = f" -- Unit {unit_number}" if unit_number else ""
    sections.append(f"# Test Validation Gate{unit_label}\n")
    sections.append(f"**Gate ID:** {gate_id}\n")

    sections.append("## What Happened\n")
    sections.append(
        "The green run failed. The tests ran against the implementation "
        "and at least one test did not pass. A diagnostic agent has analyzed the failure.\n"
    )

    if diagnostic_output:
        sections.append("## Diagnostic Analysis\n")
        sections.append(diagnostic_output)

    sections.append("## Your Decision\n")
    sections.append(
        "Please choose one:\n"
        "  -> **TEST CORRECT** -- the test is right, the implementation needs fixing\n"
        "  -> **TEST WRONG** -- the test doesn't match my requirements\n"
        "  -> **HELP** -- discuss this with the help agent before deciding"
    )

    return "\n\n".join(sections)


def _assemble_diagnostic_gate(
    project_root: Path,
    gate_id: str,
    unit_number: Optional[int] = None,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble gate prompt for diagnostic escalation gates."""
    extra = extra_context or {}
    diagnostic_output = extra.get("diagnostic_output", "") or extra.get("diagnostic_analysis", "")

    sections: List[str] = []
    unit_label = f" -- Unit {unit_number}" if unit_number else ""
    sections.append(f"# Diagnostic Escalation Gate{unit_label}\n")
    sections.append(f"**Gate ID:** {gate_id}\n")

    sections.append("## What Happened\n")
    sections.append(
        "Multiple implementation attempts have failed. "
        "The diagnostic agent has performed a three-hypothesis analysis.\n"
    )

    if diagnostic_output:
        sections.append("## Diagnostic Analysis\n")
        sections.append(diagnostic_output)

    sections.append("## Your Decision\n")
    sections.append(
        "Please choose one:\n"
        "  -> **FIX IMPLEMENTATION** -- one fresh agent attempt with diagnostic guidance\n"
        "  -> **FIX DOCUMENT** -- the spec or blueprint needs revision\n"
        "  -> **HELP** -- discuss this with the help agent before deciding"
    )

    return "\n\n".join(sections)


def _assemble_spec_approval_gate(
    project_root: Path,
    gate_id: str,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble gate prompt for spec_approval gates."""
    sections: List[str] = []
    sections.append("# Stakeholder Spec Approval Gate\n")
    sections.append(f"**Gate ID:** {gate_id}\n")

    sections.append("## The Spec\n")
    sections.append(
        "The stakeholder spec has been drafted and is ready for your review. "
        "Please read the document at `specs/stakeholder_spec.md` carefully.\n"
    )

    state = _try_load_state(project_root)
    if state:
        sections.append("## Pipeline Context\n")
        sections.append(_build_project_summary(state))

    sections.append("## Your Decision\n")
    sections.append(
        "Please choose one:\n"
        "  -> **APPROVE** -- the spec is correct and complete\n"
        "  -> **REVISE** -- the spec needs changes\n"
        "  -> **FRESH REVIEW** -- request an independent review\n"
        "  -> **HELP** -- discuss this with the help agent before deciding"
    )

    return "\n\n".join(sections)


def _assemble_blueprint_approval_gate(
    project_root: Path,
    gate_id: str,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble gate prompt for blueprint_approval gates."""
    sections: List[str] = []
    sections.append("# Blueprint Approval Gate\n")
    sections.append(f"**Gate ID:** {gate_id}\n")

    sections.append("## The Blueprint\n")
    sections.append(
        "The blueprint has passed alignment checking and is ready for your review. "
        "Please read the document at `blueprint/blueprint.md` carefully.\n"
    )

    state = _try_load_state(project_root)
    if state:
        sections.append("## Pipeline Context\n")
        sections.append(_build_project_summary(state))

    sections.append("## Your Decision\n")
    sections.append(
        "Please choose one:\n"
        "  -> **APPROVE** -- the blueprint is correct and well-structured\n"
        "  -> **REVISE** -- the blueprint needs changes\n"
        "  -> **FRESH REVIEW** -- request an independent review\n"
        "  -> **HELP** -- discuss this with the help agent before deciding"
    )

    return "\n\n".join(sections)


def _assemble_hook_activation_gate(
    project_root: Path,
    gate_id: str,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble gate prompt for hook_activation."""
    sections: List[str] = []
    sections.append("# Hook Activation Gate\n")
    sections.append(f"**Gate ID:** {gate_id}\n")

    sections.append("## What To Do\n")
    sections.append(
        "SVP uses hooks to protect your project files. Before proceeding, you need to "
        "review and activate the hook configuration.\n\n"
        "1. Open Claude Code's hooks menu by typing `/hooks`\n"
        "2. Review the SVP hook configuration\n"
        "3. Activate the hooks\n"
    )

    sections.append("## Your Decision\n")
    sections.append(
        "Please choose one:\n"
        "  -> **HOOKS ACTIVATED** -- I have reviewed and activated the hooks\n"
        "  -> **HELP** -- I need assistance with hook activation"
    )

    return "\n\n".join(sections)


def _assemble_integration_failure_gate(
    project_root: Path,
    gate_id: str,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble gate prompt for integration_failure."""
    extra = extra_context or {}
    diagnostic_output = extra.get("diagnostic_output", "") or extra.get("diagnostic_analysis", "")

    sections: List[str] = []
    sections.append("# Integration Test Failure Gate\n")
    sections.append(f"**Gate ID:** {gate_id}\n")

    sections.append("## What Happened\n")
    sections.append(
        "Integration tests have failed. The diagnostic agent has analyzed the failure.\n"
    )

    if diagnostic_output:
        sections.append("## Diagnostic Analysis\n")
        sections.append(diagnostic_output)

    sections.append("## Your Decision\n")
    sections.append(
        "Please choose one:\n"
        "  -> **ASSEMBLY FIX** -- the units are correct individually, but their assembly "
        "has a localized error\n"
        "  -> **DOCUMENT FIX** -- the blueprint's contracts need correction\n"
        "  -> **HELP** -- discuss this with the help agent before deciding"
    )

    return "\n\n".join(sections)


def _assemble_repo_test_gate(
    project_root: Path,
    gate_id: str,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble gate prompt for repo_test."""
    extra = extra_context or {}
    test_command = extra.get("test_command", "pytest")

    sections: List[str] = []
    sections.append("# Repository Test Gate\n")
    sections.append(f"**Gate ID:** {gate_id}\n")

    sections.append("## What To Do\n")
    sections.append(
        "The git repository has been assembled. Please run the following test command "
        "in your terminal to verify it works:\n\n"
        f"```\n{test_command}\n```\n"
    )

    sections.append("## Your Decision\n")
    sections.append(
        "Please choose one:\n"
        "  -> **TESTS PASSED** -- all tests pass in the delivered repository\n"
        "  -> **TESTS FAILED** -- tests failed (please paste the error output)\n"
        "  -> **HELP** -- I need assistance with running the tests"
    )

    return "\n\n".join(sections)


def _assemble_context_approval_gate(
    project_root: Path,
    gate_id: str,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble gate prompt for context_approval."""
    sections: List[str] = []
    sections.append("# Context Approval Gate\n")
    sections.append(f"**Gate ID:** {gate_id}\n")

    sections.append("## What Happened\n")
    sections.append(
        "The project context has been set up. Please review the project context "
        "and confirm it is correct.\n"
    )

    # Project context
    project_context = load_project_context(project_root)
    if project_context:
        sections.append("## Project Context\n")
        sections.append(project_context)

    sections.append("## Your Decision\n")
    sections.append(
        "Please choose one:\n"
        "  -> **APPROVE** -- the project context is correct\n"
        "  -> **REVISE** -- the project context needs changes\n"
        "  -> **HELP** -- discuss this with the help agent before deciding"
    )

    return "\n\n".join(sections)


def _assemble_debug_permission_gate(
    project_root: Path,
    gate_id: str,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble gate prompt for debug_permission."""
    sections: List[str] = []
    sections.append("# Debug Permission Gate\n")
    sections.append(f"**Gate ID:** {gate_id}\n")

    sections.append("## What Happened\n")
    sections.append(
        "A post-delivery bug has been reported. The pipeline needs your authorization "
        "to investigate and potentially modify delivered code.\n"
    )

    sections.append("## Your Decision\n")
    sections.append(
        "Please choose one:\n"
        "  -> **AUTHORIZE DEBUG** -- proceed with the debug investigation\n"
        "  -> **DENY** -- do not investigate this bug\n"
        "  -> **HELP** -- discuss this with the help agent before deciding"
    )

    return "\n\n".join(sections)


def _assemble_regression_test_gate(
    project_root: Path,
    gate_id: str,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble gate prompt for regression_test."""
    sections: List[str] = []
    sections.append("# Regression Test Gate\n")
    sections.append(f"**Gate ID:** {gate_id}\n")

    sections.append("## What Happened\n")
    sections.append(
        "A regression test has been generated for the reported bug. "
        "Please review the test to confirm it correctly captures the bug.\n"
    )

    sections.append("## Your Decision\n")
    sections.append(
        "Please choose one:\n"
        "  -> **APPROVE** -- the regression test correctly captures the bug\n"
        "  -> **REVISE** -- the regression test needs changes\n"
        "  -> **HELP** -- discuss this with the help agent before deciding"
    )

    return "\n\n".join(sections)


def _assemble_debug_classification_gate(
    project_root: Path,
    gate_id: str,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble gate prompt for debug_classification."""
    sections: List[str] = []
    sections.append("# Debug Classification Gate\n")
    sections.append(f"**Gate ID:** {gate_id}\n")

    sections.append("## What Happened\n")
    sections.append(
        "The bug triage agent has classified the bug. "
        "Please review the classification and decide how to proceed.\n"
    )

    sections.append("## Your Decision\n")
    sections.append(
        "Please choose one:\n"
        "  -> **ACCEPT CLASSIFICATION** -- proceed with the recommended fix approach\n"
        "  -> **RECLASSIFY** -- the classification is incorrect\n"
        "  -> **HELP** -- discuss this with the help agent before deciding"
    )

    return "\n\n".join(sections)


def _assemble_generic_gate(
    project_root: Path,
    gate_id: str,
    unit_number: Optional[int] = None,
    extra_context: Optional[Dict[str, str]] = None,
) -> str:
    """Assemble a generic gate prompt for any unspecialized gate."""
    sections: List[str] = []
    unit_label = f" -- Unit {unit_number}" if unit_number else ""
    sections.append(f"# Decision Gate{unit_label}\n")
    sections.append(f"**Gate ID:** {gate_id}\n")

    sections.append("## Context\n")
    sections.append(
        "A decision point has been reached in the pipeline. "
        "Please review the current state and make your decision.\n"
    )

    state = _try_load_state(project_root)
    if state:
        sections.append("## Pipeline State\n")
        sections.append(_build_project_summary(state))

    sections.append("## Your Decision\n")
    sections.append(
        "Please choose the appropriate response option for this gate."
    )

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Core public functions
# ---------------------------------------------------------------------------

def prepare_agent_task(
    project_root: Path,
    agent_type: str,
    unit_number: Optional[int] = None,
    ladder_position: Optional[str] = None,
    hint_content: Optional[str] = None,
    gate_id: Optional[str] = None,
    extra_context: Optional[Dict[str, str]] = None,
) -> Path:
    """Assemble a task prompt file at .svp/task_prompt.md and return its path.

    The content varies by agent type per the behavioral contracts.
    When hint_content is provided, delegates to Unit 8 (Hint Prompt Assembler)
    to produce the wrapped hint block and includes it in the task prompt.
    """
    assert project_root.is_dir(), "Project root must exist"

    if agent_type not in KNOWN_AGENT_TYPES:
        raise ValueError(f"Unknown agent type: {agent_type}")

    # Check if unit number is required
    if agent_type in UNIT_REQUIRED_AGENTS and unit_number is None:
        raise ValueError(f"Unit number required for agent type {agent_type}")

    if extra_context is None:
        extra_context = {}

    # Dispatch to agent-specific assembler
    assembler_map = {
        "setup_agent": lambda: _assemble_setup_agent(project_root, extra_context),
        "stakeholder_dialog": lambda: _assemble_stakeholder_dialog(
            project_root, hint_content, extra_context,
        ),
        "blueprint_author": lambda: _assemble_blueprint_author(
            project_root, hint_content, extra_context,
        ),
        "blueprint_checker": lambda: _assemble_blueprint_checker(
            project_root, extra_context,
        ),
        "blueprint_reviewer": lambda: _assemble_blueprint_reviewer(
            project_root, extra_context,
        ),
        "stakeholder_reviewer": lambda: _assemble_stakeholder_reviewer(
            project_root, extra_context,
        ),
        "test_agent": lambda: _assemble_test_agent(
            project_root, unit_number, hint_content, extra_context,
        ),
        "implementation_agent": lambda: _assemble_implementation_agent(
            project_root, unit_number, ladder_position, hint_content, extra_context,
        ),
        "coverage_review": lambda: _assemble_coverage_review(
            project_root, unit_number, extra_context,
        ),
        "diagnostic_agent": lambda: _assemble_diagnostic_agent(
            project_root, unit_number, extra_context,
        ),
        "integration_test_author": lambda: _assemble_integration_test_author(
            project_root, extra_context,
        ),
        "git_repo_agent": lambda: _assemble_git_repo_agent(
            project_root, extra_context,
        ),
        "help_agent": lambda: _assemble_help_agent(project_root, gate_id, extra_context),
        "hint_agent": lambda: _assemble_hint_agent(project_root, extra_context),
        "redo_agent": lambda: _assemble_redo_agent(
            project_root, unit_number, extra_context,
        ),
        "reference_indexing": lambda: _assemble_reference_indexing(
            project_root, extra_context,
        ),
        "bug_triage": lambda: _assemble_bug_triage(project_root, extra_context),
        "repair_agent": lambda: _assemble_repair_agent(project_root, extra_context),
    }

    content = assembler_map[agent_type]()

    # Write to .svp/task_prompt.md
    svp_dir = project_root / ".svp"
    svp_dir.mkdir(parents=True, exist_ok=True)
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
    """Assemble a gate prompt file at .svp/gate_prompt.md and return its path.

    Includes the gate description, explicit response options, and relevant
    context (e.g., diagnostic analysis for test validation gates).
    """
    assert project_root.is_dir(), "Project root must exist"

    if gate_id not in KNOWN_GATE_IDS:
        raise ValueError(f"Unknown gate ID: {gate_id}")

    if extra_context is None:
        extra_context = {}

    # Determine the gate category to dispatch to the right assembler
    gate_category = _GATE_CATEGORY_MAP.get(gate_id, "generic")

    category_map = {
        "test_validation": lambda: _assemble_test_validation_gate(
            project_root, gate_id, unit_number, extra_context,
        ),
        "diagnostic": lambda: _assemble_diagnostic_gate(
            project_root, gate_id, unit_number, extra_context,
        ),
        "spec_approval": lambda: _assemble_spec_approval_gate(
            project_root, gate_id, extra_context,
        ),
        "blueprint_approval": lambda: _assemble_blueprint_approval_gate(
            project_root, gate_id, extra_context,
        ),
        "hook_activation": lambda: _assemble_hook_activation_gate(
            project_root, gate_id, extra_context,
        ),
        "integration_failure": lambda: _assemble_integration_failure_gate(
            project_root, gate_id, extra_context,
        ),
        "repo_test": lambda: _assemble_repo_test_gate(
            project_root, gate_id, extra_context,
        ),
        "context_approval": lambda: _assemble_context_approval_gate(
            project_root, gate_id, extra_context,
        ),
        "debug_permission": lambda: _assemble_debug_permission_gate(
            project_root, gate_id, extra_context,
        ),
        "regression_test": lambda: _assemble_regression_test_gate(
            project_root, gate_id, extra_context,
        ),
        "debug_classification": lambda: _assemble_debug_classification_gate(
            project_root, gate_id, extra_context,
        ),
        "generic": lambda: _assemble_generic_gate(
            project_root, gate_id, unit_number, extra_context,
        ),
    }

    assembler = category_map.get(gate_category, category_map["generic"])
    content = assembler()

    # Write to .svp/gate_prompt.md
    svp_dir = project_root / ".svp"
    svp_dir.mkdir(parents=True, exist_ok=True)
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
    parser = argparse.ArgumentParser(
        description="SVP Preparation Script -- assembles task prompts and gate prompts."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--agent", type=str, help="Agent type to prepare a task prompt for.")
    group.add_argument("--gate", type=str, help="Gate ID to prepare a gate prompt for.")

    parser.add_argument("--project-root", type=str, required=True,
                        help="Path to the project workspace root.")
    parser.add_argument("--unit", type=int, default=None,
                        help="Unit number (required for unit-specific agents).")
    parser.add_argument("--ladder-position", type=str, default=None,
                        help="Fix ladder position.")
    parser.add_argument("--hint", type=str, default=None,
                        help="Hint content string.")
    parser.add_argument("--hint-file", type=str, default=None,
                        help="Path to a file containing hint content.")
    parser.add_argument("--gate-id", type=str, default=None,
                        help="Gate ID for context (help agent gate mode).")
    parser.add_argument("--output", type=str, default=None,
                        help="Override output path for the assembled prompt file.")
    parser.add_argument("--revision-mode", action="store_true", default=False,
                        help="Enable revision mode (for stakeholder dialog and blueprint author).")

    args = parser.parse_args()
    project_root = Path(args.project_root)

    if not project_root.is_dir():
        print(f"Error: Project root does not exist: {project_root}", file=sys.stderr)
        sys.exit(1)

    # Load hint content
    hint_content = args.hint
    if args.hint_file:
        hint_path = Path(args.hint_file)
        if hint_path.exists():
            hint_content = hint_path.read_text(encoding="utf-8").strip()

    # Build extra_context from CLI flags
    extra_context: Dict[str, str] = {}
    if args.revision_mode:
        extra_context["revision_mode"] = True

    try:
        if args.agent:
            result = prepare_agent_task(
                project_root=project_root,
                agent_type=args.agent,
                unit_number=args.unit,
                ladder_position=args.ladder_position,
                hint_content=hint_content,
                gate_id=args.gate_id,
                extra_context=extra_context if extra_context else None,
            )
        else:
            result = prepare_gate_prompt(
                project_root=project_root,
                gate_id=args.gate,
                unit_number=args.unit,
            )

        # If --output specified and differs from default, move the file
        if args.output:
            output_path = Path(args.output)
            if not output_path.is_absolute():
                output_path = project_root / output_path
            if output_path.resolve() != result.resolve():
                import shutil
                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(result), str(output_path))
                result = output_path

        print(f"Task prompt written to: {result}")
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

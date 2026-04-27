"""Unit 13: Task Preparation.

Assembles task prompts and gate prompts for all agents. Reads the blueprint,
profile, toolchain, pipeline state, ledgers, and reference documents, then
produces structured task prompt files and gate prompt files.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_scripts_dir = str(Path(__file__).resolve().parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from svp_config import ARTIFACT_FILENAMES, get_blueprint_dir
from language_registry import LANGUAGE_REGISTRY
from profile_schema import load_profile
from pipeline_state import (
    PipelineState,
    _requires_statistical_analysis,
    load_state,
)
from ledger_manager import get_ledger_path, read_ledger
from blueprint_extractor import build_unit_context as _build_unit_context_raw
from blueprint_extractor import extract_units
from hint_prompt_assembler import assemble_hint_prompt
from routing import _expected_terminal_status_for

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALL_GATE_IDS: List[str] = [
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
    "gate_3_completion_failure",
    "gate_4_1_integration_failure",
    "gate_4_1a",
    "gate_4_2_assembly_exhausted",
    "gate_4_3_adaptation_review",
    "gate_5_1_repo_test",
    "gate_5_2_assembly_exhausted",
    "gate_5_3_unused_functions",
    "gate_6_0_debug_permission",
    "gate_6_1_regression_test",
    "gate_6_1a_divergence_warning",
    "gate_6_2_debug_classification",
    "gate_6_3_repair_exhausted",
    "gate_6_4_non_reproducible",
    "gate_6_5_debug_commit",
    "gate_hint_conflict",
    "gate_7_a_trajectory_review",
    "gate_7_b_fix_plan_review",
    "gate_pass_transition_post_pass1",
    "gate_pass_transition_post_pass2",
]

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
    "checklist_generation",
    "regression_adaptation",
    "oracle_agent",
]

SELECTIVE_LOADING_MATRIX: Dict[str, str] = {
    "test_agent": "contracts_only",
    "implementation_agent": "contracts_only",
    "diagnostic_agent": "both",
    "help_agent": "prose_only",
    "hint_agent": "both",
    "integration_test_author": "contracts_only",
    "git_repo_agent": "contracts_only",
    "bug_triage_agent": "both",
    "repair_agent": "both",
    "blueprint_author": "both",
    "blueprint_checker": "both",
    "blueprint_reviewer": "both",
    "coverage_review_agent": "contracts_only",
    "oracle_agent": "both",
}

# Gate response options -- mirrors GATE_VOCABULARY from Unit 14
_GATE_RESPONSE_OPTIONS: Dict[str, List[str]] = {
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
    "gate_5_2_assembly_exhausted": [
        "RETRY ASSEMBLY",
        "FIX BLUEPRINT",
        "FIX SPEC",
    ],
    "gate_5_3_unused_functions": ["FIX SPEC", "OVERRIDE CONTINUE"],
    "gate_6_0_debug_permission": ["AUTHORIZE DEBUG", "ABANDON DEBUG"],
    "gate_6_1_regression_test": ["TEST CORRECT", "TEST WRONG"],
    "gate_6_1a_divergence_warning": [
        "PROCEED",
        "FIX DIVERGENCE",
        "ABANDON DEBUG",
    ],
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

# Stage 3 agent types that get LANGUAGE_CONTEXT injected
_STAGE3_AGENTS = {
    "test_agent",
    "implementation_agent",
    "coverage_review",
    "diagnostic_agent",
    "coverage_review_agent",
}

# Sentinel-checking agent types (Bug S3-2, S3-4)
_SENTINEL_CHECKING_AGENTS = {
    "test_agent",
    "implementation_agent",
    "coverage_review_agent",
}


# ---------------------------------------------------------------------------
# Blueprint loading functions
# ---------------------------------------------------------------------------


def load_blueprint(blueprint_dir: Path) -> str:
    """Load and concatenate both blueprint files (prose + contracts)."""
    blueprint_dir = Path(blueprint_dir)
    prose_path = blueprint_dir / Path(ARTIFACT_FILENAMES["blueprint_prose"]).name
    contracts_path = blueprint_dir / Path(ARTIFACT_FILENAMES["blueprint_contracts"]).name

    parts: List[str] = []
    if prose_path.exists():
        parts.append(prose_path.read_text(encoding="utf-8"))
    if contracts_path.exists():
        parts.append(contracts_path.read_text(encoding="utf-8"))

    return "\n\n".join(parts)


def load_blueprint_contracts_only(blueprint_dir: Path) -> str:
    """Load only the contracts file from the blueprint directory."""
    blueprint_dir = Path(blueprint_dir)
    contracts_path = blueprint_dir / Path(ARTIFACT_FILENAMES["blueprint_contracts"]).name
    if contracts_path.exists():
        return contracts_path.read_text(encoding="utf-8")
    return ""


def load_blueprint_prose_only(blueprint_dir: Path) -> str:
    """Load only the prose file from the blueprint directory."""
    blueprint_dir = Path(blueprint_dir)
    prose_path = blueprint_dir / Path(ARTIFACT_FILENAMES["blueprint_prose"]).name
    if prose_path.exists():
        return prose_path.read_text(encoding="utf-8")
    return ""


# ---------------------------------------------------------------------------
# Context building functions
# ---------------------------------------------------------------------------


def build_unit_context(
    blueprint_dir: Path,
    unit_number: int,
    include_tier1: bool = True,
) -> str:
    """Extract unit definition and build context with include_tier1 parameter.

    Uses Unit 8's extract_units and build_unit_context with path resolution.
    Prefixes output with unit identification header.
    """
    blueprint_dir = Path(blueprint_dir)
    all_units = extract_units(blueprint_dir)

    target_unit = None
    for u in all_units:
        if u.number == unit_number:
            target_unit = u
            break

    if target_unit is None:
        return ""

    raw_context = _build_unit_context_raw(
        target_unit, all_units, include_tier1=include_tier1
    )

    # Prefix with unit identification header
    unit_name = target_unit.name or f"Unit {unit_number}"
    header = f"### Unit {unit_number}: {unit_name}"
    if include_tier1:
        header += " (full context)"
    else:
        header += " (contracts only)"

    if raw_context:
        return f"{header}\n\n{raw_context}"
    return header


def build_language_context(
    language: str,
    agent_type: str,
    language_registry: Dict[str, Dict[str, Any]],
) -> str:
    """Return formatted block containing language-specific agent guidance.

    Includes: unit language, language-specific agent guidance from registry,
    test framework, quality tools, file extension.

    For sentinel-checking agent types (test_agent, implementation_agent,
    coverage_review_agent), the stub_sentinel value from the registry is
    injected verbatim (Bug S3-2, S3-4).

    Returns empty string if agent_type has no language-specific prompts.
    """
    if language not in language_registry:
        return ""

    lang_config = language_registry[language]

    # Check if agent_type has language-specific prompts
    agent_prompts = lang_config.get("agent_prompts", {})
    if agent_type not in agent_prompts:
        return ""

    agent_guidance = agent_prompts[agent_type]

    parts: List[str] = []
    parts.append("## LANGUAGE_CONTEXT")
    parts.append("")
    parts.append(f"**Language:** {lang_config.get('display_name', language)}")
    parts.append(f"**File extension:** {lang_config.get('file_extension', '')}")

    test_framework = lang_config.get("test_framework", "")
    if test_framework:
        parts.append(f"**Test framework:** {test_framework}")

    # Quality tools
    default_quality = lang_config.get("default_quality", {})
    if default_quality:
        quality_parts: List[str] = []
        for key in ["linter", "formatter", "type_checker", "import_sorter"]:
            val = default_quality.get(key)
            if val and val != "none":
                quality_parts.append(f"{key}: {val}")
        if quality_parts:
            parts.append(f"**Quality tools:** {', '.join(quality_parts)}")

    parts.append("")
    parts.append(f"**Agent guidance:** {agent_guidance}")

    # Sentinel injection for stub-checking agents (Bug S3-2, S3-4)
    if agent_type in _SENTINEL_CHECKING_AGENTS:
        stub_sentinel = lang_config.get("stub_sentinel", "")
        if stub_sentinel:
            parts.append("")
            parts.append(f"**Stub sentinel:** `{stub_sentinel}`")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_blueprint_for_agent(
    agent_type: str,
    blueprint_dir: Path,
) -> str:
    """Load blueprint based on SELECTIVE_LOADING_MATRIX for the agent type."""
    loading_mode = SELECTIVE_LOADING_MATRIX.get(agent_type)
    if loading_mode is None:
        return ""
    if loading_mode == "contracts_only":
        return load_blueprint_contracts_only(blueprint_dir)
    elif loading_mode == "prose_only":
        return load_blueprint_prose_only(blueprint_dir)
    elif loading_mode == "both":
        return load_blueprint(blueprint_dir)
    return ""


def _read_file_safe(path: Path) -> str:
    """Read file contents, returning empty string if absent."""
    path = Path(path)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _read_json_safe(path: Path) -> Any:
    """Read JSON file, returning empty dict if absent."""
    path = Path(path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _get_state_safe(project_root: Path) -> Optional[PipelineState]:
    """Load pipeline state, returning None if absent."""
    try:
        return load_state(project_root)
    except FileNotFoundError:
        return None


def _format_section(title: str, content: str) -> str:
    """Format a prompt section with a markdown heading."""
    if not content or not content.strip():
        return ""
    return f"## {title}\n\n{content.strip()}"


def _format_mode_and_expected_status_blocks(
    agent_type: str, mode: Optional[str]
) -> str:
    """Bug S3-159: emit explicit `## Mode` and `## Expected Terminal Status`
    blocks for multi-mode agents. Returns an empty string when:
    - mode is None
    - the (agent_type, mode) pair is not in the canonical multi-mode map
      (i.e., the agent is not multi-mode and has no mode-specific
      terminal-status binding to enforce).
    """
    if mode is None:
        return ""
    valid = _expected_terminal_status_for(agent_type, mode)
    if not valid:
        return ""
    bullets = "\n".join(f"- {s}" for s in valid)
    return (
        f"## Mode\n\n{mode}\n\n"
        f"## Expected Terminal Status\n\n"
        f"You MUST emit exactly one of the following terminal status lines:\n\n"
        f"{bullets}\n\n"
        f"(Other statuses are invalid for this mode and will be rejected by "
        f"the dispatcher.)"
    )


def _assemble_sections(sections: List[str]) -> str:
    """Join non-empty sections with double newlines."""
    non_empty = [s for s in sections if s and s.strip()]
    return "\n\n".join(non_empty)


def _get_hint_context(
    project_root: Path,
    agent_type: str,
    unit_number: Optional[int],
    state: Optional[PipelineState],
) -> str:
    """Build hint context if a forwarded hint exists."""
    hint_ledger_path = get_ledger_path(project_root, "hint")
    entries = read_ledger(hint_ledger_path)
    if not entries:
        return ""

    # Get the most recent hint entry
    last_entry = entries[-1]
    hint_content = last_entry.get("content", "")
    if not hint_content:
        return ""

    ladder_position = state.fix_ladder_position if state else None
    gate_context = None

    return assemble_hint_prompt(
        hint_text=hint_content,
        agent_type=agent_type,
        ladder_position=ladder_position,
        unit_number=unit_number,
        gate_context=gate_context,
    )


def _get_lessons_learned(project_root: Path, unit_number: Optional[int]) -> str:
    """Load lessons learned, optionally filtered for a specific unit."""
    lessons_path = project_root / ARTIFACT_FILENAMES["lessons_learned"]
    content = _read_file_safe(lessons_path)
    if not content:
        return ""

    if unit_number is not None:
        # Filter for current unit-related content
        lines = content.split("\n")
        filtered: List[str] = []
        include = False
        for line in lines:
            # Include general sections and unit-specific content
            if (
                f"unit {unit_number}" in line.lower()
                or f"unit_{unit_number}" in line.lower()
            ):
                include = True
            elif line.startswith("# ") or line.startswith("## "):
                include = False
            if include:
                filtered.append(line)
        if filtered:
            return "\n".join(filtered)
    return content


def _quality_tool_notification(project_root: Path) -> str:
    """Build quality tool notification section."""
    return (
        "## Quality Tools Notice (SVP 2.1)\n\n"
        "Your output will be automatically formatted, linted, and type-checked "
        "by quality tools after generation. Write clean code from the start, "
        "but you need not worry about formatting perfection -- the quality "
        "pipeline will handle final formatting, linting, and type checking "
        "adjustments."
    )


# ---------------------------------------------------------------------------
# Per-agent-type dispatch functions
# ---------------------------------------------------------------------------


def _prepare_setup_agent(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
) -> str:
    """Prepare task prompt for setup_agent."""
    sections: List[str] = []
    sections.append("# Setup Agent Task Prompt")

    # Bug S3-159: explicit Mode + Expected Terminal Status blocks for
    # multi-mode agents. Falls through silently when mode is None or
    # (agent, mode) is not in the canonical multi-mode map.
    mode_block = _format_mode_and_expected_status_blocks("setup_agent", mode)
    if mode_block:
        sections.append(mode_block)
    elif mode:
        # Fall back to the legacy inline indicator for non-multi-mode modes
        # (e.g., redo_delivery, redo_blueprint).
        sections.append(f"\n**Mode:** {mode}")

    # Load profile schema
    from profile_schema import DEFAULT_PROFILE

    sections.append(
        _format_section("Profile Schema", json.dumps(DEFAULT_PROFILE, indent=2))
    )

    if context:
        sections.append(_format_section("Context", context))

    # Load dialog areas and archetype rules from profile schema
    from profile_schema import VALID_ARCHETYPES

    sections.append(
        _format_section("Valid Archetypes", ", ".join(sorted(VALID_ARCHETYPES)))
    )

    # Load existing profile if present
    try:
        profile = load_profile(project_root)
        sections.append(
            _format_section("Current Profile", json.dumps(profile, indent=2))
        )
    except FileNotFoundError:
        pass

    return _assemble_sections(sections)


def _prepare_stakeholder_dialog(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
) -> str:
    """Prepare task prompt for stakeholder_dialog."""
    sections: List[str] = []
    sections.append("# Stakeholder Dialog Task Prompt")

    # Inject canonical output path (deterministic guardrail — Bug S3-107)
    spec_output_path = ARTIFACT_FILENAMES["stakeholder_spec"]
    sections.append(f"\n**Output path (mandatory):** Write the final specification to `{spec_output_path}`. Do not write to any other location.")

    # Bug S3-159: explicit Mode + Expected Terminal Status blocks. Replaces
    # the legacy inline `**Mode:**` indicator when (agent, mode) is in the
    # canonical multi-mode map.
    mode_block = _format_mode_and_expected_status_blocks(
        "stakeholder_dialog", mode
    )
    if mode_block:
        sections.append(mode_block)
    elif mode:
        sections.append(f"\n**Mode:** {mode}")

    # Load spec context
    spec_path = project_root / ARTIFACT_FILENAMES["stakeholder_spec"]
    spec_content = _read_file_safe(spec_path)
    if spec_content:
        sections.append(_format_section("Current Spec", spec_content))

    # Load revision feedback if applicable
    if mode in ("revision", "targeted_revision") and context:
        sections.append(_format_section("Revision Feedback", context))

    # Load dialog ledger
    ledger_path = get_ledger_path(project_root, "stakeholder")
    entries = read_ledger(ledger_path)
    if entries:
        ledger_text = "\n".join(
            f"- [{e.get('role', 'unknown')}] {e.get('content', '')}" for e in entries
        )
        sections.append(_format_section("Dialog History", ledger_text))

    if context and mode not in ("revision", "targeted_revision"):
        sections.append(_format_section("Context", context))

    # Bug S3-165: when the project profile requires statistical analysis,
    # append STAKEHOLDER_DIALOG_STATISTICAL_PRIMER so the stakeholder dialog
    # elicits machine-actionable answers for every statistical concept.
    # Defensive guard: only append when state is provided (legacy callers
    # without state get the unchanged base prompt).
    if state is not None and _requires_statistical_analysis(state):
        from construction_agents import STAKEHOLDER_DIALOG_STATISTICAL_PRIMER

        sections.append(STAKEHOLDER_DIALOG_STATISTICAL_PRIMER)

    return _assemble_sections(sections)


def _prepare_stakeholder_reviewer(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
) -> str:
    """Prepare task prompt for stakeholder_reviewer."""
    sections: List[str] = []
    sections.append("# Stakeholder Reviewer Task Prompt")

    # Load spec
    spec_path = project_root / ARTIFACT_FILENAMES["stakeholder_spec"]
    spec_content = _read_file_safe(spec_path)
    if spec_content:
        sections.append(_format_section("Spec", spec_content))

    # Review checklist
    sections.append(
        _format_section(
            "Review Checklist",
            "Review the spec for completeness, consistency, and clarity.",
        )
    )

    if context:
        sections.append(_format_section("Context", context))

    return _assemble_sections(sections)


def _prepare_blueprint_author(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
) -> str:
    """Prepare task prompt for blueprint_author."""
    sections: List[str] = []
    sections.append("# Blueprint Author Task Prompt")

    # Bug S3-159: explicit Mode + Expected Terminal Status blocks.
    mode_block = _format_mode_and_expected_status_blocks(
        "blueprint_author", mode
    )
    if mode_block:
        sections.append(mode_block)
    elif mode:
        sections.append(f"\n**Mode:** {mode}")

    # Load spec
    spec_path = project_root / ARTIFACT_FILENAMES["stakeholder_spec"]
    spec_content = _read_file_safe(spec_path)
    if spec_content:
        sections.append(_format_section("Spec", spec_content))

    # Load profile
    try:
        profile = load_profile(project_root)
        sections.append(_format_section("Profile", json.dumps(profile, indent=2)))
    except FileNotFoundError:
        pass

    # Load project context
    project_context_path = project_root / ".svp" / "project_context.md"
    project_context = _read_file_safe(project_context_path)
    if project_context:
        sections.append(_format_section("Project Context", project_context))

    # Blueprint: both files (revision mode gets existing blueprint)
    blueprint_content = _load_blueprint_for_agent("blueprint_author", blueprint_dir)
    if blueprint_content:
        sections.append(_format_section("Blueprint", blueprint_content))

    # Reviewer feedback for revision mode
    if mode == "revision" and context:
        sections.append(_format_section("Reviewer Feedback", context))

    if context and mode != "revision":
        sections.append(_format_section("Context", context))

    # Bug S3-166: when the project profile requires statistical analysis,
    # append BLUEPRINT_AUTHOR_STATISTICAL_PRIMER so blueprint contracts
    # capture every statistical concept as machine-actionable Tier 2/Tier 3
    # clauses. Defensive guard: only append when state is provided
    # (legacy callers without state get the unchanged base prompt).
    if state is not None and _requires_statistical_analysis(state):
        from construction_agents import BLUEPRINT_AUTHOR_STATISTICAL_PRIMER

        sections.append(BLUEPRINT_AUTHOR_STATISTICAL_PRIMER)

    return _assemble_sections(sections)


def _prepare_blueprint_reviewer(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
) -> str:
    """Prepare task prompt for blueprint_reviewer."""
    sections: List[str] = []
    sections.append("# Blueprint Reviewer Task Prompt")

    # Load spec
    spec_path = project_root / ARTIFACT_FILENAMES["stakeholder_spec"]
    spec_content = _read_file_safe(spec_path)
    if spec_content:
        sections.append(_format_section("Spec", spec_content))

    # Blueprint: both files
    blueprint_content = _load_blueprint_for_agent("blueprint_reviewer", blueprint_dir)
    if blueprint_content:
        sections.append(_format_section("Blueprint", blueprint_content))

    # Review checklist
    sections.append(
        _format_section(
            "Review Checklist",
            "Review the blueprint for completeness, consistency, and alignment with spec.",
        )
    )

    if context:
        sections.append(_format_section("Context", context))

    return _assemble_sections(sections)


def _prepare_blueprint_checker(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
) -> str:
    """Prepare task prompt for blueprint_checker."""
    sections: List[str] = []
    sections.append("# Blueprint Checker Task Prompt")

    # Load spec
    spec_path = project_root / ARTIFACT_FILENAMES["stakeholder_spec"]
    spec_content = _read_file_safe(spec_path)
    if spec_content:
        sections.append(_format_section("Spec", spec_content))

    # Blueprint: both files
    blueprint_content = _load_blueprint_for_agent("blueprint_checker", blueprint_dir)
    if blueprint_content:
        sections.append(_format_section("Blueprint", blueprint_content))

    # Alignment checklist
    checklist_path = project_root / ".svp" / "alignment_checker_checklist.md"
    checklist_content = _read_file_safe(checklist_path)
    if checklist_content:
        sections.append(_format_section("Alignment Checklist", checklist_content))

    if context:
        sections.append(_format_section("Context", context))

    return _assemble_sections(sections)


def _prepare_checklist_generation(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
) -> str:
    """Prepare task prompt for checklist_generation."""
    sections: List[str] = []
    sections.append("# Checklist Generation Task Prompt")

    # Load approved spec
    spec_path = project_root / ARTIFACT_FILENAMES["stakeholder_spec"]
    spec_content = _read_file_safe(spec_path)
    if spec_content:
        sections.append(_format_section("Approved Spec", spec_content))

    # Load lessons learned
    lessons = _get_lessons_learned(project_root, None)
    if lessons:
        sections.append(_format_section("Lessons Learned", lessons))

    # Load regression test inventory
    regression_dir = project_root / "tests" / "regression"
    if regression_dir.exists():
        regression_files = list(regression_dir.glob("*"))
        if regression_files:
            inventory = "\n".join(f"- {f.name}" for f in regression_files)
            sections.append(_format_section("Regression Test Inventory", inventory))

    if context:
        sections.append(_format_section("Context", context))

    return _assemble_sections(sections)


def _prepare_test_agent(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
    unit_number: Optional[int],
) -> str:
    """Prepare task prompt for test_agent."""
    sections: List[str] = []
    sections.append("# Test Agent Task Prompt")

    if unit_number is not None:
        sections.append(f"\n**Unit:** {unit_number}")

    if mode:
        sections.append(f"\n**Mode:** {mode}")

    # Blueprint: contracts only
    blueprint_content = _load_blueprint_for_agent("test_agent", blueprint_dir)
    if blueprint_content:
        sections.append(_format_section("Blueprint Contracts", blueprint_content))

    # Unit context (contracts only)
    if unit_number is not None:
        unit_ctx = build_unit_context(blueprint_dir, unit_number, include_tier1=False)
        if unit_ctx:
            sections.append(_format_section("Unit Context", unit_ctx))

    # Quality tool notification
    sections.append(_quality_tool_notification(project_root))

    # Lessons learned (filtered for current unit)
    lessons = _get_lessons_learned(project_root, unit_number)
    if lessons:
        sections.append(_format_section("Lessons Learned", lessons))

    # Language context
    if state:
        lang_ctx = build_language_context(
            state.primary_language, "test_agent", LANGUAGE_REGISTRY
        )
        if lang_ctx:
            sections.append(lang_ctx)

    # Hint context
    if state:
        hint_ctx = _get_hint_context(project_root, "test_agent", unit_number, state)
        if hint_ctx:
            sections.append(hint_ctx)

    if context:
        sections.append(_format_section("Context", context))

    return _assemble_sections(sections)


def _prepare_implementation_agent(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
    unit_number: Optional[int],
    ladder: Optional[str] = None,
    quality_report: Optional[str] = None,
) -> str:
    """Prepare task prompt for implementation_agent."""
    sections: List[str] = []
    sections.append("# Implementation Agent Task Prompt")

    if unit_number is not None:
        sections.append(f"\n**Unit:** {unit_number}")

    # Blueprint: contracts only
    blueprint_content = _load_blueprint_for_agent("implementation_agent", blueprint_dir)
    if blueprint_content:
        sections.append(_format_section("Blueprint Contracts", blueprint_content))

    # Unit context (contracts only)
    if unit_number is not None:
        unit_ctx = build_unit_context(blueprint_dir, unit_number, include_tier1=False)
        if unit_ctx:
            sections.append(_format_section("Unit Context", unit_ctx))

    # Quality tool notification
    sections.append(_quality_tool_notification(project_root))

    # Diagnostic report if ladder position is diagnostic_impl
    effective_ladder = ladder
    if effective_ladder is None and state:
        effective_ladder = state.fix_ladder_position

    if effective_ladder == "diagnostic_impl":
        diag_path = project_root / ".svp" / "diagnostic_report.md"
        diag_content = _read_file_safe(diag_path)
        if diag_content:
            sections.append(_format_section("Diagnostic Report", diag_content))

    # Quality report injection
    if quality_report:
        qr_content = _read_file_safe(Path(quality_report))
        if qr_content:
            sections.append(_format_section("Quality Report", qr_content))

    # Language context
    if state:
        lang_ctx = build_language_context(
            state.primary_language, "implementation_agent", LANGUAGE_REGISTRY
        )
        if lang_ctx:
            sections.append(lang_ctx)

    # Hint context
    if state:
        hint_ctx = _get_hint_context(
            project_root, "implementation_agent", unit_number, state
        )
        if hint_ctx:
            sections.append(hint_ctx)

    if context:
        sections.append(_format_section("Context", context))

    return _assemble_sections(sections)


def _prepare_coverage_review(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
    unit_number: Optional[int],
) -> str:
    """Prepare task prompt for coverage_review_agent."""
    sections: List[str] = []
    sections.append("# Coverage Review Task Prompt")

    # Blueprint: contracts only
    blueprint_content = _load_blueprint_for_agent(
        "coverage_review_agent", blueprint_dir
    )
    if blueprint_content:
        sections.append(_format_section("Blueprint Contracts", blueprint_content))

    # Unit context (contracts only)
    if unit_number is not None:
        unit_ctx = build_unit_context(blueprint_dir, unit_number, include_tier1=False)
        if unit_ctx:
            sections.append(_format_section("Unit Context", unit_ctx))

    # Load test files and source files
    if unit_number is not None:
        # Test files
        test_dir = project_root / "tests" / f"unit_{unit_number}"
        if test_dir.exists():
            for test_file in sorted(test_dir.glob("*.py")):
                test_content = _read_file_safe(test_file)
                if test_content:
                    sections.append(
                        _format_section(f"Test File: {test_file.name}", test_content)
                    )

        # Source files
        src_dir = project_root / "src" / f"unit_{unit_number}"
        if src_dir.exists():
            for src_file in sorted(src_dir.glob("*.py")):
                src_content = _read_file_safe(src_file)
                if src_content:
                    sections.append(
                        _format_section(f"Source File: {src_file.name}", src_content)
                    )

    # Language context
    if state:
        lang_ctx = build_language_context(
            state.primary_language, "coverage_review_agent", LANGUAGE_REGISTRY
        )
        if lang_ctx:
            sections.append(lang_ctx)

    if context:
        sections.append(_format_section("Context", context))

    return _assemble_sections(sections)


def _prepare_diagnostic_agent(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
    unit_number: Optional[int],
) -> str:
    """Prepare task prompt for diagnostic_agent."""
    sections: List[str] = []
    sections.append("# Diagnostic Agent Task Prompt")

    # Blueprint: both files
    blueprint_content = _load_blueprint_for_agent("diagnostic_agent", blueprint_dir)
    if blueprint_content:
        sections.append(_format_section("Blueprint", blueprint_content))

    # Unit context (both files)
    if unit_number is not None:
        unit_ctx = build_unit_context(blueprint_dir, unit_number, include_tier1=True)
        if unit_ctx:
            sections.append(_format_section("Unit Context", unit_ctx))

    # Test output
    test_output_path = project_root / ".svp" / "test_output.txt"
    test_output = _read_file_safe(test_output_path)
    if test_output:
        sections.append(_format_section("Test Output", test_output))

    # Implementation source
    if unit_number is not None:
        src_dir = project_root / "src" / f"unit_{unit_number}"
        if src_dir.exists():
            for src_file in sorted(src_dir.glob("*.py")):
                src_content = _read_file_safe(src_file)
                if src_content:
                    sections.append(
                        _format_section(
                            f"Implementation Source: {src_file.name}", src_content
                        )
                    )

    # Language context
    if state:
        lang_ctx = build_language_context(
            state.primary_language, "diagnostic_agent", LANGUAGE_REGISTRY
        )
        if lang_ctx:
            sections.append(lang_ctx)

    if context:
        sections.append(_format_section("Context", context))

    return _assemble_sections(sections)


def _prepare_integration_test_author(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
) -> str:
    """Prepare task prompt for integration_test_author."""
    sections: List[str] = []
    sections.append("# Integration Test Author Task Prompt")

    # Blueprint: contracts only
    blueprint_content = _load_blueprint_for_agent(
        "integration_test_author", blueprint_dir
    )
    if blueprint_content:
        sections.append(_format_section("Blueprint Contracts", blueprint_content))

    # Integration context
    assembly_map_path = project_root / ARTIFACT_FILENAMES.get(
        "assembly_map", ".svp/assembly_map.json"
    )
    assembly_map = _read_file_safe(assembly_map_path)
    if assembly_map:
        sections.append(_format_section("Assembly Map", assembly_map))

    # Bug S3-97: Inject bridge test requirement for mixed archetype
    from profile_schema import load_profile

    profile = load_profile(project_root)
    if profile.get("archetype") == "mixed":
        communication = profile.get("language", {}).get("communication", {})
        directions = list(communication.keys())
        bridge_requirement = (
            "## Bridge Test Requirement (AC-92, Section 40.6.5)\n\n"
            "This is a mixed archetype project. You MUST include at least one "
            "cross-language bridge verification test per declared communication "
            f"direction. Declared directions: {directions}.\n\n"
        )
        for direction in directions:
            comm_info = communication[direction]
            library = comm_info.get("library", direction)
            if direction == "python_r":
                bridge_requirement += (
                    f"- Direction `{direction}`: Write a test that invokes R "
                    f"from Python via {library} and verifies the result.\n"
                )
            elif direction == "r_python":
                bridge_requirement += (
                    f"- Direction `{direction}`: Write a test that invokes "
                    f"Python from R via {library} and verifies the result.\n"
                )
        sections.append(bridge_requirement)

    # Previous failure output if retry
    if context:
        sections.append(_format_section("Previous Failure / Context", context))

    return _assemble_sections(sections)


def _prepare_regression_adaptation(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
) -> str:
    """Prepare task prompt for regression_adaptation."""
    sections: List[str] = []
    sections.append("# Regression Adaptation Task Prompt")

    # Failing tests
    test_output_path = project_root / ".svp" / "test_output.txt"
    test_output = _read_file_safe(test_output_path)
    if test_output:
        sections.append(_format_section("Failing Tests", test_output))

    # Blueprint file tree -- from prose
    prose_content = load_blueprint_prose_only(blueprint_dir)
    if prose_content:
        sections.append(_format_section("Blueprint File Tree", prose_content))

    # Module listing
    src_dir = project_root / "src"
    if src_dir.exists():
        modules: List[str] = []
        for unit_dir in sorted(src_dir.iterdir()):
            if unit_dir.is_dir() and unit_dir.name.startswith("unit_"):
                for f in sorted(unit_dir.glob("*.py")):
                    modules.append(f"- {unit_dir.name}/{f.name}")
        if modules:
            sections.append(_format_section("Module Listing", "\n".join(modules)))

    # Assembly map
    assembly_map_path = project_root / ARTIFACT_FILENAMES.get(
        "assembly_map", ".svp/assembly_map.json"
    )
    assembly_map = _read_file_safe(assembly_map_path)
    if assembly_map:
        sections.append(_format_section("Assembly Map", assembly_map))

    # Previous spec summary
    spec_path = project_root / ARTIFACT_FILENAMES["stakeholder_spec"]
    spec_content = _read_file_safe(spec_path)
    if spec_content:
        sections.append(_format_section("Spec Summary", spec_content))

    if context:
        sections.append(_format_section("Context", context))

    return _assemble_sections(sections)


def _prepare_git_repo_agent(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
) -> str:
    """Prepare task prompt for git_repo_agent."""
    sections: List[str] = []
    sections.append("# Git Repo Agent Task Prompt")

    # Blueprint: contracts only
    blueprint_content = _load_blueprint_for_agent("git_repo_agent", blueprint_dir)
    if blueprint_content:
        sections.append(_format_section("Blueprint Contracts", blueprint_content))

    # Assembly config
    assembly_map_path = project_root / ARTIFACT_FILENAMES.get(
        "assembly_map", ".svp/assembly_map.json"
    )
    assembly_map = _read_file_safe(assembly_map_path)
    if assembly_map:
        sections.append(_format_section("Assembly Map", assembly_map))

    # Profile
    profile: Dict[str, Any] = {}
    try:
        profile = load_profile(project_root)
        sections.append(_format_section("Profile", json.dumps(profile, indent=2)))
    except FileNotFoundError:
        pass

    # Bug S3-112: inject canonical delivered repo path as a REQUIRED directive.
    # The agent must place the delivered repo at exactly this absolute path;
    # any deviation will be caught by dispatch_agent_status validation.
    profile_name = (
        profile.get("name")
        or profile.get("project_name")
        or project_root.name
    )
    canonical_delivered_path = (
        project_root.parent / f"{profile_name}-repo"
    ).resolve()
    sections.append(
        _format_section(
            "Delivered Repo Path (REQUIRED)",
            f"{canonical_delivered_path}\n\n"
            "You MUST place the delivered repository at exactly this "
            "absolute path. It is the canonical sibling of the project "
            "root. Call the language-appropriate `assemble_*_project()` "
            "helper from the `generate_assembly_map` module — "
            "`assemble_python_project`, `assemble_r_project`, "
            "`assemble_plugin_project`, or `assemble_mixed_project`. "
            "These helpers already use this path internally. Do NOT "
            "create `./delivered/`, `./output/`, or any other "
            "destination. Do NOT manually edit `.svp/pipeline_state.json`. "
            "See the agent definition's `## Delivered Repo Location` "
            "section for details. (Bug S3-112)",
        )
    )

    # Fix context if retry
    if context:
        sections.append(_format_section("Fix Context", context))

    return _assemble_sections(sections)


def _prepare_help_agent(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
) -> str:
    """Prepare task prompt for help_agent."""
    sections: List[str] = []
    sections.append("# Help Agent Task Prompt")

    # Project summary
    try:
        profile = load_profile(project_root)
        summary = json.dumps(
            {
                "archetype": profile.get("archetype"),
                "language": profile.get("language", {}).get("primary"),
            },
            indent=2,
        )
        sections.append(_format_section("Project Summary", summary))
    except FileNotFoundError:
        pass

    # Spec
    spec_path = project_root / ARTIFACT_FILENAMES["stakeholder_spec"]
    spec_content = _read_file_safe(spec_path)
    if spec_content:
        sections.append(_format_section("Spec", spec_content))

    # Blueprint: prose only
    blueprint_content = _load_blueprint_for_agent("help_agent", blueprint_dir)
    if blueprint_content:
        sections.append(_format_section("Blueprint (Prose)", blueprint_content))

    # Gate context if at gate
    if context:
        sections.append(_format_section("Gate Context", context))

    return _assemble_sections(sections)


def _prepare_hint_agent(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
) -> str:
    """Prepare task prompt for hint_agent."""
    sections: List[str] = []
    sections.append("# Hint Agent Task Prompt")

    # Blueprint: both files
    blueprint_content = _load_blueprint_for_agent("hint_agent", blueprint_dir)
    if blueprint_content:
        sections.append(_format_section("Blueprint", blueprint_content))

    # Hint text or ledger context
    hint_ledger_path = get_ledger_path(project_root, "hint")
    entries = read_ledger(hint_ledger_path)
    if entries:
        ledger_text = "\n".join(
            f"- [{e.get('role', 'unknown')}] {e.get('content', '')}" for e in entries
        )
        sections.append(_format_section("Hint Ledger", ledger_text))

    # Target agent context
    if context:
        sections.append(_format_section("Target Agent Context", context))

    return _assemble_sections(sections)


def _prepare_reference_indexing(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
) -> str:
    """Prepare task prompt for reference_indexing."""
    sections: List[str] = []
    sections.append("# Reference Indexing Task Prompt")

    # Reference document paths
    refs_dir = project_root / "references"
    if refs_dir.exists():
        ref_files = list(refs_dir.glob("*"))
        if ref_files:
            paths = "\n".join(f"- {f.name}" for f in ref_files)
            sections.append(_format_section("Reference Documents", paths))

    # Indexing instructions
    sections.append(
        _format_section(
            "Indexing Instructions",
            "Index all reference documents for use during the pipeline.",
        )
    )

    if context:
        sections.append(_format_section("Context", context))

    return _assemble_sections(sections)


def _prepare_redo_agent(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
) -> str:
    """Prepare task prompt for redo_agent."""
    sections: List[str] = []
    sections.append("# Redo Agent Task Prompt")

    # State summary
    if state:
        state_summary = (
            f"Stage: {state.stage}\n"
            f"Sub-stage: {state.sub_stage}\n"
            f"Current unit: {state.current_unit}\n"
            f"Fix ladder: {state.fix_ladder_position}"
        )
        sections.append(_format_section("State Summary", state_summary))

    # Error description
    if context:
        sections.append(_format_section("Error Description", context))

    return _assemble_sections(sections)


def _prepare_bug_triage(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
) -> str:
    """Prepare task prompt for bug_triage_agent."""
    sections: List[str] = []
    sections.append("# Bug Triage Agent Task Prompt")

    # Spec
    spec_path = project_root / ARTIFACT_FILENAMES["stakeholder_spec"]
    spec_content = _read_file_safe(spec_path)
    if spec_content:
        sections.append(_format_section("Spec", spec_content))

    # Blueprint: both files
    blueprint_content = _load_blueprint_for_agent("bug_triage_agent", blueprint_dir)
    if blueprint_content:
        sections.append(_format_section("Blueprint", blueprint_content))

    # Source
    src_dir = project_root / "src"
    if src_dir.exists():
        for unit_dir in sorted(src_dir.iterdir()):
            if unit_dir.is_dir():
                for f in sorted(unit_dir.glob("*.py")):
                    content = _read_file_safe(f)
                    if content:
                        sections.append(
                            _format_section(
                                f"Source: {unit_dir.name}/{f.name}", content
                            )
                        )

    # Tests
    test_dir = project_root / "tests"
    if test_dir.exists():
        for test_subdir in sorted(test_dir.iterdir()):
            if test_subdir.is_dir():
                for f in sorted(test_subdir.glob("*.py")):
                    content = _read_file_safe(f)
                    if content:
                        sections.append(
                            _format_section(
                                f"Test: {test_subdir.name}/{f.name}", content
                            )
                        )

    # Ledger
    if state and state.debug_session:
        ledger_path = state.debug_session.get("ledger_path")
        if ledger_path:
            entries = read_ledger(Path(ledger_path))
            if entries:
                ledger_text = "\n".join(
                    f"- [{e.get('role', 'unknown')}] {e.get('content', '')}"
                    for e in entries
                )
                sections.append(_format_section("Debug Ledger", ledger_text))

    # Assembly map
    assembly_map_path = project_root / ARTIFACT_FILENAMES.get(
        "assembly_map", ".svp/assembly_map.json"
    )
    assembly_map = _read_file_safe(assembly_map_path)
    if assembly_map:
        sections.append(_format_section("Assembly Map", assembly_map))

    # Delivered repo path
    if state and state.delivered_repo_path:
        sections.append(
            _format_section("Delivered Repo Path", state.delivered_repo_path)
        )

    if context:
        sections.append(_format_section("Context", context))

    return _assemble_sections(sections)


def _prepare_repair_agent(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
    unit_number: Optional[int],
) -> str:
    """Prepare task prompt for repair_agent."""
    sections: List[str] = []
    sections.append("# Repair Agent Task Prompt")

    # Error diagnosis
    triage_path = project_root / ARTIFACT_FILENAMES.get(
        "triage_result", ".svp/triage_result.json"
    )
    triage_content = _read_file_safe(triage_path)
    if triage_content:
        sections.append(_format_section("Error Diagnosis", triage_content))

    # Environment state
    if state:
        env_state = (
            f"Stage: {state.stage}\n"
            f"Sub-stage: {state.sub_stage}\n"
            f"Current unit: {state.current_unit}"
        )
        sections.append(_format_section("Environment State", env_state))

    # Blueprint: both files
    blueprint_content = _load_blueprint_for_agent("repair_agent", blueprint_dir)
    if blueprint_content:
        sections.append(_format_section("Blueprint", blueprint_content))

    # Affected unit context
    if unit_number is not None:
        unit_ctx = build_unit_context(blueprint_dir, unit_number, include_tier1=True)
        if unit_ctx:
            sections.append(_format_section("Affected Unit Context", unit_ctx))
    elif state and state.debug_session:
        affected = state.debug_session.get("affected_units", [])
        for u in affected:
            unit_ctx = build_unit_context(blueprint_dir, u, include_tier1=True)
            if unit_ctx:
                sections.append(_format_section(f"Affected Unit {u} Context", unit_ctx))

    if context:
        sections.append(_format_section("Context", context))

    return _assemble_sections(sections)


def _prepare_oracle_agent(
    project_root: Path,
    state: Optional[PipelineState],
    mode: Optional[str],
    context: Optional[str],
    blueprint_dir: Path,
) -> str:
    """Prepare task prompt for oracle_agent.

    Differentiates prompt content by oracle_phase:
    - dry_run: full analysis context (blueprint, assembly map, delivered repo, mode)
    - green_run: execution context (trajectory plan, nested session)
    - other phases: common context only
    """
    sections: List[str] = []
    oracle_phase = state.oracle_phase if state else None
    sections.append("# Oracle Agent Task Prompt")

    if oracle_phase:
        sections.append(f"\n**Oracle Phase:** {oracle_phase}")

    # --- Common inputs (all phases) ---

    # Spec
    spec_path = project_root / ARTIFACT_FILENAMES["stakeholder_spec"]
    spec_content = _read_file_safe(spec_path)
    if spec_content:
        sections.append(_format_section("Spec", spec_content))

    # Run ledger
    ledger_path = project_root / ARTIFACT_FILENAMES.get(
        "oracle_run_ledger", ".svp/oracle_run_ledger.json"
    )
    ledger_content = _read_file_safe(ledger_path)
    if ledger_content:
        sections.append(_format_section("Oracle Run Ledger", ledger_content))

    # Bug catalog
    bug_catalog_path = project_root / ".svp" / "bug_catalog.json"
    bug_catalog = _read_file_safe(bug_catalog_path)
    if bug_catalog:
        sections.append(_format_section("Bug Catalog", bug_catalog))

    # Regression tests
    regression_dir = project_root / "tests" / "regression"
    if regression_dir.exists():
        for f in sorted(regression_dir.glob("*")):
            reg_content = _read_file_safe(f)
            if reg_content:
                sections.append(
                    _format_section(f"Regression Test: {f.name}", reg_content)
                )

    # --- Phase-specific inputs ---

    if oracle_phase == "dry_run":
        # Dry run: analyze delivered code against spec
        blueprint_content = _load_blueprint_for_agent("oracle_agent", blueprint_dir)
        if blueprint_content:
            sections.append(_format_section("Blueprint", blueprint_content))

        # Assembly map
        assembly_map_path = project_root / ARTIFACT_FILENAMES.get(
            "assembly_map", ".svp/assembly_map.json"
        )
        assembly_map = _read_file_safe(assembly_map_path)
        if assembly_map:
            sections.append(_format_section("Assembly Map", assembly_map))

        # Delivered repo path for code analysis
        if state and state.delivered_repo_path:
            sections.append(
                _format_section("Delivered Repo Path", str(state.delivered_repo_path))
            )

        # Oracle mode context (E-mode vs F-mode)
        if state and state.oracle_test_project:
            test_proj = state.oracle_test_project
            oracle_mode = (
                "E-mode (product testing)"
                if "examples/" in test_proj
                else "F-mode (machinery testing)"
            )
            sections.append(_format_section("Oracle Mode", oracle_mode))
            sections.append(_format_section("Test Project", test_proj))

            # Bug S3-102: embed test project artifacts in task prompt
            artifact_dir = (
                project_root / test_proj
                if "examples/" in test_proj
                else project_root / "docs"
            )
            for artifact_name in [
                "oracle_manifest.json",
                "project_context.md",
                "stakeholder_spec.md",
                "blueprint_prose.md",
                "blueprint_contracts.md",
            ]:
                artifact_content = _read_file_safe(artifact_dir / artifact_name)
                if artifact_content:
                    sections.append(
                        _format_section(
                            f"Test Project: {artifact_name}", artifact_content
                        )
                    )

    elif oracle_phase == "green_run":
        # Green run: execute trajectory in nested session
        if state and state.oracle_nested_session_path:
            sections.append(
                _format_section(
                    "Nested Session Path", str(state.oracle_nested_session_path)
                )
            )
            nested_state_path = (
                Path(state.oracle_nested_session_path) / ".svp" / "pipeline_state.json"
            )
            nested_state = _read_file_safe(nested_state_path)
            if nested_state:
                sections.append(
                    _format_section("Nested Session State", nested_state)
                )

        # Load trajectory plan from dry run output
        trajectory_path = project_root / ".svp" / "oracle_trajectory.json"
        trajectory_content = _read_file_safe(trajectory_path)
        if trajectory_content:
            sections.append(
                _format_section("Trajectory Plan", trajectory_content)
            )

        # Bug S3-102: embed test project artifacts for green run too
        if state and state.oracle_test_project:
            test_proj = state.oracle_test_project
            artifact_dir = (
                project_root / test_proj
                if "examples/" in test_proj
                else project_root / "docs"
            )
            for artifact_name in [
                "oracle_manifest.json",
                "project_context.md",
                "stakeholder_spec.md",
                "blueprint_prose.md",
                "blueprint_contracts.md",
            ]:
                artifact_content = _read_file_safe(artifact_dir / artifact_name)
                if artifact_content:
                    sections.append(
                        _format_section(
                            f"Test Project: {artifact_name}", artifact_content
                        )
                    )

        # Green run read-only constraints (Bug S3-95)
        sections.append(
            _format_section(
                "Green Run Constraints",
                "You are READ-ONLY during green_run. Do NOT edit code, tests, "
                "specs, blueprints, or any workspace files (except oracle "
                "ledger/diagnostic map/trajectory). This is enforced by a "
                "PreToolUse hook — write attempts will be blocked.\n\n"
                "When you find a bug: (1) document it in your diagnostic map, "
                "(2) produce ORACLE_FIX_APPLIED as your terminal status with "
                "a fix plan in your output. The routing script handles Gate B "
                "presentation and /svp:bug routing. You do NOT fix bugs "
                "yourself.",
            )
        )

    else:
        # Other phases: include test project and nested session if available
        if state and state.oracle_test_project:
            test_project_path = Path(state.oracle_test_project)
            if test_project_path.exists():
                sections.append(
                    _format_section("Test Project", str(test_project_path))
                )

        if state and state.oracle_nested_session_path:
            nested_state_path = (
                Path(state.oracle_nested_session_path) / ".svp" / "pipeline_state.json"
            )
            nested_state = _read_file_safe(nested_state_path)
            if nested_state:
                sections.append(
                    _format_section("Nested Session State", nested_state)
                )

        # Assembly map
        assembly_map_path = project_root / ARTIFACT_FILENAMES.get(
            "assembly_map", ".svp/assembly_map.json"
        )
        assembly_map = _read_file_safe(assembly_map_path)
        if assembly_map:
            sections.append(_format_section("Assembly Map", assembly_map))

    if context:
        sections.append(_format_section("Context", context))

    return _assemble_sections(sections)


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------


def prepare_task_prompt(
    project_root: Path,
    agent_type: str,
    unit_number: Optional[int] = None,
    mode: Optional[str] = None,
    context: Optional[str] = None,
) -> str:
    """Assemble a task prompt for the given agent type.

    Dispatches by agent_type and mode. Blueprint loading follows
    SELECTIVE_LOADING_MATRIX. Writes output to .svp/task_prompt.md.
    Returns the content string.
    """
    project_root = Path(project_root)
    blueprint_dir = get_blueprint_dir(project_root)
    state = _get_state_safe(project_root)

    # Dispatch by agent_type
    if agent_type == "setup_agent":
        content = _prepare_setup_agent(
            project_root, state, mode, context, blueprint_dir
        )
    elif agent_type == "stakeholder_dialog":
        content = _prepare_stakeholder_dialog(
            project_root, state, mode, context, blueprint_dir
        )
    elif agent_type == "stakeholder_reviewer":
        content = _prepare_stakeholder_reviewer(
            project_root, state, mode, context, blueprint_dir
        )
    elif agent_type == "blueprint_author":
        content = _prepare_blueprint_author(
            project_root, state, mode, context, blueprint_dir
        )
    elif agent_type == "blueprint_reviewer":
        content = _prepare_blueprint_reviewer(
            project_root, state, mode, context, blueprint_dir
        )
    elif agent_type == "blueprint_checker":
        content = _prepare_blueprint_checker(
            project_root, state, mode, context, blueprint_dir
        )
    elif agent_type == "checklist_generation":
        content = _prepare_checklist_generation(
            project_root, state, mode, context, blueprint_dir
        )
    elif agent_type == "test_agent":
        content = _prepare_test_agent(
            project_root, state, mode, context, blueprint_dir, unit_number
        )
    elif agent_type == "implementation_agent":
        content = _prepare_implementation_agent(
            project_root, state, mode, context, blueprint_dir, unit_number
        )
    elif agent_type in ("coverage_review", "coverage_review_agent"):
        content = _prepare_coverage_review(
            project_root, state, mode, context, blueprint_dir, unit_number
        )
    elif agent_type == "diagnostic_agent":
        content = _prepare_diagnostic_agent(
            project_root, state, mode, context, blueprint_dir, unit_number
        )
    elif agent_type == "integration_test_author":
        content = _prepare_integration_test_author(
            project_root, state, mode, context, blueprint_dir
        )
    elif agent_type == "regression_adaptation":
        content = _prepare_regression_adaptation(
            project_root, state, mode, context, blueprint_dir
        )
    elif agent_type == "git_repo_agent":
        content = _prepare_git_repo_agent(
            project_root, state, mode, context, blueprint_dir
        )
    # Bug S3-124: accept both phase and agent_type forms for Group B agents.
    # Slash command bodies in unit_25 pass the phase form (e.g., `help`),
    # routing.py _agent_prepare_cmd passes the agent_type form (`help_agent`).
    # Both must dispatch correctly. reference_indexing is single-form because
    # phase == agent_type. bug_triage/coverage_review were dual-form before
    # S3-124; this fix extends the pattern uniformly.
    elif agent_type in ("help", "help_agent"):
        content = _prepare_help_agent(project_root, state, mode, context, blueprint_dir)
    elif agent_type in ("hint", "hint_agent"):
        content = _prepare_hint_agent(project_root, state, mode, context, blueprint_dir)
    elif agent_type == "reference_indexing":
        content = _prepare_reference_indexing(
            project_root, state, mode, context, blueprint_dir
        )
    elif agent_type in ("redo", "redo_agent"):
        content = _prepare_redo_agent(project_root, state, mode, context, blueprint_dir)
    elif agent_type in ("bug_triage", "bug_triage_agent"):
        content = _prepare_bug_triage(project_root, state, mode, context, blueprint_dir)
    elif agent_type == "repair_agent":
        content = _prepare_repair_agent(
            project_root, state, mode, context, blueprint_dir, unit_number
        )
    elif agent_type in ("oracle", "oracle_agent"):
        content = _prepare_oracle_agent(
            project_root, state, mode, context, blueprint_dir
        )
    else:
        content = f"# Task Prompt for {agent_type}\n\nNo specific dispatch for agent type: {agent_type}"
        if context:
            content += f"\n\n## Context\n\n{context}"

    # Inject LANGUAGE_CONTEXT for Stage 3 agents
    if agent_type in _STAGE3_AGENTS and state:
        lang_ctx = build_language_context(
            state.primary_language, agent_type, LANGUAGE_REGISTRY
        )
        if lang_ctx and lang_ctx not in content:
            content += "\n\n" + lang_ctx

    # Write output to .svp/task_prompt.md
    output_path = project_root / ARTIFACT_FILENAMES["task_prompt"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    return content


def prepare_gate_prompt(
    project_root: Path,
    gate_id: str,
    context: Optional[str] = None,
) -> str:
    """Assemble a gate prompt for the given gate ID.

    Reads pipeline state, gate-specific context. Uses gate_id to look up
    response options. Writes output to .svp/gate_prompt.md.
    Returns the content string.
    """
    project_root = Path(project_root)

    # Validate gate_id
    if gate_id not in ALL_GATE_IDS:
        raise ValueError(f"Unknown gate_id: {gate_id}")

    state = _get_state_safe(project_root)
    response_options = _GATE_RESPONSE_OPTIONS.get(gate_id, [])

    sections: List[str] = []
    sections.append(f"# Gate: {gate_id}")

    # Pipeline state summary
    if state:
        state_summary = (
            f"**Stage:** {state.stage}\n"
            f"**Sub-stage:** {state.sub_stage}\n"
            f"**Current unit:** {state.current_unit}"
        )
        sections.append(_format_section("Pipeline State", state_summary))

    # Gate-specific context using pipeline state (SC-20)
    gate_context_parts: List[str] = []

    # Add convergent gate path context
    if gate_id.startswith("gate_pass_transition"):
        if state and state.deferred_broken_units:
            deferred_list = ", ".join(str(u) for u in state.deferred_broken_units)
            gate_context_parts.append(f"**Deferred broken units:** {deferred_list}")

    if gate_id == "gate_6_3_repair_exhausted" and state and state.debug_session:
        triage_count = state.debug_session.get("triage_refinement_count", 0)
        if triage_count >= 3:
            gate_context_parts.append(
                "**Note:** Triage refinement limit reached. "
                "Only RETRY REPAIR and ABANDON DEBUG are available."
            )
            # Filter response options
            response_options = [
                opt
                for opt in response_options
                if opt in ("RETRY REPAIR", "ABANDON DEBUG")
            ]

    if gate_id == "gate_7_a_trajectory_review" and state:
        mod_count = getattr(state, "oracle_modification_count", 0)
        if mod_count >= 3:
            gate_context_parts.append(
                f"**Note:** Modification limit reached ({mod_count}/3). "
                "Only APPROVE TRAJECTORY and ABORT are available."
            )
            # Filter response options per spec Section 35.4
            response_options = [
                opt
                for opt in response_options
                if opt in ("APPROVE TRAJECTORY", "ABORT")
            ]

    if gate_context_parts:
        sections.append(_format_section("Gate Context", "\n".join(gate_context_parts)))

    # User-provided context
    if context:
        sections.append(_format_section("Context", context))

    # Response options
    options_text = "\n".join(f"- **{opt}**" for opt in response_options)
    sections.append(_format_section("Response Options", options_text))

    content = _assemble_sections(sections)

    # Write output to .svp/gate_prompt.md
    output_path = project_root / ARTIFACT_FILENAMES["gate_prompt"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    return content


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list = None) -> None:
    """CLI entry point for task/gate preparation.

    Arguments:
        --project-root: project root path
        --agent: agent type string
        --gate: gate ID string (optional, for gate prompts)
        --unit: unit number (int, optional)
        --output: output path (optional)
        --context: context string (optional)
        --mode: mode string (optional)
        --ladder: fix ladder position (optional)
        --revision-mode: flag for revision invocation (optional)
        --quality-report: path to quality gate report (optional)
    """
    parser = argparse.ArgumentParser(
        description="Prepare task or gate prompts for SVP pipeline agents."
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=".",
        help="Project root directory",
    )
    parser.add_argument(
        "--agent",
        type=str,
        default=None,
        help="Agent type",
    )
    parser.add_argument(
        "--gate",
        type=str,
        default=None,
        help="Gate ID for gate prompt",
    )
    parser.add_argument(
        "--unit",
        type=int,
        default=None,
        help="Unit number",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path",
    )
    parser.add_argument(
        "--context",
        type=str,
        default=None,
        help="Additional context string",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default=None,
        help="Mode string (e.g. draft, revision)",
    )
    parser.add_argument(
        "--ladder",
        type=str,
        default=None,
        help="Current fix ladder position",
    )
    parser.add_argument(
        "--revision-mode",
        action="store_true",
        default=False,
        help="Indicates revision invocation",
    )
    parser.add_argument(
        "--quality-report",
        type=str,
        default=None,
        help="Path to quality gate report for injection",
    )

    args = parser.parse_args(argv)
    # Bug S3-118: resolve at CLI boundary so downstream helpers see an
    # absolute path (Path('.').name is '', which breaks derive_env_name).
    project_root = Path(args.project_root).resolve()

    if args.gate:
        # Gate prompt mode
        content = prepare_gate_prompt(
            project_root=project_root,
            gate_id=args.gate,
            context=args.context,
        )
    elif args.agent:
        # Task prompt mode
        content = prepare_task_prompt(
            project_root=project_root,
            agent_type=args.agent,
            unit_number=args.unit,
            mode=args.mode,
            context=args.context,
        )
    else:
        print("Error: must provide --agent or --gate", file=sys.stderr)
        sys.exit(1)

    # Bug S3-144: --output and stdout are mutually exclusive. When the
    # caller provides --output, the file IS the contract (always written
    # as UTF-8) and stdout stays silent — this avoids the Windows cp1252
    # UnicodeEncodeError crash on task prompts that embed non-cp1252
    # characters (box-drawing glyphs, em-dashes, etc.). When --output is
    # omitted, stdout carries the content for interactive invocations.
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
    else:
        print(content)


if __name__ == "__main__":
    main()

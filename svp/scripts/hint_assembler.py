from typing import Optional, Dict, Any
from pathlib import Path


_VALID_AGENT_TYPES = (
    "test",
    "implementation",
    "blueprint_author",
    "stakeholder_dialog",
    "diagnostic",
    "other",
)


_AGENT_TYPE_FRAMINGS: Dict[str, str] = {
    "test": (
        "This hint may inform your test design. Consider how it relates to "
        "expected behaviors, edge cases, and assertions. Evaluate whether the "
        "hint clarifies behavioral expectations that should be captured in tests."
    ),
    "implementation": (
        "This hint may inform your implementation. Consider how it relates to "
        "code changes, algorithmic choices, and interface contracts. Evaluate "
        "whether the hint clarifies requirements that affect your implementation."
    ),
    "blueprint_author": (
        "This hint may inform your blueprint design. Consider how it relates to "
        "contract definitions, interface signatures, and behavioral specifications. "
        "Evaluate whether the hint clarifies domain requirements that should be "
        "captured in the blueprint."
    ),
    "stakeholder_dialog": (
        "This hint may inform the stakeholder dialog. Consider how it relates to "
        "requirements clarification, scope decisions, and acceptance criteria. "
        "Evaluate whether the hint provides context for the ongoing discussion."
    ),
    "diagnostic": (
        "This hint may inform your diagnostic analysis. Consider how it relates to "
        "failure root causes, behavioral mismatches, and contract violations. "
        "Evaluate whether the hint provides context that clarifies why the failure "
        "occurred."
    ),
    "other": (
        "This hint provides additional context from the human operator. Evaluate "
        "it alongside existing contracts and constraints."
    ),
}


_LADDER_POSITION_FRAMINGS: Dict[Optional[str], str] = {
    None: "",
    "first": (
        "This is the first attempt. The hint may provide foundational context "
        "that avoids common pitfalls."
    ),
    "retry": (
        "This is a retry attempt after a prior failure. The hint may address "
        "the specific issue that caused the previous attempt to fail."
    ),
    "final": (
        "This is the final attempt in the fix ladder. The hint may provide "
        "critical guidance needed to resolve a persistent issue."
    ),
}


def assemble_hint_prompt(
    hint_content: str,
    gate_id: str,
    agent_type: str,
    ladder_position: Optional[str] = None,
    unit_number: Optional[int] = None,
    stage: str = "",
) -> str:
    """Produce a complete '## Human Domain Hint (via Help Agent)' section."""
    # Pre-condition: hint_content must not be empty or whitespace-only
    if not hint_content.strip():
        raise ValueError("Empty hint content")

    # Pre-condition: agent_type must be recognized
    if agent_type not in _VALID_AGENT_TYPES:
        raise ValueError(f"Unknown agent type: {agent_type}")

    # Build the gate context line
    context_parts = []
    if gate_id:
        context_parts.append(f"Gate: {gate_id}")
    if unit_number is not None:
        context_parts.append(f"Unit: {unit_number}")
    if stage:
        context_parts.append(f"Stage: {stage}")
    gate_context = " | ".join(context_parts) if context_parts else ""

    # Get agent-type framing
    agent_framing = get_agent_type_framing(agent_type)

    # Get ladder-position framing
    ladder_framing = get_ladder_position_framing(ladder_position)

    # Assemble the sections
    lines = []
    lines.append("## Human Domain Hint (via Help Agent)")
    lines.append("")

    if gate_context:
        lines.append(f"**Context:** {gate_context}")
        lines.append("")

    lines.append(agent_framing)
    lines.append("")

    if ladder_framing:
        lines.append(ladder_framing)
        lines.append("")

    lines.append(
        "**Important:** This hint is a signal to evaluate, not a command to execute. "
        "Weigh it alongside the blueprint contracts and existing constraints."
    )
    lines.append("")
    lines.append("### Hint Content")
    lines.append("")
    lines.append(hint_content)

    result = "\n".join(lines)

    # Post-conditions
    assert "## Human Domain Hint (via Help Agent)" in result
    assert hint_content in result

    return result


def get_agent_type_framing(agent_type: str) -> str:
    """Return a template string that frames the hint for the specific agent type."""
    if agent_type not in _VALID_AGENT_TYPES:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return _AGENT_TYPE_FRAMINGS[agent_type]


def get_ladder_position_framing(ladder_position: Optional[str]) -> str:
    """Return a template string that adjusts framing based on fix ladder position."""
    if ladder_position in _LADDER_POSITION_FRAMINGS:
        return _LADDER_POSITION_FRAMINGS[ladder_position]
    # For unrecognized ladder positions, return a generic framing
    return f"Current fix ladder position: {ladder_position}."

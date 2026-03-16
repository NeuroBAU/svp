# Unit 8: Hint Prompt Assembler
from typing import Optional, Dict, Any
from pathlib import Path

VALID_AGENT_TYPES = {
    "test",
    "implementation",
    "blueprint_author",
    "stakeholder_dialog",
    "diagnostic",
    "other",
}

_AGENT_TYPE_FRAMINGS: Dict[str, str] = {
    "test": (
        "This hint is directed at the test agent. Focus on how it relates to "
        "expected behavior and assertions that validate correctness."
    ),
    "implementation": (
        "This hint is directed at the implementation agent. Focus on how it relates to "
        "code changes and implementation decisions."
    ),
    "blueprint_author": (
        "This hint is directed at the blueprint author agent. Focus on how it relates to "
        "contract design and specification clarity."
    ),
    "stakeholder_dialog": (
        "This hint is directed at the stakeholder dialog agent. Focus on how it relates to "
        "requirements and stakeholder expectations."
    ),
    "diagnostic": (
        "This hint is directed at the diagnostic agent. Focus on how it relates to "
        "analysis context and root cause investigation."
    ),
    "other": (
        "This hint is directed at a general-purpose agent. Consider it as "
        "supplementary domain context for the task at hand."
    ),
}


def get_agent_type_framing(agent_type: str) -> str:
    """Return framing string appropriate for the given agent type."""
    if agent_type not in VALID_AGENT_TYPES:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return _AGENT_TYPE_FRAMINGS[agent_type]


def get_ladder_position_framing(ladder_position: Optional[str]) -> str:
    """Return framing based on ladder position. Empty string if None."""
    if ladder_position is None:
        return ""
    return f"This hint is being provided at ladder position {ladder_position}."


def assemble_hint_prompt(
    hint_content: str,
    gate_id: str,
    agent_type: str,
    ladder_position: Optional[str] = None,
    unit_number: Optional[int] = None,
    stage: str = '',
) -> str:
    """Produce a complete '## Human Domain Hint (via Help Agent)' Markdown section."""
    # Validate inputs
    if not hint_content or not hint_content.strip():
        raise ValueError("Empty hint content")
    if agent_type not in VALID_AGENT_TYPES:
        raise ValueError(f"Unknown agent type: {agent_type}")

    agent_framing = get_agent_type_framing(agent_type)
    ladder_framing = get_ladder_position_framing(ladder_position)

    # Build context line
    context_parts = [f"Gate: {gate_id}"]
    if unit_number is not None:
        context_parts.append(f"Unit: {unit_number}")
    if stage:
        context_parts.append(f"Stage: {stage}")
    context_line = " | ".join(context_parts)

    sections = [
        "## Human Domain Hint (via Help Agent)",
        "",
        f"**Context:** {context_line}",
        "",
        agent_framing,
        "",
    ]

    if ladder_framing:
        sections.append(ladder_framing)
        sections.append("")

    sections.append("### Hint")
    sections.append("")
    sections.append(hint_content)
    sections.append("")
    sections.append(
        "**Note:** This hint is a signal to evaluate, not a command or an instruction. "
        "Assess its relevance against the blueprint contracts before acting on it."
    )

    return "\n".join(sections)

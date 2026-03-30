"""Unit 12: Hint Prompt Assembler.

Wraps human-provided hints in context-dependent prompt blocks adapted to the
receiving agent's type and the current fix ladder position.  Deterministic
template engine -- no LLM involvement.
"""

from typing import Dict, Optional

# ---------------------------------------------------------------------------
# Agent-type-specific context framings
# ---------------------------------------------------------------------------

_AGENT_TYPE_CONTEXT: Dict[str, str] = {
    "test_agent": (
        "Focus on how it relates to "
        "expected behavior and assertions that validate correctness."
    ),
    "implementation_agent": (
        "Focus on how it relates to code changes and implementation decisions."
    ),
    "diagnostic_agent": (
        "Focus on how it relates to analysis context and root cause investigation."
    ),
    "blueprint_author": (
        "Focus on how it relates to contract design and specification clarity."
    ),
    "blueprint_reviewer": (
        "Focus on how it relates to contract review and specification validation."
    ),
    "blueprint_checker": (
        "Focus on how it relates to alignment checking and specification consistency."
    ),
    "stakeholder_dialog": (
        "Focus on how it relates to requirements and stakeholder expectations."
    ),
    "coverage_review": ("Focus on how it relates to test coverage analysis and gaps."),
    "integration_test_author": (
        "Focus on how it relates to integration testing and cross-unit behavior."
    ),
    "git_repo_agent": ("Focus on how it relates to repository assembly and delivery."),
    "bug_triage": ("Focus on how it relates to bug classification and diagnosis."),
    "repair_agent": (
        "Focus on how it relates to error diagnosis and corrective implementation."
    ),
    "oracle_agent": (
        "Focus on how it relates to test project validation and pipeline verification."
    ),
}

# Fallback for agent types not explicitly listed
_DEFAULT_AGENT_CONTEXT = (
    "Consider it as supplementary domain context for the task at hand."
)


# ---------------------------------------------------------------------------
# Ladder-position-specific framings
# ---------------------------------------------------------------------------

_LADDER_POSITION_CONTEXT: Dict[str, str] = {
    "fresh_impl": (
        "This is a fresh implementation attempt. The hint provides domain "
        "context to guide the initial approach."
    ),
    "diagnostic": (
        "This hint is provided during diagnostic analysis. Use it alongside "
        "failure output and test results to guide root cause investigation."
    ),
    "diagnostic_impl": (
        "This hint is provided during a diagnostic-guided implementation "
        "retry. Use it alongside the diagnostic report to guide corrections."
    ),
    "exhausted": (
        "The automated fix ladder has been exhausted. This hint provides "
        "critical human insight that may resolve the remaining failures."
    ),
}


def _get_agent_context(agent_type: str) -> str:
    """Return agent-type-specific context framing."""
    return _AGENT_TYPE_CONTEXT.get(agent_type, _DEFAULT_AGENT_CONTEXT)


def _get_ladder_context(ladder_position: Optional[str]) -> Optional[str]:
    """Return ladder-position-specific framing, or None if not applicable."""
    if ladder_position is None:
        return None
    return _LADDER_POSITION_CONTEXT.get(
        ladder_position,
        f"This hint is being provided at ladder position: {ladder_position}.",
    )


def assemble_hint_prompt(
    hint_text: str,
    agent_type: str,
    ladder_position: Optional[str],
    unit_number: Optional[int],
    gate_context: Optional[str],
) -> str:
    """Assemble a structured hint prompt block for injection into a task prompt.

    Wraps *hint_text* in an agent-type-specific template, varying by ladder
    position.  Returns a formatted Markdown prompt block containing the
    ``[HINT]`` tag.

    Parameters
    ----------
    hint_text:
        The human-provided hint content.
    agent_type:
        The type of agent that will receive the hint (e.g. ``"test_agent"``,
        ``"implementation_agent"``).
    ladder_position:
        Current fix ladder position.  ``None`` or ``"fresh_impl"`` for fresh
        attempts; ``"diagnostic"`` / ``"diagnostic_impl"`` for diagnostic-
        guided context; ``"exhausted"`` for exhaustion context.  Included in
        the prompt only when non-None.
    unit_number:
        The unit number the hint pertains to.  Included in the prompt only
        when non-None.
    gate_context:
        Additional gate context string.  Included in the prompt only when
        non-None.

    Returns
    -------
    str
        Formatted prompt block with ``[HINT]`` tag.
    """
    agent_framing = _get_agent_context(agent_type)
    ladder_framing = _get_ladder_context(ladder_position)

    # Build sections list
    sections: list[str] = []

    # Header with [HINT] tag
    sections.append("## Human Domain Hint (via Help Agent)")
    sections.append("")
    sections.append("[HINT]")
    sections.append("")

    # Agent type context section -- includes the literal agent_type value
    sections.append(
        f"**Agent context ({agent_type}):** This hint is directed at the "
        f"{agent_type}. {agent_framing}"
    )
    sections.append("")

    # Optional: ladder position section (only when non-None)
    if ladder_position is not None and ladder_framing is not None:
        sections.append(f"**Ladder position ({ladder_position}):** {ladder_framing}")
        sections.append("")

    # Optional: unit number section (only when non-None)
    if unit_number is not None:
        sections.append(f"**Unit:** {unit_number}")
        sections.append("")

    # Optional: gate context section (only when non-None)
    if gate_context is not None:
        sections.append(f"**Gate context:** {gate_context}")
        sections.append("")

    # Hint text section
    sections.append("### Hint")
    sections.append("")
    sections.append(hint_text)
    sections.append("")

    # Evaluation note
    sections.append(
        "**Note:** This hint is a signal to evaluate, not a command or an "
        "instruction. Assess its relevance against the blueprint contracts "
        "before acting on it."
    )

    return "\n".join(sections)

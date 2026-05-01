"""Cycle K-4 (S3-206) -- test_agent F841 unused-variable prohibition.

The test_agent prompt previously lacked any F841 (unused-variable) lint
prohibition. The agent recurringly emitted F841-tripping test code
(4 of 6 WGCNA Python units in the first half of the pipeline -- 67%
recurrence). Gate A failed on each occurrence, the fix-ladder routed to
the implementation_agent, and the implementation_agent had to fix the
test file's lint issue in addition to producing the unit's
implementation.

The fix: add a "P4 -- No unused variables (F841)" entry to the existing
"## Prohibited Patterns" section in TEST_AGENT_DEFINITION, parallel in
shape and tone to P1 / P2 / P3.

Pattern reference: P14 (Agent Definition Gap) -- existing pattern; this
is a P14 sibling cycle, not a new pattern.
"""

from __future__ import annotations

from construction_agents import TEST_AGENT_DEFINITION


def test_k4_test_agent_definition_contains_f841_prohibition():
    """C-20-K4a: TEST_AGENT_DEFINITION cites the F841 ruff lint code so
    doc-consistency tests can anchor on it."""
    assert "F841" in TEST_AGENT_DEFINITION


def test_k4_test_agent_definition_prohibition_mentions_unused_variables():
    """C-20-K4a: the prohibition explicitly mentions unused variables (the
    literal antipattern name) so future weakening can't keep F841 as a code
    while losing the semantic content."""
    text = TEST_AGENT_DEFINITION.lower()
    assert "unused" in text
    assert "variable" in text


def test_k4_test_agent_definition_prohibition_appears_under_prohibited_patterns_header():
    """C-20-K4a: P4 prohibition lives inside the existing "## Prohibited
    Patterns" section, parallel to P1/P2/P3, NOT in a separate section
    (consistency with the existing prompt structure)."""
    text = TEST_AGENT_DEFINITION
    prohib_idx = text.find("## Prohibited Patterns")
    assert prohib_idx >= 0, "## Prohibited Patterns header missing"
    # Pick the first section heading after Prohibited Patterns; F841 must
    # appear before that next heading.
    after_prohib = text[prohib_idx + len("## Prohibited Patterns") :]
    next_section_idx = after_prohib.find("\n## ")
    assert next_section_idx > 0, "No next section header found after Prohibited Patterns"
    section_body = after_prohib[:next_section_idx]
    assert "F841" in section_body, (
        "F841 prohibition must appear inside the ## Prohibited Patterns section"
    )
    # And it should be labeled as P4 (parallel to P1, P2, P3).
    assert "P4 --" in section_body or "P4 -" in section_body, (
        "F841 prohibition must be labeled P4 (parallel to existing P1/P2/P3)"
    )

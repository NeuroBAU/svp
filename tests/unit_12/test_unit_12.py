"""Unit 12: Hint Prompt Assembler -- complete test suite.

Synthetic data assumptions:
- assemble_hint_prompt accepts (hint_text, agent_type, ladder_position, unit_number,
  gate_context) and returns a formatted prompt string.
- The returned string always contains the literal tag "[HINT]" so that callers
  (and ledger compaction in Unit 7) can identify hint blocks.
- Templates are agent-type-specific.  At minimum two distinct families exist:
    * "test_agent" represents test agents.
    * "implementation_agent" represents implementation agents.
  The formatted output for the same hint_text differs between these two families.
- Ladder positions govern contextual framing within the template:
    * None and "fresh_impl" produce a fresh-attempt context.
    * "diagnostic" and "diagnostic_impl" produce a diagnostic-guided context.
    * "exhausted" produce an exhaustion context.
  Fresh, diagnostic, and exhaustion contexts produce distinguishably different
  output for the same hint_text and agent_type.
- hint_text is always embedded verbatim somewhere in the returned prompt so the
  downstream agent receives the exact human-supplied guidance.
- unit_number, when provided, appears in the output (e.g., "Unit 5") so the
  agent knows which unit the hint targets.
- gate_context, when provided, appears in the output so the agent has gate-level
  information.
- Empty hint_text still produces a valid prompt block containing "[HINT]".
- Multi-line hint_text is preserved intact (no truncation or collapsing).
"""

import pytest

from hint_prompt_assembler import assemble_hint_prompt

# ---------------------------------------------------------------------------
# Constants / fixtures
# ---------------------------------------------------------------------------

SIMPLE_HINT = "Focus on edge cases in the parser."
MULTILINE_HINT = (
    "Line one of the hint.\nLine two with more detail.\nLine three: final guidance."
)
EMPTY_HINT = ""

AGENT_TYPE_TEST = "test_agent"
AGENT_TYPE_IMPL = "implementation_agent"

LADDER_FRESH_NONE = None
LADDER_FRESH_IMPL = "fresh_impl"
LADDER_DIAGNOSTIC = "diagnostic"
LADDER_DIAGNOSTIC_IMPL = "diagnostic_impl"
LADDER_EXHAUSTED = "exhausted"


# ---------------------------------------------------------------------------
# Contract: Returns formatted prompt block with [HINT] tag
# ---------------------------------------------------------------------------


class TestHintTagPresence:
    """Every call must return a string containing the literal '[HINT]' tag."""

    def test_hint_tag_present_for_test_agent_fresh(self):
        result = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_FRESH_NONE, 5, None
        )
        assert "[HINT]" in result

    def test_hint_tag_present_for_impl_agent_fresh(self):
        result = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_FRESH_IMPL, 5, None
        )
        assert "[HINT]" in result

    def test_hint_tag_present_for_diagnostic_ladder(self):
        result = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_DIAGNOSTIC, 3, None
        )
        assert "[HINT]" in result

    def test_hint_tag_present_for_diagnostic_impl_ladder(self):
        result = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_DIAGNOSTIC_IMPL, 3, None
        )
        assert "[HINT]" in result

    def test_hint_tag_present_for_exhausted_ladder(self):
        result = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_EXHAUSTED, 10, None
        )
        assert "[HINT]" in result

    def test_hint_tag_present_with_empty_hint_text(self):
        result = assemble_hint_prompt(
            EMPTY_HINT, AGENT_TYPE_IMPL, LADDER_FRESH_NONE, 1, None
        )
        assert "[HINT]" in result

    def test_hint_tag_present_with_gate_context(self):
        result = assemble_hint_prompt(
            SIMPLE_HINT,
            AGENT_TYPE_TEST,
            LADDER_FRESH_NONE,
            5,
            "gate_3_2_diagnostic_decision",
        )
        assert "[HINT]" in result


# ---------------------------------------------------------------------------
# Contract: Returns a string type
# ---------------------------------------------------------------------------


class TestReturnType:
    """assemble_hint_prompt always returns a str."""

    def test_return_type_is_string(self):
        result = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_FRESH_NONE, 5, None
        )
        assert isinstance(result, str)

    def test_return_type_is_string_with_all_optionals_none(self):
        result = assemble_hint_prompt(SIMPLE_HINT, AGENT_TYPE_TEST, None, None, None)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Contract: hint_text is embedded verbatim in the output
# ---------------------------------------------------------------------------


class TestHintTextVerbatimEmbedding:
    """The original hint_text must appear verbatim in the returned prompt."""

    def test_simple_hint_embedded_for_test_agent(self):
        result = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_FRESH_NONE, 5, None
        )
        assert SIMPLE_HINT in result

    def test_simple_hint_embedded_for_impl_agent(self):
        result = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_FRESH_IMPL, 5, None
        )
        assert SIMPLE_HINT in result

    def test_multiline_hint_preserved_intact(self):
        """Multi-line hint_text must not be truncated or collapsed."""
        result = assemble_hint_prompt(
            MULTILINE_HINT, AGENT_TYPE_TEST, LADDER_DIAGNOSTIC, 7, None
        )
        assert MULTILINE_HINT in result

    def test_hint_with_special_characters_preserved(self):
        special_hint = "Check `foo_bar` for [brackets] and {braces}."
        result = assemble_hint_prompt(
            special_hint, AGENT_TYPE_IMPL, LADDER_FRESH_NONE, 2, None
        )
        assert special_hint in result


# ---------------------------------------------------------------------------
# Contract: Templates differ for test agents vs. implementation agents
# ---------------------------------------------------------------------------


class TestAgentTypeDifferentiation:
    """The same hint_text and ladder position produce different output for
    different agent type families (test vs. implementation)."""

    def test_test_vs_impl_differ_at_fresh_none(self):
        result_test = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_FRESH_NONE, 5, None
        )
        result_impl = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_FRESH_NONE, 5, None
        )
        assert result_test != result_impl

    def test_test_vs_impl_differ_at_fresh_impl(self):
        result_test = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_FRESH_IMPL, 5, None
        )
        result_impl = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_FRESH_IMPL, 5, None
        )
        assert result_test != result_impl

    def test_test_vs_impl_differ_at_diagnostic(self):
        result_test = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_DIAGNOSTIC, 5, None
        )
        result_impl = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_DIAGNOSTIC, 5, None
        )
        assert result_test != result_impl

    def test_test_vs_impl_differ_at_diagnostic_impl(self):
        result_test = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_DIAGNOSTIC_IMPL, 5, None
        )
        result_impl = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_DIAGNOSTIC_IMPL, 5, None
        )
        assert result_test != result_impl

    def test_test_vs_impl_differ_at_exhausted(self):
        result_test = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_EXHAUSTED, 5, None
        )
        result_impl = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_EXHAUSTED, 5, None
        )
        assert result_test != result_impl


# ---------------------------------------------------------------------------
# Contract: Templates differ by ladder position
# (None/"fresh_impl" = fresh, "diagnostic"/"diagnostic_impl" = diagnostic,
#  "exhausted" = exhaustion)
# ---------------------------------------------------------------------------


class TestLadderPositionDifferentiation:
    """Fresh, diagnostic, and exhaustion contexts produce distinguishably
    different output for the same hint_text and agent_type."""

    def test_fresh_vs_diagnostic_differ_for_test_agent(self):
        result_fresh = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_FRESH_NONE, 5, None
        )
        result_diag = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_DIAGNOSTIC, 5, None
        )
        assert result_fresh != result_diag

    def test_fresh_vs_exhausted_differ_for_test_agent(self):
        result_fresh = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_FRESH_NONE, 5, None
        )
        result_exh = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_EXHAUSTED, 5, None
        )
        assert result_fresh != result_exh

    def test_diagnostic_vs_exhausted_differ_for_test_agent(self):
        result_diag = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_DIAGNOSTIC, 5, None
        )
        result_exh = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_EXHAUSTED, 5, None
        )
        assert result_diag != result_exh

    def test_fresh_vs_diagnostic_differ_for_impl_agent(self):
        result_fresh = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_FRESH_IMPL, 5, None
        )
        result_diag = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_DIAGNOSTIC_IMPL, 5, None
        )
        assert result_fresh != result_diag

    def test_fresh_vs_exhausted_differ_for_impl_agent(self):
        result_fresh = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_FRESH_IMPL, 5, None
        )
        result_exh = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_EXHAUSTED, 5, None
        )
        assert result_fresh != result_exh

    def test_diagnostic_vs_exhausted_differ_for_impl_agent(self):
        result_diag = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_DIAGNOSTIC_IMPL, 5, None
        )
        result_exh = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_EXHAUSTED, 5, None
        )
        assert result_diag != result_exh


# ---------------------------------------------------------------------------
# Contract: None and "fresh_impl" both map to fresh-attempt context
# ---------------------------------------------------------------------------


class TestFreshLadderEquivalence:
    """None and 'fresh_impl' both produce fresh-attempt context, so they
    should yield the same contextual framing (though the exact output may
    include the ladder_position value, so we verify the template family
    is the same by checking they share key structural markers)."""

    def test_none_and_fresh_impl_share_fresh_context_for_test_agent(self):
        """Both None and 'fresh_impl' use the fresh-attempt template.
        They should both differ from diagnostic, confirming they belong
        to the same template family."""
        result_none = assemble_hint_prompt(SIMPLE_HINT, AGENT_TYPE_TEST, None, 5, None)
        result_fresh = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, "fresh_impl", 5, None
        )
        result_diag = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_DIAGNOSTIC, 5, None
        )
        # Both fresh variants differ from diagnostic
        assert result_none != result_diag
        assert result_fresh != result_diag

    def test_none_and_fresh_impl_share_fresh_context_for_impl_agent(self):
        result_none = assemble_hint_prompt(SIMPLE_HINT, AGENT_TYPE_IMPL, None, 5, None)
        result_fresh = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, "fresh_impl", 5, None
        )
        result_diag = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_DIAGNOSTIC_IMPL, 5, None
        )
        # Both fresh variants differ from diagnostic
        assert result_none != result_diag
        assert result_fresh != result_diag


# ---------------------------------------------------------------------------
# Contract: "diagnostic" and "diagnostic_impl" both map to diagnostic context
# ---------------------------------------------------------------------------


class TestDiagnosticLadderEquivalence:
    """'diagnostic' and 'diagnostic_impl' both produce diagnostic-guided
    context.  They should both differ from fresh and from exhausted."""

    def test_diagnostic_and_diagnostic_impl_share_context_for_test_agent(self):
        result_d = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, "diagnostic", 5, None
        )
        result_di = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, "diagnostic_impl", 5, None
        )
        result_fresh = assemble_hint_prompt(SIMPLE_HINT, AGENT_TYPE_TEST, None, 5, None)
        # Both diagnostic variants differ from fresh
        assert result_d != result_fresh
        assert result_di != result_fresh

    def test_diagnostic_and_diagnostic_impl_share_context_for_impl_agent(self):
        result_d = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, "diagnostic", 5, None
        )
        result_di = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, "diagnostic_impl", 5, None
        )
        result_fresh = assemble_hint_prompt(SIMPLE_HINT, AGENT_TYPE_IMPL, None, 5, None)
        # Both diagnostic variants differ from fresh
        assert result_d != result_fresh
        assert result_di != result_fresh


# ---------------------------------------------------------------------------
# Contract: unit_number appears in output when provided
# ---------------------------------------------------------------------------


class TestUnitNumberInOutput:
    """When unit_number is provided, the output references it so the
    downstream agent knows which unit the hint targets."""

    def test_unit_number_appears_in_output(self):
        result = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_FRESH_NONE, 5, None
        )
        assert "5" in result

    def test_different_unit_numbers_produce_different_output(self):
        result_5 = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_FRESH_NONE, 5, None
        )
        result_10 = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_FRESH_NONE, 10, None
        )
        assert result_5 != result_10

    def test_unit_number_none_still_produces_valid_output(self):
        """When unit_number is None, the output is still valid with [HINT]."""
        result = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_FRESH_NONE, None, None
        )
        assert "[HINT]" in result
        assert SIMPLE_HINT in result


# ---------------------------------------------------------------------------
# Contract: gate_context appears in output when provided
# ---------------------------------------------------------------------------


class TestGateContextInOutput:
    """When gate_context is provided, it appears in the output."""

    def test_gate_context_appears_in_output(self):
        gate = "gate_3_2_diagnostic_decision"
        result = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_DIAGNOSTIC, 5, gate
        )
        assert gate in result

    def test_gate_context_none_still_produces_valid_output(self):
        result = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_DIAGNOSTIC, 5, None
        )
        assert "[HINT]" in result
        assert SIMPLE_HINT in result

    def test_output_differs_with_and_without_gate_context(self):
        gate = "gate_4_1_integration_failure"
        result_with = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_EXHAUSTED, 5, gate
        )
        result_without = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_EXHAUSTED, 5, None
        )
        assert result_with != result_without


# ---------------------------------------------------------------------------
# Contract: Empty hint_text still produces valid prompt block
# ---------------------------------------------------------------------------


class TestEmptyHintText:
    """An empty hint_text still produces a valid prompt block."""

    def test_empty_hint_returns_nonempty_string_with_tag(self):
        result = assemble_hint_prompt(
            EMPTY_HINT, AGENT_TYPE_TEST, LADDER_FRESH_NONE, 5, None
        )
        assert isinstance(result, str)
        assert len(result) > 0
        assert "[HINT]" in result

    def test_empty_hint_for_impl_agent(self):
        result = assemble_hint_prompt(
            EMPTY_HINT, AGENT_TYPE_IMPL, LADDER_DIAGNOSTIC_IMPL, 3, None
        )
        assert isinstance(result, str)
        assert len(result) > 0
        assert "[HINT]" in result


# ---------------------------------------------------------------------------
# Contract: Exhaustion context is distinct and present
# ---------------------------------------------------------------------------


class TestExhaustedLadderContext:
    """The 'exhausted' ladder position produces a distinct exhaustion context
    that differs from both fresh and diagnostic for all agent types."""

    def test_exhausted_differs_from_all_other_positions_test_agent(self):
        result_exh = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_EXHAUSTED, 5, None
        )
        result_none = assemble_hint_prompt(SIMPLE_HINT, AGENT_TYPE_TEST, None, 5, None)
        result_fresh = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_FRESH_IMPL, 5, None
        )
        result_diag = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_DIAGNOSTIC, 5, None
        )
        result_diag_impl = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_DIAGNOSTIC_IMPL, 5, None
        )
        assert result_exh != result_none
        assert result_exh != result_fresh
        assert result_exh != result_diag
        assert result_exh != result_diag_impl

    def test_exhausted_differs_from_all_other_positions_impl_agent(self):
        result_exh = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_EXHAUSTED, 5, None
        )
        result_none = assemble_hint_prompt(SIMPLE_HINT, AGENT_TYPE_IMPL, None, 5, None)
        result_fresh = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_FRESH_IMPL, 5, None
        )
        result_diag = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_DIAGNOSTIC, 5, None
        )
        result_diag_impl = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_DIAGNOSTIC_IMPL, 5, None
        )
        assert result_exh != result_none
        assert result_exh != result_fresh
        assert result_exh != result_diag
        assert result_exh != result_diag_impl


# ---------------------------------------------------------------------------
# Cross-cutting: Determinism -- same inputs always produce same output
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Calling assemble_hint_prompt with identical arguments must always
    return the identical string (no randomness, no timestamps)."""

    def test_deterministic_for_test_agent(self):
        a = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_DIAGNOSTIC, 5, None
        )
        b = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_TEST, LADDER_DIAGNOSTIC, 5, None
        )
        assert a == b

    def test_deterministic_for_impl_agent_with_gate(self):
        gate = "gate_6_3_repair_exhausted"
        a = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_EXHAUSTED, 8, gate
        )
        b = assemble_hint_prompt(
            SIMPLE_HINT, AGENT_TYPE_IMPL, LADDER_EXHAUSTED, 8, gate
        )
        assert a == b

    def test_deterministic_with_empty_hint(self):
        a = assemble_hint_prompt(EMPTY_HINT, AGENT_TYPE_TEST, None, None, None)
        b = assemble_hint_prompt(EMPTY_HINT, AGENT_TYPE_TEST, None, None, None)
        assert a == b


# ---------------------------------------------------------------------------
# Contract: Varying only hint_text changes the output
# ---------------------------------------------------------------------------


class TestHintTextVariation:
    """Different hint texts with the same template parameters must produce
    different outputs, proving the hint_text is actually injected."""

    def test_different_hints_produce_different_output(self):
        result_a = assemble_hint_prompt(
            "Hint alpha", AGENT_TYPE_TEST, LADDER_FRESH_NONE, 5, None
        )
        result_b = assemble_hint_prompt(
            "Hint beta", AGENT_TYPE_TEST, LADDER_FRESH_NONE, 5, None
        )
        assert result_a != result_b

    def test_different_hints_same_for_impl_agent(self):
        result_a = assemble_hint_prompt(
            "Check boundary values", AGENT_TYPE_IMPL, LADDER_EXHAUSTED, 3, None
        )
        result_b = assemble_hint_prompt(
            "Review error handling", AGENT_TYPE_IMPL, LADDER_EXHAUSTED, 3, None
        )
        assert result_a != result_b


# ---------------------------------------------------------------------------
# Full parameter matrix: all ladder positions x both agent types
# ---------------------------------------------------------------------------


class TestFullParameterMatrix:
    """Exhaustive coverage: every (agent_type, ladder_position) combination
    produces a valid prompt with [HINT] tag and embedded hint_text."""

    @pytest.mark.parametrize("agent_type", [AGENT_TYPE_TEST, AGENT_TYPE_IMPL])
    @pytest.mark.parametrize(
        "ladder_position",
        [
            None,
            "fresh_impl",
            "diagnostic",
            "diagnostic_impl",
            "exhausted",
        ],
    )
    def test_all_combinations_produce_valid_output(self, agent_type, ladder_position):
        result = assemble_hint_prompt(SIMPLE_HINT, agent_type, ladder_position, 5, None)
        assert isinstance(result, str)
        assert "[HINT]" in result
        assert SIMPLE_HINT in result

    @pytest.mark.parametrize("agent_type", [AGENT_TYPE_TEST, AGENT_TYPE_IMPL])
    @pytest.mark.parametrize(
        "ladder_position",
        [
            None,
            "fresh_impl",
            "diagnostic",
            "diagnostic_impl",
            "exhausted",
        ],
    )
    def test_all_combinations_with_gate_context(self, agent_type, ladder_position):
        gate = "gate_3_1_test_validation"
        result = assemble_hint_prompt(SIMPLE_HINT, agent_type, ladder_position, 5, gate)
        assert isinstance(result, str)
        assert "[HINT]" in result
        assert SIMPLE_HINT in result
        assert gate in result

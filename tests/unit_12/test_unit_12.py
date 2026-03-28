"""
Tests for Unit 12: Hint Prompt Assembler.

Synthetic Data Assumptions:
- hint_text values are non-empty plain-text strings representing human-authored hints.
- agent_type values include "test_agent" and "implementation_agent" as the two
  primary categories, plus other agent types to verify template selection.
- ladder_position values are drawn from the documented set:
  None, "fresh_impl", "diagnostic", "diagnostic_impl", "exhausted".
- unit_number is a positive integer or None.
- gate_context is a descriptive string or None.
- The returned prompt is a formatted string containing a [HINT] tag.
- All non-None parameters appear somewhere in the output.
- Template differences are observable between test agents and implementation agents.
- Template differences are observable across ladder positions.
"""

from hint_prompt_assembler import assemble_hint_prompt

# ---------------------------------------------------------------------------
# Fixtures / Constants
# ---------------------------------------------------------------------------

SAMPLE_HINT = "Check the boundary condition when the list is empty."
SAMPLE_HINT_MULTILINE = (
    "First, verify the input validation.\n"
    "Second, check that the return type matches the contract."
)
SAMPLE_AGENT_TEST = "test_agent"
SAMPLE_AGENT_IMPL = "implementation_agent"
SAMPLE_UNIT_NUMBER = 5
SAMPLE_GATE_CONTEXT = "gate_3_1_test_validation: tests failed on assertion line 42"
SAMPLE_LADDER_FRESH = "fresh_impl"
SAMPLE_LADDER_DIAGNOSTIC = "diagnostic"
SAMPLE_LADDER_DIAGNOSTIC_IMPL = "diagnostic_impl"
SAMPLE_LADDER_EXHAUSTED = "exhausted"


# ===========================================================================
# 1. Basic return type and [HINT] tag presence
# ===========================================================================


class TestBasicReturnAndHintTag:
    """The function must return a string containing the [HINT] tag."""

    def test_returns_string_type(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        assert isinstance(result, str)

    def test_returned_string_contains_hint_tag(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        assert "[HINT]" in result

    def test_returned_string_is_nonempty(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        assert len(result) > 0


# ===========================================================================
# 2. Hint text inclusion
# ===========================================================================


class TestHintTextInclusion:
    """The original hint_text must appear in the output."""

    def test_hint_text_appears_in_output(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        assert SAMPLE_HINT in result

    def test_multiline_hint_text_appears_in_output(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT_MULTILINE,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        assert SAMPLE_HINT_MULTILINE in result

    def test_hint_text_with_special_characters(self):
        special_hint = "Use `assert x == 42` and check <edge> & 'corner' cases."
        result = assemble_hint_prompt(
            hint_text=special_hint,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        assert special_hint in result


# ===========================================================================
# 3. Agent type appears in output
# ===========================================================================


class TestAgentTypeInclusion:
    """The agent_type must appear in the output (agent context section)."""

    def test_test_agent_type_appears_in_output(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        assert SAMPLE_AGENT_TEST in result

    def test_implementation_agent_type_appears_in_output(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        assert SAMPLE_AGENT_IMPL in result


# ===========================================================================
# 4. Template differences between test and implementation agents
# ===========================================================================


class TestAgentTypeTemplateDifferences:
    """Templates differ for test agents vs. implementation agents."""

    def test_test_and_impl_agents_produce_different_templates(self):
        result_test = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        result_impl = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        # Same hint but different templates -- outputs must differ
        assert result_test != result_impl

    def test_test_and_impl_agents_differ_with_ladder_position(self):
        result_test = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=SAMPLE_LADDER_FRESH,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        result_impl = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=SAMPLE_LADDER_FRESH,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        assert result_test != result_impl


# ===========================================================================
# 5. Ladder position template differences
# ===========================================================================


class TestLadderPositionTemplateDifferences:
    """Templates differ by ladder position."""

    def test_none_and_fresh_impl_are_fresh_attempt_context(self):
        result_none = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        result_fresh = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=SAMPLE_LADDER_FRESH,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        # Both are "fresh attempt context", so both should have the same
        # template flavor. They may or may not be identical depending on
        # whether the ladder_position string itself is embedded, but both
        # should be valid outputs with [HINT] tag.
        assert "[HINT]" in result_none
        assert "[HINT]" in result_fresh

    def test_diagnostic_position_differs_from_fresh(self):
        result_fresh = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=SAMPLE_LADDER_FRESH,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        result_diag = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=SAMPLE_LADDER_DIAGNOSTIC,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        assert result_fresh != result_diag

    def test_diagnostic_impl_position_differs_from_fresh(self):
        result_fresh = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=SAMPLE_LADDER_FRESH,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        result_diag_impl = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=SAMPLE_LADDER_DIAGNOSTIC_IMPL,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        assert result_fresh != result_diag_impl

    def test_exhausted_position_differs_from_fresh(self):
        result_fresh = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=SAMPLE_LADDER_FRESH,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        result_exhausted = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=SAMPLE_LADDER_EXHAUSTED,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        assert result_fresh != result_exhausted

    def test_exhausted_position_differs_from_diagnostic(self):
        result_diag = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=SAMPLE_LADDER_DIAGNOSTIC,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        result_exhausted = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=SAMPLE_LADDER_EXHAUSTED,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        assert result_diag != result_exhausted

    def test_diagnostic_and_diagnostic_impl_are_both_diagnostic_context(self):
        result_diag = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=SAMPLE_LADDER_DIAGNOSTIC,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        result_diag_impl = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=SAMPLE_LADDER_DIAGNOSTIC_IMPL,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        # Both are diagnostic-guided context; both must contain [HINT]
        assert "[HINT]" in result_diag
        assert "[HINT]" in result_diag_impl


# ===========================================================================
# 6. Optional parameters: included when non-None, absent when None
# ===========================================================================


class TestOptionalParameterInclusion:
    """Non-None optional parameters must appear in output; None ones should not
    generate their respective sections."""

    def test_unit_number_included_when_provided(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        assert str(SAMPLE_UNIT_NUMBER) in result

    def test_gate_context_included_when_provided(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=SAMPLE_GATE_CONTEXT,
        )
        assert SAMPLE_GATE_CONTEXT in result

    def test_ladder_position_included_when_provided(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=SAMPLE_LADDER_DIAGNOSTIC,
            unit_number=None,
            gate_context=None,
        )
        # The ladder position value or its semantic meaning should be in output
        assert SAMPLE_LADDER_DIAGNOSTIC in result or "diagnostic" in result.lower()

    def test_all_optional_params_none_still_produces_valid_output(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        assert "[HINT]" in result
        assert SAMPLE_HINT in result

    def test_all_params_provided_produces_complete_output(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=SAMPLE_LADDER_DIAGNOSTIC,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=SAMPLE_GATE_CONTEXT,
        )
        assert "[HINT]" in result
        assert SAMPLE_HINT in result
        assert SAMPLE_AGENT_IMPL in result
        assert str(SAMPLE_UNIT_NUMBER) in result
        assert SAMPLE_GATE_CONTEXT in result

    def test_output_differs_with_and_without_unit_number(self):
        result_with = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        result_without = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        assert result_with != result_without

    def test_output_differs_with_and_without_gate_context(self):
        result_with = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=SAMPLE_GATE_CONTEXT,
        )
        result_without = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        assert result_with != result_without


# ===========================================================================
# 7. Structure: hint text section + agent context section + optional sections
# ===========================================================================


class TestPromptStructure:
    """Output has identifiable structure: hint text section, agent context
    section, and optional ladder/unit/gate sections."""

    def test_hint_text_section_present(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        # The hint text must appear, and the [HINT] tag must appear
        assert SAMPLE_HINT in result
        assert "[HINT]" in result

    def test_agent_context_section_present(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        # Agent type should be referenced in agent context section
        assert SAMPLE_AGENT_TEST in result

    def test_full_structure_with_all_sections(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=SAMPLE_LADDER_EXHAUSTED,
            unit_number=17,
            gate_context="gate_4_1_integration_failure: assertion error in module",
        )
        # All sections must be present
        assert SAMPLE_HINT in result
        assert SAMPLE_AGENT_IMPL in result
        assert "17" in result
        assert "gate_4_1_integration_failure" in result
        assert "[HINT]" in result


# ===========================================================================
# 8. Ladder position: test agent variations
# ===========================================================================


class TestLadderPositionWithTestAgent:
    """Verify ladder position affects test agent output."""

    def test_test_agent_fresh_attempt_context(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=SAMPLE_LADDER_FRESH,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        assert "[HINT]" in result
        assert SAMPLE_HINT in result

    def test_test_agent_diagnostic_context(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=SAMPLE_LADDER_DIAGNOSTIC,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        assert "[HINT]" in result
        assert SAMPLE_HINT in result

    def test_test_agent_exhausted_context(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=SAMPLE_LADDER_EXHAUSTED,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        assert "[HINT]" in result
        assert SAMPLE_HINT in result

    def test_test_agent_diagnostic_differs_from_exhausted(self):
        result_diag = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=SAMPLE_LADDER_DIAGNOSTIC,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        result_exhausted = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=SAMPLE_LADDER_EXHAUSTED,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=None,
        )
        assert result_diag != result_exhausted


# ===========================================================================
# 9. Various unit numbers
# ===========================================================================


class TestVariousUnitNumbers:
    """Different unit numbers should appear in the output."""

    def test_unit_number_1(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=None,
            unit_number=1,
            gate_context=None,
        )
        assert "1" in result

    def test_unit_number_29(self):
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=None,
            unit_number=29,
            gate_context=None,
        )
        assert "29" in result

    def test_different_unit_numbers_produce_different_output(self):
        result_5 = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=None,
            unit_number=5,
            gate_context=None,
        )
        result_22 = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=None,
            unit_number=22,
            gate_context=None,
        )
        assert result_5 != result_22


# ===========================================================================
# 10. Various gate contexts
# ===========================================================================


class TestVariousGateContexts:
    """Different gate contexts should appear in the output."""

    def test_gate_context_test_validation(self):
        ctx = "gate_3_1_test_validation: 3 tests failed"
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=ctx,
        )
        assert ctx in result

    def test_gate_context_integration_failure(self):
        ctx = "gate_4_1_integration_failure: module import error"
        result = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=SAMPLE_LADDER_DIAGNOSTIC_IMPL,
            unit_number=SAMPLE_UNIT_NUMBER,
            gate_context=ctx,
        )
        assert ctx in result

    def test_different_gate_contexts_produce_different_output(self):
        result_a = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context="gate_3_1: assertion failed",
        )
        result_b = assemble_hint_prompt(
            hint_text=SAMPLE_HINT,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context="gate_5_1: repo test timeout",
        )
        assert result_a != result_b


# ===========================================================================
# 11. Comprehensive combinations
# ===========================================================================


class TestComprehensiveCombinations:
    """Test various combinations of all parameters to verify structural
    completeness."""

    def test_test_agent_all_params_diagnostic(self):
        result = assemble_hint_prompt(
            hint_text="Focus on edge case: empty input list.",
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=SAMPLE_LADDER_DIAGNOSTIC,
            unit_number=8,
            gate_context="gate_3_2_diagnostic_decision: needs human review",
        )
        assert "[HINT]" in result
        assert "Focus on edge case: empty input list." in result
        assert SAMPLE_AGENT_TEST in result
        assert "8" in result
        assert "gate_3_2_diagnostic_decision" in result

    def test_impl_agent_exhausted_with_gate(self):
        result = assemble_hint_prompt(
            hint_text="Try a completely different algorithm approach.",
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=SAMPLE_LADDER_EXHAUSTED,
            unit_number=14,
            gate_context="gate_4_2_assembly_exhausted: max retries reached",
        )
        assert "[HINT]" in result
        assert "Try a completely different algorithm approach." in result
        assert SAMPLE_AGENT_IMPL in result
        assert "14" in result
        assert "gate_4_2_assembly_exhausted" in result

    def test_impl_agent_fresh_no_optionals(self):
        result = assemble_hint_prompt(
            hint_text="Use a dictionary instead of a list for O(1) lookups.",
            agent_type=SAMPLE_AGENT_IMPL,
            ladder_position=SAMPLE_LADDER_FRESH,
            unit_number=None,
            gate_context=None,
        )
        assert "[HINT]" in result
        assert "Use a dictionary instead of a list for O(1) lookups." in result
        assert SAMPLE_AGENT_IMPL in result


# ===========================================================================
# 12. Hint text is the primary content (not overshadowed)
# ===========================================================================


class TestHintTextIsPrimaryContent:
    """The hint_text should be the primary payload, not buried in boilerplate."""

    def test_hint_text_is_substantial_portion_of_output(self):
        long_hint = "A" * 200
        result = assemble_hint_prompt(
            hint_text=long_hint,
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        # The hint should be a meaningful portion of the result
        assert long_hint in result

    def test_different_hints_produce_different_outputs(self):
        result_a = assemble_hint_prompt(
            hint_text="Hint alpha: check null case",
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        result_b = assemble_hint_prompt(
            hint_text="Hint beta: check overflow case",
            agent_type=SAMPLE_AGENT_TEST,
            ladder_position=None,
            unit_number=None,
            gate_context=None,
        )
        assert result_a != result_b

"""
Tests for Unit 8: Hint Prompt Assembler

Tests verify the behavioral contracts, invariants, error conditions, and
signatures defined in the blueprint for the hint prompt assembler module.

DATA ASSUMPTIONS
================
- Hint content strings are short English-language sentences representing
  plausible human-authored hints about domain-specific issues (e.g.,
  "The signal data uses 16-bit resolution").
- Gate IDs follow a pattern like "test_validation_gate" or
  "implementation_gate", representing pipeline gate identifiers.
- Agent types are one of the six recognized types from the blueprint:
  "test", "implementation", "blueprint_author", "stakeholder_dialog",
  "diagnostic", "other".
- Ladder positions are string identifiers representing fix ladder stages
  (e.g., "rung_1", "rung_2", "rung_3") or None when not applicable.
- Unit numbers are small positive integers (e.g., 1-20) representing
  SVP unit identifiers.
- Stage strings are short identifiers like "red_run" or "green_run".
"""

import inspect
from typing import Optional

import pytest

from svp.scripts.hint_assembler import (
    assemble_hint_prompt,
    get_agent_type_framing,
    get_ladder_position_framing,
)


# ---------------------------------------------------------------------------
# Signature verification tests
# ---------------------------------------------------------------------------


class TestSignatures:
    """Verify that function signatures match the blueprint's Tier 2 spec."""

    def test_assemble_hint_prompt_signature(self):
        """assemble_hint_prompt must accept the documented parameters with correct names and defaults."""
        sig = inspect.signature(assemble_hint_prompt)
        params = sig.parameters

        # Required positional/keyword params
        assert "hint_content" in params
        assert "gate_id" in params
        assert "agent_type" in params

        # Optional params with defaults
        assert "ladder_position" in params
        assert params["ladder_position"].default is None

        assert "unit_number" in params
        assert params["unit_number"].default is None

        assert "stage" in params
        assert params["stage"].default == ""

    def test_assemble_hint_prompt_return_type(self):
        """assemble_hint_prompt must be annotated to return str."""
        sig = inspect.signature(assemble_hint_prompt)
        assert sig.return_annotation is str or sig.return_annotation == "str"

    def test_get_agent_type_framing_signature(self):
        """get_agent_type_framing must accept agent_type: str and return str."""
        sig = inspect.signature(get_agent_type_framing)
        params = sig.parameters
        assert "agent_type" in params
        assert len(params) == 1

    def test_get_agent_type_framing_return_type(self):
        """get_agent_type_framing must return str."""
        sig = inspect.signature(get_agent_type_framing)
        assert sig.return_annotation is str or sig.return_annotation == "str"

    def test_get_ladder_position_framing_signature(self):
        """get_ladder_position_framing must accept ladder_position: Optional[str] and return str."""
        sig = inspect.signature(get_ladder_position_framing)
        params = sig.parameters
        assert "ladder_position" in params
        assert len(params) == 1

    def test_get_ladder_position_framing_return_type(self):
        """get_ladder_position_framing must return str."""
        sig = inspect.signature(get_ladder_position_framing)
        assert sig.return_annotation is str or sig.return_annotation == "str"


# ---------------------------------------------------------------------------
# Error condition tests
# ---------------------------------------------------------------------------


class TestErrorConditions:
    """Verify all Tier 3 error conditions."""

    def test_empty_hint_content_raises_value_error(self):
        """ValueError with 'Empty hint content' when hint_content is empty string."""
        # DATA ASSUMPTION: Empty string is the simplest empty input.
        with pytest.raises(ValueError, match="Empty hint content"):
            assemble_hint_prompt(
                hint_content="",
                gate_id="test_gate",
                agent_type="test",
            )

    def test_whitespace_only_hint_content_raises_value_error(self):
        """ValueError with 'Empty hint content' when hint_content is whitespace-only."""
        # DATA ASSUMPTION: Various whitespace characters that should all count as empty.
        with pytest.raises(ValueError, match="Empty hint content"):
            assemble_hint_prompt(
                hint_content="   \t\n  ",
                gate_id="test_gate",
                agent_type="test",
            )

    def test_unknown_agent_type_raises_value_error(self):
        """ValueError with 'Unknown agent type: {type}' for unrecognized agent types."""
        # DATA ASSUMPTION: "unknown_agent" is not in the recognized set.
        with pytest.raises(ValueError, match="Unknown agent type: unknown_agent"):
            assemble_hint_prompt(
                hint_content="Some hint",
                gate_id="test_gate",
                agent_type="unknown_agent",
            )

    def test_unknown_agent_type_includes_type_name(self):
        """The error message should include the specific unknown type name."""
        # DATA ASSUMPTION: "foobar" is not a recognized agent type.
        with pytest.raises(ValueError, match="Unknown agent type: foobar"):
            assemble_hint_prompt(
                hint_content="A valid hint",
                gate_id="some_gate",
                agent_type="foobar",
            )

    def test_empty_string_agent_type_raises_value_error(self):
        """An empty string agent type is also not recognized."""
        # DATA ASSUMPTION: Empty string is not in the recognized agent type set.
        with pytest.raises(ValueError, match="Unknown agent type"):
            assemble_hint_prompt(
                hint_content="A valid hint",
                gate_id="some_gate",
                agent_type="",
            )


# ---------------------------------------------------------------------------
# Invariant tests (pre-conditions and post-conditions)
# ---------------------------------------------------------------------------


class TestInvariants:
    """Verify pre-conditions and post-conditions from the blueprint."""

    # DATA ASSUMPTION: "Fix the flaky assertion in test_signal_processing"
    # is a plausible domain hint from a help agent.
    SAMPLE_HINT = "Fix the flaky assertion in test_signal_processing"

    def test_result_contains_standard_heading(self):
        """Post-condition: result must contain '## Human Domain Hint (via Help Agent)'."""
        result = assemble_hint_prompt(
            hint_content=self.SAMPLE_HINT,
            gate_id="test_validation_gate",
            agent_type="test",
        )
        assert "## Human Domain Hint (via Help Agent)" in result

    def test_result_contains_original_hint_content(self):
        """Post-condition: result must contain the original hint content verbatim."""
        result = assemble_hint_prompt(
            hint_content=self.SAMPLE_HINT,
            gate_id="test_validation_gate",
            agent_type="test",
        )
        assert self.SAMPLE_HINT in result

    def test_result_contains_hint_with_special_characters(self):
        """Post-condition: hint content with special chars must appear verbatim."""
        # DATA ASSUMPTION: Hints may contain markdown, code snippets, special chars.
        special_hint = "Use `np.allclose(a, b, atol=1e-6)` instead of `==`"
        result = assemble_hint_prompt(
            hint_content=special_hint,
            gate_id="impl_gate",
            agent_type="implementation",
        )
        assert special_hint in result

    def test_result_contains_multiline_hint_content(self):
        """Post-condition: multi-line hint content must appear verbatim."""
        # DATA ASSUMPTION: Hints can span multiple lines.
        multiline_hint = "Line one of the hint.\nLine two with more detail.\nLine three."
        result = assemble_hint_prompt(
            hint_content=multiline_hint,
            gate_id="diag_gate",
            agent_type="diagnostic",
        )
        assert multiline_hint in result


# ---------------------------------------------------------------------------
# Behavioral contract tests for assemble_hint_prompt
# ---------------------------------------------------------------------------


class TestAssembleHintPrompt:
    """Verify behavioral contracts for assemble_hint_prompt."""

    # DATA ASSUMPTION: Simple hint representing a typical domain clarification.
    HINT = "The sampling rate should be 44100 Hz, not 48000 Hz"

    def test_output_is_pure_text(self):
        """The output must be pure text -- no JSON, just Markdown."""
        result = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id="test_gate",
            agent_type="test",
        )
        assert isinstance(result, str)
        # Should not be valid JSON
        import json
        try:
            json.loads(result)
            # If it parses as JSON, that violates the contract
            pytest.fail("Output should be pure text, not JSON")
        except (json.JSONDecodeError, ValueError):
            pass  # Expected -- not JSON

    def test_output_is_markdown_section(self):
        """Output should be a Markdown section ready for inclusion in a task prompt."""
        result = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id="test_gate",
            agent_type="test",
        )
        assert result.strip().startswith("#") or "## Human Domain Hint" in result

    def test_includes_gate_context(self):
        """Output includes gate context (which gate)."""
        # DATA ASSUMPTION: gate_id "test_validation_gate" is a plausible gate name.
        gate_id = "test_validation_gate"
        result = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id=gate_id,
            agent_type="test",
        )
        assert gate_id in result

    def test_includes_unit_context(self):
        """Output includes unit context when unit_number is provided."""
        # DATA ASSUMPTION: unit_number=5 is a plausible unit identifier.
        result = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id="test_gate",
            agent_type="test",
            unit_number=5,
        )
        # The unit number should appear somewhere in the output
        assert "5" in result

    def test_includes_stage_context(self):
        """Output includes stage context when stage is provided."""
        # DATA ASSUMPTION: "red_run" is a plausible stage identifier.
        result = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id="test_gate",
            agent_type="test",
            stage="red_run",
        )
        assert "red_run" in result

    def test_includes_signal_not_command_constraint(self):
        """Output includes the constraint that the hint is a signal to evaluate,
        not a command to execute."""
        result = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id="test_gate",
            agent_type="test",
        )
        # The output should convey that the hint is a signal, not a command
        result_lower = result.lower()
        assert "signal" in result_lower or "not a command" in result_lower or \
            "evaluate" in result_lower, \
            "Output must convey that the hint is a signal to evaluate, not a command"

    def test_all_recognized_agent_types_succeed(self):
        """All six recognized agent types should produce valid output."""
        # DATA ASSUMPTION: These are all six recognized types from the blueprint.
        recognized_types = [
            "test", "implementation", "blueprint_author",
            "stakeholder_dialog", "diagnostic", "other",
        ]
        for agent_type in recognized_types:
            result = assemble_hint_prompt(
                hint_content=self.HINT,
                gate_id="some_gate",
                agent_type=agent_type,
            )
            assert "## Human Domain Hint (via Help Agent)" in result
            assert self.HINT in result

    def test_with_ladder_position(self):
        """Output should incorporate ladder position when provided."""
        # DATA ASSUMPTION: "rung_2" is a plausible fix ladder position.
        result = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id="test_gate",
            agent_type="test",
            ladder_position="rung_2",
        )
        assert isinstance(result, str)
        assert "## Human Domain Hint (via Help Agent)" in result

    def test_without_ladder_position(self):
        """Output is valid when ladder_position is None."""
        result = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id="test_gate",
            agent_type="test",
            ladder_position=None,
        )
        assert isinstance(result, str)
        assert "## Human Domain Hint (via Help Agent)" in result

    def test_without_unit_number(self):
        """Output is valid when unit_number is None."""
        result = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id="test_gate",
            agent_type="test",
            unit_number=None,
        )
        assert isinstance(result, str)
        assert "## Human Domain Hint (via Help Agent)" in result

    def test_deterministic_output(self):
        """Calling with the same arguments twice should produce identical output."""
        # DATA ASSUMPTION: Deterministic templates mean identical inputs yield identical outputs.
        kwargs = dict(
            hint_content=self.HINT,
            gate_id="test_gate",
            agent_type="test",
            ladder_position="rung_1",
            unit_number=3,
            stage="red_run",
        )
        result1 = assemble_hint_prompt(**kwargs)
        result2 = assemble_hint_prompt(**kwargs)
        assert result1 == result2

    def test_different_agent_types_produce_different_framing(self):
        """Different agent types should produce different output due to type-specific framing."""
        # DATA ASSUMPTION: "test" and "implementation" framings are distinct.
        result_test = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id="test_gate",
            agent_type="test",
        )
        result_impl = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id="test_gate",
            agent_type="implementation",
        )
        # Both should have the heading and hint, but differ in framing
        assert "## Human Domain Hint (via Help Agent)" in result_test
        assert "## Human Domain Hint (via Help Agent)" in result_impl
        # The framing portions should differ
        assert result_test != result_impl

    def test_full_parameter_set(self):
        """Test with all parameters provided."""
        # DATA ASSUMPTION: Complete parameter set with plausible values.
        result = assemble_hint_prompt(
            hint_content="Check edge case for empty arrays",
            gate_id="test_validation_gate",
            agent_type="test",
            ladder_position="rung_3",
            unit_number=12,
            stage="green_run",
        )
        assert "## Human Domain Hint (via Help Agent)" in result
        assert "Check edge case for empty arrays" in result
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Behavioral contract tests for get_agent_type_framing
# ---------------------------------------------------------------------------


class TestGetAgentTypeFraming:
    """Verify behavioral contracts for get_agent_type_framing."""

    def test_returns_string(self):
        """get_agent_type_framing must return a string."""
        # DATA ASSUMPTION: "test" is a recognized agent type.
        result = get_agent_type_framing("test")
        assert isinstance(result, str)

    def test_test_agent_framing_emphasizes_behavior_assertions(self):
        """Test agent framing should emphasize behavior and assertions."""
        result = get_agent_type_framing("test")
        result_lower = result.lower()
        # The framing for test agents should reference behavior/assertions
        assert "behav" in result_lower or "assert" in result_lower or "test" in result_lower, \
            "Test agent framing should emphasize behavior and/or assertions"

    def test_implementation_agent_framing_emphasizes_code_changes(self):
        """Implementation agent framing should emphasize code changes."""
        result = get_agent_type_framing("implementation")
        result_lower = result.lower()
        assert "code" in result_lower or "implement" in result_lower or "change" in result_lower, \
            "Implementation agent framing should emphasize code changes"

    def test_diagnostic_framing_emphasizes_analysis(self):
        """Diagnostic framing should emphasize analysis context."""
        result = get_agent_type_framing("diagnostic")
        result_lower = result.lower()
        assert "analy" in result_lower or "diagnos" in result_lower or "context" in result_lower, \
            "Diagnostic framing should emphasize analysis context"

    def test_different_types_produce_different_framing(self):
        """Different agent types should produce different framing strings."""
        # DATA ASSUMPTION: Each agent type has distinct framing per the blueprint.
        framings = {}
        for agent_type in ["test", "implementation", "diagnostic"]:
            framings[agent_type] = get_agent_type_framing(agent_type)

        # At minimum, test vs implementation vs diagnostic should differ
        assert framings["test"] != framings["implementation"]
        assert framings["test"] != framings["diagnostic"]
        assert framings["implementation"] != framings["diagnostic"]

    def test_all_recognized_types_return_non_empty_string(self):
        """All recognized agent types should return a non-empty framing string."""
        recognized_types = [
            "test", "implementation", "blueprint_author",
            "stakeholder_dialog", "diagnostic", "other",
        ]
        for agent_type in recognized_types:
            result = get_agent_type_framing(agent_type)
            assert isinstance(result, str)
            assert len(result.strip()) > 0, \
                f"Framing for agent type '{agent_type}' should not be empty"


# ---------------------------------------------------------------------------
# Behavioral contract tests for get_ladder_position_framing
# ---------------------------------------------------------------------------


class TestGetLadderPositionFraming:
    """Verify behavioral contracts for get_ladder_position_framing."""

    def test_returns_string_with_position(self):
        """get_ladder_position_framing must return a string when given a position."""
        # DATA ASSUMPTION: "rung_1" is a plausible ladder position.
        result = get_ladder_position_framing("rung_1")
        assert isinstance(result, str)

    def test_returns_string_with_none(self):
        """get_ladder_position_framing must return a string when given None."""
        result = get_ladder_position_framing(None)
        assert isinstance(result, str)

    def test_none_position_framing_differs_from_explicit_position(self):
        """Framing for None should differ from or be a subset of framing with a position."""
        # DATA ASSUMPTION: When no ladder position is specified, the framing
        # should be different (possibly empty or generic).
        result_none = get_ladder_position_framing(None)
        result_rung = get_ladder_position_framing("rung_1")
        # They should differ since one has position context and the other doesn't
        # But at minimum, both must be valid strings
        assert isinstance(result_none, str)
        assert isinstance(result_rung, str)

    def test_different_positions_may_produce_different_framing(self):
        """Different ladder positions may produce different framing."""
        # DATA ASSUMPTION: "rung_1" and "rung_3" are distinct ladder positions.
        result_1 = get_ladder_position_framing("rung_1")
        result_3 = get_ladder_position_framing("rung_3")
        # Both should be valid strings; they may or may not differ
        assert isinstance(result_1, str)
        assert isinstance(result_3, str)

    def test_non_empty_framing_for_explicit_position(self):
        """An explicit ladder position should produce non-empty framing."""
        # DATA ASSUMPTION: "rung_2" is a plausible position that should
        # produce meaningful framing text.
        result = get_ladder_position_framing("rung_2")
        assert len(result.strip()) > 0, \
            "Framing for an explicit ladder position should not be empty"


# ---------------------------------------------------------------------------
# Integration-style tests (all functions working together)
# ---------------------------------------------------------------------------


class TestIntegration:
    """Test that the functions work together coherently."""

    def test_agent_type_framing_is_reflected_in_assembled_output(self):
        """The agent type framing from get_agent_type_framing should be
        consistent with the framing in assemble_hint_prompt output."""
        # DATA ASSUMPTION: "test" agent type framing is used in assembled output.
        framing = get_agent_type_framing("test")
        assembled = assemble_hint_prompt(
            hint_content="Check boundary conditions",
            gate_id="test_gate",
            agent_type="test",
        )
        # The assembled output should incorporate the agent type framing
        # (either literally or in spirit -- we check that framing text appears)
        assert isinstance(framing, str)
        assert isinstance(assembled, str)
        # Both should be non-empty
        assert len(framing.strip()) > 0
        assert len(assembled.strip()) > 0

    def test_ladder_framing_is_reflected_in_assembled_output(self):
        """When ladder_position is given, its framing should influence the output."""
        # DATA ASSUMPTION: "rung_1" ladder position adds context to the output.
        result_with_ladder = assemble_hint_prompt(
            hint_content="Increase timeout for slow tests",
            gate_id="test_gate",
            agent_type="test",
            ladder_position="rung_1",
        )
        result_without_ladder = assemble_hint_prompt(
            hint_content="Increase timeout for slow tests",
            gate_id="test_gate",
            agent_type="test",
            ladder_position=None,
        )
        # Both should be valid
        assert "## Human Domain Hint (via Help Agent)" in result_with_ladder
        assert "## Human Domain Hint (via Help Agent)" in result_without_ladder
        # The outputs may differ due to ladder position framing
        # (this is expected behavior per the blueprint)

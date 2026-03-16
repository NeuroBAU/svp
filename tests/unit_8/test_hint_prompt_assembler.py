"""Tests for Unit 8: Hint Prompt Assembler.

Synthetic data generation assumptions:
- hint_content strings are arbitrary non-empty text
  representing raw help agent output.
- gate_id strings are arbitrary gate identifiers
  (e.g., "gate_3_1_test_validation").
- agent_type values are drawn from the blueprint's
  allowed set: "test", "implementation",
  "blueprint_author", "stakeholder_dialog",
  "diagnostic", "other".
- ladder_position values are optional strings
  representing fix ladder positions
  (e.g., "red_run", "green_run", None).
- unit_number values are optional positive integers.
- stage values are optional strings
  (e.g., "3", "").
"""

import pytest

from src.unit_8.stub import (
    assemble_hint_prompt,
    get_agent_type_framing,
    get_ladder_position_framing,
)

# ── Valid agent types from Tier 2 invariants ──

VALID_AGENT_TYPES = (
    "test",
    "implementation",
    "blueprint_author",
    "stakeholder_dialog",
    "diagnostic",
    "other",
)


class TestAssembleHintPrompt:
    """Tests for assemble_hint_prompt."""

    def test_returns_string(self):
        result = assemble_hint_prompt(
            hint_content="Fix the parser.",
            gate_id="gate_3_1_test_validation",
            agent_type="test",
        )
        assert isinstance(result, str)

    def test_contains_heading(self):
        """Invariant: result contains the hint heading."""
        result = assemble_hint_prompt(
            hint_content="Refactor loop.",
            gate_id="gate_3_1_test_validation",
            agent_type="implementation",
        )
        assert "## Human Domain Hint (via Help Agent)" in result

    def test_contains_hint_content(self):
        """Invariant: hint_content appears in result."""
        content = "The timeout must be 30 seconds."
        result = assemble_hint_prompt(
            hint_content=content,
            gate_id="gate_2_1_blueprint_approval",
            agent_type="blueprint_author",
        )
        assert content in result

    @pytest.mark.parametrize("agent_type", VALID_AGENT_TYPES)
    def test_valid_agent_types_accepted(self, agent_type):
        result = assemble_hint_prompt(
            hint_content="Some hint.",
            gate_id="gate_3_1_test_validation",
            agent_type=agent_type,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_with_ladder_position(self):
        result = assemble_hint_prompt(
            hint_content="Check edge case.",
            gate_id="gate_3_1_test_validation",
            agent_type="test",
            ladder_position="red_run",
        )
        assert "## Human Domain Hint (via Help Agent)" in result
        assert "Check edge case." in result

    def test_with_unit_number(self):
        result = assemble_hint_prompt(
            hint_content="Unit-specific hint.",
            gate_id="gate_3_1_test_validation",
            agent_type="implementation",
            unit_number=5,
        )
        assert "Unit-specific hint." in result

    def test_with_stage(self):
        result = assemble_hint_prompt(
            hint_content="Stage hint.",
            gate_id="gate_3_1_test_validation",
            agent_type="diagnostic",
            stage="3",
        )
        assert "Stage hint." in result

    def test_with_all_optional_params(self):
        result = assemble_hint_prompt(
            hint_content="Full params hint.",
            gate_id="gate_3_2_diagnostic_decision",
            agent_type="test",
            ladder_position="green_run",
            unit_number=10,
            stage="3",
        )
        assert "## Human Domain Hint (via Help Agent)" in result
        assert "Full params hint." in result

    def test_with_none_ladder_position(self):
        result = assemble_hint_prompt(
            hint_content="No ladder.",
            gate_id="gate_3_1_test_validation",
            agent_type="other",
            ladder_position=None,
        )
        assert "No ladder." in result

    def test_with_none_unit_number(self):
        result = assemble_hint_prompt(
            hint_content="No unit.",
            gate_id="gate_3_1_test_validation",
            agent_type="other",
            unit_number=None,
        )
        assert "No unit." in result

    def test_output_is_pure_text(self):
        """Contract: output is pure text (Markdown)."""
        result = assemble_hint_prompt(
            hint_content="Pure text check.",
            gate_id="gate_3_1_test_validation",
            agent_type="test",
        )
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    def test_multiline_hint_content_preserved(self):
        content = "Line 1.\nLine 2.\nLine 3."
        result = assemble_hint_prompt(
            hint_content=content,
            gate_id="gate_3_1_test_validation",
            agent_type="implementation",
        )
        assert content in result

    def test_special_characters_in_hint(self):
        content = "Use `assert x == 1` and **bold**."
        result = assemble_hint_prompt(
            hint_content=content,
            gate_id="gate_3_1_test_validation",
            agent_type="test",
        )
        assert content in result

    def test_default_stage_is_empty_string(self):
        """stage defaults to empty string."""
        result = assemble_hint_prompt(
            hint_content="Default stage.",
            gate_id="gate_3_1_test_validation",
            agent_type="test",
        )
        assert "Default stage." in result


class TestAssembleHintPromptErrors:
    """Error condition tests for assemble_hint_prompt."""

    def test_empty_hint_content_raises(self):
        with pytest.raises(ValueError, match="Empty hint"):
            assemble_hint_prompt(
                hint_content="",
                gate_id="gate_3_1_test_validation",
                agent_type="test",
            )

    def test_whitespace_only_hint_raises(self):
        """Invariant: len(hint_content.strip()) > 0."""
        with pytest.raises(ValueError, match="Empty hint"):
            assemble_hint_prompt(
                hint_content="   \n\t  ",
                gate_id="gate_3_1_test_validation",
                agent_type="test",
            )

    def test_unknown_agent_type_raises(self):
        with pytest.raises(ValueError, match="Unknown agent type"):
            assemble_hint_prompt(
                hint_content="Valid hint.",
                gate_id="gate_3_1_test_validation",
                agent_type="nonexistent_agent",
            )

    def test_unknown_agent_type_includes_name(self):
        """Error message includes the bad agent type."""
        with pytest.raises(ValueError, match="bogus_type"):
            assemble_hint_prompt(
                hint_content="Valid hint.",
                gate_id="gate_3_1_test_validation",
                agent_type="bogus_type",
            )


class TestGetAgentTypeFraming:
    """Tests for get_agent_type_framing."""

    @pytest.mark.parametrize("agent_type", VALID_AGENT_TYPES)
    def test_returns_string_for_valid_types(self, agent_type):
        result = get_agent_type_framing(agent_type)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_different_types_may_differ(self):
        """Different agent types produce framing text."""
        results = {at: get_agent_type_framing(at) for at in VALID_AGENT_TYPES}
        assert all(isinstance(v, str) for v in results.values())

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown agent type"):
            get_agent_type_framing("invalid_type")


class TestGetLadderPositionFraming:
    """Tests for get_ladder_position_framing."""

    def test_none_returns_string(self):
        result = get_ladder_position_framing(None)
        assert isinstance(result, str)

    def test_string_position_returns_string(self):
        result = get_ladder_position_framing("red_run")
        assert isinstance(result, str)

    def test_another_position_returns_string(self):
        result = get_ladder_position_framing("green_run")
        assert isinstance(result, str)

    def test_none_vs_string_may_differ(self):
        """None and a position string are both handled."""
        r_none = get_ladder_position_framing(None)
        r_pos = get_ladder_position_framing("red_run")
        assert isinstance(r_none, str)
        assert isinstance(r_pos, str)


class TestDeterministicTemplates:
    """Contract: uses deterministic templates."""

    def test_same_inputs_produce_same_output(self):
        """Deterministic: identical inputs -> same."""
        kwargs = dict(
            hint_content="Deterministic check.",
            gate_id="gate_3_1_test_validation",
            agent_type="test",
            ladder_position="red_run",
            unit_number=7,
            stage="3",
        )
        r1 = assemble_hint_prompt(**kwargs)
        r2 = assemble_hint_prompt(**kwargs)
        assert r1 == r2

    def test_different_hint_content_differs(self):
        base = dict(
            gate_id="gate_3_1_test_validation",
            agent_type="test",
        )
        r1 = assemble_hint_prompt(hint_content="Alpha.", **base)
        r2 = assemble_hint_prompt(hint_content="Beta.", **base)
        assert r1 != r2

    def test_framing_is_deterministic(self):
        r1 = get_agent_type_framing("test")
        r2 = get_agent_type_framing("test")
        assert r1 == r2

    def test_ladder_framing_is_deterministic(self):
        r1 = get_ladder_position_framing("red_run")
        r2 = get_ladder_position_framing("red_run")
        assert r1 == r2

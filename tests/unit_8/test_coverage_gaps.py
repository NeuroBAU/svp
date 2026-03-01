"""
Additional tests for Unit 8: Hint Prompt Assembler -- Coverage Gaps

These tests cover behavioral contracts, invariants, and error conditions
from the blueprint that are not exercised by the primary test suite.

DATA ASSUMPTIONS
================
- Hint content strings are short English-language sentences representing
  plausible human-authored hints about domain-specific issues.
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

import pytest

from svp.scripts.hint_assembler import (
    assemble_hint_prompt,
    get_agent_type_framing,
    get_ladder_position_framing,
)


# ---------------------------------------------------------------------------
# Gap 1: get_agent_type_framing raises ValueError for unknown agent types
#
# The blueprint invariant says agent_type must be a recognized type, and
# the error condition says ValueError: "Unknown agent type: {type}".
# The existing test suite only tests this error via assemble_hint_prompt,
# not directly on get_agent_type_framing.
# ---------------------------------------------------------------------------


class TestGetAgentTypeFramingErrorConditions:
    """Verify that get_agent_type_framing raises ValueError for unknown types."""

    def test_unknown_agent_type_raises_value_error(self):
        """get_agent_type_framing should raise ValueError for unrecognized agent type."""
        # DATA ASSUMPTION: "nonexistent_agent" is not in the recognized set.
        with pytest.raises(ValueError, match="Unknown agent type: nonexistent_agent"):
            get_agent_type_framing("nonexistent_agent")

    def test_empty_string_agent_type_raises_value_error(self):
        """get_agent_type_framing should raise ValueError for empty string agent type."""
        # DATA ASSUMPTION: Empty string is not a recognized agent type.
        with pytest.raises(ValueError, match="Unknown agent type"):
            get_agent_type_framing("")


# ---------------------------------------------------------------------------
# Gap 2: Agent type framing text literally appears in assembled output
#
# The blueprint says assemble_hint_prompt uses deterministic templates and
# includes "framing appropriate to the receiving agent type". The existing
# integration test only checks that both framing and assembled output are
# non-empty strings, but does not verify the framing text actually appears
# in the assembled output.
# ---------------------------------------------------------------------------


class TestAgentFramingIncorporation:
    """Verify that get_agent_type_framing output is literally included
    in the assembled prompt output."""

    # DATA ASSUMPTION: "Consider the data alignment issue" is a plausible hint.
    HINT = "Consider the data alignment issue"

    def test_test_agent_framing_appears_in_assembled_output(self):
        """The framing returned by get_agent_type_framing('test') must appear
        verbatim in the output of assemble_hint_prompt with agent_type='test'."""
        framing = get_agent_type_framing("test")
        assembled = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id="test_gate",
            agent_type="test",
        )
        assert framing in assembled, (
            "Agent type framing text must appear in the assembled output"
        )

    def test_implementation_agent_framing_appears_in_assembled_output(self):
        """The framing returned by get_agent_type_framing('implementation') must
        appear verbatim in the output of assemble_hint_prompt with
        agent_type='implementation'."""
        framing = get_agent_type_framing("implementation")
        assembled = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id="impl_gate",
            agent_type="implementation",
        )
        assert framing in assembled, (
            "Agent type framing text must appear in the assembled output"
        )

    def test_diagnostic_agent_framing_appears_in_assembled_output(self):
        """The framing returned by get_agent_type_framing('diagnostic') must
        appear verbatim in the output of assemble_hint_prompt with
        agent_type='diagnostic'."""
        framing = get_agent_type_framing("diagnostic")
        assembled = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id="diag_gate",
            agent_type="diagnostic",
        )
        assert framing in assembled, (
            "Agent type framing text must appear in the assembled output"
        )

    def test_all_agent_type_framings_appear_in_assembled_output(self):
        """For every recognized agent type, the framing text must appear in
        the assembled output."""
        # DATA ASSUMPTION: All six recognized agent types from the blueprint.
        recognized_types = [
            "test", "implementation", "blueprint_author",
            "stakeholder_dialog", "diagnostic", "other",
        ]
        for agent_type in recognized_types:
            framing = get_agent_type_framing(agent_type)
            assembled = assemble_hint_prompt(
                hint_content=self.HINT,
                gate_id="gate_for_" + agent_type,
                agent_type=agent_type,
            )
            assert framing in assembled, (
                f"Framing for agent type '{agent_type}' must appear "
                f"in the assembled output"
            )


# ---------------------------------------------------------------------------
# Gap 3: Ladder position framing text literally appears in assembled output
#
# The blueprint says the output includes framing based on ladder position.
# The existing test compares with/without ladder but does not verify the
# framing text from get_ladder_position_framing appears in the assembled
# output.
# ---------------------------------------------------------------------------


class TestLadderFramingIncorporation:
    """Verify that get_ladder_position_framing output is incorporated
    into the assembled prompt when a ladder_position is provided."""

    # DATA ASSUMPTION: "Adjust the retry logic" is a plausible hint.
    HINT = "Adjust the retry logic"

    def test_ladder_position_framing_appears_in_assembled_output(self):
        """When ladder_position is provided, the framing text from
        get_ladder_position_framing must appear in the assembled output."""
        # DATA ASSUMPTION: "rung_1" is a plausible ladder position.
        ladder_pos = "rung_1"
        framing = get_ladder_position_framing(ladder_pos)
        assembled = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id="test_gate",
            agent_type="test",
            ladder_position=ladder_pos,
        )
        # The framing should be non-empty for explicit positions
        assert len(framing.strip()) > 0
        assert framing in assembled, (
            "Ladder position framing text must appear in the assembled output"
        )


# ---------------------------------------------------------------------------
# Gap 4: Ladder position with None actually differs from explicit position
#
# The existing test_none_position_framing_differs_from_explicit_position
# only checks both are valid strings, without asserting they differ.
# The blueprint says get_ladder_position_framing adjusts framing based
# on position, implying None (no position) and a specific position
# produce different framing.
# ---------------------------------------------------------------------------


class TestLadderPositionDiffers:
    """Verify that None ladder position produces different framing than
    an explicit ladder position."""

    def test_none_framing_differs_from_explicit_framing(self):
        """Framing for None must differ from framing for an explicit position."""
        # DATA ASSUMPTION: "rung_1" is a plausible ladder position.
        result_none = get_ladder_position_framing(None)
        result_rung = get_ladder_position_framing("rung_1")
        assert result_none != result_rung, (
            "None ladder position framing must differ from explicit position framing"
        )


# ---------------------------------------------------------------------------
# Gap 5: Full parameter set verifies all context pieces appear simultaneously
#
# The existing test_full_parameter_set only checks heading and hint content.
# The blueprint says the output includes gate context (which gate, which
# unit, which stage). With all parameters provided, all three should appear.
# ---------------------------------------------------------------------------


class TestFullContextInOutput:
    """Verify that when all parameters are provided, all context pieces
    (gate_id, unit_number, stage) appear in the output simultaneously."""

    def test_all_context_pieces_present(self):
        """When gate_id, unit_number, and stage are all provided, each must
        appear in the assembled output."""
        # DATA ASSUMPTION: Plausible values for all context fields.
        result = assemble_hint_prompt(
            hint_content="Check the boundary values",
            gate_id="test_validation_gate",
            agent_type="test",
            ladder_position="rung_2",
            unit_number=7,
            stage="green_run",
        )
        assert "test_validation_gate" in result, "gate_id must appear in output"
        assert "7" in result, "unit_number must appear in output"
        assert "green_run" in result, "stage must appear in output"


# ---------------------------------------------------------------------------
# Gap 6: Ladder position causes assembled output to differ
#
# The existing integration test notes outputs "may differ" but does not
# assert it. The blueprint clearly states get_ladder_position_framing
# returns framing that adjusts based on position, so providing a ladder
# position should produce different assembled output than not providing one.
# ---------------------------------------------------------------------------


class TestLadderPositionAffectsAssembledOutput:
    """Verify that providing a ladder position changes the assembled output
    compared to not providing one."""

    # DATA ASSUMPTION: "Check the timeout" is a plausible hint.
    HINT = "Check the timeout"

    def test_assembled_output_differs_with_ladder_position(self):
        """Assembled output with ladder_position must differ from output without."""
        result_with = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id="test_gate",
            agent_type="test",
            ladder_position="rung_1",
        )
        result_without = assemble_hint_prompt(
            hint_content=self.HINT,
            gate_id="test_gate",
            agent_type="test",
            ladder_position=None,
        )
        assert result_with != result_without, (
            "Assembled output must differ when ladder_position is provided vs None"
        )


# ---------------------------------------------------------------------------
# Gap 7: Remaining agent type framings have appropriate content
#
# The existing suite verifies content characteristics for test,
# implementation, and diagnostic framings. The blueprint says each agent
# type gets "framing appropriate to the receiving agent type". The
# blueprint_author, stakeholder_dialog, and other types are not tested
# for content characteristics.
# ---------------------------------------------------------------------------


class TestRemainingAgentTypeFramingContent:
    """Verify that blueprint_author, stakeholder_dialog, and other agent
    types produce framing with content relevant to their role."""

    def test_blueprint_author_framing_has_relevant_content(self):
        """blueprint_author framing should reference blueprints, contracts,
        or specifications."""
        result = get_agent_type_framing("blueprint_author")
        result_lower = result.lower()
        assert (
            "blueprint" in result_lower
            or "contract" in result_lower
            or "specif" in result_lower
            or "interface" in result_lower
        ), "blueprint_author framing should reference blueprints, contracts, or specifications"

    def test_stakeholder_dialog_framing_has_relevant_content(self):
        """stakeholder_dialog framing should reference requirements,
        scope, or acceptance criteria."""
        result = get_agent_type_framing("stakeholder_dialog")
        result_lower = result.lower()
        assert (
            "require" in result_lower
            or "scope" in result_lower
            or "accept" in result_lower
            or "stakeholder" in result_lower
            or "dialog" in result_lower
            or "discussion" in result_lower
        ), "stakeholder_dialog framing should reference requirements, scope, or acceptance"

    def test_other_framing_is_generic(self):
        """'other' agent type framing should provide generic/general context."""
        result = get_agent_type_framing("other")
        result_lower = result.lower()
        assert (
            "context" in result_lower
            or "evaluate" in result_lower
            or "contract" in result_lower
        ), "'other' framing should provide generic guidance"

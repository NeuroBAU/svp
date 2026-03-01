"""
Additional coverage tests for Unit 16: Diagnostic and Classification Agent Definitions.

These tests cover gaps identified during coverage review of the blueprint's
behavioral contracts against the existing test suite.

## Synthetic Data Assumptions

- DATA ASSUMPTION: DIAGNOSTIC_AGENT_STATUS order matches the blueprint Tier 2
  signature exactly: ["DIAGNOSIS_COMPLETE: implementation",
  "DIAGNOSIS_COMPLETE: blueprint", "DIAGNOSIS_COMPLETE: spec"].
- DATA ASSUMPTION: REDO_AGENT_STATUS order matches the blueprint Tier 2
  signature exactly: ["REDO_CLASSIFIED: spec", "REDO_CLASSIFIED: blueprint",
  "REDO_CLASSIFIED: gate"].
- DATA ASSUMPTION: The Redo Agent MD_CONTENT instructions must reference
  "unit" in the context of input/received context, per the blueprint contract
  that the agent "Receives pipeline state summary, human error description,
  and current unit definition."
- DATA ASSUMPTION: The Redo Agent MD_CONTENT instructions must specifically
  mention stages 2, 3, and 4 in the context of availability, per the blueprint
  contract "Available during Stages 2, 3, and 4."
- DATA ASSUMPTION: The Diagnostic Agent MD_CONTENT instructions must reference
  "implementation" as something the agent receives/reads, per the blueprint
  contract that the agent "Receives stakeholder spec, unit blueprint section,
  failing tests, error output, and failing implementations."
"""

import pytest
import svp.scripts.diagnostic_agent_definitions as unit_16_module


def _get_md_content(name: str) -> str:
    """Retrieve an MD_CONTENT constant from the stub module."""
    value = getattr(unit_16_module, name, None)
    if value is None:
        pytest.fail(
            f"{name} is not defined in the module (expected a str constant "
            f"containing a complete Claude Code agent definition)"
        )
    return value


# ===========================================================================
# Gap 1: DIAGNOSTIC_AGENT_STATUS exact order
# ===========================================================================


class TestDiagnosticAgentStatusOrder:
    """The blueprint Tier 2 signature specifies DIAGNOSTIC_AGENT_STATUS as a
    List[str] with a specific ordering. The existing tests verify membership
    and length but not the exact order of elements."""

    def test_exact_order(self):
        """DIAGNOSTIC_AGENT_STATUS must match the blueprint order exactly.

        Blueprint Tier 2 signature:
            DIAGNOSTIC_AGENT_STATUS: List[str] = [
                "DIAGNOSIS_COMPLETE: implementation",
                "DIAGNOSIS_COMPLETE: blueprint",
                "DIAGNOSIS_COMPLETE: spec",
            ]
        """
        from svp.scripts.diagnostic_agent_definitions import DIAGNOSTIC_AGENT_STATUS
        expected = [
            "DIAGNOSIS_COMPLETE: implementation",
            "DIAGNOSIS_COMPLETE: blueprint",
            "DIAGNOSIS_COMPLETE: spec",
        ]
        assert DIAGNOSTIC_AGENT_STATUS == expected, (
            f"DIAGNOSTIC_AGENT_STATUS order must match blueprint. "
            f"Expected {expected}, got {DIAGNOSTIC_AGENT_STATUS}"
        )


# ===========================================================================
# Gap 2: REDO_AGENT_STATUS exact order
# ===========================================================================


class TestRedoAgentStatusOrder:
    """The blueprint Tier 2 signature specifies REDO_AGENT_STATUS as a
    List[str] with a specific ordering. The existing tests verify membership
    and length but not the exact order of elements."""

    def test_exact_order(self):
        """REDO_AGENT_STATUS must match the blueprint order exactly.

        Blueprint Tier 2 signature:
            REDO_AGENT_STATUS: List[str] = [
                "REDO_CLASSIFIED: spec",
                "REDO_CLASSIFIED: blueprint",
                "REDO_CLASSIFIED: gate",
            ]
        """
        from svp.scripts.diagnostic_agent_definitions import REDO_AGENT_STATUS
        expected = [
            "REDO_CLASSIFIED: spec",
            "REDO_CLASSIFIED: blueprint",
            "REDO_CLASSIFIED: gate",
        ]
        assert REDO_AGENT_STATUS == expected, (
            f"REDO_AGENT_STATUS order must match blueprint. "
            f"Expected {expected}, got {REDO_AGENT_STATUS}"
        )


# ===========================================================================
# Gap 3: Redo Agent input mentions unit definition
# ===========================================================================


class TestRedoAgentInputUnitDefinition:
    """The blueprint contract states the Redo Agent 'Receives pipeline state
    summary, human error description, and current unit definition.' The
    existing test checks for pipeline/state and error/human but does not
    verify that 'unit definition' is mentioned as an input."""

    def test_instructions_mention_unit_definition_input(self):
        """Body must mention unit definition as part of the agent's input context.

        Contract: Receives pipeline state summary, human error description,
        and current unit definition.
        """
        content = _get_md_content("REDO_AGENT_MD_CONTENT")
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        assert "unit" in body, (
            "Instructions must mention 'unit' (current unit definition) as input"
        )


# ===========================================================================
# Gap 4: Redo Agent stage availability specificity
# ===========================================================================


class TestRedoAgentStageAvailability:
    """The blueprint contract states the Redo Agent is 'Available during
    Stages 2, 3, and 4.' The existing test is loose -- it checks for 'stage'
    or any single digit or 'redo'. These tests verify each specific stage
    is referenced."""

    def test_instructions_mention_stage_2(self):
        """Body must reference Stage 2 availability.

        Contract: Available during Stages 2, 3, and 4.
        """
        content = _get_md_content("REDO_AGENT_MD_CONTENT")
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:]
        # Stage 2 should be referenced (as "Stage 2", "stage 2", or "2")
        assert "2" in body, (
            "Instructions must reference Stage 2 availability"
        )

    def test_instructions_mention_stage_3(self):
        """Body must reference Stage 3 availability.

        Contract: Available during Stages 2, 3, and 4.
        """
        content = _get_md_content("REDO_AGENT_MD_CONTENT")
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:]
        assert "3" in body, (
            "Instructions must reference Stage 3 availability"
        )

    def test_instructions_mention_stage_4(self):
        """Body must reference Stage 4 availability.

        Contract: Available during Stages 2, 3, and 4.
        """
        content = _get_md_content("REDO_AGENT_MD_CONTENT")
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:]
        assert "4" in body, (
            "Instructions must reference Stage 4 availability"
        )

    def test_instructions_mention_stage_keyword(self):
        """Body must use the word 'stage' in the context of availability.

        Contract: Available during Stages 2, 3, and 4.
        """
        content = _get_md_content("REDO_AGENT_MD_CONTENT")
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        assert "stage" in body, (
            "Instructions must use the word 'stage' when describing availability"
        )


# ===========================================================================
# Gap 5: Diagnostic Agent receives implementation code as input
# ===========================================================================


class TestDiagnosticAgentImplementationInput:
    """The blueprint contract states the Diagnostic Agent 'Receives stakeholder
    spec, unit blueprint section, failing tests, error output, and failing
    implementations.' The existing test_instructions_describe_input_context
    checks for spec, blueprint, and test/fail but does not verify that
    'implementation' is mentioned as an input the agent receives."""

    def test_instructions_mention_implementation_as_input(self):
        """Body must mention implementation as something the agent receives/reads.

        Contract: Receives stakeholder spec, unit blueprint section, failing tests,
        error output, and failing implementations.
        """
        content = _get_md_content("DIAGNOSTIC_AGENT_MD_CONTENT")
        second_delim = content.index("---\n", 4)
        body = content[second_delim + 4:].lower()
        assert "implementation" in body, (
            "Instructions must mention 'implementation' as input context "
            "(the agent receives failing implementations)"
        )

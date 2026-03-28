"""
Tests for Unit 21: Diagnostic and Redo Agent Definitions.

Synthetic Data Assumptions:
- Both agent definition constants (DIAGNOSTIC_AGENT_DEFINITION and
  REDO_AGENT_DEFINITION) are non-empty strings when implemented.
- Each definition contains specific keywords, status lines, and behavioral
  markers as specified in the blueprint contracts (Unit 21, Tier 3).
- String content checks use case-insensitive matching for general behavioral
  keywords, but exact-case matching for status line tokens (which are
  protocol-level identifiers).
- DIAGNOSTIC_AGENT_DEFINITION must enforce the three-hypothesis discipline
  (implementation, blueprint, spec), dual-format output (prose + structured),
  the "report most fundamental level" corollary, and the integration-test-failure
  directive to evaluate the blueprint hypothesis first.
- REDO_AGENT_DEFINITION must enforce five classification outcomes (spec,
  blueprint, gate, profile_delivery, profile_blueprint), the redo-triggered
  profile revision flow, and the corresponding REDO_CLASSIFIED status lines.
- No dependencies for this unit.
"""

import pytest

from unit_21 import (
    DIAGNOSTIC_AGENT_DEFINITION,
    REDO_AGENT_DEFINITION,
)

# ---------------------------------------------------------------------------
# Collect all definitions for cross-cutting tests
# ---------------------------------------------------------------------------

ALL_DEFINITIONS = {
    "DIAGNOSTIC_AGENT_DEFINITION": DIAGNOSTIC_AGENT_DEFINITION,
    "REDO_AGENT_DEFINITION": REDO_AGENT_DEFINITION,
}


# ===========================================================================
# Cross-cutting: All definitions are non-empty strings
# ===========================================================================


class TestAllDefinitionsAreNonEmptyStrings:
    """Every agent definition must be a non-empty string."""

    @pytest.mark.parametrize("name,value", list(ALL_DEFINITIONS.items()))
    def test_definition_is_a_string(self, name, value):
        assert isinstance(value, str), (
            f"{name} must be a str, got {type(value).__name__}"
        )

    @pytest.mark.parametrize("name,value", list(ALL_DEFINITIONS.items()))
    def test_definition_is_non_empty(self, name, value):
        assert len(value.strip()) > 0, f"{name} must not be empty or whitespace-only"


# ===========================================================================
# Type invariants
# ===========================================================================


class TestTypeInvariants:
    """All exported constants must be str type (not bytes, not None, etc.)."""

    @pytest.mark.parametrize("name,value", list(ALL_DEFINITIONS.items()))
    def test_definition_type_is_exactly_str(self, name, value):
        assert type(value) is str, (
            f"{name} must be exactly str, not a subclass or other type; "
            f"got {type(value).__name__}"
        )


# ===========================================================================
# Distinctness invariant
# ===========================================================================


class TestAllDefinitionsAreDistinct:
    """Each agent definition must be a unique string -- no two should be identical."""

    def test_no_duplicate_definitions(self):
        values = list(ALL_DEFINITIONS.values())
        names = list(ALL_DEFINITIONS.keys())
        seen = {}
        for name, value in zip(names, values):
            if value in seen:
                pytest.fail(
                    f"{name} has the same content as {seen[value]}; "
                    "all definitions must be distinct"
                )
            seen[value] = name


# ===========================================================================
# DIAGNOSTIC_AGENT_DEFINITION -- Three-hypothesis discipline
# ===========================================================================


class TestDiagnosticAgentThreeHypothesisDiscipline:
    """DIAGNOSTIC_AGENT_DEFINITION must enforce the three-hypothesis discipline:
    implementation, blueprint, and spec."""

    def test_references_implementation_hypothesis(self):
        text = DIAGNOSTIC_AGENT_DEFINITION.lower()
        assert "implementation" in text, (
            "DIAGNOSTIC_AGENT_DEFINITION must reference the implementation hypothesis"
        )

    def test_references_blueprint_hypothesis(self):
        text = DIAGNOSTIC_AGENT_DEFINITION.lower()
        assert "blueprint" in text, (
            "DIAGNOSTIC_AGENT_DEFINITION must reference the blueprint hypothesis"
        )

    def test_references_spec_hypothesis(self):
        text = DIAGNOSTIC_AGENT_DEFINITION.lower()
        assert "spec" in text, (
            "DIAGNOSTIC_AGENT_DEFINITION must reference the spec hypothesis"
        )

    def test_references_hypothesis_concept(self):
        text = DIAGNOSTIC_AGENT_DEFINITION.lower()
        assert "hypothesis" in text or "hypotheses" in text, (
            "DIAGNOSTIC_AGENT_DEFINITION must explicitly reference the hypothesis "
            "or hypotheses concept as part of the three-hypothesis discipline"
        )

    def test_all_three_hypotheses_present_together(self):
        """All three hypothesis levels must coexist in the definition."""
        text = DIAGNOSTIC_AGENT_DEFINITION.lower()
        has_implementation = "implementation" in text
        has_blueprint = "blueprint" in text
        has_spec = "spec" in text
        assert has_implementation and has_blueprint and has_spec, (
            "DIAGNOSTIC_AGENT_DEFINITION must contain all three hypothesis levels: "
            f"implementation={has_implementation}, blueprint={has_blueprint}, "
            f"spec={has_spec}"
        )


# ===========================================================================
# DIAGNOSTIC_AGENT_DEFINITION -- Dual-format output
# ===========================================================================


class TestDiagnosticAgentDualFormatOutput:
    """DIAGNOSTIC_AGENT_DEFINITION must require dual-format output:
    prose + structured block."""

    def test_references_prose_output(self):
        text = DIAGNOSTIC_AGENT_DEFINITION.lower()
        assert "prose" in text, (
            "DIAGNOSTIC_AGENT_DEFINITION must reference prose output format"
        )

    def test_references_structured_output(self):
        text = DIAGNOSTIC_AGENT_DEFINITION.lower()
        assert "structured" in text, (
            "DIAGNOSTIC_AGENT_DEFINITION must reference structured output format"
        )

    def test_references_dual_format_concept(self):
        text = DIAGNOSTIC_AGENT_DEFINITION.lower()
        has_prose = "prose" in text
        has_structured = "structured" in text
        assert has_prose and has_structured, (
            "DIAGNOSTIC_AGENT_DEFINITION must reference both prose and structured "
            f"formats: prose={has_prose}, structured={has_structured}"
        )


# ===========================================================================
# DIAGNOSTIC_AGENT_DEFINITION -- "Report most fundamental level" corollary
# ===========================================================================


class TestDiagnosticAgentFundamentalLevelCorollary:
    """DIAGNOSTIC_AGENT_DEFINITION must include the 'report most fundamental level'
    corollary."""

    def test_references_fundamental_level(self):
        text = DIAGNOSTIC_AGENT_DEFINITION.lower()
        assert "fundamental" in text, (
            "DIAGNOSTIC_AGENT_DEFINITION must reference the 'most fundamental level' "
            "corollary"
        )


# ===========================================================================
# DIAGNOSTIC_AGENT_DEFINITION -- Integration-test-failure directive
# ===========================================================================


class TestDiagnosticAgentIntegrationTestFailureDirective:
    """DIAGNOSTIC_AGENT_DEFINITION must instruct the agent to evaluate the
    blueprint hypothesis first with highest initial credence for
    integration-test failures."""

    def test_references_integration_test_failure(self):
        text = DIAGNOSTIC_AGENT_DEFINITION.lower()
        assert "integration" in text, (
            "DIAGNOSTIC_AGENT_DEFINITION must reference integration-test-failure "
            "directive"
        )

    def test_references_blueprint_first_credence(self):
        text = DIAGNOSTIC_AGENT_DEFINITION.lower()
        assert "credence" in text or "first" in text, (
            "DIAGNOSTIC_AGENT_DEFINITION must reference evaluating the blueprint "
            "hypothesis first or with highest initial credence"
        )


# ===========================================================================
# DIAGNOSTIC_AGENT_DEFINITION -- Status lines
# ===========================================================================


class TestDiagnosticAgentStatusLines:
    """DIAGNOSTIC_AGENT_DEFINITION must contain all three DIAGNOSIS_COMPLETE
    status variants."""

    def test_contains_diagnosis_complete_implementation_status(self):
        assert "DIAGNOSIS_COMPLETE: implementation" in DIAGNOSTIC_AGENT_DEFINITION, (
            "DIAGNOSTIC_AGENT_DEFINITION must contain "
            "'DIAGNOSIS_COMPLETE: implementation' status"
        )

    def test_contains_diagnosis_complete_blueprint_status(self):
        assert "DIAGNOSIS_COMPLETE: blueprint" in DIAGNOSTIC_AGENT_DEFINITION, (
            "DIAGNOSTIC_AGENT_DEFINITION must contain "
            "'DIAGNOSIS_COMPLETE: blueprint' status"
        )

    def test_contains_diagnosis_complete_spec_status(self):
        assert "DIAGNOSIS_COMPLETE: spec" in DIAGNOSTIC_AGENT_DEFINITION, (
            "DIAGNOSTIC_AGENT_DEFINITION must contain 'DIAGNOSIS_COMPLETE: spec' status"
        )

    def test_contains_all_three_diagnosis_complete_variants(self):
        """All three status variants must be present, not just some."""
        has_impl = "DIAGNOSIS_COMPLETE: implementation" in DIAGNOSTIC_AGENT_DEFINITION
        has_bp = "DIAGNOSIS_COMPLETE: blueprint" in DIAGNOSTIC_AGENT_DEFINITION
        has_spec = "DIAGNOSIS_COMPLETE: spec" in DIAGNOSTIC_AGENT_DEFINITION
        assert has_impl and has_bp and has_spec, (
            "DIAGNOSTIC_AGENT_DEFINITION must contain all three DIAGNOSIS_COMPLETE "
            f"variants: implementation={has_impl}, blueprint={has_bp}, spec={has_spec}"
        )

    def test_does_not_contain_other_diagnosis_complete_variants(self):
        """The definition should not introduce DIAGNOSIS_COMPLETE variants beyond
        the three specified (implementation, blueprint, spec)."""
        # Count occurrences of the base token
        text = DIAGNOSTIC_AGENT_DEFINITION
        count = text.count("DIAGNOSIS_COMPLETE:")
        assert count == 3, (
            f"DIAGNOSTIC_AGENT_DEFINITION should contain exactly 3 "
            f"DIAGNOSIS_COMPLETE: variants, found {count}"
        )


# ===========================================================================
# REDO_AGENT_DEFINITION -- Five classification outcomes
# ===========================================================================


class TestRedoAgentFiveClassificationOutcomes:
    """REDO_AGENT_DEFINITION must reference all five classification outcomes."""

    def test_references_spec_classification(self):
        text = REDO_AGENT_DEFINITION.lower()
        assert "spec" in text, (
            "REDO_AGENT_DEFINITION must reference the 'spec' classification outcome"
        )

    def test_references_blueprint_classification(self):
        text = REDO_AGENT_DEFINITION.lower()
        assert "blueprint" in text, (
            "REDO_AGENT_DEFINITION must reference the 'blueprint' classification outcome"
        )

    def test_references_gate_classification(self):
        text = REDO_AGENT_DEFINITION.lower()
        assert "gate" in text, (
            "REDO_AGENT_DEFINITION must reference the 'gate' classification outcome"
        )

    def test_references_profile_delivery_classification(self):
        text = REDO_AGENT_DEFINITION.lower()
        assert "profile_delivery" in text or "profile delivery" in text, (
            "REDO_AGENT_DEFINITION must reference the 'profile_delivery' "
            "classification outcome"
        )

    def test_references_profile_blueprint_classification(self):
        text = REDO_AGENT_DEFINITION.lower()
        assert "profile_blueprint" in text or "profile blueprint" in text, (
            "REDO_AGENT_DEFINITION must reference the 'profile_blueprint' "
            "classification outcome"
        )

    def test_references_classification_concept(self):
        text = REDO_AGENT_DEFINITION.lower()
        assert "classif" in text, (
            "REDO_AGENT_DEFINITION must reference the classification concept "
            "(e.g., 'classification', 'classifies', 'classified')"
        )


# ===========================================================================
# REDO_AGENT_DEFINITION -- Redo-triggered profile revision flow
# ===========================================================================


class TestRedoAgentProfileRevisionFlow:
    """REDO_AGENT_DEFINITION must describe the redo-triggered profile revision
    flow including classification, state snapshotting, and redo sub-stage entry."""

    def test_references_redo_concept(self):
        text = REDO_AGENT_DEFINITION.lower()
        assert "redo" in text, "REDO_AGENT_DEFINITION must reference the redo concept"

    def test_references_snapshot_or_state(self):
        text = REDO_AGENT_DEFINITION.lower()
        assert "snapshot" in text or "state" in text, (
            "REDO_AGENT_DEFINITION must reference state snapshotting as part of "
            "the redo-triggered profile revision flow"
        )

    def test_references_sub_stage(self):
        text = REDO_AGENT_DEFINITION.lower()
        assert "sub-stage" in text or "substage" in text or "sub stage" in text, (
            "REDO_AGENT_DEFINITION must reference entering a redo sub-stage"
        )


# ===========================================================================
# REDO_AGENT_DEFINITION -- Status lines
# ===========================================================================


class TestRedoAgentStatusLines:
    """REDO_AGENT_DEFINITION must contain all five REDO_CLASSIFIED status variants."""

    def test_contains_redo_classified_spec_status(self):
        assert "REDO_CLASSIFIED: spec" in REDO_AGENT_DEFINITION, (
            "REDO_AGENT_DEFINITION must contain 'REDO_CLASSIFIED: spec' status"
        )

    def test_contains_redo_classified_blueprint_status(self):
        assert "REDO_CLASSIFIED: blueprint" in REDO_AGENT_DEFINITION, (
            "REDO_AGENT_DEFINITION must contain 'REDO_CLASSIFIED: blueprint' status"
        )

    def test_contains_redo_classified_gate_status(self):
        assert "REDO_CLASSIFIED: gate" in REDO_AGENT_DEFINITION, (
            "REDO_AGENT_DEFINITION must contain 'REDO_CLASSIFIED: gate' status"
        )

    def test_contains_redo_classified_profile_delivery_status(self):
        assert "REDO_CLASSIFIED: profile_delivery" in REDO_AGENT_DEFINITION, (
            "REDO_AGENT_DEFINITION must contain "
            "'REDO_CLASSIFIED: profile_delivery' status"
        )

    def test_contains_redo_classified_profile_blueprint_status(self):
        assert "REDO_CLASSIFIED: profile_blueprint" in REDO_AGENT_DEFINITION, (
            "REDO_AGENT_DEFINITION must contain "
            "'REDO_CLASSIFIED: profile_blueprint' status"
        )

    def test_contains_all_five_redo_classified_variants(self):
        """All five status variants must be present, not just some."""
        has_spec = "REDO_CLASSIFIED: spec" in REDO_AGENT_DEFINITION
        has_bp = "REDO_CLASSIFIED: blueprint" in REDO_AGENT_DEFINITION
        has_gate = "REDO_CLASSIFIED: gate" in REDO_AGENT_DEFINITION
        has_pd = "REDO_CLASSIFIED: profile_delivery" in REDO_AGENT_DEFINITION
        has_pb = "REDO_CLASSIFIED: profile_blueprint" in REDO_AGENT_DEFINITION
        assert has_spec and has_bp and has_gate and has_pd and has_pb, (
            "REDO_AGENT_DEFINITION must contain all five REDO_CLASSIFIED variants: "
            f"spec={has_spec}, blueprint={has_bp}, gate={has_gate}, "
            f"profile_delivery={has_pd}, profile_blueprint={has_pb}"
        )

    def test_does_not_contain_other_redo_classified_variants(self):
        """The definition should not introduce REDO_CLASSIFIED variants beyond
        the five specified."""
        text = REDO_AGENT_DEFINITION
        count = text.count("REDO_CLASSIFIED:")
        assert count == 5, (
            f"REDO_AGENT_DEFINITION should contain exactly 5 "
            f"REDO_CLASSIFIED: variants, found {count}"
        )


# ===========================================================================
# Status line exclusivity
# ===========================================================================


class TestStatusLineExclusivity:
    """Definitions should only contain their own status lines, not the other's."""

    def test_diagnostic_does_not_contain_redo_classified_status(self):
        assert "REDO_CLASSIFIED" not in DIAGNOSTIC_AGENT_DEFINITION, (
            "DIAGNOSTIC_AGENT_DEFINITION must not contain REDO_CLASSIFIED statuses; "
            "those belong to REDO_AGENT_DEFINITION"
        )

    def test_redo_does_not_contain_diagnosis_complete_status(self):
        assert "DIAGNOSIS_COMPLETE" not in REDO_AGENT_DEFINITION, (
            "REDO_AGENT_DEFINITION must not contain DIAGNOSIS_COMPLETE statuses; "
            "those belong to DIAGNOSTIC_AGENT_DEFINITION"
        )

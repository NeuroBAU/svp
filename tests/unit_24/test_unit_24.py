"""
Tests for Unit 24: Debug Loop Agent Definitions.

Synthetic Data Assumptions:
- BUG_TRIAGE_AGENT_DEFINITION and REPAIR_AGENT_DEFINITION are non-empty strings
  when implemented. They contain agent definition markdown content.
- Each definition contains specific keywords, status lines, and behavioral markers
  as specified in the blueprint contracts (Unit 24, Tier 3).
- String content checks use case-insensitive matching for keywords and concepts,
  but exact-case matching for status line tokens (which are protocol-level
  identifiers, e.g., TRIAGE_COMPLETE, REPAIR_COMPLETE).
- The triage agent definition references: Socratic triage dialog, three-hypothesis
  discipline (implementation, blueprint, spec), classification outputs
  (single_unit, cross_unit, build_env), assembly_map.json awareness, bug number
  assignment via debug_history, triage_result.json, language awareness,
  reclassification bound (3), seven-step workflow, and structural check
  pre-computation (Step 0).
- The repair agent definition references: narrow mandate for build/env fixes,
  REPAIR_RECLASSIFY escalation, interface-boundary constraint, and language
  awareness.
- Neither definition is empty, both are distinct from each other, and both are
  exactly str type.
"""

import pytest

from unit_24 import (
    BUG_TRIAGE_AGENT_DEFINITION,
    REPAIR_AGENT_DEFINITION,
)

# ---------------------------------------------------------------------------
# Collect all definitions for cross-cutting tests
# ---------------------------------------------------------------------------

ALL_DEFINITIONS = {
    "BUG_TRIAGE_AGENT_DEFINITION": BUG_TRIAGE_AGENT_DEFINITION,
    "REPAIR_AGENT_DEFINITION": REPAIR_AGENT_DEFINITION,
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
# Cross-cutting: Type invariants
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
# Cross-cutting: Distinctness invariant
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
# Cross-cutting: Language awareness
# ===========================================================================


class TestAllDefinitionsAreLanguageAware:
    """Both debug loop agent definitions must be language-aware."""

    def test_triage_agent_references_language(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "language" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference language awareness "
            "(receives unit's language and language-specific context)"
        )

    def test_repair_agent_references_language(self):
        text = REPAIR_AGENT_DEFINITION.lower()
        assert "language" in text, (
            "REPAIR_AGENT_DEFINITION must reference language awareness "
            "(generates fixes in the unit's language)"
        )


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION -- Status lines
# ===========================================================================


class TestBugTriageAgentDefinitionStatusLines:
    """The triage agent definition must contain all five status lines."""

    def test_contains_triage_complete_single_unit_status(self):
        assert "TRIAGE_COMPLETE: single_unit" in BUG_TRIAGE_AGENT_DEFINITION, (
            "BUG_TRIAGE_AGENT_DEFINITION must contain "
            "'TRIAGE_COMPLETE: single_unit' status"
        )

    def test_contains_triage_complete_cross_unit_status(self):
        assert "TRIAGE_COMPLETE: cross_unit" in BUG_TRIAGE_AGENT_DEFINITION, (
            "BUG_TRIAGE_AGENT_DEFINITION must contain "
            "'TRIAGE_COMPLETE: cross_unit' status"
        )

    def test_contains_triage_complete_build_env_status(self):
        assert "TRIAGE_COMPLETE: build_env" in BUG_TRIAGE_AGENT_DEFINITION, (
            "BUG_TRIAGE_AGENT_DEFINITION must contain "
            "'TRIAGE_COMPLETE: build_env' status"
        )

    def test_contains_triage_needs_refinement_status(self):
        assert "TRIAGE_NEEDS_REFINEMENT" in BUG_TRIAGE_AGENT_DEFINITION, (
            "BUG_TRIAGE_AGENT_DEFINITION must contain 'TRIAGE_NEEDS_REFINEMENT' status"
        )

    def test_contains_triage_non_reproducible_status(self):
        assert "TRIAGE_NON_REPRODUCIBLE" in BUG_TRIAGE_AGENT_DEFINITION, (
            "BUG_TRIAGE_AGENT_DEFINITION must contain 'TRIAGE_NON_REPRODUCIBLE' status"
        )


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION -- Socratic triage dialog
# ===========================================================================


class TestBugTriageAgentDefinitionSocraticDialog:
    """The triage agent must describe a Socratic triage dialog with human."""

    def test_references_socratic_dialog(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "socratic" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference Socratic triage dialog"
        )

    def test_references_triage(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "triage" in text, "BUG_TRIAGE_AGENT_DEFINITION must reference triage"

    def test_references_dialog_or_dialogue(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "dialog" in text or "dialogue" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference dialog with human"
        )


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION -- Three-hypothesis discipline
# ===========================================================================


class TestBugTriageAgentDefinitionThreeHypothesis:
    """The triage agent must enforce a three-hypothesis discipline."""

    def test_references_hypothesis_concept(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "hypothesis" in text or "hypotheses" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference the hypothesis discipline"
        )

    def test_references_implementation_hypothesis(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "implementation" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference the implementation hypothesis"
        )

    def test_references_blueprint_hypothesis(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "blueprint" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference the blueprint hypothesis"
        )

    def test_references_spec_hypothesis(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "spec" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference the spec hypothesis"
        )


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION -- Classification outputs
# ===========================================================================


class TestBugTriageAgentDefinitionClassificationOutputs:
    """The triage agent must classify bugs into the specified categories."""

    def test_references_single_unit_classification(self):
        assert "single_unit" in BUG_TRIAGE_AGENT_DEFINITION, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference single_unit classification"
        )

    def test_references_cross_unit_classification(self):
        assert "cross_unit" in BUG_TRIAGE_AGENT_DEFINITION, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference cross_unit classification"
        )

    def test_references_build_env_classification(self):
        assert "build_env" in BUG_TRIAGE_AGENT_DEFINITION, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference build_env classification"
        )

    def test_references_non_reproducible_classification(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "non-reproducible" in text or "non_reproducible" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference non-reproducible classification"
        )


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION -- Assembly map awareness
# ===========================================================================


class TestBugTriageAgentDefinitionAssemblyMapAwareness:
    """The triage agent must be aware of assembly_map.json for path correlation."""

    def test_references_assembly_map(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "assembly_map" in text or "assembly map" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference assembly_map.json awareness"
        )

    def test_references_path_correlation(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "path" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference path correlation "
            "(delivered-to-workspace)"
        )


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION -- Bug number assignment
# ===========================================================================


class TestBugTriageAgentDefinitionBugNumberAssignment:
    """The triage agent must assign bug numbers based on debug_history length + 1."""

    def test_references_bug_number(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "bug number" in text or "bug_number" in text or "number" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference bug number assignment"
        )

    def test_references_debug_history(self):
        assert "debug_history" in BUG_TRIAGE_AGENT_DEFINITION, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference debug_history "
            "for bug number assignment (reads length + 1)"
        )


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION -- Writes triage_result.json
# ===========================================================================


class TestBugTriageAgentDefinitionTriageResultOutput:
    """The triage agent must write triage_result.json with classification and units."""

    def test_references_triage_result_json(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "triage_result" in text or "triage result" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference triage_result.json output"
        )

    def test_references_classification_in_output(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "classification" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference classification in output"
        )

    def test_references_affected_units_in_output(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "affected" in text or "unit" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference affected units in output"
        )


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION -- Reclassification bound
# ===========================================================================


class TestBugTriageAgentDefinitionReclassificationBound:
    """The triage agent must enforce a reclassification bound of 3."""

    def test_references_reclassification_concept(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "reclassif" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference reclassification"
        )

    def test_references_reclassification_limit_of_three(self):
        assert "3" in BUG_TRIAGE_AGENT_DEFINITION, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference the reclassification limit of 3"
        )

    def test_references_reclassify_bug(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.upper()
        assert "RECLASSIFY" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference RECLASSIFY BUG action"
        )

    def test_references_abandon_debug_after_limit(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "abandon" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference ABANDON DEBUG "
            "as option after reclassification limit exhausted"
        )

    def test_references_retry_repair_after_limit(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "retry" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference RETRY REPAIR "
            "as option after reclassification limit exhausted"
        )


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION -- TRIAGE_NEEDS_REFINEMENT behavior
# ===========================================================================


class TestBugTriageAgentDefinitionRefinementBehavior:
    """TRIAGE_NEEDS_REFINEMENT is emitted when initial analysis is insufficient."""

    def test_references_refinement_concept(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "refinement" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference the refinement concept "
            "(emitted when initial analysis is insufficient)"
        )

    def test_references_insufficient_analysis_trigger(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "insufficient" in text or "inadequate" in text or "unable" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must describe when refinement is needed "
            "(when initial analysis is insufficient)"
        )


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION -- Seven-step workflow
# ===========================================================================


class TestBugTriageAgentDefinitionSevenStepWorkflow:
    """The triage agent must reference the seven-step workflow."""

    def test_references_seven_step_workflow(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "seven" in text or "7" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference the seven-step workflow"
        )

    def test_references_workflow_or_steps(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "step" in text or "workflow" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference workflow steps"
        )


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION -- Structural check pre-computation (Step 0)
# ===========================================================================


class TestBugTriageAgentDefinitionStructuralCheckPreComputation:
    """The triage agent reviews structural check results in Step 0."""

    def test_references_structural_check(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "structural" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must reference structural check "
            "pre-computation results"
        )

    def test_references_registry_diagnosis_recipe(self):
        text = BUG_TRIAGE_AGENT_DEFINITION.lower()
        assert "registry" in text, (
            "BUG_TRIAGE_AGENT_DEFINITION must include a Registry Diagnosis Recipe "
            "for manual investigation"
        )


# ===========================================================================
# REPAIR_AGENT_DEFINITION -- Status lines
# ===========================================================================


class TestRepairAgentDefinitionStatusLines:
    """The repair agent definition must contain all three status lines."""

    def test_contains_repair_complete_status(self):
        assert "REPAIR_COMPLETE" in REPAIR_AGENT_DEFINITION, (
            "REPAIR_AGENT_DEFINITION must contain 'REPAIR_COMPLETE' status"
        )

    def test_contains_repair_reclassify_status(self):
        assert "REPAIR_RECLASSIFY" in REPAIR_AGENT_DEFINITION, (
            "REPAIR_AGENT_DEFINITION must contain 'REPAIR_RECLASSIFY' status"
        )

    def test_contains_repair_failed_status(self):
        assert "REPAIR_FAILED" in REPAIR_AGENT_DEFINITION, (
            "REPAIR_AGENT_DEFINITION must contain 'REPAIR_FAILED' status"
        )


# ===========================================================================
# REPAIR_AGENT_DEFINITION -- Narrow mandate for build/env fixes
# ===========================================================================


class TestRepairAgentDefinitionBuildEnvMandate:
    """The repair agent has a narrow mandate for build/environment fixes."""

    def test_references_build_or_environment_scope(self):
        text = REPAIR_AGENT_DEFINITION.lower()
        assert "build" in text or "environment" in text or "env" in text, (
            "REPAIR_AGENT_DEFINITION must reference build/environment scope"
        )

    def test_references_narrow_mandate(self):
        text = REPAIR_AGENT_DEFINITION.lower()
        assert "mandate" in text or "narrow" in text or "scope" in text, (
            "REPAIR_AGENT_DEFINITION must reference the narrow mandate for "
            "build/env fixes"
        )

    def test_references_build_env_classification(self):
        text = REPAIR_AGENT_DEFINITION.lower()
        assert "build_env" in text or "build env" in text, (
            "REPAIR_AGENT_DEFINITION must reference the build_env classification "
            "trigger condition"
        )


# ===========================================================================
# REPAIR_AGENT_DEFINITION -- REPAIR_RECLASSIFY escalation
# ===========================================================================


class TestRepairAgentDefinitionReclassifyEscalation:
    """REPAIR_RECLASSIFY is emitted when fix exceeds the repair agent's mandate."""

    def test_references_reclassify_escalation(self):
        assert "REPAIR_RECLASSIFY" in REPAIR_AGENT_DEFINITION, (
            "REPAIR_AGENT_DEFINITION must reference REPAIR_RECLASSIFY escalation"
        )

    def test_references_exceeds_mandate_condition(self):
        text = REPAIR_AGENT_DEFINITION.lower()
        assert "exceed" in text or "beyond" in text or "outside" in text, (
            "REPAIR_AGENT_DEFINITION must describe when REPAIR_RECLASSIFY is emitted "
            "(when fix exceeds mandate)"
        )


# ===========================================================================
# REPAIR_AGENT_DEFINITION -- Interface-boundary constraint
# ===========================================================================


class TestRepairAgentDefinitionInterfaceBoundaryConstraint:
    """For assembly fixes, the repair agent may modify only interfaces."""

    def test_references_interface_boundary(self):
        text = REPAIR_AGENT_DEFINITION.lower()
        assert "interface" in text, (
            "REPAIR_AGENT_DEFINITION must reference the interface-boundary constraint"
        )

    def test_references_assembly_fixes(self):
        text = REPAIR_AGENT_DEFINITION.lower()
        assert "assembly" in text, (
            "REPAIR_AGENT_DEFINITION must reference assembly fixes context "
            "for the interface-boundary constraint"
        )


# ===========================================================================
# Status line exclusivity: each definition only contains its own statuses
# ===========================================================================


class TestStatusLineExclusivity:
    """Definitions should only contain their own status lines, not others'."""

    def test_triage_agent_does_not_contain_repair_complete_status(self):
        assert "REPAIR_COMPLETE" not in BUG_TRIAGE_AGENT_DEFINITION, (
            "BUG_TRIAGE_AGENT_DEFINITION must not contain REPAIR_COMPLETE "
            "(belongs to repair agent)"
        )

    def test_triage_agent_does_not_contain_repair_failed_status(self):
        assert "REPAIR_FAILED" not in BUG_TRIAGE_AGENT_DEFINITION, (
            "BUG_TRIAGE_AGENT_DEFINITION must not contain REPAIR_FAILED "
            "(belongs to repair agent)"
        )

    def test_repair_agent_does_not_contain_triage_complete_status(self):
        assert "TRIAGE_COMPLETE" not in REPAIR_AGENT_DEFINITION, (
            "REPAIR_AGENT_DEFINITION must not contain TRIAGE_COMPLETE "
            "(belongs to triage agent)"
        )

    def test_repair_agent_does_not_contain_triage_needs_refinement_status(self):
        assert "TRIAGE_NEEDS_REFINEMENT" not in REPAIR_AGENT_DEFINITION, (
            "REPAIR_AGENT_DEFINITION must not contain TRIAGE_NEEDS_REFINEMENT "
            "(belongs to triage agent)"
        )

    def test_repair_agent_does_not_contain_triage_non_reproducible_status(self):
        assert "TRIAGE_NON_REPRODUCIBLE" not in REPAIR_AGENT_DEFINITION, (
            "REPAIR_AGENT_DEFINITION must not contain TRIAGE_NON_REPRODUCIBLE "
            "(belongs to triage agent)"
        )

    def test_triage_agent_does_not_contain_implementation_complete_status(self):
        assert "IMPLEMENTATION_COMPLETE" not in BUG_TRIAGE_AGENT_DEFINITION, (
            "BUG_TRIAGE_AGENT_DEFINITION must not contain IMPLEMENTATION_COMPLETE "
            "(belongs to implementation agent)"
        )

    def test_repair_agent_does_not_contain_implementation_complete_status(self):
        assert "IMPLEMENTATION_COMPLETE" not in REPAIR_AGENT_DEFINITION, (
            "REPAIR_AGENT_DEFINITION must not contain IMPLEMENTATION_COMPLETE "
            "(belongs to implementation agent)"
        )

    def test_triage_agent_does_not_contain_test_generation_complete_status(self):
        assert "TEST_GENERATION_COMPLETE" not in BUG_TRIAGE_AGENT_DEFINITION, (
            "BUG_TRIAGE_AGENT_DEFINITION must not contain TEST_GENERATION_COMPLETE "
            "(belongs to test agent)"
        )

    def test_repair_agent_does_not_contain_test_generation_complete_status(self):
        assert "TEST_GENERATION_COMPLETE" not in REPAIR_AGENT_DEFINITION, (
            "REPAIR_AGENT_DEFINITION must not contain TEST_GENERATION_COMPLETE "
            "(belongs to test agent)"
        )

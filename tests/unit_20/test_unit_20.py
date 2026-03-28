"""
Tests for Unit 20: Construction Agent Definitions.

Synthetic Data Assumptions:
- All 8 agent definition constants are non-empty strings when implemented.
- Each definition contains specific keywords, status lines, and behavioral
  markers as specified in the blueprint contracts (Section Unit 20, Tier 3).
- All definitions reference the LANGUAGE_CONTEXT placeholder, since agent
  definitions must provide language-conditional guidance.
- String content checks use case-insensitive matching where appropriate
  for keywords, but exact-case matching for status line tokens (which are
  protocol-level identifiers).
- The dependency on Unit 2 (Language Registry) implies that definitions
  must be aware of language-conditional behavior, verified through the
  LANGUAGE_CONTEXT placeholder requirement.
"""

import pytest

from unit_20 import (
    BLUEPRINT_AUTHOR_DEFINITION,
    BLUEPRINT_REVIEWER_DEFINITION,
    COVERAGE_REVIEW_AGENT_DEFINITION,
    IMPLEMENTATION_AGENT_DEFINITION,
    INTEGRATION_TEST_AUTHOR_DEFINITION,
    STAKEHOLDER_DIALOG_DEFINITION,
    STAKEHOLDER_REVIEWER_DEFINITION,
    TEST_AGENT_DEFINITION,
)

# ---------------------------------------------------------------------------
# Collect all definitions for cross-cutting tests
# ---------------------------------------------------------------------------

ALL_DEFINITIONS = {
    "STAKEHOLDER_DIALOG_DEFINITION": STAKEHOLDER_DIALOG_DEFINITION,
    "STAKEHOLDER_REVIEWER_DEFINITION": STAKEHOLDER_REVIEWER_DEFINITION,
    "BLUEPRINT_AUTHOR_DEFINITION": BLUEPRINT_AUTHOR_DEFINITION,
    "BLUEPRINT_REVIEWER_DEFINITION": BLUEPRINT_REVIEWER_DEFINITION,
    "TEST_AGENT_DEFINITION": TEST_AGENT_DEFINITION,
    "IMPLEMENTATION_AGENT_DEFINITION": IMPLEMENTATION_AGENT_DEFINITION,
    "COVERAGE_REVIEW_AGENT_DEFINITION": COVERAGE_REVIEW_AGENT_DEFINITION,
    "INTEGRATION_TEST_AUTHOR_DEFINITION": INTEGRATION_TEST_AUTHOR_DEFINITION,
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
# Cross-cutting: All definitions reference LANGUAGE_CONTEXT
# ===========================================================================


class TestAllDefinitionsReferenceLANGUAGE_CONTEXT:
    """All definitions must reference the LANGUAGE_CONTEXT placeholder."""

    @pytest.mark.parametrize("name,value", list(ALL_DEFINITIONS.items()))
    def test_definition_contains_language_context(self, name, value):
        assert "LANGUAGE_CONTEXT" in value, (
            f"{name} must reference the LANGUAGE_CONTEXT placeholder"
        )


# ===========================================================================
# STAKEHOLDER_DIALOG_DEFINITION
# ===========================================================================


class TestStakeholderDialogDefinition:
    """Tests for STAKEHOLDER_DIALOG_DEFINITION behavioral contracts."""

    def test_references_socratic_dialog(self):
        text = STAKEHOLDER_DIALOG_DEFINITION.lower()
        assert "socratic" in text, (
            "STAKEHOLDER_DIALOG_DEFINITION must reference Socratic dialog"
        )

    def test_references_draft_review_approve_cycle(self):
        text = STAKEHOLDER_DIALOG_DEFINITION.lower()
        assert "draft" in text, (
            "STAKEHOLDER_DIALOG_DEFINITION must reference the draft phase of the cycle"
        )
        assert "review" in text or "approve" in text, (
            "STAKEHOLDER_DIALOG_DEFINITION must reference review/approve phases"
        )

    def test_contains_spec_draft_complete_status(self):
        assert "SPEC_DRAFT_COMPLETE" in STAKEHOLDER_DIALOG_DEFINITION, (
            "STAKEHOLDER_DIALOG_DEFINITION must contain SPEC_DRAFT_COMPLETE status"
        )

    def test_contains_spec_revision_complete_status(self):
        assert "SPEC_REVISION_COMPLETE" in STAKEHOLDER_DIALOG_DEFINITION, (
            "STAKEHOLDER_DIALOG_DEFINITION must contain SPEC_REVISION_COMPLETE status"
        )


# ===========================================================================
# STAKEHOLDER_REVIEWER_DEFINITION
# ===========================================================================


class TestStakeholderReviewerDefinition:
    """Tests for STAKEHOLDER_REVIEWER_DEFINITION behavioral contracts."""

    def test_contains_review_complete_status(self):
        assert "REVIEW_COMPLETE" in STAKEHOLDER_REVIEWER_DEFINITION, (
            "STAKEHOLDER_REVIEWER_DEFINITION must contain REVIEW_COMPLETE status"
        )

    def test_references_baked_checklist(self):
        text = STAKEHOLDER_REVIEWER_DEFINITION.lower()
        assert "checklist" in text, (
            "STAKEHOLDER_REVIEWER_DEFINITION must reference a baked checklist"
        )

    def test_references_downstream_dependency_analysis(self):
        text = STAKEHOLDER_REVIEWER_DEFINITION.lower()
        assert "downstream" in text or "dependency" in text, (
            "STAKEHOLDER_REVIEWER_DEFINITION must reference downstream dependency analysis"
        )

    def test_references_contract_granularity(self):
        text = STAKEHOLDER_REVIEWER_DEFINITION.lower()
        assert "granularity" in text or "contract" in text, (
            "STAKEHOLDER_REVIEWER_DEFINITION must reference contract granularity"
        )

    def test_references_gate_reachability(self):
        text = STAKEHOLDER_REVIEWER_DEFINITION.lower()
        assert "gate" in text or "reachability" in text, (
            "STAKEHOLDER_REVIEWER_DEFINITION must reference gate reachability"
        )

    def test_is_a_cold_reviewer(self):
        text = STAKEHOLDER_REVIEWER_DEFINITION.lower()
        assert "cold" in text or "reviewer" in text, (
            "STAKEHOLDER_REVIEWER_DEFINITION must indicate a cold reviewer role"
        )


# ===========================================================================
# BLUEPRINT_AUTHOR_DEFINITION
# ===========================================================================


class TestBlueprintAuthorDefinition:
    """Tests for BLUEPRINT_AUTHOR_DEFINITION behavioral contracts."""

    def test_references_decomposition_dialog(self):
        text = BLUEPRINT_AUTHOR_DEFINITION.lower()
        assert "decomposition" in text or "dialog" in text, (
            "BLUEPRINT_AUTHOR_DEFINITION must reference decomposition dialog"
        )

    def test_contains_blueprint_draft_complete_status(self):
        assert "BLUEPRINT_DRAFT_COMPLETE" in BLUEPRINT_AUTHOR_DEFINITION, (
            "BLUEPRINT_AUTHOR_DEFINITION must contain BLUEPRINT_DRAFT_COMPLETE status"
        )

    def test_contains_blueprint_revision_complete_status(self):
        assert "BLUEPRINT_REVISION_COMPLETE" in BLUEPRINT_AUTHOR_DEFINITION, (
            "BLUEPRINT_AUTHOR_DEFINITION must contain BLUEPRINT_REVISION_COMPLETE status"
        )

    def test_references_rule_p1(self):
        assert "P1" in BLUEPRINT_AUTHOR_DEFINITION, (
            "BLUEPRINT_AUTHOR_DEFINITION must contain Rule P1"
        )

    def test_references_rule_p2(self):
        assert "P2" in BLUEPRINT_AUTHOR_DEFINITION, (
            "BLUEPRINT_AUTHOR_DEFINITION must contain Rule P2"
        )

    def test_references_rule_p3(self):
        assert "P3" in BLUEPRINT_AUTHOR_DEFINITION, (
            "BLUEPRINT_AUTHOR_DEFINITION must contain Rule P3"
        )

    def test_references_rule_p4(self):
        assert "P4" in BLUEPRINT_AUTHOR_DEFINITION, (
            "BLUEPRINT_AUTHOR_DEFINITION must contain Rule P4"
        )

    def test_references_preference_capture(self):
        text = BLUEPRINT_AUTHOR_DEFINITION.lower()
        assert "preference" in text, (
            "BLUEPRINT_AUTHOR_DEFINITION must reference preference capture"
        )


# ===========================================================================
# BLUEPRINT_REVIEWER_DEFINITION
# ===========================================================================


class TestBlueprintReviewerDefinition:
    """Tests for BLUEPRINT_REVIEWER_DEFINITION behavioral contracts."""

    def test_contains_review_complete_status(self):
        assert "REVIEW_COMPLETE" in BLUEPRINT_REVIEWER_DEFINITION, (
            "BLUEPRINT_REVIEWER_DEFINITION must contain REVIEW_COMPLETE status"
        )

    def test_references_baked_checklist(self):
        text = BLUEPRINT_REVIEWER_DEFINITION.lower()
        assert "checklist" in text, (
            "BLUEPRINT_REVIEWER_DEFINITION must reference a baked review checklist"
        )

    def test_references_pattern_catalog(self):
        text = BLUEPRINT_REVIEWER_DEFINITION.lower()
        assert "pattern" in text or "catalog" in text, (
            "BLUEPRINT_REVIEWER_DEFINITION must reference pattern catalog cross-reference"
        )

    def test_is_a_cold_reviewer(self):
        text = BLUEPRINT_REVIEWER_DEFINITION.lower()
        assert "cold" in text or "reviewer" in text, (
            "BLUEPRINT_REVIEWER_DEFINITION must indicate a cold reviewer role"
        )


# ===========================================================================
# TEST_AGENT_DEFINITION
# ===========================================================================


class TestTestAgentDefinition:
    """Tests for TEST_AGENT_DEFINITION behavioral contracts."""

    def test_contains_test_generation_complete_status(self):
        assert "TEST_GENERATION_COMPLETE" in TEST_AGENT_DEFINITION, (
            "TEST_AGENT_DEFINITION must contain TEST_GENERATION_COMPLETE status"
        )

    def test_contains_regression_test_complete_status(self):
        assert "REGRESSION_TEST_COMPLETE" in TEST_AGENT_DEFINITION, (
            "TEST_AGENT_DEFINITION must contain REGRESSION_TEST_COMPLETE status"
        )

    def test_references_quality_tool_auto_format(self):
        text = TEST_AGENT_DEFINITION.lower()
        assert "quality" in text or "format" in text, (
            "TEST_AGENT_DEFINITION must reference quality tool auto-format notification"
        )

    def test_references_readable_test_names_preference(self):
        assert "readable_test_names" in TEST_AGENT_DEFINITION, (
            "TEST_AGENT_DEFINITION must reference the testing.readable_test_names "
            "profile preference"
        )

    def test_references_lessons_learned_filtering(self):
        text = TEST_AGENT_DEFINITION.lower()
        assert "lesson" in text or "filter" in text, (
            "TEST_AGENT_DEFINITION must reference lessons learned filtering"
        )

    def test_references_synthetic_data_assumptions(self):
        text = TEST_AGENT_DEFINITION.lower()
        assert "synthetic" in text or "assumption" in text, (
            "TEST_AGENT_DEFINITION must reference synthetic data assumption declarations"
        )

    def test_does_not_allow_pytest_raises_not_implemented_error(self):
        # The definition must instruct agents NOT to use pytest.raises(NotImplementedError)
        text = TEST_AGENT_DEFINITION
        assert "NotImplementedError" in text, (
            "TEST_AGENT_DEFINITION must mention the NotImplementedError pattern "
            "(to prohibit it)"
        )

    def test_references_language_context(self):
        assert "LANGUAGE_CONTEXT" in TEST_AGENT_DEFINITION, (
            "TEST_AGENT_DEFINITION must reference LANGUAGE_CONTEXT"
        )


# ===========================================================================
# IMPLEMENTATION_AGENT_DEFINITION
# ===========================================================================


class TestImplementationAgentDefinition:
    """Tests for IMPLEMENTATION_AGENT_DEFINITION behavioral contracts."""

    def test_contains_implementation_complete_status(self):
        assert "IMPLEMENTATION_COMPLETE" in IMPLEMENTATION_AGENT_DEFINITION, (
            "IMPLEMENTATION_AGENT_DEFINITION must contain IMPLEMENTATION_COMPLETE status"
        )

    def test_references_quality_tool_notification(self):
        text = IMPLEMENTATION_AGENT_DEFINITION.lower()
        assert "quality" in text or "format" in text, (
            "IMPLEMENTATION_AGENT_DEFINITION must reference quality tool notification"
        )

    def test_references_interface_boundary_constraint(self):
        text = IMPLEMENTATION_AGENT_DEFINITION.lower()
        assert "interface" in text or "boundary" in text, (
            "IMPLEMENTATION_AGENT_DEFINITION must reference the interface-boundary "
            "constraint (assembly fixes modify only interfaces, not internal logic)"
        )

    def test_references_assembly_fix_scope(self):
        text = IMPLEMENTATION_AGENT_DEFINITION.lower()
        # The constraint specifies assembly fixes modify only interfaces, not internal logic
        assert "interface" in text, (
            "IMPLEMENTATION_AGENT_DEFINITION must reference interface scope for "
            "assembly fixes"
        )

    def test_references_language_context(self):
        assert "LANGUAGE_CONTEXT" in IMPLEMENTATION_AGENT_DEFINITION, (
            "IMPLEMENTATION_AGENT_DEFINITION must reference LANGUAGE_CONTEXT"
        )


# ===========================================================================
# COVERAGE_REVIEW_AGENT_DEFINITION
# ===========================================================================


class TestCoverageReviewAgentDefinition:
    """Tests for COVERAGE_REVIEW_AGENT_DEFINITION behavioral contracts."""

    def test_contains_coverage_complete_no_gaps_status(self):
        assert "COVERAGE_COMPLETE: no gaps" in COVERAGE_REVIEW_AGENT_DEFINITION, (
            "COVERAGE_REVIEW_AGENT_DEFINITION must contain "
            "'COVERAGE_COMPLETE: no gaps' status"
        )

    def test_contains_coverage_complete_tests_added_status(self):
        assert "COVERAGE_COMPLETE: tests added" in COVERAGE_REVIEW_AGENT_DEFINITION, (
            "COVERAGE_REVIEW_AGENT_DEFINITION must contain "
            "'COVERAGE_COMPLETE: tests added' status"
        )

    def test_references_gap_detection(self):
        text = COVERAGE_REVIEW_AGENT_DEFINITION.lower()
        assert "gap" in text, (
            "COVERAGE_REVIEW_AGENT_DEFINITION must reference gap detection"
        )

    def test_references_red_green_validation(self):
        text = COVERAGE_REVIEW_AGENT_DEFINITION.lower()
        assert "red" in text or "green" in text, (
            "COVERAGE_REVIEW_AGENT_DEFINITION must reference red-green validation "
            "for new tests"
        )

    def test_references_language_context(self):
        assert "LANGUAGE_CONTEXT" in COVERAGE_REVIEW_AGENT_DEFINITION, (
            "COVERAGE_REVIEW_AGENT_DEFINITION must reference LANGUAGE_CONTEXT"
        )


# ===========================================================================
# INTEGRATION_TEST_AUTHOR_DEFINITION
# ===========================================================================


class TestIntegrationTestAuthorDefinition:
    """Tests for INTEGRATION_TEST_AUTHOR_DEFINITION behavioral contracts."""

    def test_contains_integration_tests_complete_status(self):
        assert "INTEGRATION_TESTS_COMPLETE" in INTEGRATION_TEST_AUTHOR_DEFINITION, (
            "INTEGRATION_TEST_AUTHOR_DEFINITION must contain "
            "INTEGRATION_TESTS_COMPLETE status"
        )

    def test_references_registry_handler_alignment(self):
        text = INTEGRATION_TEST_AUTHOR_DEFINITION.lower()
        assert "registry" in text or "handler" in text or "alignment" in text, (
            "INTEGRATION_TEST_AUTHOR_DEFINITION must reference registry-handler "
            "alignment test generation"
        )

    def test_references_per_language_dispatch_verification(self):
        text = INTEGRATION_TEST_AUTHOR_DEFINITION.lower()
        assert "dispatch" in text or "language" in text, (
            "INTEGRATION_TEST_AUTHOR_DEFINITION must reference per-language "
            "dispatch verification"
        )

    def test_references_cross_unit_tests(self):
        text = INTEGRATION_TEST_AUTHOR_DEFINITION.lower()
        assert "cross" in text or "integration" in text, (
            "INTEGRATION_TEST_AUTHOR_DEFINITION must reference cross-unit tests"
        )

    def test_references_end_to_end(self):
        text = INTEGRATION_TEST_AUTHOR_DEFINITION.lower()
        assert "end" in text or "e2e" in text or "integration" in text, (
            "INTEGRATION_TEST_AUTHOR_DEFINITION must reference end-to-end testing"
        )

    def test_references_language_context(self):
        assert "LANGUAGE_CONTEXT" in INTEGRATION_TEST_AUTHOR_DEFINITION, (
            "INTEGRATION_TEST_AUTHOR_DEFINITION must reference LANGUAGE_CONTEXT"
        )


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
# Status line exclusivity: each definition only contains its own statuses
# ===========================================================================


class TestStatusLineExclusivity:
    """Definitions should only contain their own status lines, not others'."""

    def test_stakeholder_dialog_does_not_contain_blueprint_statuses(self):
        assert "BLUEPRINT_DRAFT_COMPLETE" not in STAKEHOLDER_DIALOG_DEFINITION
        assert "BLUEPRINT_REVISION_COMPLETE" not in STAKEHOLDER_DIALOG_DEFINITION

    def test_stakeholder_reviewer_does_not_contain_spec_draft_status(self):
        assert "SPEC_DRAFT_COMPLETE" not in STAKEHOLDER_REVIEWER_DEFINITION
        assert "SPEC_REVISION_COMPLETE" not in STAKEHOLDER_REVIEWER_DEFINITION

    def test_blueprint_author_does_not_contain_spec_statuses(self):
        assert "SPEC_DRAFT_COMPLETE" not in BLUEPRINT_AUTHOR_DEFINITION
        assert "SPEC_REVISION_COMPLETE" not in BLUEPRINT_AUTHOR_DEFINITION

    def test_blueprint_reviewer_does_not_contain_spec_statuses(self):
        assert "SPEC_DRAFT_COMPLETE" not in BLUEPRINT_REVIEWER_DEFINITION
        assert "SPEC_REVISION_COMPLETE" not in BLUEPRINT_REVIEWER_DEFINITION

    def test_implementation_agent_does_not_contain_test_statuses(self):
        assert "TEST_GENERATION_COMPLETE" not in IMPLEMENTATION_AGENT_DEFINITION
        assert "REGRESSION_TEST_COMPLETE" not in IMPLEMENTATION_AGENT_DEFINITION

    def test_coverage_agent_does_not_contain_implementation_status(self):
        assert "IMPLEMENTATION_COMPLETE" not in COVERAGE_REVIEW_AGENT_DEFINITION

    def test_integration_test_does_not_contain_coverage_statuses(self):
        assert "COVERAGE_COMPLETE" not in INTEGRATION_TEST_AUTHOR_DEFINITION

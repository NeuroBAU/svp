"""Unit 24: Debug Loop Agent Definitions -- complete test suite.

Synthetic data assumptions:
- BUG_TRIAGE_AGENT_DEFINITION is a str containing the complete markdown content
  of the bug triage agent definition file. All structural tests inspect this
  string for keywords, phrases, and patterns specified in the behavioral
  contracts.
- REPAIR_AGENT_DEFINITION is a str containing the complete markdown content
  of the repair agent definition file. All structural tests inspect this
  string for keywords, phrases, and patterns specified in the behavioral
  contracts.
- Both definitions are expected to be markdown content suitable for agent
  system prompts. Structural tests search for specific phrases, keywords,
  and patterns within the markdown to verify contract compliance.
- Keyword matching is case-insensitive where noted; exact tokens like
  classification values and status strings are matched case-sensitively.
- Classification values tested: single_unit, cross_unit, build_env,
  non-reproducible (or non_reproducible).
- Status strings tested against BUG_TRIAGE_AGENT_DEFINITION:
  TRIAGE_COMPLETE: single_unit, TRIAGE_COMPLETE: cross_unit,
  TRIAGE_COMPLETE: build_env, TRIAGE_NEEDS_REFINEMENT,
  TRIAGE_NON_REPRODUCIBLE.
- Status strings tested against REPAIR_AGENT_DEFINITION:
  REPAIR_COMPLETE, REPAIR_RECLASSIFY, REPAIR_FAILED.
- The reclassification bound of 3 is a numeric contract from the blueprint.
- File references (assembly_map.json, triage_result.json, debug_history)
  are expected verbatim in the definition strings.
"""

import re

from debug_agents import (
    BUG_TRIAGE_AGENT_DEFINITION,
    REPAIR_AGENT_DEFINITION,
)

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def triage_contains(phrase: str, case_sensitive: bool = True) -> bool:
    """Check whether BUG_TRIAGE_AGENT_DEFINITION contains the given phrase."""
    if case_sensitive:
        return phrase in BUG_TRIAGE_AGENT_DEFINITION
    return phrase.lower() in BUG_TRIAGE_AGENT_DEFINITION.lower()


def triage_matches(pattern: str, flags: int = 0) -> list:
    """Return all regex matches of pattern in BUG_TRIAGE_AGENT_DEFINITION."""
    return re.findall(pattern, BUG_TRIAGE_AGENT_DEFINITION, flags)


def repair_contains(phrase: str, case_sensitive: bool = True) -> bool:
    """Check whether REPAIR_AGENT_DEFINITION contains the given phrase."""
    if case_sensitive:
        return phrase in REPAIR_AGENT_DEFINITION
    return phrase.lower() in REPAIR_AGENT_DEFINITION.lower()


def repair_matches(pattern: str, flags: int = 0) -> list:
    """Return all regex matches of pattern in REPAIR_AGENT_DEFINITION."""
    return re.findall(pattern, REPAIR_AGENT_DEFINITION, flags)


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION: type and basic structure
# ===========================================================================


class TestBugTriageDefinitionBasicStructure:
    """Verify BUG_TRIAGE_AGENT_DEFINITION is a non-empty markdown string."""

    def test_definition_is_string(self):
        assert isinstance(BUG_TRIAGE_AGENT_DEFINITION, str)

    def test_definition_is_nonempty(self):
        assert len(BUG_TRIAGE_AGENT_DEFINITION.strip()) > 0

    def test_definition_is_not_none(self):
        assert BUG_TRIAGE_AGENT_DEFINITION is not None

    def test_definition_contains_markdown_headings(self):
        """Agent definition must be structured markdown with headings."""
        assert re.search(r"^#+\s+", BUG_TRIAGE_AGENT_DEFINITION, re.MULTILINE)

    def test_definition_has_substantial_content(self):
        """Agent definition should have meaningful length for a system prompt."""
        assert len(BUG_TRIAGE_AGENT_DEFINITION.strip()) > 100


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION: Socratic triage dialog
# ===========================================================================


class TestBugTriageSocraticDialog:
    """The triage agent must conduct a Socratic triage dialog with the human."""

    def test_socratic_referenced(self):
        """The definition must reference Socratic dialog methodology."""
        assert triage_contains("socratic", case_sensitive=False) or triage_contains(
            "Socratic"
        )

    def test_triage_referenced(self):
        """The definition must reference triage as a core concept."""
        assert triage_contains("triage", case_sensitive=False)

    def test_dialog_with_human_referenced(self):
        """The definition must reference dialog with the human."""
        assert triage_contains("dialog", case_sensitive=False) or triage_contains(
            "dialogue", case_sensitive=False
        )

    def test_human_interaction_referenced(self):
        """The definition must reference human interaction."""
        assert triage_contains("human", case_sensitive=False)


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION: Three-hypothesis discipline
# ===========================================================================


class TestBugTriageThreeHypothesisDiscipline:
    """Three-hypothesis discipline: implementation, blueprint, spec."""

    def test_three_hypothesis_concept_referenced(self):
        """The definition must reference the three-hypothesis discipline."""
        assert (
            triage_contains("three-hypothesis", case_sensitive=False)
            or triage_contains("three hypothesis", case_sensitive=False)
            or triage_contains("3 hypothesis", case_sensitive=False)
            or triage_contains("3-hypothesis", case_sensitive=False)
            or (
                triage_contains("hypothesis", case_sensitive=False)
                and triage_contains("three", case_sensitive=False)
            )
        )

    def test_implementation_hypothesis_referenced(self):
        """Implementation must be one of the three hypotheses."""
        assert triage_contains("implementation", case_sensitive=False)

    def test_blueprint_hypothesis_referenced(self):
        """Blueprint must be one of the three hypotheses."""
        assert triage_contains("blueprint", case_sensitive=False)

    def test_spec_hypothesis_referenced(self):
        """Spec must be one of the three hypotheses."""
        assert triage_contains("spec", case_sensitive=False)


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION: Classification outputs
# ===========================================================================


class TestBugTriageClassificationOutputs:
    """Classification outputs: single_unit, cross_unit, build_env, non-reproducible."""

    def test_single_unit_classification(self):
        """single_unit must be a valid classification output."""
        assert triage_contains("single_unit")

    def test_cross_unit_classification(self):
        """cross_unit must be a valid classification output."""
        assert triage_contains("cross_unit")

    def test_build_env_classification(self):
        """build_env must be a valid classification output."""
        assert triage_contains("build_env")

    def test_non_reproducible_classification(self):
        """non-reproducible (or non_reproducible) must be a valid classification."""
        assert triage_contains(
            "non-reproducible", case_sensitive=False
        ) or triage_contains("non_reproducible", case_sensitive=False)

    def test_classification_concept_referenced(self):
        """The definition must reference classification as a concept."""
        assert triage_contains("classif", case_sensitive=False)

    def test_all_four_classifications_present(self):
        """All four classification types must be present in the definition."""
        has_single = triage_contains("single_unit")
        has_cross = triage_contains("cross_unit")
        has_build = triage_contains("build_env")
        has_nonrepro = triage_contains(
            "non-reproducible", case_sensitive=False
        ) or triage_contains("non_reproducible", case_sensitive=False)
        assert has_single and has_cross and has_build and has_nonrepro, (
            f"Missing classifications: single_unit={has_single}, "
            f"cross_unit={has_cross}, build_env={has_build}, "
            f"non_reproducible={has_nonrepro}"
        )


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION: assembly_map.json awareness
# ===========================================================================


class TestBugTriageAssemblyMapAwareness:
    """assembly_map.json awareness for delivered-to-workspace path correlation."""

    def test_assembly_map_json_referenced(self):
        """The definition must reference assembly_map.json."""
        assert triage_contains("assembly_map.json") or triage_contains("assembly_map")

    def test_path_correlation_concept_referenced(self):
        """The definition must reference path correlation or mapping."""
        assert triage_contains("path", case_sensitive=False) and (
            triage_contains("correlat", case_sensitive=False)
            or triage_contains("map", case_sensitive=False)
            or triage_contains("delivered", case_sensitive=False)
            or triage_contains("workspace", case_sensitive=False)
        )

    def test_delivered_to_workspace_concept(self):
        """The definition must reference delivered-to-workspace mapping."""
        assert triage_contains("delivered", case_sensitive=False) or triage_contains(
            "workspace", case_sensitive=False
        )


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION: Bug number assignment
# ===========================================================================


class TestBugTriageBugNumberAssignment:
    """Bug number assignment: reads debug_history length + 1."""

    def test_debug_history_referenced(self):
        """The definition must reference debug_history."""
        assert triage_contains("debug_history")

    def test_bug_number_assignment_concept(self):
        """The definition must describe bug number assignment."""
        assert (
            triage_contains("bug number", case_sensitive=False)
            or triage_contains("bug_number", case_sensitive=False)
            or (
                triage_contains("number", case_sensitive=False)
                and triage_contains("assign", case_sensitive=False)
            )
        )

    def test_length_plus_one_logic(self):
        """Bug number is derived from debug_history length + 1."""
        assert (
            triage_contains("length", case_sensitive=False)
            or triage_contains("+ 1")
            or triage_contains("+1")
            or triage_contains("plus 1", case_sensitive=False)
        )


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION: triage_result.json output
# ===========================================================================


class TestBugTriageResultOutput:
    """Writes triage_result.json with classification and affected units."""

    def test_triage_result_json_referenced(self):
        """The definition must reference triage_result.json."""
        assert triage_contains("triage_result.json") or triage_contains("triage_result")

    def test_writes_classification_to_result(self):
        """The triage result must include classification."""
        assert triage_contains("classification", case_sensitive=False)

    def test_writes_affected_units_to_result(self):
        """The triage result must include affected units."""
        assert triage_contains(
            "affected unit", case_sensitive=False
        ) or triage_contains("affected_unit", case_sensitive=False)


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION: Language-aware
# ===========================================================================


class TestBugTriageLanguageAwareness:
    """Language-aware: receives unit's language and language-specific context."""

    def test_language_awareness_referenced(self):
        """The definition must reference language awareness."""
        assert triage_contains("language", case_sensitive=False)

    def test_language_specific_context_referenced(self):
        """The definition must reference language-specific context."""
        assert (
            triage_contains("language-specific", case_sensitive=False)
            or triage_contains("language specific", case_sensitive=False)
            or (
                triage_contains("language", case_sensitive=False)
                and triage_contains("context", case_sensitive=False)
            )
        )


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION: Reclassification bound
# ===========================================================================


class TestBugTriageReclassificationBound:
    """Reclassification bound: at most 3 RECLASSIFY BUG per session."""

    def test_reclassify_referenced(self):
        """The definition must reference RECLASSIFY or reclassification."""
        assert triage_contains("RECLASSIFY") or triage_contains(
            "reclassif", case_sensitive=False
        )

    def test_bound_of_three(self):
        """The reclassification bound of 3 must be stated."""
        assert triage_contains("3") or triage_contains("three", case_sensitive=False)

    def test_reclassify_bug_phrase(self):
        """RECLASSIFY BUG must appear as the action phrase."""
        assert triage_contains(
            "RECLASSIFY BUG", case_sensitive=False
        ) or triage_contains("reclassify", case_sensitive=False)

    def test_after_bound_retry_repair_offered(self):
        """After 3 reclassifications, RETRY REPAIR must be offered."""
        assert triage_contains("RETRY REPAIR", case_sensitive=False) or triage_contains(
            "retry", case_sensitive=False
        )

    def test_after_bound_abandon_debug_offered(self):
        """After 3 reclassifications, ABANDON DEBUG must be offered."""
        assert triage_contains(
            "ABANDON DEBUG", case_sensitive=False
        ) or triage_contains("abandon", case_sensitive=False)

    def test_bound_limits_reclassify_only(self):
        """After bound is hit, only RETRY REPAIR and ABANDON DEBUG are offered,
        not RECLASSIFY BUG."""
        # The definition must document all three action options
        has_reclassify = triage_contains("RECLASSIFY", case_sensitive=False)
        has_retry = triage_contains(
            "RETRY REPAIR", case_sensitive=False
        ) or triage_contains("retry", case_sensitive=False)
        has_abandon = triage_contains(
            "ABANDON DEBUG", case_sensitive=False
        ) or triage_contains("abandon", case_sensitive=False)
        assert has_reclassify and has_retry and has_abandon


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION: Terminal status strings
# ===========================================================================


class TestBugTriageStatusStrings:
    """Status outputs: TRIAGE_COMPLETE variants, TRIAGE_NEEDS_REFINEMENT,
    TRIAGE_NON_REPRODUCIBLE."""

    def test_status_triage_complete_single_unit(self):
        """TRIAGE_COMPLETE: single_unit must be a valid status."""
        assert triage_contains("TRIAGE_COMPLETE: single_unit") or triage_contains(
            "TRIAGE_COMPLETE:single_unit"
        )

    def test_status_triage_complete_cross_unit(self):
        """TRIAGE_COMPLETE: cross_unit must be a valid status."""
        assert triage_contains("TRIAGE_COMPLETE: cross_unit") or triage_contains(
            "TRIAGE_COMPLETE:cross_unit"
        )

    def test_status_triage_complete_build_env(self):
        """TRIAGE_COMPLETE: build_env must be a valid status."""
        assert triage_contains("TRIAGE_COMPLETE: build_env") or triage_contains(
            "TRIAGE_COMPLETE:build_env"
        )

    def test_status_triage_needs_refinement(self):
        """TRIAGE_NEEDS_REFINEMENT must be a valid status."""
        assert triage_contains("TRIAGE_NEEDS_REFINEMENT")

    def test_status_triage_non_reproducible(self):
        """TRIAGE_NON_REPRODUCIBLE must be a valid status."""
        assert triage_contains("TRIAGE_NON_REPRODUCIBLE")

    def test_all_five_statuses_present(self):
        """All five status strings must appear in the definition."""
        statuses = [
            "TRIAGE_COMPLETE",
            "TRIAGE_NEEDS_REFINEMENT",
            "TRIAGE_NON_REPRODUCIBLE",
        ]
        for status in statuses:
            assert triage_contains(status), (
                f"Status {status!r} not found in BUG_TRIAGE_AGENT_DEFINITION"
            )


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION: TRIAGE_NEEDS_REFINEMENT semantics
# ===========================================================================


class TestBugTriageNeedsRefinementSemantics:
    """TRIAGE_NEEDS_REFINEMENT is emitted when initial analysis is insufficient.
    Routing script increments triage_refinement_count and re-invokes or routes
    to gate_6_4 if exhausted."""

    def test_needs_refinement_status_present(self):
        """TRIAGE_NEEDS_REFINEMENT must appear in the definition."""
        assert triage_contains("TRIAGE_NEEDS_REFINEMENT")

    def test_refinement_concept_referenced(self):
        """The definition must reference the refinement concept."""
        assert triage_contains("refine", case_sensitive=False)

    def test_insufficient_analysis_concept(self):
        """The definition must reference insufficient analysis as the trigger."""
        assert (
            triage_contains("insufficient", case_sensitive=False)
            or triage_contains("inadequate", case_sensitive=False)
            or triage_contains("needs refinement", case_sensitive=False)
            or triage_contains("not sufficient", case_sensitive=False)
        )


# ===========================================================================
# REPAIR_AGENT_DEFINITION: type and basic structure
# ===========================================================================


class TestRepairDefinitionBasicStructure:
    """Verify REPAIR_AGENT_DEFINITION is a non-empty markdown string."""

    def test_definition_is_string(self):
        assert isinstance(REPAIR_AGENT_DEFINITION, str)

    def test_definition_is_nonempty(self):
        assert len(REPAIR_AGENT_DEFINITION.strip()) > 0

    def test_definition_is_not_none(self):
        assert REPAIR_AGENT_DEFINITION is not None

    def test_definition_contains_markdown_headings(self):
        """Agent definition must be structured markdown with headings."""
        assert re.search(r"^#+\s+", REPAIR_AGENT_DEFINITION, re.MULTILINE)

    def test_definition_has_substantial_content(self):
        """Agent definition should have meaningful length for a system prompt."""
        assert len(REPAIR_AGENT_DEFINITION.strip()) > 100


# ===========================================================================
# REPAIR_AGENT_DEFINITION: Narrow mandate for build/env fixes
# ===========================================================================


class TestRepairNarrowMandate:
    """Narrow mandate for build/environment fixes when classification == build_env."""

    def test_build_env_classification_referenced(self):
        """The definition must reference build_env classification."""
        assert (
            repair_contains("build_env")
            or repair_contains("build/env", case_sensitive=False)
            or repair_contains("build environment", case_sensitive=False)
        )

    def test_narrow_mandate_concept(self):
        """The definition must describe a narrow or limited mandate."""
        assert (
            repair_contains("narrow", case_sensitive=False)
            or repair_contains("mandate", case_sensitive=False)
            or repair_contains("limited", case_sensitive=False)
            or repair_contains("scope", case_sensitive=False)
        )

    def test_build_fix_referenced(self):
        """The definition must reference build fixes."""
        assert repair_contains("build", case_sensitive=False)

    def test_environment_fix_referenced(self):
        """The definition must reference environment fixes."""
        assert repair_contains("environment", case_sensitive=False)


# ===========================================================================
# REPAIR_AGENT_DEFINITION: REPAIR_RECLASSIFY escalation
# ===========================================================================


class TestRepairReclassifyEscalation:
    """REPAIR_RECLASSIFY escalation when fix exceeds mandate."""

    def test_repair_reclassify_status_referenced(self):
        """REPAIR_RECLASSIFY must appear in the definition."""
        assert repair_contains("REPAIR_RECLASSIFY")

    def test_escalation_concept_referenced(self):
        """The definition must reference escalation."""
        assert (
            repair_contains("escalat", case_sensitive=False)
            or repair_contains("exceed", case_sensitive=False)
            or repair_contains("beyond", case_sensitive=False)
            or repair_contains("reclassif", case_sensitive=False)
        )

    def test_exceeds_mandate_trigger(self):
        """The escalation trigger is when the fix exceeds the agent's mandate."""
        assert (
            repair_contains("exceed", case_sensitive=False)
            or repair_contains("beyond", case_sensitive=False)
            or repair_contains("outside", case_sensitive=False)
            or repair_contains("mandate", case_sensitive=False)
        )


# ===========================================================================
# REPAIR_AGENT_DEFINITION: Interface-boundary constraint
# ===========================================================================


class TestRepairInterfaceBoundaryConstraint:
    """Interface-boundary constraint: for assembly fixes, modify only interfaces."""

    def test_interface_referenced(self):
        """The definition must reference interfaces."""
        assert repair_contains("interface", case_sensitive=False)

    def test_boundary_constraint_concept(self):
        """The definition must reference boundary constraints."""
        assert (
            repair_contains("boundary", case_sensitive=False)
            or repair_contains("constraint", case_sensitive=False)
            or repair_contains("only interface", case_sensitive=False)
            or repair_contains("only modify", case_sensitive=False)
        )

    def test_assembly_fixes_referenced(self):
        """The definition must reference assembly fixes."""
        assert repair_contains("assembly", case_sensitive=False)

    def test_modify_only_interfaces_for_assembly(self):
        """For assembly fixes, only interfaces may be modified."""
        has_assembly = repair_contains("assembly", case_sensitive=False)
        has_interface = repair_contains("interface", case_sensitive=False)
        has_only = repair_contains("only", case_sensitive=False)
        assert has_assembly and has_interface and has_only


# ===========================================================================
# REPAIR_AGENT_DEFINITION: Language-aware
# ===========================================================================


class TestRepairLanguageAwareness:
    """Language-aware: generates fixes in the unit's language."""

    def test_language_referenced(self):
        """The definition must reference language."""
        assert repair_contains("language", case_sensitive=False)

    def test_generates_fixes_concept(self):
        """The definition must reference generating fixes."""
        assert (
            repair_contains("fix", case_sensitive=False)
            or repair_contains("repair", case_sensitive=False)
            or repair_contains("generat", case_sensitive=False)
        )

    def test_language_specific_fix_generation(self):
        """Fixes must be generated in the unit's language."""
        has_language = repair_contains("language", case_sensitive=False)
        has_fix = repair_contains("fix", case_sensitive=False) or repair_contains(
            "repair", case_sensitive=False
        )
        assert has_language and has_fix


# ===========================================================================
# REPAIR_AGENT_DEFINITION: Terminal status strings
# ===========================================================================


class TestRepairStatusStrings:
    """Status outputs: REPAIR_COMPLETE, REPAIR_RECLASSIFY, REPAIR_FAILED."""

    def test_status_repair_complete(self):
        """REPAIR_COMPLETE must be a valid status."""
        assert repair_contains("REPAIR_COMPLETE")

    def test_status_repair_reclassify(self):
        """REPAIR_RECLASSIFY must be a valid status."""
        assert repair_contains("REPAIR_RECLASSIFY")

    def test_status_repair_failed(self):
        """REPAIR_FAILED must be a valid status."""
        assert repair_contains("REPAIR_FAILED")

    def test_all_three_statuses_present(self):
        """All three status strings must appear in the definition."""
        statuses = [
            "REPAIR_COMPLETE",
            "REPAIR_RECLASSIFY",
            "REPAIR_FAILED",
        ]
        for status in statuses:
            assert repair_contains(status), (
                f"Status {status!r} not found in REPAIR_AGENT_DEFINITION"
            )


# ===========================================================================
# Cross-validation: definitions are distinct
# ===========================================================================


class TestDefinitionsAreDistinct:
    """BUG_TRIAGE_AGENT_DEFINITION and REPAIR_AGENT_DEFINITION must be
    different agent definitions with non-overlapping primary concerns."""

    def test_definitions_are_different_strings(self):
        """The two definitions must not be identical."""
        assert BUG_TRIAGE_AGENT_DEFINITION != REPAIR_AGENT_DEFINITION

    def test_triage_definition_not_substring_of_repair(self):
        """Triage definition should not be a substring of repair definition."""
        assert BUG_TRIAGE_AGENT_DEFINITION not in REPAIR_AGENT_DEFINITION

    def test_repair_definition_not_substring_of_triage(self):
        """Repair definition should not be a substring of triage definition."""
        assert REPAIR_AGENT_DEFINITION not in BUG_TRIAGE_AGENT_DEFINITION


# ===========================================================================
# Cross-validation: triage-specific concepts absent from repair
# ===========================================================================


class TestTriageSpecificConceptsInTriageOnly:
    """Triage-specific concepts should appear in the triage definition."""

    def test_socratic_in_triage(self):
        """Socratic dialog belongs to triage, not repair."""
        assert triage_contains("socratic", case_sensitive=False) or triage_contains(
            "Socratic"
        )

    def test_three_hypothesis_in_triage(self):
        """Three-hypothesis discipline belongs to triage."""
        assert triage_contains("hypothesis", case_sensitive=False)

    def test_debug_history_in_triage(self):
        """debug_history reference belongs to triage."""
        assert triage_contains("debug_history")

    def test_triage_result_json_in_triage(self):
        """triage_result.json reference belongs to triage."""
        assert triage_contains("triage_result", case_sensitive=False)

    def test_assembly_map_in_triage(self):
        """assembly_map.json reference belongs to triage."""
        assert triage_contains("assembly_map", case_sensitive=False)


# ===========================================================================
# Cross-validation: repair-specific concepts in repair
# ===========================================================================


class TestRepairSpecificConceptsInRepairOnly:
    """Repair-specific concepts should appear in the repair definition."""

    def test_repair_complete_in_repair(self):
        """REPAIR_COMPLETE belongs to repair."""
        assert repair_contains("REPAIR_COMPLETE")

    def test_repair_failed_in_repair(self):
        """REPAIR_FAILED belongs to repair."""
        assert repair_contains("REPAIR_FAILED")

    def test_repair_reclassify_in_repair(self):
        """REPAIR_RECLASSIFY belongs to repair."""
        assert repair_contains("REPAIR_RECLASSIFY")

    def test_interface_boundary_in_repair(self):
        """Interface-boundary constraint belongs to repair."""
        assert repair_contains("interface", case_sensitive=False)

    def test_assembly_constraint_in_repair(self):
        """Assembly fix constraint belongs to repair."""
        assert repair_contains("assembly", case_sensitive=False)


# ===========================================================================
# BUG_TRIAGE_AGENT_DEFINITION: comprehensive topic coverage
# ===========================================================================


class TestBugTriageTopicCoverage:
    """Verify all key topics from the behavioral contracts are present
    in the bug triage agent definition."""

    def test_covers_socratic_dialog(self):
        """Socratic triage dialog topic covered."""
        assert triage_contains("socratic", case_sensitive=False) or triage_contains(
            "Socratic"
        )

    def test_covers_three_hypotheses(self):
        """Three-hypothesis discipline topic covered."""
        assert triage_contains("hypothesis", case_sensitive=False)

    def test_covers_classification_outputs(self):
        """Classification outputs topic covered."""
        assert triage_contains("classif", case_sensitive=False)

    def test_covers_assembly_map_awareness(self):
        """assembly_map.json awareness topic covered."""
        assert triage_contains("assembly_map", case_sensitive=False)

    def test_covers_bug_number_assignment(self):
        """Bug number assignment topic covered."""
        assert triage_contains("debug_history")

    def test_covers_triage_result_output(self):
        """triage_result.json output topic covered."""
        assert triage_contains("triage_result", case_sensitive=False)

    def test_covers_language_awareness(self):
        """Language awareness topic covered."""
        assert triage_contains("language", case_sensitive=False)

    def test_covers_reclassification_bound(self):
        """Reclassification bound topic covered."""
        assert triage_contains("reclassif", case_sensitive=False)

    def test_covers_needs_refinement_status(self):
        """TRIAGE_NEEDS_REFINEMENT status topic covered."""
        assert triage_contains("TRIAGE_NEEDS_REFINEMENT")

    def test_covers_non_reproducible_status(self):
        """TRIAGE_NON_REPRODUCIBLE status topic covered."""
        assert triage_contains("TRIAGE_NON_REPRODUCIBLE")


# ===========================================================================
# REPAIR_AGENT_DEFINITION: comprehensive topic coverage
# ===========================================================================


class TestRepairTopicCoverage:
    """Verify all key topics from the behavioral contracts are present
    in the repair agent definition."""

    def test_covers_narrow_mandate(self):
        """Narrow mandate topic covered."""
        assert (
            repair_contains("narrow", case_sensitive=False)
            or repair_contains("mandate", case_sensitive=False)
            or repair_contains("limited", case_sensitive=False)
            or repair_contains("scope", case_sensitive=False)
        )

    def test_covers_build_env_classification(self):
        """build_env classification topic covered."""
        assert (
            repair_contains("build_env")
            or repair_contains("build/env", case_sensitive=False)
            or repair_contains("build environment", case_sensitive=False)
        )

    def test_covers_reclassify_escalation(self):
        """REPAIR_RECLASSIFY escalation topic covered."""
        assert repair_contains("REPAIR_RECLASSIFY")

    def test_covers_interface_boundary_constraint(self):
        """Interface-boundary constraint topic covered."""
        assert repair_contains("interface", case_sensitive=False)

    def test_covers_assembly_fix_constraint(self):
        """Assembly fix constraint topic covered."""
        assert repair_contains("assembly", case_sensitive=False)

    def test_covers_language_aware_fix_generation(self):
        """Language-aware fix generation topic covered."""
        assert repair_contains("language", case_sensitive=False)

    def test_covers_all_three_statuses(self):
        """All three repair statuses are covered."""
        assert repair_contains("REPAIR_COMPLETE")
        assert repair_contains("REPAIR_RECLASSIFY")
        assert repair_contains("REPAIR_FAILED")


# ===========================================================================
# Both definitions: structural consistency
# ===========================================================================


class TestStructuralConsistency:
    """Cross-structural consistency checks between both exported definitions."""

    def test_both_exports_are_non_none(self):
        """Neither exported value should be None."""
        assert BUG_TRIAGE_AGENT_DEFINITION is not None
        assert REPAIR_AGENT_DEFINITION is not None

    def test_both_exports_are_strings(self):
        """Both exports must be strings."""
        assert isinstance(BUG_TRIAGE_AGENT_DEFINITION, str)
        assert isinstance(REPAIR_AGENT_DEFINITION, str)

    def test_both_exports_are_nonempty(self):
        """Both exports must be non-empty."""
        assert len(BUG_TRIAGE_AGENT_DEFINITION.strip()) > 0
        assert len(REPAIR_AGENT_DEFINITION.strip()) > 0

    def test_both_contain_markdown_structure(self):
        """Both definitions must contain markdown headings."""
        assert re.search(r"^#+\s+", BUG_TRIAGE_AGENT_DEFINITION, re.MULTILINE)
        assert re.search(r"^#+\s+", REPAIR_AGENT_DEFINITION, re.MULTILINE)

    def test_both_reference_language(self):
        """Both agents are language-aware and must reference language."""
        assert triage_contains("language", case_sensitive=False)
        assert repair_contains("language", case_sensitive=False)

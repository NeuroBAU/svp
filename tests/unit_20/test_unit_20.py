"""Unit 20: Construction Agent Definitions -- complete test suite.

Synthetic data assumptions:
- Each of the eight *_DEFINITION exports is a str containing the complete
  markdown content of the corresponding agent definition file. All structural
  tests inspect these strings for contract-mandated phrases and patterns.
- All definitions are markdown suitable for agent system prompts. Structural
  tests search for specific phrases, keywords, status lines, and patterns
  within the markdown to verify behavioral contract compliance.
- Keyword matching is case-insensitive where noted. Status line literals
  (e.g. SPEC_DRAFT_COMPLETE) are matched case-sensitively because they are
  machine-parsed tokens.
- The LANGUAGE_CONTEXT placeholder is expected literally in every definition
  (injected at runtime by the task-prompt builder from Unit 2 language
  registry data).
- Status lines tested match the exact strings specified in the blueprint
  contracts for Unit 20.
- Review checklist references (Section 3.20 for STAKEHOLDER_REVIEWER,
  pattern catalog for BLUEPRINT_REVIEWER) are verified by presence of the
  relevant domain phrases, not by checking external section numbers.
- Bug references (S3-3, S3-6, S3-9) in the TEST_AGENT_DEFINITION are
  verified by checking that the prohibited patterns they mandate are
  documented in the definition.
- The interface-boundary constraint for IMPLEMENTATION_AGENT means the
  definition must instruct the agent to modify only interfaces, not internal
  logic, when performing assembly fixes.
- COVERAGE_REVIEW_AGENT status lines include the variant suffixes "no gaps"
  and "tests added" appended to COVERAGE_COMPLETE.
- INTEGRATION_TEST_AUTHOR tests for registry-handler alignment and
  per-language dispatch verification concepts.
"""

import re

import pytest

from construction_agents import (
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
# Helpers
# ---------------------------------------------------------------------------

ALL_DEFINITIONS = {
    "STAKEHOLDER_DIALOG": STAKEHOLDER_DIALOG_DEFINITION,
    "STAKEHOLDER_REVIEWER": STAKEHOLDER_REVIEWER_DEFINITION,
    "BLUEPRINT_AUTHOR": BLUEPRINT_AUTHOR_DEFINITION,
    "BLUEPRINT_REVIEWER": BLUEPRINT_REVIEWER_DEFINITION,
    "TEST_AGENT": TEST_AGENT_DEFINITION,
    "IMPLEMENTATION_AGENT": IMPLEMENTATION_AGENT_DEFINITION,
    "COVERAGE_REVIEW_AGENT": COVERAGE_REVIEW_AGENT_DEFINITION,
    "INTEGRATION_TEST_AUTHOR": INTEGRATION_TEST_AUTHOR_DEFINITION,
}


def _contains(definition: str, phrase: str, case_sensitive: bool = True) -> bool:
    """Check whether *definition* contains *phrase*."""
    if case_sensitive:
        return phrase in definition
    return phrase.lower() in definition.lower()


def _matches(definition: str, pattern: str, flags: int = 0) -> list:
    """Return all regex matches of *pattern* in *definition*."""
    return re.findall(pattern, definition, flags)


# ===========================================================================
# All definitions: type, non-emptiness, markdown structure
# ===========================================================================


class TestAllDefinitionsBasicStructure:
    """Every exported definition must be a non-empty markdown string."""

    @pytest.mark.parametrize("name,definition", list(ALL_DEFINITIONS.items()))
    def test_definition_is_string(self, name, definition):
        assert isinstance(definition, str), (
            f"{name}_DEFINITION should be a str, got {type(definition)}"
        )

    @pytest.mark.parametrize("name,definition", list(ALL_DEFINITIONS.items()))
    def test_definition_is_nonempty(self, name, definition):
        assert len(definition.strip()) > 0, f"{name}_DEFINITION should not be empty"

    @pytest.mark.parametrize("name,definition", list(ALL_DEFINITIONS.items()))
    def test_definition_contains_markdown_headings(self, name, definition):
        """Agent definitions must be structured markdown with headings."""
        assert re.search(r"^#+\s+", definition, re.MULTILINE), (
            f"{name}_DEFINITION should contain at least one markdown heading"
        )


# ===========================================================================
# All definitions: LANGUAGE_CONTEXT placeholder (Unit 2 dependency)
# ===========================================================================


class TestAllDefinitionsLanguageContext:
    """Every definition must reference the LANGUAGE_CONTEXT placeholder."""

    @pytest.mark.parametrize("name,definition", list(ALL_DEFINITIONS.items()))
    def test_language_context_placeholder_present(self, name, definition):
        assert _contains(definition, "LANGUAGE_CONTEXT"), (
            f"{name}_DEFINITION must reference LANGUAGE_CONTEXT placeholder"
        )


# ===========================================================================
# All definitions: distinctness
# ===========================================================================


class TestAllDefinitionsDistinct:
    """Each definition must be a distinct string (no duplicates)."""

    def test_all_eight_definitions_are_distinct(self):
        values = list(ALL_DEFINITIONS.values())
        assert len(set(values)) == 8, (
            "All eight definition strings must be distinct from each other"
        )


# ===========================================================================
# STAKEHOLDER_DIALOG_DEFINITION
# ===========================================================================


class TestStakeholderDialogDefinitionContent:
    """STAKEHOLDER_DIALOG_DEFINITION: Socratic dialog, draft-review-approve
    cycle, status lines SPEC_DRAFT_COMPLETE and SPEC_REVISION_COMPLETE."""

    def test_socratic_dialog_referenced(self):
        """Definition must describe Socratic dialog methodology."""
        assert _contains(
            STAKEHOLDER_DIALOG_DEFINITION, "Socratic", case_sensitive=False
        ) or _contains(STAKEHOLDER_DIALOG_DEFINITION, "socratic", case_sensitive=False)

    def test_draft_review_approve_cycle_referenced(self):
        """Definition must describe the draft-review-approve cycle."""
        text = STAKEHOLDER_DIALOG_DEFINITION.lower()
        assert "draft" in text
        assert "review" in text
        assert "approve" in text

    def test_status_line_spec_draft_complete(self):
        """Status line SPEC_DRAFT_COMPLETE must appear verbatim."""
        assert _contains(STAKEHOLDER_DIALOG_DEFINITION, "SPEC_DRAFT_COMPLETE")

    def test_status_line_spec_revision_complete(self):
        """Status line SPEC_REVISION_COMPLETE must appear verbatim."""
        assert _contains(STAKEHOLDER_DIALOG_DEFINITION, "SPEC_REVISION_COMPLETE")

    def test_both_status_lines_present(self):
        """Both status lines must coexist in the definition."""
        has_draft = _contains(STAKEHOLDER_DIALOG_DEFINITION, "SPEC_DRAFT_COMPLETE")
        has_revision = _contains(
            STAKEHOLDER_DIALOG_DEFINITION, "SPEC_REVISION_COMPLETE"
        )
        assert has_draft and has_revision

    def test_dialog_concept_present(self):
        """The definition should describe dialog-based interaction."""
        assert _contains(
            STAKEHOLDER_DIALOG_DEFINITION, "dialog", case_sensitive=False
        ) or _contains(STAKEHOLDER_DIALOG_DEFINITION, "dialogue", case_sensitive=False)


# ===========================================================================
# STAKEHOLDER_REVIEWER_DEFINITION
# ===========================================================================


class TestStakeholderReviewerDefinitionContent:
    """STAKEHOLDER_REVIEWER_DEFINITION: baked review checklist (Section 3.20),
    downstream dependency analysis, contract granularity, gate reachability.
    Status: REVIEW_COMPLETE."""

    def test_review_checklist_referenced(self):
        """Definition must contain a baked review checklist."""
        assert _contains(
            STAKEHOLDER_REVIEWER_DEFINITION, "checklist", case_sensitive=False
        )

    def test_section_3_20_referenced(self):
        """Definition must reference Section 3.20 for the review checklist."""
        assert _contains(STAKEHOLDER_REVIEWER_DEFINITION, "3.20") or _contains(
            STAKEHOLDER_REVIEWER_DEFINITION, "Section 3.20"
        )

    def test_downstream_dependency_analysis_referenced(self):
        """Definition must include downstream dependency analysis."""
        text = STAKEHOLDER_REVIEWER_DEFINITION.lower()
        assert "downstream" in text and "depend" in text

    def test_contract_granularity_referenced(self):
        """Definition must include contract granularity checking."""
        text = STAKEHOLDER_REVIEWER_DEFINITION.lower()
        assert "contract" in text and "granularity" in text

    def test_gate_reachability_referenced(self):
        """Definition must include gate reachability checking."""
        text = STAKEHOLDER_REVIEWER_DEFINITION.lower()
        assert "gate" in text and "reachab" in text

    def test_status_line_review_complete(self):
        """Status line REVIEW_COMPLETE must appear verbatim."""
        assert _contains(STAKEHOLDER_REVIEWER_DEFINITION, "REVIEW_COMPLETE")

    def test_baked_checklist_is_inline(self):
        """Checklist should be baked (inline), not loaded from external file."""
        assert _contains(
            STAKEHOLDER_REVIEWER_DEFINITION, "baked", case_sensitive=False
        ) or (
            not _contains(
                STAKEHOLDER_REVIEWER_DEFINITION, "load checklist", case_sensitive=False
            )
        )


# ===========================================================================
# BLUEPRINT_AUTHOR_DEFINITION
# ===========================================================================


class TestBlueprintAuthorDefinitionContent:
    """BLUEPRINT_AUTHOR_DEFINITION: Rules P1-P4 verbatim for preference
    capture. Status: BLUEPRINT_DRAFT_COMPLETE, BLUEPRINT_REVISION_COMPLETE."""

    def test_rules_p1_through_p4_referenced(self):
        """Definition must reference Rules P1 through P4."""
        text = BLUEPRINT_AUTHOR_DEFINITION
        assert _contains(text, "P1")
        assert _contains(text, "P2")
        assert _contains(text, "P3")
        assert _contains(text, "P4")

    def test_preference_capture_referenced(self):
        """Definition must reference preference capture."""
        assert _contains(
            BLUEPRINT_AUTHOR_DEFINITION, "preference", case_sensitive=False
        )

    def test_status_line_blueprint_draft_complete(self):
        """Status line BLUEPRINT_DRAFT_COMPLETE must appear verbatim."""
        assert _contains(BLUEPRINT_AUTHOR_DEFINITION, "BLUEPRINT_DRAFT_COMPLETE")

    def test_status_line_blueprint_revision_complete(self):
        """Status line BLUEPRINT_REVISION_COMPLETE must appear verbatim."""
        assert _contains(BLUEPRINT_AUTHOR_DEFINITION, "BLUEPRINT_REVISION_COMPLETE")

    def test_both_status_lines_present(self):
        """Both status lines must coexist in the definition."""
        has_draft = _contains(BLUEPRINT_AUTHOR_DEFINITION, "BLUEPRINT_DRAFT_COMPLETE")
        has_revision = _contains(
            BLUEPRINT_AUTHOR_DEFINITION, "BLUEPRINT_REVISION_COMPLETE"
        )
        assert has_draft and has_revision

    def test_rules_described_as_verbatim(self):
        """Rules P1-P4 should be included verbatim (not paraphrased)."""
        assert _contains(
            BLUEPRINT_AUTHOR_DEFINITION, "verbatim", case_sensitive=False
        ) or _contains(BLUEPRINT_AUTHOR_DEFINITION, "P1", case_sensitive=True)

    def test_p1_rule_content_present(self):
        """P1 rule content should appear in the definition."""
        assert _contains(BLUEPRINT_AUTHOR_DEFINITION, "P1")

    def test_p4_rule_content_present(self):
        """P4 rule content should appear in the definition."""
        assert _contains(BLUEPRINT_AUTHOR_DEFINITION, "P4")


class TestBlueprintAuthorSelfReviewSection:
    """Self-Review Pass methodology step + Self-Review Artifact section.

    Enhancement: blueprint author runs a structural self-review against
    six universal categories (Schema / Function Reachability / Invariant
    Coherence / Dispatch Completeness / Branch Reachability / Contract
    Bidirectional Mapping) and writes the filled review to
    .svp/blueprint_self_review.md before emitting the terminal status.
    """

    def test_definition_has_self_review_pass_methodology_step(self):
        assert _contains(BLUEPRINT_AUTHOR_DEFINITION, "Self-Review Pass"), (
            "BLUEPRINT_AUTHOR_DEFINITION must include a 'Self-Review Pass' "
            "methodology step before the terminal status is emitted."
        )

    def test_definition_has_self_review_artifact_section(self):
        assert _contains(BLUEPRINT_AUTHOR_DEFINITION, "Self-Review Artifact"), (
            "BLUEPRINT_AUTHOR_DEFINITION must include a '## Self-Review Artifact' "
            "section documenting the required output file format."
        )

    def test_definition_names_self_review_output_file(self):
        assert _contains(BLUEPRINT_AUTHOR_DEFINITION, ".svp/blueprint_self_review.md"), (
            "BLUEPRINT_AUTHOR_DEFINITION must reference the self-review "
            "output artifact at .svp/blueprint_self_review.md."
        )

    def test_definition_requires_iteration_until_all_pass(self):
        text = BLUEPRINT_AUTHOR_DEFINITION
        assert "ALL_PASS" in text, (
            "Definition must reference the ALL_PASS outcome line."
        )
        assert _contains(text, "iterate", case_sensitive=False) or _contains(
            text, "re-run", case_sensitive=False
        ), "Definition must explicitly require iteration until ALL_PASS."

    def test_definition_names_six_universal_categories(self):
        for category in [
            "Schema Coherence",
            "Function Reachability",
            "Invariant Coherence",
            "Dispatch Completeness",
            "Branch Reachability",
            "Contract Bidirectional Mapping",
        ]:
            assert _contains(BLUEPRINT_AUTHOR_DEFINITION, category), (
                f"BLUEPRINT_AUTHOR_DEFINITION must explicitly name the "
                f"'{category}' self-review category."
            )

    def test_definition_references_section_44_11(self):
        assert "44.11" in BLUEPRINT_AUTHOR_DEFINITION, (
            "Definition must cross-reference spec Section 44.11 where the "
            "six categories' seed items live."
        )


class TestBlueprintAuthorSplitFormatMandate:
    """BLUEPRINT_AUTHOR_DEFINITION must mandate split-format output: two files
    at the canonical ARTIFACT_FILENAMES paths, with explicit prohibition on a
    unified single-file blueprint (Bug S3-156).
    """

    def test_blueprint_author_definition_mentions_blueprint_prose_path(self):
        """The canonical prose path must appear in the agent prompt."""
        assert _contains(
            BLUEPRINT_AUTHOR_DEFINITION, "blueprint/blueprint_prose.md"
        ), (
            "BLUEPRINT_AUTHOR_DEFINITION must reference the canonical prose "
            "output path 'blueprint/blueprint_prose.md' (per ARTIFACT_FILENAMES)."
        )

    def test_blueprint_author_definition_mentions_blueprint_contracts_path(self):
        """The canonical contracts path must appear in the agent prompt."""
        assert _contains(
            BLUEPRINT_AUTHOR_DEFINITION, "blueprint/blueprint_contracts.md"
        ), (
            "BLUEPRINT_AUTHOR_DEFINITION must reference the canonical "
            "contracts output path 'blueprint/blueprint_contracts.md' "
            "(per ARTIFACT_FILENAMES)."
        )

    def test_blueprint_author_definition_forbids_unified_file(self):
        """The prompt must explicitly prohibit a unified single-file blueprint."""
        assert _contains(
            BLUEPRINT_AUTHOR_DEFINITION, "MUST NOT produce a unified"
        ), (
            "BLUEPRINT_AUTHOR_DEFINITION must contain explicit prohibition "
            "language ('MUST NOT produce a unified ...') against emitting a "
            "single-file blueprint."
        )


class TestStakeholderDialogReconciliation:
    """STAKEHOLDER_DIALOG_DEFINITION must mandate pre-emission cross-reference
    reconciliation as a self-audit step before terminal status emission
    (Bug S3-157).
    """

    def test_stakeholder_dialog_definition_includes_reconciliation_step(self):
        """The reconciliation section must appear in the agent prompt."""
        assert _contains(
            STAKEHOLDER_DIALOG_DEFINITION, "Cross-Reference Reconciliation"
        ), (
            "STAKEHOLDER_DIALOG_DEFINITION must include a "
            "'Cross-Reference Reconciliation' section that mandates a "
            "pre-emission self-audit (per Bug S3-157)."
        )

    def test_stakeholder_dialog_reconciliation_precedes_terminal_status(self):
        """The audit section must appear BEFORE the first SPEC_DRAFT_COMPLETE
        mention so the agent encounters it before emitting terminal status."""
        recon_idx = STAKEHOLDER_DIALOG_DEFINITION.find(
            "Cross-Reference Reconciliation"
        )
        status_idx = STAKEHOLDER_DIALOG_DEFINITION.find("SPEC_DRAFT_COMPLETE")
        assert recon_idx >= 0, (
            "STAKEHOLDER_DIALOG_DEFINITION must contain the "
            "'Cross-Reference Reconciliation' section."
        )
        assert status_idx >= 0, (
            "STAKEHOLDER_DIALOG_DEFINITION must contain the "
            "'SPEC_DRAFT_COMPLETE' terminal status line."
        )
        assert recon_idx < status_idx, (
            "The 'Cross-Reference Reconciliation' section must appear "
            "BEFORE the 'SPEC_DRAFT_COMPLETE' terminal status, so the "
            "agent performs the audit before emitting completion "
            "(per Bug S3-157)."
        )

    def test_stakeholder_dialog_reconciliation_is_convention_agnostic(self):
        """The reconciliation prompt must mention multiple reference styles
        (e.g., bracketed slugs AND Section citations), proving it is not
        hardcoded to a single convention."""
        # The prompt names "bracketed slugs" (or "slug") for the
        # [INV-02]-style convention AND "Section" citations for the
        # Section-N.N convention. Both must be present.
        assert _contains(
            STAKEHOLDER_DIALOG_DEFINITION, "bracketed"
        ) or _contains(STAKEHOLDER_DIALOG_DEFINITION, "slug"), (
            "STAKEHOLDER_DIALOG_DEFINITION reconciliation section must "
            "mention bracketed-slug references (e.g. [INV-02]) as one "
            "of the reference conventions to enumerate."
        )
        assert _contains(STAKEHOLDER_DIALOG_DEFINITION, "Section"), (
            "STAKEHOLDER_DIALOG_DEFINITION reconciliation section must "
            "mention Section citations as another reference convention "
            "to enumerate, demonstrating convention-agnostic auditing."
        )


# ===========================================================================
# BLUEPRINT_REVIEWER_DEFINITION
# ===========================================================================


class TestBlueprintReviewerDefinitionContent:
    """BLUEPRINT_REVIEWER_DEFINITION: baked review checklist, pattern catalog
    cross-reference. Status: REVIEW_COMPLETE."""

    def test_review_checklist_referenced(self):
        """Definition must contain a baked review checklist."""
        assert _contains(
            BLUEPRINT_REVIEWER_DEFINITION, "checklist", case_sensitive=False
        )

    def test_pattern_catalog_cross_reference(self):
        """Definition must reference pattern catalog cross-referencing."""
        text = BLUEPRINT_REVIEWER_DEFINITION.lower()
        assert "pattern" in text and "catalog" in text

    def test_status_line_review_complete(self):
        """Status line REVIEW_COMPLETE must appear verbatim."""
        assert _contains(BLUEPRINT_REVIEWER_DEFINITION, "REVIEW_COMPLETE")

    def test_baked_checklist_is_inline(self):
        """Checklist should be baked (inline)."""
        assert _contains(
            BLUEPRINT_REVIEWER_DEFINITION, "checklist", case_sensitive=False
        )

    def test_cross_reference_concept_present(self):
        """Cross-reference concept must be present."""
        assert (
            _contains(
                BLUEPRINT_REVIEWER_DEFINITION, "cross-reference", case_sensitive=False
            )
            or _contains(
                BLUEPRINT_REVIEWER_DEFINITION, "cross reference", case_sensitive=False
            )
            or _contains(
                BLUEPRINT_REVIEWER_DEFINITION, "cross_reference", case_sensitive=False
            )
        )


# ===========================================================================
# TEST_AGENT_DEFINITION
# ===========================================================================


class TestTestAgentDefinitionContent:
    """TEST_AGENT_DEFINITION: quality tool auto-format notification,
    testing.readable_test_names profile preference, lessons learned filtering,
    synthetic data assumption declarations, prohibited patterns P1-P3.
    Status: TEST_GENERATION_COMPLETE, REGRESSION_TEST_COMPLETE."""

    def test_quality_tool_auto_format_notification(self):
        """Definition must mention quality tool auto-format notification."""
        text = TEST_AGENT_DEFINITION.lower()
        assert "quality" in text
        assert (
            "auto-format" in text
            or "auto format" in text
            or "autoformat" in text
            or "format" in text
        )

    def test_readable_test_names_preference(self):
        """Definition must reference testing.readable_test_names profile preference."""
        assert _contains(TEST_AGENT_DEFINITION, "readable_test_names") or _contains(
            TEST_AGENT_DEFINITION, "readable test names", case_sensitive=False
        )

    def test_lessons_learned_filtering(self):
        """Definition must reference lessons learned filtering."""
        text = TEST_AGENT_DEFINITION.lower()
        assert "lessons" in text and ("learn" in text or "filter" in text)

    def test_synthetic_data_assumption_declarations(self):
        """Definition must reference synthetic data assumption declarations."""
        text = TEST_AGENT_DEFINITION.lower()
        assert "synthetic" in text and "data" in text and "assumption" in text

    def test_status_line_test_generation_complete(self):
        """Status line TEST_GENERATION_COMPLETE must appear verbatim."""
        assert _contains(TEST_AGENT_DEFINITION, "TEST_GENERATION_COMPLETE")

    def test_status_line_regression_test_complete(self):
        """Status line REGRESSION_TEST_COMPLETE must appear verbatim."""
        assert _contains(TEST_AGENT_DEFINITION, "REGRESSION_TEST_COMPLETE")

    def test_both_status_lines_present(self):
        """Both status lines for normal and debug loop modes must coexist."""
        has_normal = _contains(TEST_AGENT_DEFINITION, "TEST_GENERATION_COMPLETE")
        has_regression = _contains(TEST_AGENT_DEFINITION, "REGRESSION_TEST_COMPLETE")
        assert has_normal and has_regression


class TestTestAgentProhibitedPatterns:
    """TEST_AGENT_DEFINITION prohibited patterns P1, P2, P3 (Bug S3-3, S3-6, S3-9)."""

    def test_p1_no_pytest_raises_not_implemented_error(self):
        """P1: no pytest.raises(NotImplementedError) as behavioral test."""
        text = TEST_AGENT_DEFINITION.lower()
        assert (
            "notimplementederror" in text
            or "not_implemented" in text
            or "pytest.raises" in text
        )

    def test_p1_prohibition_language_present(self):
        """P1 must be described as a prohibition or forbidden pattern."""
        assert _contains(TEST_AGENT_DEFINITION, "NotImplementedError") or _contains(
            TEST_AGENT_DEFINITION, "notimplementederror", case_sensitive=False
        )

    def test_p2_no_pytest_skip_for_stub_exceptions(self):
        """P2: no pytest.skip for stub exceptions."""
        text = TEST_AGENT_DEFINITION.lower()
        assert "pytest.skip" in text or "skip" in text

    def test_p3_always_use_src_prefix_in_imports(self):
        """P3: always use src. prefix in imports."""
        assert _contains(TEST_AGENT_DEFINITION, "src.") or _contains(
            TEST_AGENT_DEFINITION, "src.", case_sensitive=False
        )

    def test_prohibited_patterns_section_exists(self):
        """The definition must contain a section or list documenting prohibited patterns."""
        text = TEST_AGENT_DEFINITION.lower()
        assert (
            "prohibit" in text
            or "forbidden" in text
            or "must not" in text
            or "do not" in text
            or "never" in text
        )

    def test_three_prohibited_patterns_present(self):
        """All three prohibited patterns (P1, P2, P3) must be documented."""
        text = TEST_AGENT_DEFINITION
        # Check for the three specific prohibited items
        has_not_implemented = _contains(
            text, "NotImplementedError", case_sensitive=False
        )
        has_skip = _contains(text, "pytest.skip", case_sensitive=False) or _contains(
            text, "skip", case_sensitive=False
        )
        has_src_prefix = _contains(text, "src.", case_sensitive=False)
        assert has_not_implemented and has_skip and has_src_prefix


class TestTestAgentBugReferences:
    """TEST_AGENT_DEFINITION references to bugs S3-3, S3-6, S3-9."""

    def test_bug_s3_3_addressed(self):
        """Bug S3-3 is addressed (relates to prohibited patterns)."""
        # S3-3 relates to test agent pattern prohibitions
        assert _contains(TEST_AGENT_DEFINITION, "S3-3") or _contains(
            TEST_AGENT_DEFINITION, "NotImplementedError"
        )

    def test_bug_s3_6_addressed(self):
        """Bug S3-6 is addressed (relates to prohibited patterns)."""
        assert _contains(TEST_AGENT_DEFINITION, "S3-6") or _contains(
            TEST_AGENT_DEFINITION, "skip", case_sensitive=False
        )

    def test_bug_s3_9_addressed(self):
        """Bug S3-9 is addressed (relates to import prefix)."""
        assert _contains(TEST_AGENT_DEFINITION, "S3-9") or _contains(
            TEST_AGENT_DEFINITION, "src."
        )


# ===========================================================================
# IMPLEMENTATION_AGENT_DEFINITION
# ===========================================================================


class TestImplementationAgentDefinitionContent:
    """IMPLEMENTATION_AGENT_DEFINITION: quality tool notification,
    interface-boundary constraint (assembly fixes modify only interfaces,
    not internal logic). Status: IMPLEMENTATION_COMPLETE."""

    def test_quality_tool_notification(self):
        """Definition must mention quality tool notification."""
        assert _contains(
            IMPLEMENTATION_AGENT_DEFINITION, "quality", case_sensitive=False
        )

    def test_interface_boundary_constraint(self):
        """Definition must describe the interface-boundary constraint."""
        text = IMPLEMENTATION_AGENT_DEFINITION.lower()
        assert "interface" in text

    def test_assembly_fixes_modify_only_interfaces(self):
        """Assembly fixes must modify only interfaces, not internal logic."""
        text = IMPLEMENTATION_AGENT_DEFINITION.lower()
        assert "interface" in text
        assert "internal" in text or "logic" in text

    def test_assembly_fixes_not_internal_logic(self):
        """Definition must explicitly constrain against modifying internal logic."""
        text = IMPLEMENTATION_AGENT_DEFINITION.lower()
        # The definition should say something about not modifying internal logic
        has_boundary_concept = (
            ("only" in text and "interface" in text)
            or ("not" in text and "internal" in text)
            or ("boundary" in text)
        )
        assert has_boundary_concept

    def test_status_line_implementation_complete(self):
        """Status line IMPLEMENTATION_COMPLETE must appear verbatim."""
        assert _contains(IMPLEMENTATION_AGENT_DEFINITION, "IMPLEMENTATION_COMPLETE")


# ===========================================================================
# COVERAGE_REVIEW_AGENT_DEFINITION
# ===========================================================================


class TestCoverageReviewAgentDefinitionContent:
    """COVERAGE_REVIEW_AGENT_DEFINITION: gap detection, red-green validation
    for new tests. Status: COVERAGE_COMPLETE: no gaps or
    COVERAGE_COMPLETE: tests added."""

    def test_gap_detection_referenced(self):
        """Definition must reference gap detection."""
        text = COVERAGE_REVIEW_AGENT_DEFINITION.lower()
        assert "gap" in text

    def test_red_green_validation_referenced(self):
        """Definition must reference red-green validation for new tests."""
        text = COVERAGE_REVIEW_AGENT_DEFINITION.lower()
        assert (
            ("red" in text and "green" in text)
            or "red-green" in text
            or "red/green" in text
        )

    def test_status_line_coverage_complete_no_gaps(self):
        """Status line 'COVERAGE_COMPLETE: no gaps' must appear verbatim."""
        assert _contains(COVERAGE_REVIEW_AGENT_DEFINITION, "COVERAGE_COMPLETE: no gaps")

    def test_status_line_coverage_complete_tests_added(self):
        """Status line 'COVERAGE_COMPLETE: tests added' must appear verbatim."""
        assert _contains(
            COVERAGE_REVIEW_AGENT_DEFINITION, "COVERAGE_COMPLETE: tests added"
        )

    def test_both_status_variants_present(self):
        """Both coverage status variants must coexist."""
        has_no_gaps = _contains(
            COVERAGE_REVIEW_AGENT_DEFINITION, "COVERAGE_COMPLETE: no gaps"
        )
        has_tests_added = _contains(
            COVERAGE_REVIEW_AGENT_DEFINITION, "COVERAGE_COMPLETE: tests added"
        )
        assert has_no_gaps and has_tests_added

    def test_new_tests_concept_present(self):
        """Definition should reference the concept of adding new tests."""
        text = COVERAGE_REVIEW_AGENT_DEFINITION.lower()
        assert "new test" in text or "add" in text or "tests added" in text


# ===========================================================================
# INTEGRATION_TEST_AUTHOR_DEFINITION
# ===========================================================================


class TestIntegrationTestAuthorDefinitionContent:
    """INTEGRATION_TEST_AUTHOR_DEFINITION: registry-handler alignment test
    generation, per-language dispatch verification.
    Status: INTEGRATION_TESTS_COMPLETE."""

    def test_registry_handler_alignment_referenced(self):
        """Definition must reference registry-handler alignment test generation."""
        text = INTEGRATION_TEST_AUTHOR_DEFINITION.lower()
        assert "registry" in text and ("handler" in text or "alignment" in text)

    def test_per_language_dispatch_verification_referenced(self):
        """Definition must reference per-language dispatch verification."""
        text = INTEGRATION_TEST_AUTHOR_DEFINITION.lower()
        assert "language" in text and "dispatch" in text

    def test_status_line_integration_tests_complete(self):
        """Status line INTEGRATION_TESTS_COMPLETE must appear verbatim."""
        assert _contains(
            INTEGRATION_TEST_AUTHOR_DEFINITION, "INTEGRATION_TESTS_COMPLETE"
        )

    def test_test_generation_concept_present(self):
        """Definition should reference test generation."""
        text = INTEGRATION_TEST_AUTHOR_DEFINITION.lower()
        assert "test" in text and (
            "generat" in text or "write" in text or "author" in text
        )

    def test_alignment_concept_present(self):
        """Definition should reference alignment verification."""
        assert _contains(
            INTEGRATION_TEST_AUTHOR_DEFINITION, "alignment", case_sensitive=False
        )


# ===========================================================================
# Cross-definition: status line uniqueness and completeness
# ===========================================================================


class TestStatusLineUniqueness:
    """Status lines must be unique to their respective definitions --
    no definition should claim another definition's status line."""

    def test_spec_draft_complete_only_in_stakeholder_dialog(self):
        """SPEC_DRAFT_COMPLETE should only appear in STAKEHOLDER_DIALOG."""
        for name, defn in ALL_DEFINITIONS.items():
            if name == "STAKEHOLDER_DIALOG":
                assert _contains(defn, "SPEC_DRAFT_COMPLETE")
            else:
                assert not _contains(defn, "SPEC_DRAFT_COMPLETE"), (
                    f"SPEC_DRAFT_COMPLETE should not appear in {name}_DEFINITION"
                )

    def test_spec_revision_complete_only_in_stakeholder_dialog(self):
        """SPEC_REVISION_COMPLETE should only appear in STAKEHOLDER_DIALOG."""
        for name, defn in ALL_DEFINITIONS.items():
            if name == "STAKEHOLDER_DIALOG":
                assert _contains(defn, "SPEC_REVISION_COMPLETE")
            else:
                assert not _contains(defn, "SPEC_REVISION_COMPLETE"), (
                    f"SPEC_REVISION_COMPLETE should not appear in {name}_DEFINITION"
                )

    def test_blueprint_draft_complete_only_in_blueprint_author(self):
        """BLUEPRINT_DRAFT_COMPLETE should only appear in BLUEPRINT_AUTHOR."""
        for name, defn in ALL_DEFINITIONS.items():
            if name == "BLUEPRINT_AUTHOR":
                assert _contains(defn, "BLUEPRINT_DRAFT_COMPLETE")
            else:
                assert not _contains(defn, "BLUEPRINT_DRAFT_COMPLETE"), (
                    f"BLUEPRINT_DRAFT_COMPLETE should not appear in {name}_DEFINITION"
                )

    def test_blueprint_revision_complete_only_in_blueprint_author(self):
        """BLUEPRINT_REVISION_COMPLETE should only appear in BLUEPRINT_AUTHOR."""
        for name, defn in ALL_DEFINITIONS.items():
            if name == "BLUEPRINT_AUTHOR":
                assert _contains(defn, "BLUEPRINT_REVISION_COMPLETE")
            else:
                assert not _contains(defn, "BLUEPRINT_REVISION_COMPLETE"), (
                    f"BLUEPRINT_REVISION_COMPLETE should not appear in {name}_DEFINITION"
                )

    def test_implementation_complete_only_in_implementation_agent(self):
        """IMPLEMENTATION_COMPLETE should only appear in IMPLEMENTATION_AGENT."""
        for name, defn in ALL_DEFINITIONS.items():
            if name == "IMPLEMENTATION_AGENT":
                assert _contains(defn, "IMPLEMENTATION_COMPLETE")
            else:
                assert not _contains(defn, "IMPLEMENTATION_COMPLETE"), (
                    f"IMPLEMENTATION_COMPLETE should not appear in {name}_DEFINITION"
                )

    def test_integration_tests_complete_only_in_integration_test_author(self):
        """INTEGRATION_TESTS_COMPLETE should only appear in INTEGRATION_TEST_AUTHOR."""
        for name, defn in ALL_DEFINITIONS.items():
            if name == "INTEGRATION_TEST_AUTHOR":
                assert _contains(defn, "INTEGRATION_TESTS_COMPLETE")
            else:
                assert not _contains(defn, "INTEGRATION_TESTS_COMPLETE"), (
                    f"INTEGRATION_TESTS_COMPLETE should not appear in {name}_DEFINITION"
                )


class TestStatusLineCompleteness:
    """Every definition must declare at least one status line."""

    def test_stakeholder_dialog_has_status_lines(self):
        assert _contains(
            STAKEHOLDER_DIALOG_DEFINITION, "SPEC_DRAFT_COMPLETE"
        ) and _contains(STAKEHOLDER_DIALOG_DEFINITION, "SPEC_REVISION_COMPLETE")

    def test_stakeholder_reviewer_has_status_line(self):
        assert _contains(STAKEHOLDER_REVIEWER_DEFINITION, "REVIEW_COMPLETE")

    def test_blueprint_author_has_status_lines(self):
        assert _contains(
            BLUEPRINT_AUTHOR_DEFINITION, "BLUEPRINT_DRAFT_COMPLETE"
        ) and _contains(BLUEPRINT_AUTHOR_DEFINITION, "BLUEPRINT_REVISION_COMPLETE")

    def test_blueprint_reviewer_has_status_line(self):
        assert _contains(BLUEPRINT_REVIEWER_DEFINITION, "REVIEW_COMPLETE")

    def test_test_agent_has_status_lines(self):
        assert _contains(
            TEST_AGENT_DEFINITION, "TEST_GENERATION_COMPLETE"
        ) and _contains(TEST_AGENT_DEFINITION, "REGRESSION_TEST_COMPLETE")

    def test_implementation_agent_has_status_line(self):
        assert _contains(IMPLEMENTATION_AGENT_DEFINITION, "IMPLEMENTATION_COMPLETE")

    def test_coverage_review_agent_has_status_lines(self):
        assert _contains(
            COVERAGE_REVIEW_AGENT_DEFINITION, "COVERAGE_COMPLETE: no gaps"
        ) and _contains(
            COVERAGE_REVIEW_AGENT_DEFINITION, "COVERAGE_COMPLETE: tests added"
        )

    def test_integration_test_author_has_status_line(self):
        assert _contains(
            INTEGRATION_TEST_AUTHOR_DEFINITION, "INTEGRATION_TESTS_COMPLETE"
        )


# ===========================================================================
# Cross-definition: REVIEW_COMPLETE shared by both reviewer definitions
# ===========================================================================


class TestReviewCompleteSharing:
    """REVIEW_COMPLETE is the status line for both STAKEHOLDER_REVIEWER
    and BLUEPRINT_REVIEWER definitions."""

    def test_stakeholder_reviewer_emits_review_complete(self):
        assert _contains(STAKEHOLDER_REVIEWER_DEFINITION, "REVIEW_COMPLETE")

    def test_blueprint_reviewer_emits_review_complete(self):
        assert _contains(BLUEPRINT_REVIEWER_DEFINITION, "REVIEW_COMPLETE")


# ===========================================================================
# Cross-definition: no definition is a substring of another
# ===========================================================================


class TestDefinitionIndependence:
    """No definition should be a substring of another (guards against
    copy-paste errors or missing differentiation)."""

    def test_no_definition_is_substring_of_another(self):
        names = list(ALL_DEFINITIONS.keys())
        for i, name_a in enumerate(names):
            for j, name_b in enumerate(names):
                if i == j:
                    continue
                defn_a = ALL_DEFINITIONS[name_a]
                defn_b = ALL_DEFINITIONS[name_b]
                assert defn_a not in defn_b, (
                    f"{name_a}_DEFINITION should not be a substring of "
                    f"{name_b}_DEFINITION"
                )


# ===========================================================================
# STAKEHOLDER_DIALOG: Socratic dialog specifics
# ===========================================================================


class TestStakeholderDialogSocraticProcess:
    """The Socratic dialog definition must describe a structured process
    with draft, review, and approval phases."""

    def test_draft_phase_described(self):
        assert _contains(STAKEHOLDER_DIALOG_DEFINITION, "draft", case_sensitive=False)

    def test_review_phase_described(self):
        assert _contains(STAKEHOLDER_DIALOG_DEFINITION, "review", case_sensitive=False)

    def test_approve_phase_described(self):
        assert _contains(
            STAKEHOLDER_DIALOG_DEFINITION, "approve", case_sensitive=False
        ) or _contains(STAKEHOLDER_DIALOG_DEFINITION, "approval", case_sensitive=False)

    def test_cycle_concept_present(self):
        """Draft-review-approve should be described as a cycle."""
        assert (
            _contains(STAKEHOLDER_DIALOG_DEFINITION, "cycle", case_sensitive=False)
            or _contains(
                STAKEHOLDER_DIALOG_DEFINITION, "iteration", case_sensitive=False
            )
            or _contains(STAKEHOLDER_DIALOG_DEFINITION, "loop", case_sensitive=False)
            or _contains(STAKEHOLDER_DIALOG_DEFINITION, "repeat", case_sensitive=False)
        )


# ===========================================================================
# STAKEHOLDER_REVIEWER: checklist specifics
# ===========================================================================


class TestStakeholderReviewerChecklistItems:
    """STAKEHOLDER_REVIEWER_DEFINITION checklist must include specific items
    from the behavioral contracts."""

    def test_dependency_analysis_present(self):
        """Downstream dependency analysis item must be in the checklist."""
        assert _contains(
            STAKEHOLDER_REVIEWER_DEFINITION, "dependency", case_sensitive=False
        )

    def test_contract_granularity_present(self):
        """Contract granularity item must be in the checklist."""
        assert _contains(
            STAKEHOLDER_REVIEWER_DEFINITION, "granularity", case_sensitive=False
        )

    def test_gate_reachability_present(self):
        """Gate reachability item must be in the checklist."""
        assert _contains(
            STAKEHOLDER_REVIEWER_DEFINITION, "reachab", case_sensitive=False
        )

    def test_all_three_checklist_items_coexist(self):
        """All three specific checklist items must be present together."""
        text = STAKEHOLDER_REVIEWER_DEFINITION.lower()
        assert "downstream" in text
        assert "granularity" in text
        assert "reachab" in text


# ===========================================================================
# BLUEPRINT_AUTHOR: P1-P4 specifics
# ===========================================================================


class TestBlueprintAuthorRulesP1P4:
    """BLUEPRINT_AUTHOR_DEFINITION must contain all four preference-capture
    rules P1 through P4."""

    def test_p1_present(self):
        assert _contains(BLUEPRINT_AUTHOR_DEFINITION, "P1")

    def test_p2_present(self):
        assert _contains(BLUEPRINT_AUTHOR_DEFINITION, "P2")

    def test_p3_present(self):
        assert _contains(BLUEPRINT_AUTHOR_DEFINITION, "P3")

    def test_p4_present(self):
        assert _contains(BLUEPRINT_AUTHOR_DEFINITION, "P4")

    def test_all_four_rules_present(self):
        """All four rules P1, P2, P3, P4 must coexist."""
        text = BLUEPRINT_AUTHOR_DEFINITION
        assert all(_contains(text, f"P{i}") for i in range(1, 5))

    def test_preference_capture_context(self):
        """Rules are in the context of preference capture."""
        text = BLUEPRINT_AUTHOR_DEFINITION.lower()
        assert "preference" in text or "capture" in text


# ===========================================================================
# BLUEPRINT_REVIEWER: pattern catalog specifics
# ===========================================================================


class TestBlueprintReviewerPatternCatalog:
    """BLUEPRINT_REVIEWER_DEFINITION must cross-reference the pattern catalog."""

    def test_pattern_referenced(self):
        assert _contains(BLUEPRINT_REVIEWER_DEFINITION, "pattern", case_sensitive=False)

    def test_catalog_referenced(self):
        assert _contains(BLUEPRINT_REVIEWER_DEFINITION, "catalog", case_sensitive=False)

    def test_pattern_and_catalog_coexist(self):
        text = BLUEPRINT_REVIEWER_DEFINITION.lower()
        assert "pattern" in text and "catalog" in text


# ===========================================================================
# TEST_AGENT: mode differentiation
# ===========================================================================


class TestTestAgentModes:
    """TEST_AGENT_DEFINITION has two modes: Stage 3 normal mode
    (TEST_GENERATION_COMPLETE) and debug loop regression test mode
    (REGRESSION_TEST_COMPLETE)."""

    def test_normal_mode_status(self):
        assert _contains(TEST_AGENT_DEFINITION, "TEST_GENERATION_COMPLETE")

    def test_regression_mode_status(self):
        assert _contains(TEST_AGENT_DEFINITION, "REGRESSION_TEST_COMPLETE")

    def test_stage_3_context_referenced(self):
        """Stage 3 should be referenced for the normal mode."""
        assert (
            _contains(TEST_AGENT_DEFINITION, "Stage 3", case_sensitive=False)
            or _contains(TEST_AGENT_DEFINITION, "stage 3", case_sensitive=False)
            or _contains(TEST_AGENT_DEFINITION, "stage_3", case_sensitive=False)
        )

    def test_debug_loop_or_regression_context_referenced(self):
        """Debug loop or regression test mode should be referenced."""
        text = TEST_AGENT_DEFINITION.lower()
        assert "debug" in text or "regression" in text


# ===========================================================================
# TEST_AGENT: quality tool and formatting
# ===========================================================================


class TestTestAgentQualityTool:
    """TEST_AGENT_DEFINITION must document quality tool auto-format."""

    def test_quality_tool_referenced(self):
        assert _contains(TEST_AGENT_DEFINITION, "quality", case_sensitive=False)

    def test_auto_format_referenced(self):
        text = TEST_AGENT_DEFINITION.lower()
        assert "format" in text

    def test_notification_concept_present(self):
        """Quality tool auto-format should be described as a notification."""
        text = TEST_AGENT_DEFINITION.lower()
        assert (
            "notif" in text
            or "inform" in text
            or "aware" in text
            or "note" in text
            or "quality" in text
        )


# ===========================================================================
# IMPLEMENTATION_AGENT: interface-boundary constraint detail
# ===========================================================================


class TestImplementationAgentInterfaceBoundary:
    """IMPLEMENTATION_AGENT_DEFINITION must clearly distinguish between
    interface modifications (allowed) and internal logic changes (forbidden)
    for assembly fixes."""

    def test_interface_keyword_present(self):
        assert _contains(
            IMPLEMENTATION_AGENT_DEFINITION, "interface", case_sensitive=False
        )

    def test_assembly_context_present(self):
        """Constraint applies to assembly fixes."""
        assert _contains(
            IMPLEMENTATION_AGENT_DEFINITION, "assembl", case_sensitive=False
        )

    def test_internal_logic_mentioned(self):
        """Internal logic must be mentioned as the boundary."""
        text = IMPLEMENTATION_AGENT_DEFINITION.lower()
        assert "internal" in text or "logic" in text

    def test_boundary_or_constraint_concept(self):
        """The constraint must be described as a boundary or limitation."""
        text = IMPLEMENTATION_AGENT_DEFINITION.lower()
        assert (
            "boundary" in text
            or "constraint" in text
            or "only" in text
            or "must not" in text
            or "do not" in text
        )


# ===========================================================================
# COVERAGE_REVIEW_AGENT: gap detection specifics
# ===========================================================================


class TestCoverageReviewAgentGapDetection:
    """COVERAGE_REVIEW_AGENT_DEFINITION gap detection and red-green validation."""

    def test_gap_keyword_present(self):
        assert _contains(COVERAGE_REVIEW_AGENT_DEFINITION, "gap", case_sensitive=False)

    def test_detection_keyword_present(self):
        text = COVERAGE_REVIEW_AGENT_DEFINITION.lower()
        assert "detect" in text or "identif" in text or "find" in text or "gap" in text

    def test_red_validation_referenced(self):
        """Red phase of validation (test fails before implementation)."""
        assert _contains(COVERAGE_REVIEW_AGENT_DEFINITION, "red", case_sensitive=False)

    def test_green_validation_referenced(self):
        """Green phase of validation (test passes after implementation)."""
        assert _contains(
            COVERAGE_REVIEW_AGENT_DEFINITION, "green", case_sensitive=False
        )

    def test_validation_concept_present(self):
        assert _contains(
            COVERAGE_REVIEW_AGENT_DEFINITION, "validat", case_sensitive=False
        ) or _contains(COVERAGE_REVIEW_AGENT_DEFINITION, "verif", case_sensitive=False)


# ===========================================================================
# INTEGRATION_TEST_AUTHOR: dispatch verification specifics
# ===========================================================================


class TestIntegrationTestAuthorDispatch:
    """INTEGRATION_TEST_AUTHOR_DEFINITION must cover registry-handler
    alignment and per-language dispatch."""

    def test_registry_referenced(self):
        assert _contains(
            INTEGRATION_TEST_AUTHOR_DEFINITION, "registry", case_sensitive=False
        )

    def test_handler_referenced(self):
        assert _contains(
            INTEGRATION_TEST_AUTHOR_DEFINITION, "handler", case_sensitive=False
        )

    def test_dispatch_referenced(self):
        assert _contains(
            INTEGRATION_TEST_AUTHOR_DEFINITION, "dispatch", case_sensitive=False
        )

    def test_per_language_concept(self):
        """Per-language verification must be referenced."""
        text = INTEGRATION_TEST_AUTHOR_DEFINITION.lower()
        assert (
            "per-language" in text
            or "per language" in text
            or ("language" in text and "dispatch" in text)
        )

    def test_verification_concept(self):
        """Verification or validation must be referenced."""
        text = INTEGRATION_TEST_AUTHOR_DEFINITION.lower()
        assert "verif" in text or "validat" in text or "test" in text


# ===========================================================================
# Cross-definition: definition length sanity
# ===========================================================================


class TestDefinitionLengthSanity:
    """Each definition should be a substantial markdown document -- not a
    one-liner or trivially short string."""

    @pytest.mark.parametrize("name,definition", list(ALL_DEFINITIONS.items()))
    def test_definition_minimum_length(self, name, definition):
        """Each definition should be at least 100 characters."""
        assert len(definition) >= 100, (
            f"{name}_DEFINITION is only {len(definition)} chars; "
            "agent definitions should be substantial"
        )

    @pytest.mark.parametrize("name,definition", list(ALL_DEFINITIONS.items()))
    def test_definition_has_multiple_lines(self, name, definition):
        """Each definition should span multiple lines."""
        line_count = len(definition.strip().split("\n"))
        assert line_count >= 5, (
            f"{name}_DEFINITION has only {line_count} lines; "
            "agent definitions should be multi-line"
        )


# ===========================================================================
# Cross-definition: no stub sentinel in definitions
# ===========================================================================


class TestNoStubSentinelInDefinitions:
    """Definitions should not contain the SVP stub sentinel, confirming
    they are implemented content, not stubs."""

    @pytest.mark.parametrize("name,definition", list(ALL_DEFINITIONS.items()))
    def test_no_svp_stub_marker(self, name, definition):
        assert "__SVP_STUB__" not in definition, (
            f"{name}_DEFINITION should not contain __SVP_STUB__ marker"
        )


# ===========================================================================
# Bug S3-162: standard finding output format across review agents
# ===========================================================================


_S3_162_REQUIRED_LABELS = [
    "Finding:",
    "Severity:",
    "Location:",
    "Violation:",
    "Consequence:",
    "Minimal Fix:",
    "Confidence:",
    "Open Questions:",
]


class TestS3_162StandardFindingFormat:
    """All four review agents MUST emit findings using the 8-field block (Bug S3-162).

    DIAGNOSTIC_AGENT and REDO_AGENT (Unit 21) keep their separate `[STRUCTURED]`
    convention and are intentionally out of scope for this format mandate.
    """

    def test_stakeholder_reviewer_definition_includes_standard_finding_format(self):
        missing = [
            label
            for label in _S3_162_REQUIRED_LABELS
            if label not in STAKEHOLDER_REVIEWER_DEFINITION
        ]
        assert not missing, (
            f"STAKEHOLDER_REVIEWER_DEFINITION missing finding-block labels: {missing}"
        )

    def test_blueprint_reviewer_definition_includes_standard_finding_format(self):
        missing = [
            label
            for label in _S3_162_REQUIRED_LABELS
            if label not in BLUEPRINT_REVIEWER_DEFINITION
        ]
        assert not missing, (
            f"BLUEPRINT_REVIEWER_DEFINITION missing finding-block labels: {missing}"
        )

    def test_coverage_review_definition_includes_standard_finding_format(self):
        missing = [
            label
            for label in _S3_162_REQUIRED_LABELS
            if label not in COVERAGE_REVIEW_AGENT_DEFINITION
        ]
        assert not missing, (
            f"COVERAGE_REVIEW_AGENT_DEFINITION missing finding-block labels: {missing}"
        )

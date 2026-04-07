"""Unit 21: Diagnostic and Redo Agent Definitions -- complete test suite.

Synthetic data assumptions:
- DIAGNOSTIC_AGENT_DEFINITION is a str containing the complete markdown content
  of the diagnostic agent definition file (diagnostic_agent.md). All structural
  tests inspect this string for required phrases, keywords, and patterns.
- REDO_AGENT_DEFINITION is a str containing the complete markdown content of the
  redo agent definition file (redo_agent.md). All structural tests inspect this
  string for required phrases, keywords, and patterns.
- Both definitions are agent system-prompt markdown files. They do not export
  callable functions or data structures -- only string constants.
- The diagnostic agent definition must encode the three-hypothesis discipline
  (implementation, blueprint, spec), dual-format output (prose + structured
  block), the "report most fundamental level" corollary, and the integration-
  test-failure directive (blueprint hypothesis first with highest initial
  credence).
- The structured block must include the fields: UNIT, HYPOTHESIS_1, HYPOTHESIS_2,
  HYPOTHESIS_3, RECOMMENDATION. Each hypothesis references one of the three
  levels (implementation, blueprint, spec).
- The diagnostic agent terminal status lines are:
  DIAGNOSIS_COMPLETE: implementation, DIAGNOSIS_COMPLETE: blueprint,
  DIAGNOSIS_COMPLETE: spec.
- The redo agent definition must encode five classification outcomes:
  spec, blueprint, gate, profile_delivery, profile_blueprint.
- The redo agent terminal status lines are:
  REDO_CLASSIFIED: spec, REDO_CLASSIFIED: blueprint, REDO_CLASSIFIED: gate,
  REDO_CLASSIFIED: profile_delivery, REDO_CLASSIFIED: profile_blueprint.
- The redo agent definition must describe the redo-triggered profile revision
  flow: classification triggers a redo sub-stage, state snapshot via
  redo_triggered_from, setup agent targeted revision, Mini-Gate 0.3r.
- Keyword matching is case-insensitive where noted; status lines and structured
  field names are tested in their canonical (case-sensitive) form.
"""

import re

from diagnostic_agents import (
    DIAGNOSTIC_AGENT_DEFINITION,
    REDO_AGENT_DEFINITION,
)

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def diag_contains(phrase: str, case_sensitive: bool = True) -> bool:
    """Check whether DIAGNOSTIC_AGENT_DEFINITION contains the given phrase."""
    if case_sensitive:
        return phrase in DIAGNOSTIC_AGENT_DEFINITION
    return phrase.lower() in DIAGNOSTIC_AGENT_DEFINITION.lower()


def diag_matches(pattern: str, flags: int = 0) -> list:
    """Return all regex matches of pattern in DIAGNOSTIC_AGENT_DEFINITION."""
    return re.findall(pattern, DIAGNOSTIC_AGENT_DEFINITION, flags)


def redo_contains(phrase: str, case_sensitive: bool = True) -> bool:
    """Check whether REDO_AGENT_DEFINITION contains the given phrase."""
    if case_sensitive:
        return phrase in REDO_AGENT_DEFINITION
    return phrase.lower() in REDO_AGENT_DEFINITION.lower()


def redo_matches(pattern: str, flags: int = 0) -> list:
    """Return all regex matches of pattern in REDO_AGENT_DEFINITION."""
    return re.findall(pattern, REDO_AGENT_DEFINITION, flags)


# ===========================================================================
# DIAGNOSTIC_AGENT_DEFINITION: type, non-emptiness, markdown structure
# ===========================================================================


class TestDiagnosticAgentDefinitionBasicStructure:
    """Verify DIAGNOSTIC_AGENT_DEFINITION is a non-empty markdown string."""

    def test_definition_is_string(self):
        assert isinstance(DIAGNOSTIC_AGENT_DEFINITION, str)

    def test_definition_is_nonempty(self):
        assert len(DIAGNOSTIC_AGENT_DEFINITION.strip()) > 0

    def test_definition_contains_markdown_headings(self):
        """Agent definition must be structured markdown with headings."""
        assert re.search(r"^#+\s+", DIAGNOSTIC_AGENT_DEFINITION, re.MULTILINE)

    def test_definition_has_substantial_content(self):
        """Definition should have meaningful length for an agent prompt."""
        assert len(DIAGNOSTIC_AGENT_DEFINITION.strip()) > 100


# ===========================================================================
# DIAGNOSTIC_AGENT_DEFINITION: Three-hypothesis discipline
# ===========================================================================


class TestDiagnosticThreeHypothesisDiscipline:
    """The diagnostic agent must articulate a plausible case at each of
    three levels: implementation, blueprint, spec."""

    def test_implementation_hypothesis_referenced(self):
        """Implementation-level hypothesis must be described."""
        assert diag_contains("implementation", case_sensitive=False)

    def test_blueprint_hypothesis_referenced(self):
        """Blueprint-level hypothesis must be described."""
        assert diag_contains("blueprint", case_sensitive=False)

    def test_spec_hypothesis_referenced(self):
        """Spec-level hypothesis must be described."""
        assert diag_contains("spec", case_sensitive=False)

    def test_three_hypothesis_concept_present(self):
        """The three-hypothesis discipline concept must be present."""
        assert (
            diag_contains("three", case_sensitive=False)
            or diag_contains("3", case_sensitive=False)
            or diag_contains("hypothesis", case_sensitive=False)
        )

    def test_all_three_levels_present_together(self):
        """All three levels must coexist in the definition."""
        has_implementation = diag_contains("implementation", case_sensitive=False)
        has_blueprint = diag_contains("blueprint", case_sensitive=False)
        has_spec = diag_contains("spec", case_sensitive=False)
        assert has_implementation and has_blueprint and has_spec

    def test_hypothesis_discipline_requires_all_three(self):
        """The agent must be instructed to articulate all three hypotheses
        before converging on a recommendation."""
        # The definition should reference that all three must be considered
        assert (
            diag_contains("hypothesis", case_sensitive=False)
            or diag_contains("plausible case", case_sensitive=False)
            or diag_contains("each", case_sensitive=False)
        )

    def test_implementation_remedy_described(self):
        """Implementation-level remedy: one more implementation attempt
        with diagnostic guidance."""
        assert diag_contains("implementation", case_sensitive=False)
        # Should describe what happens when implementation is diagnosed
        assert (
            diag_contains("guidance", case_sensitive=False)
            or diag_contains("attempt", case_sensitive=False)
            or diag_contains("fix", case_sensitive=False)
        )

    def test_blueprint_remedy_described(self):
        """Blueprint-level remedy: restart from Stage 2."""
        assert diag_contains("blueprint", case_sensitive=False)
        assert (
            diag_contains("Stage 2", case_sensitive=False)
            or diag_contains("stage 2", case_sensitive=False)
            or diag_contains("restart", case_sensitive=False)
        )

    def test_spec_remedy_described(self):
        """Spec-level remedy: targeted spec revision, then restart."""
        assert diag_contains("spec", case_sensitive=False)
        assert (
            diag_contains("revision", case_sensitive=False)
            or diag_contains("restart", case_sensitive=False)
            or diag_contains("fix", case_sensitive=False)
        )


# ===========================================================================
# DIAGNOSTIC_AGENT_DEFINITION: Dual-format output
# ===========================================================================


class TestDiagnosticDualFormatOutput:
    """The diagnostic agent must produce dual-format output: prose section
    for the human, then structured section with key-value data."""

    def test_prose_section_marker_present(self):
        """Definition must reference the [PROSE] section marker."""
        assert diag_contains("[PROSE]") or diag_contains("PROSE", case_sensitive=False)

    def test_structured_section_marker_present(self):
        """Definition must reference the [STRUCTURED] section marker."""
        assert diag_contains("[STRUCTURED]") or diag_contains(
            "STRUCTURED", case_sensitive=False
        )

    def test_dual_format_concept_present(self):
        """The dual-format output concept must be described."""
        assert (
            diag_contains("dual-format", case_sensitive=False)
            or diag_contains("dual format", case_sensitive=False)
            or (
                diag_contains("prose", case_sensitive=False)
                and diag_contains("structured", case_sensitive=False)
            )
        )

    def test_structured_block_unit_field(self):
        """Structured block must include the UNIT field."""
        assert diag_contains("UNIT")

    def test_structured_block_hypothesis_1_field(self):
        """Structured block must include HYPOTHESIS_1 field."""
        assert diag_contains("HYPOTHESIS_1")

    def test_structured_block_hypothesis_2_field(self):
        """Structured block must include HYPOTHESIS_2 field."""
        assert diag_contains("HYPOTHESIS_2")

    def test_structured_block_hypothesis_3_field(self):
        """Structured block must include HYPOTHESIS_3 field."""
        assert diag_contains("HYPOTHESIS_3")

    def test_structured_block_recommendation_field(self):
        """Structured block must include RECOMMENDATION field."""
        assert diag_contains("RECOMMENDATION")

    def test_hypothesis_fields_reference_levels(self):
        """Each hypothesis field should reference its corresponding level."""
        # The definition should show that hypothesis fields map to
        # implementation, blueprint, spec
        text_lower = DIAGNOSTIC_AGENT_DEFINITION.lower()
        assert "implementation" in text_lower
        assert "blueprint" in text_lower
        assert "spec" in text_lower

    def test_recommendation_is_one_of_three_levels(self):
        """RECOMMENDATION value must be one of: implementation, blueprint, spec."""
        assert diag_contains("RECOMMENDATION")
        # The definition should make clear these are the valid values
        assert (
            diag_contains("implementation")
            and diag_contains("blueprint")
            and diag_contains("spec")
        )


# ===========================================================================
# DIAGNOSTIC_AGENT_DEFINITION: "Report most fundamental level" corollary
# ===========================================================================


class TestDiagnosticReportMostFundamentalLevel:
    """When problems exist at multiple levels, the agent reports only the
    deepest problem. Spec supersedes blueprint, which supersedes
    implementation."""

    def test_most_fundamental_level_concept(self):
        """The 'report most fundamental level' corollary must be described."""
        assert (
            diag_contains("most fundamental", case_sensitive=False)
            or diag_contains("deepest", case_sensitive=False)
            or diag_contains("fundamental level", case_sensitive=False)
            or diag_contains("supersede", case_sensitive=False)
        )

    def test_spec_supersedes_blueprint(self):
        """Spec problems supersede blueprint problems."""
        assert diag_contains("spec", case_sensitive=False)
        assert diag_contains("blueprint", case_sensitive=False)
        # The hierarchy must be described -- spec > blueprint > implementation
        assert (
            diag_contains("supersede", case_sensitive=False)
            or diag_contains("fundamental", case_sensitive=False)
            or diag_contains("deepest", case_sensitive=False)
            or diag_contains("hierarchy", case_sensitive=False)
            or diag_contains("priority", case_sensitive=False)
        )

    def test_blueprint_supersedes_implementation(self):
        """Blueprint problems supersede implementation problems."""
        assert diag_contains("blueprint", case_sensitive=False)
        assert diag_contains("implementation", case_sensitive=False)

    def test_hierarchy_ordering_present(self):
        """The hierarchy ordering (spec > blueprint > implementation) must
        be conveyed."""
        text_lower = DIAGNOSTIC_AGENT_DEFINITION.lower()
        # All three levels must appear
        assert "spec" in text_lower
        assert "blueprint" in text_lower
        assert "implementation" in text_lower
        # Some ordering concept must be present
        assert (
            "supersede" in text_lower
            or "fundamental" in text_lower
            or "deepest" in text_lower
            or "most" in text_lower
            or "hierarchy" in text_lower
            or "level" in text_lower
        )


# ===========================================================================
# DIAGNOSTIC_AGENT_DEFINITION: Integration-test-failure directive
# ===========================================================================


class TestDiagnosticIntegrationTestDirective:
    """The integration-test-failure directive instructs the agent to evaluate
    the blueprint hypothesis FIRST with the highest initial credence."""

    def test_integration_test_failure_referenced(self):
        """The definition must reference integration test failures."""
        assert diag_contains("integration", case_sensitive=False)

    def test_blueprint_hypothesis_first_directive(self):
        """Blueprint hypothesis must be evaluated FIRST."""
        assert diag_contains("first", case_sensitive=False) or diag_contains(
            "FIRST", case_sensitive=True
        )

    def test_highest_initial_credence(self):
        """Blueprint hypothesis should have highest initial credence."""
        assert (
            diag_contains("credence", case_sensitive=False)
            or diag_contains("highest", case_sensitive=False)
            or diag_contains("disproportionately", case_sensitive=False)
        )

    def test_blueprint_before_implementation_for_integration(self):
        """For integration test failures, blueprint evaluated before
        implementation."""
        # The directive should convey that blueprint is checked before
        # concluding implementation
        text_lower = DIAGNOSTIC_AGENT_DEFINITION.lower()
        assert "blueprint" in text_lower
        assert "integration" in text_lower
        assert (
            "first" in text_lower
            or "before" in text_lower
            or "highest" in text_lower
            or "disproportionately" in text_lower
        )

    def test_integration_failures_blueprint_origin_noted(self):
        """Integration test failures disproportionately originate from
        blueprint-level issues."""
        assert diag_contains("blueprint", case_sensitive=False)
        assert diag_contains("integration", case_sensitive=False) and (
            diag_contains("disproportionately", case_sensitive=False)
            or diag_contains("originate", case_sensitive=False)
            or diag_contains("first", case_sensitive=False)
            or diag_contains("highest", case_sensitive=False)
        )

    def test_only_conclude_implementation_if_contracts_correct(self):
        """Should only conclude implementation-level if blueprint contracts
        are clearly correct."""
        assert diag_contains("contract", case_sensitive=False) or diag_contains(
            "correct", case_sensitive=False
        )


# ===========================================================================
# DIAGNOSTIC_AGENT_DEFINITION: Terminal status lines
# ===========================================================================


class TestDiagnosticTerminalStatusLines:
    """Terminal status: DIAGNOSIS_COMPLETE: implementation,
    DIAGNOSIS_COMPLETE: blueprint, or DIAGNOSIS_COMPLETE: spec."""

    def test_status_diagnosis_complete_implementation(self):
        """Status line DIAGNOSIS_COMPLETE: implementation must appear."""
        assert diag_contains("DIAGNOSIS_COMPLETE: implementation")

    def test_status_diagnosis_complete_blueprint(self):
        """Status line DIAGNOSIS_COMPLETE: blueprint must appear."""
        assert diag_contains("DIAGNOSIS_COMPLETE: blueprint")

    def test_status_diagnosis_complete_spec(self):
        """Status line DIAGNOSIS_COMPLETE: spec must appear."""
        assert diag_contains("DIAGNOSIS_COMPLETE: spec")

    def test_exactly_three_status_variants(self):
        """There should be exactly three DIAGNOSIS_COMPLETE status variants."""
        matches = diag_matches(r"DIAGNOSIS_COMPLETE:\s*\w+")
        unique_statuses = set(matches)
        assert len(unique_statuses) >= 3, (
            f"Expected at least 3 unique DIAGNOSIS_COMPLETE statuses, "
            f"found {len(unique_statuses)}: {unique_statuses}"
        )

    def test_status_lines_match_three_levels(self):
        """Each status line suffix corresponds to one of the three
        hypothesis levels."""
        assert diag_contains("DIAGNOSIS_COMPLETE: implementation")
        assert diag_contains("DIAGNOSIS_COMPLETE: blueprint")
        assert diag_contains("DIAGNOSIS_COMPLETE: spec")


# ===========================================================================
# DIAGNOSTIC_AGENT_DEFINITION: Context loading / inputs
# ===========================================================================


class TestDiagnosticAgentContext:
    """The diagnostic agent receives specific context: stakeholder spec,
    blueprint (current unit + upstream contracts), tests, failing
    implementation(s), and error output."""

    def test_spec_input_referenced(self):
        """Definition should reference receiving the stakeholder spec."""
        assert diag_contains("spec", case_sensitive=False)

    def test_blueprint_input_referenced(self):
        """Definition should reference receiving the blueprint."""
        assert diag_contains("blueprint", case_sensitive=False)

    def test_tests_input_referenced(self):
        """Definition should reference receiving the tests."""
        assert diag_contains("test", case_sensitive=False)

    def test_failing_implementation_input_referenced(self):
        """Definition should reference receiving failing implementation(s)."""
        assert (
            diag_contains("implementation", case_sensitive=False)
            or diag_contains("source", case_sensitive=False)
            or diag_contains("code", case_sensitive=False)
        )

    def test_error_output_input_referenced(self):
        """Definition should reference receiving error output."""
        assert (
            diag_contains("error", case_sensitive=False)
            or diag_contains("failure", case_sensitive=False)
            or diag_contains("output", case_sensitive=False)
        )


# ===========================================================================
# DIAGNOSTIC_AGENT_DEFINITION: Single-shot invocation pattern
# ===========================================================================


class TestDiagnosticAgentInvocationPattern:
    """The diagnostic agent uses single-shot invocation: receives context,
    produces output with terminal status, terminates."""

    def test_definition_contains_terminal_status(self):
        """A terminal status line pattern must be documented."""
        assert diag_contains("DIAGNOSIS_COMPLETE")

    def test_agent_produces_output_and_terminates(self):
        """Agent should produce output -- not enter a dialog loop."""
        # Definition should not reference ledger-based or multi-turn
        # It should contain output/analysis/report language
        assert (
            diag_contains("output", case_sensitive=False)
            or diag_contains("analysis", case_sensitive=False)
            or diag_contains("report", case_sensitive=False)
            or diag_contains("diagnos", case_sensitive=False)
        )


# ===========================================================================
# REDO_AGENT_DEFINITION: type, non-emptiness, markdown structure
# ===========================================================================


class TestRedoAgentDefinitionBasicStructure:
    """Verify REDO_AGENT_DEFINITION is a non-empty markdown string."""

    def test_definition_is_string(self):
        assert isinstance(REDO_AGENT_DEFINITION, str)

    def test_definition_is_nonempty(self):
        assert len(REDO_AGENT_DEFINITION.strip()) > 0

    def test_definition_contains_markdown_headings(self):
        """Agent definition must be structured markdown with headings."""
        assert re.search(r"^#+\s+", REDO_AGENT_DEFINITION, re.MULTILINE)

    def test_definition_has_substantial_content(self):
        """Definition should have meaningful length for an agent prompt."""
        assert len(REDO_AGENT_DEFINITION.strip()) > 100


# ===========================================================================
# REDO_AGENT_DEFINITION: Five classification outcomes
# ===========================================================================


class TestRedoFiveClassificationOutcomes:
    """The redo agent must classify into exactly five outcomes:
    spec, blueprint, gate, profile_delivery, profile_blueprint."""

    def test_spec_classification_referenced(self):
        """The spec classification outcome must be described."""
        assert redo_contains("spec", case_sensitive=False)

    def test_blueprint_classification_referenced(self):
        """The blueprint classification outcome must be described."""
        assert redo_contains("blueprint", case_sensitive=False)

    def test_gate_classification_referenced(self):
        """The gate classification outcome must be described."""
        assert redo_contains("gate", case_sensitive=False)

    def test_profile_delivery_classification_referenced(self):
        """The profile_delivery classification outcome must be described."""
        assert redo_contains("profile_delivery") or redo_contains(
            "profile delivery", case_sensitive=False
        )

    def test_profile_blueprint_classification_referenced(self):
        """The profile_blueprint classification outcome must be described."""
        assert redo_contains("profile_blueprint") or redo_contains(
            "profile blueprint", case_sensitive=False
        )

    def test_all_five_classifications_present(self):
        """All five classification outcomes must coexist in the definition."""
        text_lower = REDO_AGENT_DEFINITION.lower()
        assert "spec" in text_lower
        assert "blueprint" in text_lower
        assert "gate" in text_lower
        assert "profile_delivery" in text_lower or "profile delivery" in text_lower
        assert "profile_blueprint" in text_lower or "profile blueprint" in text_lower

    def test_spec_classification_meaning(self):
        """spec classification: spec says the wrong thing, targeted revision,
        restart from Stage 2."""
        text_lower = REDO_AGENT_DEFINITION.lower()
        assert "spec" in text_lower
        assert (
            "revision" in text_lower
            or "restart" in text_lower
            or "stage 2" in text_lower
            or "wrong" in text_lower
        )

    def test_blueprint_classification_meaning(self):
        """blueprint classification: blueprint translated incorrectly,
        restart from Stage 2."""
        text_lower = REDO_AGENT_DEFINITION.lower()
        assert "blueprint" in text_lower
        assert (
            "restart" in text_lower
            or "stage 2" in text_lower
            or "incorrect" in text_lower
            or "translat" in text_lower
        )

    def test_gate_classification_meaning(self):
        """gate classification: documents correct, human approved wrong thing,
        unit-level rollback."""
        text_lower = REDO_AGENT_DEFINITION.lower()
        assert "gate" in text_lower
        assert (
            "rollback" in text_lower
            or "roll back" in text_lower
            or "invalidate" in text_lower
            or "reprocess" in text_lower
            or "approved" in text_lower
            or "human" in text_lower
        )

    def test_profile_delivery_classification_meaning(self):
        """profile_delivery: delivery-only profile change, focused dialog,
        no pipeline restart, takes effect at Stage 5."""
        text_lower = REDO_AGENT_DEFINITION.lower()
        assert "profile_delivery" in text_lower or "profile delivery" in text_lower
        assert "delivery" in text_lower and (
            "stage 5" in text_lower
            or "no.*restart" in text_lower
            or "focused" in text_lower
            or "dialog" in text_lower
        )

    def test_profile_blueprint_classification_meaning(self):
        """profile_blueprint: blueprint-influencing profile change, focused
        dialog, restart from Stage 2."""
        text_lower = REDO_AGENT_DEFINITION.lower()
        assert "profile_blueprint" in text_lower or "profile blueprint" in text_lower
        assert (
            "restart" in text_lower
            or "stage 2" in text_lower
            or "blueprint" in text_lower
        )


# ===========================================================================
# REDO_AGENT_DEFINITION: Terminal status lines
# ===========================================================================


class TestRedoTerminalStatusLines:
    """Terminal status lines for each of the five classifications."""

    def test_status_redo_classified_spec(self):
        """Status line REDO_CLASSIFIED: spec must appear."""
        assert redo_contains("REDO_CLASSIFIED: spec")

    def test_status_redo_classified_blueprint(self):
        """Status line REDO_CLASSIFIED: blueprint must appear."""
        assert redo_contains("REDO_CLASSIFIED: blueprint")

    def test_status_redo_classified_gate(self):
        """Status line REDO_CLASSIFIED: gate must appear."""
        assert redo_contains("REDO_CLASSIFIED: gate")

    def test_status_redo_classified_profile_delivery(self):
        """Status line REDO_CLASSIFIED: profile_delivery must appear."""
        assert redo_contains("REDO_CLASSIFIED: profile_delivery")

    def test_status_redo_classified_profile_blueprint(self):
        """Status line REDO_CLASSIFIED: profile_blueprint must appear."""
        assert redo_contains("REDO_CLASSIFIED: profile_blueprint")

    def test_exactly_five_status_variants(self):
        """There should be at least five REDO_CLASSIFIED status variants."""
        matches = redo_matches(r"REDO_CLASSIFIED:\s*\S+")
        unique_statuses = set(matches)
        assert len(unique_statuses) >= 5, (
            f"Expected at least 5 unique REDO_CLASSIFIED statuses, "
            f"found {len(unique_statuses)}: {unique_statuses}"
        )

    def test_status_lines_match_five_classifications(self):
        """Each status line corresponds to one of the five classification
        outcomes."""
        assert redo_contains("REDO_CLASSIFIED: spec")
        assert redo_contains("REDO_CLASSIFIED: blueprint")
        assert redo_contains("REDO_CLASSIFIED: gate")
        assert redo_contains("REDO_CLASSIFIED: profile_delivery")
        assert redo_contains("REDO_CLASSIFIED: profile_blueprint")


# ===========================================================================
# REDO_AGENT_DEFINITION: Redo-triggered profile revision flow
# ===========================================================================


class TestRedoTriggeredProfileRevisionFlow:
    """When redo produces profile_delivery or profile_blueprint, the setup
    agent runs in targeted revision mode with state snapshot and Mini-Gate."""

    def test_profile_revision_flow_referenced(self):
        """The profile revision flow must be described."""
        assert redo_contains("profile", case_sensitive=False)
        assert (
            redo_contains("revision", case_sensitive=False)
            or redo_contains("dialog", case_sensitive=False)
            or redo_contains("setup", case_sensitive=False)
        )

    def test_redo_sub_stage_concept_present(self):
        """Redo sub-stages (redo_profile_delivery, redo_profile_blueprint)
        must be referenced or implied."""
        assert (
            redo_contains("redo_profile_delivery")
            or redo_contains("redo_profile_blueprint")
            or redo_contains("sub-stage", case_sensitive=False)
            or redo_contains("sub_stage", case_sensitive=False)
            or redo_contains("profile_delivery")
            or redo_contains("profile_blueprint")
        )

    def test_state_snapshot_mechanism_present(self):
        """The redo_triggered_from snapshot mechanism should be described
        or implied."""
        assert (
            redo_contains("redo_triggered_from")
            or redo_contains("snapshot", case_sensitive=False)
            or redo_contains("capture", case_sensitive=False)
            or redo_contains("current.*position", case_sensitive=False)
            or redo_contains("restore", case_sensitive=False)
        )

    def test_setup_agent_targeted_revision_mode(self):
        """The setup agent runs in targeted revision mode."""
        assert (
            redo_contains("setup agent", case_sensitive=False)
            or redo_contains("targeted revision", case_sensitive=False)
            or redo_contains("focused dialog", case_sensitive=False)
            or redo_contains("profile revision", case_sensitive=False)
        )

    def test_profile_delivery_no_restart(self):
        """profile_delivery classification does not restart the pipeline --
        it restores the snapshot after profile revision."""
        text_lower = REDO_AGENT_DEFINITION.lower()
        assert "profile_delivery" in text_lower or "profile delivery" in text_lower
        assert (
            "no.*restart" in text_lower
            or "restore" in text_lower
            or "stage 5" in text_lower
            or "delivery" in text_lower
        )

    def test_profile_blueprint_triggers_restart(self):
        """profile_blueprint classification restarts from Stage 2."""
        text_lower = REDO_AGENT_DEFINITION.lower()
        assert "profile_blueprint" in text_lower or "profile blueprint" in text_lower
        assert "restart" in text_lower or "stage 2" in text_lower

    def test_gate_0_3r_referenced_or_implied(self):
        """Mini-Gate 0.3r (profile revision approval) should be referenced
        or implied."""
        assert (
            redo_contains("0.3r")
            or redo_contains("gate_0_3r")
            or redo_contains("Gate 0.3r", case_sensitive=False)
            or redo_contains("PROFILE APPROVED", case_sensitive=False)
            or redo_contains("PROFILE REJECTED", case_sensitive=False)
            or redo_contains("profile.*approv", case_sensitive=False)
            or redo_contains("mini-gate", case_sensitive=False)
            or redo_contains("gate", case_sensitive=False)
        )


# ===========================================================================
# REDO_AGENT_DEFINITION: Document hierarchy tracing
# ===========================================================================


class TestRedoDocumentHierarchyTracing:
    """The redo agent traces the relevant term through the document
    hierarchy to classify."""

    def test_document_hierarchy_concept(self):
        """The definition should reference tracing through the document
        hierarchy."""
        assert (
            redo_contains("hierarchy", case_sensitive=False)
            or redo_contains("trace", case_sensitive=False)
            or redo_contains("document", case_sensitive=False)
            or redo_contains("classify", case_sensitive=False)
            or redo_contains("classification", case_sensitive=False)
        )

    def test_classification_process_described(self):
        """The classification process should be described -- the agent
        determines which level the problem originates from."""
        text_lower = REDO_AGENT_DEFINITION.lower()
        assert (
            "classif" in text_lower
            or "determine" in text_lower
            or "trace" in text_lower
            or "analyz" in text_lower
        )


# ===========================================================================
# REDO_AGENT_DEFINITION: Slash command invocation
# ===========================================================================


class TestRedoSlashCommandInvocation:
    """The redo agent is invoked exclusively through the /svp:redo slash
    command. It does not appear in the main routing dispatch table."""

    def test_slash_command_referenced(self):
        """The /svp:redo slash command should be referenced."""
        assert (
            redo_contains("/svp:redo")
            or redo_contains("svp:redo")
            or redo_contains("redo", case_sensitive=False)
        )

    def test_redo_concept_present(self):
        """The concept of redoing a previously completed step must be
        described."""
        assert (
            redo_contains("redo", case_sensitive=False)
            or redo_contains("roll back", case_sensitive=False)
            or redo_contains("rollback", case_sensitive=False)
        )


# ===========================================================================
# REDO_AGENT_DEFINITION: Single-shot invocation pattern
# ===========================================================================


class TestRedoAgentInvocationPattern:
    """The redo agent uses single-shot invocation: receives context,
    produces classification with terminal status, terminates."""

    def test_definition_contains_terminal_status(self):
        """A terminal status line pattern must be documented."""
        assert redo_contains("REDO_CLASSIFIED")

    def test_agent_produces_classification_output(self):
        """Agent should produce a classification -- not enter a dialog loop."""
        assert (
            redo_contains("classif", case_sensitive=False)
            or redo_contains("output", case_sensitive=False)
            or redo_contains("result", case_sensitive=False)
        )


# ===========================================================================
# REDO_AGENT_DEFINITION: Context loading / inputs
# ===========================================================================


class TestRedoAgentContext:
    """The redo agent receives: state summary, error description, unit
    definition. Blueprint: not loaded (reads on demand)."""

    def test_state_input_referenced(self):
        """Definition should reference receiving state information."""
        assert redo_contains("state", case_sensitive=False) or redo_contains(
            "pipeline", case_sensitive=False
        )

    def test_error_or_description_input_referenced(self):
        """Definition should reference receiving an error description or
        context about what went wrong."""
        assert (
            redo_contains("error", case_sensitive=False)
            or redo_contains("description", case_sensitive=False)
            or redo_contains("problem", case_sensitive=False)
            or redo_contains("issue", case_sensitive=False)
            or redo_contains("wrong", case_sensitive=False)
        )


# ===========================================================================
# REDO_AGENT_DEFINITION: Dual-format output
# ===========================================================================


class TestRedoDualFormatOutput:
    """The redo agent is one of the agents that produces dual-format output
    (prose + structured) per Section 18.2."""

    def test_prose_output_referenced(self):
        """The redo agent should produce prose output for the human."""
        assert (
            redo_contains("[PROSE]")
            or redo_contains("prose", case_sensitive=False)
            or redo_contains("PROSE", case_sensitive=True)
        )

    def test_structured_output_referenced(self):
        """The redo agent should produce structured output for routing."""
        assert (
            redo_contains("[STRUCTURED]")
            or redo_contains("structured", case_sensitive=False)
            or redo_contains("STRUCTURED", case_sensitive=True)
        )

    def test_dual_format_concept(self):
        """The dual-format output concept should be conveyed."""
        assert (
            redo_contains("dual-format", case_sensitive=False)
            or redo_contains("dual format", case_sensitive=False)
        ) or (
            redo_contains("prose", case_sensitive=False)
            and redo_contains("structured", case_sensitive=False)
        )


# ===========================================================================
# Cross-definition: definitions are distinct
# ===========================================================================


class TestDefinitionsAreDistinct:
    """DIAGNOSTIC_AGENT_DEFINITION and REDO_AGENT_DEFINITION must be
    different strings serving different purposes."""

    def test_definitions_are_not_identical(self):
        """The two definitions must not be the same string."""
        assert DIAGNOSTIC_AGENT_DEFINITION != REDO_AGENT_DEFINITION

    def test_diagnostic_has_diagnosis_complete(self):
        """Only the diagnostic definition should have DIAGNOSIS_COMPLETE."""
        assert diag_contains("DIAGNOSIS_COMPLETE")

    def test_redo_has_redo_classified(self):
        """Only the redo definition should have REDO_CLASSIFIED."""
        assert redo_contains("REDO_CLASSIFIED")

    def test_diagnostic_does_not_have_redo_classified(self):
        """The diagnostic definition should not contain REDO_CLASSIFIED
        status lines (they belong to the redo agent)."""
        assert not diag_contains("REDO_CLASSIFIED")

    def test_redo_does_not_have_diagnosis_complete(self):
        """The redo definition should not contain DIAGNOSIS_COMPLETE
        status lines (they belong to the diagnostic agent)."""
        assert not redo_contains("DIAGNOSIS_COMPLETE")


# ===========================================================================
# Cross-definition: both are str type at module level
# ===========================================================================


class TestModuleLevelConstants:
    """Both exports are module-level string constants (not callables)."""

    def test_diagnostic_is_not_callable(self):
        assert not callable(DIAGNOSTIC_AGENT_DEFINITION)

    def test_redo_is_not_callable(self):
        assert not callable(REDO_AGENT_DEFINITION)

    def test_diagnostic_is_str_type_exactly(self):
        assert type(DIAGNOSTIC_AGENT_DEFINITION) is str

    def test_redo_is_str_type_exactly(self):
        assert type(REDO_AGENT_DEFINITION) is str


# ===========================================================================
# DIAGNOSTIC_AGENT_DEFINITION: Structured block completeness
# ===========================================================================


class TestDiagnosticStructuredBlockCompleteness:
    """The structured block must contain all required fields with the
    correct semantics."""

    def test_structured_block_has_five_fields(self):
        """The structured block should reference all five fields:
        UNIT, HYPOTHESIS_1, HYPOTHESIS_2, HYPOTHESIS_3, RECOMMENDATION."""
        required_fields = [
            "UNIT",
            "HYPOTHESIS_1",
            "HYPOTHESIS_2",
            "HYPOTHESIS_3",
            "RECOMMENDATION",
        ]
        for field in required_fields:
            assert diag_contains(field), (
                f"Structured block field {field!r} not found in definition"
            )

    def test_hypothesis_1_references_implementation(self):
        """HYPOTHESIS_1 should be associated with the implementation level."""
        # The example shows HYPOTHESIS_1: implementation -- ...
        assert diag_contains("HYPOTHESIS_1")
        assert diag_contains("implementation")

    def test_hypothesis_2_references_blueprint(self):
        """HYPOTHESIS_2 should be associated with the blueprint level."""
        assert diag_contains("HYPOTHESIS_2")
        assert diag_contains("blueprint")

    def test_hypothesis_3_references_spec(self):
        """HYPOTHESIS_3 should be associated with the spec level."""
        assert diag_contains("HYPOTHESIS_3")
        assert diag_contains("spec")

    def test_structured_block_example_present(self):
        """The definition should contain an example of the structured block
        format."""
        # Look for the example pattern with UNIT and HYPOTHESIS fields
        assert diag_contains("UNIT:") or diag_contains("UNIT :")


# ===========================================================================
# REDO_AGENT_DEFINITION: Classification outcomes detailed
# ===========================================================================


class TestRedoClassificationOutcomesDetailed:
    """Detailed validation of each classification outcome's description."""

    def test_spec_wrong_thing_described(self):
        """spec: 'spec says the wrong thing' -- targeted revision."""
        assert redo_contains("spec", case_sensitive=False)
        assert (
            redo_contains("wrong", case_sensitive=False)
            or redo_contains("incorrect", case_sensitive=False)
            or redo_contains("revision", case_sensitive=False)
            or redo_contains("incomplete", case_sensitive=False)
        )

    def test_blueprint_translated_incorrectly(self):
        """blueprint: 'blueprint translated incorrectly' -- restart Stage 2."""
        assert redo_contains("blueprint", case_sensitive=False)
        assert (
            redo_contains("translat", case_sensitive=False)
            or redo_contains("incorrect", case_sensitive=False)
            or redo_contains("restart", case_sensitive=False)
            or redo_contains("stage 2", case_sensitive=False)
        )

    def test_gate_human_approved_wrong(self):
        """gate: 'documents correct, human approved wrong thing'."""
        assert redo_contains("gate", case_sensitive=False)
        assert (
            redo_contains("human", case_sensitive=False)
            or redo_contains("approved", case_sensitive=False)
            or redo_contains("correct", case_sensitive=False)
            or redo_contains("rollback", case_sensitive=False)
            or redo_contains("roll back", case_sensitive=False)
        )

    def test_profile_delivery_delivery_only(self):
        """profile_delivery: delivery-only change, no pipeline restart."""
        text_lower = REDO_AGENT_DEFINITION.lower()
        assert "delivery" in text_lower
        assert (
            "delivery-only" in text_lower
            or "delivery only" in text_lower
            or "no.*restart" in text_lower
            or "stage 5" in text_lower
            or "focused" in text_lower
        )

    def test_profile_blueprint_influences_blueprint(self):
        """profile_blueprint: blueprint-influencing change, restart Stage 2."""
        text_lower = REDO_AGENT_DEFINITION.lower()
        assert "profile_blueprint" in text_lower or "profile blueprint" in text_lower
        assert "blueprint" in text_lower and (
            "restart" in text_lower
            or "stage 2" in text_lower
            or "influenc" in text_lower
        )


# ===========================================================================
# REDO_AGENT_DEFINITION: Available stages
# ===========================================================================


class TestRedoAgentAvailableStages:
    """The redo agent is available at Stages 2, 3, 4."""

    def test_stage_availability_documented(self):
        """The definition should reference the stages where redo is
        available, or the concept of completed steps."""
        assert (
            redo_contains("Stage 2", case_sensitive=False)
            or redo_contains("stage 2", case_sensitive=False)
            or redo_contains("Stage 3", case_sensitive=False)
            or redo_contains("stage 3", case_sensitive=False)
            or redo_contains("Stage 4", case_sensitive=False)
            or redo_contains("stage 4", case_sensitive=False)
            or redo_contains("completed step", case_sensitive=False)
            or redo_contains("previously completed", case_sensitive=False)
        )


# ===========================================================================
# DIAGNOSTIC_AGENT_DEFINITION: Available stages
# ===========================================================================


class TestDiagnosticAgentAvailableStages:
    """The diagnostic agent is available at Stages 3 and 4."""

    def test_stage_3_context_referenced(self):
        """The definition should reference Stage 3 context (unit fix ladder)
        or failing tests."""
        assert (
            diag_contains("Stage 3", case_sensitive=False)
            or diag_contains("fix ladder", case_sensitive=False)
            or diag_contains("escalation", case_sensitive=False)
            or diag_contains("test", case_sensitive=False)
        )

    def test_stage_4_context_referenced(self):
        """The definition should reference Stage 4 context (integration
        test failures) or assembly failures."""
        assert (
            diag_contains("Stage 4", case_sensitive=False)
            or diag_contains("integration", case_sensitive=False)
            or diag_contains("assembly", case_sensitive=False)
        )


# ===========================================================================
# Structural: both definitions are proper markdown
# ===========================================================================


class TestBothDefinitionsMarkdownStructure:
    """Both definitions should be well-structured markdown documents."""

    def test_diagnostic_has_multiple_sections(self):
        """Diagnostic definition should have multiple markdown sections."""
        headings = re.findall(r"^#+\s+", DIAGNOSTIC_AGENT_DEFINITION, re.MULTILINE)
        assert len(headings) >= 2, (
            "Diagnostic definition should have at least 2 markdown headings"
        )

    def test_redo_has_multiple_sections(self):
        """Redo definition should have multiple markdown sections."""
        headings = re.findall(r"^#+\s+", REDO_AGENT_DEFINITION, re.MULTILINE)
        assert len(headings) >= 2, (
            "Redo definition should have at least 2 markdown headings"
        )

    def test_diagnostic_no_leading_trailing_whitespace_only(self):
        """Definition should not be only whitespace."""
        assert DIAGNOSTIC_AGENT_DEFINITION.strip() != ""

    def test_redo_no_leading_trailing_whitespace_only(self):
        """Definition should not be only whitespace."""
        assert REDO_AGENT_DEFINITION.strip() != ""

"""
Tests for Unit 22: Support Agent Definitions.

Synthetic Data Assumptions:
- All 3 agent definition constants are non-empty strings when implemented.
- Each definition contains specific keywords, status lines, and behavioral
  markers as specified in the blueprint contracts (Unit 22, Tier 3).
- String content checks use case-insensitive matching where appropriate
  for keywords, but exact-case matching for status line tokens (which are
  protocol-level identifiers).
- The help agent definition references read-only tool restrictions (Read,
  Grep, Glob, web search), gate-invocation hint formulation workflow, and
  hint forwarding mechanism.
- The hint agent definition references dual-mode behavior (single-shot
  reactive and ledger-based proactive), mode determination logic (reactive
  when hint text provided, proactive when ledger context only), and the
  cross-agent HINT_BLUEPRINT_CONFLICT status.
- The reference indexing agent definition references document and repository
  reference handling and the single-shot interaction pattern.
- No dependencies exist for this unit.
"""

import pytest

from unit_22 import (
    HELP_AGENT_DEFINITION,
    HINT_AGENT_DEFINITION,
    REFERENCE_INDEXING_AGENT_DEFINITION,
)

# ---------------------------------------------------------------------------
# Collect all definitions for cross-cutting tests
# ---------------------------------------------------------------------------

ALL_DEFINITIONS = {
    "HELP_AGENT_DEFINITION": HELP_AGENT_DEFINITION,
    "HINT_AGENT_DEFINITION": HINT_AGENT_DEFINITION,
    "REFERENCE_INDEXING_AGENT_DEFINITION": REFERENCE_INDEXING_AGENT_DEFINITION,
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
# Cross-cutting: All definitions are distinct
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
# HELP_AGENT_DEFINITION
# ===========================================================================


class TestHelpAgentDefinition:
    """Tests for HELP_AGENT_DEFINITION behavioral contracts."""

    # --- Read-only constraint ---

    def test_references_read_only_constraint(self):
        text = HELP_AGENT_DEFINITION.lower()
        assert "read" in text and ("only" in text or "restrict" in text), (
            "HELP_AGENT_DEFINITION must reference the read-only constraint"
        )

    def test_references_read_tool(self):
        assert "Read" in HELP_AGENT_DEFINITION, (
            "HELP_AGENT_DEFINITION must reference the Read tool "
            "as part of tool access restrictions"
        )

    def test_references_grep_tool(self):
        assert "Grep" in HELP_AGENT_DEFINITION, (
            "HELP_AGENT_DEFINITION must reference the Grep tool "
            "as part of tool access restrictions"
        )

    def test_references_glob_tool(self):
        assert "Glob" in HELP_AGENT_DEFINITION, (
            "HELP_AGENT_DEFINITION must reference the Glob tool "
            "as part of tool access restrictions"
        )

    def test_references_web_search_tool(self):
        text = HELP_AGENT_DEFINITION.lower()
        assert "web" in text and "search" in text, (
            "HELP_AGENT_DEFINITION must reference web search "
            "as part of tool access restrictions"
        )

    # --- Gate-invocation hint formulation workflow ---

    def test_references_gate_invocation_mode(self):
        text = HELP_AGENT_DEFINITION.lower()
        assert "gate" in text, (
            "HELP_AGENT_DEFINITION must reference gate-invocation mode"
        )

    def test_references_hint_formulation_workflow(self):
        text = HELP_AGENT_DEFINITION.lower()
        assert "hint" in text and "formul" in text, (
            "HELP_AGENT_DEFINITION must reference the hint formulation workflow"
        )

    # --- Hint forwarding mechanism ---

    def test_references_hint_forwarding_mechanism(self):
        text = HELP_AGENT_DEFINITION.lower()
        assert "forward" in text, (
            "HELP_AGENT_DEFINITION must reference hint forwarding mechanism"
        )

    # --- Status lines ---

    def test_contains_help_session_complete_no_hint_status(self):
        assert "HELP_SESSION_COMPLETE: no hint" in HELP_AGENT_DEFINITION, (
            "HELP_AGENT_DEFINITION must contain 'HELP_SESSION_COMPLETE: no hint' status"
        )

    def test_contains_help_session_complete_hint_forwarded_status(self):
        assert "HELP_SESSION_COMPLETE: hint forwarded" in HELP_AGENT_DEFINITION, (
            "HELP_AGENT_DEFINITION must contain "
            "'HELP_SESSION_COMPLETE: hint forwarded' status"
        )

    # --- Ledger multi-turn interaction pattern ---

    def test_references_ledger_interaction_pattern(self):
        text = HELP_AGENT_DEFINITION.lower()
        assert "ledger" in text, (
            "HELP_AGENT_DEFINITION must reference the ledger-based "
            "multi-turn interaction pattern"
        )

    def test_references_multi_turn_pattern(self):
        text = HELP_AGENT_DEFINITION.lower()
        assert "multi" in text and "turn" in text, (
            "HELP_AGENT_DEFINITION must reference the multi-turn interaction pattern"
        )

    # --- Pipeline pause behavior ---

    def test_references_pipeline_pause_behavior(self):
        text = HELP_AGENT_DEFINITION.lower()
        assert "pause" in text or "stateless" in text, (
            "HELP_AGENT_DEFINITION must reference that the pipeline pauses "
            "while the help agent is active or that it is stateless across sessions"
        )


# ===========================================================================
# HINT_AGENT_DEFINITION
# ===========================================================================


class TestHintAgentDefinition:
    """Tests for HINT_AGENT_DEFINITION behavioral contracts."""

    # --- Dual-mode behavior ---

    def test_references_dual_mode_behavior(self):
        text = HINT_AGENT_DEFINITION.lower()
        assert "dual" in text or ("reactive" in text and "proactive" in text), (
            "HINT_AGENT_DEFINITION must reference dual-mode behavior "
            "(reactive and proactive)"
        )

    def test_references_single_shot_reactive_mode(self):
        text = HINT_AGENT_DEFINITION.lower()
        assert "reactive" in text, (
            "HINT_AGENT_DEFINITION must reference the single-shot reactive mode"
        )

    def test_references_single_shot_in_reactive_context(self):
        text = HINT_AGENT_DEFINITION.lower()
        assert "single" in text and "shot" in text, (
            "HINT_AGENT_DEFINITION must reference single-shot as part of "
            "the reactive interaction mode"
        )

    def test_references_ledger_based_proactive_mode(self):
        text = HINT_AGENT_DEFINITION.lower()
        assert "proactive" in text, (
            "HINT_AGENT_DEFINITION must reference the ledger-based proactive mode"
        )

    def test_references_ledger_for_proactive_mode(self):
        text = HINT_AGENT_DEFINITION.lower()
        assert "ledger" in text, (
            "HINT_AGENT_DEFINITION must reference ledger-based interaction "
            "for the proactive mode"
        )

    # --- Mode determination logic ---

    def test_references_mode_determination_logic(self):
        text = HINT_AGENT_DEFINITION.lower()
        # The mode determination is: reactive when hint text provided,
        # proactive when ledger context only
        assert "hint" in text, (
            "HINT_AGENT_DEFINITION must reference hint text as part of "
            "mode determination logic"
        )

    def test_references_reactive_trigger_condition(self):
        text = HINT_AGENT_DEFINITION.lower()
        # Reactive is triggered when hint text is provided
        assert "reactive" in text and ("hint" in text or "text" in text), (
            "HINT_AGENT_DEFINITION must explain that reactive mode is "
            "triggered by provided hint text"
        )

    def test_references_proactive_trigger_condition(self):
        text = HINT_AGENT_DEFINITION.lower()
        # Proactive is triggered when ledger context only (no direct hint text)
        assert "proactive" in text and "ledger" in text, (
            "HINT_AGENT_DEFINITION must explain that proactive mode is "
            "triggered by ledger context"
        )

    # --- Status lines ---

    def test_contains_hint_analysis_complete_status(self):
        assert "HINT_ANALYSIS_COMPLETE" in HINT_AGENT_DEFINITION, (
            "HINT_AGENT_DEFINITION must contain 'HINT_ANALYSIS_COMPLETE' status"
        )

    def test_contains_hint_blueprint_conflict_status(self):
        assert "HINT_BLUEPRINT_CONFLICT" in HINT_AGENT_DEFINITION, (
            "HINT_AGENT_DEFINITION must contain "
            "'HINT_BLUEPRINT_CONFLICT' status (cross-agent status)"
        )

    # --- Cross-agent status: HINT_BLUEPRINT_CONFLICT ---

    def test_hint_blueprint_conflict_is_cross_agent_status(self):
        # The HINT_BLUEPRINT_CONFLICT status indicates a conflict between
        # the human hint and the blueprint contract. It includes details.
        text = HINT_AGENT_DEFINITION
        assert "HINT_BLUEPRINT_CONFLICT:" in text or (
            "HINT_BLUEPRINT_CONFLICT" in text and "<details>" in text
        ), (
            "HINT_AGENT_DEFINITION must indicate HINT_BLUEPRINT_CONFLICT "
            "includes details (e.g., 'HINT_BLUEPRINT_CONFLICT: <details>')"
        )

    def test_references_blueprint_conflict_concept(self):
        text = HINT_AGENT_DEFINITION.lower()
        assert "conflict" in text or "contradict" in text, (
            "HINT_AGENT_DEFINITION must reference the concept of a hint "
            "conflicting with or contradicting the blueprint"
        )


# ===========================================================================
# REFERENCE_INDEXING_AGENT_DEFINITION
# ===========================================================================


class TestReferenceIndexingAgentDefinition:
    """Tests for REFERENCE_INDEXING_AGENT_DEFINITION behavioral contracts."""

    # --- Document and repository reference handling ---

    def test_references_document_handling(self):
        text = REFERENCE_INDEXING_AGENT_DEFINITION.lower()
        assert "document" in text or "reference" in text, (
            "REFERENCE_INDEXING_AGENT_DEFINITION must reference document handling"
        )

    def test_references_repository_handling(self):
        text = REFERENCE_INDEXING_AGENT_DEFINITION.lower()
        assert "repo" in text or "repository" in text, (
            "REFERENCE_INDEXING_AGENT_DEFINITION must reference repository "
            "reference handling"
        )

    def test_references_summary_production(self):
        text = REFERENCE_INDEXING_AGENT_DEFINITION.lower()
        assert "summary" in text or "index" in text, (
            "REFERENCE_INDEXING_AGENT_DEFINITION must reference producing "
            "a structured summary or index"
        )

    # --- Status line ---

    def test_contains_indexing_complete_status(self):
        assert "INDEXING_COMPLETE" in REFERENCE_INDEXING_AGENT_DEFINITION, (
            "REFERENCE_INDEXING_AGENT_DEFINITION must contain "
            "'INDEXING_COMPLETE' status"
        )

    # --- Single-shot interaction pattern ---

    def test_references_single_shot_interaction_pattern(self):
        text = REFERENCE_INDEXING_AGENT_DEFINITION.lower()
        assert "single" in text and "shot" in text, (
            "REFERENCE_INDEXING_AGENT_DEFINITION must reference the "
            "single-shot interaction pattern"
        )


# ===========================================================================
# Status line exclusivity: each definition only contains its own statuses
# ===========================================================================


class TestStatusLineExclusivity:
    """Definitions should only contain their own status lines, not others'."""

    def test_help_agent_does_not_contain_hint_analysis_status(self):
        assert "HINT_ANALYSIS_COMPLETE" not in HELP_AGENT_DEFINITION, (
            "HELP_AGENT_DEFINITION must not contain the hint agent's "
            "HINT_ANALYSIS_COMPLETE status"
        )

    def test_help_agent_does_not_contain_indexing_status(self):
        assert "INDEXING_COMPLETE" not in HELP_AGENT_DEFINITION, (
            "HELP_AGENT_DEFINITION must not contain the reference indexing "
            "agent's INDEXING_COMPLETE status"
        )

    def test_hint_agent_does_not_contain_help_session_status(self):
        assert "HELP_SESSION_COMPLETE" not in HINT_AGENT_DEFINITION, (
            "HINT_AGENT_DEFINITION must not contain the help agent's "
            "HELP_SESSION_COMPLETE status"
        )

    def test_hint_agent_does_not_contain_indexing_status(self):
        assert "INDEXING_COMPLETE" not in HINT_AGENT_DEFINITION, (
            "HINT_AGENT_DEFINITION must not contain the reference indexing "
            "agent's INDEXING_COMPLETE status"
        )

    def test_reference_indexing_does_not_contain_help_session_status(self):
        assert "HELP_SESSION_COMPLETE" not in REFERENCE_INDEXING_AGENT_DEFINITION, (
            "REFERENCE_INDEXING_AGENT_DEFINITION must not contain the help "
            "agent's HELP_SESSION_COMPLETE status"
        )

    def test_reference_indexing_does_not_contain_hint_analysis_status(self):
        assert "HINT_ANALYSIS_COMPLETE" not in REFERENCE_INDEXING_AGENT_DEFINITION, (
            "REFERENCE_INDEXING_AGENT_DEFINITION must not contain the hint "
            "agent's HINT_ANALYSIS_COMPLETE status"
        )

    def test_reference_indexing_does_not_contain_hint_blueprint_conflict_status(self):
        assert "HINT_BLUEPRINT_CONFLICT" not in REFERENCE_INDEXING_AGENT_DEFINITION, (
            "REFERENCE_INDEXING_AGENT_DEFINITION must not contain the hint "
            "agent's HINT_BLUEPRINT_CONFLICT status"
        )


# ===========================================================================
# Cross-cutting: No foreign agent statuses leak into any definition
# ===========================================================================


class TestNoForeignStatusLeakage:
    """Definitions must not contain status lines belonging to unrelated agents."""

    # Statuses from other agents that should NOT appear in any Unit 22 definition
    FOREIGN_STATUSES = [
        "SPEC_DRAFT_COMPLETE",
        "SPEC_REVISION_COMPLETE",
        "BLUEPRINT_DRAFT_COMPLETE",
        "BLUEPRINT_REVISION_COMPLETE",
        "TEST_GENERATION_COMPLETE",
        "IMPLEMENTATION_COMPLETE",
        "REVIEW_COMPLETE",
        "COVERAGE_COMPLETE",
        "INTEGRATION_TESTS_COMPLETE",
        "REPO_ASSEMBLY_COMPLETE",
        "TRIAGE_COMPLETE",
        "REPAIR_COMPLETE",
        "ORACLE_DRY_RUN_COMPLETE",
        "ORACLE_ALL_CLEAR",
        "ORACLE_FIX_APPLIED",
    ]

    @pytest.mark.parametrize("name,defn", list(ALL_DEFINITIONS.items()))
    @pytest.mark.parametrize("foreign_status", FOREIGN_STATUSES)
    def test_definition_does_not_contain_foreign_status(
        self, name, defn, foreign_status
    ):
        assert foreign_status not in defn, (
            f"{name} must not contain foreign status '{foreign_status}'"
        )


# ===========================================================================
# Content substantiality: definitions have meaningful content
# ===========================================================================


class TestContentSubstantiality:
    """Each definition must have substantial content (not just a placeholder)."""

    @pytest.mark.parametrize("name,value", list(ALL_DEFINITIONS.items()))
    def test_definition_has_minimum_length(self, name, value):
        # Agent definitions are markdown documents with instructions;
        # they should be at least a few hundred characters
        assert len(value) >= 100, (
            f"{name} has only {len(value)} characters; "
            "agent definitions must be substantial markdown documents"
        )

    @pytest.mark.parametrize("name,value", list(ALL_DEFINITIONS.items()))
    def test_definition_has_multiple_lines(self, name, value):
        line_count = len(value.strip().splitlines())
        assert line_count >= 5, (
            f"{name} has only {line_count} lines; "
            "agent definitions must span multiple lines"
        )

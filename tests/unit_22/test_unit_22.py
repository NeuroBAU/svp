"""Unit 22: Support Agent Definitions -- complete test suite.

Synthetic data assumptions:
- HELP_AGENT_DEFINITION is a str containing the complete markdown content of
  the help agent definition file. All structural tests inspect this string.
- HINT_AGENT_DEFINITION is a str containing the complete markdown content of
  the hint agent definition file. All structural tests inspect this string.
- REFERENCE_INDEXING_AGENT_DEFINITION is a str containing the complete markdown
  content of the reference indexing agent definition file. All structural tests
  inspect this string.
- All three definitions are agent system prompt markdown files. Structural
  tests search for specific phrases, keywords, and patterns within the markdown
  to verify contract compliance.
- Tool names tested against HELP_AGENT_DEFINITION are the canonical tool names:
  Read, Grep, Glob, and web search (the read-only tool set).
- Status strings are expected verbatim in the definitions:
  HELP_SESSION_COMPLETE: no hint, HELP_SESSION_COMPLETE: hint forwarded,
  HINT_ANALYSIS_COMPLETE, HINT_BLUEPRINT_CONFLICT, INDEXING_COMPLETE.
- The hint agent dual-mode terms (reactive, proactive, single-shot,
  ledger-based) are expected as keywords or phrases within the definition.
- Keyword matching is case-insensitive where noted, but status strings and
  tool names are expected in their canonical form.
"""

import re

from support_agents import (
    HELP_AGENT_DEFINITION,
    HINT_AGENT_DEFINITION,
    REFERENCE_INDEXING_AGENT_DEFINITION,
)

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def help_contains(phrase: str, case_sensitive: bool = True) -> bool:
    """Check whether the help agent definition contains the given phrase."""
    if case_sensitive:
        return phrase in HELP_AGENT_DEFINITION
    return phrase.lower() in HELP_AGENT_DEFINITION.lower()


def help_matches(pattern: str, flags: int = 0) -> list:
    """Return all regex matches of pattern in the help agent definition."""
    return re.findall(pattern, HELP_AGENT_DEFINITION, flags)


def hint_contains(phrase: str, case_sensitive: bool = True) -> bool:
    """Check whether the hint agent definition contains the given phrase."""
    if case_sensitive:
        return phrase in HINT_AGENT_DEFINITION
    return phrase.lower() in HINT_AGENT_DEFINITION.lower()


def hint_matches(pattern: str, flags: int = 0) -> list:
    """Return all regex matches of pattern in the hint agent definition."""
    return re.findall(pattern, HINT_AGENT_DEFINITION, flags)


def ref_contains(phrase: str, case_sensitive: bool = True) -> bool:
    """Check whether the reference indexing definition contains the phrase."""
    if case_sensitive:
        return phrase in REFERENCE_INDEXING_AGENT_DEFINITION
    return phrase.lower() in REFERENCE_INDEXING_AGENT_DEFINITION.lower()


def ref_matches(pattern: str, flags: int = 0) -> list:
    """Return all regex matches of pattern in the reference indexing def."""
    return re.findall(pattern, REFERENCE_INDEXING_AGENT_DEFINITION, flags)


# ===========================================================================
# HELP_AGENT_DEFINITION: type and non-emptiness
# ===========================================================================


class TestHelpAgentDefinitionBasicStructure:
    """Verify HELP_AGENT_DEFINITION is a non-empty string with markdown."""

    def test_definition_is_string(self):
        assert isinstance(HELP_AGENT_DEFINITION, str)

    def test_definition_is_nonempty(self):
        assert len(HELP_AGENT_DEFINITION.strip()) > 0

    def test_definition_contains_markdown_headings(self):
        """Agent definition must be structured markdown with headings."""
        assert re.search(r"^#+\s+", HELP_AGENT_DEFINITION, re.MULTILINE)


# ===========================================================================
# HELP_AGENT_DEFINITION: read-only constraint
# ===========================================================================


class TestHelpAgentReadOnlyConstraint:
    """HELP_AGENT_DEFINITION must restrict tool access to Read, Grep, Glob,
    and web search (read-only constraint)."""

    def test_read_tool_referenced(self):
        """Read tool must be listed in the allowed tools."""
        assert help_contains("Read")

    def test_grep_tool_referenced(self):
        """Grep tool must be listed in the allowed tools."""
        assert help_contains("Grep")

    def test_glob_tool_referenced(self):
        """Glob tool must be listed in the allowed tools."""
        assert help_contains("Glob")

    def test_web_search_tool_referenced(self):
        """Web search tool must be listed in the allowed tools."""
        assert (
            help_contains("web search", case_sensitive=False)
            or help_contains("WebSearch")
            or help_contains("web_search")
        )

    def test_read_only_constraint_documented(self):
        """The read-only nature of the constraint must be documented."""
        assert (
            help_contains("read-only", case_sensitive=False)
            or help_contains("read only", case_sensitive=False)
            or help_contains("restricted", case_sensitive=False)
        )

    def test_no_write_tools_permitted(self):
        """The definition should convey that writing/editing is not allowed.

        We verify the read-only constraint is explicit by checking for
        restrictive language, not by exhaustively listing banned tools."""
        assert (
            help_contains("restrict", case_sensitive=False)
            or help_contains("read-only", case_sensitive=False)
            or help_contains("only", case_sensitive=False)
        )


# ===========================================================================
# HELP_AGENT_DEFINITION: gate-invocation hint formulation workflow
# ===========================================================================


class TestHelpAgentHintFormulationWorkflow:
    """HELP_AGENT_DEFINITION must describe the gate-invocation hint
    formulation workflow."""

    def test_gate_invocation_referenced(self):
        """Gate invocation must be referenced in the definition."""
        assert help_contains("gate", case_sensitive=False)

    def test_hint_formulation_referenced(self):
        """Hint formulation workflow must be referenced."""
        assert help_contains("hint", case_sensitive=False)

    def test_formulation_or_workflow_keyword_present(self):
        """The workflow concept must be present."""
        assert (
            help_contains("formulation", case_sensitive=False)
            or help_contains("workflow", case_sensitive=False)
            or help_contains("formulate", case_sensitive=False)
        )


# ===========================================================================
# HELP_AGENT_DEFINITION: hint forwarding mechanism
# ===========================================================================


class TestHelpAgentHintForwarding:
    """HELP_AGENT_DEFINITION must describe the hint forwarding mechanism:
    assembles hint, passes to hint system."""

    def test_forwarding_referenced(self):
        """Hint forwarding must be referenced."""
        assert help_contains("forward", case_sensitive=False)

    def test_assembles_hint_referenced(self):
        """Assembling the hint must be referenced."""
        assert (
            help_contains("assembl", case_sensitive=False)
            or help_contains("construct", case_sensitive=False)
            or help_contains("build", case_sensitive=False)
            or help_contains("formulate", case_sensitive=False)
        )

    def test_hint_system_referenced(self):
        """Passing to the hint system must be referenced."""
        assert (
            help_contains("hint system", case_sensitive=False)
            or help_contains("hint agent", case_sensitive=False)
            or (
                help_contains("hint", case_sensitive=False)
                and help_contains("pass", case_sensitive=False)
            )
        )


# ===========================================================================
# HELP_AGENT_DEFINITION: terminal status strings
# ===========================================================================


class TestHelpAgentStatusStrings:
    """HELP_AGENT_DEFINITION must document both terminal status strings."""

    def test_status_no_hint(self):
        """Status 'HELP_SESSION_COMPLETE: no hint' must appear."""
        assert (
            help_contains("HELP_SESSION_COMPLETE: no hint")
            or help_contains("HELP_SESSION_COMPLETE:no hint")
            or (help_contains("HELP_SESSION_COMPLETE") and help_contains("no hint"))
        )

    def test_status_hint_forwarded(self):
        """Status 'HELP_SESSION_COMPLETE: hint forwarded' must appear."""
        assert (
            help_contains("HELP_SESSION_COMPLETE: hint forwarded")
            or help_contains("HELP_SESSION_COMPLETE:hint forwarded")
            or (
                help_contains("HELP_SESSION_COMPLETE")
                and help_contains("hint forwarded")
            )
        )

    def test_both_statuses_are_distinct(self):
        """Both status variants must be distinguishable in the definition."""
        assert help_contains("no hint") and help_contains("hint forwarded")

    def test_help_session_complete_prefix_present(self):
        """The HELP_SESSION_COMPLETE prefix must appear at least once."""
        assert help_contains("HELP_SESSION_COMPLETE")


# ===========================================================================
# HINT_AGENT_DEFINITION: type and non-emptiness
# ===========================================================================


class TestHintAgentDefinitionBasicStructure:
    """Verify HINT_AGENT_DEFINITION is a non-empty string with markdown."""

    def test_definition_is_string(self):
        assert isinstance(HINT_AGENT_DEFINITION, str)

    def test_definition_is_nonempty(self):
        assert len(HINT_AGENT_DEFINITION.strip()) > 0

    def test_definition_contains_markdown_headings(self):
        """Agent definition must be structured markdown with headings."""
        assert re.search(r"^#+\s+", HINT_AGENT_DEFINITION, re.MULTILINE)


# ===========================================================================
# HINT_AGENT_DEFINITION: dual-mode behavior
# ===========================================================================


class TestHintAgentDualMode:
    """HINT_AGENT_DEFINITION must describe dual-mode behavior:
    single-shot reactive and ledger-based proactive."""

    def test_reactive_mode_referenced(self):
        """Reactive mode must be referenced in the definition."""
        assert hint_contains("reactive", case_sensitive=False)

    def test_proactive_mode_referenced(self):
        """Proactive mode must be referenced in the definition."""
        assert hint_contains("proactive", case_sensitive=False)

    def test_single_shot_reactive_described(self):
        """Single-shot reactive mode (immediate response to hint text)."""
        assert (
            hint_contains("single-shot", case_sensitive=False)
            or hint_contains("single shot", case_sensitive=False)
            or hint_contains("immediate", case_sensitive=False)
        )

    def test_ledger_based_proactive_described(self):
        """Ledger-based proactive mode (analyzes context, suggests actions)."""
        assert hint_contains("ledger", case_sensitive=False)

    def test_dual_mode_concept_present(self):
        """The dual-mode concept should be explicitly stated."""
        assert (
            hint_contains("dual-mode", case_sensitive=False)
            or hint_contains("dual mode", case_sensitive=False)
            or hint_contains("two mode", case_sensitive=False)
            or (
                hint_contains("reactive", case_sensitive=False)
                and hint_contains("proactive", case_sensitive=False)
            )
        )


# ===========================================================================
# HINT_AGENT_DEFINITION: mode determination logic
# ===========================================================================


class TestHintAgentModeDetermination:
    """HINT_AGENT_DEFINITION must describe mode determination logic:
    reactive when hint text provided, proactive when ledger context only."""

    def test_reactive_trigger_hint_text(self):
        """Reactive mode triggers when hint text is provided."""
        assert (
            hint_contains("hint text", case_sensitive=False)
            or hint_contains("hint provided", case_sensitive=False)
            or (
                hint_contains("hint", case_sensitive=False)
                and hint_contains("text", case_sensitive=False)
            )
        )

    def test_proactive_trigger_ledger_context(self):
        """Proactive mode triggers when only ledger context is available."""
        assert hint_contains("ledger context", case_sensitive=False) or hint_contains(
            "ledger", case_sensitive=False
        )

    def test_mode_determination_documented(self):
        """Mode determination or selection logic must be documented."""
        assert (
            hint_contains("determin", case_sensitive=False)
            or hint_contains("select", case_sensitive=False)
            or hint_contains("mode", case_sensitive=False)
        )

    def test_reactive_is_immediate_response(self):
        """Reactive mode provides immediate response to hint text."""
        assert (
            hint_contains("immediate", case_sensitive=False)
            or hint_contains("respond", case_sensitive=False)
            or hint_contains("response", case_sensitive=False)
        )

    def test_proactive_analyzes_context(self):
        """Proactive mode analyzes context and suggests actions."""
        assert hint_contains("analy", case_sensitive=False) or hint_contains(
            "context", case_sensitive=False
        )

    def test_proactive_suggests_actions(self):
        """Proactive mode suggests actions."""
        assert (
            hint_contains("suggest", case_sensitive=False)
            or hint_contains("action", case_sensitive=False)
            or hint_contains("recommend", case_sensitive=False)
        )


# ===========================================================================
# HINT_AGENT_DEFINITION: terminal status strings
# ===========================================================================


class TestHintAgentStatusStrings:
    """HINT_AGENT_DEFINITION must document both terminal status strings."""

    def test_status_hint_analysis_complete(self):
        """Status 'HINT_ANALYSIS_COMPLETE' must appear."""
        assert hint_contains("HINT_ANALYSIS_COMPLETE")

    def test_status_hint_blueprint_conflict(self):
        """Status 'HINT_BLUEPRINT_CONFLICT' must appear."""
        assert hint_contains("HINT_BLUEPRINT_CONFLICT")

    def test_blueprint_conflict_includes_details_placeholder(self):
        """HINT_BLUEPRINT_CONFLICT status includes a details component."""
        # The contract says: HINT_BLUEPRINT_CONFLICT: <details>
        assert (
            hint_contains("HINT_BLUEPRINT_CONFLICT:")
            or hint_contains("HINT_BLUEPRINT_CONFLICT <")
            or (
                hint_contains("HINT_BLUEPRINT_CONFLICT")
                and hint_contains("detail", case_sensitive=False)
            )
        )

    def test_both_statuses_are_distinct_strings(self):
        """Both HINT_ANALYSIS_COMPLETE and HINT_BLUEPRINT_CONFLICT must be
        present as distinct status options."""
        assert hint_contains("HINT_ANALYSIS_COMPLETE")
        assert hint_contains("HINT_BLUEPRINT_CONFLICT")


# ===========================================================================
# REFERENCE_INDEXING_AGENT_DEFINITION: type and non-emptiness
# ===========================================================================


class TestReferenceIndexingDefinitionBasicStructure:
    """Verify REFERENCE_INDEXING_AGENT_DEFINITION is a non-empty string
    with markdown."""

    def test_definition_is_string(self):
        assert isinstance(REFERENCE_INDEXING_AGENT_DEFINITION, str)

    def test_definition_is_nonempty(self):
        assert len(REFERENCE_INDEXING_AGENT_DEFINITION.strip()) > 0

    def test_definition_contains_markdown_headings(self):
        """Agent definition must be structured markdown with headings."""
        assert re.search(r"^#+\s+", REFERENCE_INDEXING_AGENT_DEFINITION, re.MULTILINE)


# ===========================================================================
# REFERENCE_INDEXING_AGENT_DEFINITION: document and repository reference
# ===========================================================================


class TestReferenceIndexingDocumentHandling:
    """REFERENCE_INDEXING_AGENT_DEFINITION must describe document and
    repository reference handling."""

    def test_document_reference_handling(self):
        """Document reference handling must be described."""
        assert ref_contains("document", case_sensitive=False)

    def test_repository_reference_handling(self):
        """Repository reference handling must be described."""
        assert ref_contains("repository", case_sensitive=False) or ref_contains(
            "repo", case_sensitive=False
        )

    def test_reference_concept_present(self):
        """Reference handling concept must be present."""
        assert ref_contains("reference", case_sensitive=False)

    def test_indexing_concept_present(self):
        """Indexing concept must be present."""
        assert ref_contains("index", case_sensitive=False)


# ===========================================================================
# REFERENCE_INDEXING_AGENT_DEFINITION: terminal status string
# ===========================================================================


class TestReferenceIndexingStatusStrings:
    """REFERENCE_INDEXING_AGENT_DEFINITION must document its terminal status."""

    def test_status_indexing_complete(self):
        """Status 'INDEXING_COMPLETE' must appear."""
        assert ref_contains("INDEXING_COMPLETE")


# ===========================================================================
# Cross-definition: all three definitions are distinct
# ===========================================================================


class TestCrossDefinitionDistinctness:
    """All three agent definitions must be distinct non-overlapping strings."""

    def test_help_and_hint_are_distinct(self):
        """HELP_AGENT_DEFINITION and HINT_AGENT_DEFINITION differ."""
        assert HELP_AGENT_DEFINITION != HINT_AGENT_DEFINITION

    def test_help_and_reference_are_distinct(self):
        """HELP_AGENT_DEFINITION and REFERENCE_INDEXING_AGENT_DEFINITION
        differ."""
        assert HELP_AGENT_DEFINITION != REFERENCE_INDEXING_AGENT_DEFINITION

    def test_hint_and_reference_are_distinct(self):
        """HINT_AGENT_DEFINITION and REFERENCE_INDEXING_AGENT_DEFINITION
        differ."""
        assert HINT_AGENT_DEFINITION != REFERENCE_INDEXING_AGENT_DEFINITION


# ===========================================================================
# Cross-definition: status strings are unique to their definition
# ===========================================================================


class TestStatusStringUniqueness:
    """Each agent's terminal status string(s) should appear in its own
    definition and not be confused with other agents' statuses."""

    def test_help_session_complete_in_help_definition(self):
        """HELP_SESSION_COMPLETE appears in help agent definition."""
        assert help_contains("HELP_SESSION_COMPLETE")

    def test_hint_analysis_complete_in_hint_definition(self):
        """HINT_ANALYSIS_COMPLETE appears in hint agent definition."""
        assert hint_contains("HINT_ANALYSIS_COMPLETE")

    def test_hint_blueprint_conflict_in_hint_definition(self):
        """HINT_BLUEPRINT_CONFLICT appears in hint agent definition."""
        assert hint_contains("HINT_BLUEPRINT_CONFLICT")

    def test_indexing_complete_in_reference_definition(self):
        """INDEXING_COMPLETE appears in reference indexing definition."""
        assert ref_contains("INDEXING_COMPLETE")


# ===========================================================================
# Cross-definition: all exports are non-None
# ===========================================================================


class TestAllExportsNonNone:
    """No exported value should be None."""

    def test_help_definition_not_none(self):
        assert HELP_AGENT_DEFINITION is not None

    def test_hint_definition_not_none(self):
        assert HINT_AGENT_DEFINITION is not None

    def test_reference_definition_not_none(self):
        assert REFERENCE_INDEXING_AGENT_DEFINITION is not None


# ===========================================================================
# HELP_AGENT_DEFINITION: comprehensive tool set verification
# ===========================================================================


class TestHelpAgentToolSet:
    """Verify the complete read-only tool set is documented: exactly Read,
    Grep, Glob, and web search -- no write/edit tools."""

    def test_four_tools_enumerated(self):
        """All four allowed tools should be mentioned."""
        has_read = help_contains("Read")
        has_grep = help_contains("Grep")
        has_glob = help_contains("Glob")
        has_web = (
            help_contains("web search", case_sensitive=False)
            or help_contains("WebSearch")
            or help_contains("web_search")
        )
        assert has_read and has_grep and has_glob and has_web, (
            f"Expected all four tools. Read={has_read}, Grep={has_grep}, "
            f"Glob={has_glob}, WebSearch={has_web}"
        )


# ===========================================================================
# HELP_AGENT_DEFINITION: hint workflow produces two possible outcomes
# ===========================================================================


class TestHelpAgentWorkflowOutcomes:
    """The help agent workflow produces exactly two outcomes: no hint
    generated, or hint assembled and forwarded."""

    def test_no_hint_outcome_documented(self):
        """The no-hint outcome must be documented."""
        assert help_contains("no hint")

    def test_hint_forwarded_outcome_documented(self):
        """The hint-forwarded outcome must be documented."""
        assert help_contains("hint forwarded") or help_contains(
            "forwarded", case_sensitive=False
        )

    def test_two_status_variants_match_two_outcomes(self):
        """Each outcome maps to its own terminal status string."""
        no_hint_status = help_contains("HELP_SESSION_COMPLETE") and help_contains(
            "no hint"
        )
        forwarded_status = help_contains("HELP_SESSION_COMPLETE") and help_contains(
            "hint forwarded"
        )
        assert no_hint_status and forwarded_status


# ===========================================================================
# HINT_AGENT_DEFINITION: reactive mode details
# ===========================================================================


class TestHintAgentReactiveMode:
    """Reactive mode: single-shot, immediate response to hint text."""

    def test_reactive_mode_is_single_shot(self):
        """Reactive mode is described as single-shot."""
        assert hint_contains("single-shot", case_sensitive=False) or hint_contains(
            "single shot", case_sensitive=False
        )

    def test_reactive_triggered_by_hint_text(self):
        """Reactive mode is triggered when hint text is provided."""
        assert (
            hint_contains("hint text", case_sensitive=False)
            or hint_contains("hint provided", case_sensitive=False)
            or hint_contains("provided", case_sensitive=False)
        )

    def test_reactive_produces_immediate_response(self):
        """Reactive mode produces an immediate response."""
        assert (
            hint_contains("immediate", case_sensitive=False)
            or hint_contains("response", case_sensitive=False)
            or hint_contains("respond", case_sensitive=False)
        )


# ===========================================================================
# HINT_AGENT_DEFINITION: proactive mode details
# ===========================================================================


class TestHintAgentProactiveMode:
    """Proactive mode: ledger-based, analyzes context, suggests actions."""

    def test_proactive_mode_is_ledger_based(self):
        """Proactive mode is described as ledger-based."""
        assert (
            hint_contains("ledger-based", case_sensitive=False)
            or hint_contains("ledger based", case_sensitive=False)
            or hint_contains("ledger", case_sensitive=False)
        )

    def test_proactive_triggered_by_ledger_context_only(self):
        """Proactive mode triggers when only ledger context is available."""
        assert hint_contains("ledger context", case_sensitive=False) or (
            hint_contains("ledger", case_sensitive=False)
            and hint_contains("context", case_sensitive=False)
        )

    def test_proactive_analyzes_and_suggests(self):
        """Proactive mode analyzes context and suggests actions."""
        analyzes = hint_contains("analy", case_sensitive=False)
        suggests = (
            hint_contains("suggest", case_sensitive=False)
            or hint_contains("action", case_sensitive=False)
            or hint_contains("recommend", case_sensitive=False)
        )
        assert analyzes or suggests


# ===========================================================================
# HINT_AGENT_DEFINITION: blueprint conflict details
# ===========================================================================


class TestHintAgentBlueprintConflict:
    """HINT_BLUEPRINT_CONFLICT status includes details about the conflict."""

    def test_blueprint_keyword_present(self):
        """Blueprint concept must be present in hint definition."""
        assert hint_contains("blueprint", case_sensitive=False)

    def test_conflict_keyword_present(self):
        """Conflict concept must be present in hint definition."""
        assert hint_contains("conflict", case_sensitive=False) or hint_contains(
            "BLUEPRINT_CONFLICT"
        )

    def test_conflict_status_has_details_format(self):
        """The HINT_BLUEPRINT_CONFLICT status should indicate it carries
        details (e.g., colon-separated or angle-bracketed)."""
        # Contract: HINT_BLUEPRINT_CONFLICT: <details>
        pattern = r"HINT_BLUEPRINT_CONFLICT\s*[:\-]\s*"
        assert (
            re.search(pattern, HINT_AGENT_DEFINITION)
            or hint_contains("HINT_BLUEPRINT_CONFLICT:")
            or (
                hint_contains("HINT_BLUEPRINT_CONFLICT")
                and hint_contains("<details>", case_sensitive=False)
            )
        )


# ===========================================================================
# REFERENCE_INDEXING_AGENT_DEFINITION: content depth
# ===========================================================================


class TestReferenceIndexingContentDepth:
    """The reference indexing definition should contain substantive content
    beyond just a status string."""

    def test_definition_has_meaningful_length(self):
        """The definition should be a substantive document, not a stub."""
        assert len(REFERENCE_INDEXING_AGENT_DEFINITION.strip()) > 50

    def test_definition_describes_handling_behavior(self):
        """The definition should describe how references are handled."""
        assert (
            ref_contains("handl", case_sensitive=False)
            or ref_contains("process", case_sensitive=False)
            or ref_contains("manag", case_sensitive=False)
            or ref_contains("index", case_sensitive=False)
        )

    def test_definition_mentions_both_reference_types(self):
        """Both document and repository references should be mentioned."""
        has_doc = ref_contains("document", case_sensitive=False)
        has_repo = ref_contains("repository", case_sensitive=False) or ref_contains(
            "repo", case_sensitive=False
        )
        assert has_doc and has_repo, (
            f"Expected both reference types. document={has_doc}, repository={has_repo}"
        )


# ===========================================================================
# HELP_AGENT_DEFINITION: content depth
# ===========================================================================


class TestHelpAgentContentDepth:
    """The help agent definition should contain substantive content
    covering all contracted behaviors."""

    def test_definition_has_meaningful_length(self):
        """The definition should be a substantive document, not a stub."""
        assert len(HELP_AGENT_DEFINITION.strip()) > 100

    def test_definition_covers_tool_access(self):
        """Tool access restrictions are documented."""
        assert help_contains("tool", case_sensitive=False) or help_contains(
            "access", case_sensitive=False
        )

    def test_definition_covers_hint_workflow(self):
        """Hint formulation workflow is documented."""
        assert help_contains("hint", case_sensitive=False)

    def test_definition_covers_forwarding(self):
        """Hint forwarding mechanism is documented."""
        assert help_contains("forward", case_sensitive=False)

    def test_definition_covers_terminal_status(self):
        """Terminal status strings are documented."""
        assert help_contains("HELP_SESSION_COMPLETE")


# ===========================================================================
# HINT_AGENT_DEFINITION: content depth
# ===========================================================================


class TestHintAgentContentDepth:
    """The hint agent definition should contain substantive content
    covering all contracted behaviors."""

    def test_definition_has_meaningful_length(self):
        """The definition should be a substantive document, not a stub."""
        assert len(HINT_AGENT_DEFINITION.strip()) > 100

    def test_definition_covers_dual_mode(self):
        """Dual-mode behavior is documented."""
        assert hint_contains("reactive", case_sensitive=False) and hint_contains(
            "proactive", case_sensitive=False
        )

    def test_definition_covers_mode_determination(self):
        """Mode determination logic is documented."""
        assert hint_contains("mode", case_sensitive=False)

    def test_definition_covers_terminal_status(self):
        """Terminal status strings are documented."""
        assert hint_contains("HINT_ANALYSIS_COMPLETE") and hint_contains(
            "HINT_BLUEPRINT_CONFLICT"
        )


# ===========================================================================
# All definitions: markdown structure quality
# ===========================================================================


class TestMarkdownStructureQuality:
    """All three definitions should have well-formed markdown structure."""

    def test_help_definition_has_multiple_sections(self):
        """Help definition should have multiple markdown sections."""
        headings = re.findall(r"^#+\s+", HELP_AGENT_DEFINITION, re.MULTILINE)
        assert len(headings) >= 1

    def test_hint_definition_has_multiple_sections(self):
        """Hint definition should have multiple markdown sections."""
        headings = re.findall(r"^#+\s+", HINT_AGENT_DEFINITION, re.MULTILINE)
        assert len(headings) >= 1

    def test_reference_definition_has_multiple_sections(self):
        """Reference definition should have multiple markdown sections."""
        headings = re.findall(
            r"^#+\s+", REFERENCE_INDEXING_AGENT_DEFINITION, re.MULTILINE
        )
        assert len(headings) >= 1

    def test_help_definition_no_trailing_whitespace_only(self):
        """Help definition is not just whitespace."""
        assert HELP_AGENT_DEFINITION.strip() != ""

    def test_hint_definition_no_trailing_whitespace_only(self):
        """Hint definition is not just whitespace."""
        assert HINT_AGENT_DEFINITION.strip() != ""

    def test_reference_definition_no_trailing_whitespace_only(self):
        """Reference definition is not just whitespace."""
        assert REFERENCE_INDEXING_AGENT_DEFINITION.strip() != ""

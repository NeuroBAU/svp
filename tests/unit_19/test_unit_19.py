"""
Tests for Unit 19: Blueprint Checker Definition.

Verifies the BLUEPRINT_CHECKER_DEFINITION constant contains all required
content elements as specified in the blueprint contracts.

Synthetic data assumptions:
- No synthetic data is generated. All tests inspect the actual module-level
  constant BLUEPRINT_CHECKER_DEFINITION for the presence of required content
  fragments (keywords, phrases, structural markers).
- String matching is case-insensitive where appropriate to avoid brittle
  tests tied to specific capitalization choices.
- The constant is expected to be a non-empty markdown string containing the
  full agent definition for the blueprint checker agent.

Test count: 35 tests.
"""

from unit_19 import BLUEPRINT_CHECKER_DEFINITION

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _lower(text: str) -> str:
    """Return lowercased text for case-insensitive matching."""
    return text.lower()


# ---------------------------------------------------------------------------
# Basic structural requirements
# ---------------------------------------------------------------------------


class TestBlueprintCheckerDefinitionBasicStructure:
    """Verify that the definition is a non-empty markdown string."""

    def test_definition_is_a_string(self):
        assert isinstance(BLUEPRINT_CHECKER_DEFINITION, str)

    def test_definition_is_non_empty(self):
        assert len(BLUEPRINT_CHECKER_DEFINITION.strip()) > 0

    def test_definition_contains_markdown_heading(self):
        """Agent definition markdown should contain at least one heading."""
        assert "#" in BLUEPRINT_CHECKER_DEFINITION

    def test_definition_has_substantial_length(self):
        """A full agent definition should be non-trivial in length."""
        assert len(BLUEPRINT_CHECKER_DEFINITION) > 200, (
            "A complete agent definition markdown should be substantially longer "
            "than a few sentences"
        )


# ---------------------------------------------------------------------------
# DAG acyclicity check
# ---------------------------------------------------------------------------


class TestDAGAcyclicityCheck:
    """The definition must mandate a DAG acyclicity check."""

    def test_mentions_dag(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        assert "dag" in lower

    def test_mentions_acyclicity_or_acyclic(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        has_acyclicity = "acyclic" in lower or "acyclicity" in lower
        assert has_acyclicity, (
            "Definition must mention acyclicity or acyclic in the context of DAG checks"
        )


# ---------------------------------------------------------------------------
# Profile preference validation (Layer 2)
# ---------------------------------------------------------------------------


class TestProfilePreferenceValidation:
    """The definition must require profile preference validation at Layer 2."""

    def test_mentions_profile_preference(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        has_profile_pref = "profile" in lower and "preference" in lower
        assert has_profile_pref, (
            "Definition must reference profile preference validation"
        )

    def test_mentions_layer_2(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        has_layer_2 = "layer 2" in lower or "layer-2" in lower or "layer2" in lower
        assert has_layer_2, (
            "Definition must reference Layer 2 in the context of profile preference "
            "validation"
        )


# ---------------------------------------------------------------------------
# Pattern catalog validation (P1-P13+)
# ---------------------------------------------------------------------------


class TestPatternCatalogValidation:
    """The definition must require pattern catalog validation covering P1-P13+."""

    def test_mentions_pattern_catalog(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        has_pattern_catalog = "pattern catalog" in lower or "pattern-catalog" in lower
        assert has_pattern_catalog, (
            "Definition must reference pattern catalog validation"
        )

    def test_mentions_pattern_identifiers(self):
        """Should reference the pattern range P1 through P13 or beyond."""
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        has_p1 = "p1" in lower
        has_p13 = "p13" in lower
        assert has_p1 or has_p13, (
            "Definition must reference pattern identifiers (e.g. P1-P13)"
        )


# ---------------------------------------------------------------------------
# Contract granularity verification
# ---------------------------------------------------------------------------


class TestContractGranularityVerification:
    """
    The definition must require contract granularity verification covering:
    - Exported function coverage
    - Per-gate-option dispatch contracts
    - Call-site verification
    - Re-entry path documentation
    """

    def test_mentions_contract_granularity(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        has_contract_gran = "contract" in lower and "granularity" in lower
        assert has_contract_gran, (
            "Definition must reference contract granularity verification"
        )

    def test_mentions_exported_function_coverage(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        has_exported = "exported" in lower and "function" in lower
        assert has_exported, "Definition must reference exported function coverage"

    def test_mentions_per_gate_option_dispatch_contracts(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        has_gate_dispatch = "gate" in lower and "dispatch" in lower
        assert has_gate_dispatch, (
            "Definition must reference per-gate-option dispatch contracts"
        )

    def test_mentions_call_site_verification(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        has_call_site = "call-site" in lower or "call site" in lower
        assert has_call_site, "Definition must reference call-site verification"

    def test_mentions_re_entry_path_documentation(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        has_reentry = "re-entry" in lower or "reentry" in lower or "re entry" in lower
        assert has_reentry, "Definition must reference re-entry path documentation"


# ---------------------------------------------------------------------------
# Language registry completeness validation
# ---------------------------------------------------------------------------


class TestLanguageRegistryCompletenessValidation:
    """The definition must require language registry completeness validation."""

    def test_mentions_language_registry(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        has_lang_registry = "language" in lower and "registry" in lower
        assert has_lang_registry, (
            "Definition must reference language registry completeness validation"
        )

    def test_mentions_completeness(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        has_completeness = "completeness" in lower or "complete" in lower
        assert has_completeness, (
            "Definition must reference completeness in the context of registry validation"
        )


# ---------------------------------------------------------------------------
# Alignment checker checklist file
# ---------------------------------------------------------------------------


class TestAlignmentCheckerChecklist:
    """The definition must reference the alignment checker checklist file."""

    def test_mentions_alignment_checker_checklist_path(self):
        assert "alignment_checker_checklist" in BLUEPRINT_CHECKER_DEFINITION, (
            "Definition must reference the alignment checker checklist file path"
        )

    def test_mentions_svp_directory_for_checklist(self):
        assert ".svp" in BLUEPRINT_CHECKER_DEFINITION, (
            "Definition must reference the .svp directory where the checklist resides"
        )

    def test_mentions_checklist_markdown_extension(self):
        """The checklist file should be referenced with its .md extension."""
        assert "alignment_checker_checklist.md" in BLUEPRINT_CHECKER_DEFINITION, (
            "Definition must reference the complete checklist filename including .md"
        )


# ---------------------------------------------------------------------------
# Internal consistency validation (prose vs contracts)
# ---------------------------------------------------------------------------


class TestInternalConsistencyValidation:
    """Validate internal consistency between prose and contracts."""

    def test_mentions_prose(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        assert "prose" in lower, (
            "Definition must reference prose in the context of consistency checking"
        )

    def test_mentions_contracts(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        assert "contracts" in lower or "contract" in lower, (
            "Definition must reference contracts in the context of consistency checking"
        )

    def test_mentions_consistency(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        has_consistency = "consistency" in lower or "consistent" in lower
        assert has_consistency, (
            "Definition must reference consistency between prose and contracts"
        )


# ---------------------------------------------------------------------------
# Report most fundamental level corollary
# ---------------------------------------------------------------------------


class TestReportMostFundamentalLevel:
    """
    The definition must encode the 'report most fundamental level' corollary:
    spec problems supersede blueprint problems.
    """

    def test_mentions_fundamental_level_or_supersede(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        has_fundamental = "fundamental" in lower or "supersede" in lower
        assert has_fundamental, (
            "Definition must reference the 'report most fundamental level' corollary"
        )

    def test_spec_problems_supersede_blueprint_problems(self):
        """Spec-level issues must be reported in preference to blueprint issues."""
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        assert "spec" in lower, (
            "Definition must reference spec-level problems superseding blueprint problems"
        )


# ---------------------------------------------------------------------------
# Terminal status lines
# ---------------------------------------------------------------------------


class TestTerminalStatusLines:
    """
    The definition must specify exactly three terminal statuses:
    - ALIGNMENT_CONFIRMED
    - ALIGNMENT_FAILED: spec
    - ALIGNMENT_FAILED: blueprint
    """

    def test_contains_alignment_confirmed_status(self):
        assert "ALIGNMENT_CONFIRMED" in BLUEPRINT_CHECKER_DEFINITION

    def test_contains_alignment_failed_spec_status(self):
        assert "ALIGNMENT_FAILED" in BLUEPRINT_CHECKER_DEFINITION
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        assert "alignment_failed" in lower and "spec" in lower

    def test_contains_alignment_failed_blueprint_status(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        assert "alignment_failed" in lower and "blueprint" in lower


# ---------------------------------------------------------------------------
# Baked checklist items (Section 3.20 adaptation)
# ---------------------------------------------------------------------------


class TestBakedChecklistItems:
    """The definition must include baked-in checklist items per Section 3.20 adaptation."""

    def test_mentions_checklist(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        assert "checklist" in lower, (
            "Definition must reference a checklist (baked checklist items)"
        )


# ---------------------------------------------------------------------------
# Section 3.19 contract granularity rules
# ---------------------------------------------------------------------------


class TestSection319ContractGranularityRules:
    """The definition must reference or encode Section 3.19 contract granularity rules."""

    def test_mentions_granularity_rules_or_section_reference(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        assert "granularity" in lower, (
            "Definition must reference contract granularity rules"
        )


# ---------------------------------------------------------------------------
# Alignment iteration limit awareness
# ---------------------------------------------------------------------------


class TestAlignmentIterationLimitAwareness:
    """The definition must be aware of the alignment iteration limit."""

    def test_mentions_iteration(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        assert "iteration" in lower, (
            "Definition must reference iteration limit awareness for alignment cycles"
        )

    def test_mentions_limit(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        assert "limit" in lower, (
            "Definition must reference a limit in the context of alignment iterations"
        )


# ---------------------------------------------------------------------------
# Lessons learned review requirement
# ---------------------------------------------------------------------------


class TestLessonsLearnedReviewRequirement:
    """The definition must require a lessons learned review."""

    def test_mentions_lessons_learned(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        has_lessons = "lessons" in lower and "learned" in lower
        assert has_lessons, (
            "Definition must reference lessons learned review requirement"
        )


# ---------------------------------------------------------------------------
# Alignment concept -- core identity of the agent
# ---------------------------------------------------------------------------


class TestAlignmentConcept:
    """The definition must be centered around alignment checking."""

    def test_mentions_alignment(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        assert "alignment" in lower, (
            "Definition must reference alignment as the core task of this agent"
        )

    def test_mentions_blueprint(self):
        lower = _lower(BLUEPRINT_CHECKER_DEFINITION)
        assert "blueprint" in lower, (
            "Definition must reference blueprint since this is the blueprint checker"
        )

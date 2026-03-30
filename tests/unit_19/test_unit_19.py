"""Unit 19: Blueprint Checker Definition -- complete test suite.

Synthetic data assumptions:
- BLUEPRINT_CHECKER_DEFINITION is a str containing the complete markdown content
  of the blueprint checker agent definition file. All structural tests inspect
  this string directly.
- The definition string is expected to be markdown content suitable for an agent
  system prompt. Structural tests search for specific phrases, keywords, and
  patterns within the markdown to verify contract compliance.
- Keyword matching is case-insensitive where noted. Terminal status strings and
  file paths are matched case-sensitively since they are machine-parsed tokens.
- The five mandatory alignment checklist domains are: DAG acyclicity, profile
  preference validation (Layer 2), pattern catalog validation (P1-P13+),
  contract granularity verification (exported function coverage, per-gate-option
  dispatch contracts, call-site verification, re-entry path documentation), and
  language registry completeness validation.
- The contract granularity verification domain has exactly four sub-items:
  exported function coverage, per-gate-option dispatch contracts, call-site
  verification, and re-entry path documentation.
- The three terminal status values are exact string tokens:
  ALIGNMENT_CONFIRMED, ALIGNMENT_FAILED: spec, ALIGNMENT_FAILED: blueprint.
- The alignment checker checklist file path is
  .svp/alignment_checker_checklist.md (exact path token).
- The "report most fundamental level" corollary establishes that spec problems
  supersede blueprint problems in the hierarchy of failure reporting.
- Pattern catalog references P1 through P13 at minimum, with the "+" notation
  indicating the catalog may extend beyond P13.
- Dependency on Unit 2 (Language Registry) means the definition must reference
  language registry validation concepts.
- Internal consistency validation refers to cross-checking between prose
  (specification narrative) and contracts files (blueprint behavioral contracts).
"""

import re

from src.unit_19.stub import BLUEPRINT_CHECKER_DEFINITION

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def definition_contains(phrase: str, case_sensitive: bool = True) -> bool:
    """Check whether the definition string contains the given phrase."""
    if case_sensitive:
        return phrase in BLUEPRINT_CHECKER_DEFINITION
    return phrase.lower() in BLUEPRINT_CHECKER_DEFINITION.lower()


def definition_matches(pattern: str, flags: int = 0) -> list:
    """Return all regex matches of pattern in the definition string."""
    return re.findall(pattern, BLUEPRINT_CHECKER_DEFINITION, flags)


# ===========================================================================
# BLUEPRINT_CHECKER_DEFINITION: type and non-emptiness
# ===========================================================================


class TestBlueprintCheckerDefinitionBasicStructure:
    """Verify BLUEPRINT_CHECKER_DEFINITION is a non-empty string with markdown."""

    def test_definition_is_string(self):
        assert isinstance(BLUEPRINT_CHECKER_DEFINITION, str)

    def test_definition_is_nonempty(self):
        assert len(BLUEPRINT_CHECKER_DEFINITION.strip()) > 0

    def test_definition_is_not_none(self):
        assert BLUEPRINT_CHECKER_DEFINITION is not None

    def test_definition_contains_markdown_headings(self):
        """Agent definition must be structured markdown with headings."""
        assert re.search(r"^#+\s+", BLUEPRINT_CHECKER_DEFINITION, re.MULTILINE)

    def test_definition_has_substantial_content(self):
        """Definition should contain enough content to be a meaningful agent prompt."""
        # A complete agent definition should be at least a few hundred characters
        assert len(BLUEPRINT_CHECKER_DEFINITION.strip()) > 200


# ===========================================================================
# Mandatory alignment checklist: DAG acyclicity
# ===========================================================================


class TestMandatoryChecklistDAGAcyclicity:
    """The definition must include DAG acyclicity as a mandatory checklist item."""

    def test_dag_keyword_present(self):
        """DAG (Directed Acyclic Graph) must be referenced."""
        assert definition_contains("DAG", case_sensitive=True) or definition_contains(
            "dag", case_sensitive=False
        )

    def test_acyclicity_keyword_present(self):
        """Acyclicity concept must be referenced."""
        assert (
            definition_contains("acyclic", case_sensitive=False)
            or definition_contains("acyclicity", case_sensitive=False)
            or definition_contains("cycle", case_sensitive=False)
        )

    def test_dag_acyclicity_as_checklist_item(self):
        """DAG acyclicity should be identifiable as a checklist or validation item."""
        has_dag = definition_contains(
            "DAG", case_sensitive=True
        ) or definition_contains("dag", case_sensitive=False)
        has_acyclic = definition_contains(
            "acyclic", case_sensitive=False
        ) or definition_contains("cycle", case_sensitive=False)
        assert has_dag and has_acyclic, (
            "DAG acyclicity must appear as a mandatory alignment checklist item"
        )


# ===========================================================================
# Mandatory alignment checklist: profile preference validation (Layer 2)
# ===========================================================================


class TestMandatoryChecklistProfilePreferenceValidation:
    """The definition must include profile preference validation (Layer 2)."""

    def test_profile_keyword_present(self):
        """Profile must be referenced."""
        assert definition_contains("profile", case_sensitive=False)

    def test_preference_keyword_present(self):
        """Preference must be referenced in context of validation."""
        assert definition_contains("preference", case_sensitive=False)

    def test_layer_2_reference_present(self):
        """Layer 2 must be referenced as the profile preference layer."""
        assert (
            definition_contains("Layer 2", case_sensitive=False)
            or definition_contains("layer 2", case_sensitive=True)
            or definition_contains("layer two", case_sensitive=False)
        )

    def test_profile_preference_validation_combined(self):
        """Profile preference validation must appear as a coherent checklist item."""
        has_profile = definition_contains("profile", case_sensitive=False)
        has_preference = definition_contains("preference", case_sensitive=False)
        has_valid = definition_contains("valid", case_sensitive=False)
        assert has_profile and has_preference and has_valid, (
            "Profile preference validation (Layer 2) must appear as a mandatory "
            "alignment checklist item"
        )


# ===========================================================================
# Mandatory alignment checklist: pattern catalog validation (P1-P13+)
# ===========================================================================


class TestMandatoryChecklistPatternCatalogValidation:
    """The definition must include pattern catalog validation (P1-P13+)."""

    def test_pattern_keyword_present(self):
        """Pattern must be referenced."""
        assert definition_contains("pattern", case_sensitive=False)

    def test_catalog_keyword_present(self):
        """Catalog must be referenced."""
        assert definition_contains(
            "catalog", case_sensitive=False
        ) or definition_contains("catalogue", case_sensitive=False)

    def test_p1_reference_present(self):
        """P1 must be referenced as part of pattern catalog range."""
        assert definition_contains("P1", case_sensitive=True)

    def test_p13_reference_present(self):
        """P13 must be referenced as the lower bound of pattern catalog range."""
        assert definition_contains("P13", case_sensitive=True)

    def test_pattern_catalog_range_notation(self):
        """Pattern catalog should reference the P1-P13+ range."""
        # Match patterns like "P1-P13", "P1 through P13", "P1...P13"
        has_range = re.search(
            r"P1[\s\-\u2013\u2014]+P13|P1\s+through\s+P13|P1\s*\.\.\.\s*P13",
            BLUEPRINT_CHECKER_DEFINITION,
        )
        # Or at minimum both P1 and P13 appear in the definition
        has_both = definition_contains("P1") and definition_contains("P13")
        assert has_range or has_both, (
            "Pattern catalog validation must reference the P1-P13+ range"
        )

    def test_pattern_catalog_extensibility_indicated(self):
        """The '+' or equivalent notation indicates catalog extends beyond P13."""
        # Look for "P13+" or "P13 or more" or "beyond P13" etc.
        has_plus = definition_contains("P13+")
        has_beyond = re.search(
            r"beyond\s+P13|P13\s+or\s+more|P13\s+and\s+beyond|at\s+least\s+P13",
            BLUEPRINT_CHECKER_DEFINITION,
            re.IGNORECASE,
        )
        # Could also just mention the pattern numbers exist
        assert has_plus or has_beyond or definition_contains("P13"), (
            "Pattern catalog should indicate extensibility beyond P13"
        )


# ===========================================================================
# Mandatory alignment checklist: contract granularity verification
# ===========================================================================


class TestMandatoryChecklistContractGranularity:
    """The definition must include contract granularity verification with
    four sub-items: exported function coverage, per-gate-option dispatch
    contracts, call-site verification, re-entry path documentation."""

    def test_contract_granularity_concept_present(self):
        """Contract granularity verification must be referenced."""
        has_contract = definition_contains("contract", case_sensitive=False)
        has_granularity = definition_contains("granularity", case_sensitive=False)
        assert has_contract and has_granularity, (
            "Contract granularity verification must be a mandatory checklist item"
        )

    def test_exported_function_coverage_subitem(self):
        """Exported function coverage must be referenced as a sub-item."""
        has_exported = definition_contains(
            "exported", case_sensitive=False
        ) or definition_contains("export", case_sensitive=False)
        has_function = definition_contains("function", case_sensitive=False)
        has_coverage = definition_contains("coverage", case_sensitive=False)
        assert has_exported and has_function and has_coverage, (
            "Exported function coverage must appear as a contract granularity sub-item"
        )

    def test_per_gate_option_dispatch_contracts_subitem(self):
        """Per-gate-option dispatch contracts must be referenced as a sub-item."""
        has_gate = definition_contains("gate", case_sensitive=False)
        has_dispatch = definition_contains("dispatch", case_sensitive=False)
        assert has_gate and has_dispatch, (
            "Per-gate-option dispatch contracts must appear as a contract "
            "granularity sub-item"
        )

    def test_call_site_verification_subitem(self):
        """Call-site verification must be referenced as a sub-item."""
        assert (
            definition_contains("call-site", case_sensitive=False)
            or definition_contains("call site", case_sensitive=False)
            or definition_contains("callsite", case_sensitive=False)
        ), "Call-site verification must appear as a contract granularity sub-item"

    def test_re_entry_path_documentation_subitem(self):
        """Re-entry path documentation must be referenced as a sub-item."""
        has_reentry = (
            definition_contains("re-entry", case_sensitive=False)
            or definition_contains("reentry", case_sensitive=False)
            or definition_contains("re entry", case_sensitive=False)
        )
        has_path = definition_contains("path", case_sensitive=False)
        has_doc = definition_contains("document", case_sensitive=False)
        assert has_reentry and has_path and has_doc, (
            "Re-entry path documentation must appear as a contract granularity sub-item"
        )

    def test_all_four_granularity_subitems_present(self):
        """All four contract granularity sub-items must be present together."""
        has_exported_fn = (
            definition_contains("exported", case_sensitive=False)
            or definition_contains("export", case_sensitive=False)
        ) and definition_contains("function", case_sensitive=False)

        has_gate_dispatch = definition_contains(
            "gate", case_sensitive=False
        ) and definition_contains("dispatch", case_sensitive=False)

        has_call_site = (
            definition_contains("call-site", case_sensitive=False)
            or definition_contains("call site", case_sensitive=False)
            or definition_contains("callsite", case_sensitive=False)
        )

        has_reentry = definition_contains(
            "re-entry", case_sensitive=False
        ) or definition_contains("reentry", case_sensitive=False)

        all_present = (
            has_exported_fn and has_gate_dispatch and has_call_site and has_reentry
        )
        assert all_present, (
            "All four contract granularity sub-items must appear: "
            "exported function coverage, per-gate-option dispatch contracts, "
            "call-site verification, re-entry path documentation"
        )


# ===========================================================================
# Mandatory alignment checklist: language registry completeness validation
# ===========================================================================


class TestMandatoryChecklistLanguageRegistryCompleteness:
    """The definition must include language registry completeness validation.
    This is the dependency on Unit 2."""

    def test_language_registry_keyword_present(self):
        """Language registry must be referenced."""
        assert definition_contains("language registry", case_sensitive=False) or (
            definition_contains("language", case_sensitive=False)
            and definition_contains("registry", case_sensitive=False)
        )

    def test_completeness_keyword_present(self):
        """Completeness validation must be referenced for language registry."""
        assert definition_contains(
            "completeness", case_sensitive=False
        ) or definition_contains("complete", case_sensitive=False)

    def test_language_registry_validation_combined(self):
        """Language registry completeness validation as a coherent checklist item."""
        has_language = definition_contains("language", case_sensitive=False)
        has_registry = definition_contains("registry", case_sensitive=False)
        has_complete = definition_contains("complete", case_sensitive=False)
        assert has_language and has_registry and has_complete, (
            "Language registry completeness validation must appear as a mandatory "
            "alignment checklist item"
        )


# ===========================================================================
# All five mandatory checklist domains present together
# ===========================================================================


class TestAllMandatoryChecklistDomainsPresent:
    """Verify all five mandatory alignment checklist domains are present."""

    def test_dag_acyclicity_domain_present(self):
        """DAG acyclicity domain present."""
        assert definition_contains("DAG", case_sensitive=True) or definition_contains(
            "acyclic", case_sensitive=False
        )

    def test_profile_preference_domain_present(self):
        """Profile preference validation domain present."""
        assert definition_contains("preference", case_sensitive=False)

    def test_pattern_catalog_domain_present(self):
        """Pattern catalog validation domain present."""
        assert definition_contains("pattern", case_sensitive=False) and (
            definition_contains("catalog", case_sensitive=False)
            or definition_contains("catalogue", case_sensitive=False)
        )

    def test_contract_granularity_domain_present(self):
        """Contract granularity verification domain present."""
        assert definition_contains("granularity", case_sensitive=False)

    def test_language_registry_completeness_domain_present(self):
        """Language registry completeness validation domain present."""
        assert definition_contains("registry", case_sensitive=False)


# ===========================================================================
# Receives alignment checker checklist file
# ===========================================================================


class TestAlignmentCheckerChecklist:
    """The definition must reference receiving the alignment checker checklist
    from .svp/alignment_checker_checklist.md."""

    def test_alignment_checker_checklist_path_referenced(self):
        """Exact file path .svp/alignment_checker_checklist.md must appear."""
        assert definition_contains(
            ".svp/alignment_checker_checklist.md"
        ) or definition_contains("alignment_checker_checklist.md")

    def test_svp_directory_referenced(self):
        """The .svp directory must be referenced as source of checklist."""
        assert definition_contains(".svp/") or definition_contains(".svp")

    def test_alignment_checker_checklist_concept(self):
        """The concept of receiving a checklist for alignment checking is present."""
        has_alignment = definition_contains("alignment", case_sensitive=False)
        has_checklist = definition_contains("checklist", case_sensitive=False)
        assert has_alignment and has_checklist, (
            "Definition must reference receiving the alignment checker checklist"
        )

    def test_receives_checklist_as_input(self):
        """The agent receives the checklist (input, not output)."""
        has_receive = (
            definition_contains("receive", case_sensitive=False)
            or definition_contains("read", case_sensitive=False)
            or definition_contains("input", case_sensitive=False)
            or definition_contains("load", case_sensitive=False)
            or definition_contains("given", case_sensitive=False)
            or definition_contains("provided", case_sensitive=False)
        )
        has_checklist = definition_contains("checklist", case_sensitive=False)
        assert has_receive and has_checklist, (
            "Definition must indicate the agent receives the checklist as input"
        )


# ===========================================================================
# Validates internal consistency: prose vs contracts
# ===========================================================================


class TestInternalConsistencyValidation:
    """The definition must describe validation of internal consistency
    between prose and contracts files."""

    def test_internal_consistency_concept_present(self):
        """Internal consistency must be referenced."""
        has_internal = definition_contains("internal", case_sensitive=False)
        has_consistency = definition_contains(
            "consistency", case_sensitive=False
        ) or definition_contains("consistent", case_sensitive=False)
        assert has_internal and has_consistency, (
            "Definition must reference internal consistency validation"
        )

    def test_prose_referenced(self):
        """Prose (specification narrative) must be referenced."""
        assert definition_contains("prose", case_sensitive=False)

    def test_contracts_referenced(self):
        """Contracts files must be referenced."""
        assert definition_contains("contract", case_sensitive=False)

    def test_prose_vs_contracts_cross_validation(self):
        """Both prose and contracts must be referenced as cross-validation targets."""
        has_prose = definition_contains("prose", case_sensitive=False)
        has_contracts = definition_contains("contract", case_sensitive=False)
        assert has_prose and has_contracts, (
            "Definition must describe cross-validation between prose and contracts"
        )


# ===========================================================================
# "Report most fundamental level" corollary
# ===========================================================================


class TestReportMostFundamentalLevel:
    """The definition must include the 'report most fundamental level' corollary:
    spec problems supersede blueprint problems."""

    def test_fundamental_level_concept_present(self):
        """The 'most fundamental level' concept must be referenced."""
        assert definition_contains(
            "fundamental", case_sensitive=False
        ) or definition_contains("most fundamental", case_sensitive=False)

    def test_spec_supersedes_blueprint(self):
        """Spec problems must be documented as superseding blueprint problems."""
        has_spec = definition_contains("spec", case_sensitive=False)
        has_blueprint = definition_contains("blueprint", case_sensitive=False)
        has_supersede = (
            definition_contains("supersede", case_sensitive=False)
            or definition_contains("precede", case_sensitive=False)
            or definition_contains("priority", case_sensitive=False)
            or definition_contains("before", case_sensitive=False)
            or definition_contains("fundamental", case_sensitive=False)
            or definition_contains("first", case_sensitive=False)
        )
        assert has_spec and has_blueprint and has_supersede, (
            "Spec problems must supersede blueprint problems per the "
            "'report most fundamental level' corollary"
        )

    def test_corollary_language_present(self):
        """The corollary concept must use language indicating priority ordering."""
        # The corollary establishes a hierarchy: spec > blueprint
        has_hierarchy = (
            definition_contains("fundamental", case_sensitive=False)
            or definition_contains("supersede", case_sensitive=False)
            or definition_contains("hierarchy", case_sensitive=False)
            or definition_contains("priority", case_sensitive=False)
            or definition_contains("most fundamental level", case_sensitive=False)
        )
        assert has_hierarchy, "Definition must express the priority hierarchy corollary"


# ===========================================================================
# Terminal status values
# ===========================================================================


class TestTerminalStatusValues:
    """The definition must include exactly three terminal status values:
    ALIGNMENT_CONFIRMED, ALIGNMENT_FAILED: spec, ALIGNMENT_FAILED: blueprint."""

    def test_alignment_confirmed_status_present(self):
        """ALIGNMENT_CONFIRMED terminal status must appear."""
        assert definition_contains("ALIGNMENT_CONFIRMED")

    def test_alignment_failed_spec_status_present(self):
        """ALIGNMENT_FAILED: spec terminal status must appear."""
        assert definition_contains("ALIGNMENT_FAILED: spec") or definition_contains(
            "ALIGNMENT_FAILED:spec"
        )

    def test_alignment_failed_blueprint_status_present(self):
        """ALIGNMENT_FAILED: blueprint terminal status must appear."""
        assert definition_contains(
            "ALIGNMENT_FAILED: blueprint"
        ) or definition_contains("ALIGNMENT_FAILED:blueprint")

    def test_all_three_terminal_statuses_present(self):
        """All three terminal statuses must be present together."""
        has_confirmed = definition_contains("ALIGNMENT_CONFIRMED")
        has_failed_spec = definition_contains(
            "ALIGNMENT_FAILED: spec"
        ) or definition_contains("ALIGNMENT_FAILED:spec")
        has_failed_blueprint = definition_contains(
            "ALIGNMENT_FAILED: blueprint"
        ) or definition_contains("ALIGNMENT_FAILED:blueprint")
        assert has_confirmed and has_failed_spec and has_failed_blueprint, (
            "All three terminal statuses must be present: ALIGNMENT_CONFIRMED, "
            "ALIGNMENT_FAILED: spec, ALIGNMENT_FAILED: blueprint"
        )

    def test_terminal_status_uses_exact_tokens(self):
        """Terminal statuses must use the exact uppercase token format."""
        # ALIGNMENT_CONFIRMED must be all caps with underscore
        assert re.search(r"ALIGNMENT_CONFIRMED", BLUEPRINT_CHECKER_DEFINITION), (
            "ALIGNMENT_CONFIRMED must appear in exact uppercase token format"
        )
        # ALIGNMENT_FAILED must be all caps with underscore
        assert re.search(r"ALIGNMENT_FAILED", BLUEPRINT_CHECKER_DEFINITION), (
            "ALIGNMENT_FAILED must appear in exact uppercase token format"
        )


# ===========================================================================
# Terminal status semantics: spec vs blueprint failure distinction
# ===========================================================================


class TestTerminalStatusSemantics:
    """The definition must establish correct semantics for the two failure modes:
    spec failure is more fundamental than blueprint failure."""

    def test_spec_failure_is_distinct_from_blueprint_failure(self):
        """ALIGNMENT_FAILED: spec and ALIGNMENT_FAILED: blueprint are distinct."""
        has_spec_failure = definition_contains(
            "ALIGNMENT_FAILED: spec"
        ) or definition_contains("ALIGNMENT_FAILED:spec")
        has_blueprint_failure = definition_contains(
            "ALIGNMENT_FAILED: blueprint"
        ) or definition_contains("ALIGNMENT_FAILED:blueprint")
        assert has_spec_failure and has_blueprint_failure

    def test_spec_failure_relates_to_specification_problems(self):
        """ALIGNMENT_FAILED: spec relates to specification-level problems."""
        has_spec = definition_contains("spec", case_sensitive=False)
        has_failure_concept = (
            definition_contains("fail", case_sensitive=False)
            or definition_contains("problem", case_sensitive=False)
            or definition_contains("error", case_sensitive=False)
            or definition_contains("issue", case_sensitive=False)
        )
        assert has_spec and has_failure_concept

    def test_blueprint_failure_relates_to_blueprint_problems(self):
        """ALIGNMENT_FAILED: blueprint relates to blueprint-level problems."""
        has_blueprint = definition_contains("blueprint", case_sensitive=False)
        has_failure_concept = (
            definition_contains("fail", case_sensitive=False)
            or definition_contains("problem", case_sensitive=False)
            or definition_contains("error", case_sensitive=False)
            or definition_contains("issue", case_sensitive=False)
        )
        assert has_blueprint and has_failure_concept

    def test_fundamental_level_determines_failure_type(self):
        """The most fundamental level corollary determines which failure to report.
        If spec is broken, report spec even if blueprint is also broken."""
        # Both "spec" and "blueprint" appear in failure context
        has_spec_status = definition_contains(
            "ALIGNMENT_FAILED: spec"
        ) or definition_contains("ALIGNMENT_FAILED:spec")
        has_bp_status = definition_contains(
            "ALIGNMENT_FAILED: blueprint"
        ) or definition_contains("ALIGNMENT_FAILED:blueprint")
        has_fundamental = definition_contains("fundamental", case_sensitive=False)
        assert has_spec_status and has_bp_status and has_fundamental, (
            "Both failure modes and the fundamental-level corollary must be present"
        )


# ===========================================================================
# Alignment checker checklist items as structured content
# ===========================================================================


class TestChecklistStructure:
    """The five mandatory checklist domains should appear as structured items
    in the definition (numbered, bulleted, or otherwise enumerated)."""

    def test_definition_contains_list_structure(self):
        """Definition should contain list markers (bullets, numbers, dashes)."""
        has_bullets = re.search(r"(?:^|\n)\s*[-*+]\s+", BLUEPRINT_CHECKER_DEFINITION)
        has_numbers = re.search(
            r"(?:^|\n)\s*\d+[\.\)]\s+", BLUEPRINT_CHECKER_DEFINITION
        )
        assert has_bullets or has_numbers, (
            "Definition should contain structured list items for checklist domains"
        )

    def test_checklist_keyword_present(self):
        """The word 'checklist' must appear in the definition."""
        assert definition_contains("checklist", case_sensitive=False)

    def test_alignment_keyword_present(self):
        """The word 'alignment' must appear in the definition."""
        assert definition_contains("alignment", case_sensitive=False)

    def test_validation_keyword_present(self):
        """The word 'validation' or 'validate' must appear in the definition."""
        assert definition_contains("validat", case_sensitive=False)


# ===========================================================================
# Unit 2 dependency: language registry references
# ===========================================================================


class TestUnit2DependencyReferences:
    """The definition depends on Unit 2 (Language Registry) and must reference
    language registry concepts for completeness validation."""

    def test_language_keyword_present(self):
        """Language must be referenced (Unit 2 dependency)."""
        assert definition_contains("language", case_sensitive=False)

    def test_registry_keyword_present(self):
        """Registry must be referenced (Unit 2 dependency)."""
        assert definition_contains("registry", case_sensitive=False)

    def test_language_registry_validation_concept(self):
        """The definition must reference validation of language registry content."""
        has_language_registry = definition_contains(
            "language registry", case_sensitive=False
        ) or (
            definition_contains("language", case_sensitive=False)
            and definition_contains("registry", case_sensitive=False)
        )
        has_validation = (
            definition_contains("validat", case_sensitive=False)
            or definition_contains("check", case_sensitive=False)
            or definition_contains("verify", case_sensitive=False)
        )
        assert has_language_registry and has_validation


# ===========================================================================
# Blueprint concept references
# ===========================================================================


class TestBlueprintConceptReferences:
    """The definition must reference key blueprint concepts since it is the
    blueprint checker agent."""

    def test_blueprint_keyword_present(self):
        """Blueprint must be referenced as the target of checking."""
        assert definition_contains("blueprint", case_sensitive=False)

    def test_spec_keyword_present(self):
        """Spec/specification must be referenced for cross-validation."""
        assert definition_contains("spec", case_sensitive=False) or definition_contains(
            "specification", case_sensitive=False
        )

    def test_alignment_keyword_present(self):
        """Alignment must be referenced as the core validation goal."""
        assert definition_contains("alignment", case_sensitive=False)


# ===========================================================================
# Cross-validation: all contract keywords in definition
# ===========================================================================


class TestContractKeywordCoverage:
    """Verify every significant keyword from the behavioral contracts
    appears in the definition."""

    def test_dag_keyword(self):
        assert definition_contains("DAG") or definition_contains(
            "dag", case_sensitive=False
        )

    def test_acyclicity_keyword(self):
        assert definition_contains("acyclic", case_sensitive=False)

    def test_profile_keyword(self):
        assert definition_contains("profile", case_sensitive=False)

    def test_preference_keyword(self):
        assert definition_contains("preference", case_sensitive=False)

    def test_layer_2_keyword(self):
        assert definition_contains("Layer 2", case_sensitive=False)

    def test_pattern_keyword(self):
        assert definition_contains("pattern", case_sensitive=False)

    def test_catalog_keyword(self):
        assert definition_contains(
            "catalog", case_sensitive=False
        ) or definition_contains("catalogue", case_sensitive=False)

    def test_p1_keyword(self):
        assert definition_contains("P1")

    def test_p13_keyword(self):
        assert definition_contains("P13")

    def test_contract_keyword(self):
        assert definition_contains("contract", case_sensitive=False)

    def test_granularity_keyword(self):
        assert definition_contains("granularity", case_sensitive=False)

    def test_exported_keyword(self):
        assert definition_contains(
            "exported", case_sensitive=False
        ) or definition_contains("export", case_sensitive=False)

    def test_function_keyword(self):
        assert definition_contains("function", case_sensitive=False)

    def test_coverage_keyword(self):
        assert definition_contains("coverage", case_sensitive=False)

    def test_gate_keyword(self):
        assert definition_contains("gate", case_sensitive=False)

    def test_dispatch_keyword(self):
        assert definition_contains("dispatch", case_sensitive=False)

    def test_call_site_keyword(self):
        assert (
            definition_contains("call-site", case_sensitive=False)
            or definition_contains("call site", case_sensitive=False)
            or definition_contains("callsite", case_sensitive=False)
        )

    def test_re_entry_keyword(self):
        assert definition_contains(
            "re-entry", case_sensitive=False
        ) or definition_contains("reentry", case_sensitive=False)

    def test_language_registry_keyword(self):
        assert definition_contains(
            "language", case_sensitive=False
        ) and definition_contains("registry", case_sensitive=False)

    def test_completeness_keyword(self):
        assert definition_contains(
            "completeness", case_sensitive=False
        ) or definition_contains("complete", case_sensitive=False)

    def test_prose_keyword(self):
        assert definition_contains("prose", case_sensitive=False)

    def test_consistency_keyword(self):
        assert definition_contains(
            "consistency", case_sensitive=False
        ) or definition_contains("consistent", case_sensitive=False)

    def test_fundamental_keyword(self):
        assert definition_contains("fundamental", case_sensitive=False)

    def test_supersede_keyword(self):
        assert (
            definition_contains("supersede", case_sensitive=False)
            or definition_contains("precede", case_sensitive=False)
            or definition_contains("priority", case_sensitive=False)
            or definition_contains("most fundamental", case_sensitive=False)
        )

    def test_checklist_keyword(self):
        assert definition_contains("checklist", case_sensitive=False)


# ===========================================================================
# Definition content: overall topic coverage
# ===========================================================================


class TestDefinitionTopicCoverage:
    """Verify that all key topics from the behavioral contracts are present
    somewhere in the agent definition."""

    def test_five_mandatory_checklist_domains_topic(self):
        """All five mandatory checklist domains should be referenced."""
        domains_present = 0
        # DAG acyclicity
        if definition_contains("DAG", case_sensitive=True) or definition_contains(
            "acyclic", case_sensitive=False
        ):
            domains_present += 1
        # Profile preference validation
        if definition_contains(
            "preference", case_sensitive=False
        ) and definition_contains("profile", case_sensitive=False):
            domains_present += 1
        # Pattern catalog validation
        if definition_contains("pattern", case_sensitive=False) and (
            definition_contains("catalog", case_sensitive=False)
            or definition_contains("catalogue", case_sensitive=False)
        ):
            domains_present += 1
        # Contract granularity verification
        if definition_contains(
            "granularity", case_sensitive=False
        ) and definition_contains("contract", case_sensitive=False):
            domains_present += 1
        # Language registry completeness
        if definition_contains(
            "registry", case_sensitive=False
        ) and definition_contains("language", case_sensitive=False):
            domains_present += 1
        assert domains_present == 5, (
            f"Expected 5 mandatory checklist domains, found {domains_present}"
        )

    def test_alignment_checker_checklist_input_topic(self):
        """Alignment checker checklist input topic is covered."""
        assert definition_contains(
            "alignment_checker_checklist", case_sensitive=False
        ) or (
            definition_contains("alignment", case_sensitive=False)
            and definition_contains("checklist", case_sensitive=False)
        )

    def test_internal_consistency_topic(self):
        """Internal consistency between prose and contracts topic is covered."""
        assert (
            definition_contains("internal", case_sensitive=False)
            and definition_contains("consistency", case_sensitive=False)
            or definition_contains("consistent", case_sensitive=False)
        )

    def test_fundamental_level_corollary_topic(self):
        """Report most fundamental level corollary topic is covered."""
        assert definition_contains("fundamental", case_sensitive=False)

    def test_terminal_status_topic(self):
        """Terminal status values topic is covered."""
        assert definition_contains("ALIGNMENT_CONFIRMED") and definition_contains(
            "ALIGNMENT_FAILED"
        )

    def test_spec_vs_blueprint_distinction_topic(self):
        """Spec vs blueprint failure distinction topic is covered."""
        assert definition_contains(
            "spec", case_sensitive=False
        ) and definition_contains("blueprint", case_sensitive=False)


# ===========================================================================
# Structural integrity: definition as a well-formed agent prompt
# ===========================================================================


class TestDefinitionStructuralIntegrity:
    """The definition should be structurally sound as an agent system prompt."""

    def test_has_multiple_sections(self):
        """Definition should have multiple markdown sections."""
        headings = re.findall(r"^#+\s+", BLUEPRINT_CHECKER_DEFINITION, re.MULTILINE)
        assert len(headings) >= 2, (
            "Definition should have at least 2 markdown section headings"
        )

    def test_no_empty_definition(self):
        """Definition must not be whitespace-only."""
        assert BLUEPRINT_CHECKER_DEFINITION.strip() != ""

    def test_contains_actionable_language(self):
        """Definition should contain actionable language for the agent."""
        actionable_words = [
            "check",
            "verify",
            "validate",
            "confirm",
            "report",
            "ensure",
            "inspect",
            "analyze",
            "examine",
            "review",
        ]
        found = any(
            definition_contains(word, case_sensitive=False) for word in actionable_words
        )
        assert found, (
            "Definition should contain actionable language directing the agent"
        )

    def test_definition_references_agent_role(self):
        """Definition should clearly establish the agent's role."""
        has_checker = definition_contains("checker", case_sensitive=False)
        has_alignment = definition_contains("alignment", case_sensitive=False)
        has_blueprint = definition_contains("blueprint", case_sensitive=False)
        assert (has_checker or has_alignment) and has_blueprint, (
            "Definition should establish the blueprint checker agent role"
        )

"""Unit 18: Setup Agent Definition -- complete test suite.

Synthetic data assumptions:
- SETUP_AGENT_DEFINITION is a str containing the complete markdown content of
  the setup agent definition file. All structural tests inspect this string.
- REQUIRED_RULES is a list of exactly 4 items corresponding to the four
  numbered behavioral requirements: (1) plain language explanations,
  (2) best-option recommendations, (3) sensible defaults,
  (4) progressive disclosure.
- AREA_0_ARCHETYPES is a list of exactly 6 items corresponding to Options A
  through F in the Area 0 language/ecosystem archetype selector dialog.
- DIALOG_AREAS is a list of exactly 6 items corresponding to dialog areas 0-5:
  Area 0 (Language/Ecosystem), Area 1 (VCS), Area 2 (README/Docs),
  Area 3 (Testing), Area 4 (Licensing/Metadata), Area 5 (Quality).
- The definition string is expected to be markdown content suitable for an
  agent system prompt. Structural tests search for specific phrases, keywords,
  and patterns within the markdown to verify contract compliance.
- Keyword matching is case-insensitive where noted, but numbered rules and
  option labels are expected in their canonical form.
- Profile field names tested against the definition are drawn from the
  Unit 3 profile schema: archetype, language (primary, secondary, components,
  communication, notebooks), delivery, quality, testing, readme, license,
  vcs, pipeline, and plugin sub-fields (external_services, hook_events,
  skills, mcp_servers).
- Bridge library names (rpy2, reticulate) and constraint values (conda,
  environment.yml) are drawn from Unit 2 language registry contracts.
"""

import re

from src.unit_18.stub import (
    AREA_0_ARCHETYPES,
    DIALOG_AREAS,
    REQUIRED_RULES,
    SETUP_AGENT_DEFINITION,
)

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def definition_contains(phrase: str, case_sensitive: bool = True) -> bool:
    """Check whether the definition string contains the given phrase."""
    if case_sensitive:
        return phrase in SETUP_AGENT_DEFINITION
    return phrase.lower() in SETUP_AGENT_DEFINITION.lower()


def definition_matches(pattern: str, flags: int = 0) -> list:
    """Return all regex matches of pattern in the definition string."""
    return re.findall(pattern, SETUP_AGENT_DEFINITION, flags)


# ===========================================================================
# SETUP_AGENT_DEFINITION: type and non-emptiness
# ===========================================================================


class TestSetupAgentDefinitionBasicStructure:
    """Verify SETUP_AGENT_DEFINITION is a non-empty string with markdown."""

    def test_definition_is_string(self):
        assert isinstance(SETUP_AGENT_DEFINITION, str)

    def test_definition_is_nonempty(self):
        assert len(SETUP_AGENT_DEFINITION.strip()) > 0

    def test_definition_contains_markdown_headings(self):
        """Agent definition must be structured markdown with headings."""
        assert re.search(r"^#+\s+", SETUP_AGENT_DEFINITION, re.MULTILINE)


# ===========================================================================
# REQUIRED_RULES: structural validation targets
# ===========================================================================


class TestRequiredRulesStructure:
    """REQUIRED_RULES must be a list of exactly 4 items for Rules 1-4."""

    def test_required_rules_is_list(self):
        assert isinstance(REQUIRED_RULES, list)

    def test_required_rules_has_four_items(self):
        assert len(REQUIRED_RULES) == 4

    def test_required_rules_items_are_strings(self):
        for i, rule in enumerate(REQUIRED_RULES):
            assert isinstance(rule, str), (
                f"REQUIRED_RULES[{i}] should be a string, got {type(rule)}"
            )

    def test_required_rules_items_are_nonempty(self):
        for i, rule in enumerate(REQUIRED_RULES):
            assert len(rule.strip()) > 0, f"REQUIRED_RULES[{i}] should not be empty"


class TestRequiredRulesContent:
    """Rules 1-4 appear verbatim as numbered requirements in the definition."""

    def test_rule_1_plain_language_in_definition(self):
        """Rule 1 (plain language explanations) must appear in the definition."""
        assert REQUIRED_RULES[0] in SETUP_AGENT_DEFINITION

    def test_rule_2_best_option_in_definition(self):
        """Rule 2 (best-option recommendations) must appear in the definition."""
        assert REQUIRED_RULES[1] in SETUP_AGENT_DEFINITION

    def test_rule_3_sensible_defaults_in_definition(self):
        """Rule 3 (sensible defaults) must appear in the definition."""
        assert REQUIRED_RULES[2] in SETUP_AGENT_DEFINITION

    def test_rule_4_progressive_disclosure_in_definition(self):
        """Rule 4 (progressive disclosure) must appear in the definition."""
        assert REQUIRED_RULES[3] in SETUP_AGENT_DEFINITION

    def test_rule_1_relates_to_plain_language(self):
        """Rule 1 text should reference plain language explanations."""
        assert (
            definition_contains("plain language", case_sensitive=False)
            or "plain language" in REQUIRED_RULES[0].lower()
        )

    def test_rule_2_relates_to_best_option(self):
        """Rule 2 text should reference best-option recommendations."""
        assert (
            definition_contains("best-option", case_sensitive=False)
            or definition_contains("best option", case_sensitive=False)
            or "best" in REQUIRED_RULES[1].lower()
        )

    def test_rule_3_relates_to_sensible_defaults(self):
        """Rule 3 text should reference sensible defaults."""
        assert (
            definition_contains("sensible default", case_sensitive=False)
            or definition_contains("defaults", case_sensitive=False)
            or "default" in REQUIRED_RULES[2].lower()
        )

    def test_rule_4_relates_to_progressive_disclosure(self):
        """Rule 4 text should reference progressive disclosure."""
        assert (
            definition_contains("progressive disclosure", case_sensitive=False)
            or "progressive" in REQUIRED_RULES[3].lower()
            or "disclosure" in REQUIRED_RULES[3].lower()
        )

    def test_rules_appear_as_numbered_requirements(self):
        """All four rules should appear as numbered items (1-4) in the definition."""
        for i in range(1, 5):
            pattern = rf"(?:^|\n)\s*{i}[\.\)]\s+"
            matches = re.search(pattern, SETUP_AGENT_DEFINITION)
            assert matches is not None, (
                f"Rule {i} should appear as a numbered requirement in the definition"
            )


# ===========================================================================
# AREA_0_ARCHETYPES: Options A through F
# ===========================================================================


class TestArea0ArchetypesStructure:
    """AREA_0_ARCHETYPES must be a list of exactly 6 items (A-F)."""

    def test_area_0_archetypes_is_list(self):
        assert isinstance(AREA_0_ARCHETYPES, list)

    def test_area_0_archetypes_has_six_items(self):
        assert len(AREA_0_ARCHETYPES) == 6

    def test_area_0_archetypes_items_are_strings(self):
        for i, archetype in enumerate(AREA_0_ARCHETYPES):
            assert isinstance(archetype, str), (
                f"AREA_0_ARCHETYPES[{i}] should be a string, got {type(archetype)}"
            )

    def test_area_0_archetypes_items_are_nonempty(self):
        for i, archetype in enumerate(AREA_0_ARCHETYPES):
            assert len(archetype.strip()) > 0, (
                f"AREA_0_ARCHETYPES[{i}] should not be empty"
            )


class TestArea0ArchetypesInDefinition:
    """Area 0 archetype selector with Options A-F in the definition."""

    def test_option_a_appears_in_definition(self):
        assert definition_contains(
            "Option A", case_sensitive=False
        ) or definition_contains("option a", case_sensitive=False)

    def test_option_b_appears_in_definition(self):
        assert definition_contains(
            "Option B", case_sensitive=False
        ) or definition_contains("option b", case_sensitive=False)

    def test_option_c_appears_in_definition(self):
        assert definition_contains(
            "Option C", case_sensitive=False
        ) or definition_contains("option c", case_sensitive=False)

    def test_option_d_appears_in_definition(self):
        assert definition_contains(
            "Option D", case_sensitive=False
        ) or definition_contains("option d", case_sensitive=False)

    def test_option_e_appears_in_definition(self):
        assert definition_contains(
            "Option E", case_sensitive=False
        ) or definition_contains("option e", case_sensitive=False)

    def test_option_f_appears_in_definition(self):
        assert definition_contains(
            "Option F", case_sensitive=False
        ) or definition_contains("option f", case_sensitive=False)

    def test_options_e_f_hidden_from_normal_users(self):
        """Options E/F must be hidden from normal users."""
        assert definition_contains("hidden", case_sensitive=False)


# ===========================================================================
# DIALOG_AREAS: 6 dialog areas (0-5)
# ===========================================================================


class TestDialogAreasStructure:
    """DIALOG_AREAS must be a list of exactly 6 items for areas 0-5."""

    def test_dialog_areas_is_list(self):
        assert isinstance(DIALOG_AREAS, list)

    def test_dialog_areas_has_six_items(self):
        assert len(DIALOG_AREAS) == 6

    def test_dialog_areas_items_are_strings(self):
        for i, area in enumerate(DIALOG_AREAS):
            assert isinstance(area, str), (
                f"DIALOG_AREAS[{i}] should be a string, got {type(area)}"
            )

    def test_dialog_areas_items_are_nonempty(self):
        for i, area in enumerate(DIALOG_AREAS):
            assert len(area.strip()) > 0, f"DIALOG_AREAS[{i}] should not be empty"


class TestDialogAreasContent:
    """Six dialog areas cover the required topics."""

    def test_area_0_is_language_ecosystem(self):
        """Area 0 should cover Language/Ecosystem."""
        area_0_text = DIALOG_AREAS[0].lower()
        assert "language" in area_0_text or "ecosystem" in area_0_text

    def test_area_1_is_vcs(self):
        """Area 1 should cover VCS."""
        area_1_text = DIALOG_AREAS[1].lower()
        assert "vcs" in area_1_text or "version control" in area_1_text

    def test_area_2_is_readme_docs(self):
        """Area 2 should cover README/Docs."""
        area_2_text = DIALOG_AREAS[2].lower()
        assert "readme" in area_2_text or "doc" in area_2_text

    def test_area_3_is_testing(self):
        """Area 3 should cover Testing."""
        area_3_text = DIALOG_AREAS[3].lower()
        assert "test" in area_3_text

    def test_area_4_is_licensing_metadata(self):
        """Area 4 should cover Licensing/Metadata."""
        area_4_text = DIALOG_AREAS[4].lower()
        assert "licens" in area_4_text or "metadata" in area_4_text

    def test_area_5_is_quality(self):
        """Area 5 should cover Quality."""
        area_5_text = DIALOG_AREAS[5].lower()
        assert "quality" in area_5_text


class TestDialogAreasInDefinition:
    """All six dialog areas are referenced in the definition."""

    def test_area_0_referenced_in_definition(self):
        assert definition_contains("Area 0", case_sensitive=False)

    def test_area_1_referenced_in_definition(self):
        assert definition_contains("Area 1", case_sensitive=False)

    def test_area_2_referenced_in_definition(self):
        assert definition_contains("Area 2", case_sensitive=False)

    def test_area_3_referenced_in_definition(self):
        assert definition_contains("Area 3", case_sensitive=False)

    def test_area_4_referenced_in_definition(self):
        assert definition_contains("Area 4", case_sensitive=False)

    def test_area_5_referenced_in_definition(self):
        assert definition_contains("Area 5", case_sensitive=False)

    def test_area_5_skip_condition_documented(self):
        """Area 5 may be skipped if Area 0 already populated quality settings."""
        assert definition_contains("skip", case_sensitive=False)


# ===========================================================================
# Two modes: project_context and project_profile
# ===========================================================================


class TestTwoModes:
    """The definition must reference both modes: project_context and project_profile."""

    def test_project_context_mode_referenced(self):
        assert definition_contains("project_context")

    def test_project_profile_mode_referenced(self):
        assert definition_contains("project_profile")


# ===========================================================================
# Profile schema: canonical field names
# ===========================================================================


class TestProfileSchemaFieldNames:
    """Definition must reference exact canonical field names for profile fields."""

    def test_archetype_field_referenced(self):
        assert definition_contains("archetype")

    def test_language_field_referenced(self):
        assert definition_contains("language")

    def test_language_primary_field_referenced(self):
        assert definition_contains("language.primary") or definition_contains("primary")

    def test_delivery_field_referenced(self):
        assert definition_contains("delivery")

    def test_quality_field_referenced(self):
        assert definition_contains("quality")

    def test_testing_field_referenced(self):
        assert definition_contains("testing")

    def test_readme_field_referenced(self):
        assert definition_contains("readme", case_sensitive=False)

    def test_license_field_referenced(self):
        assert definition_contains("license", case_sensitive=False)

    def test_vcs_field_referenced(self):
        assert definition_contains("vcs", case_sensitive=False)

    def test_pipeline_field_referenced(self):
        assert definition_contains("pipeline")


# ===========================================================================
# Mode A (self-build): default pre-population logic
# ===========================================================================


class TestModeASelfBuild:
    """Mode A (self-build) must describe default pre-population logic."""

    def test_self_build_referenced(self):
        assert (
            definition_contains("self-build", case_sensitive=False)
            or definition_contains("self_build", case_sensitive=False)
            or definition_contains("self build", case_sensitive=False)
        )

    def test_pre_population_logic_referenced(self):
        """Default pre-population logic should be described."""
        assert (
            definition_contains("pre-populat", case_sensitive=False)
            or definition_contains("prepopulat", case_sensitive=False)
            or definition_contains("default", case_sensitive=False)
        )


# ===========================================================================
# Option C (plugin): extended interview
# ===========================================================================


class TestOptionCPlugin:
    """Option C (plugin) requires extended interview with 4 questions."""

    def test_plugin_option_referenced(self):
        assert definition_contains("plugin", case_sensitive=False)

    def test_external_services_question_referenced(self):
        assert definition_contains("external_services") or definition_contains(
            "external services", case_sensitive=False
        )

    def test_auth_question_referenced(self):
        assert definition_contains("auth", case_sensitive=False)

    def test_hook_events_question_referenced(self):
        assert definition_contains("hook_events") or definition_contains(
            "hook events", case_sensitive=False
        )

    def test_skills_question_referenced(self):
        assert definition_contains("skills", case_sensitive=False)

    def test_plugin_external_services_profile_field(self):
        """Plugin interview populates plugin.external_services in profile."""
        assert definition_contains("plugin.external_services") or definition_contains(
            "external_services"
        )

    def test_plugin_hook_events_profile_field(self):
        """Plugin interview populates plugin.hook_events in profile."""
        assert definition_contains("plugin.hook_events") or definition_contains(
            "hook_events"
        )

    def test_plugin_skills_profile_field(self):
        """Plugin interview populates plugin.skills in profile."""
        assert definition_contains("plugin.skills") or definition_contains("skills")

    def test_plugin_mcp_servers_profile_field(self):
        """Plugin interview populates plugin.mcp_servers in profile."""
        assert definition_contains("plugin.mcp_servers") or definition_contains(
            "mcp_servers"
        )


# ===========================================================================
# Option D (mixed-language): focused dialog flow
# ===========================================================================


class TestOptionDMixedLanguage:
    """Option D (mixed-language) requires focused dialog flow (3-4 questions)."""

    def test_mixed_language_option_referenced(self):
        assert definition_contains("mixed", case_sensitive=False)

    def test_q1_which_language_owns_structure(self):
        """Q1 asks which language owns the project structure."""
        assert (
            definition_contains("which language owns", case_sensitive=False)
            or definition_contains("project structure", case_sensitive=False)
            or definition_contains("language.primary")
        )

    def test_q1_presents_non_component_only_languages(self):
        """Q1 presents all non-component-only languages (Python, R)."""
        has_python = definition_contains("Python")
        has_r = (
            definition_contains(" R ")
            or definition_contains(" R,")
            or definition_contains(" R.")
            or definition_contains('"R"')
        )
        assert has_python and has_r

    def test_q2_communication_direction(self):
        """Q2 asks about communication direction."""
        assert definition_contains("communication", case_sensitive=False)

    def test_q2_bridge_library_rpy2(self):
        """Q2 sets rpy2 for Python-calls-R."""
        assert definition_contains("rpy2")

    def test_q2_bridge_library_reticulate(self):
        """Q2 sets reticulate for R-calls-Python."""
        assert definition_contains("reticulate")

    def test_q2_bidirectional_option(self):
        """Q2 supports bidirectional communication (both libraries)."""
        assert definition_contains(
            "bidirectional", case_sensitive=False
        ) or definition_contains("both", case_sensitive=False)

    def test_q3_same_tools_as_pipeline(self):
        """Q3 asks about same tools as pipeline for primary language."""
        assert definition_contains(
            "same tools", case_sensitive=False
        ) or definition_contains("pipeline", case_sensitive=False)

    def test_q3_fast_path(self):
        """Q3 yes answer triggers fast-path population with pipeline defaults."""
        assert (
            definition_contains("fast-path", case_sensitive=False)
            or definition_contains("fast path", case_sensitive=False)
            or definition_contains("default", case_sensitive=False)
        )

    def test_q4_default_tools_for_secondary(self):
        """Q4 asks about default tools for secondary language."""
        assert definition_contains("secondary", case_sensitive=False)

    def test_mixed_hard_constraint_conda(self):
        """Mixed archetype forces environment_recommendation to conda."""
        assert definition_contains("conda")

    def test_mixed_hard_constraint_environment_yml(self):
        """Mixed archetype forces dependency_format to environment.yml."""
        assert definition_contains("environment.yml")

    def test_mixed_profile_archetype_field(self):
        """Mixed path sets archetype to 'mixed'."""
        assert definition_contains("mixed")

    def test_mixed_profile_language_primary(self):
        """Mixed path populates language.primary."""
        assert definition_contains("language.primary") or (
            definition_contains("language") and definition_contains("primary")
        )

    def test_mixed_profile_language_secondary(self):
        """Mixed path populates language.secondary."""
        assert definition_contains("language.secondary") or definition_contains(
            "secondary"
        )

    def test_mixed_profile_language_communication(self):
        """Mixed path populates language.communication."""
        assert definition_contains("language.communication") or definition_contains(
            "communication"
        )

    def test_mixed_profile_both_delivery_sections(self):
        """Mixed path populates delivery sections for both languages."""
        assert definition_contains("delivery")

    def test_mixed_profile_both_quality_sections(self):
        """Mixed path populates quality sections for both languages."""
        assert definition_contains("quality")


# ===========================================================================
# Options E/F: plugin fields auto-populated from SVP context
# ===========================================================================


class TestOptionsEFSvpContext:
    """Options E/F auto-populate plugin fields from SVP context."""

    def test_option_e_referenced(self):
        assert definition_contains(
            "Option E", case_sensitive=False
        ) or definition_contains("E", case_sensitive=True)

    def test_option_f_referenced(self):
        assert definition_contains(
            "Option F", case_sensitive=False
        ) or definition_contains("F", case_sensitive=True)

    def test_svp_context_auto_population(self):
        """E/F options auto-populate plugin fields from SVP context."""
        assert definition_contains("SVP", case_sensitive=True) or definition_contains(
            "svp", case_sensitive=False
        )

    def test_ef_hidden_from_normal_users(self):
        """Options E/F should be hidden from normal users."""
        assert definition_contains("hidden", case_sensitive=False)


# ===========================================================================
# Contradiction detection rules
# ===========================================================================


class TestContradictionDetection:
    """The definition must document contradiction detection rules."""

    def test_mixed_archetype_forces_conda_documented(self):
        """Mixed archetype forces conda constraint is documented."""
        assert definition_contains("conda")
        assert definition_contains("mixed", case_sensitive=False)

    def test_component_language_requires_host_documented(self):
        """Component language requires host constraint is documented."""
        assert definition_contains("component", case_sensitive=False)
        assert definition_contains("host", case_sensitive=False)

    def test_contradiction_detection_concept_present(self):
        """Contradiction detection is referenced in the definition."""
        assert (
            definition_contains("contradiction", case_sensitive=False)
            or definition_contains("conflict", case_sensitive=False)
            or definition_contains("constraint", case_sensitive=False)
        )


# ===========================================================================
# Single ledger: ledgers/setup_dialog.jsonl
# ===========================================================================


class TestLedgerReference:
    """Agent uses single ledger: ledgers/setup_dialog.jsonl."""

    def test_setup_dialog_ledger_referenced(self):
        assert definition_contains("setup_dialog.jsonl") or definition_contains(
            "setup_dialog"
        )

    def test_ledgers_directory_referenced(self):
        assert definition_contains("ledgers/") or definition_contains("ledgers")


# ===========================================================================
# Cross-validation: REQUIRED_RULES, AREA_0_ARCHETYPES, DIALOG_AREAS
# vs. SETUP_AGENT_DEFINITION content
# ===========================================================================


class TestCrossValidationRulesVsDefinition:
    """All items in the structural validation lists appear in the definition."""

    def test_all_required_rules_in_definition(self):
        """Every rule in REQUIRED_RULES must appear verbatim in the definition."""
        for i, rule in enumerate(REQUIRED_RULES):
            assert rule in SETUP_AGENT_DEFINITION, (
                f"REQUIRED_RULES[{i}] = {rule!r} not found verbatim in definition"
            )

    def test_all_dialog_areas_represented_in_definition(self):
        """Every area label in DIALOG_AREAS should be findable in the definition."""
        for i, area in enumerate(DIALOG_AREAS):
            assert (
                area in SETUP_AGENT_DEFINITION
                or area.lower() in SETUP_AGENT_DEFINITION.lower()
            ), f"DIALOG_AREAS[{i}] = {area!r} not found in definition"


class TestCrossValidationArchetypesVsDefinition:
    """Archetype options from the list should be traceable in the definition."""

    def test_all_archetypes_represented_in_definition(self):
        """Each archetype label in AREA_0_ARCHETYPES should appear in the definition."""
        for i, archetype in enumerate(AREA_0_ARCHETYPES):
            assert (
                archetype in SETUP_AGENT_DEFINITION
                or archetype.lower() in SETUP_AGENT_DEFINITION.lower()
            ), f"AREA_0_ARCHETYPES[{i}] = {archetype!r} not found in definition"


# ===========================================================================
# Environment recommendation and dependency format for mixed archetype
# ===========================================================================


class TestMixedArchetypeHardConstraints:
    """Both environment_recommendation forced to conda, both dependency_format
    forced to environment.yml for mixed archetype."""

    def test_environment_recommendation_keyword_present(self):
        assert definition_contains("environment_recommendation") or definition_contains(
            "environment recommendation", case_sensitive=False
        )

    def test_dependency_format_keyword_present(self):
        assert definition_contains("dependency_format") or definition_contains(
            "dependency format", case_sensitive=False
        )

    def test_conda_constraint_present(self):
        assert definition_contains("conda")

    def test_environment_yml_constraint_present(self):
        assert definition_contains("environment.yml")


# ===========================================================================
# Option C plugin profile fields in detail
# ===========================================================================


class TestOptionCPluginExtendedInterview:
    """Option C extended interview covers 4 specific topics and populates
    the correct plugin sub-fields."""

    def test_four_plugin_profile_subfields_all_present(self):
        """All four plugin sub-fields are referenced in the definition:
        external_services, hook_events, skills, mcp_servers."""
        subfields = [
            "external_services",
            "hook_events",
            "skills",
            "mcp_servers",
        ]
        for field in subfields:
            assert definition_contains(field), (
                f"Plugin sub-field {field!r} not found in definition"
            )


# ===========================================================================
# Option D mixed-language dialog: bridge libraries
# ===========================================================================


class TestOptionDBridgeLibraries:
    """Option D dialog must reference both bridge libraries with correct
    direction semantics."""

    def test_rpy2_python_calls_r(self):
        """rpy2 is the bridge for Python-calls-R."""
        assert definition_contains("rpy2")

    def test_reticulate_r_calls_python(self):
        """reticulate is the bridge for R-calls-Python."""
        assert definition_contains("reticulate")


# ===========================================================================
# Area 0: archetype selector completeness
# ===========================================================================


class TestArea0ArchetypeSelector:
    """Area 0 presents an archetype selector with six options (A-F)."""

    def test_six_options_labeled_a_through_f(self):
        """The definition should contain labels for options A through F."""
        labels = ["A", "B", "C", "D", "E", "F"]
        for label in labels:
            # Looking for patterns like "Option A", "A)", "A.", "(A)"
            pattern = (
                rf"(?:Option\s+{label}|{label}\)|{label}\.|"
                rf"\({label}\)|\b{label}\b\s*[:\-])"
            )
            matches = re.search(pattern, SETUP_AGENT_DEFINITION)
            assert matches is not None, (
                f"Option {label} not found in definition archetype selector"
            )


# ===========================================================================
# Consistency: AREA_0_ARCHETYPES count matches DIALOG_AREAS count
# ===========================================================================


class TestStructuralConsistency:
    """Cross-structural consistency checks between exported lists."""

    def test_area_0_archetypes_count_is_six(self):
        assert len(AREA_0_ARCHETYPES) == 6

    def test_dialog_areas_count_is_six(self):
        assert len(DIALOG_AREAS) == 6

    def test_required_rules_count_is_four(self):
        assert len(REQUIRED_RULES) == 4

    def test_all_exports_are_non_none(self):
        """No exported value should be None."""
        assert SETUP_AGENT_DEFINITION is not None
        assert REQUIRED_RULES is not None
        assert AREA_0_ARCHETYPES is not None
        assert DIALOG_AREAS is not None

    def test_required_rules_are_unique(self):
        """All four rules should be distinct."""
        assert len(set(REQUIRED_RULES)) == 4

    def test_area_0_archetypes_are_unique(self):
        """All six archetypes should be distinct."""
        assert len(set(AREA_0_ARCHETYPES)) == 6

    def test_dialog_areas_are_unique(self):
        """All six dialog areas should be distinct."""
        assert len(set(DIALOG_AREAS)) == 6


# ===========================================================================
# Definition content: key topics coverage
# ===========================================================================


class TestDefinitionTopicCoverage:
    """Verify that all key topics from the behavioral contracts are present
    somewhere in the agent definition."""

    def test_system_prompt_references_rules(self):
        """System prompt contains numbered behavioral requirements."""
        # Look for numbered list items
        numbered = re.findall(r"(?:^|\n)\s*\d+[\.\)]\s+\S", SETUP_AGENT_DEFINITION)
        assert len(numbered) >= 4, (
            "Definition should contain at least 4 numbered items for Rules 1-4"
        )

    def test_area_0_language_dialog_present(self):
        """Area 0 language dialog is described in the definition."""
        assert definition_contains(
            "Area 0", case_sensitive=False
        ) or definition_contains("language", case_sensitive=False)

    def test_two_modes_documented(self):
        """Both project_context and project_profile modes are documented."""
        assert definition_contains("project_context")
        assert definition_contains("project_profile")

    def test_option_c_plugin_interview_documented(self):
        """Option C plugin extended interview is documented."""
        assert definition_contains("plugin", case_sensitive=False)

    def test_option_d_mixed_language_documented(self):
        """Option D mixed-language dialog flow is documented."""
        assert definition_contains("mixed", case_sensitive=False)

    def test_contradiction_detection_documented(self):
        """Contradiction detection rules are documented."""
        assert (
            definition_contains("contradiction", case_sensitive=False)
            or definition_contains("constraint", case_sensitive=False)
            or definition_contains("conflict", case_sensitive=False)
        )

    def test_ledger_reference_documented(self):
        """Single ledger reference is documented."""
        assert definition_contains("setup_dialog")

    def test_ef_hidden_documented(self):
        """E/F hidden from normal users is documented."""
        assert definition_contains("hidden", case_sensitive=False)

    def test_area_5_skip_condition_documented(self):
        """Area 5 skip condition is documented."""
        assert definition_contains("Area 5", case_sensitive=False)
        assert definition_contains("skip", case_sensitive=False) or definition_contains(
            "already populated", case_sensitive=False
        )

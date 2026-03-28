"""
Tests for Unit 18: Setup Agent Definition.

Synthetic Data Assumptions:
- SETUP_AGENT_DEFINITION is a non-empty string containing the full agent definition
  markdown for the setup agent. It defines the setup agent's behavior for the Stage 0
  setup dialog.
- REQUIRED_RULES is a list of 4 rule strings that must appear verbatim in the
  SETUP_AGENT_DEFINITION. Rules correspond to: (1) plain-language explanations,
  (2) best-option recommendations, (3) sensible defaults, (4) progressive disclosure.
- AREA_0_ARCHETYPES is a list of 6 archetype option strings (Options A-F).
  Options A-D are standard project types; Options E-F are SVP self-build archetypes.
- DIALOG_AREAS is a list of 6 area descriptions covering: Area 0 (Language/Ecosystem),
  Area 1 (VCS), Area 2 (README/Docs), Area 3 (Testing), Area 4 (Licensing/Metadata),
  Area 5 (Quality).
- The definition string must contain content about: archetype selector with A-D visible
  and EXPERT MODE for E/F, Option B R dialog with profile field mappings, Option D
  mixed-language dialog, Option E build scope question (NEW LANGUAGE / MIX LANGUAGES /
  BOTH), Option C plugin interview (4 questions), two modes (project_context and
  project_profile), Mode A self-build defaults, contradiction detection, single ledger.
- Profile field names referenced in the definition correspond to canonical field names
  from Unit 3 (Profile Schema) and Unit 2 (Language Registry).
- No implementation code has been read; all tests verify against the behavioral
  contracts specified in the blueprint.
"""

from unit_18 import (
    AREA_0_ARCHETYPES,
    DIALOG_AREAS,
    REQUIRED_RULES,
    SETUP_AGENT_DEFINITION,
)

# ===========================================================================
# SETUP_AGENT_DEFINITION -- Basic structural properties
# ===========================================================================


class TestSetupAgentDefinitionIsNonEmptyString:
    """SETUP_AGENT_DEFINITION must be a non-empty string."""

    def test_definition_is_a_string(self):
        assert isinstance(SETUP_AGENT_DEFINITION, str)

    def test_definition_is_not_empty(self):
        assert len(SETUP_AGENT_DEFINITION) > 0

    def test_definition_has_substantial_content(self):
        """The definition should be a full agent markdown, not just a few words."""
        assert len(SETUP_AGENT_DEFINITION) > 100


# ===========================================================================
# REQUIRED_RULES -- Structure and content
# ===========================================================================


class TestRequiredRulesListStructure:
    """REQUIRED_RULES must be a list of exactly 4 rule strings."""

    def test_required_rules_is_a_list(self):
        assert isinstance(REQUIRED_RULES, list)

    def test_required_rules_has_exactly_four_entries(self):
        assert len(REQUIRED_RULES) == 4

    def test_every_rule_is_a_non_empty_string(self):
        for i, rule in enumerate(REQUIRED_RULES):
            assert isinstance(rule, str), f"Rule {i} is not a string"
            assert len(rule) > 0, f"Rule {i} is empty"


class TestRequiredRulesContentMatchesContracts:
    """Each rule covers its designated behavioral requirement."""

    def test_rule_1_concerns_plain_language_explanations(self):
        rule_1 = REQUIRED_RULES[0].lower()
        assert "plain" in rule_1 or "language" in rule_1 or "explain" in rule_1

    def test_rule_2_concerns_best_option_recommendations(self):
        rule_2 = REQUIRED_RULES[1].lower()
        assert "recommend" in rule_2 or "best" in rule_2

    def test_rule_3_concerns_sensible_defaults(self):
        rule_3 = REQUIRED_RULES[2].lower()
        assert "default" in rule_3

    def test_rule_4_concerns_progressive_disclosure(self):
        rule_4 = REQUIRED_RULES[3].lower()
        assert "progressive" in rule_4 or "disclosure" in rule_4


class TestAllRequiredRulesAppearVerbatimInDefinition:
    """Rules 1-4 must appear verbatim in the SETUP_AGENT_DEFINITION."""

    def test_rule_1_appears_verbatim_in_definition(self):
        assert REQUIRED_RULES[0] in SETUP_AGENT_DEFINITION

    def test_rule_2_appears_verbatim_in_definition(self):
        assert REQUIRED_RULES[1] in SETUP_AGENT_DEFINITION

    def test_rule_3_appears_verbatim_in_definition(self):
        assert REQUIRED_RULES[2] in SETUP_AGENT_DEFINITION

    def test_rule_4_appears_verbatim_in_definition(self):
        assert REQUIRED_RULES[3] in SETUP_AGENT_DEFINITION


# ===========================================================================
# AREA_0_ARCHETYPES -- Structure and content
# ===========================================================================


class TestArea0ArchetypesListStructure:
    """AREA_0_ARCHETYPES must be a list of 6 archetype option strings (A-F)."""

    def test_archetypes_is_a_list(self):
        assert isinstance(AREA_0_ARCHETYPES, list)

    def test_archetypes_has_exactly_six_entries(self):
        assert len(AREA_0_ARCHETYPES) == 6

    def test_every_archetype_is_a_non_empty_string(self):
        for i, archetype in enumerate(AREA_0_ARCHETYPES):
            assert isinstance(archetype, str), f"Archetype {i} is not a string"
            assert len(archetype) > 0, f"Archetype {i} is empty"


class TestArea0ArchetypesContentCoversAllSixOptions:
    """The archetypes must cover Options A through F as defined in the spec."""

    def test_option_a_python_project_is_present(self):
        text = " ".join(AREA_0_ARCHETYPES).lower()
        assert "python" in text

    def test_option_b_r_project_is_present(self):
        # R project must appear in one of the archetype strings
        found = any(
            "r " in a.lower() or "r project" in a.lower() or a.lower().startswith("r ")
            for a in AREA_0_ARCHETYPES
        )
        if not found:
            # Fallback: check for "R" as a standalone token
            found = any(" R " in a or a.startswith("R ") for a in AREA_0_ARCHETYPES)
        assert found, f"No R project archetype found in {AREA_0_ARCHETYPES}"

    def test_option_c_plugin_is_present(self):
        text = " ".join(AREA_0_ARCHETYPES).lower()
        assert "plugin" in text

    def test_option_d_mixed_language_is_present(self):
        text = " ".join(AREA_0_ARCHETYPES).lower()
        assert "mixed" in text

    def test_option_e_svp_language_extension_is_present(self):
        text = " ".join(AREA_0_ARCHETYPES).lower()
        assert "language" in text and (
            "extension" in text or "self-build" in text or "svp" in text
        )

    def test_option_f_svp_architectural_change_is_present(self):
        text = " ".join(AREA_0_ARCHETYPES).lower()
        assert "architectural" in text or "architecture" in text


class TestArea0ArchetypesOrdering:
    """Options A-D should precede E-F in the list."""

    def test_first_four_entries_are_standard_project_types(self):
        """A-D are standard project types (Python, R, plugin, mixed)."""
        first_four = " ".join(AREA_0_ARCHETYPES[:4]).lower()
        assert "python" in first_four
        assert "plugin" in first_four or "claude" in first_four
        assert "mixed" in first_four

    def test_last_two_entries_are_svp_self_build_types(self):
        """E-F are SVP self-build archetypes."""
        last_two = " ".join(AREA_0_ARCHETYPES[4:6]).lower()
        assert "svp" in last_two or "self-build" in last_two or "extension" in last_two


# ===========================================================================
# DIALOG_AREAS -- Structure and content
# ===========================================================================


class TestDialogAreasListStructure:
    """DIALOG_AREAS must be a list of 6 area descriptions."""

    def test_dialog_areas_is_a_list(self):
        assert isinstance(DIALOG_AREAS, list)

    def test_dialog_areas_has_exactly_six_entries(self):
        assert len(DIALOG_AREAS) == 6

    def test_every_area_is_a_non_empty_string(self):
        for i, area in enumerate(DIALOG_AREAS):
            assert isinstance(area, str), f"Area {i} is not a string"
            assert len(area) > 0, f"Area {i} is empty"


class TestDialogAreasContentMatchesSpecifiedAreas:
    """Each dialog area corresponds to the specified domain."""

    def test_area_0_is_language_ecosystem(self):
        area_0 = DIALOG_AREAS[0].lower()
        assert "language" in area_0 or "ecosystem" in area_0

    def test_area_1_is_vcs(self):
        area_1 = DIALOG_AREAS[1].lower()
        assert "vcs" in area_1 or "version control" in area_1 or "git" in area_1

    def test_area_2_is_readme_docs(self):
        area_2 = DIALOG_AREAS[2].lower()
        assert "readme" in area_2 or "doc" in area_2

    def test_area_3_is_testing(self):
        area_3 = DIALOG_AREAS[3].lower()
        assert "test" in area_3

    def test_area_4_is_licensing_metadata(self):
        area_4 = DIALOG_AREAS[4].lower()
        assert "licens" in area_4 or "metadata" in area_4

    def test_area_5_is_quality(self):
        area_5 = DIALOG_AREAS[5].lower()
        assert "quality" in area_5


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Archetype selector with EXPERT MODE
# ===========================================================================


class TestDefinitionContainsArchetypeSelectorWithExpertMode:
    """
    The definition must include the archetype selector with Options A-D visible
    to normal users and EXPERT MODE for Options E/F.
    """

    def test_definition_mentions_expert_mode(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "expert mode" in defn_lower or "expert_mode" in defn_lower

    def test_definition_references_options_a_through_d(self):
        """Options A-D should be visible as standard choices."""
        defn = SETUP_AGENT_DEFINITION
        assert "A" in defn or "Option A" in defn
        assert "B" in defn or "Option B" in defn
        assert "C" in defn or "Option C" in defn
        assert "D" in defn or "Option D" in defn

    def test_definition_references_options_e_and_f(self):
        """Options E/F should be referenced under expert mode."""
        defn = SETUP_AGENT_DEFINITION
        assert "E" in defn or "Option E" in defn
        assert "F" in defn or "Option F" in defn

    def test_all_six_archetypes_appear_in_definition(self):
        """Every archetype option string from AREA_0_ARCHETYPES appears in the definition."""
        for archetype in AREA_0_ARCHETYPES:
            assert archetype in SETUP_AGENT_DEFINITION, (
                f"Archetype option not found in definition: {archetype!r}"
            )


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Option B: R dialog with profile field mappings
# ===========================================================================


class TestDefinitionContainsOptionBRDialogWithProfileFieldMappings:
    """
    Option B R dialog populates specific profile fields. The definition must
    reference these fields.
    """

    def test_definition_mentions_r_project_dialog(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert (
            "r project" in defn_lower
            or "r_project" in defn_lower
            or "option b" in defn_lower
        )

    def test_definition_references_delivery_r_environment_recommendation(self):
        assert "environment_recommendation" in SETUP_AGENT_DEFINITION

    def test_definition_references_quality_r_linter(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "linter" in defn_lower

    def test_definition_references_quality_r_formatter(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "formatter" in defn_lower

    def test_definition_references_delivery_r_source_layout(self):
        assert "source_layout" in SETUP_AGENT_DEFINITION

    def test_definition_references_renv_as_environment_option(self):
        assert "renv" in SETUP_AGENT_DEFINITION

    def test_definition_references_testthat_as_test_framework_option(self):
        assert "testthat" in SETUP_AGENT_DEFINITION

    def test_definition_references_lintr_as_linter_option(self):
        assert "lintr" in SETUP_AGENT_DEFINITION

    def test_definition_references_styler_as_formatter_option(self):
        assert "styler" in SETUP_AGENT_DEFINITION

    def test_definition_references_roxygen2_as_documentation_option(self):
        assert "roxygen2" in SETUP_AGENT_DEFINITION

    def test_definition_references_stan_component_integration(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "stan" in defn_lower

    def test_definition_references_bioconductor(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "bioconductor" in defn_lower

    def test_definition_references_shiny(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "shiny" in defn_lower


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Option D: Mixed-language dialog
# ===========================================================================


class TestDefinitionContainsOptionDMixedLanguageDialog:
    """
    Option D conducts a focused dialog for mixed-language projects (3-4 questions).
    The definition must contain the question content and profile field mappings.
    """

    def test_definition_mentions_mixed_language_or_option_d(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "mixed" in defn_lower

    def test_definition_mentions_which_language_owns_project_structure(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert (
            "owns" in defn_lower or "primary" in defn_lower or "structure" in defn_lower
        )

    def test_definition_references_language_primary_field(self):
        assert (
            "language.primary" in SETUP_AGENT_DEFINITION
            or "primary" in SETUP_AGENT_DEFINITION
        )

    def test_definition_references_language_secondary_field(self):
        assert (
            "language.secondary" in SETUP_AGENT_DEFINITION
            or "secondary" in SETUP_AGENT_DEFINITION
        )

    def test_definition_references_communication_direction(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "communication" in defn_lower

    def test_definition_references_rpy2_bridge_library(self):
        assert "rpy2" in SETUP_AGENT_DEFINITION

    def test_definition_references_reticulate_bridge_library(self):
        assert "reticulate" in SETUP_AGENT_DEFINITION

    def test_definition_mentions_conda_forced_for_mixed_archetype(self):
        """Mixed archetype forces both environment_recommendation to conda."""
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "conda" in defn_lower

    def test_definition_mentions_environment_yml_forced_for_mixed_archetype(self):
        """Mixed archetype forces both dependency_format to environment.yml."""
        assert "environment.yml" in SETUP_AGENT_DEFINITION


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Option E: Build scope question
# ===========================================================================


class TestDefinitionContainsOptionEBuildScopeQuestion:
    """
    Option E asks a build scope question with three choices:
    NEW LANGUAGE, MIX LANGUAGES, BOTH.
    """

    def test_definition_references_new_language_scope(self):
        defn_upper = SETUP_AGENT_DEFINITION.upper()
        assert "NEW LANGUAGE" in defn_upper

    def test_definition_references_mix_languages_scope(self):
        defn_upper = SETUP_AGENT_DEFINITION.upper()
        assert "MIX LANGUAGES" in defn_upper

    def test_definition_references_both_scope(self):
        defn_upper = SETUP_AGENT_DEFINITION.upper()
        assert "BOTH" in defn_upper

    def test_definition_references_svp_language_extension(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert (
            "svp_language_extension" in defn_lower or "language extension" in defn_lower
        )

    def test_definition_references_build_scope(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "build scope" in defn_lower or "scope" in defn_lower


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Option C: Plugin interview
# ===========================================================================


class TestDefinitionContainsOptionCPluginInterview:
    """
    Option C (plugin) has an extended interview with 4 questions about
    external services, auth, hook events, and skills.
    """

    def test_definition_mentions_plugin_or_option_c(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "plugin" in defn_lower

    def test_definition_references_external_services(self):
        assert (
            "external_services" in SETUP_AGENT_DEFINITION
            or "external services" in SETUP_AGENT_DEFINITION.lower()
        )

    def test_definition_references_hook_events(self):
        assert (
            "hook_events" in SETUP_AGENT_DEFINITION
            or "hook events" in SETUP_AGENT_DEFINITION.lower()
        )

    def test_definition_references_skills(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "skills" in defn_lower

    def test_definition_references_mcp_servers(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "mcp" in defn_lower or "mcp_servers" in defn_lower


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Two modes
# ===========================================================================


class TestDefinitionContainsTwoModes:
    """The definition must reference both modes: project_context and project_profile."""

    def test_definition_references_project_context_mode(self):
        assert "project_context" in SETUP_AGENT_DEFINITION

    def test_definition_references_project_profile_mode(self):
        assert "project_profile" in SETUP_AGENT_DEFINITION


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Mode A (self-build) default pre-population
# ===========================================================================


class TestDefinitionContainsModeASelfBuildDefaults:
    """Mode A (self-build) has default pre-population logic."""

    def test_definition_references_self_build_or_svp_build(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert (
            "self-build" in defn_lower
            or "self_build" in defn_lower
            or "svp_build" in defn_lower
            or "is_svp_build" in defn_lower
        )


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Options E/F auto-populated plugin fields
# ===========================================================================


class TestDefinitionContainsOptionEFAutoPopulation:
    """Options E/F: plugin fields are auto-populated from SVP context."""

    def test_definition_references_auto_population_for_svp_builds(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "auto" in defn_lower and "popul" in defn_lower


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Contradiction detection
# ===========================================================================


class TestDefinitionContainsContradictionDetection:
    """
    The definition must include contradiction detection rules:
    - Mixed archetype forces conda.
    - Component language requires host.
    """

    def test_definition_references_contradiction_detection(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert (
            "contradiction" in defn_lower
            or "conflict" in defn_lower
            or "invalid" in defn_lower
        )

    def test_definition_mentions_mixed_forces_conda_constraint(self):
        """Mixed archetype forces environment_recommendation to conda for both languages."""
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "conda" in defn_lower
        assert "mixed" in defn_lower

    def test_definition_mentions_component_requires_host_constraint(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "component" in defn_lower and (
            "host" in defn_lower or "compatible" in defn_lower
        )


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Single ledger
# ===========================================================================


class TestDefinitionContainsSingleLedger:
    """The agent uses a single ledger: ledgers/setup_dialog.jsonl."""

    def test_definition_references_setup_dialog_ledger(self):
        assert "setup_dialog" in SETUP_AGENT_DEFINITION

    def test_definition_references_ledger_directory(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "ledger" in defn_lower

    def test_definition_references_jsonl_format(self):
        assert (
            "jsonl" in SETUP_AGENT_DEFINITION.lower()
            or ".jsonl" in SETUP_AGENT_DEFINITION
        )


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Profile schema / canonical field names
# ===========================================================================


class TestDefinitionContainsProfileSchemaFieldNames:
    """The definition must reference exact canonical field names for profile fields."""

    def test_definition_references_archetype_field(self):
        assert "archetype" in SETUP_AGENT_DEFINITION

    def test_definition_references_language_primary(self):
        assert (
            "language" in SETUP_AGENT_DEFINITION and "primary" in SETUP_AGENT_DEFINITION
        )

    def test_definition_references_delivery_section(self):
        assert "delivery" in SETUP_AGENT_DEFINITION

    def test_definition_references_quality_section(self):
        assert "quality" in SETUP_AGENT_DEFINITION

    def test_definition_references_testing_section(self):
        assert "testing" in SETUP_AGENT_DEFINITION.lower()

    def test_definition_references_license_section(self):
        assert "license" in SETUP_AGENT_DEFINITION.lower()

    def test_definition_references_vcs_section(self):
        assert "vcs" in SETUP_AGENT_DEFINITION.lower()

    def test_definition_references_readme_section(self):
        assert "readme" in SETUP_AGENT_DEFINITION.lower()


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Six dialog areas mentioned
# ===========================================================================


class TestDefinitionReferencesAllSixDialogAreas:
    """The definition must reference all six dialog areas."""

    def test_definition_mentions_area_0(self):
        assert (
            "Area 0" in SETUP_AGENT_DEFINITION
            or "area 0" in SETUP_AGENT_DEFINITION.lower()
        )

    def test_definition_mentions_area_1(self):
        assert (
            "Area 1" in SETUP_AGENT_DEFINITION
            or "area 1" in SETUP_AGENT_DEFINITION.lower()
        )

    def test_definition_mentions_area_2(self):
        assert (
            "Area 2" in SETUP_AGENT_DEFINITION
            or "area 2" in SETUP_AGENT_DEFINITION.lower()
        )

    def test_definition_mentions_area_3(self):
        assert (
            "Area 3" in SETUP_AGENT_DEFINITION
            or "area 3" in SETUP_AGENT_DEFINITION.lower()
        )

    def test_definition_mentions_area_4(self):
        assert (
            "Area 4" in SETUP_AGENT_DEFINITION
            or "area 4" in SETUP_AGENT_DEFINITION.lower()
        )

    def test_definition_mentions_area_5(self):
        assert (
            "Area 5" in SETUP_AGENT_DEFINITION
            or "area 5" in SETUP_AGENT_DEFINITION.lower()
        )


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Area 5 skip condition
# ===========================================================================


class TestDefinitionContainsArea5SkipCondition:
    """Area 5 may be skipped if Area 0 already populated quality settings."""

    def test_definition_mentions_area_5_skip_logic(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert (
            "skip" in defn_lower
            and "area 5" in defn_lower
            or ("quality" in defn_lower and "already" in defn_lower)
        )


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Option D hard constraints
# ===========================================================================


class TestDefinitionContainsOptionDHardConstraints:
    """
    Option D (mixed) enforces hard constraints:
    - Both environment_recommendation forced to conda
    - Both dependency_format forced to environment.yml
    """

    def test_definition_references_environment_recommendation_conda(self):
        assert "environment_recommendation" in SETUP_AGENT_DEFINITION
        assert "conda" in SETUP_AGENT_DEFINITION

    def test_definition_references_dependency_format_environment_yml(self):
        assert "dependency_format" in SETUP_AGENT_DEFINITION
        assert "environment.yml" in SETUP_AGENT_DEFINITION


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Option D profile fields populated
# ===========================================================================


class TestDefinitionContainsOptionDProfileFieldsPopulated:
    """
    Option D populates: archetype: "mixed", language.primary, language.secondary,
    language.communication, and both delivery and quality sections for both languages.
    """

    def test_definition_mentions_archetype_mixed(self):
        assert "mixed" in SETUP_AGENT_DEFINITION

    def test_definition_mentions_language_communication_field(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "communication" in defn_lower

    def test_definition_mentions_both_delivery_sections(self):
        """Both languages get delivery sections."""
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "delivery" in defn_lower

    def test_definition_mentions_both_quality_sections(self):
        """Both languages get quality sections."""
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "quality" in defn_lower


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Option B Stan dialog
# ===========================================================================


class TestDefinitionContainsStanComponentDialog:
    """
    Option B R dialog includes Stan component language integration questions.
    """

    def test_definition_mentions_stan(self):
        assert (
            "Stan" in SETUP_AGENT_DEFINITION or "stan" in SETUP_AGENT_DEFINITION.lower()
        )

    def test_definition_references_language_components(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "component" in defn_lower

    def test_definition_references_cmdstanr_or_rstan(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "cmdstanr" in defn_lower or "rstan" in defn_lower


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Option A: Python project fast path
# ===========================================================================


class TestDefinitionContainsOptionAPythonProjectFastPath:
    """
    Option A asks if the user wants the same tools as the pipeline.
    Fast path: yes -> populate pipeline defaults.
    """

    def test_definition_references_python_project(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "python" in defn_lower

    def test_definition_references_same_tools_as_pipeline(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "pipeline" in defn_lower or "same tools" in defn_lower


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Option B R dialog app frameworks
# ===========================================================================


class TestDefinitionContainsOptionBAppFrameworks:
    """
    Option B R dialog includes Shiny app framework choices: plain Shiny, golem, rhino.
    """

    def test_definition_mentions_golem(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "golem" in defn_lower

    def test_definition_mentions_rhino(self):
        defn_lower = SETUP_AGENT_DEFINITION.lower()
        assert "rhino" in defn_lower

    def test_definition_references_app_framework_field(self):
        assert "app_framework" in SETUP_AGENT_DEFINITION


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Option C plugin profile fields
# ===========================================================================


class TestDefinitionContainsOptionCPluginProfileFields:
    """
    Option C populates plugin.external_services, plugin.hook_events,
    plugin.skills, plugin.mcp_servers.
    """

    def test_definition_references_plugin_external_services(self):
        assert "plugin" in SETUP_AGENT_DEFINITION.lower()
        assert (
            "external_services" in SETUP_AGENT_DEFINITION
            or "external services" in SETUP_AGENT_DEFINITION.lower()
        )

    def test_definition_references_plugin_hook_events(self):
        assert (
            "hook_events" in SETUP_AGENT_DEFINITION
            or "hook events" in SETUP_AGENT_DEFINITION.lower()
        )

    def test_definition_references_plugin_skills(self):
        assert "skills" in SETUP_AGENT_DEFINITION.lower()

    def test_definition_references_plugin_mcp_servers(self):
        assert (
            "mcp_servers" in SETUP_AGENT_DEFINITION
            or "mcp" in SETUP_AGENT_DEFINITION.lower()
        )


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Option E/F archetype field values
# ===========================================================================


class TestDefinitionContainsOptionEFArchetypeFieldValues:
    """
    Option E sets archetype: svp_language_extension.
    Option F sets archetype: svp_architectural.
    """

    def test_definition_references_svp_language_extension_archetype(self):
        assert "svp_language_extension" in SETUP_AGENT_DEFINITION

    def test_definition_references_svp_architectural_archetype(self):
        assert "svp_architectural" in SETUP_AGENT_DEFINITION


# ===========================================================================
# Cross-constant consistency
# ===========================================================================


class TestCrossConstantConsistency:
    """Verify relationships between the module-level constants."""

    def test_all_archetypes_from_list_appear_in_definition(self):
        """Every string in AREA_0_ARCHETYPES must appear in the definition."""
        for archetype in AREA_0_ARCHETYPES:
            assert archetype in SETUP_AGENT_DEFINITION, (
                f"AREA_0_ARCHETYPES entry not found in SETUP_AGENT_DEFINITION: {archetype!r}"
            )

    def test_all_dialog_areas_from_list_appear_in_definition(self):
        """Every string in DIALOG_AREAS should appear in or relate to the definition."""
        for area in DIALOG_AREAS:
            assert area in SETUP_AGENT_DEFINITION, (
                f"DIALOG_AREAS entry not found in SETUP_AGENT_DEFINITION: {area!r}"
            )

    def test_all_required_rules_from_list_appear_in_definition(self):
        """Every string in REQUIRED_RULES must appear verbatim in the definition."""
        for rule in REQUIRED_RULES:
            assert rule in SETUP_AGENT_DEFINITION, (
                f"REQUIRED_RULES entry not found in SETUP_AGENT_DEFINITION: {rule!r}"
            )

    def test_no_duplicate_archetypes(self):
        """AREA_0_ARCHETYPES should contain no duplicates."""
        assert len(AREA_0_ARCHETYPES) == len(set(AREA_0_ARCHETYPES))

    def test_no_duplicate_dialog_areas(self):
        """DIALOG_AREAS should contain no duplicates."""
        assert len(DIALOG_AREAS) == len(set(DIALOG_AREAS))

    def test_no_duplicate_rules(self):
        """REQUIRED_RULES should contain no duplicates."""
        assert len(REQUIRED_RULES) == len(set(REQUIRED_RULES))


# ===========================================================================
# SETUP_AGENT_DEFINITION -- Rules are numbered
# ===========================================================================


class TestDefinitionContainsNumberedRules:
    """Rules 1-4 must appear as numbered behavioral requirements."""

    def test_definition_contains_rule_numbering(self):
        """The definition should contain rule numbering patterns like Rule 1, Rule 2, etc."""
        defn = SETUP_AGENT_DEFINITION
        numbered_patterns_found = 0
        for i in range(1, 5):
            if f"Rule {i}" in defn or f"rule {i}" in defn.lower():
                numbered_patterns_found += 1
        assert numbered_patterns_found >= 4, (
            f"Expected 4 numbered rules, found {numbered_patterns_found}"
        )

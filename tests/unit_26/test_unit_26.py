"""Unit 26: Orchestration Skill -- complete test suite.

Synthetic data assumptions:
- ORCHESTRATION_SKILL is a str containing the complete SKILL.md markdown content
  for the svp:orchestration skill. All structural tests inspect this string for
  keywords, phrases, and patterns specified in the behavioral contracts.
- The content begins with YAML frontmatter delimited by '---' lines, containing
  fields: name, description, argument-hint, allowed-tools, model, effort, context.
- The frontmatter field 'name' must have value "svp:orchestration".
- The body contains markdown sections describing the six-step mechanical action
  cycle, REMINDER block template, three-layer model, language context flow,
  per-stage orchestrator oversight checklists, pipeline fidelity invariant,
  self-escalation invariant, spec refresh behavior, hard stop protocol, and
  break-glass behavioral guidance.
- Keyword matching is case-insensitive where noted; exact tokens like stage
  numbers, section references, and status strings are matched as specified.
- Stage oversight references tested: Stages 0 through 7.
- Stage 0 references: 3-gate mentor protocol, Section 6.9, Gates 0.1/0.2/0.3.
- Stage 1 references: 7 sub-protocols, Section 7.7, sub-sections 7.7.1 through
  7.7.8.
- Stage 2 references: 23-item checklist, Section 8.5.
- Stage 3 references: 26-item checklist, Section 10.15.
- Stage 4 references: 6-item checklist.
- Stage 5 references: 10-item checklist, Section 12.17.
- Stage 6 references: 9-item checklist, Section 12.18.13.
- Stage 7 (oracle): no separate oversight protocol.
- Self-escalation invariant: 3+ consecutive identical dispatches triggers
  break-glass.
- Spec refresh: 5 phase transition points, 3 orchestrator rules per refresh.
- Hard stop protocol: Section 41, Pass 1, bug detection, checkpoint restart.
- Break-glass guidance: Section 43.9, 5 permitted actions, explicit forbidden
  list.
"""

import re

import pytest

from src.unit_26.stub import ORCHESTRATION_SKILL

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def skill_contains(phrase: str, case_sensitive: bool = True) -> bool:
    """Check whether ORCHESTRATION_SKILL contains the given phrase."""
    if case_sensitive:
        return phrase in ORCHESTRATION_SKILL
    return phrase.lower() in ORCHESTRATION_SKILL.lower()


def skill_matches(pattern: str, flags: int = 0) -> list:
    """Return all regex matches of pattern in ORCHESTRATION_SKILL."""
    return re.findall(pattern, ORCHESTRATION_SKILL, flags)


def extract_frontmatter() -> str:
    """Extract YAML frontmatter from ORCHESTRATION_SKILL.

    Returns the text between the first pair of '---' delimiters.
    """
    match = re.match(r"^---\s*\n(.*?)\n---", ORCHESTRATION_SKILL, re.DOTALL)
    if match:
        return match.group(1)
    return ""


# ===========================================================================
# ORCHESTRATION_SKILL: type and basic structure
# ===========================================================================


class TestOrchestrationSkillBasicStructure:
    """Verify ORCHESTRATION_SKILL is a non-empty markdown string."""

    def test_skill_is_string(self):
        assert isinstance(ORCHESTRATION_SKILL, str)

    def test_skill_is_not_none(self):
        assert ORCHESTRATION_SKILL is not None

    def test_skill_is_nonempty(self):
        assert len(ORCHESTRATION_SKILL.strip()) > 0

    def test_skill_contains_markdown_headings(self):
        """Skill definition must be structured markdown with headings."""
        assert re.search(r"^#+\s+", ORCHESTRATION_SKILL, re.MULTILINE)

    def test_skill_has_substantial_content(self):
        """Skill definition should have meaningful length for a system prompt."""
        assert len(ORCHESTRATION_SKILL.strip()) > 500


# ===========================================================================
# Frontmatter: YAML structure
# ===========================================================================


class TestFrontmatterStructure:
    """Frontmatter follows Claude Code schema with required fields."""

    def test_frontmatter_delimiters_present(self):
        """Skill must start with YAML frontmatter delimited by '---'."""
        assert ORCHESTRATION_SKILL.strip().startswith("---")
        # Must have a closing delimiter too
        lines = ORCHESTRATION_SKILL.strip().split("\n")
        # First line is '---', find the next '---'
        closing_indices = [
            i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        ]
        assert len(closing_indices) >= 1, "No closing frontmatter delimiter found"

    def test_frontmatter_contains_name_field(self):
        """Frontmatter must contain a 'name' field."""
        fm = extract_frontmatter()
        assert re.search(r"^name\s*:", fm, re.MULTILINE), (
            "Frontmatter missing 'name' field"
        )

    def test_frontmatter_name_value_is_svp_orchestration(self):
        """Frontmatter name must be 'svp:orchestration'."""
        fm = extract_frontmatter()
        assert "svp:orchestration" in fm, "Frontmatter name must be 'svp:orchestration'"

    def test_frontmatter_contains_description_field(self):
        """Frontmatter must contain a 'description' field."""
        fm = extract_frontmatter()
        assert re.search(r"^description\s*:", fm, re.MULTILINE), (
            "Frontmatter missing 'description' field"
        )

    def test_frontmatter_contains_argument_hint_field(self):
        """Frontmatter must contain an 'argument-hint' field."""
        fm = extract_frontmatter()
        assert re.search(r"^argument-hint\s*:", fm, re.MULTILINE), (
            "Frontmatter missing 'argument-hint' field"
        )

    def test_frontmatter_contains_allowed_tools_field(self):
        """Frontmatter must contain an 'allowed-tools' field."""
        fm = extract_frontmatter()
        assert re.search(r"^allowed-tools\s*:", fm, re.MULTILINE), (
            "Frontmatter missing 'allowed-tools' field"
        )

    def test_frontmatter_contains_model_field(self):
        """Frontmatter must contain a 'model' field."""
        fm = extract_frontmatter()
        assert re.search(r"^model\s*:", fm, re.MULTILINE), (
            "Frontmatter missing 'model' field"
        )

    def test_frontmatter_contains_effort_field(self):
        """Frontmatter must contain an 'effort' field."""
        fm = extract_frontmatter()
        assert re.search(r"^effort\s*:", fm, re.MULTILINE), (
            "Frontmatter missing 'effort' field"
        )

    def test_frontmatter_contains_context_field(self):
        """Frontmatter must contain a 'context' field."""
        fm = extract_frontmatter()
        assert re.search(r"^context\s*:", fm, re.MULTILINE), (
            "Frontmatter missing 'context' field"
        )


# ===========================================================================
# Six-step mechanical action cycle
# ===========================================================================


class TestSixStepActionCycle:
    """The skill must describe the six-step mechanical action cycle."""

    def test_six_step_concept_referenced(self):
        """The skill must reference a six-step cycle."""
        assert (
            skill_contains("six", case_sensitive=False)
            or skill_contains("6 step", case_sensitive=False)
            or skill_contains("6-step", case_sensitive=False)
        )

    def test_action_cycle_referenced(self):
        """The skill must reference the action cycle."""
        assert skill_contains("action cycle", case_sensitive=False) or skill_contains(
            "action-cycle", case_sensitive=False
        )

    def test_routing_script_step_referenced(self):
        """Step 1: run the routing script."""
        assert skill_contains("routing script", case_sensitive=False) or skill_contains(
            "routing.py", case_sensitive=False
        )

    def test_prepare_command_step_referenced(self):
        """Step 2: run the PREPARE command."""
        assert skill_contains("PREPARE", case_sensitive=True) or skill_contains(
            "prepare command", case_sensitive=False
        )

    def test_action_execution_step_referenced(self):
        """Step 3: execute the ACTION."""
        assert skill_contains("ACTION", case_sensitive=True)

    def test_last_status_step_referenced(self):
        """Step 4: write result to last_status.txt."""
        assert skill_contains("last_status.txt") or skill_contains(
            "last_status", case_sensitive=False
        )

    def test_post_command_step_referenced(self):
        """Step 5: run the POST command."""
        assert skill_contains("POST", case_sensitive=True) or skill_contains(
            "post command", case_sensitive=False
        )

    def test_loop_back_step_referenced(self):
        """Step 6: go back to step 1."""
        assert (
            skill_contains("step 1", case_sensitive=False)
            or skill_contains("go to", case_sensitive=False)
            or skill_contains("repeat", case_sensitive=False)
        )


# ===========================================================================
# REMINDER block template
# ===========================================================================


class TestReminderBlockTemplate:
    """The skill must contain the REMINDER block template from Section 3.6."""

    def test_reminder_keyword_present(self):
        """REMINDER block must be referenced."""
        assert skill_contains("REMINDER", case_sensitive=True)

    def test_reminder_block_template_structure(self):
        """REMINDER block template must appear as a block/template construct."""
        assert skill_contains("REMINDER", case_sensitive=True)
        # Must contain some kind of template or block marker
        assert skill_contains("block", case_sensitive=False) or skill_contains(
            "template", case_sensitive=False
        )

    def test_section_3_6_referenced(self):
        """REMINDER block must reference Section 3.6 as its source."""
        assert skill_contains("3.6") or skill_contains(
            "Section 3.6", case_sensitive=False
        )


# ===========================================================================
# Three-layer model explanation
# ===========================================================================


class TestThreeLayerModel:
    """The skill must explain the three-layer model."""

    def test_three_layer_concept_referenced(self):
        """Three-layer model must be described."""
        assert (
            skill_contains("three-layer", case_sensitive=False)
            or skill_contains("three layer", case_sensitive=False)
            or skill_contains("3-layer", case_sensitive=False)
            or skill_contains("3 layer", case_sensitive=False)
        )

    def test_pipeline_toolchain_referenced(self):
        """Pipeline toolchain must be one of the three layers."""
        assert skill_contains(
            "pipeline toolchain", case_sensitive=False
        ) or skill_contains("pipeline", case_sensitive=False)

    def test_build_time_quality_referenced(self):
        """Build-time quality must be one of the three layers."""
        assert (
            skill_contains("build-time quality", case_sensitive=False)
            or skill_contains("build-time", case_sensitive=False)
            or skill_contains("build time quality", case_sensitive=False)
        )

    def test_delivery_toolchain_referenced(self):
        """Delivery toolchain must be one of the three layers."""
        assert skill_contains(
            "delivery toolchain", case_sensitive=False
        ) or skill_contains("delivery", case_sensitive=False)

    def test_all_three_layers_present(self):
        """All three layers must be present in a single skill document."""
        has_pipeline = skill_contains("pipeline", case_sensitive=False)
        has_build_time = skill_contains(
            "build-time", case_sensitive=False
        ) or skill_contains("build time", case_sensitive=False)
        has_delivery = skill_contains("delivery", case_sensitive=False)
        assert has_pipeline and has_build_time and has_delivery, (
            "All three layers (pipeline, build-time quality, delivery) must be present"
        )


# ===========================================================================
# Language context flow guidance
# ===========================================================================


class TestLanguageContextFlow:
    """The skill must include language context flow guidance."""

    def test_language_context_referenced(self):
        """Language context flow must be described."""
        assert skill_contains(
            "language context", case_sensitive=False
        ) or skill_contains("language-context", case_sensitive=False)

    def test_context_flow_referenced(self):
        """Context flow must be described."""
        assert (
            skill_contains("context flow", case_sensitive=False)
            or skill_contains("context-flow", case_sensitive=False)
            or (
                skill_contains("context", case_sensitive=False)
                and skill_contains("flow", case_sensitive=False)
            )
        )


# ===========================================================================
# Stage 0 oversight: 3-gate mentor protocol
# ===========================================================================


class TestStage0OversightChecklist:
    """Stage 0: 3-gate mentor protocol (Section 6.9)."""

    def test_stage_0_referenced(self):
        """Stage 0 must be referenced in the oversight section."""
        assert skill_contains("Stage 0", case_sensitive=False)

    def test_three_gate_mentor_protocol_referenced(self):
        """3-gate mentor protocol must be referenced."""
        assert (
            skill_contains("3-gate", case_sensitive=False)
            or skill_contains("three-gate", case_sensitive=False)
            or skill_contains("three gate", case_sensitive=False)
            or skill_contains("3 gate", case_sensitive=False)
        )

    def test_mentor_protocol_referenced(self):
        """Mentor protocol must be referenced."""
        assert skill_contains("mentor", case_sensitive=False)

    def test_section_6_9_referenced(self):
        """Section 6.9 must be referenced."""
        assert skill_contains("6.9")

    def test_gate_0_1_hook_activation_referenced(self):
        """Gate 0.1 (hook activation) must be referenced."""
        assert skill_contains("0.1") or skill_contains(
            "hook activation", case_sensitive=False
        )

    def test_gate_0_2_context_approval_referenced(self):
        """Gate 0.2 (context approval) must be referenced."""
        assert skill_contains("0.2") or skill_contains(
            "context approval", case_sensitive=False
        )

    def test_gate_0_3_profile_approval_referenced(self):
        """Gate 0.3 (profile approval) must be referenced."""
        assert skill_contains("0.3") or skill_contains(
            "profile approval", case_sensitive=False
        )

    def test_full_pipeline_visibility_referenced(self):
        """Orchestrator provides framing using full-pipeline visibility."""
        assert (
            skill_contains("full-pipeline visibility", case_sensitive=False)
            or skill_contains("full pipeline visibility", case_sensitive=False)
            or skill_contains("pipeline visibility", case_sensitive=False)
        )

    def test_no_detection_checklist_for_stage_0(self):
        """Stage 0 has no detection checklist (nothing generated yet).

        We verify this by checking the skill mentions this explicitly.
        """
        assert (
            skill_contains("nothing generated", case_sensitive=False)
            or skill_contains("no detection checklist", case_sensitive=False)
            or skill_contains("no checklist", case_sensitive=False)
            or skill_contains("no separate", case_sensitive=False)
        )


# ===========================================================================
# Stage 1 oversight: 7 sub-protocols
# ===========================================================================


class TestStage1OversightChecklist:
    """Stage 1: 7 sub-protocols (Section 7.7)."""

    def test_stage_1_referenced(self):
        """Stage 1 must be referenced in the oversight section."""
        assert skill_contains("Stage 1", case_sensitive=False)

    def test_section_7_7_referenced(self):
        """Section 7.7 must be referenced."""
        assert skill_contains("7.7")

    def test_seven_sub_protocols_referenced(self):
        """7 sub-protocols must be referenced."""
        assert (
            skill_contains("7 sub-protocol", case_sensitive=False)
            or skill_contains("seven sub-protocol", case_sensitive=False)
            or skill_contains("7.7")
        )

    def test_decision_tracking_referenced(self):
        """Decision tracking (7.7.1) must be referenced."""
        assert skill_contains(
            "decision tracking", case_sensitive=False
        ) or skill_contains("7.7.1")

    def test_spec_draft_verification_referenced(self):
        """Spec draft verification (7.7.2) must be referenced."""
        assert skill_contains("spec draft", case_sensitive=False) or skill_contains(
            "7.7.2"
        )

    def test_feature_parity_checking_referenced(self):
        """Feature parity checking (7.7.3) must be referenced."""
        assert skill_contains("feature parity", case_sensitive=False) or skill_contains(
            "7.7.3"
        )

    def test_contradiction_detection_pass_referenced(self):
        """Contradiction detection pass (7.7.4) must be referenced."""
        assert skill_contains(
            "contradiction detection", case_sensitive=False
        ) or skill_contains("7.7.4")

    def test_contradiction_detection_delegated_to_subagent(self):
        """Contradiction detection (7.7.4) must be delegated to subagent."""
        assert skill_contains("7.7.4") or skill_contains(
            "contradiction", case_sensitive=False
        )
        assert skill_contains("subagent", case_sensitive=False) or skill_contains(
            "delegat", case_sensitive=False
        )

    def test_staleness_redundancy_pass_referenced(self):
        """Staleness/redundancy pass (7.7.5) must be referenced."""
        assert (
            skill_contains("staleness", case_sensitive=False)
            or skill_contains("redundancy", case_sensitive=False)
            or skill_contains("7.7.5")
        )

    def test_staleness_redundancy_delegated_to_subagent(self):
        """Staleness/redundancy pass (7.7.5) must be delegated to subagent."""
        assert (
            skill_contains("7.7.5")
            or skill_contains("staleness", case_sensitive=False)
            or skill_contains("redundancy", case_sensitive=False)
        )
        assert skill_contains("subagent", case_sensitive=False) or skill_contains(
            "delegat", case_sensitive=False
        )

    def test_referential_integrity_referenced(self):
        """Referential integrity (7.7.6) must be referenced."""
        assert skill_contains(
            "referential integrity", case_sensitive=False
        ) or skill_contains("7.7.6")

    def test_pipeline_fidelity_constraint_referenced(self):
        """Pipeline fidelity constraint (7.7.8) must be referenced."""
        assert skill_contains(
            "pipeline fidelity", case_sensitive=False
        ) or skill_contains("7.7.8")


# ===========================================================================
# Stage 2 oversight: 23-item checklist
# ===========================================================================


class TestStage2OversightChecklist:
    """Stage 2: 23-item checklist (Section 8.5)."""

    def test_stage_2_referenced(self):
        """Stage 2 must be referenced in the oversight section."""
        assert skill_contains("Stage 2", case_sensitive=False)

    def test_section_8_5_referenced(self):
        """Section 8.5 must be referenced."""
        assert skill_contains("8.5")

    def test_23_item_checklist_referenced(self):
        """23-item checklist must be referenced."""
        assert skill_contains("23") or skill_contains(
            "twenty-three", case_sensitive=False
        )

    def test_profile_blueprint_alignment_referenced(self):
        """Profile-blueprint alignment must be referenced."""
        assert (
            skill_contains("profile-blueprint", case_sensitive=False)
            or skill_contains("profile blueprint", case_sensitive=False)
            or (
                skill_contains("profile", case_sensitive=False)
                and skill_contains("alignment", case_sensitive=False)
            )
        )

    def test_contract_granularity_referenced(self):
        """Contract granularity must be referenced."""
        assert skill_contains(
            "contract granularity", case_sensitive=False
        ) or skill_contains("granularity", case_sensitive=False)

    def test_dag_validation_referenced(self):
        """DAG validation must be referenced."""
        assert skill_contains("DAG", case_sensitive=True) or skill_contains(
            "dag validation", case_sensitive=False
        )

    def test_pattern_catalog_cross_reference_referenced(self):
        """Pattern catalog cross-reference must be referenced."""
        assert skill_contains("pattern catalog", case_sensitive=False)

    def test_cross_language_dispatch_completeness_referenced(self):
        """Cross-language dispatch completeness must be referenced."""
        assert (
            skill_contains("cross-language dispatch", case_sensitive=False)
            or skill_contains("dispatch completeness", case_sensitive=False)
            or skill_contains("cross-language", case_sensitive=False)
        )

    def test_machinery_unit_tagging_referenced(self):
        """Machinery unit tagging verification must be referenced."""
        assert skill_contains("machinery unit", case_sensitive=False) or skill_contains(
            "tagging", case_sensitive=False
        )

    def test_assembly_map_annotation_completeness_referenced(self):
        """Assembly map annotation completeness must be referenced."""
        assert skill_contains("assembly map", case_sensitive=False)


# ===========================================================================
# Stage 3 oversight: 26-item checklist
# ===========================================================================


class TestStage3OversightChecklist:
    """Stage 3: 26-item checklist (Section 10.15)."""

    def test_stage_3_referenced(self):
        """Stage 3 must be referenced in the oversight section."""
        assert skill_contains("Stage 3", case_sensitive=False)

    def test_section_10_15_referenced(self):
        """Section 10.15 must be referenced."""
        assert skill_contains("10.15")

    def test_26_item_checklist_referenced(self):
        """26-item checklist must be referenced."""
        assert skill_contains("26") or skill_contains(
            "twenty-six", case_sensitive=False
        )

    def test_sub_stage_routing_correctness_referenced(self):
        """Sub-stage routing correctness must be referenced."""
        assert skill_contains(
            "sub-stage routing", case_sensitive=False
        ) or skill_contains("routing correctness", case_sensitive=False)

    def test_fix_ladder_progression_referenced(self):
        """Fix ladder progression must be referenced."""
        assert skill_contains("fix ladder", case_sensitive=False)

    def test_quality_gate_dispatch_referenced(self):
        """Quality gate dispatch must be referenced."""
        assert skill_contains("quality gate", case_sensitive=False)

    def test_red_green_run_validation_referenced(self):
        """Red/green run validation must be referenced."""
        assert (
            skill_contains("red/green", case_sensitive=False)
            or skill_contains("red green", case_sensitive=False)
            or (
                skill_contains("red", case_sensitive=False)
                and skill_contains("green", case_sensitive=False)
                and skill_contains("run validation", case_sensitive=False)
            )
        )

    def test_coverage_verification_referenced(self):
        """Coverage verification must be referenced."""
        assert skill_contains(
            "coverage verification", case_sensitive=False
        ) or skill_contains("coverage", case_sensitive=False)

    def test_language_dispatch_correctness_referenced(self):
        """Language dispatch correctness must be referenced."""
        assert skill_contains("language dispatch", case_sensitive=False)

    def test_stub_sentinel_presence_referenced(self):
        """Stub sentinel presence must be referenced."""
        assert skill_contains("stub sentinel", case_sensitive=False) or skill_contains(
            "sentinel", case_sensitive=False
        )

    def test_lessons_learned_integration_referenced(self):
        """Lessons learned integration must be referenced."""
        assert skill_contains(
            "lessons learned", case_sensitive=False
        ) or skill_contains("lessons-learned", case_sensitive=False)


# ===========================================================================
# Stage 4 oversight: 6-item checklist
# ===========================================================================


class TestStage4OversightChecklist:
    """Stage 4: 6-item checklist."""

    def test_stage_4_referenced(self):
        """Stage 4 must be referenced in the oversight section."""
        assert skill_contains("Stage 4", case_sensitive=False)

    def test_6_item_checklist_referenced(self):
        """6-item checklist size must be referenced for Stage 4."""
        # The number 6 must appear in the context of Stage 4
        assert skill_contains("6", case_sensitive=False)

    def test_integration_test_coverage_referenced(self):
        """Integration test coverage of cross-unit interfaces must be referenced."""
        assert (
            skill_contains("integration test", case_sensitive=False)
            or skill_contains("cross-unit interface", case_sensitive=False)
            or skill_contains("cross-unit", case_sensitive=False)
        )

    def test_assembly_retry_counter_tracking_referenced(self):
        """Assembly retry counter tracking must be referenced."""
        assert skill_contains("retry counter", case_sensitive=False) or skill_contains(
            "assembly retry", case_sensitive=False
        )

    def test_regression_adaptation_review_referenced(self):
        """Regression adaptation review must be referenced."""
        assert skill_contains(
            "regression adaptation", case_sensitive=False
        ) or skill_contains("regression", case_sensitive=False)

    def test_stage_3_completion_validation_referenced(self):
        """Stage 3 completion validation must be referenced."""
        assert (
            skill_contains("completion validation", case_sensitive=False)
            or skill_contains("stage 3 completion", case_sensitive=False)
            or skill_contains("Stage 3 completion", case_sensitive=False)
        )

    def test_assembly_map_currency_referenced(self):
        """Assembly map currency must be referenced."""
        assert skill_contains("assembly map", case_sensitive=False)


# ===========================================================================
# Stage 5 oversight: 10-item checklist
# ===========================================================================


class TestStage5OversightChecklist:
    """Stage 5: 10-item checklist (Section 12.17)."""

    def test_stage_5_referenced(self):
        """Stage 5 must be referenced in the oversight section."""
        assert skill_contains("Stage 5", case_sensitive=False)

    def test_section_12_17_referenced(self):
        """Section 12.17 must be referenced."""
        assert skill_contains("12.17")

    def test_10_item_checklist_referenced(self):
        """10-item checklist size must be referenced for Stage 5."""
        assert skill_contains("10", case_sensitive=False)

    def test_cross_artifact_consistency_referenced(self):
        """Cross-artifact consistency must be referenced."""
        assert skill_contains("cross-artifact", case_sensitive=False) or skill_contains(
            "cross artifact", case_sensitive=False
        )

    def test_assembly_map_bijectivity_referenced(self):
        """Assembly map bijectivity must be referenced."""
        assert skill_contains("bijectiv", case_sensitive=False) or skill_contains(
            "assembly map", case_sensitive=False
        )

    def test_assembly_map_completeness_referenced(self):
        """Assembly map completeness must be referenced."""
        assert skill_contains("completeness", case_sensitive=False)

    def test_no_surviving_workspace_references(self):
        """No surviving workspace references must be checked."""
        assert skill_contains(
            "workspace reference", case_sensitive=False
        ) or skill_contains("surviving", case_sensitive=False)

    def test_commit_order_referenced(self):
        """Commit order must be referenced."""
        assert skill_contains("commit order", case_sensitive=False) or skill_contains(
            "commit", case_sensitive=False
        )

    def test_readme_content_referenced(self):
        """README content must be referenced."""
        assert skill_contains("README", case_sensitive=False)

    def test_quality_config_accuracy_referenced(self):
        """Quality config accuracy must be referenced."""
        assert skill_contains("quality config", case_sensitive=False) or skill_contains(
            "quality configuration", case_sensitive=False
        )

    def test_changelog_content_referenced(self):
        """Changelog content must be referenced."""
        assert skill_contains("changelog", case_sensitive=False)

    def test_validation_meta_oversight_referenced(self):
        """Validation meta-oversight must be referenced."""
        assert (
            skill_contains("meta-oversight", case_sensitive=False)
            or skill_contains("meta oversight", case_sensitive=False)
            or skill_contains("validation", case_sensitive=False)
        )

    def test_structural_check_ran_referenced(self):
        """Structural check ran must be referenced."""
        assert skill_contains("structural check", case_sensitive=False)

    def test_compliance_scan_ran_referenced(self):
        """Compliance scan ran must be referenced."""
        assert skill_contains("compliance scan", case_sensitive=False)

    def test_unused_function_check_ran_referenced(self):
        """Unused function check ran must be referenced."""
        assert skill_contains(
            "unused function", case_sensitive=False
        ) or skill_contains("unused", case_sensitive=False)


# ===========================================================================
# Stage 6 oversight: 9-item checkpoint-annotated checklist
# ===========================================================================


class TestStage6OversightChecklist:
    """Stage 6: 9-item checkpoint-annotated checklist (Section 12.18.13)."""

    def test_stage_6_referenced(self):
        """Stage 6 must be referenced in the oversight section."""
        assert skill_contains("Stage 6", case_sensitive=False)

    def test_section_12_18_13_referenced(self):
        """Section 12.18.13 must be referenced."""
        assert skill_contains("12.18.13")

    def test_9_item_checklist_referenced(self):
        """9-item checklist size must be referenced for Stage 6."""
        assert skill_contains("9", case_sensitive=False)

    def test_checkpoint_annotated_referenced(self):
        """Checkpoint-annotated checklist must be referenced."""
        assert skill_contains("checkpoint", case_sensitive=False)

    def test_after_triage_checkpoint_referenced(self):
        """After triage checkpoint (3 items) must be referenced."""
        assert skill_contains("triage", case_sensitive=False)

    def test_after_repair_checkpoint_referenced(self):
        """After repair checkpoint (2 items) must be referenced."""
        assert skill_contains("repair", case_sensitive=False)

    def test_after_regression_test_checkpoint_referenced(self):
        """After regression test checkpoint (2 items) must be referenced."""
        assert skill_contains("regression", case_sensitive=False)

    def test_after_lessons_learned_checkpoint_referenced(self):
        """After lessons learned checkpoint (2 items) must be referenced."""
        assert skill_contains(
            "lessons learned", case_sensitive=False
        ) or skill_contains("lessons-learned", case_sensitive=False)

    def test_orchestrator_detects_issues_referenced(self):
        """Orchestrator detects issues; all fixing flows through agents."""
        assert skill_contains("detect", case_sensitive=False)
        assert skill_contains("agent", case_sensitive=False)


# ===========================================================================
# Stage 7 (oracle): no separate oversight protocol
# ===========================================================================


class TestStage7OversightChecklist:
    """Stage 7 (oracle): no separate oversight protocol."""

    def test_stage_7_referenced(self):
        """Stage 7 must be referenced in the oversight section."""
        assert skill_contains("Stage 7", case_sensitive=False)

    def test_oracle_referenced(self):
        """Oracle must be referenced for Stage 7."""
        assert skill_contains("oracle", case_sensitive=False)

    def test_no_separate_oversight_protocol(self):
        """Stage 7 must state there is no separate oversight protocol."""
        # Check that oracle is described as an orchestrator-level construct
        # or that there is no separate protocol for it
        assert (
            skill_contains("no separate oversight", case_sensitive=False)
            or skill_contains("orchestrator-level construct", case_sensitive=False)
            or skill_contains("orchestrator level construct", case_sensitive=False)
            or skill_contains("no oversight protocol", case_sensitive=False)
            or skill_contains("no separate protocol", case_sensitive=False)
        )


# ===========================================================================
# All stages present
# ===========================================================================


class TestAllStagesPresent:
    """All stages (0-7) must be mentioned in the per-stage oversight section."""

    @pytest.mark.parametrize("stage_num", [0, 1, 2, 3, 4, 5, 6, 7])
    def test_stage_number_present(self, stage_num):
        """Each stage number must appear in the skill content."""
        assert skill_contains(f"Stage {stage_num}", case_sensitive=False), (
            f"Stage {stage_num} not found in ORCHESTRATION_SKILL"
        )


# ===========================================================================
# Orchestrator Pipeline Fidelity Invariant
# ===========================================================================


class TestPipelineFidelityInvariant:
    """The skill must include the Orchestrator Pipeline Fidelity Invariant."""

    def test_pipeline_fidelity_invariant_referenced(self):
        """Pipeline Fidelity Invariant must be referenced."""
        assert skill_contains(
            "Pipeline Fidelity Invariant", case_sensitive=False
        ) or skill_contains("pipeline fidelity", case_sensitive=False)

    def test_invariant_keyword_present(self):
        """The word 'invariant' must appear in context of pipeline fidelity."""
        assert skill_contains("invariant", case_sensitive=False)


# ===========================================================================
# Orchestrator Self-Escalation Invariant
# ===========================================================================


class TestSelfEscalationInvariant:
    """Self-Escalation Invariant: loop detection and break-glass escalation."""

    def test_self_escalation_invariant_referenced(self):
        """Self-Escalation Invariant must be referenced."""
        assert (
            skill_contains("Self-Escalation", case_sensitive=False)
            or skill_contains("self escalation", case_sensitive=False)
            or skill_contains("self-escalation invariant", case_sensitive=False)
        )

    def test_loop_detection_referenced(self):
        """Loop condition detection must be referenced."""
        assert skill_contains("loop", case_sensitive=False)

    def test_consecutive_dispatch_threshold_referenced(self):
        """3+ consecutive identical dispatches must be referenced."""
        assert skill_contains("3", case_sensitive=True) and (
            skill_contains("consecutive", case_sensitive=False)
            or skill_contains("same action", case_sensitive=False)
        )

    def test_no_state_change_condition_referenced(self):
        """No state change condition must be referenced."""
        assert skill_contains("state change", case_sensitive=False) or skill_contains(
            "no change", case_sensitive=False
        )

    def test_break_glass_escalation_referenced(self):
        """Break-glass mode escalation must be referenced."""
        assert skill_contains("break-glass", case_sensitive=False) or skill_contains(
            "break glass", case_sensitive=False
        )


# ===========================================================================
# Spec refresh behavior at phase transitions
# ===========================================================================


class TestSpecRefreshBehavior:
    """Spec refresh at phase transitions (Section 43.10, E/F self-builds)."""

    def test_spec_refresh_concept_referenced(self):
        """Spec refresh behavior must be referenced."""
        assert (
            skill_contains("spec refresh", case_sensitive=False)
            or skill_contains("re-read", case_sensitive=False)
            or skill_contains("reread", case_sensitive=False)
        )

    def test_section_43_10_referenced(self):
        """Section 43.10 must be referenced."""
        assert skill_contains("43.10")

    def test_ef_self_builds_referenced(self):
        """E/F self-builds must be referenced."""
        assert (
            skill_contains("self-build", case_sensitive=False)
            or skill_contains("self build", case_sensitive=False)
            or skill_contains("E/F", case_sensitive=True)
        )

    def test_phase_transition_concept_referenced(self):
        """Phase transitions must be referenced."""
        assert skill_contains("phase transition", case_sensitive=False)

    def test_pass_1_start_transition_point_referenced(self):
        """Pass 1 start must be a refresh transition point."""
        assert skill_contains("Pass 1", case_sensitive=False)

    def test_pass_1_to_transition_gate_referenced(self):
        """Pass 1 to transition gate must be a refresh transition point."""
        assert skill_contains("transition gate", case_sensitive=False)

    def test_pass_2_start_transition_point_referenced(self):
        """Pass 2 start must be a refresh transition point."""
        assert skill_contains("Pass 2", case_sensitive=False)

    def test_oracle_start_transition_point_referenced(self):
        """Oracle start must be a refresh transition point."""
        assert skill_contains("oracle", case_sensitive=False)

    def test_three_orchestrator_rules_at_refresh(self):
        """Three orchestrator rules must be restated at each refresh point."""
        # Rule 1: re-read the spec
        has_reread = skill_contains("re-read", case_sensitive=False) or skill_contains(
            "reread", case_sensitive=False
        )
        # Rule 2: can only plan and delegate -- never execute directly
        has_delegate = skill_contains(
            "delegat", case_sensitive=False
        ) or skill_contains("never execute directly", case_sensitive=False)
        # Rule 3: must monitor subagent output
        has_monitor = skill_contains("monitor", case_sensitive=False) or skill_contains(
            "intervene", case_sensitive=False
        )
        assert has_reread and has_delegate and has_monitor, (
            "All three orchestrator rules must be present at refresh points"
        )

    def test_rule_never_execute_directly(self):
        """Rule 2: orchestrator can only plan and delegate, never execute."""
        assert (
            skill_contains("never execute directly", case_sensitive=False)
            or skill_contains("never execute", case_sensitive=False)
            or (
                skill_contains("plan", case_sensitive=False)
                and skill_contains("delegate", case_sensitive=False)
            )
        )

    def test_rule_monitor_subagent_output(self):
        """Rule 3: monitor subagent output and intervene when deviation."""
        assert skill_contains("monitor", case_sensitive=False) or skill_contains(
            "subagent", case_sensitive=False
        )
        assert skill_contains("deviation", case_sensitive=False) or skill_contains(
            "intervene", case_sensitive=False
        )


# ===========================================================================
# Hard Stop Protocol reference
# ===========================================================================


class TestHardStopProtocol:
    """Hard Stop Protocol reference (Section 41)."""

    def test_hard_stop_protocol_referenced(self):
        """Hard Stop Protocol must be referenced."""
        assert (
            skill_contains("Hard Stop", case_sensitive=False)
            or skill_contains("hard stop", case_sensitive=False)
            or skill_contains("hard-stop", case_sensitive=False)
        )

    def test_section_41_referenced(self):
        """Section 41 must be referenced."""
        assert skill_contains("Section 41", case_sensitive=False) or skill_contains(
            "41"
        )

    def test_pass_1_ef_self_builds_referenced(self):
        """During Pass 1 of E/F self-builds."""
        assert skill_contains("Pass 1", case_sensitive=False)

    def test_builder_script_bug_detection_referenced(self):
        """Builder script bug detection must be referenced."""
        assert (
            skill_contains("builder script", case_sensitive=False)
            or skill_contains("bug detect", case_sensitive=False)
            or skill_contains("bug", case_sensitive=False)
        )

    def test_save_artifacts_referenced(self):
        """Save artifacts must be referenced."""
        assert skill_contains("save artifact", case_sensitive=False) or skill_contains(
            "artifacts", case_sensitive=False
        )

    def test_bug_analysis_referenced(self):
        """Produce bug analysis must be referenced."""
        assert skill_contains("bug analysis", case_sensitive=False) or skill_contains(
            "analysis", case_sensitive=False
        )

    def test_svp_bug_command_referenced(self):
        """Switch to SVP N workspace for /svp:bug."""
        assert skill_contains("/svp:bug", case_sensitive=False) or skill_contains(
            "svp:bug", case_sensitive=False
        )

    def test_checkpoint_restart_referenced(self):
        """Restart from checkpoint must be referenced."""
        assert skill_contains("checkpoint", case_sensitive=False) and skill_contains(
            "restart", case_sensitive=False
        )

    def test_must_not_modify_builder_scripts_directly(self):
        """Orchestrator MUST NOT modify builder scripts directly."""
        assert (
            skill_contains("MUST NOT modify builder scripts", case_sensitive=False)
            or skill_contains("must not modify builder", case_sensitive=False)
            or skill_contains(
                "not modify builder scripts directly", case_sensitive=False
            )
            or (
                skill_contains("builder script", case_sensitive=False)
                and skill_contains("must not", case_sensitive=False)
            )
        )


# ===========================================================================
# Break-glass behavioral guidance
# ===========================================================================


class TestBreakGlassBehavioralGuidance:
    """Break-glass behavioral guidance (Section 43.9)."""

    def test_break_glass_referenced(self):
        """Break-glass must be referenced."""
        assert (
            skill_contains("break-glass", case_sensitive=False)
            or skill_contains("break glass", case_sensitive=False)
            or skill_contains("break_glass", case_sensitive=False)
        )

    def test_section_43_9_referenced(self):
        """Section 43.9 must be referenced."""
        assert skill_contains("43.9")

    def test_routing_script_emits_break_glass_action_type(self):
        """Routing script emits break_glass action type."""
        assert skill_contains("break_glass", case_sensitive=False) or skill_contains(
            "break-glass", case_sensitive=False
        )

    def test_permitted_action_present_failure_diagnostics(self):
        """Permitted action 1: present failure diagnostics to human."""
        assert skill_contains(
            "failure diagnostics", case_sensitive=False
        ) or skill_contains("diagnostics", case_sensitive=False)

    def test_permitted_action_write_lessons_learned(self):
        """Permitted action 2: write lessons-learned entry."""
        assert skill_contains(
            "lessons-learned", case_sensitive=False
        ) or skill_contains("lessons learned", case_sensitive=False)

    def test_permitted_action_mark_deferred_broken(self):
        """Permitted action 3: mark unit deferred_broken with human consent."""
        assert skill_contains(
            "deferred_broken", case_sensitive=False
        ) or skill_contains("deferred broken", case_sensitive=False)

    def test_permitted_action_human_consent_for_deferred_broken(self):
        """Marking deferred_broken requires human consent."""
        assert skill_contains("human consent", case_sensitive=False) or skill_contains(
            "consent", case_sensitive=False
        )

    def test_permitted_action_retry_with_human_guidance(self):
        """Permitted action 4: retry with human-provided guidance."""
        assert (
            skill_contains("human-provided guidance", case_sensitive=False)
            or skill_contains("human provided guidance", case_sensitive=False)
            or (
                skill_contains("retry", case_sensitive=False)
                and skill_contains("guidance", case_sensitive=False)
            )
        )

    def test_retry_max_3_per_unit_per_pass(self):
        """Retry is limited to max 3 per unit per pass."""
        assert (
            skill_contains("max 3", case_sensitive=False)
            or skill_contains("3 per unit", case_sensitive=False)
            or (
                skill_contains("3", case_sensitive=True)
                and skill_contains("per unit", case_sensitive=False)
            )
        )

    def test_permitted_action_escalate_to_pipeline_restart(self):
        """Permitted action 5: escalate to pipeline restart."""
        assert skill_contains(
            "pipeline restart", case_sensitive=False
        ) or skill_contains("escalate", case_sensitive=False)

    def test_forbidden_fix_code_directly(self):
        """Forbidden: fix code directly."""
        assert skill_contains(
            "fix code directly", case_sensitive=False
        ) or skill_contains("forbidden", case_sensitive=False)

    def test_forbidden_modify_spec_blueprint(self):
        """Forbidden: modify spec/blueprint."""
        assert (
            skill_contains("modify spec", case_sensitive=False)
            or skill_contains("spec/blueprint", case_sensitive=False)
            or skill_contains("modify blueprint", case_sensitive=False)
            or (
                skill_contains("forbidden", case_sensitive=False)
                and skill_contains("spec", case_sensitive=False)
            )
        )

    def test_forbidden_skip_stages(self):
        """Forbidden: skip stages."""
        assert (
            skill_contains("skip stage", case_sensitive=False)
            or skill_contains("skip stages", case_sensitive=False)
            or (
                skill_contains("forbidden", case_sensitive=False)
                and skill_contains("skip", case_sensitive=False)
            )
        )


# ===========================================================================
# Cross-cutting: content integrity checks
# ===========================================================================


class TestContentIntegrityChecks:
    """Cross-cutting checks that verify overall content coherence."""

    def test_skill_references_svp(self):
        """The skill must reference SVP (Stratified Verification Pipeline)."""
        assert skill_contains("SVP", case_sensitive=True)

    def test_skill_references_orchestrator(self):
        """The skill must reference the orchestrator role."""
        assert skill_contains("orchestrator", case_sensitive=False)

    def test_skill_references_pipeline(self):
        """The skill must reference the pipeline."""
        assert skill_contains("pipeline", case_sensitive=False)

    def test_skill_references_agent(self):
        """The skill must reference agents (subagents are the execution model)."""
        assert skill_contains("agent", case_sensitive=False)

    def test_skill_contains_multiple_sections(self):
        """The skill must contain multiple markdown sections."""
        headings = re.findall(r"^#+\s+", ORCHESTRATION_SKILL, re.MULTILINE)
        assert len(headings) >= 5, (
            f"Expected at least 5 markdown headings, found {len(headings)}"
        )

    def test_frontmatter_and_body_both_present(self):
        """The skill must have both frontmatter and body content."""
        fm = extract_frontmatter()
        assert len(fm.strip()) > 0, "Frontmatter is empty"
        # Body is everything after the closing '---'
        match = re.match(r"^---\s*\n.*?\n---\s*\n(.*)", ORCHESTRATION_SKILL, re.DOTALL)
        assert match is not None, "Could not extract body after frontmatter"
        body = match.group(1)
        assert len(body.strip()) > 0, "Body after frontmatter is empty"

    def test_no_stub_sentinel_in_content(self):
        """The skill content must not contain the stub sentinel."""
        assert "__SVP_STUB__" not in ORCHESTRATION_SKILL

    def test_skill_mentions_all_key_concepts(self):
        """Verify all key concepts from the contract appear somewhere."""
        key_concepts = [
            "routing",
            "action",
            "pipeline",
            "orchestrator",
            "agent",
            "stage",
        ]
        for concept in key_concepts:
            assert skill_contains(concept, case_sensitive=False), (
                f"Key concept '{concept}' not found in ORCHESTRATION_SKILL"
            )

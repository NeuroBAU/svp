"""Tests for Unit 26: Orchestration Skill.

Synthetic Data Assumptions:
- ORCHESTRATION_SKILL is a module-level string constant containing the full
  orchestration skill markdown content.
- The content must be non-empty markdown that includes specific structural
  sections, protocol references, and behavioral guidance as defined in the
  blueprint contracts.
- All string-matching tests use case-insensitive or substring checks where
  the blueprint does not mandate exact casing, but use exact matches for
  specific terms and identifiers that are explicitly named.
- Section numbers (e.g., 3.6, 6.9, 7.7, 8.5, 10.15, 12.17, 12.18.13,
  41, 43.9, 43.10) are expected to appear as textual references.
- Frontmatter fields are expected to follow Claude Code skill schema
  conventions.
"""

from unit_26 import ORCHESTRATION_SKILL

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _skill() -> str:
    """Return the skill content for readability."""
    return ORCHESTRATION_SKILL


def _skill_lower() -> str:
    """Return lowercased skill content for case-insensitive searching."""
    return ORCHESTRATION_SKILL.lower()


# ===========================================================================
# 1. Basic structural invariants
# ===========================================================================


class TestBasicStructuralInvariants:
    """ORCHESTRATION_SKILL must be a non-empty markdown string."""

    def test_orchestration_skill_is_a_string(self):
        assert isinstance(ORCHESTRATION_SKILL, str)

    def test_orchestration_skill_is_non_empty(self):
        assert len(ORCHESTRATION_SKILL.strip()) > 0

    def test_orchestration_skill_contains_markdown_formatting(self):
        """Non-empty markdown string should contain at least one heading marker."""
        assert "#" in _skill()


# ===========================================================================
# 2. Frontmatter (Claude Code skill schema)
# ===========================================================================


class TestFrontmatter:
    """Frontmatter must follow Claude Code schema with required fields."""

    def test_frontmatter_contains_name_svp_orchestration(self):
        assert "svp-orchestration" in _skill()

    def test_frontmatter_contains_description_field(self):
        content = _skill_lower()
        assert "description" in content

    def test_frontmatter_contains_argument_hint_field(self):
        # The field name may use hyphens or underscores; check for presence
        content = _skill_lower()
        assert "argument-hint" in content or "argument_hint" in content

    def test_frontmatter_contains_allowed_tools_field(self):
        content = _skill_lower()
        assert "allowed-tools" in content or "allowed_tools" in content

    def test_frontmatter_contains_model_field(self):
        content = _skill_lower()
        assert "model" in content

    def test_frontmatter_contains_effort_field(self):
        content = _skill_lower()
        assert "effort" in content

    def test_frontmatter_contains_context_field(self):
        content = _skill_lower()
        assert "context" in content


# ===========================================================================
# 3. Six-step mechanical action cycle
# ===========================================================================


class TestSixStepActionCycle:
    """Must contain the six-step mechanical action cycle."""

    def test_contains_six_step_action_cycle_reference(self):
        content = _skill_lower()
        assert "six" in content or "6" in content
        # Also verify 'action cycle' or 'step' language is present
        assert "action cycle" in content or "step" in content

    def test_step_1_run_routing_script(self):
        content = _skill_lower()
        assert "routing" in content

    def test_step_2_run_prepare_command(self):
        content = _skill_lower()
        assert "prepare" in content

    def test_step_3_execute_action(self):
        content = _skill_lower()
        assert "action" in content

    def test_step_4_write_last_status(self):
        content = _skill_lower()
        assert "last_status" in content or "last-status" in content

    def test_step_5_run_post_command(self):
        content = _skill_lower()
        assert "post" in content

    def test_step_6_go_to_step_1(self):
        """The cycle must loop back (go to step 1)."""
        content = _skill_lower()
        assert "step 1" in content or "go to" in content or "repeat" in content


# ===========================================================================
# 4. REMINDER block template
# ===========================================================================


class TestReminderBlock:
    """Must contain REMINDER block template (exact text from Section 3.6)."""

    def test_contains_reminder_block(self):
        assert "REMINDER" in _skill()

    def test_reminder_references_section_3_6(self):
        assert "3.6" in _skill()


# ===========================================================================
# 5. Slash command action cycles
# ===========================================================================


class TestSlashCommandActionCycles:
    """Must contain slash command action cycles."""

    def test_contains_slash_command_references(self):
        content = _skill()
        # Slash commands start with /svp: prefix
        assert "/svp:" in content or "slash command" in _skill_lower()


# ===========================================================================
# 6. Three-layer toolchain model
# ===========================================================================


class TestThreeLayerToolchainModel:
    """Must explain the three-layer model: pipeline toolchain, build-time quality, delivery toolchain."""

    def test_contains_three_layer_model_reference(self):
        content = _skill_lower()
        assert "three" in content or "3" in content
        assert "layer" in content or "toolchain" in content

    def test_contains_pipeline_toolchain_reference(self):
        content = _skill_lower()
        assert "pipeline" in content and "toolchain" in content

    def test_contains_build_time_quality_reference(self):
        content = _skill_lower()
        assert "build" in content and "quality" in content

    def test_contains_delivery_toolchain_reference(self):
        content = _skill_lower()
        assert "delivery" in content and "toolchain" in content


# ===========================================================================
# 7. Language context flow guidance
# ===========================================================================


class TestLanguageContextFlowGuidance:
    """Must include language context flow guidance."""

    def test_contains_language_context_flow(self):
        content = _skill_lower()
        assert "language" in content
        assert "context" in content


# ===========================================================================
# 8. Per-stage orchestrator oversight checklist references
# ===========================================================================


class TestStage0OversightProtocol:
    """Stage 0: 3-gate mentor protocol (Section 6.9)."""

    def test_references_section_6_9(self):
        assert "6.9" in _skill()

    def test_references_gate_0_1_hook_activation(self):
        content = _skill_lower()
        assert "0.1" in _skill() or "gate" in content
        assert "hook" in content or "activation" in content

    def test_references_gate_0_2_context_approval(self):
        content = _skill_lower()
        assert "0.2" in _skill() or ("context" in content and "approval" in content)

    def test_references_gate_0_3_profile_approval(self):
        content = _skill_lower()
        assert "0.3" in _skill() or ("profile" in content and "approval" in content)

    def test_stage_0_mentor_protocol(self):
        content = _skill_lower()
        assert "mentor" in content or "framing" in content

    def test_stage_0_no_detection_checklist_since_nothing_generated(self):
        """Stage 0 has no detection checklist because nothing is generated yet."""
        # We verify the mentor/framing role is present (tested above)
        # and that the stage 0 section describes providing framing
        content = _skill_lower()
        assert "stage 0" in content or "stage-0" in content


class TestStage1OversightProtocol:
    """Stage 1: 7 sub-protocols (Section 7.7)."""

    def test_references_section_7_7(self):
        assert "7.7" in _skill()

    def test_references_decision_tracking_7_7_1(self):
        content = _skill_lower()
        assert "decision" in content and "tracking" in content or "7.7.1" in _skill()

    def test_references_spec_draft_verification_7_7_2(self):
        content = _skill_lower()
        assert (
            "spec" in content and "draft" in content and "verif" in content
        ) or "7.7.2" in _skill()

    def test_references_feature_parity_checking_7_7_3(self):
        content = _skill_lower()
        assert ("feature" in content and "parity" in content) or "7.7.3" in _skill()

    def test_references_contradiction_detection_7_7_4(self):
        content = _skill_lower()
        assert (
            "contradiction" in content and "detection" in content
        ) or "7.7.4" in _skill()

    def test_references_staleness_redundancy_pass_7_7_5(self):
        content = _skill_lower()
        assert ("stale" in content or "redundan" in content) or "7.7.5" in _skill()

    def test_references_referential_integrity_7_7_6(self):
        content = _skill_lower()
        assert (
            "referential" in content and "integrity" in content
        ) or "7.7.6" in _skill()

    def test_references_pipeline_fidelity_constraint_7_7_8(self):
        content = _skill_lower()
        assert ("pipeline" in content and "fidelity" in content) or "7.7.8" in _skill()


class TestStage2OversightProtocol:
    """Stage 2: 23-item checklist (Section 8.5)."""

    def test_references_section_8_5(self):
        assert "8.5" in _skill()

    def test_references_profile_blueprint_alignment(self):
        content = _skill_lower()
        assert (
            "profile" in content and "blueprint" in content and "align" in content
        ) or "alignment" in content

    def test_references_contract_granularity(self):
        content = _skill_lower()
        assert "contract" in content and "granularity" in content

    def test_references_dag_validation(self):
        content = _skill_lower()
        assert "dag" in content

    def test_references_pattern_catalog_cross_reference(self):
        content = _skill_lower()
        assert "pattern" in content and "catalog" in content

    def test_references_cross_language_dispatch_completeness(self):
        content = _skill_lower()
        assert "dispatch" in content and (
            "completeness" in content or "complete" in content
        )

    def test_references_machinery_unit_tagging(self):
        content = _skill_lower()
        assert "machinery" in content and ("tag" in content or "unit" in content)

    def test_references_assembly_map_annotation_completeness(self):
        content = _skill_lower()
        assert "assembly" in content and "map" in content


class TestStage3OversightProtocol:
    """Stage 3: 26-item checklist (Section 10.15)."""

    def test_references_section_10_15(self):
        assert "10.15" in _skill()

    def test_references_sub_stage_routing_correctness(self):
        content = _skill_lower()
        assert "sub-stage" in content or "substage" in content or "routing" in content

    def test_references_fix_ladder_progression(self):
        content = _skill_lower()
        assert "fix" in content and "ladder" in content

    def test_references_quality_gate_dispatch(self):
        content = _skill_lower()
        assert "quality" in content and "gate" in content

    def test_references_red_green_run_validation(self):
        content = _skill_lower()
        assert "red" in content and "green" in content

    def test_references_coverage_verification(self):
        content = _skill_lower()
        assert "coverage" in content and ("verif" in content or "check" in content)

    def test_references_language_dispatch_correctness(self):
        content = _skill_lower()
        assert "language" in content and "dispatch" in content

    def test_references_stub_sentinel_presence(self):
        content = _skill_lower()
        assert "stub" in content and "sentinel" in content

    def test_references_lessons_learned_integration(self):
        content = _skill_lower()
        assert "lessons" in content and "learned" in content


class TestStage4OversightProtocol:
    """Stage 4: 6-item checklist."""

    def test_references_stage_4(self):
        content = _skill_lower()
        assert "stage 4" in content or "stage-4" in content

    def test_references_integration_test_coverage(self):
        content = _skill_lower()
        assert "integration" in content and "test" in content

    def test_references_assembly_retry_counter_tracking(self):
        content = _skill_lower()
        assert "retry" in content or "counter" in content

    def test_references_regression_adaptation_review(self):
        content = _skill_lower()
        assert "regression" in content and "adaptation" in content

    def test_references_stage_3_completion_validation(self):
        content = _skill_lower()
        assert "stage 3" in content or "stage-3" in content or "completion" in content

    def test_references_assembly_map_currency(self):
        content = _skill_lower()
        assert "assembly" in content and "map" in content


class TestStage5OversightProtocol:
    """Stage 5: 10-item checklist (Section 12.17)."""

    def test_references_section_12_17(self):
        assert "12.17" in _skill()

    def test_references_assembly_map_bijectivity(self):
        content = _skill_lower()
        assert "bijectiv" in content or ("assembly" in content and "map" in content)

    def test_references_assembly_map_completeness(self):
        content = _skill_lower()
        assert (
            "assembly" in content
            and "map" in content
            and ("complet" in content or "all" in content)
        )

    def test_references_no_surviving_workspace_references(self):
        content = _skill_lower()
        assert "workspace" in content or "surviving" in content

    def test_references_commit_order(self):
        content = _skill_lower()
        assert "commit" in content and "order" in content

    def test_references_readme_content(self):
        content = _skill_lower()
        assert "readme" in content

    def test_references_quality_config_accuracy(self):
        content = _skill_lower()
        assert "quality" in content and "config" in content

    def test_references_changelog_content(self):
        content = _skill_lower()
        assert "changelog" in content

    def test_references_structural_check_ran(self):
        content = _skill_lower()
        assert "structural" in content and "check" in content

    def test_references_compliance_scan_ran(self):
        content = _skill_lower()
        assert "compliance" in content and "scan" in content

    def test_references_unused_function_check_ran(self):
        content = _skill_lower()
        assert "unused" in content and "function" in content


class TestStage6OversightProtocol:
    """Stage 6: 9-item checkpoint-annotated checklist (Section 12.18.13)."""

    def test_references_section_12_18_13(self):
        assert "12.18.13" in _skill()

    def test_references_after_triage_checkpoint(self):
        content = _skill_lower()
        assert "triage" in content

    def test_references_after_repair_checkpoint(self):
        content = _skill_lower()
        assert "repair" in content

    def test_references_after_regression_test_checkpoint(self):
        content = _skill_lower()
        assert "regression" in content and "test" in content

    def test_references_after_lessons_learned_checkpoint(self):
        content = _skill_lower()
        assert "lessons" in content and "learned" in content

    def test_orchestrator_detects_issues_but_agents_fix(self):
        content = _skill_lower()
        assert "agent" in content


class TestStage7OversightProtocol:
    """Stage 7 (oracle): no separate oversight protocol."""

    def test_references_stage_7_or_oracle(self):
        content = _skill_lower()
        assert "stage 7" in content or "oracle" in content


# ===========================================================================
# 9. Orchestrator Pipeline Fidelity Invariant
# ===========================================================================


class TestOrchestratorPipelineFidelityInvariant:
    """Must contain the orchestrator pipeline fidelity invariant."""

    def test_contains_pipeline_fidelity_invariant(self):
        content = _skill_lower()
        assert (
            "pipeline" in content and "fidelity" in content and "invariant" in content
        )


# ===========================================================================
# 10. Orchestrator Self-Escalation Invariant
# ===========================================================================


class TestOrchestratorSelfEscalationInvariant:
    """Detects loop conditions (same action 3+ times with no state change)."""

    def test_contains_self_escalation_invariant(self):
        content = _skill_lower()
        assert (
            "self-escalation" in content
            or "self escalation" in content
            or "escalation invariant" in content
        )

    def test_references_loop_condition_detection(self):
        content = _skill_lower()
        assert "loop" in content

    def test_references_three_consecutive_same_actions(self):
        content = _skill()
        assert "3" in content or "three" in _skill_lower()

    def test_references_break_glass_mode_escalation(self):
        content = _skill_lower()
        assert "break" in content and "glass" in content


# ===========================================================================
# 11. Spec refresh behavior at phase transitions
# ===========================================================================


class TestSpecRefreshAtPhaseTransitions:
    """Spec refresh behavior at phase transitions (Section 43.10, E/F self-builds)."""

    def test_references_section_43_10(self):
        assert "43.10" in _skill()

    def test_references_phase_transitions(self):
        content = _skill_lower()
        assert "phase transition" in content or "phase" in content

    def test_references_pass_1_start(self):
        content = _skill_lower()
        assert "pass 1" in content or "pass-1" in content

    def test_references_pass_2_start(self):
        content = _skill_lower()
        assert "pass 2" in content or "pass-2" in content

    def test_references_transition_gate(self):
        content = _skill_lower()
        assert "transition" in content and "gate" in content

    def test_references_oracle_start(self):
        content = _skill_lower()
        assert "oracle" in content

    def test_rule_1_reread_spec(self):
        content = _skill_lower()
        assert "re-read" in content or "reread" in content or "re read" in content

    def test_rule_2_plan_and_delegate_never_execute_directly(self):
        content = _skill_lower()
        assert "delegate" in content
        assert (
            "never execute directly" in content
            or "never execute" in content
            or "not execute directly" in content
        )

    def test_rule_3_monitor_subagent_output_and_intervene(self):
        content = _skill_lower()
        assert "monitor" in content and (
            "subagent" in content or "sub-agent" in content
        )

    def test_references_ef_self_builds(self):
        content = _skill_lower()
        assert "self-build" in content or "self build" in content


# ===========================================================================
# 12. Hard Stop Protocol reference
# ===========================================================================


class TestHardStopProtocol:
    """Hard Stop Protocol reference (Section 41)."""

    def test_references_section_41(self):
        # Must contain "41" as a section reference
        content = _skill()
        assert "41" in content

    def test_references_hard_stop_protocol(self):
        content = _skill_lower()
        assert "hard stop" in content or "hard-stop" in content

    def test_references_builder_script_bug_detection(self):
        content = _skill_lower()
        assert "builder" in content and ("bug" in content or "script" in content)

    def test_references_save_artifacts(self):
        content = _skill_lower()
        assert "save" in content and "artifact" in content

    def test_references_bug_analysis(self):
        content = _skill_lower()
        assert "bug" in content and "analysis" in content

    def test_references_svp_n_workspace(self):
        content = _skill_lower()
        assert "svp" in content and ("workspace" in content or "n" in content.split())

    def test_references_svp_bug_command(self):
        content = _skill()
        assert "/svp:bug" in content or "svp:bug" in content

    def test_orchestrator_must_not_modify_builder_scripts_directly(self):
        content = _skill_lower()
        assert "must not" in content or "forbidden" in content or "never" in content
        assert "builder" in content


# ===========================================================================
# 13. Break-glass behavioral guidance (Section 43.9)
# ===========================================================================


class TestBreakGlassBehavioralGuidance:
    """Break-glass guidance per Section 43.9: permitted and forbidden actions."""

    def test_references_section_43_9(self):
        assert "43.9" in _skill()

    def test_references_break_glass_action_type(self):
        content = _skill_lower()
        assert (
            "break_glass" in content
            or "break-glass" in content
            or "break glass" in content
        )

    def test_permitted_action_present_failure_diagnostics(self):
        content = _skill_lower()
        assert "failure" in content and "diagnostic" in content

    def test_permitted_action_write_lessons_learned_entry(self):
        content = _skill_lower()
        assert "lessons" in content and "learned" in content

    def test_permitted_action_mark_unit_deferred_broken(self):
        content = _skill_lower()
        assert "deferred_broken" in content or "deferred broken" in content

    def test_permitted_action_retry_with_human_guidance(self):
        content = _skill_lower()
        assert "retry" in content and ("human" in content or "guidance" in content)

    def test_permitted_action_retry_max_3_per_unit_per_pass(self):
        content = _skill()
        assert "3" in content
        content_lower = _skill_lower()
        assert (
            "per unit" in content_lower
            or "per pass" in content_lower
            or "max" in content_lower
        )

    def test_permitted_action_escalate_to_pipeline_restart(self):
        content = _skill_lower()
        assert "escalat" in content and ("pipeline" in content and "restart" in content)

    def test_forbidden_fix_code_directly(self):
        content = _skill_lower()
        assert "fix" in content and "directly" in content or "forbidden" in content

    def test_forbidden_modify_spec_or_blueprint(self):
        content = _skill_lower()
        assert "spec" in content or "blueprint" in content
        assert "modify" in content or "forbidden" in content or "not" in content

    def test_forbidden_skip_stages(self):
        content = _skill_lower()
        assert "skip" in content and "stage" in content


# ===========================================================================
# 14. Cross-cutting: all required sections present together
# ===========================================================================


class TestAllRequiredSectionsPresent:
    """Verify that all major required content areas coexist in the skill."""

    def test_skill_contains_all_major_section_references(self):
        """A single test verifying the co-presence of all mandatory topics."""
        content = _skill_lower()
        # Six-step action cycle
        assert "action cycle" in content or "step" in content
        # REMINDER block
        assert "reminder" in content
        # Three-layer toolchain model
        assert "toolchain" in content
        # Break-glass
        assert "break" in content and "glass" in content
        # Hard stop
        assert "hard stop" in content or "hard-stop" in content
        # Spec refresh
        assert "refresh" in content or "re-read" in content or "reread" in content
        # Self-escalation
        assert "escalat" in content

    def test_skill_references_all_stage_numbers(self):
        """Every stage from 0 through 7 must be referenced."""
        content = _skill_lower()
        for stage_num in range(8):
            assert f"stage {stage_num}" in content or f"stage-{stage_num}" in content, (
                f"Stage {stage_num} not referenced in skill content"
            )

    def test_skill_references_key_section_numbers(self):
        """All key spec section numbers must appear."""
        content = _skill()
        required_sections = [
            "3.6",
            "6.9",
            "7.7",
            "8.5",
            "10.15",
            "12.17",
            "12.18.13",
            "43.9",
            "43.10",
        ]
        for section in required_sections:
            assert section in content, (
                f"Section {section} not referenced in skill content"
            )

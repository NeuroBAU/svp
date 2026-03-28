"""
Tests for Unit 25: Slash Command Files.

Synthetic Data Assumptions:
- COMMAND_NAMES is expected to be exactly the 11-element list specified in the
  blueprint: svp_help, svp_hint, svp_ref, svp_redo, svp_bug, svp_oracle,
  svp_save, svp_quit, svp_status, svp_clean, svp_visual_verify.
- COMMAND_DEFINITIONS is expected to be a dict mapping each of the 11 command
  names to a non-empty markdown string.
- Group A commands (save, quit, status, clean) are direct-action commands that
  do NOT invoke an agent and do NOT participate in the routing cycle.
- Group B commands (help, hint, ref, redo, bug, oracle) invoke an agent via
  a --phase flag with specific phase values per the blueprint.
- /svp:visual-verify is a standalone utility with no --phase value.
- /svp:oracle includes test project selection UX.
- Phase values: help->help, hint->hint, ref->reference_indexing, redo->redo,
  bug->bug_triage, oracle->oracle.
- Markdown content is tested for structural patterns (e.g., containing
  phase-related keywords, script references) rather than exact text.
"""

import pytest

from unit_25 import COMMAND_DEFINITIONS, COMMAND_NAMES

# ---------------------------------------------------------------------------
# Canonical reference data
# ---------------------------------------------------------------------------

EXPECTED_COMMAND_NAMES = [
    "svp_help",
    "svp_hint",
    "svp_ref",
    "svp_redo",
    "svp_bug",
    "svp_oracle",
    "svp_save",
    "svp_quit",
    "svp_status",
    "svp_clean",
    "svp_visual_verify",
]

GROUP_A_COMMANDS = ["svp_save", "svp_quit", "svp_status", "svp_clean"]

GROUP_B_COMMANDS = [
    "svp_help",
    "svp_hint",
    "svp_ref",
    "svp_redo",
    "svp_bug",
    "svp_oracle",
]

PHASE_MAP = {
    "svp_help": "help",
    "svp_hint": "hint",
    "svp_ref": "reference_indexing",
    "svp_redo": "redo",
    "svp_bug": "bug_triage",
    "svp_oracle": "oracle",
}


# ===========================================================================
# COMMAND_NAMES tests
# ===========================================================================


class TestCommandNames:
    """Tests for the COMMAND_NAMES constant."""

    def test_command_names_is_a_list(self):
        assert isinstance(COMMAND_NAMES, list)

    def test_command_names_has_exactly_11_entries(self):
        assert len(COMMAND_NAMES) == 11

    def test_command_names_exact_contents(self):
        """Every expected name is present and no extras exist."""
        assert set(COMMAND_NAMES) == set(EXPECTED_COMMAND_NAMES)

    def test_command_names_contains_svp_help(self):
        assert "svp_help" in COMMAND_NAMES

    def test_command_names_contains_svp_hint(self):
        assert "svp_hint" in COMMAND_NAMES

    def test_command_names_contains_svp_ref(self):
        assert "svp_ref" in COMMAND_NAMES

    def test_command_names_contains_svp_redo(self):
        assert "svp_redo" in COMMAND_NAMES

    def test_command_names_contains_svp_bug(self):
        assert "svp_bug" in COMMAND_NAMES

    def test_command_names_contains_svp_oracle(self):
        assert "svp_oracle" in COMMAND_NAMES

    def test_command_names_contains_svp_save(self):
        assert "svp_save" in COMMAND_NAMES

    def test_command_names_contains_svp_quit(self):
        assert "svp_quit" in COMMAND_NAMES

    def test_command_names_contains_svp_status(self):
        assert "svp_status" in COMMAND_NAMES

    def test_command_names_contains_svp_clean(self):
        assert "svp_clean" in COMMAND_NAMES

    def test_command_names_contains_svp_visual_verify(self):
        assert "svp_visual_verify" in COMMAND_NAMES

    def test_command_names_has_no_duplicates(self):
        assert len(COMMAND_NAMES) == len(set(COMMAND_NAMES))

    def test_all_command_names_are_strings(self):
        for name in COMMAND_NAMES:
            assert isinstance(name, str), f"Expected str, got {type(name)} for {name!r}"

    def test_all_command_names_start_with_svp_prefix(self):
        for name in COMMAND_NAMES:
            assert name.startswith("svp_"), f"{name!r} does not start with 'svp_'"


# ===========================================================================
# COMMAND_DEFINITIONS tests
# ===========================================================================


class TestCommandDefinitions:
    """Tests for the COMMAND_DEFINITIONS constant."""

    def test_command_definitions_is_a_dict(self):
        assert isinstance(COMMAND_DEFINITIONS, dict)

    def test_command_definitions_has_exactly_11_entries(self):
        assert len(COMMAND_DEFINITIONS) == 11

    def test_command_definitions_keys_match_command_names(self):
        """Every key in COMMAND_DEFINITIONS matches an entry in COMMAND_NAMES."""
        assert set(COMMAND_DEFINITIONS.keys()) == set(COMMAND_NAMES)

    def test_every_command_name_has_a_definition(self):
        """Every entry in COMMAND_NAMES appears as a key in COMMAND_DEFINITIONS."""
        for name in EXPECTED_COMMAND_NAMES:
            assert name in COMMAND_DEFINITIONS, f"Missing definition for {name!r}"

    def test_all_definitions_are_strings(self):
        for name, content in COMMAND_DEFINITIONS.items():
            assert isinstance(content, str), (
                f"Definition for {name!r} should be str, got {type(content)}"
            )

    def test_all_definitions_are_non_empty(self):
        for name, content in COMMAND_DEFINITIONS.items():
            assert len(content.strip()) > 0, (
                f"Definition for {name!r} is empty or whitespace-only"
            )

    def test_no_extra_keys_beyond_command_names(self):
        extra = set(COMMAND_DEFINITIONS.keys()) - set(EXPECTED_COMMAND_NAMES)
        assert extra == set(), f"Unexpected keys in COMMAND_DEFINITIONS: {extra}"


# ===========================================================================
# Group A commands -- direct action, no agent
# ===========================================================================


class TestGroupACommands:
    """Group A commands (save, quit, status, clean) invoke dedicated cmd_*.py
    scripts directly with no agent invocation and no routing cycle."""

    @pytest.mark.parametrize("cmd", GROUP_A_COMMANDS)
    def test_group_a_command_present_in_definitions(self, cmd):
        assert cmd in COMMAND_DEFINITIONS

    @pytest.mark.parametrize("cmd", GROUP_A_COMMANDS)
    def test_group_a_definition_is_non_empty_markdown(self, cmd):
        content = COMMAND_DEFINITIONS[cmd]
        assert isinstance(content, str)
        assert len(content.strip()) > 0

    @pytest.mark.parametrize("cmd", GROUP_A_COMMANDS)
    def test_group_a_commands_do_not_reference_phase_flag(self, cmd):
        """Group A commands should not contain --phase since they do not
        invoke agents via the routing cycle."""
        content = COMMAND_DEFINITIONS[cmd]
        assert "--phase" not in content, (
            f"Group A command {cmd!r} should not reference --phase"
        )

    @pytest.mark.parametrize("cmd", GROUP_A_COMMANDS)
    def test_group_a_commands_do_not_reference_prepare_task(self, cmd):
        """Group A commands do not use prepare_task.py since they skip the
        agent invocation cycle."""
        content = COMMAND_DEFINITIONS[cmd]
        assert "prepare_task" not in content, (
            f"Group A command {cmd!r} should not reference prepare_task"
        )

    @pytest.mark.parametrize("cmd", GROUP_A_COMMANDS)
    def test_group_a_commands_do_not_reference_spawn_agent(self, cmd):
        """Group A commands should not mention spawning an agent."""
        content = COMMAND_DEFINITIONS[cmd]
        assert (
            "spawn agent" not in content.lower()
            and "spawn_agent" not in content.lower()
        ), f"Group A command {cmd!r} should not reference agent spawning"


# ===========================================================================
# Group B commands -- invoke agent via --phase
# ===========================================================================


class TestGroupBCommands:
    """Group B commands (help, hint, ref, redo, bug, oracle) include the
    complete action cycle: prepare_task, spawn agent, write status, update_state,
    re-run routing."""

    @pytest.mark.parametrize("cmd", GROUP_B_COMMANDS)
    def test_group_b_command_present_in_definitions(self, cmd):
        assert cmd in COMMAND_DEFINITIONS

    @pytest.mark.parametrize("cmd", GROUP_B_COMMANDS)
    def test_group_b_definition_is_non_empty_markdown(self, cmd):
        content = COMMAND_DEFINITIONS[cmd]
        assert isinstance(content, str)
        assert len(content.strip()) > 0

    @pytest.mark.parametrize("cmd", GROUP_B_COMMANDS)
    def test_group_b_commands_reference_prepare_task(self, cmd):
        """Group B commands include step 1 of the action cycle: run
        prepare_task.py."""
        content = COMMAND_DEFINITIONS[cmd]
        assert "prepare_task" in content, (
            f"Group B command {cmd!r} should reference prepare_task"
        )

    @pytest.mark.parametrize("cmd", GROUP_B_COMMANDS)
    def test_group_b_commands_reference_update_state(self, cmd):
        """Group B commands include step 4 of the action cycle: run
        update_state.py."""
        content = COMMAND_DEFINITIONS[cmd]
        assert "update_state" in content, (
            f"Group B command {cmd!r} should reference update_state"
        )

    @pytest.mark.parametrize("cmd", GROUP_B_COMMANDS)
    def test_group_b_commands_reference_last_status(self, cmd):
        """Group B commands include step 3: write terminal status to
        last_status.txt."""
        content = COMMAND_DEFINITIONS[cmd]
        assert "last_status" in content, (
            f"Group B command {cmd!r} should reference last_status"
        )

    @pytest.mark.parametrize("cmd", GROUP_B_COMMANDS)
    def test_group_b_commands_reference_routing(self, cmd):
        """Group B commands include step 5: re-run the routing script."""
        content = COMMAND_DEFINITIONS[cmd]
        assert "routing" in content.lower(), (
            f"Group B command {cmd!r} should reference routing"
        )


# ===========================================================================
# Per-command --phase values
# ===========================================================================


class TestPhaseValues:
    """Each Group B command must reference its specific --phase value."""

    def test_svp_help_has_phase_help(self):
        content = COMMAND_DEFINITIONS["svp_help"]
        assert "--phase help" in content or "--phase=help" in content, (
            "svp_help definition must contain --phase help"
        )

    def test_svp_hint_has_phase_hint(self):
        content = COMMAND_DEFINITIONS["svp_hint"]
        assert "--phase hint" in content or "--phase=hint" in content, (
            "svp_hint definition must contain --phase hint"
        )

    def test_svp_ref_has_phase_reference_indexing(self):
        content = COMMAND_DEFINITIONS["svp_ref"]
        assert (
            "--phase reference_indexing" in content
            or "--phase=reference_indexing" in content
        ), "svp_ref definition must contain --phase reference_indexing"

    def test_svp_redo_has_phase_redo(self):
        content = COMMAND_DEFINITIONS["svp_redo"]
        assert "--phase redo" in content or "--phase=redo" in content, (
            "svp_redo definition must contain --phase redo"
        )

    def test_svp_bug_has_phase_bug_triage(self):
        content = COMMAND_DEFINITIONS["svp_bug"]
        assert "--phase bug_triage" in content or "--phase=bug_triage" in content, (
            "svp_bug definition must contain --phase bug_triage"
        )

    def test_svp_oracle_has_phase_oracle(self):
        content = COMMAND_DEFINITIONS["svp_oracle"]
        assert "--phase oracle" in content or "--phase=oracle" in content, (
            "svp_oracle definition must contain --phase oracle"
        )

    @pytest.mark.parametrize(
        "cmd,phase",
        list(PHASE_MAP.items()),
        ids=list(PHASE_MAP.keys()),
    )
    def test_parametrized_phase_value_present(self, cmd, phase):
        """Parametrized check: each Group B command's definition contains its
        expected --phase value."""
        content = COMMAND_DEFINITIONS[cmd]
        assert f"--phase {phase}" in content or f"--phase={phase}" in content, (
            f"{cmd!r} definition must contain --phase {phase}"
        )


# ===========================================================================
# /svp:oracle -- test project selection UX
# ===========================================================================


class TestOracleCommand:
    """The /svp:oracle command includes test project selection UX with numbered
    list from docs/ and examples/."""

    def test_oracle_definition_mentions_test_project_selection(self):
        content = COMMAND_DEFINITIONS["svp_oracle"]
        # The definition should reference test project selection in some form
        content_lower = content.lower()
        assert (
            "test project" in content_lower
            or "project selection" in content_lower
            or "numbered list" in content_lower
        ), "svp_oracle should describe test project selection UX"

    def test_oracle_definition_mentions_docs_or_examples_directories(self):
        content = COMMAND_DEFINITIONS["svp_oracle"]
        content_lower = content.lower()
        has_docs = "docs/" in content_lower or "docs" in content_lower
        has_examples = "examples/" in content_lower or "examples" in content_lower
        assert has_docs or has_examples, (
            "svp_oracle definition should mention docs/ or examples/ directories"
        )


# ===========================================================================
# /svp:visual-verify -- standalone utility, no --phase
# ===========================================================================


class TestVisualVerifyCommand:
    """The /svp:visual-verify command is a standalone utility with no --phase
    value. It accepts --target, --interval, and --interactions flags."""

    def test_visual_verify_present_in_definitions(self):
        assert "svp_visual_verify" in COMMAND_DEFINITIONS

    def test_visual_verify_definition_is_non_empty(self):
        content = COMMAND_DEFINITIONS["svp_visual_verify"]
        assert len(content.strip()) > 0

    def test_visual_verify_does_not_have_phase_value(self):
        """visual-verify is not a routed command; it must not contain --phase."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"]
        assert "--phase" not in content, (
            "svp_visual_verify should not have a --phase value"
        )

    def test_visual_verify_references_target_flag(self):
        content = COMMAND_DEFINITIONS["svp_visual_verify"]
        assert "--target" in content, "svp_visual_verify should accept --target flag"

    def test_visual_verify_references_interval_flag(self):
        content = COMMAND_DEFINITIONS["svp_visual_verify"]
        assert "--interval" in content, (
            "svp_visual_verify should accept --interval flag"
        )

    def test_visual_verify_references_interactions_flag(self):
        content = COMMAND_DEFINITIONS["svp_visual_verify"]
        assert "--interactions" in content, (
            "svp_visual_verify should accept --interactions flag"
        )

    def test_visual_verify_mentions_visual_verification(self):
        content = COMMAND_DEFINITIONS["svp_visual_verify"]
        content_lower = content.lower()
        assert "visual" in content_lower, (
            "svp_visual_verify definition should mention visual verification"
        )

    def test_visual_verify_mentions_screenshot_capture(self):
        """The command captures visual output (screenshots)."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"]
        content_lower = content.lower()
        assert "screenshot" in content_lower or "capture" in content_lower, (
            "svp_visual_verify should mention screenshot capture"
        )

    def test_visual_verify_is_supplementary_not_authoritative(self):
        """The command is supplementary -- the test suite is authoritative."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"]
        content_lower = content.lower()
        assert (
            "supplementary" in content_lower or "not authoritative" in content_lower
        ), "svp_visual_verify should note it is supplementary, not authoritative"


# ===========================================================================
# Structural invariants
# ===========================================================================


class TestStructuralInvariants:
    """Cross-cutting structural invariants across all commands."""

    def test_group_a_and_group_b_are_disjoint(self):
        """Group A and Group B should have no overlap."""
        overlap = set(GROUP_A_COMMANDS) & set(GROUP_B_COMMANDS)
        assert overlap == set(), f"Overlap between groups: {overlap}"

    def test_group_a_plus_group_b_plus_visual_verify_covers_all(self):
        """Group A + Group B + visual_verify should cover all 11 commands."""
        covered = set(GROUP_A_COMMANDS) | set(GROUP_B_COMMANDS) | {"svp_visual_verify"}
        assert covered == set(EXPECTED_COMMAND_NAMES)

    def test_definitions_keys_are_identical_to_names(self):
        """COMMAND_DEFINITIONS keys must be exactly COMMAND_NAMES."""
        assert set(COMMAND_DEFINITIONS.keys()) == set(COMMAND_NAMES)

    def test_every_definition_is_markdown_content(self):
        """Each definition should look like markdown (contain at least one
        typical markdown indicator: heading, list item, backtick, link, etc.)."""
        markdown_indicators = ("#", "-", "*", "`", "[", ">")
        for name, content in COMMAND_DEFINITIONS.items():
            has_indicator = any(ind in content for ind in markdown_indicators)
            assert has_indicator, (
                f"Definition for {name!r} does not appear to be markdown"
            )

    def test_no_command_name_contains_whitespace(self):
        for name in COMMAND_NAMES:
            assert " " not in name and "\t" not in name, (
                f"Command name {name!r} contains whitespace"
            )

    def test_no_command_name_is_empty(self):
        for name in COMMAND_NAMES:
            assert len(name) > 0

    def test_phase_map_covers_all_group_b_commands(self):
        """Every Group B command has a corresponding phase value in PHASE_MAP."""
        for cmd in GROUP_B_COMMANDS:
            assert cmd in PHASE_MAP, f"Missing phase mapping for {cmd!r}"

    def test_group_a_commands_not_in_phase_map(self):
        """No Group A command should have a phase mapping."""
        for cmd in GROUP_A_COMMANDS:
            assert cmd not in PHASE_MAP, (
                f"Group A command {cmd!r} should not have a phase mapping"
            )

    def test_visual_verify_not_in_phase_map(self):
        """visual_verify is not a routed command."""
        assert "svp_visual_verify" not in PHASE_MAP

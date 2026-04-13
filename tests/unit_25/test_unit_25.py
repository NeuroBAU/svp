"""Unit 25: Slash Command Files -- complete test suite.

Synthetic data assumptions:
- COMMAND_DEFINITIONS is a dict mapping command name strings to markdown content
  strings. Each value is the complete markdown content for that slash command
  definition file.
- COMMAND_NAMES is a List[str] containing exactly these 11 entries:
  ["svp_help", "svp_hint", "svp_ref", "svp_redo", "svp_bug", "svp_oracle",
   "svp_save", "svp_quit", "svp_status", "svp_clean", "svp_visual_verify"].
- Group A commands (svp_save, svp_quit, svp_status, svp_clean) invoke
  dedicated cmd_*.py scripts directly with no agent invocation and no
  routing cycle. Their markdown content describes direct script invocation.
- Group B commands (svp_help, svp_hint, svp_ref, svp_redo, svp_bug,
  svp_oracle) include a complete action cycle: (1) run prepare_task.py,
  (2) spawn agent, (3) write terminal status to last_status.txt,
  (4) run update_state.py, (5) re-run routing script.
  Exception: svp_oracle is a thin redirect (Bug S3-79) — it enters the
  oracle session state and defers to the routing script for all content
  construction, including test project selection. It does NOT follow the
  standard 5-step cycle.
  Exception: svp_bug is a thin redirect (Bug S3-119, extending S3-79) —
  it enters the debug session state via the svp_bug_entry command and
  defers to the routing script. Like svp_oracle, it does NOT follow the
  standard 5-step cycle.
- Per-command --phase values for standard Group B: help -> "help",
  hint -> "hint", ref -> "reference_indexing", redo -> "redo". Bug and
  oracle are thin redirects and use --command entries instead of --phase:
  bug uses --command svp_bug_entry, oracle uses --command oracle_start.
- /svp:oracle command is a thin redirect that enters oracle session state
  and defers to the routing script. It must NOT contain directory-scanning
  instructions (Bug S3-79 / P21 / P23).
- /svp:visual-verify command provides visual verification for GUI-based
  test projects. It is a standalone utility with no --phase value. It
  accepts --target, --interval, and --interactions parameters.
- Keyword matching is case-insensitive where noted; exact tokens and command
  names are matched case-sensitively unless otherwise specified.
- All markdown content strings are expected to be non-empty and contain
  meaningful content describing the command's behavior.
"""

import re

import pytest

from slash_commands import (
    COMMAND_DEFINITIONS,
    COMMAND_NAMES,
)

# ---------------------------------------------------------------------------
# Expected constants
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

# Bug S3-79: svp_oracle is a thin redirect, not a standard 5-step Group B command.
# Bug S3-119: svp_bug is also a thin redirect (extends S3-79 to cover bug entry).
GROUP_B_THIN_REDIRECTS = ["svp_bug", "svp_oracle"]
GROUP_B_STANDARD = [cmd for cmd in GROUP_B_COMMANDS if cmd not in GROUP_B_THIN_REDIRECTS]

PHASE_VALUES = {
    "svp_help": "help",
    "svp_hint": "hint",
    "svp_ref": "reference_indexing",
    "svp_redo": "redo",
}


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def cmd_contains(cmd_name: str, phrase: str, case_sensitive: bool = True) -> bool:
    """Check whether COMMAND_DEFINITIONS[cmd_name] contains the given phrase."""
    content = COMMAND_DEFINITIONS[cmd_name]
    if case_sensitive:
        return phrase in content
    return phrase.lower() in content.lower()


def cmd_matches(cmd_name: str, pattern: str, flags: int = 0) -> list:
    """Return all regex matches of pattern in COMMAND_DEFINITIONS[cmd_name]."""
    return re.findall(pattern, COMMAND_DEFINITIONS[cmd_name], flags)


# ===========================================================================
# COMMAND_NAMES: type and content
# ===========================================================================


class TestCommandNamesType:
    """Verify COMMAND_NAMES is a list of strings."""

    def test_command_names_is_list(self):
        assert isinstance(COMMAND_NAMES, list)

    def test_command_names_elements_are_strings(self):
        for name in COMMAND_NAMES:
            assert isinstance(name, str), f"Expected str, got {type(name)} for {name!r}"

    def test_command_names_is_not_empty(self):
        assert len(COMMAND_NAMES) > 0


class TestCommandNamesContent:
    """Verify COMMAND_NAMES contains exactly the 11 expected command names."""

    def test_command_names_has_correct_count(self):
        assert len(COMMAND_NAMES) == 11

    def test_svp_help_in_command_names(self):
        assert "svp_help" in COMMAND_NAMES

    def test_svp_hint_in_command_names(self):
        assert "svp_hint" in COMMAND_NAMES

    def test_svp_ref_in_command_names(self):
        assert "svp_ref" in COMMAND_NAMES

    def test_svp_redo_in_command_names(self):
        assert "svp_redo" in COMMAND_NAMES

    def test_svp_bug_in_command_names(self):
        assert "svp_bug" in COMMAND_NAMES

    def test_svp_oracle_in_command_names(self):
        assert "svp_oracle" in COMMAND_NAMES

    def test_svp_save_in_command_names(self):
        assert "svp_save" in COMMAND_NAMES

    def test_svp_quit_in_command_names(self):
        assert "svp_quit" in COMMAND_NAMES

    def test_svp_status_in_command_names(self):
        assert "svp_status" in COMMAND_NAMES

    def test_svp_clean_in_command_names(self):
        assert "svp_clean" in COMMAND_NAMES

    def test_svp_visual_verify_in_command_names(self):
        assert "svp_visual_verify" in COMMAND_NAMES

    def test_command_names_exact_set(self):
        """COMMAND_NAMES must contain exactly the 11 expected names (as a set)."""
        assert set(COMMAND_NAMES) == set(EXPECTED_COMMAND_NAMES)

    def test_no_duplicate_command_names(self):
        """COMMAND_NAMES must not contain duplicates."""
        assert len(COMMAND_NAMES) == len(set(COMMAND_NAMES))


# ===========================================================================
# COMMAND_DEFINITIONS: type and structure
# ===========================================================================


class TestCommandDefinitionsType:
    """Verify COMMAND_DEFINITIONS is a dict mapping str to str."""

    def test_command_definitions_is_dict(self):
        assert isinstance(COMMAND_DEFINITIONS, dict)

    def test_command_definitions_is_not_empty(self):
        assert len(COMMAND_DEFINITIONS) > 0

    def test_command_definitions_keys_are_strings(self):
        for key in COMMAND_DEFINITIONS:
            assert isinstance(key, str), (
                f"Expected str key, got {type(key)} for {key!r}"
            )

    def test_command_definitions_values_are_strings(self):
        for key, val in COMMAND_DEFINITIONS.items():
            assert isinstance(val, str), (
                f"Expected str value for {key!r}, got {type(val)}"
            )

    def test_command_definitions_values_are_nonempty(self):
        for key, val in COMMAND_DEFINITIONS.items():
            assert len(val.strip()) > 0, f"Command definition for {key!r} is empty"


class TestCommandDefinitionsKeys:
    """Verify COMMAND_DEFINITIONS keys match COMMAND_NAMES."""

    def test_all_command_names_have_definitions(self):
        """Every entry in COMMAND_NAMES must have a corresponding definition."""
        for name in EXPECTED_COMMAND_NAMES:
            assert name in COMMAND_DEFINITIONS, (
                f"Missing definition for command {name!r}"
            )

    def test_definitions_keys_match_command_names(self):
        """COMMAND_DEFINITIONS keys should match COMMAND_NAMES (as sets)."""
        assert set(COMMAND_DEFINITIONS.keys()) == set(EXPECTED_COMMAND_NAMES)

    def test_definitions_count_matches_command_names_count(self):
        """Number of definitions must equal number of command names."""
        assert len(COMMAND_DEFINITIONS) == len(EXPECTED_COMMAND_NAMES)


class TestCommandDefinitionsAreMarkdown:
    """Verify all command definitions contain markdown content."""

    def test_all_definitions_have_substantial_content(self):
        """Each definition should have meaningful length for a command file."""
        for name in EXPECTED_COMMAND_NAMES:
            content = COMMAND_DEFINITIONS[name]
            assert len(content.strip()) > 20, (
                f"Definition for {name!r} is too short ({len(content.strip())} chars)"
            )


# ===========================================================================
# Group A commands: direct script invocation, no agent, no routing cycle
# ===========================================================================


class TestGroupACommandsSaveDirectInvocation:
    """svp_save invokes a dedicated cmd_*.py script directly."""

    def test_save_references_cmd_script(self):
        """svp_save must reference a cmd_ script."""
        assert cmd_contains("svp_save", "cmd_", case_sensitive=False)

    def test_save_references_save_concept(self):
        """svp_save must describe saving."""
        assert cmd_contains("svp_save", "save", case_sensitive=False)


class TestGroupACommandsQuitDirectInvocation:
    """svp_quit invokes a dedicated cmd_*.py script directly."""

    def test_quit_references_cmd_script(self):
        """svp_quit must reference a cmd_ script."""
        assert cmd_contains("svp_quit", "cmd_", case_sensitive=False)

    def test_quit_references_quit_concept(self):
        """svp_quit must describe quitting."""
        assert cmd_contains("svp_quit", "quit", case_sensitive=False)


class TestGroupACommandsStatusDirectInvocation:
    """svp_status invokes a dedicated cmd_*.py script directly."""

    def test_status_references_cmd_script(self):
        """svp_status must reference a cmd_ script."""
        assert cmd_contains("svp_status", "cmd_", case_sensitive=False)

    def test_status_references_status_concept(self):
        """svp_status must describe status."""
        assert cmd_contains("svp_status", "status", case_sensitive=False)


class TestGroupACommandsCleanDirectInvocation:
    """svp_clean invokes a dedicated cmd_*.py script directly."""

    def test_clean_references_cmd_script(self):
        """svp_clean must reference a cmd_ script."""
        assert cmd_contains("svp_clean", "cmd_", case_sensitive=False)

    def test_clean_references_clean_concept(self):
        """svp_clean must describe cleaning."""
        assert cmd_contains("svp_clean", "clean", case_sensitive=False)


class TestGroupANoAgentInvocation:
    """Group A commands must not invoke agents."""

    def test_save_no_agent_invocation(self):
        """svp_save must not reference agent spawning."""
        content = COMMAND_DEFINITIONS["svp_save"].lower()
        assert (
            "spawn agent" not in content
            or "no agent" in content
            or "without agent" in content
        )

    def test_quit_no_agent_invocation(self):
        """svp_quit must not reference agent spawning."""
        content = COMMAND_DEFINITIONS["svp_quit"].lower()
        assert (
            "spawn agent" not in content
            or "no agent" in content
            or "without agent" in content
        )

    def test_status_no_agent_invocation(self):
        """svp_status must not reference agent spawning."""
        content = COMMAND_DEFINITIONS["svp_status"].lower()
        assert (
            "spawn agent" not in content
            or "no agent" in content
            or "without agent" in content
        )

    def test_clean_no_agent_invocation(self):
        """svp_clean must not reference agent spawning."""
        content = COMMAND_DEFINITIONS["svp_clean"].lower()
        assert (
            "spawn agent" not in content
            or "no agent" in content
            or "without agent" in content
        )


class TestGroupANoRoutingCycle:
    """Group A commands must not involve a routing cycle."""

    def test_save_no_routing_cycle(self):
        """svp_save should not reference the full routing cycle."""
        content = COMMAND_DEFINITIONS["svp_save"].lower()
        # Group A commands should not reference prepare_task.py or update_state.py
        has_no_prepare = "prepare_task" not in content
        has_no_update_state = "update_state" not in content
        assert has_no_prepare or has_no_update_state, (
            "svp_save should not reference both prepare_task.py and update_state.py"
        )

    def test_quit_no_routing_cycle(self):
        """svp_quit should not reference the full routing cycle."""
        content = COMMAND_DEFINITIONS["svp_quit"].lower()
        has_no_prepare = "prepare_task" not in content
        has_no_update_state = "update_state" not in content
        assert has_no_prepare or has_no_update_state

    def test_status_no_routing_cycle(self):
        """svp_status should not reference the full routing cycle."""
        content = COMMAND_DEFINITIONS["svp_status"].lower()
        has_no_prepare = "prepare_task" not in content
        has_no_update_state = "update_state" not in content
        assert has_no_prepare or has_no_update_state

    def test_clean_no_routing_cycle(self):
        """svp_clean should not reference the full routing cycle."""
        content = COMMAND_DEFINITIONS["svp_clean"].lower()
        has_no_prepare = "prepare_task" not in content
        has_no_update_state = "update_state" not in content
        assert has_no_prepare or has_no_update_state


# ===========================================================================
# Group B commands: complete action cycle
# ===========================================================================


class TestGroupBActionCyclePrepareTask:
    """Group B commands must reference prepare_task.py as step 1."""

    def test_help_references_prepare_task(self):
        assert cmd_contains("svp_help", "prepare_task", case_sensitive=False)

    def test_hint_references_prepare_task(self):
        assert cmd_contains("svp_hint", "prepare_task", case_sensitive=False)

    def test_ref_references_prepare_task(self):
        assert cmd_contains("svp_ref", "prepare_task", case_sensitive=False)

    def test_redo_references_prepare_task(self):
        assert cmd_contains("svp_redo", "prepare_task", case_sensitive=False)

    def test_bug_does_not_reference_prepare_task(self):
        """Bug S3-119: svp_bug is a thin redirect like svp_oracle. The thin
        trigger must not invoke prepare_task.py — that machinery lives in
        _route_debug after Gate 6.0 authorization."""
        assert not cmd_contains("svp_bug", "prepare_task", case_sensitive=False)

    def test_oracle_references_routing_script(self):
        """Bug S3-79: oracle is a thin redirect to the routing script."""
        assert cmd_contains("svp_oracle", "routing.py", case_sensitive=False)

    def test_bug_references_routing_script(self):
        """Bug S3-119: svp_bug is also a thin redirect to the routing script."""
        assert cmd_contains("svp_bug", "routing.py", case_sensitive=False)


class TestGroupBActionCycleSpawnAgent:
    """Group B commands must reference spawning an agent as step 2."""

    def test_help_references_agent(self):
        assert cmd_contains("svp_help", "agent", case_sensitive=False)

    def test_hint_references_agent(self):
        assert cmd_contains("svp_hint", "agent", case_sensitive=False)

    def test_ref_references_agent(self):
        assert cmd_contains("svp_ref", "agent", case_sensitive=False)

    def test_redo_references_agent(self):
        assert cmd_contains("svp_redo", "agent", case_sensitive=False)

    def test_bug_references_agent(self):
        assert cmd_contains("svp_bug", "agent", case_sensitive=False)

    def test_oracle_references_agent(self):
        assert cmd_contains("svp_oracle", "agent", case_sensitive=False)


class TestGroupBActionCycleLastStatus:
    """Group B commands must reference writing terminal status to last_status.txt."""

    def test_help_references_last_status(self):
        assert cmd_contains("svp_help", "last_status", case_sensitive=False)

    def test_hint_references_last_status(self):
        assert cmd_contains("svp_hint", "last_status", case_sensitive=False)

    def test_ref_references_last_status(self):
        assert cmd_contains("svp_ref", "last_status", case_sensitive=False)

    def test_redo_references_last_status(self):
        assert cmd_contains("svp_redo", "last_status", case_sensitive=False)

    def test_bug_does_not_reference_last_status(self):
        """Bug S3-119: svp_bug thin trigger does not write a sentinel to
        last_status.txt. The svp_bug_entry command dispatch is state-only."""
        assert not cmd_contains("svp_bug", "last_status", case_sensitive=False)

    def test_oracle_references_last_status(self):
        assert cmd_contains("svp_oracle", "last_status", case_sensitive=False)


class TestGroupBActionCycleUpdateState:
    """Group B commands must reference update_state.py as step 4."""

    def test_help_references_update_state(self):
        assert cmd_contains("svp_help", "update_state", case_sensitive=False)

    def test_hint_references_update_state(self):
        assert cmd_contains("svp_hint", "update_state", case_sensitive=False)

    def test_ref_references_update_state(self):
        assert cmd_contains("svp_ref", "update_state", case_sensitive=False)

    def test_redo_references_update_state(self):
        assert cmd_contains("svp_redo", "update_state", case_sensitive=False)

    def test_bug_references_update_state(self):
        assert cmd_contains("svp_bug", "update_state", case_sensitive=False)

    def test_oracle_references_update_state(self):
        assert cmd_contains("svp_oracle", "update_state", case_sensitive=False)


class TestGroupBActionCycleRoutingRerun:
    """Group B commands must reference re-running the routing script as step 5."""

    def test_help_references_routing(self):
        assert cmd_contains("svp_help", "routing", case_sensitive=False)

    def test_hint_references_routing(self):
        assert cmd_contains("svp_hint", "routing", case_sensitive=False)

    def test_ref_references_routing(self):
        assert cmd_contains("svp_ref", "routing", case_sensitive=False)

    def test_redo_references_routing(self):
        assert cmd_contains("svp_redo", "routing", case_sensitive=False)

    def test_bug_references_routing(self):
        assert cmd_contains("svp_bug", "routing", case_sensitive=False)

    def test_oracle_references_routing(self):
        assert cmd_contains("svp_oracle", "routing", case_sensitive=False)


# ===========================================================================
# Group B commands: per-command --phase values
# ===========================================================================


class TestGroupBPhaseValueHelp:
    """svp_help must use --phase help."""

    def test_help_phase_value_present(self):
        """The help command definition must contain the phase value 'help'."""
        content = COMMAND_DEFINITIONS["svp_help"]
        # Look for the phase value in the context of update_state or --phase
        assert "help" in content.lower()

    def test_help_phase_argument_in_update_state(self):
        """The help command must reference --phase help with update_state."""
        content = COMMAND_DEFINITIONS["svp_help"]
        has_phase_help = (
            "--phase help" in content
            or "--phase=help" in content
            or "phase help" in content.lower()
        )
        assert has_phase_help


class TestGroupBPhaseValueHint:
    """svp_hint must use --phase hint."""

    def test_hint_phase_value_present(self):
        content = COMMAND_DEFINITIONS["svp_hint"]
        assert "hint" in content.lower()

    def test_hint_phase_argument_in_update_state(self):
        content = COMMAND_DEFINITIONS["svp_hint"]
        has_phase_hint = (
            "--phase hint" in content
            or "--phase=hint" in content
            or "phase hint" in content.lower()
        )
        assert has_phase_hint


class TestGroupBPhaseValueRef:
    """svp_ref must use --phase reference_indexing."""

    def test_ref_phase_value_present(self):
        content = COMMAND_DEFINITIONS["svp_ref"]
        assert (
            "reference_indexing" in content or "reference indexing" in content.lower()
        )

    def test_ref_phase_argument_in_update_state(self):
        content = COMMAND_DEFINITIONS["svp_ref"]
        has_phase_ref = (
            "--phase reference_indexing" in content
            or "--phase=reference_indexing" in content
            or "phase reference_indexing" in content.lower()
        )
        assert has_phase_ref


class TestGroupBPhaseValueRedo:
    """svp_redo must use --phase redo."""

    def test_redo_phase_value_present(self):
        content = COMMAND_DEFINITIONS["svp_redo"]
        assert "redo" in content.lower()

    def test_redo_phase_argument_in_update_state(self):
        content = COMMAND_DEFINITIONS["svp_redo"]
        has_phase_redo = (
            "--phase redo" in content
            or "--phase=redo" in content
            or "phase redo" in content.lower()
        )
        assert has_phase_redo


class TestGroupBPhaseValueBug:
    """svp_bug uses --command svp_bug_entry (Bug S3-119 — thin redirect).

    Prior to S3-119, svp_bug was modeled as a standard Group B command
    using --phase bug_triage. That pattern did not create the debug_session
    object, so /svp:bug could not bootstrap from pipeline_complete. The
    fix replaces the 5-step cycle with a thin state-transition trigger
    using --command svp_bug_entry (mirroring /svp:oracle's Bug S3-79 fix)."""

    def test_bug_uses_command_svp_bug_entry(self):
        """Bug S3-119: bug uses --command svp_bug_entry instead of --phase bug_triage."""
        content = COMMAND_DEFINITIONS["svp_bug"]
        assert "--command svp_bug_entry" in content or "svp_bug_entry" in content

    def test_bug_does_not_use_phase_argument(self):
        """Bug S3-119: the thin trigger does not dispatch via --phase.
        --phase bug_triage would route to dispatch_agent_status, which is
        the post-agent dispatch path; the entry path is --command instead."""
        content = COMMAND_DEFINITIONS["svp_bug"]
        assert "--phase bug_triage" not in content
        assert "--phase=bug_triage" not in content


class TestGroupBPhaseValueOracle:
    """svp_oracle must use --phase oracle."""

    def test_oracle_phase_value_present(self):
        content = COMMAND_DEFINITIONS["svp_oracle"]
        assert "oracle" in content.lower()

    def test_oracle_uses_command_oracle_start(self):
        """Bug S3-79: oracle uses --command oracle_start instead of --phase oracle."""
        content = COMMAND_DEFINITIONS["svp_oracle"]
        assert "--command oracle_start" in content or "oracle_start" in content


# ===========================================================================
# Group B: prepare_task.py --agent <type> pattern
# ===========================================================================


class TestGroupBPrepareTaskAgentFlag:
    """Group B commands must reference prepare_task.py --agent <type>."""

    def test_help_prepare_task_agent_flag(self):
        content = COMMAND_DEFINITIONS["svp_help"]
        assert "--agent" in content or "agent" in content.lower()

    def test_hint_prepare_task_agent_flag(self):
        content = COMMAND_DEFINITIONS["svp_hint"]
        assert "--agent" in content or "agent" in content.lower()

    def test_ref_prepare_task_agent_flag(self):
        content = COMMAND_DEFINITIONS["svp_ref"]
        assert "--agent" in content or "agent" in content.lower()

    def test_redo_prepare_task_agent_flag(self):
        content = COMMAND_DEFINITIONS["svp_redo"]
        assert "--agent" in content or "agent" in content.lower()

    def test_bug_prepare_task_agent_flag(self):
        content = COMMAND_DEFINITIONS["svp_bug"]
        assert "--agent" in content or "agent" in content.lower()

    def test_oracle_prepare_task_agent_flag(self):
        content = COMMAND_DEFINITIONS["svp_oracle"]
        assert "--agent" in content or "agent" in content.lower()


class TestGroupBPrepareTaskProjectRoot:
    """Group B commands must reference --project-root . in prepare_task.py."""

    def test_help_project_root_flag(self):
        content = COMMAND_DEFINITIONS["svp_help"]
        assert (
            "--project-root" in content
            or "project-root" in content.lower()
            or "project_root" in content.lower()
        )

    def test_hint_project_root_flag(self):
        content = COMMAND_DEFINITIONS["svp_hint"]
        assert (
            "--project-root" in content
            or "project-root" in content.lower()
            or "project_root" in content.lower()
        )

    def test_ref_project_root_flag(self):
        content = COMMAND_DEFINITIONS["svp_ref"]
        assert (
            "--project-root" in content
            or "project-root" in content.lower()
            or "project_root" in content.lower()
        )

    def test_redo_project_root_flag(self):
        content = COMMAND_DEFINITIONS["svp_redo"]
        assert (
            "--project-root" in content
            or "project-root" in content.lower()
            or "project_root" in content.lower()
        )

    def test_bug_project_root_flag(self):
        content = COMMAND_DEFINITIONS["svp_bug"]
        assert (
            "--project-root" in content
            or "project-root" in content.lower()
            or "project_root" in content.lower()
        )

    def test_oracle_project_root_flag(self):
        content = COMMAND_DEFINITIONS["svp_oracle"]
        assert (
            "--project-root" in content
            or "project-root" in content.lower()
            or "project_root" in content.lower()
        )


# ===========================================================================
# /svp:oracle command: test project selection UX
# ===========================================================================


class TestOracleTestProjectSelectionUX:
    """/svp:oracle is a thin redirect (Bug S3-79). It must NOT build content."""

    def test_oracle_references_test_project_selection(self):
        """Oracle must mention test project selection is handled by routing."""
        content = COMMAND_DEFINITIONS["svp_oracle"].lower()
        has_test_project = "test project" in content
        has_routing = "routing" in content
        assert has_test_project and has_routing

    def test_oracle_does_not_scan_directories(self):
        """Bug S3-79: oracle must NOT instruct orchestrator to scan directories."""
        content = COMMAND_DEFINITIONS["svp_oracle"]
        assert "Do NOT scan directories" in content

    def test_oracle_no_docs_directory_reference(self):
        """Bug S3-79: oracle must NOT reference docs/ for scanning."""
        content = COMMAND_DEFINITIONS["svp_oracle"]
        assert "from the `docs/`" not in content

    def test_oracle_no_examples_directory_reference(self):
        """Bug S3-79: oracle must NOT reference examples/ for scanning."""
        content = COMMAND_DEFINITIONS["svp_oracle"]
        assert "from the `examples/`" not in content

    def test_oracle_no_numbered_list_instruction(self):
        """Bug S3-79: oracle must NOT instruct building a numbered list."""
        content = COMMAND_DEFINITIONS["svp_oracle"]
        assert "numbered list of available test projects" not in content


# ===========================================================================
# /svp:visual-verify command: standalone visual verification utility
# ===========================================================================


class TestVisualVerifyBasicStructure:
    """/svp:visual-verify is a standalone visual verification command."""

    def test_visual_verify_definition_exists(self):
        """svp_visual_verify must have a definition."""
        assert "svp_visual_verify" in COMMAND_DEFINITIONS

    def test_visual_verify_is_nonempty(self):
        """svp_visual_verify definition must be non-empty."""
        assert len(COMMAND_DEFINITIONS["svp_visual_verify"].strip()) > 0

    def test_visual_verify_references_visual(self):
        """svp_visual_verify must reference visual verification."""
        assert cmd_contains("svp_visual_verify", "visual", case_sensitive=False)

    def test_visual_verify_references_verification(self):
        """svp_visual_verify must reference verification."""
        assert cmd_contains("svp_visual_verify", "verif", case_sensitive=False)


class TestVisualVerifyGUITestProjects:
    """/svp:visual-verify provides visual verification for GUI-based test projects."""

    def test_visual_verify_references_gui(self):
        """Must reference GUI-based test projects."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"].lower()
        assert "gui" in content or "graphical" in content or "visual" in content

    def test_visual_verify_references_test_project(self):
        """Must reference test projects."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"].lower()
        assert "test project" in content or "test" in content

    def test_visual_verify_references_screenshots(self):
        """Must reference screenshots or visual capture."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"].lower()
        assert "screenshot" in content or "capture" in content or "image" in content


class TestVisualVerifyLaunchAndCapture:
    """/svp:visual-verify launches a target program and captures visual output."""

    def test_visual_verify_references_launch(self):
        """Must reference launching a target program."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"].lower()
        assert (
            "launch" in content
            or "run" in content
            or "start" in content
            or "execut" in content
        )

    def test_visual_verify_references_target(self):
        """Must reference a target program or executable."""
        assert cmd_contains("svp_visual_verify", "target", case_sensitive=False)

    def test_visual_verify_references_capture(self):
        """Must reference capturing visual output."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"].lower()
        assert "capture" in content or "screenshot" in content or "image" in content


class TestVisualVerifyParameters:
    """/svp:visual-verify accepts --target, --interval, and --interactions."""

    def test_visual_verify_target_parameter(self):
        """Must accept --target parameter."""
        assert cmd_contains(
            "svp_visual_verify", "--target", case_sensitive=False
        ) or cmd_contains("svp_visual_verify", "target", case_sensitive=False)

    def test_visual_verify_interval_parameter(self):
        """Must accept --interval parameter."""
        assert cmd_contains(
            "svp_visual_verify", "--interval", case_sensitive=False
        ) or cmd_contains("svp_visual_verify", "interval", case_sensitive=False)

    def test_visual_verify_interactions_parameter(self):
        """Must accept --interactions parameter."""
        assert cmd_contains(
            "svp_visual_verify", "--interactions", case_sensitive=False
        ) or cmd_contains("svp_visual_verify", "interaction", case_sensitive=False)


class TestVisualVerifyStandaloneUtility:
    """/svp:visual-verify is a standalone utility with no --phase value."""

    def test_visual_verify_is_standalone(self):
        """Must be described as standalone or utility."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"].lower()
        assert (
            "standalone" in content
            or "utility" in content
            or "not a routed command" in content
            or "not routed" in content
            or "no phase" in content
            or "no --phase" in content
        )

    def test_visual_verify_no_phase_value(self):
        """Must not have a --phase value for update_state.py."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"]
        # visual-verify should not include --phase with update_state
        has_update_state_phase = "--phase" in content and "update_state" in content
        assert not has_update_state_phase, (
            "svp_visual_verify should not have a --phase value for update_state.py"
        )


class TestVisualVerifySupplementaryNotAuthoritative:
    """/svp:visual-verify is supplementary, not authoritative."""

    def test_visual_verify_supplementary_nature(self):
        """Must describe itself as supplementary or non-authoritative."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"].lower()
        assert (
            "supplementary" in content
            or "not authoritative" in content
            or "not the authoritative" in content
            or "secondary" in content
        )

    def test_visual_verify_test_suite_is_authoritative(self):
        """Must reference the test suite as the authoritative verification."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"].lower()
        assert "test suite" in content or "test" in content


class TestVisualVerifyInvocationContexts:
    """/svp:visual-verify invocable by oracle agent and by human independently."""

    def test_visual_verify_oracle_agent_invocation(self):
        """Must reference oracle agent as an invoker."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"].lower()
        assert "oracle" in content

    def test_visual_verify_human_invocation(self):
        """Must reference human as an independent invoker."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"].lower()
        assert "human" in content

    def test_visual_verify_e_mode_green_runs(self):
        """Must reference E-mode green runs as the oracle invocation context."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"].lower()
        assert (
            "e-mode" in content
            or "e mode" in content
            or "green run" in content
            or "green" in content
        )


class TestVisualVerifyPersistedTestProjects:
    """/svp:visual-verify works with persisted test projects."""

    def test_visual_verify_persisted_test_projects(self):
        """Must reference persisted test projects."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"].lower()
        assert (
            "persist" in content
            or "persisted" in content
            or "saved" in content
            or "test project" in content
        )


# ===========================================================================
# Cross-group validation: Group A vs Group B distinction
# ===========================================================================


class TestGroupAGroupBDistinction:
    """Group A and Group B commands must have clearly different structures."""

    def test_group_a_commands_lack_prepare_task(self):
        """Group A commands should not reference prepare_task.py."""
        for cmd in GROUP_A_COMMANDS:
            content = COMMAND_DEFINITIONS[cmd].lower()
            assert "prepare_task" not in content, (
                f"Group A command {cmd!r} unexpectedly references prepare_task"
            )

    def test_group_a_commands_lack_update_state(self):
        """Group A commands should not reference update_state.py."""
        for cmd in GROUP_A_COMMANDS:
            content = COMMAND_DEFINITIONS[cmd].lower()
            assert "update_state" not in content, (
                f"Group A command {cmd!r} unexpectedly references update_state"
            )

    def test_group_b_standard_commands_have_prepare_task(self):
        """Standard Group B commands must reference prepare_task.

        Thin redirects (svp_bug per S3-119, svp_oracle per S3-79) are
        excluded — they dispatch agents via routing, not directly."""
        for cmd in GROUP_B_STANDARD:
            assert cmd_contains(cmd, "prepare_task", case_sensitive=False), (
                f"Group B command {cmd!r} missing prepare_task reference"
            )

    def test_group_b_thin_redirects_lack_prepare_task(self):
        """Thin-redirect Group B commands (svp_bug, svp_oracle) must NOT
        reference prepare_task — that machinery lives in _route_debug /
        _route_oracle after state entry."""
        for cmd in GROUP_B_THIN_REDIRECTS:
            assert not cmd_contains(cmd, "prepare_task", case_sensitive=False), (
                f"Thin-redirect command {cmd!r} unexpectedly references prepare_task"
            )

    def test_group_b_commands_have_update_state(self):
        """Group B commands must reference update_state."""
        for cmd in GROUP_B_COMMANDS:
            assert cmd_contains(cmd, "update_state", case_sensitive=False), (
                f"Group B command {cmd!r} missing update_state reference"
            )

    def test_group_b_commands_have_agent_reference(self):
        """Group B commands must reference agent invocation."""
        for cmd in GROUP_B_COMMANDS:
            assert cmd_contains(cmd, "agent", case_sensitive=False), (
                f"Group B command {cmd!r} missing agent reference"
            )


# ===========================================================================
# Per-command phase value correctness
# ===========================================================================


class TestPhaseValueCorrectness:
    """Each Group B command must reference its correct --phase value."""

    def test_help_has_correct_phase(self):
        content = COMMAND_DEFINITIONS["svp_help"]
        assert "help" in content.lower()

    def test_hint_has_correct_phase(self):
        content = COMMAND_DEFINITIONS["svp_hint"]
        assert "hint" in content.lower()

    def test_ref_has_correct_phase_reference_indexing(self):
        content = COMMAND_DEFINITIONS["svp_ref"]
        assert "reference_indexing" in content

    def test_redo_has_correct_phase(self):
        content = COMMAND_DEFINITIONS["svp_redo"]
        assert "redo" in content.lower()

    def test_bug_has_correct_entry_command(self):
        """Bug S3-119: svp_bug is a thin redirect using --command svp_bug_entry.
        The previous contract was --phase bug_triage; see TestGroupBPhaseValueBug
        for the bootstrap-path rationale."""
        content = COMMAND_DEFINITIONS["svp_bug"]
        assert "svp_bug_entry" in content

    def test_oracle_has_correct_phase(self):
        content = COMMAND_DEFINITIONS["svp_oracle"]
        assert "oracle" in content.lower()


# ===========================================================================
# All command definitions: uniqueness and distinctness
# ===========================================================================


class TestCommandDefinitionsUniqueness:
    """All command definitions must be distinct from each other."""

    def test_no_two_definitions_are_identical(self):
        """No two command definitions should have the same content."""
        names = list(COMMAND_DEFINITIONS.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                assert COMMAND_DEFINITIONS[names[i]] != COMMAND_DEFINITIONS[names[j]], (
                    f"Definitions for {names[i]!r} and {names[j]!r} are identical"
                )

    def test_each_definition_references_its_own_command(self):
        """Each definition should reference its own command name or purpose."""
        # Map underscore names to the slash-command style for matching
        name_to_slug = {
            "svp_help": "help",
            "svp_hint": "hint",
            "svp_ref": "ref",
            "svp_redo": "redo",
            "svp_bug": "bug",
            "svp_oracle": "oracle",
            "svp_save": "save",
            "svp_quit": "quit",
            "svp_status": "status",
            "svp_clean": "clean",
            "svp_visual_verify": "visual",
        }
        for name, slug in name_to_slug.items():
            content = COMMAND_DEFINITIONS[name].lower()
            assert slug in content, (
                f"Definition for {name!r} does not reference its slug {slug!r}"
            )


# ===========================================================================
# COMMAND_DEFINITIONS and COMMAND_NAMES consistency
# ===========================================================================


class TestDefinitionsAndNamesConsistency:
    """COMMAND_DEFINITIONS keys and COMMAND_NAMES must be consistent."""

    def test_every_name_has_definition(self):
        """Every entry in COMMAND_NAMES has a key in COMMAND_DEFINITIONS."""
        for name in COMMAND_NAMES:
            assert name in COMMAND_DEFINITIONS, (
                f"COMMAND_NAMES entry {name!r} has no definition"
            )

    def test_every_definition_has_name(self):
        """Every key in COMMAND_DEFINITIONS appears in COMMAND_NAMES."""
        for key in COMMAND_DEFINITIONS:
            assert key in COMMAND_NAMES, (
                f"COMMAND_DEFINITIONS key {key!r} not in COMMAND_NAMES"
            )

    def test_sets_are_equal(self):
        """The sets of names and definition keys are equal."""
        assert set(COMMAND_NAMES) == set(COMMAND_DEFINITIONS.keys())


# ===========================================================================
# Group B: five-step action cycle completeness
# ===========================================================================


class TestGroupBFiveStepCycleCompleteness:
    """Each Group B command must reference all five steps of the action cycle."""

    @pytest.mark.parametrize("cmd_name", GROUP_B_STANDARD)
    def test_step_1_prepare_task(self, cmd_name):
        """Step 1: run prepare_task.py --agent <type> --project-root . (oracle excluded per S3-79)."""
        assert cmd_contains(cmd_name, "prepare_task", case_sensitive=False)

    @pytest.mark.parametrize("cmd_name", GROUP_B_COMMANDS)
    def test_step_2_spawn_agent(self, cmd_name):
        """Step 2: spawn agent."""
        assert cmd_contains(cmd_name, "agent", case_sensitive=False)

    @pytest.mark.parametrize("cmd_name", GROUP_B_STANDARD)
    def test_step_3_write_last_status(self, cmd_name):
        """Step 3: write terminal status to last_status.txt.

        Thin redirects (svp_bug per S3-119, svp_oracle per S3-79 —
        though svp_oracle still writes ORACLE_REQUESTED) do not
        universally participate in this step. Restrict to the
        standard 5-step commands."""
        assert cmd_contains(cmd_name, "last_status", case_sensitive=False)

    @pytest.mark.parametrize("cmd_name", GROUP_B_COMMANDS)
    def test_step_4_update_state(self, cmd_name):
        """Step 4: run update_state.py --phase <phase>."""
        assert cmd_contains(cmd_name, "update_state", case_sensitive=False)

    @pytest.mark.parametrize("cmd_name", GROUP_B_COMMANDS)
    def test_step_5_rerun_routing(self, cmd_name):
        """Step 5: re-run routing script."""
        assert cmd_contains(cmd_name, "routing", case_sensitive=False)


# ===========================================================================
# Group B: phase parameter correctness via parametrize
# ===========================================================================


class TestGroupBPhaseParameterCorrectness:
    """Each Group B command has the correct --phase value."""

    @pytest.mark.parametrize("cmd_name,phase_value", list(PHASE_VALUES.items()))
    def test_phase_value_appears_in_definition(self, cmd_name, phase_value):
        """The phase value must appear in the command definition."""
        content = COMMAND_DEFINITIONS[cmd_name]
        assert phase_value in content, (
            f"Phase value {phase_value!r} not found in {cmd_name!r} definition"
        )


# ===========================================================================
# All commands: no None values
# ===========================================================================


class TestNoNoneValues:
    """No command definition value should be None."""

    @pytest.mark.parametrize("cmd_name", EXPECTED_COMMAND_NAMES)
    def test_definition_is_not_none(self, cmd_name):
        assert COMMAND_DEFINITIONS[cmd_name] is not None


# ===========================================================================
# Comprehensive topic coverage
# ===========================================================================


class TestComprehensiveTopicCoverage:
    """Verify all key topics from the behavioral contracts are covered."""

    def test_covers_all_11_commands(self):
        """All 11 commands are present in both COMMAND_NAMES and COMMAND_DEFINITIONS."""
        assert len(COMMAND_NAMES) == 11
        assert len(COMMAND_DEFINITIONS) == 11
        assert set(COMMAND_NAMES) == set(EXPECTED_COMMAND_NAMES)

    def test_covers_group_a_direct_invocation(self):
        """All Group A commands reference direct script invocation."""
        for cmd in GROUP_A_COMMANDS:
            assert cmd_contains(cmd, "cmd_", case_sensitive=False), (
                f"Group A command {cmd!r} missing cmd_ script reference"
            )

    def test_covers_group_b_action_cycle(self):
        """Standard Group B commands reference the complete action cycle (oracle excluded per S3-79)."""
        for cmd in GROUP_B_STANDARD:
            content = COMMAND_DEFINITIONS[cmd].lower()
            has_prepare = "prepare_task" in content
            has_agent = "agent" in content
            has_status = "last_status" in content
            has_update = "update_state" in content
            has_routing = "routing" in content
            assert (
                has_prepare and has_agent and has_status and has_update and has_routing
            ), (
                f"Group B command {cmd!r} missing action cycle elements: "
                f"prepare={has_prepare}, agent={has_agent}, status={has_status}, "
                f"update={has_update}, routing={has_routing}"
            )

    def test_covers_oracle_thin_redirect(self):
        """Bug S3-79: oracle is a thin redirect to the routing script."""
        content = COMMAND_DEFINITIONS["svp_oracle"].lower()
        has_routing = "routing" in content
        has_update = "update_state" in content
        has_no_scan = "do not scan directories" in content
        assert has_routing and has_update and has_no_scan, (
            f"Oracle thin redirect missing elements: "
            f"routing={has_routing}, update={has_update}, no_scan={has_no_scan}"
        )

    def test_covers_visual_verify_parameters(self):
        """Visual verify command covers all three parameters."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"].lower()
        has_target = "target" in content
        has_interval = "interval" in content
        has_interactions = "interaction" in content
        assert has_target and has_interval and has_interactions

    def test_covers_visual_verify_standalone_nature(self):
        """Visual verify is a standalone utility."""
        content = COMMAND_DEFINITIONS["svp_visual_verify"].lower()
        assert (
            "standalone" in content
            or "utility" in content
            or "not routed" in content
            or "no phase" in content
            or "no --phase" in content
        )

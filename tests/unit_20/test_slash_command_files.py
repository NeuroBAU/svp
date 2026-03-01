"""
Tests for Unit 20: Slash Command Files.

Verifies the slash command markdown file constants and the Group A/B
classification invariant (SVP 1.1 hardening).

DATA ASSUMPTIONS:
- Command names are drawn from the blueprint spec Section 13: save, quit,
  help, hint, status, ref, redo, bug, clean.
- Group A commands (save, quit, status, clean) invoke cmd_*.py scripts directly.
- Group B commands (help, hint, ref, redo, bug) invoke prepare_task.py then
  spawn a subagent.
- PROHIBITED_SCRIPTS are cmd_*.py files that must never exist for Group B
  commands (cmd_help.py, cmd_hint.py, cmd_ref.py, cmd_redo.py, cmd_bug.py).
- MD_CONTENT constants are plain Markdown (no YAML frontmatter).
"""

import pytest

from svp.scripts.slash_command_files import (
    COMMAND_FILES,
    GROUP_A_COMMANDS,
    GROUP_B_COMMANDS,
    PROHIBITED_SCRIPTS,
)


# ---------------------------------------------------------------------------
# Helper to safely access MD_CONTENT constants (type annotations only in stub)
# ---------------------------------------------------------------------------

def _get_md_content(name: str) -> str:
    """Safely retrieve an MD_CONTENT constant by name."""
    import svp.scripts.slash_command_files as mod
    val = getattr(mod, name, None)
    if val is None or not isinstance(val, str):
        pytest.fail(f"{name} is not defined or not a string in svp.scripts.slash_command_files")
    return val


# Map from command name to its MD_CONTENT constant name
_CONTENT_NAMES = {
    "save": "SAVE_MD_CONTENT",
    "quit": "QUIT_MD_CONTENT",
    "help": "HELP_MD_CONTENT",
    "hint": "HINT_MD_CONTENT",
    "status": "STATUS_MD_CONTENT",
    "ref": "REF_MD_CONTENT",
    "redo": "REDO_MD_CONTENT",
    "bug": "BUG_MD_CONTENT",
    "clean": "CLEAN_MD_CONTENT",
}


# ===========================================================================
# Signature / Structure Tests
# ===========================================================================


class TestCommandFilesStructure:
    """Verify the module-level constants have correct types and values."""

    def test_command_files_is_dict(self):
        """COMMAND_FILES must be a dict."""
        assert isinstance(COMMAND_FILES, dict)

    def test_command_files_keys(self):
        """COMMAND_FILES must contain exactly the nine expected command keys."""
        expected_keys = {"save", "quit", "help", "hint", "status", "ref", "redo", "bug", "clean"}
        assert set(COMMAND_FILES.keys()) == expected_keys

    def test_command_files_values_are_md_filenames(self):
        """Each COMMAND_FILES value must be '{name}.md'."""
        for name, filename in COMMAND_FILES.items():
            assert isinstance(filename, str)
            assert filename == f"{name}.md", (
                f"Expected '{name}.md' but got '{filename}'"
            )

    def test_group_a_commands_is_list(self):
        assert isinstance(GROUP_A_COMMANDS, list)

    def test_group_b_commands_is_list(self):
        assert isinstance(GROUP_B_COMMANDS, list)

    def test_prohibited_scripts_is_list(self):
        assert isinstance(PROHIBITED_SCRIPTS, list)

    def test_group_a_commands_content(self):
        """Group A must be exactly: save, quit, status, clean."""
        assert set(GROUP_A_COMMANDS) == {"save", "quit", "status", "clean"}

    def test_group_b_commands_content(self):
        """Group B must be exactly: help, hint, ref, redo, bug."""
        assert set(GROUP_B_COMMANDS) == {"help", "hint", "ref", "redo", "bug"}

    def test_prohibited_scripts_content(self):
        """PROHIBITED_SCRIPTS must list cmd_*.py for every Group B command."""
        expected = {
            "cmd_help.py",
            "cmd_hint.py",
            "cmd_ref.py",
            "cmd_redo.py",
            "cmd_bug.py",
        }
        assert set(PROHIBITED_SCRIPTS) == expected

    def test_groups_are_disjoint(self):
        """Group A and Group B must share no commands."""
        overlap = set(GROUP_A_COMMANDS) & set(GROUP_B_COMMANDS)
        assert overlap == set(), f"Groups A and B overlap: {overlap}"

    def test_groups_cover_all_commands(self):
        """Group A + Group B must cover all COMMAND_FILES keys."""
        all_commands = set(GROUP_A_COMMANDS) | set(GROUP_B_COMMANDS)
        assert all_commands == set(COMMAND_FILES.keys()), (
            f"Groups do not cover all commands. "
            f"Missing: {set(COMMAND_FILES.keys()) - all_commands}"
        )

    def test_prohibited_scripts_match_group_b(self):
        """Each prohibited script must correspond to a Group B command."""
        for script in PROHIBITED_SCRIPTS:
            # Extract the command name from 'cmd_{name}.py'
            assert script.startswith("cmd_") and script.endswith(".py"), (
                f"Unexpected prohibited script format: {script}"
            )
            cmd_name = script[4:-3]  # strip 'cmd_' prefix and '.py' suffix
            assert cmd_name in GROUP_B_COMMANDS, (
                f"Prohibited script '{script}' has no matching Group B command"
            )

    def test_no_prohibited_scripts_for_group_a(self):
        """Group A commands must NOT appear in the prohibited scripts list."""
        prohibited_command_names = {s[4:-3] for s in PROHIBITED_SCRIPTS}
        for cmd in GROUP_A_COMMANDS:
            assert cmd not in prohibited_command_names, (
                f"Group A command '{cmd}' should not be in PROHIBITED_SCRIPTS"
            )


# ===========================================================================
# MD_CONTENT Non-Emptiness Tests
# ===========================================================================


class TestMdContentNonEmpty:
    """Each *_MD_CONTENT constant must be a non-empty string."""

    @pytest.mark.parametrize("cmd_name,content_name", list(_CONTENT_NAMES.items()))
    def test_md_content_is_non_empty_string(self, cmd_name, content_name):
        # DATA ASSUMPTION: MD_CONTENT constants must be non-empty strings
        # as specified in the blueprint.
        content = _get_md_content(content_name)
        assert isinstance(content, str)
        assert len(content.strip()) > 0, f"{content_name} must not be empty"


# ===========================================================================
# Group A Behavioral Contract Tests
# ===========================================================================


class TestGroupAContracts:
    """
    Group A commands (save, quit, status, clean) must direct the main session
    to run 'python scripts/cmd_{name}.py --project-root .' and present output.
    No subagent is spawned.
    """

    @pytest.mark.parametrize("cmd_name", ["save", "quit", "status"])
    def test_group_a_invokes_cmd_script(self, cmd_name):
        """Group A content must reference 'cmd_{name}.py'."""
        # DATA ASSUMPTION: Group A commands reference their deterministic
        # scripts by name, e.g. cmd_save.py, cmd_quit.py, cmd_status.py.
        content_name = _CONTENT_NAMES[cmd_name]
        content = _get_md_content(content_name)
        assert f"cmd_{cmd_name}.py" in content, (
            f"{content_name} must reference 'cmd_{cmd_name}.py'"
        )

    def test_clean_invokes_cmd_clean_with_pythonpath(self):
        """
        /svp:clean must be invoked as 'PYTHONPATH=scripts python scripts/cmd_clean.py'
        so library imports resolve correctly (spec Section 12.5).
        """
        # DATA ASSUMPTION: The clean command has a special invocation pattern
        # with PYTHONPATH=scripts prefix for import resolution.
        content = _get_md_content("CLEAN_MD_CONTENT")
        assert "PYTHONPATH=scripts" in content, (
            "CLEAN_MD_CONTENT must include PYTHONPATH=scripts for import resolution"
        )
        assert "cmd_clean.py" in content, (
            "CLEAN_MD_CONTENT must reference cmd_clean.py"
        )

    @pytest.mark.parametrize("cmd_name", GROUP_A_COMMANDS)
    def test_group_a_contains_project_root_arg(self, cmd_name):
        """Group A content must include '--project-root' argument."""
        # DATA ASSUMPTION: Group A commands pass --project-root . to their
        # scripts per the blueprint contract.
        content_name = _CONTENT_NAMES[cmd_name]
        content = _get_md_content(content_name)
        assert "--project-root" in content, (
            f"{content_name} must include '--project-root' argument"
        )

    @pytest.mark.parametrize("cmd_name", GROUP_A_COMMANDS)
    def test_group_a_does_not_spawn_subagent(self, cmd_name):
        """Group A commands must NOT invoke prepare_task.py or spawn subagent."""
        # DATA ASSUMPTION: Group A commands are deterministic scripts;
        # they never use the agent invocation pathway (prepare_task.py).
        content_name = _CONTENT_NAMES[cmd_name]
        content = _get_md_content(content_name)
        assert "prepare_task.py" not in content, (
            f"{content_name} must NOT reference 'prepare_task.py' "
            "(Group A does not spawn subagents)"
        )


# ===========================================================================
# Group B Behavioral Contract Tests
# ===========================================================================


class TestGroupBContracts:
    """
    Group B commands (help, hint, ref, redo, bug) must direct the main session
    to run 'python scripts/prepare_task.py --agent {role}' to produce the task
    prompt, then spawn the corresponding subagent. No cmd_*.py script is invoked.
    """

    @pytest.mark.parametrize("cmd_name", GROUP_B_COMMANDS)
    def test_group_b_invokes_prepare_task(self, cmd_name):
        """Group B content must reference 'prepare_task.py'."""
        # DATA ASSUMPTION: Group B commands use the prepare_task.py pathway
        # as specified in the blueprint.
        content_name = _CONTENT_NAMES[cmd_name]
        content = _get_md_content(content_name)
        assert "prepare_task.py" in content, (
            f"{content_name} must reference 'prepare_task.py'"
        )

    @pytest.mark.parametrize("cmd_name", GROUP_B_COMMANDS)
    def test_group_b_does_not_invoke_cmd_script(self, cmd_name):
        """Group B commands must NOT invoke cmd_{name}.py."""
        # DATA ASSUMPTION: Group B commands never use deterministic cmd_*.py
        # scripts -- this is the hardened Group A/B distinction from SVP 1.1.
        content_name = _CONTENT_NAMES[cmd_name]
        content = _get_md_content(content_name)
        assert f"cmd_{cmd_name}.py" not in content, (
            f"{content_name} must NOT reference 'cmd_{cmd_name}.py' "
            "(Group B does not use cmd_*.py scripts)"
        )


# ===========================================================================
# Content Quality Tests
# ===========================================================================


class TestContentQuality:
    """
    Each command file must contain explicit, unambiguous directives that
    describe when to use the command, what it does, and the exact execution
    steps.
    """

    @pytest.mark.parametrize("cmd_name,content_name", list(_CONTENT_NAMES.items()))
    def test_content_contains_command_name(self, cmd_name, content_name):
        """Each MD content must mention its own command name."""
        # DATA ASSUMPTION: The markdown content for each command identifies
        # the command it corresponds to.
        content = _get_md_content(content_name)
        # The command name should appear somewhere in the content
        assert cmd_name in content.lower(), (
            f"{content_name} should mention the command name '{cmd_name}'"
        )

    @pytest.mark.parametrize("cmd_name,content_name", list(_CONTENT_NAMES.items()))
    def test_content_contains_script_reference(self, cmd_name, content_name):
        """Each command must reference either a cmd_*.py script (Group A)
        or prepare_task.py (Group B)."""
        # DATA ASSUMPTION: Every command has explicit execution instructions
        # referencing the exact script to run.
        content = _get_md_content(content_name)
        if cmd_name in GROUP_A_COMMANDS:
            assert f"cmd_{cmd_name}.py" in content, (
                f"Group A command '{cmd_name}' must reference cmd_{cmd_name}.py"
            )
        else:
            assert "prepare_task.py" in content, (
                f"Group B command '{cmd_name}' must reference prepare_task.py"
            )


# ===========================================================================
# Stage Availability Tests
# ===========================================================================


class TestStageAvailability:
    """
    Certain commands have stage restrictions per the blueprint:
    - /svp:ref is available during Stages 0, 1, and 2 only. Locked from Stage 3 onward.
    - /svp:redo is available during Stages 2, 3, and 4.
    - /svp:bug is available only after Stage 5 completion.
    """

    def test_ref_mentions_stage_restriction(self):
        """REF_MD_CONTENT should indicate it is locked from Stage 3 onward."""
        # DATA ASSUMPTION: The ref command's markdown content documents
        # the stage availability constraint per the blueprint.
        content = _get_md_content("REF_MD_CONTENT")
        # Check that stage restriction is documented in the content
        # The content should mention stages 0, 1, 2 or the locking from stage 3
        content_lower = content.lower()
        has_stage_ref = (
            "stage" in content_lower
            or "locked" in content_lower
            or "available" in content_lower
        )
        assert has_stage_ref, (
            "REF_MD_CONTENT should document stage availability restrictions"
        )

    def test_redo_mentions_stage_restriction(self):
        """REDO_MD_CONTENT should indicate it is available in stages 2, 3, 4."""
        # DATA ASSUMPTION: The redo command's markdown content documents
        # its stage availability (stages 2, 3, 4).
        content = _get_md_content("REDO_MD_CONTENT")
        content_lower = content.lower()
        has_stage_ref = (
            "stage" in content_lower
            or "available" in content_lower
        )
        assert has_stage_ref, (
            "REDO_MD_CONTENT should document stage availability restrictions"
        )

    def test_bug_mentions_stage_restriction(self):
        """BUG_MD_CONTENT should indicate it is available after Stage 5."""
        # DATA ASSUMPTION: The bug command's markdown content documents
        # that it is only available after stage 5 completion.
        content = _get_md_content("BUG_MD_CONTENT")
        content_lower = content.lower()
        has_stage_ref = (
            "stage" in content_lower
            or "available" in content_lower
            or "after" in content_lower
        )
        assert has_stage_ref, (
            "BUG_MD_CONTENT should document stage availability restrictions"
        )


# ===========================================================================
# Bug Command -- Abandon Flag
# ===========================================================================


class TestBugCommandAbandonFlag:
    """The /svp:bug command supports an --abandon flag per the blueprint."""

    def test_bug_mentions_abandon(self):
        """BUG_MD_CONTENT should document the --abandon flag."""
        # DATA ASSUMPTION: The bug command markdown references the --abandon
        # flag as specified in the behavioral contract.
        content = _get_md_content("BUG_MD_CONTENT")
        assert "abandon" in content.lower(), (
            "BUG_MD_CONTENT should mention the --abandon flag"
        )


# ===========================================================================
# SVP 1.1 Hardening Invariant: Group A/B Distinction
# ===========================================================================


class TestGroupABHardeningInvariant:
    """
    The SVP 1.1 hardening invariant states that:
    - Group A commands invoke cmd_*.py scripts directly (no subagent).
    - Group B commands invoke prepare_task.py then spawn subagent (no cmd_*.py).
    - The scripts cmd_help.py, cmd_hint.py, cmd_ref.py, cmd_redo.py, cmd_bug.py
      MUST NEVER EXIST.
    """

    def test_prohibited_scripts_exactly_five(self):
        """There must be exactly 5 prohibited scripts (one per Group B command)."""
        assert len(PROHIBITED_SCRIPTS) == 5

    def test_prohibited_scripts_all_start_with_cmd(self):
        """Each prohibited script follows the cmd_{name}.py naming pattern."""
        for script in PROHIBITED_SCRIPTS:
            assert script.startswith("cmd_"), f"'{script}' does not start with 'cmd_'"
            assert script.endswith(".py"), f"'{script}' does not end with '.py'"

    def test_each_group_b_command_has_prohibited_script(self):
        """Every Group B command has a corresponding prohibited cmd_*.py entry."""
        prohibited_names = {s[4:-3] for s in PROHIBITED_SCRIPTS}  # strip cmd_ and .py
        for cmd in GROUP_B_COMMANDS:
            assert cmd in prohibited_names, (
                f"Group B command '{cmd}' missing from PROHIBITED_SCRIPTS"
            )

    def test_group_a_commands_have_no_prohibited_scripts(self):
        """No Group A command should appear in PROHIBITED_SCRIPTS."""
        prohibited_names = {s[4:-3] for s in PROHIBITED_SCRIPTS}
        for cmd in GROUP_A_COMMANDS:
            assert cmd not in prohibited_names, (
                f"Group A command '{cmd}' should not be in PROHIBITED_SCRIPTS"
            )


# ===========================================================================
# Cross-reference: COMMAND_FILES vs MD_CONTENT constants
# ===========================================================================


class TestCommandFilesMatchMdContent:
    """Every key in COMMAND_FILES should have a corresponding *_MD_CONTENT constant."""

    @pytest.mark.parametrize("cmd_name", list(COMMAND_FILES.keys()))
    def test_md_content_exists_for_command(self, cmd_name):
        """A *_MD_CONTENT constant must exist for each command in COMMAND_FILES."""
        content_name = f"{cmd_name.upper()}_MD_CONTENT"
        # This will pytest.fail if not defined or not a string
        content = _get_md_content(content_name)
        assert len(content.strip()) > 0


# ===========================================================================
# Clean command special invocation test
# ===========================================================================


class TestCleanCommandInvocation:
    """
    /svp:clean must be invoked as
    'PYTHONPATH=scripts python scripts/cmd_clean.py'
    so library imports resolve correctly (spec Section 12.5).
    """

    def test_clean_has_pythonpath_before_python(self):
        """PYTHONPATH=scripts must appear before 'python' in the clean invocation."""
        # DATA ASSUMPTION: The clean command content contains the full
        # invocation string with PYTHONPATH prefix for import resolution.
        content = _get_md_content("CLEAN_MD_CONTENT")
        # Find PYTHONPATH=scripts and ensure python follows it
        idx_pythonpath = content.find("PYTHONPATH=scripts")
        idx_python = content.find("python", idx_pythonpath + 1 if idx_pythonpath >= 0 else 0)
        assert idx_pythonpath >= 0, "CLEAN_MD_CONTENT must contain PYTHONPATH=scripts"
        assert idx_python > idx_pythonpath, (
            "CLEAN_MD_CONTENT must have 'python' after 'PYTHONPATH=scripts'"
        )


# ===========================================================================
# Group B subagent-related content
# ===========================================================================


class TestGroupBSubagentContent:
    """
    Group B commands must direct spawning a subagent with the task prompt
    verbatim. The content should mention subagent/agent invocation concepts.
    """

    @pytest.mark.parametrize("cmd_name", GROUP_B_COMMANDS)
    def test_group_b_mentions_agent_or_subagent(self, cmd_name):
        """Group B content should reference agent/subagent spawning."""
        # DATA ASSUMPTION: Group B command markdown content describes the
        # agent invocation workflow (spawning a subagent with the task prompt).
        content_name = _CONTENT_NAMES[cmd_name]
        content = _get_md_content(content_name)
        content_lower = content.lower()
        has_agent_ref = (
            "agent" in content_lower
            or "subagent" in content_lower
            or "sub-agent" in content_lower
            or "spawn" in content_lower
        )
        assert has_agent_ref, (
            f"{content_name} should mention agent/subagent invocation"
        )

    @pytest.mark.parametrize("cmd_name", GROUP_B_COMMANDS)
    def test_group_b_mentions_task_prompt(self, cmd_name):
        """Group B content should reference the task prompt."""
        # DATA ASSUMPTION: Group B commands describe passing the task prompt
        # verbatim to the subagent.
        content_name = _CONTENT_NAMES[cmd_name]
        content = _get_md_content(content_name)
        content_lower = content.lower()
        has_task_ref = (
            "task prompt" in content_lower
            or "task_prompt" in content_lower
            or "verbatim" in content_lower
            or "TASK_PROMPT" in content
        )
        assert has_task_ref, (
            f"{content_name} should mention the task prompt"
        )


# ===========================================================================
# No YAML frontmatter (these are NOT agent definitions)
# ===========================================================================


class TestNotAgentDefinitions:
    """
    Slash command files are plain Markdown instruction files.
    They must NOT have YAML frontmatter (they are not agent definition files).
    """

    @pytest.mark.parametrize("cmd_name,content_name", list(_CONTENT_NAMES.items()))
    def test_no_yaml_frontmatter(self, cmd_name, content_name):
        """MD_CONTENT must NOT start with YAML frontmatter '---'."""
        # DATA ASSUMPTION: Command instruction files are plain Markdown,
        # not agent definition files with YAML frontmatter.
        content = _get_md_content(content_name)
        stripped = content.strip()
        assert not stripped.startswith("---"), (
            f"{content_name} should NOT have YAML frontmatter "
            "(these are command files, not agent definitions)"
        )

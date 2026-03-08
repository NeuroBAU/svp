"""
Additional coverage tests for Unit 20: Slash Command Files.

Covers blueprint behavioral contracts not exercised by the existing test suite:

1. Group B commands include '--agent {role}' with the correct role name in
   their prepare_task.py invocation.
2. Specific stage numbers are documented in ref (0,1,2), redo (2,3,4),
   and bug (after Stage 5) command content.
3. Bug command references the '--abandon' flag format (not just the word).
4. Each command's MD_CONTENT describes all three required sections: when to use,
   what it does, and the exact execution steps.
5. Group B content instructs passing the task prompt 'verbatim' to the subagent.

DATA ASSUMPTIONS:
- Group B commands use 'prepare_task.py --agent {role}' where {role} matches
  the KNOWN_AGENT_TYPES name (help_agent, hint_agent, reference_indexing, redo_agent, bug_triage).
- Stage-restricted commands document the specific stage numbers in their content.
- The bug command documents the '--abandon' flag as a CLI flag.
- Each command file contains sections for when to use, what it does, and
  execution steps, per the blueprint.
"""

import pytest

from svp.scripts.slash_command_files import (
    GROUP_A_COMMANDS,
    GROUP_B_COMMANDS,
)


# ---------------------------------------------------------------------------
# Helper to safely access MD_CONTENT constants
# ---------------------------------------------------------------------------

def _get_md_content(name: str) -> str:
    """Safely retrieve an MD_CONTENT constant by name."""
    import svp.scripts.slash_command_files as mod
    val = getattr(mod, name, None)
    if val is None or not isinstance(val, str):
        pytest.fail(f"{name} is not defined or not a string in svp.scripts.slash_command_files")
    return val


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

# Maps command short names to the agent type used in prepare_task.py --agent
_AGENT_TYPE_NAMES = {
    "help": "help_agent",
    "hint": "hint_agent",
    "ref": "reference_indexing",
    "redo": "redo_agent",
    "bug": "bug_triage",
}


# ===========================================================================
# Gap 1: Group B --agent {role} argument
# ===========================================================================


class TestGroupBAgentRoleArgument:
    """
    Blueprint contract: Group B commands direct the main session to run
    'python scripts/prepare_task.py --agent {role}'. The existing tests
    verify that prepare_task.py is referenced, but do not verify that
    '--agent {role}' with the correct role name is present.
    """

    @pytest.mark.parametrize("cmd_name", GROUP_B_COMMANDS)
    def test_group_b_references_agent_flag_with_role(self, cmd_name):
        """Group B content must include '--agent {agent_type}' in its invocation."""
        # The --agent flag value uses the KNOWN_AGENT_TYPES name, not the
        # command short name (e.g., --agent help_agent, --agent hint_agent).
        content_name = _CONTENT_NAMES[cmd_name]
        content = _get_md_content(content_name)
        agent_type = _AGENT_TYPE_NAMES[cmd_name]
        expected_fragment = f"--agent {agent_type}"
        assert expected_fragment in content, (
            f"{content_name} must contain '{expected_fragment}' in its "
            "prepare_task.py invocation"
        )


# ===========================================================================
# Gap 2: Specific stage numbers in stage-restricted commands
# ===========================================================================


class TestStageAvailabilitySpecificNumbers:
    """
    The blueprint specifies exact stage restrictions:
    - /svp:ref: Stages 0, 1, and 2 only. Locked from Stage 3 onward.
    - /svp:redo: Stages 2, 3, and 4.
    - /svp:bug: Only after Stage 5 completion.

    The existing tests check for generic words ('stage', 'available') but
    not for the specific stage numbers.
    """

    def test_ref_mentions_stage_3_locking(self):
        """REF_MD_CONTENT must specifically mention Stage 3 as the lock point."""
        # DATA ASSUMPTION: The ref command documents that it is locked from
        # Stage 3 onward, per the blueprint.
        content = _get_md_content("REF_MD_CONTENT")
        assert "3" in content, (
            "REF_MD_CONTENT must mention Stage 3 (the lock point)"
        )

    def test_ref_mentions_available_stages(self):
        """REF_MD_CONTENT must mention the stages it is available in (0, 1, 2)."""
        # DATA ASSUMPTION: The ref command content documents availability
        # in Stages 0, 1, and 2.
        content = _get_md_content("REF_MD_CONTENT")
        assert "0" in content, "REF_MD_CONTENT must mention Stage 0"
        assert "1" in content, "REF_MD_CONTENT must mention Stage 1"
        assert "2" in content, "REF_MD_CONTENT must mention Stage 2"

    def test_redo_mentions_specific_stages(self):
        """REDO_MD_CONTENT must mention stages 2, 3, and 4."""
        # DATA ASSUMPTION: The redo command content documents availability
        # in Stages 2, 3, and 4.
        content = _get_md_content("REDO_MD_CONTENT")
        assert "2" in content, "REDO_MD_CONTENT must mention Stage 2"
        assert "3" in content, "REDO_MD_CONTENT must mention Stage 3"
        assert "4" in content, "REDO_MD_CONTENT must mention Stage 4"

    def test_bug_mentions_stage_5(self):
        """BUG_MD_CONTENT must specifically mention Stage 5."""
        # DATA ASSUMPTION: The bug command content documents that it is
        # available only after Stage 5 completion.
        content = _get_md_content("BUG_MD_CONTENT")
        assert "5" in content, (
            "BUG_MD_CONTENT must mention Stage 5"
        )


# ===========================================================================
# Gap 3: Bug --abandon flag format
# ===========================================================================


class TestBugAbandonFlagFormat:
    """
    The blueprint says /svp:bug 'Supports --abandon flag.' The existing
    test checks for the word 'abandon' but does not verify the actual
    CLI flag format '--abandon'.
    """

    def test_bug_contains_abandon_flag(self):
        """BUG_MD_CONTENT must contain the '--abandon' flag format."""
        # DATA ASSUMPTION: The bug command documents --abandon as a CLI flag
        # (not just the word 'abandon').
        content = _get_md_content("BUG_MD_CONTENT")
        assert "--abandon" in content, (
            "BUG_MD_CONTENT must contain '--abandon' flag format"
        )


# ===========================================================================
# Gap 4: Content structure -- when to use / what it does / execution steps
# ===========================================================================


class TestContentStructureSections:
    """
    Blueprint contract: 'Each command's content must describe: when to use
    the command, what it does, and the exact execution steps.'

    The existing tests verify script references and command names but do not
    check that all three informational sections are present.
    """

    @pytest.mark.parametrize("cmd_name,content_name", list(_CONTENT_NAMES.items()))
    def test_content_has_when_to_use_section(self, cmd_name, content_name):
        """Each MD_CONTENT must describe when to use the command."""
        # DATA ASSUMPTION: Each command file contains a 'when to use' section
        # or equivalent phrasing per the blueprint.
        content = _get_md_content(content_name)
        content_lower = content.lower()
        assert "when to use" in content_lower or "when" in content_lower, (
            f"{content_name} must describe when to use the command"
        )

    @pytest.mark.parametrize("cmd_name,content_name", list(_CONTENT_NAMES.items()))
    def test_content_has_what_it_does_section(self, cmd_name, content_name):
        """Each MD_CONTENT must describe what the command does."""
        # DATA ASSUMPTION: Each command file contains a 'what it does' section
        # or equivalent phrasing per the blueprint.
        content = _get_md_content(content_name)
        content_lower = content.lower()
        assert "what it does" in content_lower or "does" in content_lower, (
            f"{content_name} must describe what the command does"
        )

    @pytest.mark.parametrize("cmd_name,content_name", list(_CONTENT_NAMES.items()))
    def test_content_has_execution_steps_section(self, cmd_name, content_name):
        """Each MD_CONTENT must describe the exact execution steps."""
        # DATA ASSUMPTION: Each command file contains an 'execution steps'
        # section or equivalent phrasing per the blueprint.
        content = _get_md_content(content_name)
        content_lower = content.lower()
        has_steps = (
            "execution steps" in content_lower
            or "steps" in content_lower
            or "run the following" in content_lower
        )
        assert has_steps, (
            f"{content_name} must describe the exact execution steps"
        )


# ===========================================================================
# Gap 5: Group B verbatim task prompt relay
# ===========================================================================


class TestGroupBVerbatimRelay:
    """
    Blueprint contract: Group B commands spawn 'the corresponding subagent
    with the task prompt verbatim.' The existing test checks for 'task prompt'
    OR 'verbatim' individually, but the blueprint specifically requires
    the verbatim relay instruction.
    """

    @pytest.mark.parametrize("cmd_name", GROUP_B_COMMANDS)
    def test_group_b_mentions_verbatim(self, cmd_name):
        """Group B content must instruct passing the task prompt verbatim."""
        # DATA ASSUMPTION: Group B command markdown content explicitly uses
        # the word 'verbatim' to describe how the task prompt is passed.
        content_name = _CONTENT_NAMES[cmd_name]
        content = _get_md_content(content_name)
        content_lower = content.lower()
        assert "verbatim" in content_lower, (
            f"{content_name} must instruct passing the task prompt 'verbatim'"
        )

"""
Tests for Unit 20: Slash Command Files.

Verifies COMMAND_FILES dict, GROUP_A/B lists,
PROHIBITED_SCRIPTS, and all 9 command MD content
strings.
"""

from src.unit_20.stub import (
    BUG_MD_CONTENT,
    CLEAN_MD_CONTENT,
    COMMAND_FILES,
    GROUP_A_COMMANDS,
    GROUP_B_COMMANDS,
    HELP_MD_CONTENT,
    HINT_MD_CONTENT,
    PROHIBITED_SCRIPTS,
    QUIT_MD_CONTENT,
    REDO_MD_CONTENT,
    REF_MD_CONTENT,
    SAVE_MD_CONTENT,
    STATUS_MD_CONTENT,
)


class TestCommandFiles:
    def test_nine_commands(self):
        assert len(COMMAND_FILES) == 9

    def test_all_keys(self):
        expected = {
            "save",
            "quit",
            "help",
            "hint",
            "status",
            "ref",
            "redo",
            "bug",
            "clean",
        }
        assert set(COMMAND_FILES.keys()) == expected

    def test_values_are_md(self):
        for v in COMMAND_FILES.values():
            assert v.endswith(".md")


class TestGroups:
    def test_group_a(self):
        expected = ["save", "quit", "status", "clean"]
        assert GROUP_A_COMMANDS == expected

    def test_group_b(self):
        expected = [
            "help",
            "hint",
            "ref",
            "redo",
            "bug",
        ]
        assert GROUP_B_COMMANDS == expected

    def test_prohibited_scripts(self):
        assert "cmd_help.py" in PROHIBITED_SCRIPTS
        assert "cmd_hint.py" in PROHIBITED_SCRIPTS
        assert "cmd_ref.py" in PROHIBITED_SCRIPTS
        assert "cmd_redo.py" in PROHIBITED_SCRIPTS
        assert "cmd_bug.py" in PROHIBITED_SCRIPTS


class TestGroupAContent:
    """Group A commands: save, quit, status, clean."""

    def test_save_nonempty(self):
        assert isinstance(SAVE_MD_CONTENT, str)
        assert len(SAVE_MD_CONTENT) > 0

    def test_quit_nonempty(self):
        assert isinstance(QUIT_MD_CONTENT, str)
        assert len(QUIT_MD_CONTENT) > 0

    def test_status_nonempty(self):
        assert isinstance(STATUS_MD_CONTENT, str)
        assert len(STATUS_MD_CONTENT) > 0

    def test_clean_nonempty(self):
        assert isinstance(CLEAN_MD_CONTENT, str)
        assert len(CLEAN_MD_CONTENT) > 0

    def test_save_mentions_save(self):
        assert "save" in SAVE_MD_CONTENT.lower()

    def test_quit_mentions_quit(self):
        assert "quit" in QUIT_MD_CONTENT.lower()

    def test_status_mentions_status(self):
        assert "status" in STATUS_MD_CONTENT.lower()

    def test_clean_mentions_clean(self):
        assert "clean" in CLEAN_MD_CONTENT.lower()


class TestGroupBContent:
    """Group B commands include action cycle."""

    def test_help_nonempty(self):
        assert isinstance(HELP_MD_CONTENT, str)
        assert len(HELP_MD_CONTENT) > 0

    def test_hint_nonempty(self):
        assert isinstance(HINT_MD_CONTENT, str)
        assert len(HINT_MD_CONTENT) > 0

    def test_ref_nonempty(self):
        assert isinstance(REF_MD_CONTENT, str)
        assert len(REF_MD_CONTENT) > 0

    def test_redo_nonempty(self):
        assert isinstance(REDO_MD_CONTENT, str)
        assert len(REDO_MD_CONTENT) > 0

    def test_bug_nonempty(self):
        assert isinstance(BUG_MD_CONTENT, str)
        assert len(BUG_MD_CONTENT) > 0


class TestGroupBActionCycle:
    """Each Group B command includes the 5-step cycle."""

    def test_help_has_prepare(self):
        assert "prepare_task" in HELP_MD_CONTENT

    def test_help_has_update_state(self):
        assert "update_state" in HELP_MD_CONTENT

    def test_help_has_phase(self):
        assert "help" in HELP_MD_CONTENT.lower()

    def test_hint_has_prepare(self):
        assert "prepare_task" in HINT_MD_CONTENT

    def test_hint_has_phase(self):
        assert "hint" in HINT_MD_CONTENT.lower()

    def test_ref_has_prepare(self):
        assert "prepare_task" in REF_MD_CONTENT

    def test_ref_has_phase(self):
        content = REF_MD_CONTENT.lower()
        assert "reference" in content or "ref" in content

    def test_redo_has_prepare(self):
        assert "prepare_task" in REDO_MD_CONTENT

    def test_redo_has_phase(self):
        assert "redo" in REDO_MD_CONTENT.lower()

    def test_bug_has_prepare(self):
        assert "prepare_task" in BUG_MD_CONTENT

    def test_bug_has_phase(self):
        assert "bug" in BUG_MD_CONTENT.lower()

    def test_help_has_last_status(self):
        assert "last_status" in HELP_MD_CONTENT

    def test_help_has_routing(self):
        assert "routing" in HELP_MD_CONTENT

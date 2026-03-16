"""
Tests for Unit 21: Orchestration Skill.

Verifies SKILL_MD_CONTENT string constant contains
the required structural elements.
"""

from orchestration_skill import SKILL_MD_CONTENT


class TestSkillMdContent:
    def test_is_nonempty_string(self):
        assert isinstance(SKILL_MD_CONTENT, str)
        assert len(SKILL_MD_CONTENT) > 0

    def test_mentions_six_step_cycle(self):
        content = SKILL_MD_CONTENT.lower()
        assert "six" in content or "6" in content
        assert "action" in content or "cycle" in content

    def test_mentions_routing_script(self):
        assert "routing" in SKILL_MD_CONTENT

    def test_mentions_verbatim_relay(self):
        content = SKILL_MD_CONTENT.lower()
        assert "verbatim" in content

    def test_mentions_task_prompt(self):
        content = SKILL_MD_CONTENT.lower()
        assert "task_prompt" in content or ("task prompt" in content)

    def test_mentions_last_status(self):
        assert "last_status" in SKILL_MD_CONTENT

    def test_mentions_group_b_bypass(self):
        content = SKILL_MD_CONTENT.lower()
        assert "group b" in content or ("slash" in content and "command" in content)

    def test_mentions_defer_human_input(self):
        content = SKILL_MD_CONTENT.lower()
        assert "defer" in content

    def test_mentions_prepare_command(self):
        content = SKILL_MD_CONTENT.lower()
        assert "prepare" in content

    def test_mentions_post_command(self):
        content = SKILL_MD_CONTENT.lower()
        assert "post" in content

    def test_mentions_action_block(self):
        content = SKILL_MD_CONTENT.lower()
        assert "action" in content

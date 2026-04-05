"""Regression tests for Bug S3-87: Orchestration skill name prefix consistency.

The orchestration skill name must follow the same svp:svp_* prefix pattern
as all SVP commands. Claude Code derives command names from
{namespace}:{filename_stem}, so svp_bug.md becomes svp:svp_bug. The skill
frontmatter name must match this convention: svp:svp_orchestration.
"""

import re

from src.unit_26.stub import ORCHESTRATION_SKILL


class TestSkillNamePrefixConsistency:
    """The skill name must use the svp:svp_* prefix pattern (Bug S3-87)."""

    def test_skill_name_is_svp_svp_orchestration(self):
        """Frontmatter name must be 'svp:svp_orchestration'."""
        match = re.match(r"^---\s*\n(.*?)\n---", ORCHESTRATION_SKILL, re.DOTALL)
        assert match, "No frontmatter found"
        fm = match.group(1)
        assert 'name: "svp:svp_orchestration"' in fm, (
            "Skill name must be 'svp:svp_orchestration' to match "
            "the svp:svp_* command naming convention"
        )

    def test_skill_name_not_bare_orchestration(self):
        """Regression: name must NOT be the old 'svp:orchestration' (missing prefix)."""
        match = re.match(r"^---\s*\n(.*?)\n---", ORCHESTRATION_SKILL, re.DOTALL)
        assert match, "No frontmatter found"
        fm = match.group(1)
        # Must not contain the old name without the svp_ prefix
        # Use a negative pattern: "svp:orchestration" that is NOT "svp:svp_orchestration"
        lines = fm.split("\n")
        for line in lines:
            if line.strip().startswith("name:"):
                assert "svp:svp_orchestration" in line, (
                    f"Skill name line '{line.strip()}' is missing the svp_ prefix"
                )

    def test_skill_name_not_hyphenated(self):
        """Regression: name must NOT be 'svp-orchestration' (S3-69)."""
        match = re.match(r"^---\s*\n(.*?)\n---", ORCHESTRATION_SKILL, re.DOTALL)
        assert match, "No frontmatter found"
        fm = match.group(1)
        assert "svp-orchestration" not in fm, (
            "Skill name must not use hyphen separator (S3-69)"
        )

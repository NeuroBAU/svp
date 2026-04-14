"""Regression tests for Bug S3-121: Orchestration skill name correction (inverts S3-87).

S3-87 was a mis-diagnosis. It observed that the orchestration skill loaded as
`svp:orchestration` while commands loaded as `svp:svp_bug`, and "aligned" the
skill frontmatter to `svp:svp_orchestration` instead of fixing the commands.
That edit was also functionally inert: Claude Code derives skill names from the
directory path (`skills/orchestration/` -> `svp:orchestration`), not from the
frontmatter `name` field. The frontmatter field is documentation that should
match reality.

S3-121 corrects both halves of the original mistake:
  1. Renames all 11 command files from svp_*.md to bare <name>.md so they
     register as `/svp:<name>` instead of `/svp:svp_<name>`. (Tested in
     test_bug_s3_121_command_double_prefix.py.)
  2. Reverts the S3-87 frontmatter edit so the skill frontmatter name matches
     the directory-derived registration `svp:orchestration`. (Tested here.)

The S3-69 hyphen guard (`svp-orchestration` forbidden) is preserved because
that bug is still a real forbidden form.
"""

import re

from orchestration_skill import ORCHESTRATION_SKILL


class TestSkillNameCorrection:
    """The skill name must be `svp:orchestration` (Bug S3-121 inverts S3-87)."""

    def test_skill_name_is_svp_orchestration(self):
        """Frontmatter name must be 'svp:orchestration' (matches directory path)."""
        match = re.match(r"^---\s*\n(.*?)\n---", ORCHESTRATION_SKILL, re.DOTALL)
        assert match, "No frontmatter found"
        fm = match.group(1)
        assert 'name: "svp:orchestration"' in fm, (
            "Skill name must be 'svp:orchestration' to match the directory-derived "
            "Claude Code registration (skills/orchestration/ -> svp:orchestration)"
        )

    def test_skill_name_not_double_prefixed(self):
        """Regression guard (S3-121): name must NOT be 'svp:svp_orchestration'.

        This is the negative sentinel that would have caught S3-87's mis-diagnosis
        had it existed at that time. If someone re-introduces the double-prefix form
        in the future, this assertion fires immediately.
        """
        match = re.match(r"^---\s*\n(.*?)\n---", ORCHESTRATION_SKILL, re.DOTALL)
        assert match, "No frontmatter found"
        fm = match.group(1)
        assert "svp:svp_orchestration" not in fm, (
            "Skill frontmatter must NOT contain 'svp:svp_orchestration' (S3-121 regression). "
            "Claude Code derives skill names from the directory path, not the frontmatter; "
            "the double-prefix form is documentation drift that misled S3-87."
        )

    def test_skill_name_not_hyphenated(self):
        """Regression (S3-69): name must NOT be 'svp-orchestration'."""
        match = re.match(r"^---\s*\n(.*?)\n---", ORCHESTRATION_SKILL, re.DOTALL)
        assert match, "No frontmatter found"
        fm = match.group(1)
        assert "svp-orchestration" not in fm, (
            "Skill name must not use hyphen separator (S3-69)"
        )

"""Regression tests for Bug S3-121: Command filename double-prefix.

Plugin command files were shipped as `svp_bug.md`, `svp_save.md`, etc.
Claude Code prepends the plugin namespace (`svp`) to the filename stem
without stripping any prefix, so these registered as `/svp:svp_bug`
instead of `/svp:bug`. The fix renames all 11 command files to bare
names (`bug.md`, `save.md`, ...). This file locks the bare-name form
against regression by inspecting the source-of-truth `COMMAND_NAMES`
list and `COMMAND_DEFINITIONS` dict keys in Unit 25's stub.

The companion test (test_bug_s3_121_skill_name_correction.py) covers
the inverted half of the fix: reverting S3-87's mis-diagnosed skill
frontmatter edit.
"""

import re

from slash_commands import COMMAND_DEFINITIONS, COMMAND_NAMES


class TestCommandNamesBareForm:
    """COMMAND_NAMES entries must be bare (no `svp_` prefix) (Bug S3-121)."""

    def test_command_names_no_svp_prefix(self):
        """No entry in COMMAND_NAMES may start with 'svp_'.

        Claude Code prepends the plugin namespace to the filename stem; a
        leading 'svp_' would register as '/svp:svp_<name>' (double-prefix).
        """
        offenders = [n for n in COMMAND_NAMES if n.startswith("svp_")]
        assert not offenders, (
            f"COMMAND_NAMES entries must not start with 'svp_' "
            f"(Bug S3-121 double-prefix regression): {offenders}"
        )

    def test_command_names_no_svp_dash_prefix(self):
        """No entry in COMMAND_NAMES may start with 'svp-' either.

        Symmetric with the 'svp_' guard: a hyphenated double-prefix
        ('/svp:svp-bug') is just as broken.
        """
        offenders = [n for n in COMMAND_NAMES if n.startswith("svp-")]
        assert not offenders, (
            f"COMMAND_NAMES entries must not start with 'svp-' "
            f"(Bug S3-121 double-prefix regression, hyphenated form): {offenders}"
        )

    def test_command_names_match_bare_regex(self):
        """Every entry in COMMAND_NAMES matches ^[a-z][a-z_-]*$ (lowercase, underscore, hyphen — no uppercase, no digits, no leading punctuation)."""
        pattern = re.compile(r"^[a-z][a-z_-]*$")
        offenders = [n for n in COMMAND_NAMES if not pattern.match(n)]
        assert not offenders, (
            f"COMMAND_NAMES entries must match ^[a-z][a-z_-]*$ "
            f"(bare lowercase/underscore/hyphen form): {offenders}"
        )


class TestCommandDefinitionsKeysBareForm:
    """COMMAND_DEFINITIONS dict keys must mirror COMMAND_NAMES (Bug S3-121)."""

    def test_command_definitions_keys_no_svp_prefix(self):
        """No COMMAND_DEFINITIONS key may start with 'svp_' or 'svp-'."""
        offenders = [
            k for k in COMMAND_DEFINITIONS if k.startswith(("svp_", "svp-"))
        ]
        assert not offenders, (
            f"COMMAND_DEFINITIONS keys must not start with 'svp_' or 'svp-' "
            f"(Bug S3-121 double-prefix regression): {offenders}"
        )

    def test_command_definitions_keys_match_bare_regex(self):
        """Every COMMAND_DEFINITIONS key matches ^[a-z][a-z_-]*$."""
        pattern = re.compile(r"^[a-z][a-z_-]*$")
        offenders = [k for k in COMMAND_DEFINITIONS if not pattern.match(k)]
        assert not offenders, (
            f"COMMAND_DEFINITIONS keys must match ^[a-z][a-z_-]*$ "
            f"(bare lowercase/underscore/hyphen form): {offenders}"
        )


class TestCommandBodyHeadingMatchesFilename:
    """Each command body must open with '# /svp:<cmd_name>' heading (Bug S3-121).

    This is the drift detector: if the dict key is renamed but the body
    heading is left as '# /svp:svp_<name>', the deployed command file
    contents would be self-inconsistent (filename bare, heading prefixed).
    """

    def test_body_heading_matches_filename_stem(self):
        """For every (cmd_name, content), content must start with '# /svp:{cmd_name}\\n'."""
        mismatches = []
        for cmd_name, content in COMMAND_DEFINITIONS.items():
            expected_heading = f"# /svp:{cmd_name}\n"
            if not content.startswith(expected_heading):
                first_line = content.split("\n", 1)[0] if content else "<empty>"
                mismatches.append(
                    f"  {cmd_name!r}: expected opening {expected_heading!r}, "
                    f"got {first_line!r}"
                )
        assert not mismatches, (
            "Command body headings must match their filename stems "
            "(Bug S3-121 drift guard):\n" + "\n".join(mismatches)
        )


class TestCommandNamesAndDefinitionsConsistency:
    """COMMAND_NAMES and COMMAND_DEFINITIONS must agree as sets (Bug S3-121)."""

    def test_command_names_list_matches_definitions_keys(self):
        """set(COMMAND_NAMES) must equal set(COMMAND_DEFINITIONS.keys())."""
        assert set(COMMAND_NAMES) == set(COMMAND_DEFINITIONS.keys()), (
            f"COMMAND_NAMES and COMMAND_DEFINITIONS keys must agree as sets. "
            f"Only in COMMAND_NAMES: {set(COMMAND_NAMES) - set(COMMAND_DEFINITIONS)}. "
            f"Only in COMMAND_DEFINITIONS: "
            f"{set(COMMAND_DEFINITIONS) - set(COMMAND_NAMES)}."
        )

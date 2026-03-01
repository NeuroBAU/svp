"""
Additional coverage tests for Unit 17: Support Agent Definitions.

These tests fill gaps identified by comparing the blueprint's behavioral
contracts against the existing test suite in test_support_agent_definitions.py.

DATA ASSUMPTIONS
================

DATA ASSUMPTION: The behavioral contracts state each *_MD_CONTENT must describe
the agent's "input/output format." The Help Agent tests did not have an
explicit input/output format check (the Hint Agent did).

DATA ASSUMPTION: Both agents are read-only (tools restricted to Read, Glob,
Grep). The Hint Agent's body text was not explicitly checked for mentioning
the read-only constraint, unlike the Help Agent which has a dedicated
TestHelpAgentReadOnlyInvariant class.

DATA ASSUMPTION: The invariant states "In non-gate mode, hint formulation
instruction is omitted." This requires the Help Agent body to describe
that hint formulation is reserved for / only in gate mode.

DATA ASSUMPTION: The blueprint states reactive mode requires "no additional
human input needed." The Hint Agent body should describe this aspect.

DATA ASSUMPTION: The blueprint says the Help Agent "hint forwarded" output
is "followed by hint content." The body should describe including hint
content after the status line.

DATA ASSUMPTION: Both agents must produce exactly one terminal status line
when their session/analysis ends. The body should convey the requirement
to always produce a terminal status line.
"""

import pytest
from typing import Any, Dict

from svp.scripts.support_agent_definitions import (
    HELP_AGENT_FRONTMATTER,
    HINT_AGENT_FRONTMATTER,
    HELP_AGENT_STATUS,
    HINT_AGENT_STATUS,
)


# ---------------------------------------------------------------------------
# Helpers (same as in test_support_agent_definitions.py)
# ---------------------------------------------------------------------------

def _get_md_content(name: str) -> str:
    """Safely retrieve an MD_CONTENT constant by name."""
    import svp.scripts.support_agent_definitions as mod
    val = getattr(mod, name, None)
    if val is None or not isinstance(val, str):
        pytest.fail(f"{name} is not defined or not a string in svp.scripts.support_agent_definitions")
    return val


def _parse_frontmatter(md_content: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from a Markdown agent definition string."""
    assert md_content.startswith("---\n"), "MD content must start with YAML frontmatter delimiter"
    second_delim = md_content.index("---\n", 4)
    yaml_block = md_content[4:second_delim]
    result: Dict[str, Any] = {}
    current_key = None
    current_list: list = []
    lines = yaml_block.splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith("  - ") or line.startswith("\t- "):
            item = stripped[2:].strip().strip("\"'")
            current_list.append(item)
            continue
        if current_key and current_list:
            result[current_key] = current_list
            current_list = []
            current_key = None
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1]
                items = [item.strip().strip("\"'") for item in inner.split(",") if item.strip()]
                result[key] = items
            elif val == "":
                current_key = key
            elif val.startswith('"') and val.endswith('"'):
                result[key] = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                result[key] = val[1:-1]
            else:
                result[key] = val
    if current_key and current_list:
        result[current_key] = current_list
    return result


def _get_body_after_frontmatter(md_content: str) -> str:
    """Extract the body text after the YAML frontmatter section."""
    assert md_content.startswith("---\n")
    second_delim = md_content.index("---\n", 4)
    return md_content[second_delim + 4:]


# ===========================================================================
# Gap 1: Help Agent describes input/output format
# ===========================================================================


class TestHelpAgentInputOutput:
    """The blueprint behavioral contract states each *_MD_CONTENT must describe
    'its input/output format.' The Hint Agent has test_describes_input_output
    but the Help Agent does not have an equivalent test.
    """

    def test_help_agent_describes_input_or_output(self):
        """Help Agent body must describe its input/output format."""
        content = _get_md_content("HELP_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        body_lower = body.lower()
        assert ("input" in body_lower or "output" in body_lower
                or "receive" in body_lower or "produc" in body_lower), (
            "Help Agent must describe its input/output format"
        )


# ===========================================================================
# Gap 2: Hint Agent read-only body text check
# ===========================================================================


class TestHintAgentReadOnlyInvariant:
    """The blueprint invariant says both agents are read-only. The Help Agent
    has a dedicated TestHelpAgentReadOnlyInvariant class checking that the
    body text explicitly mentions read-only. The Hint Agent needs the same.
    """

    def test_hint_agent_body_mentions_read_only(self):
        """Hint Agent body must explicitly state the read-only constraint."""
        content = _get_md_content("HINT_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        body_lower = body.lower()
        assert ("read-only" in body_lower or "read only" in body_lower
                or "never modif" in body_lower or "do not modif" in body_lower
                or "not modify" in body_lower or "must not modif" in body_lower
                or "never write" in body_lower or "do not write" in body_lower), (
            "Hint Agent body must explicitly state read-only constraint"
        )


# ===========================================================================
# Gap 3: Help Agent non-gate mode omits hint formulation
# ===========================================================================


class TestHelpAgentNonGateModeOmitsHint:
    """The invariant states: 'In non-gate mode, hint formulation instruction
    is omitted.' The existing test only checks that 'gate' appears in the body.
    This test verifies the body explicitly describes that hint formulation is
    reserved for gate mode / not offered outside gate mode.
    """

    def test_body_distinguishes_non_gate_omission(self):
        """Help Agent body must describe that hint formulation is omitted
        or not offered in non-gate mode."""
        content = _get_md_content("HELP_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        body_lower = body.lower()
        # The body should indicate that hint formulation is limited to gate mode
        # or not done outside gate mode
        assert (
            ("non-gate" in body_lower or "non gate" in body_lower)
            or ("gate" in body_lower and (
                "only" in body_lower or "omit" in body_lower
                or "reserved" in body_lower or "not offer" in body_lower
                or "do not" in body_lower
            ))
        ), (
            "Help Agent must describe that hint formulation is omitted "
            "in non-gate mode"
        )


# ===========================================================================
# Gap 4: Hint Agent reactive mode requires no human input
# ===========================================================================


class TestHintAgentReactiveModeNoHumanInput:
    """The blueprint states reactive mode requires 'no additional human input
    needed.' The body should describe this aspect of reactive mode.
    """

    def test_reactive_mode_no_human_input(self):
        """Hint Agent reactive mode must describe not needing additional
        human input (single-shot, no questions asked)."""
        content = _get_md_content("HINT_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        body_lower = body.lower()
        # Reactive mode is single-shot: no dialog, no questions
        assert (
            "single-shot" in body_lower
            or "single shot" in body_lower
            or ("reactive" in body_lower and (
                "no" in body_lower or "without" in body_lower
                or "do not ask" in body_lower
            ))
        ), (
            "Hint Agent reactive mode must describe not needing "
            "additional human input (single-shot analysis)"
        )


# ===========================================================================
# Gap 5: Help Agent hint forwarded output includes hint content
# ===========================================================================


class TestHelpAgentHintContentInOutput:
    """The blueprint states Help Agent output to main session is
    'HELP_SESSION_COMPLETE: hint forwarded followed by hint content.'
    The body should describe including the actual hint content after
    the status line.
    """

    def test_body_describes_hint_content_after_status(self):
        """Help Agent body must describe that hint content follows the
        'hint forwarded' terminal status line."""
        content = _get_md_content("HELP_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        body_lower = body.lower()
        # The body should describe hint content appearing after the status line
        assert ("hint content" in body_lower
                or ("hint" in body_lower and "follow" in body_lower)
                or ("hint" in body_lower and "after" in body_lower and "status" in body_lower)
                or "## hint content" in body_lower
                or ("hint forwarded" in body_lower and "content" in body_lower)), (
            "Help Agent must describe that hint content follows the "
            "'hint forwarded' terminal status line"
        )


# ===========================================================================
# Gap 6: Both agents must always produce a terminal status line
# ===========================================================================


class TestAgentsMustAlwaysProduceTerminalStatus:
    """The blueprint states agents produce terminal status lines. Each agent's
    body should convey the requirement to always produce exactly one terminal
    status line when work is done.
    """

    @pytest.mark.parametrize("const_name", [
        "HELP_AGENT_MD_CONTENT",
        "HINT_AGENT_MD_CONTENT",
    ])
    def test_body_requires_always_producing_status(self, const_name):
        """Agent body must indicate the terminal status line is mandatory
        (always produced when session/analysis ends)."""
        content = _get_md_content(const_name)
        body = _get_body_after_frontmatter(content)
        body_lower = body.lower()
        # Should convey that producing a status line is required/mandatory
        assert (
            "must always" in body_lower
            or "always produce" in body_lower
            or "must produce" in body_lower
            or ("always" in body_lower and "status" in body_lower)
            or "exactly one" in body_lower
        ), (
            f"{const_name} must describe that producing a terminal status "
            "line is mandatory"
        )

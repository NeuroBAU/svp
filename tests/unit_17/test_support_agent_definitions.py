"""
Tests for Unit 17: Support Agent Definitions.

Validates the YAML frontmatter dictionaries, terminal status line lists,
and the two *_MD_CONTENT agent definition strings for the Help Agent and
Hint Agent.

DATA ASSUMPTIONS
================

DATA ASSUMPTION: YAML frontmatter in each *_MD_CONTENT string uses the
standard "---" delimiter on separate lines, with key: value pairs between
them. This is the Claude Code agent definition format.

DATA ASSUMPTION: The frontmatter dictionaries defined in Tier 2 signatures
exactly match the keys/values specified in the blueprint. These are the
canonical agent metadata attributes.

DATA ASSUMPTION: Help Agent uses claude-sonnet-4-6 and is restricted to
read-only tools: Read, Glob, Grep. It never modifies documents, code,
tests, or pipeline state. It also has access to web search via MCP, but
that is not listed in the tools frontmatter.

DATA ASSUMPTION: Hint Agent uses claude-opus-4-6 and is restricted to
Read, Glob, Grep tools.

DATA ASSUMPTION: Help Agent operates in two modes: gate-invocation mode
(proactively offers hint formulation) and non-gate mode (hint formulation
instruction omitted). Conversation ledger is cleared on dismissal.

DATA ASSUMPTION: Hint Agent operates in reactive mode (reads logs,
identifies patterns, no human input needed) or proactive mode (asks
human questions). Offers CONTINUE or RESTART options.

DATA ASSUMPTION: "Substantial behavioral instructions" means >100 characters
after the second YAML frontmatter delimiter, per the Tier 2 invariant.

DATA ASSUMPTION: Terminal status lines are exact string matches used by the
main session routing script. No variations or prefixes are allowed.

DATA ASSUMPTION: Help Agent status lines include the colon-space separator:
"HELP_SESSION_COMPLETE: no hint" and "HELP_SESSION_COMPLETE: hint forwarded".

DATA ASSUMPTION: Hint Agent has a single terminal status line:
"HINT_ANALYSIS_COMPLETE".
"""

import re
from typing import Any, Dict, List

import pytest

# Import the unit under test -- frontmatter dicts and status lists have
# concrete values in the stub, so they can be imported directly.
from svp.scripts.support_agent_definitions import (
    HELP_AGENT_FRONTMATTER,
    HINT_AGENT_FRONTMATTER,
    HELP_AGENT_STATUS,
    HINT_AGENT_STATUS,
)


# ---------------------------------------------------------------------------
# Helper: safely import *_MD_CONTENT constants that are type-only in the stub
# ---------------------------------------------------------------------------

def _get_md_content(name: str) -> str:
    """Safely retrieve an MD_CONTENT constant by name.

    The stub declares these as type annotations without values, so
    direct import will fail on the stub (red run) and succeed on
    the implementation (green run).
    """
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
# Section 1: Frontmatter Dictionary Constants
# ===========================================================================


class TestHelpAgentFrontmatter:
    """Verify the HELP_AGENT_FRONTMATTER dict matches the blueprint."""

    def test_is_dict(self):
        assert isinstance(HELP_AGENT_FRONTMATTER, dict)

    def test_name(self):
        assert HELP_AGENT_FRONTMATTER["name"] == "help_agent"

    def test_description(self):
        assert HELP_AGENT_FRONTMATTER["description"] == (
            "Answers questions, collaborates on hint formulation at gates"
        )

    def test_model(self):
        # DATA ASSUMPTION: Help Agent uses claude-sonnet-4-6 per blueprint
        assert HELP_AGENT_FRONTMATTER["model"] == "claude-sonnet-4-6"

    def test_tools(self):
        # DATA ASSUMPTION: Help Agent is READ-ONLY: tools restricted to
        # Read, Glob, Grep (web search via MCP is not in frontmatter)
        assert HELP_AGENT_FRONTMATTER["tools"] == ["Read", "Glob", "Grep"]

    def test_has_required_keys(self):
        """Frontmatter must have name, description, model, tools."""
        required = {"name", "description", "model", "tools"}
        missing = required - set(HELP_AGENT_FRONTMATTER.keys())
        assert not missing, f"HELP_AGENT_FRONTMATTER missing keys: {missing}"


class TestHintAgentFrontmatter:
    """Verify the HINT_AGENT_FRONTMATTER dict matches the blueprint."""

    def test_is_dict(self):
        assert isinstance(HINT_AGENT_FRONTMATTER, dict)

    def test_name(self):
        assert HINT_AGENT_FRONTMATTER["name"] == "hint_agent"

    def test_description(self):
        assert HINT_AGENT_FRONTMATTER["description"] == (
            "Provides diagnostic analysis of pipeline state"
        )

    def test_model(self):
        # DATA ASSUMPTION: Hint Agent uses claude-opus-4-6 per blueprint
        assert HINT_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_tools(self):
        # DATA ASSUMPTION: Hint Agent uses Read, Glob, Grep
        assert HINT_AGENT_FRONTMATTER["tools"] == ["Read", "Glob", "Grep"]

    def test_has_required_keys(self):
        """Frontmatter must have name, description, model, tools."""
        required = {"name", "description", "model", "tools"}
        missing = required - set(HINT_AGENT_FRONTMATTER.keys())
        assert not missing, f"HINT_AGENT_FRONTMATTER missing keys: {missing}"


class TestFrontmatterCrossCutting:
    """Cross-cutting checks for both frontmatter dicts."""

    def test_different_models(self):
        """Help Agent uses sonnet, Hint Agent uses opus."""
        assert HELP_AGENT_FRONTMATTER["model"] != HINT_AGENT_FRONTMATTER["model"]
        assert HELP_AGENT_FRONTMATTER["model"] == "claude-sonnet-4-6"
        assert HINT_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_both_read_only_tools(self):
        """Both agents are restricted to read-only tools (Read, Glob, Grep).
        Neither should have Write, Edit, or Bash."""
        for label, fm in [
            ("HELP_AGENT", HELP_AGENT_FRONTMATTER),
            ("HINT_AGENT", HINT_AGENT_FRONTMATTER),
        ]:
            tools = fm["tools"]
            assert "Write" not in tools, f"{label} must not have Write tool"
            assert "Edit" not in tools, f"{label} must not have Edit tool"
            assert "Bash" not in tools, f"{label} must not have Bash tool"

    def test_different_names(self):
        """Each agent has a distinct name."""
        assert HELP_AGENT_FRONTMATTER["name"] != HINT_AGENT_FRONTMATTER["name"]


# ===========================================================================
# Section 2: Terminal Status Line Constants
# ===========================================================================


class TestHelpAgentStatusLines:
    """Verify HELP_AGENT_STATUS list matches the blueprint."""

    def test_is_list(self):
        assert isinstance(HELP_AGENT_STATUS, list)

    def test_values(self):
        assert HELP_AGENT_STATUS == [
            "HELP_SESSION_COMPLETE: no hint",
            "HELP_SESSION_COMPLETE: hint forwarded",
        ]

    def test_length(self):
        assert len(HELP_AGENT_STATUS) == 2

    def test_no_hint_status(self):
        """The 'no hint' status must be present."""
        assert "HELP_SESSION_COMPLETE: no hint" in HELP_AGENT_STATUS

    def test_hint_forwarded_status(self):
        """The 'hint forwarded' status must be present."""
        assert "HELP_SESSION_COMPLETE: hint forwarded" in HELP_AGENT_STATUS


class TestHintAgentStatusLines:
    """Verify HINT_AGENT_STATUS list matches the blueprint."""

    def test_is_list(self):
        assert isinstance(HINT_AGENT_STATUS, list)

    def test_values(self):
        assert HINT_AGENT_STATUS == ["HINT_ANALYSIS_COMPLETE"]

    def test_length(self):
        assert len(HINT_AGENT_STATUS) == 1


# ===========================================================================
# Section 3: MD_CONTENT String Existence and Type
# ===========================================================================


class TestMdContentExistence:
    """Verify that *_MD_CONTENT constants exist and are non-empty strings.

    These tests will fail on the stub (red run) because the stub only
    declares type annotations without assigning values.
    """

    def test_help_agent_md_content_is_string(self):
        content = _get_md_content("HELP_AGENT_MD_CONTENT")
        assert isinstance(content, str)
        assert len(content) > 0, "HELP_AGENT_MD_CONTENT must not be empty"

    def test_hint_agent_md_content_is_string(self):
        content = _get_md_content("HINT_AGENT_MD_CONTENT")
        assert isinstance(content, str)
        assert len(content) > 0, "HINT_AGENT_MD_CONTENT must not be empty"


# ===========================================================================
# Section 4: YAML Frontmatter Structure Invariants
# ===========================================================================


class TestYamlFrontmatterInvariants:
    """Verify every *_MD_CONTENT string starts with valid YAML frontmatter.

    Invariant: Starts with '---\\n', contains 'name:', 'model:', 'tools:',
    and has a second '---\\n' to close the frontmatter.
    """

    @pytest.mark.parametrize("const_name", [
        "HELP_AGENT_MD_CONTENT",
        "HINT_AGENT_MD_CONTENT",
    ])
    def test_starts_with_yaml_delimiter(self, const_name):
        content = _get_md_content(const_name)
        assert content.startswith("---\n"), (
            f"{const_name} must start with '---\\n'"
        )

    @pytest.mark.parametrize("const_name", [
        "HELP_AGENT_MD_CONTENT",
        "HINT_AGENT_MD_CONTENT",
    ])
    def test_has_closing_yaml_delimiter(self, const_name):
        content = _get_md_content(const_name)
        # There must be a second "---\n" after the opening one
        idx = content.index("---\n", 4)
        assert idx > 4, (
            f"{const_name} must have a closing '---\\n' frontmatter delimiter"
        )

    @pytest.mark.parametrize("const_name", [
        "HELP_AGENT_MD_CONTENT",
        "HINT_AGENT_MD_CONTENT",
    ])
    def test_frontmatter_contains_name(self, const_name):
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert "name" in fm, f"{const_name} frontmatter must contain 'name:'"

    @pytest.mark.parametrize("const_name", [
        "HELP_AGENT_MD_CONTENT",
        "HINT_AGENT_MD_CONTENT",
    ])
    def test_frontmatter_contains_model(self, const_name):
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert "model" in fm, f"{const_name} frontmatter must contain 'model:'"

    @pytest.mark.parametrize("const_name", [
        "HELP_AGENT_MD_CONTENT",
        "HINT_AGENT_MD_CONTENT",
    ])
    def test_frontmatter_contains_tools(self, const_name):
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert "tools" in fm, f"{const_name} frontmatter must contain 'tools:'"

    @pytest.mark.parametrize("const_name", [
        "HELP_AGENT_MD_CONTENT",
        "HINT_AGENT_MD_CONTENT",
    ])
    def test_body_after_frontmatter_is_substantial(self, const_name):
        """Invariant: >100 chars of behavioral instructions after frontmatter."""
        content = _get_md_content(const_name)
        body = _get_body_after_frontmatter(content)
        assert len(body.strip()) > 100, (
            f"{const_name} must have >100 chars of instructions after "
            f"frontmatter, got {len(body.strip())}"
        )


# ===========================================================================
# Section 5: Frontmatter Values Match Constants
# ===========================================================================


class TestFrontmatterMatchesConstants:
    """Verify the YAML frontmatter in each *_MD_CONTENT matches its
    corresponding *_FRONTMATTER dict.
    """

    def test_help_agent_frontmatter_name_matches(self):
        content = _get_md_content("HELP_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["name"] == HELP_AGENT_FRONTMATTER["name"]

    def test_help_agent_frontmatter_model_matches(self):
        content = _get_md_content("HELP_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["model"] == HELP_AGENT_FRONTMATTER["model"]

    def test_help_agent_frontmatter_tools_matches(self):
        content = _get_md_content("HELP_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["tools"] == HELP_AGENT_FRONTMATTER["tools"]

    def test_hint_agent_frontmatter_name_matches(self):
        content = _get_md_content("HINT_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["name"] == HINT_AGENT_FRONTMATTER["name"]

    def test_hint_agent_frontmatter_model_matches(self):
        content = _get_md_content("HINT_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["model"] == HINT_AGENT_FRONTMATTER["model"]

    def test_hint_agent_frontmatter_tools_matches(self):
        content = _get_md_content("HINT_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["tools"] == HINT_AGENT_FRONTMATTER["tools"]

    def test_help_agent_frontmatter_description_matches(self):
        """The description in the MD frontmatter should match the constant."""
        content = _get_md_content("HELP_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm.get("description") == HELP_AGENT_FRONTMATTER["description"]

    def test_hint_agent_frontmatter_description_matches(self):
        """The description in the MD frontmatter should match the constant."""
        content = _get_md_content("HINT_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm.get("description") == HINT_AGENT_FRONTMATTER["description"]


# ===========================================================================
# Section 6: Behavioral Contracts -- Help Agent
# ===========================================================================


class TestHelpAgentBehavioralContracts:
    """Verify Help Agent MD content describes the required behaviors.

    Behavioral contracts from the blueprint:
    - Read-only. Tools restricted to Read, Glob, Grep, and web search.
    - Receives project summary, stakeholder spec, blueprint.
    - In gate-invocation mode: receives gate flag and proactively offers
      hint formulation when conversation produces an actionable observation.
    - The human approves hint text explicitly.
    - Output: HELP_SESSION_COMPLETE: no hint / HELP_SESSION_COMPLETE: hint forwarded
    - Conversation ledger cleared on dismissal.
    - Uses claude-sonnet-4-6.
    """

    @pytest.fixture
    def content(self):
        return _get_md_content("HELP_AGENT_MD_CONTENT")

    @pytest.fixture
    def body(self, content):
        return _get_body_after_frontmatter(content)

    def test_describes_read_only_constraint(self, body):
        """Help Agent is read-only: never modifies documents, code, tests,
        or pipeline state."""
        body_lower = body.lower()
        assert ("read-only" in body_lower or "read only" in body_lower
                or "never modif" in body_lower or "do not modif" in body_lower
                or "not modify" in body_lower or "must not modif" in body_lower
                or "shall not modif" in body_lower), (
            "Help Agent must describe its read-only constraint"
        )

    def test_describes_purpose(self, body):
        """Help Agent must describe its purpose: answering questions and
        collaborating on hint formulation at gates."""
        body_lower = body.lower()
        assert ("question" in body_lower or "answer" in body_lower
                or "help" in body_lower), (
            "Help Agent must describe answering questions"
        )

    def test_describes_hint_formulation(self, body):
        """Help Agent collaborates on hint formulation."""
        body_lower = body.lower()
        assert "hint" in body_lower, (
            "Help Agent must mention hint formulation"
        )

    def test_describes_gate_invocation_mode(self, body):
        """In gate-invocation mode, Help Agent proactively offers hint
        formulation."""
        body_lower = body.lower()
        assert "gate" in body_lower, (
            "Help Agent must describe gate-invocation mode"
        )

    def test_describes_proactive_hint_offer(self, body):
        """In gate mode, Help Agent proactively offers hint formulation
        when conversation produces an actionable observation."""
        body_lower = body.lower()
        assert ("proactive" in body_lower or "offer" in body_lower
                or "actionable" in body_lower), (
            "Help Agent must describe proactive hint formulation offering"
        )

    def test_describes_human_approves_hint(self, body):
        """The human approves hint text explicitly."""
        body_lower = body.lower()
        assert ("approv" in body_lower or "confirm" in body_lower
                or "explicit" in body_lower), (
            "Help Agent must describe human approval of hint text"
        )

    def test_terminal_status_no_hint(self, body):
        """Help Agent must mention HELP_SESSION_COMPLETE: no hint."""
        assert "HELP_SESSION_COMPLETE" in body, (
            "Help Agent must mention HELP_SESSION_COMPLETE status"
        )
        assert "no hint" in body, (
            "Help Agent must mention 'no hint' variant"
        )

    def test_terminal_status_hint_forwarded(self, body):
        """Help Agent must mention HELP_SESSION_COMPLETE: hint forwarded."""
        assert "hint forwarded" in body, (
            "Help Agent must mention 'hint forwarded' variant"
        )

    def test_describes_ledger_clearing(self, body):
        """Conversation ledger is cleared on dismissal."""
        body_lower = body.lower()
        assert ("clear" in body_lower and ("ledger" in body_lower
                or "dismiss" in body_lower or "session" in body_lower)), (
            "Help Agent must describe ledger clearing on dismissal"
        )

    def test_uses_sonnet_model(self, content):
        """Help Agent uses claude-sonnet-4-6."""
        fm = _parse_frontmatter(content)
        assert fm["model"] == "claude-sonnet-4-6"

    def test_tools_are_read_only(self, content):
        """Help Agent tools must be read-only: Read, Glob, Grep only."""
        fm = _parse_frontmatter(content)
        tools = fm["tools"]
        assert "Read" in tools
        assert "Glob" in tools
        assert "Grep" in tools
        assert "Write" not in tools
        assert "Edit" not in tools
        assert "Bash" not in tools

    def test_describes_receives_context(self, body):
        """Help Agent receives project summary, stakeholder spec, blueprint."""
        body_lower = body.lower()
        # Should mention at least some of: project, spec, blueprint
        has_project = "project" in body_lower
        has_spec = "spec" in body_lower or "stakeholder" in body_lower
        has_blueprint = "blueprint" in body_lower
        assert has_project or has_spec or has_blueprint, (
            "Help Agent must describe what context it receives "
            "(project summary, stakeholder spec, blueprint)"
        )

    def test_describes_non_gate_mode_difference(self, body):
        """In non-gate mode, hint formulation instruction is omitted.
        The agent must describe the distinction between gate and non-gate modes."""
        body_lower = body.lower()
        # The agent should acknowledge the gate/non-gate distinction
        assert "gate" in body_lower, (
            "Help Agent must describe gate vs non-gate mode"
        )

    def test_describes_methodology(self, body):
        """Help Agent must describe its methodology."""
        body_lower = body.lower()
        # Should have sections about how it works
        assert ("method" in body_lower or "approach" in body_lower
                or "process" in body_lower or "step" in body_lower
                or "how" in body_lower or "procedure" in body_lower
                or "##" in body), (
            "Help Agent must describe its methodology"
        )

    def test_describes_constraints(self, body):
        """Help Agent must describe its constraints."""
        body_lower = body.lower()
        assert ("constraint" in body_lower or "must not" in body_lower
                or "do not" in body_lower or "never" in body_lower
                or "restrict" in body_lower), (
            "Help Agent must describe its constraints"
        )


# ===========================================================================
# Section 7: Behavioral Contracts -- Hint Agent
# ===========================================================================


class TestHintAgentBehavioralContracts:
    """Verify Hint Agent MD content describes the required behaviors.

    Behavioral contracts from the blueprint:
    - Operates in reactive mode (reads accumulated logs, identifies patterns,
      no additional human input needed) or proactive mode (asks human what
      prompted their concern, which document they suspect).
    - Produces diagnostic analysis.
    - Offers explicit options: CONTINUE or RESTART.
    - Terminal status: HINT_ANALYSIS_COMPLETE.
    - Uses claude-opus-4-6.
    """

    @pytest.fixture
    def content(self):
        return _get_md_content("HINT_AGENT_MD_CONTENT")

    @pytest.fixture
    def body(self, content):
        return _get_body_after_frontmatter(content)

    def test_describes_reactive_mode(self, body):
        """Hint Agent operates in reactive mode: reads accumulated logs,
        identifies patterns."""
        body_lower = body.lower()
        assert ("reactive" in body_lower or "log" in body_lower
                or "pattern" in body_lower), (
            "Hint Agent must describe reactive mode "
            "(reading logs, identifying patterns)"
        )

    def test_describes_proactive_mode(self, body):
        """Hint Agent operates in proactive mode: asks human what prompted
        their concern."""
        body_lower = body.lower()
        assert ("proactive" in body_lower or "concern" in body_lower
                or "ask" in body_lower), (
            "Hint Agent must describe proactive mode "
            "(asking human about their concern)"
        )

    def test_describes_diagnostic_analysis(self, body):
        """Hint Agent produces diagnostic analysis."""
        body_lower = body.lower()
        assert ("diagnos" in body_lower or "analysis" in body_lower
                or "analyz" in body_lower), (
            "Hint Agent must describe diagnostic analysis"
        )

    def test_describes_continue_option(self, body):
        """Hint Agent offers CONTINUE option."""
        assert "CONTINUE" in body, (
            "Hint Agent must mention CONTINUE option"
        )

    def test_describes_restart_option(self, body):
        """Hint Agent offers RESTART option."""
        assert "RESTART" in body, (
            "Hint Agent must mention RESTART option"
        )

    def test_terminal_status_hint_analysis_complete(self, body):
        """Hint Agent must mention HINT_ANALYSIS_COMPLETE terminal status."""
        assert "HINT_ANALYSIS_COMPLETE" in body

    def test_uses_opus_model(self, content):
        """Hint Agent uses claude-opus-4-6."""
        fm = _parse_frontmatter(content)
        assert fm["model"] == "claude-opus-4-6"

    def test_tools_are_read_only(self, content):
        """Hint Agent tools must be read-only: Read, Glob, Grep only."""
        fm = _parse_frontmatter(content)
        tools = fm["tools"]
        assert "Read" in tools
        assert "Glob" in tools
        assert "Grep" in tools
        assert "Write" not in tools
        assert "Edit" not in tools
        assert "Bash" not in tools

    def test_describes_purpose(self, body):
        """Hint Agent must describe its purpose: diagnostic analysis of
        pipeline state."""
        body_lower = body.lower()
        assert ("diagnos" in body_lower or "pipeline" in body_lower
                or "analysis" in body_lower), (
            "Hint Agent must describe its purpose"
        )

    def test_describes_methodology(self, body):
        """Hint Agent must describe its methodology."""
        body_lower = body.lower()
        assert ("method" in body_lower or "approach" in body_lower
                or "process" in body_lower or "step" in body_lower
                or "how" in body_lower or "procedure" in body_lower
                or "##" in body), (
            "Hint Agent must describe its methodology"
        )

    def test_describes_constraints(self, body):
        """Hint Agent must describe its constraints."""
        body_lower = body.lower()
        assert ("constraint" in body_lower or "must not" in body_lower
                or "do not" in body_lower or "never" in body_lower
                or "restrict" in body_lower), (
            "Hint Agent must describe its constraints"
        )

    def test_describes_input_output(self, body):
        """Hint Agent must describe its input/output format."""
        body_lower = body.lower()
        assert ("input" in body_lower or "output" in body_lower
                or "receive" in body_lower or "produc" in body_lower), (
            "Hint Agent must describe its input/output format"
        )


# ===========================================================================
# Section 8: Cross-Cutting Behavioral Contracts (Both Agents)
# ===========================================================================


class TestAllAgentsCommonContracts:
    """Verify behavioral contracts that apply to both agents."""

    @pytest.mark.parametrize("const_name,status_list", [
        ("HELP_AGENT_MD_CONTENT", HELP_AGENT_STATUS),
        ("HINT_AGENT_MD_CONTENT", HINT_AGENT_STATUS),
    ])
    def test_all_terminal_status_lines_mentioned(self, const_name, status_list):
        """Each agent's body must mention all its terminal status lines."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        for status in status_list:
            # For multi-word status lines like "HELP_SESSION_COMPLETE: no hint",
            # check the key identifier is present
            key_part = status.split(":")[0].strip()
            assert key_part in body, (
                f"{const_name} must mention terminal status line '{status}' "
                f"(at minimum '{key_part}')"
            )

    @pytest.mark.parametrize("const_name", [
        "HELP_AGENT_MD_CONTENT",
        "HINT_AGENT_MD_CONTENT",
    ])
    def test_describes_terminal_status_line_concept(self, const_name):
        """Both agents must describe their terminal status line mechanism."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        body_lower = body.lower()
        assert ("terminal status" in body_lower or "status line" in body_lower
                or "terminal line" in body_lower), (
            f"{const_name} must describe the terminal status line concept"
        )

    @pytest.mark.parametrize("const_name", [
        "HELP_AGENT_MD_CONTENT",
        "HINT_AGENT_MD_CONTENT",
    ])
    def test_is_valid_yaml_frontmatter(self, const_name):
        """Frontmatter YAML must be parseable without errors."""
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert isinstance(fm, dict), (
            f"{const_name} frontmatter must parse as a dict"
        )

    @pytest.mark.parametrize("const_name", [
        "HELP_AGENT_MD_CONTENT",
        "HINT_AGENT_MD_CONTENT",
    ])
    def test_describes_purpose(self, const_name):
        """Both agents must describe their purpose with substantial text."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        stripped = body.strip()
        assert len(stripped) > 100, (
            f"{const_name} body must be >100 chars (got {len(stripped)})"
        )


# ===========================================================================
# Section 9: Agent Definition Completeness
# ===========================================================================


class TestAgentDefinitionCompleteness:
    """Verify each *_MD_CONTENT is a complete agent definition, not a
    placeholder or skeleton."""

    @pytest.mark.parametrize("const_name", [
        "HELP_AGENT_MD_CONTENT",
        "HINT_AGENT_MD_CONTENT",
    ])
    def test_not_a_placeholder(self, const_name):
        """Content must not be a placeholder -- it should have multiple
        sections of substantive text."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        # DATA ASSUMPTION: A non-skeleton agent definition is at least 500 chars
        assert len(body.strip()) >= 500, (
            f"{const_name} appears to be a skeleton/placeholder "
            f"({len(body.strip())} chars). Expected >= 500 chars of "
            "substantive instructions."
        )

    @pytest.mark.parametrize("const_name", [
        "HELP_AGENT_MD_CONTENT",
        "HINT_AGENT_MD_CONTENT",
    ])
    def test_has_multiple_sections_or_paragraphs(self, const_name):
        """A complete agent definition should have multiple paragraphs."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        non_empty_lines = [
            line for line in body.split("\n") if line.strip()
        ]
        # DATA ASSUMPTION: A complete agent definition has at least 10
        # non-empty lines of instructions
        assert len(non_empty_lines) >= 10, (
            f"{const_name} has only {len(non_empty_lines)} non-empty lines. "
            "Expected >= 10 for a complete agent definition."
        )

    @pytest.mark.parametrize("const_name", [
        "HELP_AGENT_MD_CONTENT",
        "HINT_AGENT_MD_CONTENT",
    ])
    def test_has_markdown_headings(self, const_name):
        """A complete agent definition should use Markdown section headings."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        heading_pattern = re.compile(r"^#+\s+", re.MULTILINE)
        headings = heading_pattern.findall(body)
        # DATA ASSUMPTION: A well-structured agent definition has at least
        # 3 section headings (e.g., Purpose, Methodology, Constraints)
        assert len(headings) >= 3, (
            f"{const_name} has only {len(headings)} Markdown headings. "
            "Expected >= 3 for a well-structured agent definition."
        )


# ===========================================================================
# Section 10: Help Agent Read-Only Invariant
# ===========================================================================


class TestHelpAgentReadOnlyInvariant:
    """The Help Agent is explicitly read-only.

    Invariant: Help Agent never modifies documents, code, tests, or pipeline state.
    This is enforced at the tool level (only Read, Glob, Grep) and must be
    reiterated in the behavioral instructions.
    """

    def test_frontmatter_tools_are_read_only(self):
        """Frontmatter tools must not include any write/modify tools."""
        tools = HELP_AGENT_FRONTMATTER["tools"]
        write_tools = {"Write", "Edit", "Bash"}
        for t in write_tools:
            assert t not in tools, (
                f"Help Agent must not have {t} in its tool list"
            )

    def test_md_content_tools_are_read_only(self):
        """The MD content frontmatter must also restrict to read-only tools."""
        content = _get_md_content("HELP_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        tools = fm["tools"]
        write_tools = {"Write", "Edit", "Bash"}
        for t in write_tools:
            assert t not in tools, (
                f"Help Agent MD content frontmatter must not include {t}"
            )

    def test_body_mentions_read_only(self):
        """The behavioral instructions must explicitly state the read-only
        constraint."""
        content = _get_md_content("HELP_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        body_lower = body.lower()
        assert ("read-only" in body_lower or "read only" in body_lower
                or "never modif" in body_lower or "do not modif" in body_lower
                or "not modify" in body_lower or "must not modif" in body_lower
                or "never write" in body_lower or "do not write" in body_lower), (
            "Help Agent body must explicitly state read-only constraint"
        )


# ===========================================================================
# Section 11: Help Agent Ledger Cleared on Dismissal
# ===========================================================================


class TestHelpAgentLedgerClearing:
    """Invariant: Help agent ledger is cleared on dismissal.

    The agent definition must mention this behavior so the implementation
    can enforce it.
    """

    def test_mentions_ledger(self):
        """Help Agent must reference a conversation ledger."""
        content = _get_md_content("HELP_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        body_lower = body.lower()
        assert "ledger" in body_lower or "conversation" in body_lower, (
            "Help Agent must reference the conversation ledger"
        )

    def test_mentions_clearing_or_dismissal(self):
        """Help Agent must describe ledger clearing on dismissal."""
        content = _get_md_content("HELP_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        body_lower = body.lower()
        assert ("clear" in body_lower or "dismiss" in body_lower
                or "reset" in body_lower), (
            "Help Agent must describe ledger clearing or dismissal behavior"
        )


# ===========================================================================
# Section 12: Help Agent Gate Invocation Mode
# ===========================================================================


class TestHelpAgentGateMode:
    """In gate-invocation mode, Help Agent proactively offers hint
    formulation when conversation produces an actionable observation.

    In non-gate mode, the hint formulation instruction is omitted.
    """

    def test_describes_gate_flag(self):
        """Help Agent must describe receiving a gate flag."""
        content = _get_md_content("HELP_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        body_lower = body.lower()
        assert "gate" in body_lower, (
            "Help Agent must describe gate-invocation mode"
        )

    def test_describes_hint_forwarding_output(self):
        """Help Agent output includes HELP_SESSION_COMPLETE: hint forwarded
        followed by hint content."""
        content = _get_md_content("HELP_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        assert "HELP_SESSION_COMPLETE" in body
        assert "hint forwarded" in body


# ===========================================================================
# Section 13: Hint Agent Modes
# ===========================================================================


class TestHintAgentModes:
    """Hint Agent operates in reactive (single-shot) or proactive
    (ledger multi-turn) mode."""

    def test_describes_two_modes(self):
        """Hint Agent must describe both reactive and proactive modes."""
        content = _get_md_content("HINT_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        body_lower = body.lower()
        assert ("reactive" in body_lower and "proactive" in body_lower) or (
            "mode" in body_lower and (
                ("log" in body_lower or "pattern" in body_lower)
                and ("ask" in body_lower or "concern" in body_lower)
            )
        ), (
            "Hint Agent must describe both reactive and proactive modes"
        )

    def test_reactive_mode_reads_logs(self):
        """Reactive mode reads accumulated logs and identifies patterns."""
        content = _get_md_content("HINT_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        body_lower = body.lower()
        assert ("log" in body_lower or "pattern" in body_lower
                or "accumulate" in body_lower), (
            "Hint Agent reactive mode must describe reading logs/patterns"
        )

    def test_proactive_mode_asks_human(self):
        """Proactive mode asks human about their concern or suspected document."""
        content = _get_md_content("HINT_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        body_lower = body.lower()
        assert ("concern" in body_lower or "suspect" in body_lower
                or "ask" in body_lower or "prompted" in body_lower), (
            "Hint Agent proactive mode must describe asking the human"
        )


# ===========================================================================
# Section 14: Hint Agent Offers CONTINUE or RESTART
# ===========================================================================


class TestHintAgentOptions:
    """Hint Agent offers explicit options: CONTINUE or RESTART."""

    def test_continue_option_present(self):
        content = _get_md_content("HINT_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        assert "CONTINUE" in body, (
            "Hint Agent must offer CONTINUE option"
        )

    def test_restart_option_present(self):
        content = _get_md_content("HINT_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        assert "RESTART" in body, (
            "Hint Agent must offer RESTART option"
        )

    def test_options_described_as_explicit(self):
        """The options must be described as explicit choices for the user."""
        content = _get_md_content("HINT_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        body_lower = body.lower()
        assert ("option" in body_lower or "choice" in body_lower
                or "explicit" in body_lower or "recommend" in body_lower
                or "offer" in body_lower), (
            "Hint Agent must describe CONTINUE/RESTART as explicit options"
        )


# ===========================================================================
# Section 15: Web Search Mention for Help Agent
# ===========================================================================


class TestHelpAgentWebSearch:
    """Help Agent has access to web search via MCP.

    This is mentioned in the behavioral contract but NOT in the tools
    frontmatter (since it is provided by MCP, not the standard tool list).
    The body instructions should reference web search capability.
    """

    def test_body_mentions_web_search_or_mcp(self):
        """Help Agent body should reference web search capability."""
        content = _get_md_content("HELP_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        body_lower = body.lower()
        # The agent may describe web search in various ways
        assert ("web search" in body_lower or "web_search" in body_lower
                or "mcp" in body_lower or "search" in body_lower), (
            "Help Agent must mention web search or MCP capability"
        )

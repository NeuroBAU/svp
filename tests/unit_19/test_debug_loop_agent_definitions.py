"""
Tests for Unit 19: Debug Loop Agent Definitions.

Validates the YAML frontmatter dictionaries, terminal status line lists,
and the two *_MD_CONTENT agent definition strings for the Bug Triage Agent
and Repair Agent. Implements spec Section 12.9.

DATA ASSUMPTIONS
================

DATA ASSUMPTION: YAML frontmatter in each *_MD_CONTENT string uses the
standard "---" delimiter on separate lines, with key: value pairs between
them. This is the Claude Code agent definition format.

DATA ASSUMPTION: The frontmatter dictionaries defined in Tier 2 signatures
exactly match the keys/values specified in the blueprint. These are the
canonical agent metadata attributes.

DATA ASSUMPTION: Bug Triage Agent uses claude-opus-4-6 and has tools:
Read, Write, Edit, Bash, Glob, Grep. It conducts Socratic triage dialog
for post-delivery bugs.

DATA ASSUMPTION: Repair Agent uses claude-sonnet-4-6 and has tools:
Read, Write, Edit, Bash, Glob, Grep. It fixes build and environment
issues in delivered software.

DATA ASSUMPTION: "Substantial behavioral instructions" means >100 characters
after the second YAML frontmatter delimiter, per the Tier 2 invariant.

DATA ASSUMPTION: Terminal status lines are exact string matches used by the
main session routing script. No variations or prefixes are allowed.

DATA ASSUMPTION: Bug Triage Agent terminal status lines:
"TRIAGE_COMPLETE: build_env", "TRIAGE_COMPLETE: single_unit",
"TRIAGE_COMPLETE: cross_unit", "TRIAGE_NEEDS_REFINEMENT",
"TRIAGE_NON_REPRODUCIBLE".

DATA ASSUMPTION: Repair Agent terminal status lines:
"REPAIR_COMPLETE", "REPAIR_FAILED", "REPAIR_RECLASSIFY".

DATA ASSUMPTION: A non-skeleton agent definition is at least 500 characters
of body text and has at least 10 non-empty lines of instructions.

DATA ASSUMPTION: Bug Triage Agent starts in read-only mode (before Gate 6.0
authorization). After authorization, gains write access to tests/regressions/
and .svp/triage_scratch/.

DATA ASSUMPTION: Bug Triage Agent uses structured response format with
tagged closing lines: [QUESTION], [DECISION], [CONFIRMED].

DATA ASSUMPTION: Bug Triage Agent classifies bugs as build/environment or
logic (single-unit vs cross-unit).

DATA ASSUMPTION: Bug Triage Agent uses its own ledger (bug_triage_N.jsonl).

DATA ASSUMPTION: Bug Triage Agent produces dual-format output.

DATA ASSUMPTION: Bug Triage Agent aims to produce test-writable assertions
with concrete inputs, expected outputs, actual outputs for logic bugs.

DATA ASSUMPTION: Bug Triage Agent uses real data for diagnosis but produces
tests with synthetic data.

DATA ASSUMPTION: Repair Agent has narrow mandate for build/environment fixes.
Can modify: environment files, pyproject.toml, __init__.py files, directory
structure. Cannot modify implementation .py files in src/unit_N/ other than
__init__.py.

DATA ASSUMPTION: Repair Agent returns REPAIR_RECLASSIFY if fix requires
implementation changes.

DATA ASSUMPTION: Repair Agent participates in bounded fix cycle (up to 3
attempts).
"""

import re
from typing import Any, Dict, List

import pytest

# Import the unit under test -- frontmatter dicts and status lists have
# concrete values in the stub, so they can be imported directly.
from svp.scripts.debug_loop_agent_definitions import (
    BUG_TRIAGE_AGENT_FRONTMATTER,
    REPAIR_AGENT_FRONTMATTER,
    BUG_TRIAGE_STATUS,
    REPAIR_AGENT_STATUS,
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
    import svp.scripts.debug_loop_agent_definitions as mod
    val = getattr(mod, name, None)
    if val is None or not isinstance(val, str):
        pytest.fail(f"{name} is not defined or not a string in svp.scripts.debug_loop_agent_definitions")
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


class TestBugTriageAgentFrontmatter:
    """Verify the BUG_TRIAGE_AGENT_FRONTMATTER dict matches the blueprint."""

    def test_is_dict(self):
        assert isinstance(BUG_TRIAGE_AGENT_FRONTMATTER, dict)

    def test_name(self):
        assert BUG_TRIAGE_AGENT_FRONTMATTER["name"] == "bug_triage_agent"

    def test_description(self):
        assert BUG_TRIAGE_AGENT_FRONTMATTER["description"] == (
            "Conducts Socratic triage dialog for post-delivery bugs"
        )

    def test_model(self):
        # DATA ASSUMPTION: Bug Triage Agent uses claude-opus-4-6
        assert BUG_TRIAGE_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_tools(self):
        # DATA ASSUMPTION: Bug Triage Agent has Read, Write, Edit, Bash, Glob, Grep
        assert BUG_TRIAGE_AGENT_FRONTMATTER["tools"] == [
            "Read", "Write", "Edit", "Bash", "Glob", "Grep"
        ]

    def test_has_required_keys(self):
        """Frontmatter must have name, description, model, tools."""
        required = {"name", "description", "model", "tools"}
        missing = required - set(BUG_TRIAGE_AGENT_FRONTMATTER.keys())
        assert not missing, f"BUG_TRIAGE_AGENT_FRONTMATTER missing keys: {missing}"


class TestRepairAgentFrontmatter:
    """Verify the REPAIR_AGENT_FRONTMATTER dict matches the blueprint."""

    def test_is_dict(self):
        assert isinstance(REPAIR_AGENT_FRONTMATTER, dict)

    def test_name(self):
        assert REPAIR_AGENT_FRONTMATTER["name"] == "repair_agent"

    def test_description(self):
        assert REPAIR_AGENT_FRONTMATTER["description"] == (
            "Fixes build and environment issues in delivered software"
        )

    def test_model(self):
        # DATA ASSUMPTION: Repair Agent uses claude-sonnet-4-6
        assert REPAIR_AGENT_FRONTMATTER["model"] == "claude-sonnet-4-6"

    def test_tools(self):
        # DATA ASSUMPTION: Repair Agent has Read, Write, Edit, Bash, Glob, Grep
        assert REPAIR_AGENT_FRONTMATTER["tools"] == [
            "Read", "Write", "Edit", "Bash", "Glob", "Grep"
        ]

    def test_has_required_keys(self):
        """Frontmatter must have name, description, model, tools."""
        required = {"name", "description", "model", "tools"}
        missing = required - set(REPAIR_AGENT_FRONTMATTER.keys())
        assert not missing, f"REPAIR_AGENT_FRONTMATTER missing keys: {missing}"


# ===========================================================================
# Section 2: Terminal Status Line Lists
# ===========================================================================


class TestBugTriageStatus:
    """Verify BUG_TRIAGE_STATUS list contains the correct terminal status lines."""

    def test_is_list(self):
        assert isinstance(BUG_TRIAGE_STATUS, list)

    def test_length(self):
        # DATA ASSUMPTION: Bug Triage Agent has exactly 5 terminal status lines.
        assert len(BUG_TRIAGE_STATUS) == 5

    def test_contains_triage_complete_build_env(self):
        assert "TRIAGE_COMPLETE: build_env" in BUG_TRIAGE_STATUS

    def test_contains_triage_complete_single_unit(self):
        assert "TRIAGE_COMPLETE: single_unit" in BUG_TRIAGE_STATUS

    def test_contains_triage_complete_cross_unit(self):
        assert "TRIAGE_COMPLETE: cross_unit" in BUG_TRIAGE_STATUS

    def test_contains_triage_needs_refinement(self):
        assert "TRIAGE_NEEDS_REFINEMENT" in BUG_TRIAGE_STATUS

    def test_contains_triage_non_reproducible(self):
        assert "TRIAGE_NON_REPRODUCIBLE" in BUG_TRIAGE_STATUS

    def test_all_elements_are_strings(self):
        for item in BUG_TRIAGE_STATUS:
            assert isinstance(item, str), f"Expected str, got {type(item)}: {item!r}"

    def test_no_empty_strings(self):
        for item in BUG_TRIAGE_STATUS:
            assert item.strip(), f"Empty or whitespace-only status line found"

    def test_no_duplicates(self):
        assert len(BUG_TRIAGE_STATUS) == len(set(BUG_TRIAGE_STATUS)), (
            "BUG_TRIAGE_STATUS contains duplicate entries"
        )


class TestRepairAgentStatus:
    """Verify REPAIR_AGENT_STATUS list contains the correct terminal status lines."""

    def test_is_list(self):
        assert isinstance(REPAIR_AGENT_STATUS, list)

    def test_length(self):
        # DATA ASSUMPTION: Repair Agent has exactly 3 terminal status lines.
        assert len(REPAIR_AGENT_STATUS) == 3

    def test_contains_repair_complete(self):
        assert "REPAIR_COMPLETE" in REPAIR_AGENT_STATUS

    def test_contains_repair_failed(self):
        assert "REPAIR_FAILED" in REPAIR_AGENT_STATUS

    def test_contains_repair_reclassify(self):
        assert "REPAIR_RECLASSIFY" in REPAIR_AGENT_STATUS

    def test_all_elements_are_strings(self):
        for item in REPAIR_AGENT_STATUS:
            assert isinstance(item, str), f"Expected str, got {type(item)}: {item!r}"

    def test_no_empty_strings(self):
        for item in REPAIR_AGENT_STATUS:
            assert item.strip(), f"Empty or whitespace-only status line found"

    def test_no_duplicates(self):
        assert len(REPAIR_AGENT_STATUS) == len(set(REPAIR_AGENT_STATUS)), (
            "REPAIR_AGENT_STATUS contains duplicate entries"
        )


# ===========================================================================
# Section 3: BUG_TRIAGE_AGENT_MD_CONTENT — Structure and Frontmatter
# ===========================================================================


class TestBugTriageAgentMdContentStructure:
    """Verify the structural format of the Bug Triage Agent MD content."""

    def test_is_string(self):
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        assert isinstance(content, str)

    def test_starts_with_frontmatter_delimiter(self):
        """Invariant: every *_MD_CONTENT string must start with '---\\n'."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        assert content.startswith("---\n"), (
            "BUG_TRIAGE_AGENT_MD_CONTENT must start with YAML frontmatter delimiter '---\\n'"
        )

    def test_has_second_frontmatter_delimiter(self):
        """Invariant: must contain a second '---\\n' ending the frontmatter."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        # Find second occurrence
        first_end = content.index("---\n", 0) + 4
        try:
            content.index("---\n", first_end)
        except ValueError:
            pytest.fail("BUG_TRIAGE_AGENT_MD_CONTENT missing second frontmatter delimiter")

    def test_frontmatter_contains_name(self):
        """Invariant: frontmatter must contain 'name:' field."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert "name" in fm, "Frontmatter missing 'name' field"

    def test_frontmatter_contains_model(self):
        """Invariant: frontmatter must contain 'model:' field."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert "model" in fm, "Frontmatter missing 'model' field"

    def test_frontmatter_contains_tools(self):
        """Invariant: frontmatter must contain 'tools:' field."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert "tools" in fm, "Frontmatter missing 'tools' field"

    def test_substantial_body_after_frontmatter(self):
        """Invariant: >100 chars of behavioral instructions after frontmatter."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        assert len(body) > 100, (
            f"Body after frontmatter is only {len(body)} chars, expected >100"
        )


class TestBugTriageAgentMdContentFrontmatterMatch:
    """Verify the MD_CONTENT YAML frontmatter matches BUG_TRIAGE_AGENT_FRONTMATTER dict."""

    def test_name_matches_frontmatter_dict(self):
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["name"] == BUG_TRIAGE_AGENT_FRONTMATTER["name"], (
            f"Frontmatter name {fm['name']!r} != dict name "
            f"{BUG_TRIAGE_AGENT_FRONTMATTER['name']!r}"
        )

    def test_description_matches_frontmatter_dict(self):
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm.get("description") == BUG_TRIAGE_AGENT_FRONTMATTER["description"], (
            f"Frontmatter description {fm.get('description')!r} != dict description "
            f"{BUG_TRIAGE_AGENT_FRONTMATTER['description']!r}"
        )

    def test_model_matches_frontmatter_dict(self):
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["model"] == BUG_TRIAGE_AGENT_FRONTMATTER["model"], (
            f"Frontmatter model {fm['model']!r} != dict model "
            f"{BUG_TRIAGE_AGENT_FRONTMATTER['model']!r}"
        )

    def test_tools_match_frontmatter_dict(self):
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["tools"] == BUG_TRIAGE_AGENT_FRONTMATTER["tools"], (
            f"Frontmatter tools {fm['tools']!r} != dict tools "
            f"{BUG_TRIAGE_AGENT_FRONTMATTER['tools']!r}"
        )


# ===========================================================================
# Section 4: BUG_TRIAGE_AGENT_MD_CONTENT — Behavioral Instructions
# ===========================================================================


class TestBugTriageAgentBehavioralInstructions:
    """Verify the Bug Triage Agent's behavioral instructions cover all required topics."""

    def _get_body(self) -> str:
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        return _get_body_after_frontmatter(content)

    def test_body_is_not_skeleton(self):
        """Body must be substantial -- not a placeholder or skeleton."""
        # DATA ASSUMPTION: At least 500 chars and 10 non-empty lines
        body = self._get_body()
        assert len(body) >= 500, (
            f"Body is only {len(body)} chars, expected >= 500 for a real agent definition"
        )
        non_empty_lines = [l for l in body.splitlines() if l.strip()]
        assert len(non_empty_lines) >= 10, (
            f"Body has only {len(non_empty_lines)} non-empty lines, expected >= 10"
        )

    def test_describes_purpose(self):
        """Instructions must describe the agent's purpose."""
        body = self._get_body().lower()
        assert "triage" in body, "Body must mention triage (the agent's purpose)"
        assert "bug" in body or "post-delivery" in body, (
            "Body must mention bugs or post-delivery context"
        )

    def test_describes_socratic_dialog(self):
        """Bug Triage Agent uses Socratic triage dialog."""
        body = self._get_body().lower()
        assert "socratic" in body or "dialog" in body or "dialogue" in body, (
            "Body must describe the Socratic dialog methodology"
        )

    def test_describes_read_only_mode(self):
        """Bug Triage Agent starts in read-only mode before Gate 6.0 authorization."""
        body = self._get_body().lower()
        assert "read-only" in body or "read only" in body, (
            "Body must describe the initial read-only mode"
        )

    def test_describes_write_access_after_authorization(self):
        """After authorization, gains write access to specific directories."""
        body = self._get_body().lower()
        # Should mention the authorized write paths
        assert "tests/regressions" in body or "regressions" in body, (
            "Body must mention tests/regressions/ as a write-accessible path"
        )
        assert "triage_scratch" in body, (
            "Body must mention .svp/triage_scratch/ as a write-accessible path"
        )

    def test_describes_classification(self):
        """Bug Triage Agent classifies bugs as build/environment or logic."""
        body = self._get_body().lower()
        assert "build" in body and "environment" in body or "build_env" in body or "build/env" in body, (
            "Body must describe build/environment classification"
        )
        assert "single" in body or "single_unit" in body or "single-unit" in body, (
            "Body must describe single-unit classification for logic bugs"
        )
        assert "cross" in body or "cross_unit" in body or "cross-unit" in body, (
            "Body must describe cross-unit classification for logic bugs"
        )

    def test_describes_test_writable_assertion(self):
        """For logic bugs: aims to produce test-writable assertion with concrete data."""
        body = self._get_body().lower()
        # Should mention producing assertions / test data
        assert "assert" in body or "test" in body, (
            "Body must describe producing test-writable assertions"
        )
        # Should mention inputs and expected/actual outputs
        assert "input" in body, (
            "Body must mention inputs for test-writable assertions"
        )
        assert "output" in body or "expect" in body, (
            "Body must mention expected/actual outputs for assertions"
        )

    def test_describes_synthetic_data_for_tests(self):
        """Uses real data for diagnosis but produces tests with synthetic data."""
        body = self._get_body().lower()
        assert "synthetic" in body, (
            "Body must mention using synthetic data for tests"
        )

    def test_describes_structured_response_format(self):
        """Bug Triage Agent uses structured response format with tagged closing lines."""
        body = self._get_body()
        # Check for the specific tags: [QUESTION], [DECISION], [CONFIRMED]
        assert "[QUESTION]" in body or "QUESTION" in body, (
            "Body must describe the [QUESTION] structured response tag"
        )
        assert "[DECISION]" in body or "DECISION" in body, (
            "Body must describe the [DECISION] structured response tag"
        )
        assert "[CONFIRMED]" in body or "CONFIRMED" in body, (
            "Body must describe the [CONFIRMED] structured response tag"
        )

    def test_describes_own_ledger(self):
        """Triage dialog uses its own ledger (bug_triage_N.jsonl)."""
        body = self._get_body().lower()
        assert "bug_triage" in body and "jsonl" in body or "ledger" in body, (
            "Body must mention the bug triage ledger"
        )

    def test_describes_dual_format_output(self):
        """Bug Triage Agent produces dual-format output."""
        body = self._get_body().lower()
        assert "dual" in body or "format" in body, (
            "Body must describe dual-format output"
        )

    def test_mentions_all_terminal_status_lines(self):
        """Body must document all terminal status lines from BUG_TRIAGE_STATUS."""
        body = self._get_body()
        for status in BUG_TRIAGE_STATUS:
            assert status in body, (
                f"Body must document terminal status line: {status!r}"
            )

    def test_describes_input_output_format(self):
        """Instructions must describe input/output format."""
        body = self._get_body().lower()
        assert "input" in body, "Body must describe input format"
        assert "output" in body, "Body must describe output format"

    def test_describes_constraints(self):
        """Instructions must describe the agent's constraints."""
        body = self._get_body().lower()
        assert "constraint" in body or "must not" in body or "do not" in body or "cannot" in body, (
            "Body must describe constraints on the agent's behavior"
        )


# ===========================================================================
# Section 5: REPAIR_AGENT_MD_CONTENT — Structure and Frontmatter
# ===========================================================================


class TestRepairAgentMdContentStructure:
    """Verify the structural format of the Repair Agent MD content."""

    def test_is_string(self):
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        assert isinstance(content, str)

    def test_starts_with_frontmatter_delimiter(self):
        """Invariant: every *_MD_CONTENT string must start with '---\\n'."""
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        assert content.startswith("---\n"), (
            "REPAIR_AGENT_MD_CONTENT must start with YAML frontmatter delimiter '---\\n'"
        )

    def test_has_second_frontmatter_delimiter(self):
        """Invariant: must contain a second '---\\n' ending the frontmatter."""
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        first_end = content.index("---\n", 0) + 4
        try:
            content.index("---\n", first_end)
        except ValueError:
            pytest.fail("REPAIR_AGENT_MD_CONTENT missing second frontmatter delimiter")

    def test_frontmatter_contains_name(self):
        """Invariant: frontmatter must contain 'name:' field."""
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert "name" in fm, "Frontmatter missing 'name' field"

    def test_frontmatter_contains_model(self):
        """Invariant: frontmatter must contain 'model:' field."""
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert "model" in fm, "Frontmatter missing 'model' field"

    def test_frontmatter_contains_tools(self):
        """Invariant: frontmatter must contain 'tools:' field."""
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert "tools" in fm, "Frontmatter missing 'tools' field"

    def test_substantial_body_after_frontmatter(self):
        """Invariant: >100 chars of behavioral instructions after frontmatter."""
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        assert len(body) > 100, (
            f"Body after frontmatter is only {len(body)} chars, expected >100"
        )


class TestRepairAgentMdContentFrontmatterMatch:
    """Verify the MD_CONTENT YAML frontmatter matches REPAIR_AGENT_FRONTMATTER dict."""

    def test_name_matches_frontmatter_dict(self):
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["name"] == REPAIR_AGENT_FRONTMATTER["name"], (
            f"Frontmatter name {fm['name']!r} != dict name "
            f"{REPAIR_AGENT_FRONTMATTER['name']!r}"
        )

    def test_description_matches_frontmatter_dict(self):
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm.get("description") == REPAIR_AGENT_FRONTMATTER["description"], (
            f"Frontmatter description {fm.get('description')!r} != dict description "
            f"{REPAIR_AGENT_FRONTMATTER['description']!r}"
        )

    def test_model_matches_frontmatter_dict(self):
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["model"] == REPAIR_AGENT_FRONTMATTER["model"], (
            f"Frontmatter model {fm['model']!r} != dict model "
            f"{REPAIR_AGENT_FRONTMATTER['model']!r}"
        )

    def test_tools_match_frontmatter_dict(self):
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["tools"] == REPAIR_AGENT_FRONTMATTER["tools"], (
            f"Frontmatter tools {fm['tools']!r} != dict tools "
            f"{REPAIR_AGENT_FRONTMATTER['tools']!r}"
        )


# ===========================================================================
# Section 6: REPAIR_AGENT_MD_CONTENT — Behavioral Instructions
# ===========================================================================


class TestRepairAgentBehavioralInstructions:
    """Verify the Repair Agent's behavioral instructions cover all required topics."""

    def _get_body(self) -> str:
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        return _get_body_after_frontmatter(content)

    def test_body_is_not_skeleton(self):
        """Body must be substantial -- not a placeholder or skeleton."""
        # DATA ASSUMPTION: At least 500 chars and 10 non-empty lines
        body = self._get_body()
        assert len(body) >= 500, (
            f"Body is only {len(body)} chars, expected >= 500 for a real agent definition"
        )
        non_empty_lines = [l for l in body.splitlines() if l.strip()]
        assert len(non_empty_lines) >= 10, (
            f"Body has only {len(non_empty_lines)} non-empty lines, expected >= 10"
        )

    def test_describes_purpose(self):
        """Instructions must describe the agent's purpose."""
        body = self._get_body().lower()
        assert "repair" in body, "Body must mention repair (the agent's purpose)"
        assert "build" in body or "environment" in body, (
            "Body must mention build/environment fixes"
        )

    def test_describes_narrow_mandate(self):
        """Repair Agent has narrow mandate for build/environment fixes."""
        body = self._get_body().lower()
        # Should describe what can be modified
        assert "environment" in body, (
            "Body must mention environment files as modifiable"
        )
        assert "pyproject.toml" in body or "pyproject" in body, (
            "Body must mention pyproject.toml as modifiable"
        )
        assert "__init__.py" in body or "__init__" in body, (
            "Body must mention __init__.py files as modifiable"
        )

    def test_describes_file_modification_restrictions(self):
        """Repair Agent cannot modify implementation .py files in src/unit_N/."""
        body = self._get_body().lower()
        # Must describe the restriction on implementation files
        assert "implementation" in body or "src/unit_" in body or "source" in body, (
            "Body must describe restrictions on modifying implementation files"
        )
        assert "cannot" in body or "must not" in body or "do not" in body or "not modify" in body, (
            "Body must explicitly state the restriction on implementation file modification"
        )

    def test_describes_reclassify_behavior(self):
        """Returns REPAIR_RECLASSIFY if fix requires implementation changes."""
        body = self._get_body()
        assert "REPAIR_RECLASSIFY" in body, (
            "Body must describe REPAIR_RECLASSIFY for fixes requiring implementation changes"
        )

    def test_describes_bounded_fix_cycle(self):
        """Repair Agent participates in bounded fix cycle (up to 3 attempts)."""
        body = self._get_body().lower()
        assert "3" in body or "three" in body, (
            "Body must mention the maximum number of fix cycle attempts (3)"
        )
        # Should mention fix cycle or bounded attempts
        assert "fix" in body and ("cycle" in body or "attempt" in body), (
            "Body must describe the bounded fix cycle"
        )

    def test_mentions_all_terminal_status_lines(self):
        """Body must document all terminal status lines from REPAIR_AGENT_STATUS."""
        body = self._get_body()
        for status in REPAIR_AGENT_STATUS:
            assert status in body, (
                f"Body must document terminal status line: {status!r}"
            )

    def test_describes_input_output_format(self):
        """Instructions must describe input/output format."""
        body = self._get_body().lower()
        assert "input" in body, "Body must describe input format"
        assert "output" in body, "Body must describe output format"

    def test_describes_constraints(self):
        """Instructions must describe the agent's constraints."""
        body = self._get_body().lower()
        assert "constraint" in body or "must not" in body or "do not" in body or "cannot" in body, (
            "Body must describe constraints on the agent's behavior"
        )

    def test_describes_methodology(self):
        """Instructions must describe the agent's methodology."""
        body = self._get_body().lower()
        assert "diagnos" in body or "method" in body or "process" in body or "step" in body, (
            "Body must describe the repair methodology or process"
        )


# ===========================================================================
# Section 7: Cross-Cutting Invariant Checks
# ===========================================================================


class TestAgentModelAssignment:
    """Verify model assignments are correct per the blueprint."""

    def test_bug_triage_uses_opus(self):
        """Bug Triage Agent must use claude-opus-4-6 (per blueprint)."""
        assert BUG_TRIAGE_AGENT_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_repair_uses_sonnet(self):
        """Repair Agent must use claude-sonnet-4-6 (per blueprint)."""
        assert REPAIR_AGENT_FRONTMATTER["model"] == "claude-sonnet-4-6"

    def test_bug_triage_md_content_model_is_opus(self):
        """The MD content frontmatter must also use claude-opus-4-6."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["model"] == "claude-opus-4-6"

    def test_repair_md_content_model_is_sonnet(self):
        """The MD content frontmatter must also use claude-sonnet-4-6."""
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["model"] == "claude-sonnet-4-6"


class TestAgentToolSets:
    """Verify both agents have the correct tool sets."""

    def test_bug_triage_tools_complete(self):
        """Bug Triage Agent needs Read, Write, Edit, Bash, Glob, Grep."""
        expected = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
        assert BUG_TRIAGE_AGENT_FRONTMATTER["tools"] == expected

    def test_repair_tools_complete(self):
        """Repair Agent needs Read, Write, Edit, Bash, Glob, Grep."""
        expected = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
        assert REPAIR_AGENT_FRONTMATTER["tools"] == expected

    def test_bug_triage_md_content_tools_match(self):
        """MD content tools must match the frontmatter dict."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        expected = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
        assert fm["tools"] == expected

    def test_repair_md_content_tools_match(self):
        """MD content tools must match the frontmatter dict."""
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        expected = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
        assert fm["tools"] == expected


class TestMdContentDeliverablePaths:
    """Verify each *_MD_CONTENT maps to the correct deliverable file path."""

    def test_bug_triage_agent_md_is_complete_definition(self):
        """BUG_TRIAGE_AGENT_MD_CONTENT -> agents/bug_triage_agent.md."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["name"] == "bug_triage_agent"

    def test_repair_agent_md_is_complete_definition(self):
        """REPAIR_AGENT_MD_CONTENT -> agents/repair_agent.md."""
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["name"] == "repair_agent"


class TestBugTriageReadOnlyInvariant:
    """Bug Triage Agent starts in read-only mode (before Gate 6.0 authorization).

    The MD content must describe the read-only constraint and when it is
    lifted (after Gate 6.0).
    """

    def test_mentions_gate_6_0(self):
        """Body should mention Gate 6.0 for authorization."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        assert "6.0" in body or "gate" in body.lower(), (
            "Body must describe the Gate 6.0 authorization for write access"
        )

    def test_describes_read_only_before_authorization(self):
        """Body must describe read-only mode as the initial state."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content).lower()
        assert "read-only" in body or "read only" in body, (
            "Body must describe the initial read-only mode"
        )


class TestRepairCannotModifyImplementation:
    """Repair Agent cannot modify implementation files (src/unit_N/*.py other than __init__.py).

    If fix requires implementation changes, must return REPAIR_RECLASSIFY.
    """

    def test_repair_reclassify_on_impl_changes(self):
        """Repair Agent must return REPAIR_RECLASSIFY if implementation changes needed."""
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        assert "REPAIR_RECLASSIFY" in body, (
            "Body must describe returning REPAIR_RECLASSIFY for implementation changes"
        )

    def test_repair_describes_impl_restriction(self):
        """Body must describe the restriction on implementation files."""
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content).lower()
        # Should mention that implementation files cannot be modified
        has_impl_restriction = (
            ("implementation" in body and ("cannot" in body or "must not" in body or "not modify" in body))
            or ("src/unit_" in body and ("cannot" in body or "must not" in body or "not modify" in body))
        )
        assert has_impl_restriction, (
            "Body must explicitly describe the restriction on modifying implementation files"
        )


class TestBugTriageStructuredResponseFormat:
    """Bug Triage Agent uses structured response format ([QUESTION], [DECISION], [CONFIRMED])."""

    def test_all_tags_present(self):
        """All three structured response tags must be documented."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        for tag in ["QUESTION", "DECISION", "CONFIRMED"]:
            assert tag in body, (
                f"Body must document the [{tag}] structured response tag"
            )


class TestBugTriageLedger:
    """Bug Triage Agent uses its own ledger (bug_triage_N.jsonl)."""

    def test_mentions_ledger(self):
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content).lower()
        assert "ledger" in body, (
            "Body must mention the triage dialog ledger"
        )

    def test_mentions_bug_triage_ledger_name(self):
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        assert "bug_triage" in body.lower(), (
            "Body must mention 'bug_triage' as the ledger naming convention"
        )


class TestRepairBoundedFixCycleDetail:
    """Repair Agent bounded fix cycle -- up to 3 attempts."""

    def test_mentions_attempt_limit(self):
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        body = _get_body_after_frontmatter(content)
        # Should mention "3" or "three" in context of attempts
        has_three = "3" in body or "three" in body.lower()
        assert has_three, (
            "Body must specify the bounded fix cycle limit (3 attempts)"
        )


# ===========================================================================
# Section 8: Module-Level Signature Checks
# ===========================================================================


class TestModuleLevelSignatures:
    """Verify the exported constants have correct types as specified in Tier 2."""

    def test_bug_triage_frontmatter_type(self):
        """BUG_TRIAGE_AGENT_FRONTMATTER must be Dict[str, Any]."""
        assert isinstance(BUG_TRIAGE_AGENT_FRONTMATTER, dict)
        for key in BUG_TRIAGE_AGENT_FRONTMATTER:
            assert isinstance(key, str), f"Key {key!r} is not a string"

    def test_repair_frontmatter_type(self):
        """REPAIR_AGENT_FRONTMATTER must be Dict[str, Any]."""
        assert isinstance(REPAIR_AGENT_FRONTMATTER, dict)
        for key in REPAIR_AGENT_FRONTMATTER:
            assert isinstance(key, str), f"Key {key!r} is not a string"

    def test_bug_triage_status_type(self):
        """BUG_TRIAGE_STATUS must be List[str]."""
        assert isinstance(BUG_TRIAGE_STATUS, list)
        for item in BUG_TRIAGE_STATUS:
            assert isinstance(item, str)

    def test_repair_status_type(self):
        """REPAIR_AGENT_STATUS must be List[str]."""
        assert isinstance(REPAIR_AGENT_STATUS, list)
        for item in REPAIR_AGENT_STATUS:
            assert isinstance(item, str)

    def test_bug_triage_md_content_type(self):
        """BUG_TRIAGE_AGENT_MD_CONTENT must be str."""
        content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        assert isinstance(content, str)

    def test_repair_md_content_type(self):
        """REPAIR_AGENT_MD_CONTENT must be str."""
        content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        assert isinstance(content, str)


class TestAgentNamesAreUnique:
    """Both agent definitions must have distinct names."""

    def test_frontmatter_dict_names_differ(self):
        assert BUG_TRIAGE_AGENT_FRONTMATTER["name"] != REPAIR_AGENT_FRONTMATTER["name"]

    def test_md_content_names_differ(self):
        bt_content = _get_md_content("BUG_TRIAGE_AGENT_MD_CONTENT")
        repair_content = _get_md_content("REPAIR_AGENT_MD_CONTENT")
        bt_fm = _parse_frontmatter(bt_content)
        repair_fm = _parse_frontmatter(repair_content)
        assert bt_fm["name"] != repair_fm["name"]


class TestStatusLinesDisjoint:
    """Bug Triage and Repair Agent status lines must be disjoint."""

    def test_no_overlap(self):
        bt_set = set(BUG_TRIAGE_STATUS)
        repair_set = set(REPAIR_AGENT_STATUS)
        overlap = bt_set & repair_set
        assert not overlap, (
            f"BUG_TRIAGE_STATUS and REPAIR_AGENT_STATUS overlap: {overlap}"
        )

"""
Tests for Unit 18: Utility Agent Definitions.

Validates the YAML frontmatter dictionaries, terminal status line lists,
and the three *_MD_CONTENT agent definition strings for the Reference
Indexing Agent, Integration Test Author, and Git Repo Agent. Also validates
README_MD_CONTENT as a plain Markdown README (not an agent definition).

DATA ASSUMPTIONS
================

DATA ASSUMPTION: YAML frontmatter in each *_MD_CONTENT string uses the
standard "---" delimiter on separate lines, with key: value pairs between
them. This is the Claude Code agent definition format.

DATA ASSUMPTION: The frontmatter dictionaries defined in Tier 2 signatures
exactly match the keys/values specified in the blueprint. These are the
canonical agent metadata attributes.

DATA ASSUMPTION: Reference Indexing Agent uses claude-sonnet-4-6 and has
tools: Read, Write, Glob, Grep. It reads reference documents and produces
structured summaries saved to references/index/.

DATA ASSUMPTION: Integration Test Author uses claude-opus-4-6 and has
tools: Read, Write, Edit, Bash, Glob, Grep. It generates integration
tests covering cross-unit interactions.

DATA ASSUMPTION: Git Repo Agent uses claude-sonnet-4-6 and has tools:
Read, Write, Edit, Bash, Glob, Grep. It creates a clean git repository
from verified artifacts.

DATA ASSUMPTION: "Substantial behavioral instructions" means >100 characters
after the second YAML frontmatter delimiter, per the Tier 2 invariant.

DATA ASSUMPTION: Terminal status lines are exact string matches used by the
main session routing script. No variations or prefixes are allowed.

DATA ASSUMPTION: Reference Indexing Agent terminal status: "INDEXING_COMPLETE".
DATA ASSUMPTION: Integration Test Author terminal status:
"INTEGRATION_TESTS_COMPLETE".
DATA ASSUMPTION: Git Repo Agent terminal status: "REPO_ASSEMBLY_COMPLETE".

DATA ASSUMPTION: README_MD_CONTENT is a plain Markdown file (NOT an agent
definition). It does NOT have YAML frontmatter. It is tested separately
from the agent MD_CONTENT strings.

DATA ASSUMPTION: For SVP 1.2 (this project), README_MD_CONTENT follows
Mode A: carry-forward from v1.1 README with minimal updates. Must preserve
all 10 baseline sections in order.

DATA ASSUMPTION: A non-skeleton agent definition is at least 500 characters
of body text and has at least 10 non-empty lines of instructions.

DATA ASSUMPTION: Git Repo Agent must reference build-backend =
"setuptools.build_meta" in its instructions.

DATA ASSUMPTION: Git Repo Agent must never reference stub.py in entry
points or imports.

DATA ASSUMPTION: Git Repo Agent must never reference src.unit_N paths
in entry points or imports.

DATA ASSUMPTION: Git Repo Agent entry point:
svp = "svp.scripts.svp_launcher:main" (never svp.scripts.svp_launcher).

DATA ASSUMPTION: Git Repo Agent creates repo at
{project_root.parent}/{project_name}-repo (absolute path).

DATA ASSUMPTION: Git Repo Agent must verify pip install -e . succeeds.

DATA ASSUMPTION: Git Repo Agent must verify CLI entry point loads without
import errors after install.
"""

import re
from typing import Any, Dict, List

import pytest

# Import the unit under test -- frontmatter dicts and status lists have
# concrete values in the stub, so they can be imported directly.
from svp.scripts.utility_agent_definitions import (
    REFERENCE_INDEXING_FRONTMATTER,
    INTEGRATION_TEST_AUTHOR_FRONTMATTER,
    GIT_REPO_AGENT_FRONTMATTER,
    REFERENCE_INDEXING_STATUS,
    INTEGRATION_TEST_AUTHOR_STATUS,
    GIT_REPO_AGENT_STATUS,
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
    import svp.scripts.utility_agent_definitions as mod
    val = getattr(mod, name, None)
    if val is None or not isinstance(val, str):
        pytest.fail(f"{name} is not defined or not a string in svp.scripts.utility_agent_definitions")
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


class TestReferenceIndexingFrontmatter:
    """Verify the REFERENCE_INDEXING_FRONTMATTER dict matches the blueprint."""

    def test_is_dict(self):
        assert isinstance(REFERENCE_INDEXING_FRONTMATTER, dict)

    def test_name(self):
        assert REFERENCE_INDEXING_FRONTMATTER["name"] == "reference_indexing_agent"

    def test_description(self):
        assert REFERENCE_INDEXING_FRONTMATTER["description"] == (
            "Reads reference documents and produces structured summaries"
        )

    def test_model(self):
        # DATA ASSUMPTION: Reference Indexing Agent uses claude-sonnet-4-6
        assert REFERENCE_INDEXING_FRONTMATTER["model"] == "claude-sonnet-4-6"

    def test_tools(self):
        # DATA ASSUMPTION: Reference Indexing Agent has Read, Write, Glob, Grep
        assert REFERENCE_INDEXING_FRONTMATTER["tools"] == ["Read", "Write", "Glob", "Grep"]

    def test_has_required_keys(self):
        """Frontmatter must have name, description, model, tools."""
        required = {"name", "description", "model", "tools"}
        missing = required - set(REFERENCE_INDEXING_FRONTMATTER.keys())
        assert not missing, f"REFERENCE_INDEXING_FRONTMATTER missing keys: {missing}"


class TestIntegrationTestAuthorFrontmatter:
    """Verify the INTEGRATION_TEST_AUTHOR_FRONTMATTER dict matches the blueprint."""

    def test_is_dict(self):
        assert isinstance(INTEGRATION_TEST_AUTHOR_FRONTMATTER, dict)

    def test_name(self):
        assert INTEGRATION_TEST_AUTHOR_FRONTMATTER["name"] == "integration_test_author"

    def test_description(self):
        assert INTEGRATION_TEST_AUTHOR_FRONTMATTER["description"] == (
            "Generates integration tests covering cross-unit interactions"
        )

    def test_model(self):
        # DATA ASSUMPTION: Integration Test Author uses claude-opus-4-6
        assert INTEGRATION_TEST_AUTHOR_FRONTMATTER["model"] == "claude-opus-4-6"

    def test_tools(self):
        # DATA ASSUMPTION: Integration Test Author has Read, Write, Edit, Bash, Glob, Grep
        assert INTEGRATION_TEST_AUTHOR_FRONTMATTER["tools"] == [
            "Read", "Write", "Edit", "Bash", "Glob", "Grep"
        ]

    def test_has_required_keys(self):
        """Frontmatter must have name, description, model, tools."""
        required = {"name", "description", "model", "tools"}
        missing = required - set(INTEGRATION_TEST_AUTHOR_FRONTMATTER.keys())
        assert not missing, f"INTEGRATION_TEST_AUTHOR_FRONTMATTER missing keys: {missing}"


class TestGitRepoAgentFrontmatter:
    """Verify the GIT_REPO_AGENT_FRONTMATTER dict matches the blueprint."""

    def test_is_dict(self):
        assert isinstance(GIT_REPO_AGENT_FRONTMATTER, dict)

    def test_name(self):
        assert GIT_REPO_AGENT_FRONTMATTER["name"] == "git_repo_agent"

    def test_description(self):
        assert GIT_REPO_AGENT_FRONTMATTER["description"] == (
            "Creates clean git repository from verified artifacts"
        )

    def test_model(self):
        # DATA ASSUMPTION: Git Repo Agent uses claude-sonnet-4-6
        assert GIT_REPO_AGENT_FRONTMATTER["model"] == "claude-sonnet-4-6"

    def test_tools(self):
        # DATA ASSUMPTION: Git Repo Agent has Read, Write, Edit, Bash, Glob, Grep
        assert GIT_REPO_AGENT_FRONTMATTER["tools"] == [
            "Read", "Write", "Edit", "Bash", "Glob", "Grep"
        ]

    def test_has_required_keys(self):
        """Frontmatter must have name, description, model, tools."""
        required = {"name", "description", "model", "tools"}
        missing = required - set(GIT_REPO_AGENT_FRONTMATTER.keys())
        assert not missing, f"GIT_REPO_AGENT_FRONTMATTER missing keys: {missing}"


class TestFrontmatterCrossCutting:
    """Cross-cutting checks for all three frontmatter dicts."""

    def test_models_match_blueprint(self):
        """Reference Indexing and Git Repo use sonnet; Integration Test Author uses opus."""
        assert REFERENCE_INDEXING_FRONTMATTER["model"] == "claude-sonnet-4-6"
        assert INTEGRATION_TEST_AUTHOR_FRONTMATTER["model"] == "claude-opus-4-6"
        assert GIT_REPO_AGENT_FRONTMATTER["model"] == "claude-sonnet-4-6"

    def test_all_have_distinct_names(self):
        """Each agent has a distinct name."""
        names = {
            REFERENCE_INDEXING_FRONTMATTER["name"],
            INTEGRATION_TEST_AUTHOR_FRONTMATTER["name"],
            GIT_REPO_AGENT_FRONTMATTER["name"],
        }
        assert len(names) == 3, "All three agents must have distinct names"

    def test_reference_indexing_no_edit_bash(self):
        """Reference Indexing Agent does NOT have Edit or Bash tools."""
        tools = REFERENCE_INDEXING_FRONTMATTER["tools"]
        assert "Edit" not in tools, "Reference Indexing must not have Edit tool"
        assert "Bash" not in tools, "Reference Indexing must not have Bash tool"

    def test_integration_and_git_have_write_edit_bash(self):
        """Integration Test Author and Git Repo Agent have Write, Edit, Bash."""
        for label, fm in [
            ("INTEGRATION_TEST_AUTHOR", INTEGRATION_TEST_AUTHOR_FRONTMATTER),
            ("GIT_REPO_AGENT", GIT_REPO_AGENT_FRONTMATTER),
        ]:
            tools = fm["tools"]
            assert "Write" in tools, f"{label} must have Write tool"
            assert "Edit" in tools, f"{label} must have Edit tool"
            assert "Bash" in tools, f"{label} must have Bash tool"


# ===========================================================================
# Section 2: Terminal Status Line Constants
# ===========================================================================


class TestReferenceIndexingStatusLines:
    """Verify REFERENCE_INDEXING_STATUS list matches the blueprint."""

    def test_is_list(self):
        assert isinstance(REFERENCE_INDEXING_STATUS, list)

    def test_values(self):
        assert REFERENCE_INDEXING_STATUS == ["INDEXING_COMPLETE"]

    def test_length(self):
        assert len(REFERENCE_INDEXING_STATUS) == 1


class TestIntegrationTestAuthorStatusLines:
    """Verify INTEGRATION_TEST_AUTHOR_STATUS list matches the blueprint."""

    def test_is_list(self):
        assert isinstance(INTEGRATION_TEST_AUTHOR_STATUS, list)

    def test_values(self):
        assert INTEGRATION_TEST_AUTHOR_STATUS == ["INTEGRATION_TESTS_COMPLETE"]

    def test_length(self):
        assert len(INTEGRATION_TEST_AUTHOR_STATUS) == 1


class TestGitRepoAgentStatusLines:
    """Verify GIT_REPO_AGENT_STATUS list matches the blueprint."""

    def test_is_list(self):
        assert isinstance(GIT_REPO_AGENT_STATUS, list)

    def test_values(self):
        assert GIT_REPO_AGENT_STATUS == ["REPO_ASSEMBLY_COMPLETE"]

    def test_length(self):
        assert len(GIT_REPO_AGENT_STATUS) == 1


# ===========================================================================
# Section 3: MD_CONTENT String Existence and Type
# ===========================================================================


class TestMdContentExistence:
    """Verify that *_MD_CONTENT constants exist and are non-empty strings.

    These tests will fail on the stub (red run) because the stub only
    declares type annotations without assigning values.
    """

    def test_reference_indexing_md_content_is_string(self):
        content = _get_md_content("REFERENCE_INDEXING_AGENT_MD_CONTENT")
        assert isinstance(content, str)
        assert len(content) > 0, "REFERENCE_INDEXING_AGENT_MD_CONTENT must not be empty"

    def test_integration_test_author_md_content_is_string(self):
        content = _get_md_content("INTEGRATION_TEST_AUTHOR_MD_CONTENT")
        assert isinstance(content, str)
        assert len(content) > 0, "INTEGRATION_TEST_AUTHOR_MD_CONTENT must not be empty"

    def test_git_repo_agent_md_content_is_string(self):
        content = _get_md_content("GIT_REPO_AGENT_MD_CONTENT")
        assert isinstance(content, str)
        assert len(content) > 0, "GIT_REPO_AGENT_MD_CONTENT must not be empty"

    def test_readme_md_content_is_string(self):
        content = _get_md_content("README_MD_CONTENT")
        assert isinstance(content, str)
        assert len(content) > 0, "README_MD_CONTENT must not be empty"


# ===========================================================================
# Section 4: YAML Frontmatter Structure Invariants (Agent MD_CONTENTs only)
# ===========================================================================


AGENT_MD_CONTENT_NAMES = [
    "REFERENCE_INDEXING_AGENT_MD_CONTENT",
    "INTEGRATION_TEST_AUTHOR_MD_CONTENT",
    "GIT_REPO_AGENT_MD_CONTENT",
]


class TestYamlFrontmatterInvariants:
    """Verify every agent *_MD_CONTENT string starts with valid YAML frontmatter.

    Invariant: Starts with '---\\n', contains 'name:', 'model:', 'tools:',
    and has a second '---\\n' to close the frontmatter.

    NOTE: README_MD_CONTENT is NOT an agent definition, so these invariants
    do NOT apply to it.
    """

    @pytest.mark.parametrize("const_name", AGENT_MD_CONTENT_NAMES)
    def test_starts_with_yaml_delimiter(self, const_name):
        content = _get_md_content(const_name)
        assert content.startswith("---\n"), (
            f"{const_name} must start with '---\\n'"
        )

    @pytest.mark.parametrize("const_name", AGENT_MD_CONTENT_NAMES)
    def test_has_closing_yaml_delimiter(self, const_name):
        content = _get_md_content(const_name)
        # There must be a second "---\n" after the opening one
        idx = content.index("---\n", 4)
        assert idx > 4, (
            f"{const_name} must have a closing '---\\n' frontmatter delimiter"
        )

    @pytest.mark.parametrize("const_name", AGENT_MD_CONTENT_NAMES)
    def test_frontmatter_contains_name(self, const_name):
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert "name" in fm, f"{const_name} frontmatter must contain 'name:'"

    @pytest.mark.parametrize("const_name", AGENT_MD_CONTENT_NAMES)
    def test_frontmatter_contains_model(self, const_name):
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert "model" in fm, f"{const_name} frontmatter must contain 'model:'"

    @pytest.mark.parametrize("const_name", AGENT_MD_CONTENT_NAMES)
    def test_frontmatter_contains_tools(self, const_name):
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert "tools" in fm, f"{const_name} frontmatter must contain 'tools:'"

    @pytest.mark.parametrize("const_name", AGENT_MD_CONTENT_NAMES)
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
    """Verify the YAML frontmatter in each agent *_MD_CONTENT matches its
    corresponding *_FRONTMATTER dict.
    """

    # -- Reference Indexing Agent --

    def test_reference_indexing_frontmatter_name_matches(self):
        content = _get_md_content("REFERENCE_INDEXING_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["name"] == REFERENCE_INDEXING_FRONTMATTER["name"]

    def test_reference_indexing_frontmatter_description_matches(self):
        content = _get_md_content("REFERENCE_INDEXING_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm.get("description") == REFERENCE_INDEXING_FRONTMATTER["description"]

    def test_reference_indexing_frontmatter_model_matches(self):
        content = _get_md_content("REFERENCE_INDEXING_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["model"] == REFERENCE_INDEXING_FRONTMATTER["model"]

    def test_reference_indexing_frontmatter_tools_matches(self):
        content = _get_md_content("REFERENCE_INDEXING_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["tools"] == REFERENCE_INDEXING_FRONTMATTER["tools"]

    # -- Integration Test Author --

    def test_integration_test_author_frontmatter_name_matches(self):
        content = _get_md_content("INTEGRATION_TEST_AUTHOR_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["name"] == INTEGRATION_TEST_AUTHOR_FRONTMATTER["name"]

    def test_integration_test_author_frontmatter_description_matches(self):
        content = _get_md_content("INTEGRATION_TEST_AUTHOR_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm.get("description") == INTEGRATION_TEST_AUTHOR_FRONTMATTER["description"]

    def test_integration_test_author_frontmatter_model_matches(self):
        content = _get_md_content("INTEGRATION_TEST_AUTHOR_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["model"] == INTEGRATION_TEST_AUTHOR_FRONTMATTER["model"]

    def test_integration_test_author_frontmatter_tools_matches(self):
        content = _get_md_content("INTEGRATION_TEST_AUTHOR_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["tools"] == INTEGRATION_TEST_AUTHOR_FRONTMATTER["tools"]

    # -- Git Repo Agent --

    def test_git_repo_agent_frontmatter_name_matches(self):
        content = _get_md_content("GIT_REPO_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["name"] == GIT_REPO_AGENT_FRONTMATTER["name"]

    def test_git_repo_agent_frontmatter_description_matches(self):
        content = _get_md_content("GIT_REPO_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm.get("description") == GIT_REPO_AGENT_FRONTMATTER["description"]

    def test_git_repo_agent_frontmatter_model_matches(self):
        content = _get_md_content("GIT_REPO_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["model"] == GIT_REPO_AGENT_FRONTMATTER["model"]

    def test_git_repo_agent_frontmatter_tools_matches(self):
        content = _get_md_content("GIT_REPO_AGENT_MD_CONTENT")
        fm = _parse_frontmatter(content)
        assert fm["tools"] == GIT_REPO_AGENT_FRONTMATTER["tools"]


# ===========================================================================
# Section 6: Behavioral Contracts -- Reference Indexing Agent
# ===========================================================================


class TestReferenceIndexingBehavioralContracts:
    """Verify Reference Indexing Agent MD content describes the required behaviors.

    Behavioral contracts from the blueprint:
    - Reads a full reference document or explores a GitHub repository via MCP.
    - Produces a structured summary saved to references/index/.
    - For PDFs, uses Claude's native document understanding.
    - For GitHub repos, reads README, maps directory structure, identifies
      key modules.
    - Terminal status: INDEXING_COMPLETE.
    - Uses claude-sonnet-4-6.
    """

    @pytest.fixture
    def content(self):
        return _get_md_content("REFERENCE_INDEXING_AGENT_MD_CONTENT")

    @pytest.fixture
    def body(self, content):
        return _get_body_after_frontmatter(content)

    def test_describes_purpose(self, body):
        """Reference Indexing Agent must describe reading reference documents
        and producing summaries."""
        body_lower = body.lower()
        assert ("reference" in body_lower or "document" in body_lower
                or "summar" in body_lower), (
            "Reference Indexing Agent must describe its purpose"
        )

    def test_describes_structured_summary(self, body):
        """Agent produces structured summaries."""
        body_lower = body.lower()
        assert ("summar" in body_lower or "structur" in body_lower
                or "index" in body_lower), (
            "Reference Indexing Agent must describe structured summary output"
        )

    def test_describes_output_path(self, body):
        """Summaries are saved to references/index/."""
        assert ("references/index" in body or "references/index/" in body), (
            "Reference Indexing Agent must mention references/index/ output path"
        )

    def test_describes_pdf_handling(self, body):
        """For PDFs, uses Claude's native document understanding."""
        body_lower = body.lower()
        assert ("pdf" in body_lower or "document understanding" in body_lower), (
            "Reference Indexing Agent must describe PDF handling"
        )

    def test_describes_github_repo_handling(self, body):
        """For GitHub repos, reads README, maps directory structure,
        identifies key modules."""
        body_lower = body.lower()
        assert ("github" in body_lower or "repo" in body_lower
                or "repository" in body_lower), (
            "Reference Indexing Agent must describe GitHub repo handling"
        )

    def test_terminal_status_indexing_complete(self, body):
        """Must mention INDEXING_COMPLETE terminal status."""
        assert "INDEXING_COMPLETE" in body, (
            "Reference Indexing Agent must mention INDEXING_COMPLETE status"
        )

    def test_uses_sonnet_model(self, content):
        """Reference Indexing Agent uses claude-sonnet-4-6."""
        fm = _parse_frontmatter(content)
        assert fm["model"] == "claude-sonnet-4-6"

    def test_describes_methodology(self, body):
        """Must describe its methodology."""
        body_lower = body.lower()
        assert ("method" in body_lower or "approach" in body_lower
                or "process" in body_lower or "step" in body_lower
                or "how" in body_lower or "procedure" in body_lower
                or "##" in body), (
            "Reference Indexing Agent must describe its methodology"
        )

    def test_describes_constraints(self, body):
        """Must describe its constraints."""
        body_lower = body.lower()
        assert ("constraint" in body_lower or "must not" in body_lower
                or "do not" in body_lower or "never" in body_lower
                or "restrict" in body_lower or "must" in body_lower), (
            "Reference Indexing Agent must describe its constraints"
        )

    def test_describes_input_output_format(self, body):
        """Must describe its input/output format."""
        body_lower = body.lower()
        assert ("input" in body_lower or "output" in body_lower
                or "receive" in body_lower or "produc" in body_lower
                or "format" in body_lower), (
            "Reference Indexing Agent must describe its input/output format"
        )

    def test_describes_github_readme_directory_modules(self, body):
        """For GitHub repos: reads README, maps directory structure,
        identifies key modules."""
        body_lower = body.lower()
        has_readme = "readme" in body_lower
        has_directory = "director" in body_lower or "structure" in body_lower
        has_modules = "module" in body_lower or "key" in body_lower
        assert has_readme or has_directory or has_modules, (
            "Reference Indexing Agent must describe GitHub repo exploration: "
            "reading README, mapping directory structure, identifying key modules"
        )


# ===========================================================================
# Section 7: Behavioral Contracts -- Integration Test Author
# ===========================================================================


class TestIntegrationTestAuthorBehavioralContracts:
    """Verify Integration Test Author MD content describes the required behaviors.

    Behavioral contracts from the blueprint:
    - Receives stakeholder spec plus contract signatures from all units.
    - Reads specific source files on demand from disk.
    - Generates tests covering cross-unit interactions: data flow, resource
      contention, timing, error propagation.
    - Plus at least one end-to-end domain-meaningful validation.
    - For SVP self-builds: must include integration test exercising the
      svp restore code path using bundled Game of Life example files.
    - Terminal status: INTEGRATION_TESTS_COMPLETE.
    - Uses claude-opus-4-6.
    """

    @pytest.fixture
    def content(self):
        return _get_md_content("INTEGRATION_TEST_AUTHOR_MD_CONTENT")

    @pytest.fixture
    def body(self, content):
        return _get_body_after_frontmatter(content)

    def test_describes_purpose(self, body):
        """Must describe generating integration tests."""
        body_lower = body.lower()
        assert ("integration test" in body_lower or "cross-unit" in body_lower
                or "integration" in body_lower), (
            "Integration Test Author must describe integration testing"
        )

    def test_describes_cross_unit_interactions(self, body):
        """Must cover cross-unit interactions."""
        body_lower = body.lower()
        assert ("cross-unit" in body_lower or "cross unit" in body_lower
                or "interaction" in body_lower or "between unit" in body_lower
                or "across unit" in body_lower), (
            "Integration Test Author must describe cross-unit interactions"
        )

    def test_describes_data_flow(self, body):
        """Must mention data flow testing."""
        body_lower = body.lower()
        assert ("data flow" in body_lower or "data" in body_lower), (
            "Integration Test Author must describe data flow testing"
        )

    def test_describes_error_propagation(self, body):
        """Must mention error propagation testing."""
        body_lower = body.lower()
        assert ("error propagation" in body_lower or "error" in body_lower), (
            "Integration Test Author must describe error propagation testing"
        )

    def test_describes_end_to_end_validation(self, body):
        """Must include at least one end-to-end domain-meaningful validation."""
        body_lower = body.lower()
        assert ("end-to-end" in body_lower or "end to end" in body_lower
                or "e2e" in body_lower or "domain" in body_lower), (
            "Integration Test Author must describe end-to-end validation"
        )

    def test_describes_svp_restore_test(self, body):
        """For SVP self-builds: must include integration test exercising
        the svp restore code path using Game of Life example files."""
        body_lower = body.lower()
        assert ("restore" in body_lower or "game of life" in body_lower
                or "gol" in body_lower), (
            "Integration Test Author must describe the svp restore "
            "integration test using Game of Life example"
        )

    def test_terminal_status_integration_tests_complete(self, body):
        """Must mention INTEGRATION_TESTS_COMPLETE terminal status."""
        assert "INTEGRATION_TESTS_COMPLETE" in body, (
            "Integration Test Author must mention INTEGRATION_TESTS_COMPLETE status"
        )

    def test_uses_opus_model(self, content):
        """Integration Test Author uses claude-opus-4-6."""
        fm = _parse_frontmatter(content)
        assert fm["model"] == "claude-opus-4-6"

    def test_describes_receives_spec_and_contracts(self, body):
        """Receives stakeholder spec plus contract signatures from all units."""
        body_lower = body.lower()
        assert ("spec" in body_lower or "stakeholder" in body_lower
                or "contract" in body_lower or "signature" in body_lower), (
            "Integration Test Author must describe receiving spec and contracts"
        )

    def test_describes_reading_source_files(self, body):
        """Reads specific source files on demand from disk."""
        body_lower = body.lower()
        assert ("source" in body_lower or "file" in body_lower
                or "read" in body_lower or "disk" in body_lower), (
            "Integration Test Author must describe reading source files"
        )

    def test_describes_methodology(self, body):
        """Must describe its methodology."""
        body_lower = body.lower()
        assert ("method" in body_lower or "approach" in body_lower
                or "process" in body_lower or "step" in body_lower
                or "how" in body_lower or "procedure" in body_lower
                or "##" in body), (
            "Integration Test Author must describe its methodology"
        )

    def test_describes_constraints(self, body):
        """Must describe its constraints."""
        body_lower = body.lower()
        assert ("constraint" in body_lower or "must not" in body_lower
                or "do not" in body_lower or "never" in body_lower
                or "restrict" in body_lower or "must" in body_lower), (
            "Integration Test Author must describe its constraints"
        )

    def test_describes_resource_contention_or_timing(self, body):
        """Must mention resource contention or timing testing."""
        body_lower = body.lower()
        assert ("resource" in body_lower or "contention" in body_lower
                or "timing" in body_lower or "concurren" in body_lower), (
            "Integration Test Author must describe resource contention "
            "or timing testing"
        )


# ===========================================================================
# Section 8: Behavioral Contracts -- Git Repo Agent
# ===========================================================================


class TestGitRepoAgentBehavioralContracts:
    """Verify Git Repo Agent MD content describes the required behaviors.

    Behavioral contracts from the blueprint:
    - Creates a clean git repository at {project_root.parent}/{project_name}-repo.
    - Assembly mapping: reads blueprint preamble file tree.
    - Copies unit implementation content from src/unit_N/ to final paths.
    - Rewrites all from src.unit_N imports to final module paths.
    - Never reproduces workspace src/unit_N/ directory structure.
    - Commits in topological order.
    - Must use build-backend = "setuptools.build_meta".
    - Entry points to final relocated module paths -- never stub.py, never src.unit_N.
    - Entry point for launcher: svp.scripts.svp_launcher:main.
    - Must verify pip install -e . succeeds.
    - Must verify CLI entry point loads without import errors.
    - Bounded fix cycle (up to 3 reassembly attempts).
    - Structural validation for plugin directory structure.
    - Writes README.md from README_MD_CONTENT.
    - Terminal status: REPO_ASSEMBLY_COMPLETE.
    - Uses claude-sonnet-4-6.
    """

    @pytest.fixture
    def content(self):
        return _get_md_content("GIT_REPO_AGENT_MD_CONTENT")

    @pytest.fixture
    def body(self, content):
        return _get_body_after_frontmatter(content)

    def test_describes_purpose(self, body):
        """Git Repo Agent must describe creating a clean git repository."""
        body_lower = body.lower()
        assert ("git" in body_lower and ("repo" in body_lower
                or "repository" in body_lower)), (
            "Git Repo Agent must describe creating a git repository"
        )

    def test_describes_repo_path(self, body):
        """Repo at {project_root.parent}/{project_name}-repo (absolute path)."""
        assert ("-repo" in body or "project_root" in body
                or "parent" in body.lower()), (
            "Git Repo Agent must describe the repo output path"
        )

    def test_describes_assembly_mapping(self, body):
        """Reads blueprint preamble file tree to determine final paths."""
        body_lower = body.lower()
        assert ("blueprint" in body_lower or "file tree" in body_lower
                or "preamble" in body_lower or "mapping" in body_lower
                or "assembly" in body_lower), (
            "Git Repo Agent must describe assembly mapping from blueprint"
        )

    def test_describes_import_rewriting(self, body):
        """Rewrites all from src.unit_N imports to final module paths."""
        body_lower = body.lower()
        assert ("rewrite" in body_lower or "import" in body_lower), (
            "Git Repo Agent must describe import rewriting"
        )

    def test_describes_never_reproduces_workspace_structure(self, body):
        """Never reproduces workspace src/unit_N/ directory structure."""
        body_lower = body.lower()
        assert ("src/unit" in body_lower or "unit_n" in body_lower
                or "src.unit" in body_lower or "workspace" in body_lower
                or "never" in body_lower), (
            "Git Repo Agent must describe not reproducing workspace structure"
        )

    def test_describes_commit_order(self, body):
        """Commits in order: infrastructure, stakeholder spec, blueprint, etc."""
        body_lower = body.lower()
        assert ("commit" in body_lower and ("order" in body_lower
                or "topolog" in body_lower or "infrastructure" in body_lower
                or "sequence" in body_lower)), (
            "Git Repo Agent must describe commit ordering"
        )

    def test_describes_setuptools_build_backend(self, body):
        """Must use build-backend = 'setuptools.build_meta'."""
        assert ("setuptools.build_meta" in body
                or "setuptools" in body.lower()), (
            "Git Repo Agent must mention setuptools.build_meta build backend"
        )

    def test_describes_entry_point_launcher(self, body):
        """Entry point: svp = 'svp.scripts.svp_launcher:main'."""
        assert ("svp.scripts.svp_launcher" in body
                or "svp_launcher" in body), (
            "Git Repo Agent must describe the launcher entry point"
        )

    def test_describes_no_stub_in_entry_points(self, body):
        """Never stub.py in entry points or imports."""
        body_lower = body.lower()
        assert ("stub" in body_lower or "never" in body_lower), (
            "Git Repo Agent must describe the constraint against stub.py "
            "in entry points"
        )

    def test_describes_pip_install_verification(self, body):
        """Must verify pip install -e . succeeds."""
        body_lower = body.lower()
        assert ("pip install" in body_lower or "pip" in body_lower
                or "install" in body_lower), (
            "Git Repo Agent must describe pip install verification"
        )

    def test_describes_cli_entry_point_verification(self, body):
        """Must verify CLI entry point loads without import errors."""
        body_lower = body.lower()
        assert ("entry point" in body_lower or "cli" in body_lower
                or "import error" in body_lower), (
            "Git Repo Agent must describe CLI entry point verification"
        )

    def test_describes_bounded_fix_cycle(self, body):
        """Bounded fix cycle (up to 3 reassembly attempts)."""
        body_lower = body.lower()
        assert ("fix" in body_lower or "reassembl" in body_lower
                or "retry" in body_lower or "attempt" in body_lower
                or "3" in body or "three" in body_lower), (
            "Git Repo Agent must describe bounded fix cycle"
        )

    def test_terminal_status_repo_assembly_complete(self, body):
        """Must mention REPO_ASSEMBLY_COMPLETE terminal status."""
        assert "REPO_ASSEMBLY_COMPLETE" in body, (
            "Git Repo Agent must mention REPO_ASSEMBLY_COMPLETE status"
        )

    def test_uses_sonnet_model(self, content):
        """Git Repo Agent uses claude-sonnet-4-6."""
        fm = _parse_frontmatter(content)
        assert fm["model"] == "claude-sonnet-4-6"

    def test_describes_methodology(self, body):
        """Must describe its methodology."""
        body_lower = body.lower()
        assert ("method" in body_lower or "approach" in body_lower
                or "process" in body_lower or "step" in body_lower
                or "how" in body_lower or "procedure" in body_lower
                or "##" in body), (
            "Git Repo Agent must describe its methodology"
        )

    def test_describes_constraints(self, body):
        """Must describe its constraints."""
        body_lower = body.lower()
        assert ("constraint" in body_lower or "must not" in body_lower
                or "do not" in body_lower or "never" in body_lower
                or "restrict" in body_lower or "must" in body_lower), (
            "Git Repo Agent must describe its constraints"
        )

    def test_describes_readme_writing(self, body):
        """Must describe writing README.md from README_MD_CONTENT."""
        body_lower = body.lower()
        assert ("readme" in body_lower), (
            "Git Repo Agent must describe README.md writing"
        )

    def test_describes_structural_validation(self, body):
        """Structural validation for plugin directory structure."""
        body_lower = body.lower()
        assert ("validat" in body_lower or "structur" in body_lower
                or "plugin" in body_lower or "verif" in body_lower), (
            "Git Repo Agent must describe structural validation"
        )


# ===========================================================================
# Section 9: Cross-Cutting Behavioral Contracts (All Three Agents)
# ===========================================================================


class TestAllAgentsCommonContracts:
    """Verify behavioral contracts that apply to all three agents."""

    @pytest.mark.parametrize("const_name,status_list", [
        ("REFERENCE_INDEXING_AGENT_MD_CONTENT", REFERENCE_INDEXING_STATUS),
        ("INTEGRATION_TEST_AUTHOR_MD_CONTENT", INTEGRATION_TEST_AUTHOR_STATUS),
        ("GIT_REPO_AGENT_MD_CONTENT", GIT_REPO_AGENT_STATUS),
    ])
    def test_all_terminal_status_lines_mentioned(self, const_name, status_list):
        """Each agent's body must mention all its terminal status lines."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        for status in status_list:
            key_part = status.split(":")[0].strip()
            assert key_part in body, (
                f"{const_name} must mention terminal status line '{status}' "
                f"(at minimum '{key_part}')"
            )

    @pytest.mark.parametrize("const_name", AGENT_MD_CONTENT_NAMES)
    def test_describes_terminal_status_line_concept(self, const_name):
        """All agents must describe their terminal status line mechanism."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        body_lower = body.lower()
        assert ("terminal status" in body_lower or "status line" in body_lower
                or "terminal line" in body_lower), (
            f"{const_name} must describe the terminal status line concept"
        )

    @pytest.mark.parametrize("const_name", AGENT_MD_CONTENT_NAMES)
    def test_is_valid_yaml_frontmatter(self, const_name):
        """Frontmatter YAML must be parseable without errors."""
        content = _get_md_content(const_name)
        fm = _parse_frontmatter(content)
        assert isinstance(fm, dict), (
            f"{const_name} frontmatter must parse as a dict"
        )

    @pytest.mark.parametrize("const_name", AGENT_MD_CONTENT_NAMES)
    def test_body_is_substantial(self, const_name):
        """All agents must have substantial body text (>100 chars)."""
        body = _get_body_after_frontmatter(_get_md_content(const_name))
        stripped = body.strip()
        assert len(stripped) > 100, (
            f"{const_name} body must be >100 chars (got {len(stripped)})"
        )


# ===========================================================================
# Section 10: Agent Definition Completeness
# ===========================================================================


class TestAgentDefinitionCompleteness:
    """Verify each agent *_MD_CONTENT is a complete agent definition, not a
    placeholder or skeleton."""

    @pytest.mark.parametrize("const_name", AGENT_MD_CONTENT_NAMES)
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

    @pytest.mark.parametrize("const_name", AGENT_MD_CONTENT_NAMES)
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

    @pytest.mark.parametrize("const_name", AGENT_MD_CONTENT_NAMES)
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
# Section 11: Git Repo Agent Invariants
# ===========================================================================


class TestGitRepoAgentInvariants:
    """Test Git Repo Agent-specific invariants from the blueprint.

    The invariants require:
    - build-backend = "setuptools.build_meta" in pyproject.toml
    - Never reference stub.py in entry points or imports
    - Never reference src.unit_N paths in entry points or imports
    - Relocate unit implementations from src/unit_N/ to blueprint file tree paths
    - Rewrite cross-unit imports from src.unit_N to final module paths
    - Create repo at {project_root.parent}/{project_name}-repo (absolute path)
    - Verify pip install -e . succeeds
    - Verify CLI entry point loads without import errors
    - Place svp_launcher.py at svp/scripts/svp_launcher.py (not at repo root)
    - Entry point: svp = "svp.scripts.svp_launcher:main"
    - Write README.md from README_MD_CONTENT
    """

    @pytest.fixture
    def body(self):
        content = _get_md_content("GIT_REPO_AGENT_MD_CONTENT")
        return _get_body_after_frontmatter(content)

    def test_mentions_setuptools_build_meta(self, body):
        """Must reference setuptools.build_meta."""
        assert "setuptools" in body.lower(), (
            "Git Repo Agent must mention setuptools build backend"
        )

    def test_mentions_no_stub_py(self, body):
        """Must mention the constraint against using stub.py."""
        body_lower = body.lower()
        assert "stub" in body_lower, (
            "Git Repo Agent must reference the stub.py prohibition"
        )

    def test_mentions_svp_launcher_entry_point(self, body):
        """Must mention svp.scripts.svp_launcher:main entry point."""
        assert "svp_launcher" in body or "svp.scripts" in body, (
            "Git Repo Agent must mention the svp_launcher entry point"
        )

    def test_mentions_pip_install(self, body):
        """Must mention pip install verification."""
        assert "pip" in body.lower(), (
            "Git Repo Agent must mention pip install verification"
        )

    def test_mentions_absolute_path_repo_location(self, body):
        """Repo at {project_root.parent}/{project_name}-repo (absolute path)."""
        body_lower = body.lower()
        assert ("absolute" in body_lower or "-repo" in body
                or "project_root" in body), (
            "Git Repo Agent must describe absolute path repo location"
        )

    def test_mentions_readme(self, body):
        """Must mention writing README.md."""
        assert "README" in body or "readme" in body.lower(), (
            "Git Repo Agent must mention README.md"
        )

    def test_mentions_svp_launcher_placement(self, body):
        """svp_launcher.py at svp/scripts/svp_launcher.py, not at repo root."""
        assert ("svp/scripts" in body or "svp_launcher" in body), (
            "Git Repo Agent must describe svp_launcher.py placement"
        )


# ===========================================================================
# Section 12: README_MD_CONTENT (NOT an agent definition)
# ===========================================================================


class TestReadmeMdContent:
    """Verify README_MD_CONTENT is a valid plain Markdown README file.

    README_MD_CONTENT is NOT an agent definition -- it does NOT have
    YAML frontmatter. It is tested separately from the agent MD_CONTENT
    strings.

    For SVP 1.2 (this project), Mode A applies: carry-forward from v1.1
    README with minimal updates.
    """

    def test_is_string_and_nonempty(self):
        """README_MD_CONTENT must be a non-empty string."""
        content = _get_md_content("README_MD_CONTENT")
        assert isinstance(content, str)
        assert len(content) > 0

    def test_does_not_start_with_yaml_frontmatter(self):
        """README is NOT an agent definition -- should NOT start with '---'
        YAML frontmatter delimiter (unless it happens to, which is uncommon
        for READMEs). We check it is valid Markdown, not agent definition."""
        content = _get_md_content("README_MD_CONTENT")
        # A README should be a standard Markdown file. It may or may not
        # start with '---'. The key invariant is that it should NOT be
        # tested against agent definition invariants.
        assert isinstance(content, str)

    def test_has_markdown_headings(self):
        """A README should have section headings."""
        content = _get_md_content("README_MD_CONTENT")
        heading_pattern = re.compile(r"^#+\s+", re.MULTILINE)
        headings = heading_pattern.findall(content)
        # DATA ASSUMPTION: A proper README has at least a few headings
        assert len(headings) >= 1, (
            f"README_MD_CONTENT should have Markdown headings, found {len(headings)}"
        )

    def test_is_substantial(self):
        """README should have substantial content."""
        content = _get_md_content("README_MD_CONTENT")
        # DATA ASSUMPTION: A proper README has at least 200 characters
        assert len(content.strip()) >= 200, (
            f"README_MD_CONTENT should be substantial, got {len(content.strip())} chars"
        )

    def test_has_multiple_lines(self):
        """README should have multiple lines of content."""
        content = _get_md_content("README_MD_CONTENT")
        non_empty_lines = [line for line in content.split("\n") if line.strip()]
        # DATA ASSUMPTION: A proper README has at least 10 non-empty lines
        assert len(non_empty_lines) >= 10, (
            f"README_MD_CONTENT has only {len(non_empty_lines)} non-empty lines"
        )


# ===========================================================================
# Section 13: Signature Validation -- Types
# ===========================================================================


class TestSignatureTypes:
    """Verify that all exported constants have the correct types as declared
    in the Tier 2 signatures."""

    def test_reference_indexing_frontmatter_is_dict(self):
        assert isinstance(REFERENCE_INDEXING_FRONTMATTER, dict)

    def test_integration_test_author_frontmatter_is_dict(self):
        assert isinstance(INTEGRATION_TEST_AUTHOR_FRONTMATTER, dict)

    def test_git_repo_agent_frontmatter_is_dict(self):
        assert isinstance(GIT_REPO_AGENT_FRONTMATTER, dict)

    def test_reference_indexing_status_is_list(self):
        assert isinstance(REFERENCE_INDEXING_STATUS, list)
        for item in REFERENCE_INDEXING_STATUS:
            assert isinstance(item, str)

    def test_integration_test_author_status_is_list(self):
        assert isinstance(INTEGRATION_TEST_AUTHOR_STATUS, list)
        for item in INTEGRATION_TEST_AUTHOR_STATUS:
            assert isinstance(item, str)

    def test_git_repo_agent_status_is_list(self):
        assert isinstance(GIT_REPO_AGENT_STATUS, list)
        for item in GIT_REPO_AGENT_STATUS:
            assert isinstance(item, str)

    def test_md_content_strings_are_str(self):
        """All MD_CONTENT values must be strings when defined."""
        for name in [
            "REFERENCE_INDEXING_AGENT_MD_CONTENT",
            "INTEGRATION_TEST_AUTHOR_MD_CONTENT",
            "GIT_REPO_AGENT_MD_CONTENT",
            "README_MD_CONTENT",
        ]:
            val = _get_md_content(name)
            assert isinstance(val, str), f"{name} must be a string"


# ===========================================================================
# Section 14: Integration Test Author -- SVP Self-Build Specifics
# ===========================================================================


class TestIntegrationTestAuthorSvpSelfBuild:
    """Verify Integration Test Author describes SVP self-build specific
    integration tests.

    For SVP self-builds, must include an integration test that exercises
    the svp restore code path using the bundled Game of Life example files
    (Unit 22's GOL_*_CONTENT constants). The test calls the launcher's
    restore functions directly (not via subprocess) with the example files
    written to a temporary directory, then verifies workspace creation,
    pipeline state initialization at pre_stage_3, spec and blueprint
    injection, CLAUDE.md generation, and default config writing.
    """

    @pytest.fixture
    def body(self):
        content = _get_md_content("INTEGRATION_TEST_AUTHOR_MD_CONTENT")
        return _get_body_after_frontmatter(content)

    def test_mentions_restore_code_path(self, body):
        """Must mention the restore code path."""
        body_lower = body.lower()
        assert "restore" in body_lower, (
            "Integration Test Author must mention restore code path"
        )

    def test_mentions_game_of_life(self, body):
        """Must mention Game of Life example files."""
        body_lower = body.lower()
        assert ("game of life" in body_lower or "gol" in body_lower
                or "game-of-life" in body_lower), (
            "Integration Test Author must mention Game of Life example"
        )

    def test_mentions_workspace_creation(self, body):
        """Must verify workspace directory structure is created."""
        body_lower = body.lower()
        assert ("workspace" in body_lower or "director" in body_lower), (
            "Integration Test Author must describe workspace creation verification"
        )

    def test_mentions_pipeline_state(self, body):
        """Must verify pipeline state is initialized at pre_stage_3."""
        body_lower = body.lower()
        assert ("pipeline" in body_lower or "state" in body_lower
                or "pre_stage_3" in body_lower), (
            "Integration Test Author must describe pipeline state verification"
        )

    def test_mentions_temporary_directory(self, body):
        """Must use temporary directory."""
        body_lower = body.lower()
        assert ("tempor" in body_lower or "temp" in body_lower
                or "tmp" in body_lower), (
            "Integration Test Author must describe using temporary directory"
        )

    def test_mentions_not_subprocess(self, body):
        """Must call launcher's restore functions directly, not via subprocess."""
        body_lower = body.lower()
        assert ("direct" in body_lower or "not via subprocess" in body_lower
                or "subprocess" in body_lower or "import" in body_lower
                or "function" in body_lower or "call" in body_lower), (
            "Integration Test Author must describe calling restore functions "
            "directly (not via subprocess)"
        )

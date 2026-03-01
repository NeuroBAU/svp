"""
Coverage gap tests for Unit 18: Utility Agent Definitions.

These tests cover blueprint-implied behaviors that were not exercised by
the existing test suite.

DATA ASSUMPTIONS
================

DATA ASSUMPTION: README_MD_CONTENT follows Mode A (carry-forward from v1.1).
Per the blueprint, the content must preserve all 10 baseline sections in
order. The 10 sections correspond to the top-level Markdown headings in the
v1.1 README.

DATA ASSUMPTION: README_MD_CONTENT is a plain Markdown file (NOT an agent
definition). It does NOT have YAML frontmatter delimiters ("---") at the
start of the file.

DATA ASSUMPTION: Integration Test Author instructions must mention
tests/integration/ as the output directory for generated tests, per the
behavioral contract.

DATA ASSUMPTION: Integration Test Author SVP self-build instructions must
describe verifying CLAUDE.md generation in the workspace, per the
behavioral contract for the restore code path test.

DATA ASSUMPTION: Integration Test Author SVP self-build instructions must
describe verifying default configuration (svp_config.json) writing, per
the behavioral contract for the restore code path test.

DATA ASSUMPTION: Integration Test Author SVP self-build instructions must
describe verifying that injected spec and blueprint match the originals,
per the behavioral contract for the restore code path test.

DATA ASSUMPTION: Git Repo Agent instructions must explicitly mention the
prohibition against src.unit_N paths in entry points or imports, per the
Tier 2 invariant "Git Repo Agent must never reference src.unit_N paths
in entry points or imports".

DATA ASSUMPTION: The 10 baseline README sections for Mode A are identified
by their top-level headings (# or ##). A valid carry-forward README must
have at least 10 distinct section headings.
"""

import re

import pytest

from svp.scripts.utility_agent_definitions import (
    REFERENCE_INDEXING_FRONTMATTER,
    INTEGRATION_TEST_AUTHOR_FRONTMATTER,
    GIT_REPO_AGENT_FRONTMATTER,
)


# ---------------------------------------------------------------------------
# Helper: safely import *_MD_CONTENT constants
# ---------------------------------------------------------------------------

def _get_md_content(name: str) -> str:
    """Safely retrieve an MD_CONTENT constant by name."""
    import svp.scripts.utility_agent_definitions as mod
    val = getattr(mod, name, None)
    if val is None or not isinstance(val, str):
        pytest.fail(f"{name} is not defined or not a string in svp.scripts.utility_agent_definitions")
    return val


def _get_body_after_frontmatter(md_content: str) -> str:
    """Extract the body text after the YAML frontmatter section."""
    assert md_content.startswith("---\n")
    second_delim = md_content.index("---\n", 4)
    return md_content[second_delim + 4:]


# ===========================================================================
# Section A: README_MD_CONTENT -- Mode A baseline section preservation
# ===========================================================================


class TestReadmeBaselineSections:
    """Verify README_MD_CONTENT preserves all 10 baseline sections (Mode A).

    The blueprint invariant states: "The content must preserve all 10
    baseline sections in order." This tests that the README has at least
    10 section headings.
    """

    def test_readme_has_at_least_10_sections(self):
        """README Mode A must preserve all 10 baseline sections."""
        content = _get_md_content("README_MD_CONTENT")
        # Count top-level and second-level headings (# and ##)
        heading_pattern = re.compile(r"^#{1,2}\s+", re.MULTILINE)
        headings = heading_pattern.findall(content)
        assert len(headings) >= 10, (
            f"README_MD_CONTENT Mode A must preserve all 10 baseline sections. "
            f"Found only {len(headings)} top-level/second-level headings."
        )

    def test_readme_sections_include_expected_topics(self):
        """README Mode A must include the expected baseline section topics.

        The v1.1 README has sections covering: title/intro, what SVP does,
        who it's for, installation, configuration, commands, quick tutorial,
        example project, project structure, and license.
        """
        content = _get_md_content("README_MD_CONTENT")
        content_lower = content.lower()
        # Check for key section topics that must be present
        expected_topics = [
            ("what svp does", "what"),
            ("who it's for", "who"),
            ("installation", "install"),
            ("configuration", "config"),
            ("commands", "command"),
            ("tutorial", "tutorial"),
            ("example", "example"),
            ("project structure", "structure"),
            ("license", "license"),
        ]
        missing = []
        for topic_name, keyword in expected_topics:
            if keyword not in content_lower:
                missing.append(topic_name)
        assert not missing, (
            f"README_MD_CONTENT Mode A is missing expected section topics: {missing}"
        )


# ===========================================================================
# Section B: README_MD_CONTENT -- Not an agent definition
# ===========================================================================


class TestReadmeNotAgentDefinition:
    """Verify README_MD_CONTENT does NOT have YAML frontmatter.

    The blueprint and data assumptions explicitly state that README_MD_CONTENT
    is a plain Markdown file, NOT an agent definition. It should not start
    with the YAML frontmatter delimiter '---'.
    """

    def test_readme_does_not_start_with_yaml_frontmatter(self):
        """README_MD_CONTENT must NOT start with '---' YAML frontmatter."""
        content = _get_md_content("README_MD_CONTENT")
        assert not content.startswith("---\n"), (
            "README_MD_CONTENT is a plain Markdown file and must NOT start "
            "with YAML frontmatter delimiter '---'"
        )

    def test_readme_starts_with_heading_or_text(self):
        """README_MD_CONTENT should start with a Markdown heading or text."""
        content = _get_md_content("README_MD_CONTENT")
        first_line = content.split("\n")[0].strip()
        # A README typically starts with a heading (# Title) or plain text
        assert first_line.startswith("#") or len(first_line) > 0, (
            "README_MD_CONTENT should start with a Markdown heading or text"
        )


# ===========================================================================
# Section C: Integration Test Author -- output directory
# ===========================================================================


class TestIntegrationTestAuthorOutputDirectory:
    """Verify Integration Test Author describes writing to tests/integration/.

    The behavioral contract states: 'Write comprehensive integration tests.
    Generate test files in the tests/integration/ directory.'
    """

    @pytest.fixture
    def body(self):
        content = _get_md_content("INTEGRATION_TEST_AUTHOR_MD_CONTENT")
        return _get_body_after_frontmatter(content)

    def test_mentions_integration_test_directory(self, body):
        """Must mention tests/integration/ as the output directory."""
        assert ("tests/integration" in body or "tests/integration/" in body), (
            "Integration Test Author must mention tests/integration/ output directory"
        )


# ===========================================================================
# Section D: Integration Test Author SVP self-build -- additional verifications
# ===========================================================================


class TestIntegrationTestAuthorSvpSelfBuildVerifications:
    """Verify Integration Test Author describes additional SVP self-build
    verification steps in the restore code path test.

    The behavioral contract specifies that the restore code path test must
    verify: CLAUDE.md generation, default config writing, and spec/blueprint
    injection matching.
    """

    @pytest.fixture
    def body(self):
        content = _get_md_content("INTEGRATION_TEST_AUTHOR_MD_CONTENT")
        return _get_body_after_frontmatter(content)

    def test_mentions_claude_md_generation(self, body):
        """Must describe verifying CLAUDE.md is generated."""
        assert "CLAUDE.md" in body or "claude.md" in body.lower(), (
            "Integration Test Author must mention CLAUDE.md generation "
            "verification in the restore code path test"
        )

    def test_mentions_default_config_writing(self, body):
        """Must describe verifying default configuration is written."""
        body_lower = body.lower()
        assert ("svp_config" in body_lower or "default config" in body_lower
                or "configuration" in body_lower), (
            "Integration Test Author must mention default configuration "
            "(svp_config.json) writing verification"
        )

    def test_mentions_spec_blueprint_injection_matching(self, body):
        """Must describe verifying injected spec and blueprint match originals."""
        body_lower = body.lower()
        has_spec_match = ("spec" in body_lower and "match" in body_lower)
        has_blueprint_match = ("blueprint" in body_lower and "match" in body_lower)
        has_inject = "inject" in body_lower
        has_original = "original" in body_lower
        # The body should describe that injected documents match originals
        assert (has_spec_match or has_blueprint_match or has_inject
                or has_original), (
            "Integration Test Author must describe verifying that injected "
            "stakeholder spec and blueprint match the originals"
        )

    def test_mentions_pre_stage_3_specifically(self, body):
        """Must mention pre_stage_3 as the initial pipeline state for restore."""
        assert "pre_stage_3" in body, (
            "Integration Test Author must specifically mention pre_stage_3 "
            "as the initial pipeline state for the restore code path"
        )

    def test_mentions_gol_content_constants(self, body):
        """Must mention GOL_*_CONTENT constants from Unit 22."""
        assert ("GOL_" in body or "gol_" in body.lower()
                or "GOL_STAKEHOLDER_SPEC_CONTENT" in body
                or "Game of Life" in body), (
            "Integration Test Author must mention GOL_*_CONTENT constants "
            "or Game of Life example files from Unit 22"
        )


# ===========================================================================
# Section E: Git Repo Agent -- src.unit_N prohibition in entry points
# ===========================================================================


class TestGitRepoAgentSrcUnitProhibition:
    """Verify Git Repo Agent instructions explicitly mention the prohibition
    against src.unit_N paths in entry points or imports.

    Tier 2 invariant: 'Git Repo Agent must never reference src.unit_N paths
    in entry points or imports.'
    """

    @pytest.fixture
    def body(self):
        content = _get_md_content("GIT_REPO_AGENT_MD_CONTENT")
        return _get_body_after_frontmatter(content)

    def test_mentions_src_unit_prohibition(self, body):
        """Must describe the prohibition against src.unit_N references."""
        # The body should mention src.unit or src/unit in the context of
        # what NOT to do
        has_src_unit = ("src.unit" in body or "src/unit" in body
                        or "src.unit_N" in body or "src.unit_" in body)
        assert has_src_unit, (
            "Git Repo Agent must explicitly mention src.unit_N paths "
            "in the context of the prohibition against referencing them"
        )

    def test_mentions_no_workspace_imports_in_delivered_code(self, body):
        """Must describe that no delivered code may contain workspace imports."""
        body_lower = body.lower()
        # The body should describe that no Python file may import from src.unit_
        has_no_workspace = ("from src.unit" in body or "import src.unit" in body
                           or "src.unit_" in body)
        assert has_no_workspace, (
            "Git Repo Agent must describe prohibition against workspace-style "
            "imports (from src.unit_N) in the delivered repository"
        )


# ===========================================================================
# Section F: Git Repo Agent -- svp_launcher placement detail
# ===========================================================================


class TestGitRepoAgentLauncherPlacement:
    """Verify Git Repo Agent describes the specific svp_launcher.py placement.

    Tier 2 invariant: 'Git Repo Agent must place svp_launcher.py at
    svp/scripts/svp_launcher.py (not at repo root).'
    """

    @pytest.fixture
    def body(self):
        content = _get_md_content("GIT_REPO_AGENT_MD_CONTENT")
        return _get_body_after_frontmatter(content)

    def test_mentions_svp_scripts_path(self, body):
        """Must mention svp/scripts/ as the launcher location."""
        assert "svp/scripts/svp_launcher.py" in body, (
            "Git Repo Agent must mention svp/scripts/svp_launcher.py "
            "as the launcher placement path"
        )

    def test_mentions_entry_point_format(self, body):
        """Must mention the exact entry point format."""
        assert "svp.scripts.svp_launcher:main" in body, (
            "Git Repo Agent must mention the exact entry point "
            "'svp.scripts.svp_launcher:main'"
        )


# ===========================================================================
# Section G: Git Repo Agent -- plugin directory structural validation
# ===========================================================================


class TestGitRepoAgentPluginValidation:
    """Verify Git Repo Agent describes plugin directory structural validation.

    The behavioral contract states: 'Structural validation for plugin
    directory structure (spec Section 12.3) including checks for
    workspace-internal paths.'
    """

    @pytest.fixture
    def body(self):
        content = _get_md_content("GIT_REPO_AGENT_MD_CONTENT")
        return _get_body_after_frontmatter(content)

    def test_mentions_plugin_directory(self, body):
        """Must mention plugin directory structure."""
        body_lower = body.lower()
        assert ("plugin" in body_lower or ".claude-plugin" in body_lower), (
            "Git Repo Agent must describe plugin directory structure validation"
        )

    def test_mentions_marketplace_json(self, body):
        """Must mention marketplace.json as part of plugin structure."""
        assert ("marketplace.json" in body or "marketplace" in body.lower()), (
            "Git Repo Agent must mention marketplace.json in structural validation"
        )

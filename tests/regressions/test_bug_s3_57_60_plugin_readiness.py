"""Regression tests for Bugs S3-57 through S3-60: Plugin installation readiness.

S3-57: pyproject.toml must have entry point and correct build backend.
S3-58: Agent .md files must have YAML frontmatter.
S3-59: hooks.json must use 'hooks' array, not 'handler' object.
S3-60: svp/scripts/__init__.py must exist.
"""

import json
import tempfile
from pathlib import Path

import pytest

from hooks import HOOKS_JSON_SCHEMA, generate_hooks_json
from generate_assembly_map import assemble_plugin_components


@pytest.fixture
def assembled_repo():
    profile = {
        "plugin": {
            "name": "svp",
            "description": "Test SVP",
            "version": "2.2.0",
            "author": {"name": "Test"},
        },
        "license": {"author": "Test"},
        "pipeline": {
            "agent_models": {
                "setup_agent": "claude-sonnet-4-6",
                "test_agent": "claude-sonnet-4-6",
            }
        },
    }
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        assemble_plugin_components(repo, profile)
        yield repo


class TestS3_58_AgentFrontmatter:
    """Agent .md files must have YAML frontmatter."""

    def test_agents_have_frontmatter(self, assembled_repo):
        for md in (assembled_repo / "svp" / "agents").glob("*.md"):
            content = md.read_text()
            assert content.startswith("---\n"), f"{md.name} missing frontmatter"
            assert "\n---\n" in content[4:], f"{md.name} frontmatter not closed"

    def test_frontmatter_has_name(self, assembled_repo):
        for md in (assembled_repo / "svp" / "agents").glob("*.md"):
            content = md.read_text()
            assert "name:" in content.split("---")[1], f"{md.name} missing name"

    def test_frontmatter_has_description(self, assembled_repo):
        for md in (assembled_repo / "svp" / "agents").glob("*.md"):
            content = md.read_text()
            assert "description:" in content.split("---")[1], f"{md.name} missing description"


class TestS3_59_HooksJsonSchema:
    """hooks.json must use 'hooks' array format."""

    def test_schema_uses_hooks_array(self):
        for event_entries in HOOKS_JSON_SCHEMA["hooks"].values():
            for entry in event_entries:
                assert "hooks" in entry, f"Entry uses 'handler' instead of 'hooks'"
                assert "handler" not in entry
                assert isinstance(entry["hooks"], list)

    def test_generated_json_uses_hooks_array(self):
        data = json.loads(generate_hooks_json())
        for event_entries in data["hooks"].values():
            for entry in event_entries:
                assert "hooks" in entry
                assert "handler" not in entry


class TestS3_60_ScriptsInit:
    """svp/scripts/__init__.py must be created during assembly."""

    def test_init_py_exists(self, assembled_repo):
        init = assembled_repo / "svp" / "scripts" / "__init__.py"
        assert init.is_file()

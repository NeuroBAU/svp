"""Regression tests for Bug S3-56: Plugin manifest path format.

Verifies that marketplace.json source field uses './svp' (not './')
and that plugin.json path fields use './' prefix per Claude Code spec.
"""

import json

import pytest

from structural_check import generate_marketplace_json, generate_plugin_json


@pytest.fixture
def valid_profile():
    return {
        "plugin": {
            "name": "svp",
            "description": "Test plugin",
            "version": "2.2.0",
            "author": {"name": "Test"},
            "commands": "./commands/",
            "agents": "./agents/",
            "skills": "./skills/",
            "hooks": "./hooks/",
        },
        "license": {"author": "Test"},
    }


class TestS3_56_MarketplaceSource:
    """marketplace.json source must point to plugin subdirectory."""

    def test_source_is_dot_slash_name(self, valid_profile):
        """source field must be './svp', not './'."""
        result = json.loads(generate_marketplace_json(valid_profile))
        assert result["plugins"][0]["source"] == "./svp"

    def test_source_not_bare_dot_slash(self, valid_profile):
        """source field must NOT be './'."""
        result = json.loads(generate_marketplace_json(valid_profile))
        assert result["plugins"][0]["source"] != "./"

    def test_source_matches_plugin_name(self):
        """source field uses the plugin name from profile."""
        profile = {
            "plugin": {
                "name": "my-plugin",
                "description": "Test",
                "version": "1.0.0",
            },
            "license": {"author": "Test"},
        }
        result = json.loads(generate_marketplace_json(profile))
        assert result["plugins"][0]["source"] == "./my-plugin"


class TestS3_56_PluginJsonPaths:
    """plugin.json path fields must use './' prefix."""

    def test_path_fields_have_dot_slash_prefix(self, valid_profile):
        """All path fields start with './'."""
        result = json.loads(generate_plugin_json(valid_profile))
        for key in ("commands", "agents", "skills", "hooks"):
            if key in result:
                assert result[key].startswith("./"), (
                    f"{key} = '{result[key]}' missing './' prefix"
                )

    def test_bare_paths_not_accepted(self):
        """Path fields without './' prefix should not appear in output."""
        profile = {
            "plugin": {
                "name": "svp",
                "description": "Test",
                "version": "1.0.0",
                "commands": "./commands/",
            },
        }
        result = json.loads(generate_plugin_json(profile))
        if "commands" in result:
            assert not result["commands"].startswith("commands")

"""Regression tests for Bug S3-53: Plugin manifest empty fields.

Verifies that generate_plugin_json() and generate_marketplace_json()
raise ValueError when required fields resolve to empty strings, and
produce valid output when the profile has a proper plugin section.
"""

import json

import pytest

from src.unit_28.stub import generate_marketplace_json, generate_plugin_json


class TestS3_53_PluginManifestValidation:
    """Bug S3-53: manifest generation must reject empty required fields."""

    def test_plugin_json_empty_profile_raises(self):
        """generate_plugin_json with no plugin section raises ValueError."""
        with pytest.raises(ValueError, match="required fields empty"):
            generate_plugin_json({})

    def test_plugin_json_empty_name_raises(self):
        """generate_plugin_json with empty name raises ValueError."""
        profile = {"plugin": {"name": "", "description": "test"}}
        with pytest.raises(ValueError, match="required fields empty"):
            generate_plugin_json(profile)

    def test_plugin_json_empty_description_raises(self):
        """generate_plugin_json with empty description raises ValueError."""
        profile = {"plugin": {"name": "test", "description": ""}}
        with pytest.raises(ValueError, match="required fields empty"):
            generate_plugin_json(profile)

    def test_marketplace_json_empty_profile_raises(self):
        """generate_marketplace_json with no plugin section raises ValueError."""
        with pytest.raises(ValueError, match="'name' field is empty"):
            generate_marketplace_json({})

    def test_plugin_json_valid_profile(self):
        """generate_plugin_json with proper plugin section produces valid output."""
        profile = {
            "plugin": {
                "name": "svp",
                "description": "Test plugin",
                "version": "1.0.0",
                "author": {"name": "Test Author"},
            }
        }
        result = json.loads(generate_plugin_json(profile))
        assert result["name"] == "svp"
        assert result["description"] == "Test plugin"
        assert result["version"] == "1.0.0"
        assert result["author"]["name"] == "Test Author"

    def test_marketplace_json_valid_profile(self):
        """generate_marketplace_json with proper plugin section produces valid output."""
        profile = {
            "plugin": {
                "name": "svp",
                "description": "Test plugin",
                "version": "1.0.0",
                "author": "Test Author",
            },
            "license": {"author": "Test Owner"},
        }
        result = json.loads(generate_marketplace_json(profile))
        assert result["name"] == "svp"
        assert result["owner"]["name"] == "Test Owner"
        assert len(result["plugins"]) == 1
        assert result["plugins"][0]["name"] == "svp"
        assert result["plugins"][0]["description"] == "Test plugin"

    def test_marketplace_json_no_empty_required_fields(self):
        """Valid marketplace.json has no empty string required fields."""
        profile = {
            "plugin": {
                "name": "svp",
                "description": "Test",
                "version": "1.0.0",
                "author": "Author",
            },
            "license": {"author": "Owner"},
        }
        result = json.loads(generate_marketplace_json(profile))
        assert result["name"] != ""
        assert result["plugins"][0]["name"] != ""

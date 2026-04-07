"""Regression tests for Bug S3-51: Plugin manifest string path fields rejected.

Claude Code's Zod schema validator rejects string directory paths for hooks
and agents in plugin.json. These fields are auto-discovered by convention.

Covers:
- validate_plugin_manifest rejects hooks as string path
- validate_plugin_manifest warns about agents/commands/skills as string paths
- generate_plugin_json excludes auto-discovered directory fields
- generate_plugin_json excludes hooks when passed as string path
- generated manifest with inline hooks object passes validation
"""

import json

import pytest

from structural_check import generate_plugin_json, validate_plugin_manifest


def _minimal_profile():
    return {
        "name": "test-plugin",
        "description": "Test plugin",
        "version": "1.0.0",
        "author": "Test Author",
    }


class TestBugS3_51_ManifestStringPaths:
    """Bug S3-51: String directory paths in plugin.json cause install failure."""

    def test_validate_rejects_hooks_as_string_path(self):
        """hooks as string path must produce validation error."""
        manifest = {
            "name": "test",
            "description": "test",
            "version": "1.0.0",
            "author": "test",
            "hooks": "./hooks/",
        }
        errors = validate_plugin_manifest(manifest)
        assert any("hooks" in e and "object" in e for e in errors), (
            f"Expected error about hooks being string, got: {errors}"
        )

    def test_validate_rejects_hooks_as_file_path(self):
        """hooks as string file path must also produce validation error."""
        manifest = {
            "name": "test",
            "description": "test",
            "version": "1.0.0",
            "author": "test",
            "hooks": "hooks.json",
        }
        errors = validate_plugin_manifest(manifest)
        assert any("hooks" in e and "object" in e for e in errors)

    def test_validate_warns_agents_as_string(self):
        """agents as string path must produce validation error."""
        manifest = {
            "name": "test",
            "description": "test",
            "version": "1.0.0",
            "author": "test",
            "agents": "./agents/",
        }
        errors = validate_plugin_manifest(manifest)
        assert any("agents" in e and "auto-discover" in e.lower() for e in errors)

    def test_validate_warns_commands_as_string(self):
        """commands as string path must produce validation error."""
        manifest = {
            "name": "test",
            "description": "test",
            "version": "1.0.0",
            "author": "test",
            "commands": "./commands/",
        }
        errors = validate_plugin_manifest(manifest)
        assert any("commands" in e and "auto-discover" in e.lower() for e in errors)

    def test_validate_warns_skills_as_string(self):
        """skills as string path must produce validation error."""
        manifest = {
            "name": "test",
            "description": "test",
            "version": "1.0.0",
            "author": "test",
            "skills": "./skills/",
        }
        errors = validate_plugin_manifest(manifest)
        assert any("skills" in e and "auto-discover" in e.lower() for e in errors)

    def test_validate_accepts_hooks_as_object(self):
        """hooks as inline object must pass validation."""
        manifest = {
            "name": "test",
            "description": "test",
            "version": "1.0.0",
            "author": "test",
            "hooks": {"PreToolUse": [{"matcher": "Write", "hooks": []}]},
        }
        errors = validate_plugin_manifest(manifest)
        assert not any("hooks" in e for e in errors), (
            f"hooks as object should not produce errors, got: {errors}"
        )

    def test_generate_excludes_agents_from_output(self):
        """generate_plugin_json must not emit agents field."""
        profile = {**_minimal_profile(), "agents": "./agents/"}
        parsed = json.loads(generate_plugin_json(profile))
        assert "agents" not in parsed

    def test_generate_excludes_commands_from_output(self):
        """generate_plugin_json must not emit commands field."""
        profile = {**_minimal_profile(), "commands": "./commands/"}
        parsed = json.loads(generate_plugin_json(profile))
        assert "commands" not in parsed

    def test_generate_excludes_skills_from_output(self):
        """generate_plugin_json must not emit skills field."""
        profile = {**_minimal_profile(), "skills": "./skills/"}
        parsed = json.loads(generate_plugin_json(profile))
        assert "skills" not in parsed

    def test_generate_excludes_hooks_string_path(self):
        """generate_plugin_json must not emit hooks when it's a string path."""
        profile = {**_minimal_profile(), "hooks": "./hooks/"}
        parsed = json.loads(generate_plugin_json(profile))
        assert "hooks" not in parsed

    def test_generate_includes_hooks_inline_object(self):
        """generate_plugin_json must emit hooks when it's an inline object."""
        hooks_obj = {"PreToolUse": [{"matcher": "Write", "hooks": []}]}
        profile = {**_minimal_profile(), "hooks": hooks_obj}
        parsed = json.loads(generate_plugin_json(profile))
        assert "hooks" in parsed
        assert parsed["hooks"] == hooks_obj

    def test_minimal_manifest_passes_validation(self):
        """Manifest with only required fields must pass validation."""
        manifest = {
            "name": "svp",
            "description": "Stratified Verification Pipeline",
            "version": "2.2.0",
            "author": {"name": "Test Author"},
        }
        errors = validate_plugin_manifest(manifest)
        assert errors == []

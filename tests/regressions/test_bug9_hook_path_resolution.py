"""Regression test for Bug 9: Hook scripts unreachable due to wrong relative path.

Bug: Hook commands in HOOKS_JSON_CONTENT and hooks.json used paths like
"bash scripts/write_authorization.sh" which resolve to the pipeline scripts
directory, not ".claude/scripts/" where hook shell scripts actually reside.
This caused both security hooks to silently fail with exit code 127.

These tests verify that:
1. HOOKS_JSON_CONTENT uses .claude/scripts/ paths (hook_configurations)
2. HOOKS_JSON_SCHEMA uses .claude/scripts/ paths (hook_configurations)
3. _copy_hooks rewrites script paths to .claude/scripts/ (svp_launcher)
"""

import json
from pathlib import Path

import pytest

from svp.scripts.hook_configurations import (
    HOOKS_JSON_CONTENT,
    HOOKS_JSON_SCHEMA,
    _hooks_json_data,
)
from svp.scripts.svp_launcher import _copy_hooks


class TestHookConfigurationPaths:
    """Verify hook configurations use .claude/scripts/ paths."""

    def test_hooks_json_content_write_auth_path(self):
        """HOOKS_JSON_CONTENT write authorization command uses .claude/scripts/ path."""
        data = json.loads(HOOKS_JSON_CONTENT)
        write_hook = data["hooks"]["PreToolUse"][0]["hooks"][0]
        assert ".claude/scripts/write_authorization.sh" in write_hook["command"]

    def test_hooks_json_content_non_svp_path(self):
        """HOOKS_JSON_CONTENT non-SVP protection command uses .claude/scripts/ path."""
        data = json.loads(HOOKS_JSON_CONTENT)
        bash_hook = data["hooks"]["PreToolUse"][1]["hooks"][0]
        assert ".claude/scripts/non_svp_protection.sh" in bash_hook["command"]

    def test_hooks_json_content_no_bare_scripts_path(self):
        """HOOKS_JSON_CONTENT must not contain bare 'scripts/' paths (without .claude/ prefix)."""
        data = json.loads(HOOKS_JSON_CONTENT)
        for hook_group in data["hooks"]["PreToolUse"]:
            for hook_entry in hook_group["hooks"]:
                cmd = hook_entry.get("command", "")
                if "scripts/" in cmd:
                    assert ".claude/scripts/" in cmd, (
                        f"Hook command uses bare 'scripts/' path without .claude/ prefix: {cmd}"
                    )

    def test_hooks_json_schema_write_auth_path(self):
        """HOOKS_JSON_SCHEMA write authorization script uses .claude/scripts/ path."""
        entry = HOOKS_JSON_SCHEMA["hooks"]["PreToolUse"][0]
        assert entry["script"] == ".claude/scripts/write_authorization.sh"

    def test_hooks_json_schema_non_svp_path(self):
        """HOOKS_JSON_SCHEMA non-SVP protection script uses .claude/scripts/ path."""
        entry = HOOKS_JSON_SCHEMA["hooks"]["PreToolUse"][1]
        assert entry["script"] == ".claude/scripts/non_svp_protection.sh"


class TestCopyHooksPathRewriting:
    """Verify _copy_hooks rewrites script paths to .claude/scripts/."""

    def test_rewrites_bare_scripts_path(self, tmp_path):
        """_copy_hooks rewrites 'bash scripts/foo.sh' to 'bash .claude/scripts/foo.sh'."""
        plugin_root = tmp_path / "plugin"
        project_root = tmp_path / "project"
        hooks_dir = plugin_root / "hooks"
        hooks_dir.mkdir(parents=True)
        hooks_scripts = hooks_dir / "scripts"
        hooks_scripts.mkdir()
        (hooks_scripts / "write_authorization.sh").write_text("#!/bin/bash\nexit 0")
        (hooks_scripts / "non_svp_protection.sh").write_text("#!/bin/bash\nexit 0")

        old_hooks = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Write|Edit|MultiEdit|Create",
                        "hooks": [{"type": "command", "command": "bash scripts/write_authorization.sh"}],
                    },
                    {
                        "matcher": "Bash",
                        "hooks": [{"type": "command", "command": "bash scripts/non_svp_protection.sh"}],
                    },
                ]
            }
        }
        (hooks_dir / "hooks.json").write_text(json.dumps(old_hooks))

        project_root.mkdir(parents=True)
        _copy_hooks(plugin_root, project_root)

        result = json.loads((project_root / ".claude" / "hooks.json").read_text())
        write_cmd = result["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        bash_cmd = result["hooks"]["PreToolUse"][1]["hooks"][0]["command"]
        assert write_cmd == "bash .claude/scripts/write_authorization.sh"
        assert bash_cmd == "bash .claude/scripts/non_svp_protection.sh"

    def test_preserves_correct_paths(self, tmp_path):
        """_copy_hooks preserves already-correct .claude/scripts/ paths."""
        plugin_root = tmp_path / "plugin"
        project_root = tmp_path / "project"
        hooks_dir = plugin_root / "hooks"
        hooks_dir.mkdir(parents=True)
        hooks_scripts = hooks_dir / "scripts"
        hooks_scripts.mkdir()
        (hooks_scripts / "write_authorization.sh").write_text("#!/bin/bash\nexit 0")

        correct_hooks = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Write|Edit|MultiEdit|Create",
                        "hooks": [{"type": "command", "command": "bash .claude/scripts/write_authorization.sh"}],
                    },
                ]
            }
        }
        (hooks_dir / "hooks.json").write_text(json.dumps(correct_hooks))

        project_root.mkdir(parents=True)
        _copy_hooks(plugin_root, project_root)

        result = json.loads((project_root / ".claude" / "hooks.json").read_text())
        cmd = result["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        assert cmd == "bash .claude/scripts/write_authorization.sh"

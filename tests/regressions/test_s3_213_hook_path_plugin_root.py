"""Regression tests for Bug S3-213 -- plugin hook commands anchored to
${CLAUDE_PLUGIN_ROOT}.

The SVP plugin's hooks.json previously used bare relative ``.claude/scripts/X.sh``
commands, which resolve against the session CWD and miss when the SVP project is
opened as a subdirectory below the session root (silently disabling the
non_svp_protection guard and emitting a noisy "No such file or directory" on every
Bash call). ``${CLAUDE_PLUGIN_ROOT}`` points to the plugin's own install dir and is
CWD/nesting-agnostic; the scripts ship inside the plugin at ``svp/hooks/*.sh``.
"""

from __future__ import annotations

import hooks
from hooks import HOOKS_JSON_SCHEMA, generate_hooks_json

_EXPECTED_SCRIPTS = {
    "write_authorization.sh",
    "non_svp_protection.sh",
    "stub_sentinel_check.sh",
    "monitoring_reminder.sh",
}


def _all_commands():
    cmds = []
    for hook_type in ("PreToolUse", "PostToolUse"):
        for entry in HOOKS_JSON_SCHEMA["hooks"][hook_type]:
            for handler in entry["hooks"]:
                cmds.append(handler["command"])
    return cmds


def test_s3_213_all_commands_use_plugin_root_hooks_anchor():
    cmds = _all_commands()
    assert len(cmds) == 4
    for cmd in cmds:
        assert cmd.startswith("${CLAUDE_PLUGIN_ROOT}/hooks/"), cmd
        assert ".claude/scripts/" not in cmd, cmd


def test_s3_213_every_expected_script_is_referenced():
    referenced = {cmd.rsplit("/", 1)[-1] for cmd in _all_commands()}
    assert referenced == _EXPECTED_SCRIPTS


def test_s3_213_no_bare_relative_path_anywhere_in_generated_json():
    rendered = generate_hooks_json()
    assert ".claude/scripts/" not in rendered
    assert rendered.count("${CLAUDE_PLUGIN_ROOT}/hooks/") == 4


def test_s3_213_generate_hooks_json_roundtrips_to_schema():
    import json

    assert json.loads(generate_hooks_json()) == HOOKS_JSON_SCHEMA

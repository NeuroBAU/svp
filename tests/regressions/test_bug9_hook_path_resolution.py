"""Bug 9 regression: Hook script paths must resolve correctly.

Hook configurations must reference scripts at .claude/scripts/ paths,
not absolute or plugin-relative paths.
"""

from hooks import HOOKS_JSON_SCHEMA


def test_write_authorization_path():
    """Write authorization hook must use .claude/scripts/ path."""
    hooks = HOOKS_JSON_SCHEMA["hooks"]["PreToolUse"]
    write_hook = next(h for h in hooks if h["matcher"] == "Write")
    command = write_hook["hooks"][0]["command"]
    assert command == ".claude/scripts/write_authorization.sh"


def test_non_svp_protection_path():
    """Non-SVP protection hook must use .claude/scripts/ path."""
    hooks = HOOKS_JSON_SCHEMA["hooks"]["PreToolUse"]
    bash_hook = next(h for h in hooks if h["matcher"] == "Bash")
    command = bash_hook["hooks"][0]["command"]
    assert command == ".claude/scripts/non_svp_protection.sh"

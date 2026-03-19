"""Bug 13 regression: Hook JSON schema must use type 'command', not 'bash'.

The hook configuration schema must specify type: "command" for all hooks,
not type: "bash" which was an incorrect value.
"""

from hooks import HOOKS_JSON_SCHEMA


def test_all_hooks_use_command_type():
    """Every hook entry must have type == 'command'."""
    for matcher_entry in HOOKS_JSON_SCHEMA["hooks"]["PreToolUse"]:
        for hook in matcher_entry["hooks"]:
            assert hook["type"] == "command", (
                f"Hook for matcher '{matcher_entry['matcher']}' uses "
                f"type '{hook['type']}' instead of 'command'"
            )


def test_no_bash_type_in_hooks():
    """No hook should use type 'bash'."""
    for matcher_entry in HOOKS_JSON_SCHEMA["hooks"]["PreToolUse"]:
        for hook in matcher_entry["hooks"]:
            assert hook["type"] != "bash", "Hook type must not be 'bash'"

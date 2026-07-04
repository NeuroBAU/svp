"""Bug 9 regression: Hook script paths must resolve correctly.

Hook configurations must reference scripts by a path that resolves regardless of
the session's working directory. **(SUPERSEDED IN 2.2 -- Bug S3-213.)** The
original Bug-9 rule preferred a bare relative ``.claude/scripts/`` path; the
Claude Code hooks docs confirm hook commands resolve against the session CWD, so
that path misses when the SVP project is opened as a subdirectory below the
session root (and ``${CLAUDE_PROJECT_DIR}`` is the session launch dir, not the
managed project, so it does not fix it either). The scripts ship inside the
plugin at ``svp/hooks/*.sh``, so the CWD/nesting-agnostic anchor is
``${CLAUDE_PLUGIN_ROOT}/hooks/``.
"""

from hooks import HOOKS_JSON_SCHEMA


def test_write_authorization_path():
    """Write authorization hook uses the ${CLAUDE_PLUGIN_ROOT}/hooks/ anchor."""
    hooks = HOOKS_JSON_SCHEMA["hooks"]["PreToolUse"]
    write_hook = next(h for h in hooks if h["matcher"] == "Write")
    command = write_hook["hooks"][0]["command"]
    assert command == "${CLAUDE_PLUGIN_ROOT}/hooks/write_authorization.sh"


def test_non_svp_protection_path():
    """Non-SVP protection hook uses the ${CLAUDE_PLUGIN_ROOT}/hooks/ anchor."""
    hooks = HOOKS_JSON_SCHEMA["hooks"]["PreToolUse"]
    bash_hook = next(h for h in hooks if h["matcher"] == "Bash")
    command = bash_hook["hooks"][0]["command"]
    assert command == "${CLAUDE_PLUGIN_ROOT}/hooks/non_svp_protection.sh"

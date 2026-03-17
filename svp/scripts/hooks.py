# Unit 12: Hook Configurations
"""JSON hook schema, shell script string constants, and hook-logic functions."""

import json
import os
from typing import Any, Dict

SVP_ENV_VAR: str = "SVP_PLUGIN_ACTIVE"

HOOKS_JSON_SCHEMA: Dict[str, Any] = {
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": (".claude/scripts/write_authorization.sh"),
                    }
                ],
            },
            {
                "matcher": "Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": (".claude/scripts/non_svp_protection.sh"),
                    }
                ],
            },
        ],
        "PostToolUse": [
            {
                "matcher": "Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": (".claude/scripts/stub_sentinel_check.sh"),
                    }
                ],
            },
        ],
    }
}

HOOKS_JSON_CONTENT: str = json.dumps(HOOKS_JSON_SCHEMA, indent=2)

WRITE_AUTHORIZATION_SH_CONTENT: str = """\
#!/usr/bin/env bash
# write_authorization.sh
# PreToolUse hook: controls write access by stage.
#
# Receives: $TOOL_INPUT (JSON with file_path)
# Exit 0 = allow, Exit 2 = block

set -euo pipefail

FILE_PATH=$(echo "$TOOL_INPUT" | \
  python3 -c "import sys,json; \
  print(json.load(sys.stdin).get('file_path',''))")

# Infrastructure paths: always writable
case "$FILE_PATH" in
  .svp/*|.svp) exit 0 ;;
  scripts/*) exit 0 ;;
  ledgers/*) exit 0 ;;
  logs/*) exit 0 ;;
esac

STATE_FILE="pipeline_state.json"

# Read current stage and sub_stage
if [ -f "$STATE_FILE" ]; then
  STAGE=$(python3 -c "import json; \
    d=json.load(open('$STATE_FILE')); \
    print(d.get('stage',''))")
  SUB_STAGE=$(python3 -c "import json; \
    d=json.load(open('$STATE_FILE')); \
    print(d.get('sub_stage','') or '')")
  DEBUG_AUTH=$(python3 -c "import json; \
    d=json.load(open('$STATE_FILE')); \
    ds=d.get('debug_session'); \
    print('true' if ds and \
    ds.get('authorized') else 'false')")
  DELIVERED=$(python3 -c "import json; \
    d=json.load(open('$STATE_FILE')); \
    print(d.get('delivered_repo_path','') or '')")
else
  STAGE=""
  SUB_STAGE=""
  DEBUG_AUTH="false"
  DELIVERED=""
fi

# toolchain.json: permanently read-only
case "$FILE_PATH" in
  toolchain.json)
    echo "BLOCKED: toolchain.json is read-only"
    exit 2
    ;;
esac

# ruff.toml: permanently read-only
case "$FILE_PATH" in
  ruff.toml)
    echo "BLOCKED: ruff.toml is read-only"
    exit 2
    ;;
esac

# project_profile.json: writable only during
# project_profile or redo profile sub-stages
case "$FILE_PATH" in
  project_profile.json)
    if [ "$SUB_STAGE" = "project_profile" ] || \
       [ "$SUB_STAGE" = "redo_profile_delivery" ] || \
       [ "$SUB_STAGE" = "redo_profile_blueprint" ]; then
      exit 0
    fi
    echo "BLOCKED: profile not writable in $SUB_STAGE"
    exit 2
    ;;
esac

# delivered_repo_path: writable during debug
if [ -n "$DELIVERED" ]; then
  case "$FILE_PATH" in
    "$DELIVERED"/*)
      if [ "$DEBUG_AUTH" = "true" ]; then
        exit 0
      fi
      echo "BLOCKED: delivered repo not authorized"
      exit 2
      ;;
  esac
fi

# lessons learned: writable during debug
case "$FILE_PATH" in
  *lessons_learned*)
    if [ "$DEBUG_AUTH" = "true" ]; then
      exit 0
    fi
    echo "BLOCKED: lessons learned not authorized"
    exit 2
    ;;
esac

# Bug 55: triage_result.json writable during triage phases
case "$FILE_PATH" in
  .svp/triage_result.json|.svp/triage_scratch/*)
    if [ "$DEBUG_AUTH" = "true" ]; then
      exit 0
    fi
    ;;
esac

# Project artifact paths: state-gated
case "$FILE_PATH" in
  specs/*|blueprint/*|src/*|tests/*|data/*|\
references/*)
    exit 0
    ;;
esac

# Default: allow
exit 0
"""

NON_SVP_PROTECTION_SH_CONTENT: str = """\
#!/usr/bin/env bash
# non_svp_protection.sh
# PreToolUse hook: blocks Bash commands when
# SVP_PLUGIN_ACTIVE is not set.
#
# Exit 0 = allow, Exit 2 = block

set -euo pipefail

if [ "${SVP_PLUGIN_ACTIVE:-}" != "1" ]; then
  echo "BLOCKED: Not an SVP session."
  echo "Set SVP_PLUGIN_ACTIVE=1 to enable."
  exit 2
fi

exit 0
"""

STUB_SENTINEL_CHECK_SH_CONTENT: str = """\
#!/usr/bin/env bash
# stub_sentinel_check.sh
# PostToolUse hook: checks for __SVP_STUB__ sentinel
# in files written to src/unit_N/ paths.
#
# Exit 0 = ok, Exit 2 = sentinel found

set -euo pipefail

FILE_PATH=$(echo "$TOOL_INPUT" | \
  python3 -c "import sys,json; \
  print(json.load(sys.stdin).get('file_path',''))")

# Only check src/unit_* paths
case "$FILE_PATH" in
  src/unit_*)
    ;;
  *)
    exit 0
    ;;
esac

if [ -f "$FILE_PATH" ]; then
  if grep -q "__SVP_STUB__" "$FILE_PATH"; then
    echo "ERROR: __SVP_STUB__ sentinel in $FILE_PATH"
    echo "Remove sentinel before delivery."
    exit 2
  fi
fi

exit 0
"""


def check_write_authorization(
    tool_name: str,
    file_path: str,
    pipeline_state_path: str,
) -> int:
    """Check if a write is authorized.

    Returns 0 for allowed, 2 for blocked.
    """
    # Infrastructure paths always allowed
    infra = (".svp/", "scripts/", "ledgers/", "logs/")
    for prefix in infra:
        if file_path.startswith(prefix):
            return 0

    # toolchain.json permanently read-only
    if file_path.endswith("toolchain.json"):
        return 2

    # ruff.toml permanently read-only
    if file_path.endswith("ruff.toml"):
        return 2

    # Load state if available
    sub_stage = ""
    try:
        with open(pipeline_state_path) as f:
            state = json.load(f)
        sub_stage = state.get("sub_stage", "") or ""
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # project_profile.json
    if file_path.endswith("project_profile.json"):
        allowed_subs = (
            "project_profile",
            "redo_profile_delivery",
            "redo_profile_blueprint",
        )
        if sub_stage in allowed_subs:
            return 0
        return 2

    return 0


def check_svp_session(env_var_name: str) -> int:
    """Check if SVP session is active.

    Returns 0 if active, 2 if not.
    """
    val = os.environ.get(env_var_name, "")
    if val == "1":
        return 0
    return 2


def check_stub_sentinel(file_path: str) -> int:
    """Check file for __SVP_STUB__ sentinel.

    Returns 0 if clean, 2 if sentinel found.
    """
    try:
        with open(file_path) as f:
            content = f.read()
        if "__SVP_STUB__" in content:
            return 2
        return 0
    except (FileNotFoundError, OSError):
        return 0

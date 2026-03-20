# Unit 12: Hook Configurations
# Defines hooks.json, write_authorization.sh, and non_svp_protection.sh content.

from typing import Dict, Any, List
import json
import os
import re

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Bug 17 fix: correct hook configuration schema
HOOKS_JSON_SCHEMA: Dict[str, Any] = {
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": ".claude/scripts/write_authorization.sh",
                    }
                ],
            },
            {
                "matcher": "Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": ".claude/scripts/non_svp_protection.sh",
                    }
                ],
            },
        ]
    }
}

SVP_ENV_VAR: str = "SVP_PLUGIN_ACTIVE"

# ---------------------------------------------------------------------------
# HOOKS_JSON_CONTENT -- Claude Code plugin hook format
# ---------------------------------------------------------------------------

_hooks_json_data: Dict[str, Any] = {
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": ".claude/scripts/write_authorization.sh",
                    }
                ],
            },
            {
                "matcher": "Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": ".claude/scripts/non_svp_protection.sh",
                    }
                ],
            },
        ]
    }
}

HOOKS_JSON_CONTENT: str = json.dumps(_hooks_json_data, indent=2) + "\n"

# ---------------------------------------------------------------------------
# NON_SVP_PROTECTION_SH_CONTENT
# ---------------------------------------------------------------------------

NON_SVP_PROTECTION_SH_CONTENT: str = r'''#!/usr/bin/env bash
# non_svp_protection.sh
# Checks for SVP_PLUGIN_ACTIVE environment variable.
# If not set, blocks all bash tool use (exit 2).
# If set, allows (exit 0).

set -euo pipefail

if [ -z "${SVP_PLUGIN_ACTIVE:-}" ]; then
    echo "BLOCKED: This is an SVP-managed project. Bash tool use is not permitted outside of an SVP session."
    echo "Please use the 'svp' command to interact with this project."
    exit 2
fi

exit 0
'''

# ---------------------------------------------------------------------------
# WRITE_AUTHORIZATION_SH_CONTENT
# ---------------------------------------------------------------------------

WRITE_AUTHORIZATION_SH_CONTENT: str = r'''#!/usr/bin/env bash
# write_authorization.sh
# Universal write authorization hook for SVP-managed projects.
# Reads pipeline_state.json to determine current state and checks the
# requested file path against the two-tier authorization model.
#
# Exit codes:
#   0 = allow write
#   2 = block write (with message)
#
# SVP 2.1: toolchain.json permanently read-only, ruff.toml permanently read-only,
# project_profile.json state-gated, delivered_repo_path writable during authorized
# debug, lessons learned document writable during authorized debug.

set -euo pipefail

# The tool input is provided via stdin as JSON.
# We need to extract the file_path from the tool input.
TOOL_INPUT=""
if [ ! -t 0 ]; then
    TOOL_INPUT="$(cat)"
fi

# Extract file_path from tool input JSON
FILE_PATH=""
if [ -n "$TOOL_INPUT" ]; then
    FILE_PATH="$(echo "$TOOL_INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    # Try common field names for file path (flat and nested formats)
    ti = data.get('tool_input', {}) or {}
    path = data.get('file_path') or data.get('path') or ti.get('file_path') or ti.get('path') or data.get('command', '')
    print(path)
except:
    print('')
" 2>/dev/null || echo "")"
fi

# If we couldn't extract a file path, allow (non-file operations)
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Normalize: remove leading ./ and resolve to relative path from project root
FILE_PATH="${FILE_PATH#./}"

# State file path
STATE_FILE="pipeline_state.json"

# --- Permanently read-only files (unconditional block) ---
case "$FILE_PATH" in
    toolchain.json)
        echo "BLOCKED: toolchain.json is permanently read-only. Path: $FILE_PATH"
        exit 2
        ;;
    ruff.toml)
        echo "BLOCKED: ruff.toml is permanently read-only. Path: $FILE_PATH"
        exit 2
        ;;
esac

# If state file doesn't exist, block everything except infrastructure
if [ ! -f "$STATE_FILE" ]; then
    # Check infrastructure paths even without state
    case "$FILE_PATH" in
        .svp/*|pipeline_state.json|ledgers/*|logs/*)
            exit 0
            ;;
        *)
            echo "BLOCKED: pipeline_state.json not found. Cannot determine write authorization for: $FILE_PATH"
            exit 2
            ;;
    esac
fi

# Read state
STATE="$(cat "$STATE_FILE")"

# Extract fields using python3 for reliable JSON parsing
read -r STAGE SUB_STAGE CURRENT_UNIT DEBUG_AUTHORIZED DEBUG_CLASSIFICATION DEBUG_PHASE DEBUG_AFFECTED_UNITS DELIVERED_REPO_PATH <<< "$(echo "$STATE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
stage = data.get('stage', '0')
sub_stage = data.get('sub_stage', '') or ''
current_unit = str(data.get('current_unit', ''))
delivered_repo_path = data.get('delivered_repo_path', '') or ''
ds = data.get('debug_session')
if ds:
    authorized = 'true' if ds.get('authorized', False) else 'false'
    classification = ds.get('classification', '') or ''
    phase = ds.get('phase', '')
    affected = ','.join(str(u) for u in ds.get('affected_units', []))
else:
    authorized = 'none'
    classification = ''
    phase = ''
    affected = ''
print(f'{stage} {sub_stage} {current_unit} {authorized} {classification} {phase} {affected} {delivered_repo_path}')
" 2>/dev/null)"

# --- Infrastructure paths: always writable ---
case "$FILE_PATH" in
    .svp/*|pipeline_state.json|ledgers/*|logs/*)
        exit 0
        ;;
esac

# --- project_profile.json: state-gated ---
case "$FILE_PATH" in
    project_profile.json)
        # Writable during Stage 0 project_profile sub-stage
        if [ "$STAGE" = "0" ] && [ "$SUB_STAGE" = "project_profile" ]; then
            exit 0
        fi
        # Writable during redo-triggered profile revision sub-stages
        if [ "$SUB_STAGE" = "redo_profile_delivery" ] || [ "$SUB_STAGE" = "redo_profile_blueprint" ]; then
            exit 0
        fi
        echo "BLOCKED: project_profile.json is read-only in current state. Path: $FILE_PATH"
        exit 2
        ;;
esac

# --- Debug session handling (Bug 2 fix) ---
if [ "$DEBUG_AUTHORIZED" = "true" ]; then
    # Authorized debug session

    # tests/regressions/ always writable during authorized debug
    case "$FILE_PATH" in
        tests/regressions/*)
            exit 0
            ;;
    esac

    # Lessons learned document writable during authorized debug (SVP 2.1)
    case "$FILE_PATH" in
        lessons_learned.md|lessons_learned.txt)
            exit 0
            ;;
    esac

    # delivered_repo_path writable during authorized debug (SVP 2.1)
    if [ -n "$DELIVERED_REPO_PATH" ]; then
        case "$FILE_PATH" in
            "${DELIVERED_REPO_PATH}"|"${DELIVERED_REPO_PATH}"/*)
                exit 0
                ;;
        esac
    fi

    # .svp/triage_scratch/ and .svp/triage_result.json writable during triage phases (Bug 55)
    case "$DEBUG_PHASE" in
        triage|triage_readonly)
            case "$FILE_PATH" in
                .svp/triage_scratch/*)
                    exit 0
                    ;;
                .svp/triage_result.json)
                    exit 0
                    ;;
            esac
            ;;
    esac

    case "$DEBUG_CLASSIFICATION" in
        build_env)
            # Environment files, pyproject.toml, __init__.py, directory structure are writable.
            # Implementation .py files in src/unit_N/ (other than __init__.py) are NOT writable.
            case "$FILE_PATH" in
                pyproject.toml|setup.py|setup.cfg|requirements*.txt|environment.yml|.env|.env.*)
                    exit 0
                    ;;
                */__init__.py)
                    exit 0
                    ;;
                src/unit_*/[!_]*.py|src/unit_*/?[!_]*.py)
                    echo "BLOCKED: Implementation files in src/unit_N/ are not writable during build_env debug. Path: $FILE_PATH"
                    exit 2
                    ;;
                src/unit_*/__init__.py)
                    exit 0
                    ;;
                src/unit_*/*.py)
                    echo "BLOCKED: Implementation files in src/unit_N/ are not writable during build_env debug. Path: $FILE_PATH"
                    exit 2
                    ;;
                src/*|tests/*|specs/*|blueprint/*|references/*)
                    exit 0
                    ;;
            esac
            ;;
        single_unit)
            # src/unit_N/ and tests/unit_N/ writable only for affected units
            IFS=',' read -ra UNITS <<< "$DEBUG_AFFECTED_UNITS"
            for unit in "${UNITS[@]}"; do
                [ -z "$unit" ] && continue
                case "$FILE_PATH" in
                    src/unit_${unit}/*)
                        exit 0
                        ;;
                    tests/unit_${unit}/*)
                        exit 0
                        ;;
                esac
            done

            # If it's a src/unit_* or tests/unit_* path but not for an affected unit, block
            case "$FILE_PATH" in
                src/unit_*/*|tests/unit_*/*)
                    echo "BLOCKED: Path is not for an affected unit during single_unit debug. Path: $FILE_PATH"
                    exit 2
                    ;;
            esac
            ;;
    esac

    # For authorized debug, paths not handled above fall through to normal stage-gating
elif [ "$DEBUG_AUTHORIZED" = "false" ]; then
    # Debug session present but not yet authorized (pre-Gate 6.0)
    # Only infrastructure paths are writable. We already allowed those above.
    echo "BLOCKED: Debug session not yet authorized. Only infrastructure paths are writable. Path: $FILE_PATH"
    exit 2
fi

# --- Stage-gated authorization (normal pipeline) ---
case "$STAGE" in
    0|1|2|pre_stage_3)
        # During early stages, only infrastructure paths are writable (already handled above).
        # Block all project artifact paths.
        case "$FILE_PATH" in
            src/*|tests/*|specs/*|blueprint/*|references/*|*-repo/*)
                echo "BLOCKED: Project artifact paths are not writable during stage $STAGE. Path: $FILE_PATH"
                exit 2
                ;;
        esac
        ;;
    3)
        # During stage 3, src/unit_N/ is writable only for the current unit
        if [ -n "$CURRENT_UNIT" ]; then
            case "$FILE_PATH" in
                src/unit_${CURRENT_UNIT}/*)
                    exit 0
                    ;;
                tests/unit_${CURRENT_UNIT}/*)
                    exit 0
                    ;;
                src/unit_*/*|tests/unit_*/*)
                    echo "BLOCKED: Only unit $CURRENT_UNIT is writable during stage 3. Path: $FILE_PATH"
                    exit 2
                    ;;
                specs/*|blueprint/*|references/*|*-repo/*)
                    exit 0
                    ;;
            esac
        fi
        ;;
    4)
        # During stage 4 (integration), broader write access to src/ and tests/
        case "$FILE_PATH" in
            src/*|tests/*|specs/*|blueprint/*|references/*|*-repo/*)
                exit 0
                ;;
        esac
        ;;
    5)
        # During stage 5 (assembly/delivery), broad write access
        case "$FILE_PATH" in
            src/*|tests/*|specs/*|blueprint/*|references/*|*-repo/*)
                exit 0
                ;;
        esac
        ;;
esac

# Default: allow (paths not matching any known pattern are allowed)
exit 0
'''

# ---------------------------------------------------------------------------
# Python functions modeling the shell script behavior
# ---------------------------------------------------------------------------


def check_write_authorization(
    tool_name: str,
    file_path: str,
    pipeline_state_path: str,
) -> int:
    """Check whether a write to file_path is authorized given the current pipeline state.

    Returns 0 (allow) or 2 (block).
    """
    # Normalize path
    if file_path.startswith("./"):
        file_path = file_path[2:]

    # Infrastructure paths: always writable
    if (
        file_path.startswith(".svp/")
        or file_path == "pipeline_state.json"
        or file_path.startswith("ledgers/")
        or file_path.startswith("logs/")
    ):
        return 0

    # --- Permanently read-only files (unconditional block) ---
    if file_path == "toolchain.json":
        return 2
    if file_path == "ruff.toml":
        return 2

    # Load state
    if not os.path.isfile(pipeline_state_path):
        return 2

    with open(pipeline_state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    stage = state.get("stage", "0")
    sub_stage = state.get("sub_stage") or ""
    current_unit = state.get("current_unit")
    debug_session = state.get("debug_session")
    delivered_repo_path = state.get("delivered_repo_path") or ""

    # --- project_profile.json: state-gated ---
    if file_path == "project_profile.json":
        # Writable during Stage 0 project_profile sub-stage
        if stage == "0" and sub_stage == "project_profile":
            return 0
        # Writable during redo-triggered profile revision sub-stages
        if sub_stage in ("redo_profile_delivery", "redo_profile_blueprint"):
            return 0
        return 2

    # --- Debug session handling ---
    if debug_session is not None:
        authorized = debug_session.get("authorized", False)
        classification = debug_session.get("classification") or ""
        phase = debug_session.get("phase", "")
        affected_units = debug_session.get("affected_units", [])

        if authorized:
            # tests/regressions/ always writable
            if file_path.startswith("tests/regressions/"):
                return 0

            # Lessons learned document writable during authorized debug (SVP 2.1)
            if file_path in ("lessons_learned.md", "lessons_learned.txt"):
                return 0

            # delivered_repo_path writable during authorized debug (SVP 2.1)
            if delivered_repo_path:
                if file_path == delivered_repo_path or file_path.startswith(
                    delivered_repo_path.rstrip("/") + "/"
                ):
                    return 0

            # .svp/triage_scratch/ and .svp/triage_result.json writable during triage (Bug 55)
            if phase in ("triage", "triage_readonly"):
                if file_path.startswith(".svp/triage_scratch/"):
                    return 0
                if file_path == ".svp/triage_result.json":
                    return 0

            if classification == "build_env":
                # Environment files, pyproject.toml, __init__.py writable
                basename = os.path.basename(file_path)
                if basename in (
                    "pyproject.toml",
                    "setup.py",
                    "setup.cfg",
                    ".env",
                ) or basename.startswith("requirements"):
                    return 0
                if basename == "__init__.py":
                    return 0
                # Implementation .py in src/unit_N/ (not __init__.py) blocked
                unit_src_match = re.match(r"^src/unit_\d+/(.+)$", file_path)
                if unit_src_match:
                    inner = unit_src_match.group(1)
                    if inner.endswith(".py") and inner != "__init__.py":
                        return 2
                    return 0
                # Other project paths allowed
                for prefix in ("src/", "tests/", "specs/", "blueprint/", "references/"):
                    if file_path.startswith(prefix):
                        return 0
                return 0

            elif classification == "single_unit":
                # src/unit_N/ and tests/unit_N/ writable only for affected units
                unit_match = re.match(r"^(src|tests)/unit_(\d+)/", file_path)
                if unit_match:
                    unit_num = int(unit_match.group(2))
                    if unit_num in affected_units:
                        return 0
                    return 2

            # Fall through to normal stage-gating for other classifications / paths
        else:
            # Not authorized: only infrastructure (already checked above)
            return 2

    # --- Normal stage-gated authorization ---
    project_prefixes = ("src/", "tests/", "specs/", "blueprint/", "references/")

    if stage in ("0", "1", "2", "pre_stage_3"):
        for prefix in project_prefixes:
            if file_path.startswith(prefix):
                return 2
        # Also check *-repo/ pattern
        if re.match(r"^[^/]+-repo/", file_path):
            return 2

    elif stage == "3":
        if current_unit is not None:
            cu = str(current_unit)
            if file_path.startswith(f"src/unit_{cu}/") or file_path.startswith(
                f"tests/unit_{cu}/"
            ):
                return 0
            # Other unit paths blocked
            unit_match = re.match(r"^(src|tests)/unit_\d+/", file_path)
            if unit_match:
                return 2
            # Other project paths allowed in stage 3
            for prefix in ("specs/", "blueprint/", "references/"):
                if file_path.startswith(prefix):
                    return 0
            if re.match(r"^[^/]+-repo/", file_path):
                return 0

    elif stage in ("4", "5"):
        # Broad write access
        for prefix in project_prefixes:
            if file_path.startswith(prefix):
                return 0
        if re.match(r"^[^/]+-repo/", file_path):
            return 0

    # Default: allow
    return 0


def check_svp_session(env_var_name: str) -> int:
    """Check whether the SVP session environment variable is set.

    Returns 0 (allow) if the variable is set, 2 (block) if not.
    """
    value = os.environ.get(env_var_name, "")
    if not value:
        return 2
    return 0

"""Unit 17: Hook Enforcement.

Generates hook configuration JSON and shell scripts for Claude Code
hook enforcement in SVP-managed projects.

Dependencies: Unit 2 (Language Registry), Unit 5 (Pipeline State).
"""

import json
import textwrap
from typing import Any, Dict

# ---------------------------------------------------------------------------
# HOOKS_JSON_SCHEMA -- structural schema for the hooks.json configuration
# ---------------------------------------------------------------------------

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
        ],
        "PostToolUse": [
            {
                "matcher": "Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": ".claude/scripts/stub_sentinel_check.sh",
                    }
                ],
            },
            {
                "matcher": "Agent",
                "hooks": [
                    {
                        "type": "command",
                        "command": ".claude/scripts/monitoring_reminder.sh",
                    }
                ],
            },
        ],
    }
}


# ---------------------------------------------------------------------------
# generate_hooks_json
# ---------------------------------------------------------------------------


def generate_hooks_json() -> str:
    """Return the hooks.json content as a JSON string.

    Produces valid Claude Code hook configuration with:
    - PreToolUse: Write -> write_authorization.sh, Bash -> non_svp_protection.sh
    - PostToolUse: Write -> stub_sentinel_check.sh, Agent -> monitoring_reminder.sh

    Each entry: {"matcher": "<tool>", "handler": {"type": "command", "command": "<path>"}}.
    Paths use .claude/scripts/ prefix.
    """
    return json.dumps(HOOKS_JSON_SCHEMA, indent=2)


# ---------------------------------------------------------------------------
# generate_write_authorization_sh
# ---------------------------------------------------------------------------


def generate_write_authorization_sh() -> str:
    """Return the write_authorization.sh shell script content.

    Hook order:
    1. Read current stage from pipeline_state.json
    2. Check pipeline_state.json protection (writable only by update_state.py)
    3. Check builder script protection (scripts/*.py read-only Stages 3-5)
    4. Check remaining path rules

    Infrastructure paths (.svp/, ledgers/, logs/) always writable.
    pipeline_state.json only writable by update_state.py.
    Builder scripts (scripts/*.py) read-only during Stages 3-5 with Hard Stop message.
    Profile/toolchain read-only after Gate 0.3.
    Exit code 2 for blocks.
    """
    return textwrap.dedent("""\
        #!/usr/bin/env bash
        # write_authorization.sh
        # PreToolUse hook: validates writes against pipeline state.
        #
        # Exit codes:
        #   0 = allow write
        #   2 = block write (with message)

        set -euo pipefail

        # Read tool input from stdin
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
            ti = data.get('tool_input', {}) or {}
            path = data.get('file_path') or data.get('path') or ti.get('file_path') or ti.get('path') or ''
            print(path)
        except:
            print('')
        " 2>/dev/null || echo "")"
        fi

        # If we couldn't extract a file path, allow (non-file operations)
        if [ -z "$FILE_PATH" ]; then
            exit 0
        fi

        # Normalize: remove leading ./
        FILE_PATH="${FILE_PATH#./}"

        # --- Infrastructure paths: always writable ---
        case "$FILE_PATH" in
            .svp/*|ledgers/*|logs/*)
                exit 0
                ;;
        esac

        # --- (1) Read current stage from pipeline_state.json ---
        STATE_FILE="pipeline_state.json"
        STAGE=""
        SUB_STAGE=""
        CURRENT_UNIT=""
        ORACLE_SESSION_ACTIVE="false"
        DEBUG_SESSION=""
        DEBUG_AUTHORIZED="none"
        DEBUG_CLASSIFICATION=""
        DEBUG_PHASE=""
        DEBUG_AFFECTED_UNITS=""
        DELIVERED_REPO_PATH=""

        if [ -f "$STATE_FILE" ]; then
            read -r STAGE SUB_STAGE CURRENT_UNIT ORACLE_SESSION_ACTIVE DEBUG_AUTHORIZED DEBUG_CLASSIFICATION DEBUG_PHASE DEBUG_AFFECTED_UNITS DELIVERED_REPO_PATH <<< "$(cat "$STATE_FILE" | python3 -c "
        import sys, json
        data = json.load(sys.stdin)
        stage = data.get('stage', '0')
        sub_stage = data.get('sub_stage', '') or ''
        current_unit = str(data.get('current_unit', '') or '')
        oracle_active = 'true' if data.get('oracle_session_active', False) else 'false'
        delivered_repo_path = data.get('delivered_repo_path', '') or ''
        ds = data.get('debug_session')
        if ds:
            authorized = 'true' if ds.get('authorized', False) else 'false'
            classification = ds.get('classification', '') or ''
            phase = ds.get('phase', '') or ''
            affected = ','.join(str(u) for u in ds.get('affected_units', []))
        else:
            authorized = 'none'
            classification = ''
            phase = ''
            affected = ''
        print(f'{stage} {sub_stage or \"_\"} {current_unit or \"_\"} {oracle_active} {authorized} {classification or \"_\"} {phase or \"_\"} {affected or \"_\"} {delivered_repo_path or \"_\"}')
        " 2>/dev/null)"
            # Normalize underscore placeholders to empty
            [ "$SUB_STAGE" = "_" ] && SUB_STAGE=""
            [ "$CURRENT_UNIT" = "_" ] && CURRENT_UNIT=""
            [ "$DEBUG_CLASSIFICATION" = "_" ] && DEBUG_CLASSIFICATION=""
            [ "$DEBUG_PHASE" = "_" ] && DEBUG_PHASE=""
            [ "$DEBUG_AFFECTED_UNITS" = "_" ] && DEBUG_AFFECTED_UNITS=""
            [ "$DELIVERED_REPO_PATH" = "_" ] && DELIVERED_REPO_PATH=""
        fi

        # --- (2) Check pipeline_state.json protection ---
        # pipeline_state.json is only writable by update_state.py
        case "$FILE_PATH" in
            pipeline_state.json)
                echo "BLOCKED: pipeline_state.json is only writable by update_state.py. Direct writes are not permitted."
                exit 2
                ;;
        esac

        # --- Permanently read-only files ---
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

        # --- (3) Check builder script protection (Stages 3-5) ---
        case "$FILE_PATH" in
            scripts/*.py)
                case "$STAGE" in
                    3|4|5)
                        echo "BLOCKED: Builder script modification blocked during Stages 3-5. If this script has a bug, follow the Hard Stop Protocol: save artifacts, produce bug analysis, fix via /svp:bug in the SVP N workspace, then restart from checkpoint."
                        exit 2
                        ;;
                esac
                ;;
        esac

        # --- (4) Check remaining path rules ---

        # project_profile.json: state-gated
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

        # Oracle session rules
        if [ "$ORACLE_SESSION_ACTIVE" = "true" ]; then
            case "$FILE_PATH" in
                .svp/oracle_run_ledger.json)
                    exit 0
                    ;;
            esac
        fi

        # Debug session handling
        if [ "$DEBUG_AUTHORIZED" = "true" ]; then
            # tests/regressions/ always writable during authorized debug
            case "$FILE_PATH" in
                tests/regressions/*)
                    exit 0
                    ;;
            esac

            # delivered_repo_path writable during authorized debug
            if [ -n "$DELIVERED_REPO_PATH" ]; then
                case "$FILE_PATH" in
                    "${DELIVERED_REPO_PATH}"|"${DELIVERED_REPO_PATH}"/*)
                        exit 0
                        ;;
                esac
            fi

            # Unit-specific dirs writable for affected units
            if [ -n "$DEBUG_AFFECTED_UNITS" ]; then
                IFS=',' read -ra UNITS <<< "$DEBUG_AFFECTED_UNITS"
                for unit in "${UNITS[@]}"; do
                    [ -z "$unit" ] && continue
                    case "$FILE_PATH" in
                        src/unit_${unit}/*|tests/unit_${unit}/*)
                            exit 0
                            ;;
                    esac
                done
            fi
        elif [ "$DEBUG_AUTHORIZED" = "false" ]; then
            # Debug session present but not yet authorized
            echo "BLOCKED: Debug session not yet authorized. Only infrastructure paths are writable. Path: $FILE_PATH"
            exit 2
        fi

        # If state file doesn't exist, block non-infrastructure writes
        if [ ! -f "$STATE_FILE" ]; then
            echo "BLOCKED: pipeline_state.json not found. Cannot determine write authorization for: $FILE_PATH"
            exit 2
        fi

        # Stage-gated authorization
        case "$STAGE" in
            0|1|2|pre_stage_3)
                case "$FILE_PATH" in
                    src/*|tests/*|specs/*|blueprint/*|references/*|*-repo/*)
                        echo "BLOCKED: Project artifact paths are not writable during stage $STAGE. Path: $FILE_PATH"
                        exit 2
                        ;;
                esac
                ;;
            3)
                if [ -n "$CURRENT_UNIT" ]; then
                    case "$FILE_PATH" in
                        src/unit_${CURRENT_UNIT}/*|tests/unit_${CURRENT_UNIT}/*)
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
            4|5)
                case "$FILE_PATH" in
                    src/*|tests/*|specs/*|blueprint/*|references/*|*-repo/*)
                        exit 0
                        ;;
                esac
                ;;
        esac

        # Default: allow
        exit 0
    """)


# ---------------------------------------------------------------------------
# generate_non_svp_protection_sh
# ---------------------------------------------------------------------------


def generate_non_svp_protection_sh() -> str:
    """Return the non_svp_protection.sh shell script content.

    Checks SVP_PLUGIN_ACTIVE environment variable.
    If not set or not "1": blocks all bash commands, prints README message.
    Exit code 2 for blocked commands.
    """
    return textwrap.dedent("""\
        #!/usr/bin/env bash
        # non_svp_protection.sh
        # PreToolUse hook: checks for SVP_PLUGIN_ACTIVE environment variable.
        # If not set or not "1", blocks all bash tool use (exit 2).

        set -euo pipefail

        if [ "${SVP_PLUGIN_ACTIVE:-}" != "1" ]; then
            echo "BLOCKED: This is an SVP-managed project. Bash tool use is not permitted outside of an SVP session."
            echo "Please read the project README for instructions on how to interact with this project."
            exit 2
        fi

        exit 0
    """)


# ---------------------------------------------------------------------------
# generate_stub_sentinel_check_sh
# ---------------------------------------------------------------------------


def generate_stub_sentinel_check_sh() -> str:
    """Return the stub_sentinel_check.sh shell script content.

    PostToolUse hook on Write matcher. Greps written file for stub sentinels
    from LANGUAGE_REGISTRY. If found: exit code 2 with message directing
    agent to implement, not copy stub.
    """
    return textwrap.dedent("""\
        #!/usr/bin/env bash
        # stub_sentinel_check.sh
        # PostToolUse hook: checks for stub sentinel markers in written files.
        #
        # Exit 0 = ok, Exit 2 = sentinel found

        set -euo pipefail

        # Read tool input from stdin
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
            ti = data.get('tool_input', {}) or {}
            path = data.get('file_path') or data.get('path') or ti.get('file_path') or ti.get('path') or ''
            print(path)
        except:
            print('')
        " 2>/dev/null || echo "")"
        fi

        if [ -z "$FILE_PATH" ]; then
            exit 0
        fi

        # Check for Python stub sentinel
        if [ -f "$FILE_PATH" ]; then
            if grep -q "__SVP_STUB__" "$FILE_PATH"; then
                echo "BLOCKED: Stub sentinel (__SVP_STUB__) found in $FILE_PATH."
                echo "You must implement the module, not copy the stub file. Remove the sentinel and provide a complete implementation."
                exit 2
            fi
            # Check for R stub sentinel
            if grep -q "# __SVP_STUB__ <- TRUE" "$FILE_PATH"; then
                echo "BLOCKED: Stub sentinel (__SVP_STUB__) found in $FILE_PATH."
                echo "You must implement the module, not copy the stub file. Remove the sentinel and provide a complete implementation."
                exit 2
            fi
        fi

        exit 0
    """)


# ---------------------------------------------------------------------------
# generate_monitoring_reminder_sh
# ---------------------------------------------------------------------------


def generate_monitoring_reminder_sh() -> str:
    """Return the monitoring_reminder.sh shell script content.

    PostToolUse hook on Agent matcher. Reads project_profile.json (NOT
    pipeline_state.json) for is_svp_build. If true: output monitoring
    reminder. If false or absent: exit 0 silently.
    """
    return textwrap.dedent("""\
        #!/usr/bin/env bash
        # monitoring_reminder.sh
        # PostToolUse hook: outputs monitoring reminder for E/F self-builds.
        # Reads project_profile.json to check is_svp_build.

        set -euo pipefail

        PROFILE_FILE="project_profile.json"

        # If profile doesn't exist, exit silently
        if [ ! -f "$PROFILE_FILE" ]; then
            exit 0
        fi

        # Check is_svp_build field
        IS_SVP_BUILD="$(python3 -c "
        import json
        try:
            with open('$PROFILE_FILE') as f:
                data = json.load(f)
            print('true' if data.get('is_svp_build', False) else 'false')
        except:
            print('false')
        " 2>/dev/null || echo "false")"

        if [ "$IS_SVP_BUILD" = "true" ]; then
            echo "MONITORING REMINDER: This is an SVP self-build (E/F archetype). Before proceeding, verify the subagent output against the spec. Check that the agent's terminal status is valid, the output conforms to blueprint contracts, and no pipeline invariants were violated."
        fi

        exit 0
    """)

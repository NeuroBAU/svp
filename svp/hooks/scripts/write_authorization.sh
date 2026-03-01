#!/usr/bin/env bash
# write_authorization.sh
# Universal write authorization hook for SVP-managed projects.
# Reads pipeline_state.json to determine current state and checks the
# requested file path against the two-tier authorization model.
#
# Exit codes:
#   0 = allow write
#   2 = block write (with message)

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
read -r STAGE CURRENT_UNIT DEBUG_AUTHORIZED DEBUG_CLASSIFICATION DEBUG_PHASE DEBUG_AFFECTED_UNITS <<< "$(echo "$STATE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
stage = data.get('stage', '0')
current_unit = str(data.get('current_unit', ''))
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
print(f'{stage} {current_unit} {authorized} {classification} {phase} {affected}')
" 2>/dev/null)"

# --- Infrastructure paths: always writable ---
case "$FILE_PATH" in
    .svp/*|pipeline_state.json|ledgers/*|logs/*)
        exit 0
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

    # .svp/triage_scratch/ writable during triage phases
    case "$DEBUG_PHASE" in
        triage|triage_readonly)
            case "$FILE_PATH" in
                .svp/triage_scratch/*)
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

#!/usr/bin/env bash
# stub_sentinel_check.sh
# PostToolUse hook: checks for stub sentinel markers in written files.
#
# Exit 0 = ok, Exit 2 = sentinel found

set -euo pipefail

# Portable Python: prefer python3, fall back to python (Bug S3-71)
PYTHON="$(command -v python3 2>/dev/null || command -v python 2>/dev/null || echo python3)"

# Read tool input from stdin
TOOL_INPUT=""
if [ ! -t 0 ]; then
    TOOL_INPUT="$(cat)"
fi

# Extract file_path from tool input JSON
FILE_PATH=""
if [ -n "$TOOL_INPUT" ]; then
    FILE_PATH="$(echo "$TOOL_INPUT" | $PYTHON -c "
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

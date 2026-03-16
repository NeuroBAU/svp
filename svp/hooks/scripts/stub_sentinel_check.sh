#!/usr/bin/env bash
# stub_sentinel_check.sh
# PostToolUse hook: checks for __SVP_STUB__ sentinel
# in files written to src/unit_N/ paths.
#
# Exit 0 = ok, Exit 2 = sentinel found

set -euo pipefail

FILE_PATH=$(echo "$TOOL_INPUT" |   python3 -c "import sys,json;   print(json.load(sys.stdin).get('file_path',''))")

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

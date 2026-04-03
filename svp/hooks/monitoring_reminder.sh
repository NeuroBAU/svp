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

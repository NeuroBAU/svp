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

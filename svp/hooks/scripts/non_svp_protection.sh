#!/usr/bin/env bash
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

#!/usr/bin/env bash
#
# setup_svp_user.sh — Per-user SVP activation WITHOUT pip (shell-function method).
#
# The POSIX counterpart to setup_svp_user.ps1. Makes the `svp` command work for
# the current macOS/Linux user by:
#   1. Validating the shared toolchain (python >= 3.11 + pytest, claude, git, conda).
#   2. Exporting SVP_PLUGIN_ROOT in the user's shell rc as an explicit override /
#      fallback. The launcher's _find_plugin_root() self-locates from its own
#      on-disk path (it runs out of svp/scripts/), so discovery works from this
#      repo even before the export loads; the var still wins when set.
#   3. Adding a `svp` shell function to the user's rc that invokes
#      svp/scripts/svp_launcher.py directly (replaces the pip-generated `svp`
#      console script — no `pip install`, and immune to the macOS framework-Python
#      site-packages issue and to repo relocation).
#   4. Optionally registering this repo as a Claude Code marketplace.
#
# It does NOT edit PATH or ~/.claude/settings.json. The launcher handles
# project-scoped plugin activation automatically on the first `svp new`.
#
# Usage:
#   ./setup_svp_user.sh [--register-marketplace] [--python <path>] [--repo <path>]
#
# Run this AS the target user, from inside a copy of the SVP repo this user can
# read. The repo root is auto-detected from the script's own location.

set -euo pipefail

# --- Colors (fall back to plain text when not a TTY) --------------------
if [ -t 1 ]; then
    C_G=$'\033[32m'; C_R=$'\033[31m'; C_C=$'\033[36m'; C_Y=$'\033[33m'; C_0=$'\033[0m'
else
    C_G=''; C_R=''; C_C=''; C_Y=''; C_0=''
fi
ok()   { printf '    %sOK:%s   %s\n' "$C_G" "$C_0" "$1"; }
fail() { printf '    %sFAIL:%s %s\n' "$C_R" "$C_0" "$1" >&2; }
step() { printf '%s==> %s%s\n' "$C_C" "$1" "$C_0"; }
warn() { printf '    %sWARN:%s %s\n' "$C_Y" "$C_0" "$1"; }

# --- Args ---------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SVP_REPO="$SCRIPT_DIR"
PYTHON=""
REGISTER_MARKETPLACE=false

while [ $# -gt 0 ]; do
    case "$1" in
        --register-marketplace) REGISTER_MARKETPLACE=true; shift ;;
        --python) PYTHON="${2:-}"; shift 2 ;;
        --repo)   SVP_REPO="${2:-}"; shift 2 ;;
        -h|--help)
            grep '^#' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) fail "unknown argument: $1"; exit 1 ;;
    esac
done

SVP_REPO="$(cd "$SVP_REPO" && pwd)"
LAUNCHER="$SVP_REPO/svp/scripts/svp_launcher.py"
PLUGIN_ROOT="$SVP_REPO/svp"
MARKET="$SVP_REPO/.claude-plugin/marketplace.json"

# --- Validate the repo copy ---------------------------------------------
step "Validating SVP repo at: $SVP_REPO"
for p in "$LAUNCHER" "$PLUGIN_ROOT" "$MARKET"; do
    if [ -e "$p" ]; then
        ok "$(basename "$p")"
    else
        fail "missing: $p"
        fail "Is this a complete SVP repo this user can read?"
        exit 1
    fi
done

# --- Choose interpreter -------------------------------------------------
if [ -z "$PYTHON" ]; then
    if [ -n "${CONDA_PREFIX:-}" ] && [ -x "$CONDA_PREFIX/bin/python" ]; then
        PYTHON="$CONDA_PREFIX/bin/python"
    else
        PYTHON="$(command -v python3 || true)"
    fi
fi
if [ -z "$PYTHON" ] || ! [ -x "$PYTHON" ]; then
    # command -v may return a bare name resolvable on PATH
    if ! command -v "$PYTHON" >/dev/null 2>&1; then
        fail "no usable python interpreter found (pass --python <path>)"
        exit 1
    fi
fi

# --- Validate shared toolchain (mirrors launcher preflight) -------------
step "Validating shared toolchain"
if ! "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
    fail "$PYTHON is not >= 3.11"
    exit 1
fi
if ! "$PYTHON" -c 'import pytest' 2>/dev/null; then
    fail "pytest is not importable from $PYTHON"
    warn "Install it into the SAME interpreter, then re-run, e.g.:"
    warn "  pip install -e '.[test]' --user      # from the repo root"
    warn "  sudo port install py311-pytest        # MacPorts"
    exit 1
fi
ok "$PYTHON (>= 3.11, pytest importable)"
for c in claude git conda; do
    if command -v "$c" >/dev/null 2>&1; then
        ok "$c on PATH"
    else
        fail "$c not on PATH for this user"
        exit 1
    fi
done

# --- Select the shell rc file -------------------------------------------
case "$(basename "${SHELL:-}")" in
    zsh)  RC="${ZDOTDIR:-$HOME}/.zshrc" ;;
    bash) RC="$HOME/.bashrc" ;;
    *)    RC="$HOME/.profile" ;;
esac

# --- Write the activation block (idempotent) ----------------------------
step "Installing SVP activation into: $RC"
MARKER="# >>> SVP launcher (setup_svp_user.sh, no pip) >>>"
END_MARKER="# <<< SVP launcher (setup_svp_user.sh, no pip) <<<"
mkdir -p "$(dirname "$RC")"
touch "$RC"
if grep -qF "$MARKER" "$RC"; then
    warn "an SVP activation block already exists in $RC — left as-is."
    warn "To refresh it, delete the block between the >>> and <<< markers and re-run."
else
    {
        printf '\n%s\n' "$MARKER"
        printf 'export SVP_PLUGIN_ROOT=%q\n' "$PLUGIN_ROOT"
        printf 'svp() { %q %q "$@"; }\n' "$PYTHON" "$LAUNCHER"
        printf '%s\n' "$END_MARKER"
    } >> "$RC"
    ok "added SVP activation block to $RC"
fi

# --- Optional marketplace registration ----------------------------------
if [ "$REGISTER_MARKETPLACE" = true ]; then
    step "Registering Claude Code marketplace"
    if claude plugin marketplace add "$SVP_REPO"; then
        ok "marketplace registered: $SVP_REPO"
    else
        warn "marketplace add returned non-zero (may already exist)."
    fi
fi

# --- Next steps ----------------------------------------------------------
printf '\n'
printf '%s===================================================================%s\n' "$C_G" "$C_0"
printf '%s SVP activated for user: %s%s\n' "$C_G" "${USER:-$(id -un)}" "$C_0"
printf '%s===================================================================%s\n' "$C_G" "$C_0"
printf '\n'
printf 'Open a NEW shell (or run: source %q), then from any directory\n' "$RC"
printf 'OUTSIDE this repo:\n'
printf '    %ssvp new my-project%s\n' "$C_Y" "$C_0"
printf '\n'
printf 'Verify with:  type svp    (should show a shell function)\n'

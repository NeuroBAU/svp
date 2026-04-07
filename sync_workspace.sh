#!/usr/bin/env bash
# sync_workspace.sh — Bidirectional sync between SVP workspace and repos.
# Run from the workspace root directory (svp2.2-pass2/).
#
# Usage:
#   bash sync_workspace.sh              # sync using file timestamps (newer wins)
#   bash sync_workspace.sh --dry-run    # preview only, no changes
#   bash sync_workspace.sh --force-workspace  # workspace overwrites repo
#   bash sync_workspace.sh --force-repo       # repo overwrites workspace

set -euo pipefail

WORKSPACE="$(cd "$(dirname "$0")" && pwd)"
REPO="$WORKSPACE/../svp2.2-pass2-repo"
PASS1_REPO="$WORKSPACE/../svp2.2-repo"

DRY_RUN=false
FORCE_WS=false
FORCE_REPO=false
COPIED=0
SKIPPED=0
ERRORS=0

for arg in "$@"; do
    case "$arg" in
        --dry-run)    DRY_RUN=true ;;
        --force-workspace) FORCE_WS=true ;;
        --force-repo)      FORCE_REPO=true ;;
        *) echo "Unknown arg: $arg"; exit 1 ;;
    esac
done

# --- helpers ---

get_mtime() {
    # Portable: try GNU stat (Linux/Windows Git Bash), then macOS stat, then Python fallback
    stat -c %Y "$1" 2>/dev/null \
        || stat -f %m "$1" 2>/dev/null \
        || python3 -c "import os; print(int(os.path.getmtime('$1')))" 2>/dev/null \
        || echo 0
}

sync_file() {
    local src="$1" dst="$2" label="$3"
    if [ ! -f "$src" ]; then
        return
    fi
    local dir
    dir="$(dirname "$dst")"
    if [ ! -d "$dir" ]; then
        if $DRY_RUN; then
            echo "  [dry-run] mkdir -p $dir"
        else
            mkdir -p "$dir"
        fi
    fi
    if $DRY_RUN; then
        echo "  [dry-run] cp $label"
        COPIED=$((COPIED + 1))
    else
        # handle read-only destination
        if [ -f "$dst" ] && [ ! -w "$dst" ]; then
            chmod u+w "$dst"
        fi
        cp "$src" "$dst"
        COPIED=$((COPIED + 1))
        echo "  copied: $label"
    fi
}

sync_pair() {
    # Sync two files bidirectionally based on mtime or force flags.
    local a="$1" b="$2" label="$3"
    if [ ! -f "$a" ] && [ ! -f "$b" ]; then
        return
    fi
    if [ ! -f "$a" ]; then
        echo "  [only-in-b] $label ($(basename "$b"))"
        SKIPPED=$((SKIPPED + 1))
        return
    fi
    if [ ! -f "$b" ]; then
        echo "  [only-in-a] $label ($(basename "$a"))"
        SKIPPED=$((SKIPPED + 1))
        return
    fi
    if diff -q "$a" "$b" > /dev/null 2>&1; then
        return  # identical, nothing to do
    fi
    # Files differ
    if $FORCE_WS; then
        sync_file "$a" "$b" "$label (workspace → repo)"
    elif $FORCE_REPO; then
        sync_file "$b" "$a" "$label (repo → workspace)"
    else
        local mt_a mt_b
        mt_a="$(get_mtime "$a")"
        mt_b="$(get_mtime "$b")"
        if [ "$mt_a" -gt "$mt_b" ]; then
            sync_file "$a" "$b" "$label (workspace newer → repo)"
        elif [ "$mt_b" -gt "$mt_a" ]; then
            sync_file "$b" "$a" "$label (repo newer → workspace)"
        else
            echo "  [CONFLICT] $label — same mtime, different content. Manual resolution needed."
            ERRORS=$((ERRORS + 1))
        fi
    fi
}

echo "=== SVP Workspace Sync ==="
echo "Workspace: $WORKSPACE"
echo "Repo:      $REPO"
echo "Pass1:     $PASS1_REPO"
if $DRY_RUN; then echo "Mode: DRY RUN"; fi
if $FORCE_WS; then echo "Mode: FORCE WORKSPACE"; fi
if $FORCE_REPO; then echo "Mode: FORCE REPO"; fi
echo ""

# --- Step 0: Derive scripts from stubs (Bug S3-98) ---
# Stubs are the single source of truth. Scripts are derived by import rewriting.
echo "--- Step 0: Derive Scripts from Stubs ---"
if $DRY_RUN; then
    python3 "$WORKSPACE/scripts/derive_scripts_from_stubs.py" --workspace "$WORKSPACE" --dry-run
else
    python3 "$WORKSPACE/scripts/derive_scripts_from_stubs.py" --workspace "$WORKSPACE"
fi
echo ""

# --- Step 1: Scripts (workspace scripts/ ↔ repo svp/scripts/) ---
echo "--- Step 1: Scripts ---"
for f in "$WORKSPACE"/scripts/*.py; do
    [ -f "$f" ] || continue
    name="$(basename "$f")"
    sync_pair "$f" "$REPO/svp/scripts/$name" "scripts/$name"
done
# Check repo-only scripts
for f in "$REPO"/svp/scripts/*.py; do
    [ -f "$f" ] || continue
    name="$(basename "$f")"
    if [ ! -f "$WORKSPACE/scripts/$name" ]; then
        echo "  [repo-only] svp/scripts/$name"
        SKIPPED=$((SKIPPED + 1))
    fi
done
echo ""

# --- Step 2: Source units (workspace src/unit_*/stub.py ↔ repo src/unit_*/stub.py) ---
echo "--- Step 2: Source Units ---"
for d in "$WORKSPACE"/src/unit_*/; do
    [ -d "$d" ] || continue
    unit="$(basename "$d")"
    sync_pair "$d/stub.py" "$REPO/src/$unit/stub.py" "src/$unit/stub.py"
done
echo ""

# --- Step 3: Docs (workspace is authoritative → all repo locations) ---
echo "--- Step 3: Docs ---"

doc_sync() {
    local ws_file="$1"
    shift
    local name
    name="$(basename "$ws_file")"
    if [ ! -f "$ws_file" ]; then
        echo "  [missing] $ws_file"
        ERRORS=$((ERRORS + 1))
        return
    fi
    for dst in "$@"; do
        if [ ! -f "$dst" ] || ! diff -q "$ws_file" "$dst" > /dev/null 2>&1; then
            sync_file "$ws_file" "$dst" "$name → $(echo "$dst" | sed "s|$WORKSPACE/../||")"
        fi
    done
}

doc_sync "$WORKSPACE/specs/stakeholder_spec.md" \
    "$REPO/docs/stakeholder_spec.md" \
    "$REPO/specs/stakeholder_spec.md" \
    "$PASS1_REPO/docs/stakeholder_spec.md"

doc_sync "$WORKSPACE/blueprint/blueprint_contracts.md" \
    "$REPO/docs/blueprint_contracts.md" \
    "$REPO/blueprint/blueprint_contracts.md" \
    "$PASS1_REPO/docs/blueprint_contracts.md"

doc_sync "$WORKSPACE/blueprint/blueprint_prose.md" \
    "$REPO/docs/blueprint_prose.md" \
    "$REPO/blueprint/blueprint_prose.md" \
    "$PASS1_REPO/docs/blueprint_prose.md"

doc_sync "$WORKSPACE/references/svp_2_1_lessons_learned.md" \
    "$REPO/docs/references/svp_2_1_lessons_learned.md" \
    "$REPO/references/svp_2_1_lessons_learned.md" \
    "$PASS1_REPO/docs/references/svp_2_1_lessons_learned.md"
echo ""

# --- Step 3b: Workspace root files (Bug S3-98, S3-99) ---
# Universal files (all projects): project_context.md, ruff.toml.
# SVP self-build files (E/F only): CLAUDE.md, sync_workspace.sh.
# Stage 5 assembly is the authoritative delivery mechanism for E/F carry-over;
# this step is a development convenience to keep the repo current between builds.
echo "--- Step 3b: Workspace Root Files ---"
for rootfile in CLAUDE.md project_context.md ruff.toml sync_workspace.sh; do
    if [ -f "$WORKSPACE/$rootfile" ]; then
        if [ ! -f "$REPO/$rootfile" ] || ! diff -q "$WORKSPACE/$rootfile" "$REPO/$rootfile" > /dev/null 2>&1; then
            sync_file "$WORKSPACE/$rootfile" "$REPO/$rootfile" "$rootfile (workspace → repo)"
        fi
    fi
done
echo ""

# --- Step 4: Tests (workspace tests/ ↔ repo tests/) ---
echo "--- Step 4: Tests ---"
# Find all test files in both locations
(cd "$WORKSPACE" && find tests -name '*.py' -type f 2>/dev/null) | sort > /tmp/svp_ws_tests.txt
(cd "$REPO" && find tests -name '*.py' -type f 2>/dev/null) | sort > /tmp/svp_repo_tests.txt

# Files in both
comm -12 /tmp/svp_ws_tests.txt /tmp/svp_repo_tests.txt | while read -r tf; do
    sync_pair "$WORKSPACE/$tf" "$REPO/$tf" "$tf"
done

# Workspace-only
ws_only=$(comm -23 /tmp/svp_ws_tests.txt /tmp/svp_repo_tests.txt | wc -l | tr -d ' ')
if [ "$ws_only" -gt 0 ]; then
    echo "  [$ws_only workspace-only test file(s)]"
fi

# Repo-only
repo_only=$(comm -13 /tmp/svp_ws_tests.txt /tmp/svp_repo_tests.txt | wc -l | tr -d ' ')
if [ "$repo_only" -gt 0 ]; then
    echo "  [$repo_only repo-only test file(s)]"
fi

rm -f /tmp/svp_ws_tests.txt /tmp/svp_repo_tests.txt
echo ""

# --- Step 4b: Deployed Artifacts (Bug S3-80) ---
# Regenerate deployed plugin artifacts in both repos from source Units.
# These are the .md files Claude Code loads at runtime (svp/commands/, svp/agents/, etc.)
echo "--- Step 4b: Deployed Artifacts ---"
if [ "$DRY_RUN" = true ]; then
    echo "  [dry-run] would regenerate deployed artifacts in both repos"
else
    WORKSPACE="$WORKSPACE" REPO="$REPO" PASS1_REPO="$PASS1_REPO" python3 -c "
import sys, os
sys.path.insert(0, os.environ['WORKSPACE'])
from pathlib import Path
from src.unit_23.stub import regenerate_deployed_artifacts
for label, repo in [('pass2', os.environ['REPO']), ('pass1', os.environ['PASS1_REPO'])]:
    r = regenerate_deployed_artifacts(Path(repo))
    total = sum(r.values())
    if total > 0:
        print(f'  regenerated {total} artifacts in {label} repo ({r})')
    else:
        print(f'  no svp/ directory in {label} repo, skipped')
" 2>&1 || {
        echo "  ERROR: artifact regeneration failed"
        ERRORS=$((ERRORS + 1))
    }
fi
echo ""

# --- Step 5: Verify ---
echo "--- Step 5: Verify ---"
REMAINING=0

verify_pair() {
    local a="$1" b="$2" label="$3"
    if [ -f "$a" ] && [ -f "$b" ]; then
        if ! diff -q "$a" "$b" > /dev/null 2>&1; then
            echo "  [STILL DIFFERS] $label"
            REMAINING=$((REMAINING + 1))
        fi
    fi
}

# Spot-check critical files
for f in "$WORKSPACE"/scripts/*.py; do
    [ -f "$f" ] || continue
    name="$(basename "$f")"
    verify_pair "$f" "$REPO/svp/scripts/$name" "scripts/$name"
done
for d in "$WORKSPACE"/src/unit_*/; do
    [ -d "$d" ] || continue
    unit="$(basename "$d")"
    verify_pair "$d/stub.py" "$REPO/src/$unit/stub.py" "src/$unit/stub.py"
done

if [ "$REMAINING" -eq 0 ]; then
    echo "  All paired files in sync."
else
    echo "  $REMAINING file(s) still differ after sync."
fi
echo ""

# --- Summary ---
echo "=== Summary ==="
echo "  Copied:   $COPIED"
echo "  Skipped:  $SKIPPED (one-side-only files)"
echo "  Errors:   $ERRORS"
if [ "$ERRORS" -gt 0 ]; then
    echo "  !! Resolve errors manually."
    exit 1
fi
echo "  Done."

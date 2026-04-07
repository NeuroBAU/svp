#!/usr/bin/env bash
# sync_workspace.sh — One-way sync from SVP workspace to repos.
# The workspace is the single source of truth. The repo is a derived artifact.
# Run from the workspace root directory.
#
# Usage:
#   bash sync_workspace.sh              # sync workspace → repo
#   bash sync_workspace.sh --dry-run    # preview only, no changes
#
# Repo paths are read from .svp/sync_config.json (portable).
# Falls back to hardcoded relative paths if config is missing.
#
# Bug S3-103: Redesigned from bidirectional (mtime-based) to one-way
# (workspace always wins) with safety warnings if repo is newer.

set -euo pipefail

WORKSPACE="$(cd "$(dirname "$0")" && pwd)"

# Read repo paths from .svp/sync_config.json if available
SYNC_CONFIG="$WORKSPACE/.svp/sync_config.json"
if [ -f "$SYNC_CONFIG" ]; then
    REPO="$(python3 -c "import json; print(json.load(open('$SYNC_CONFIG'))['repo'])")"
    PASS1_REPO="$(python3 -c "import json; print(json.load(open('$SYNC_CONFIG')).get('pass1_repo', ''))" 2>/dev/null || echo "")"
else
    # Fallback to relative paths (backward compatibility)
    REPO="$WORKSPACE/../svp2.2-pass2-repo"
    PASS1_REPO="$WORKSPACE/../svp2.2-repo"
fi

DRY_RUN=false
COPIED=0
SKIPPED=0
ERRORS=0

for arg in "$@"; do
    case "$arg" in
        --dry-run)    DRY_RUN=true ;;
        *) echo "Unknown arg: $arg"; exit 1 ;;
    esac
done

# --- helpers ---

get_mtime() {
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
        if [ -f "$dst" ] && [ ! -w "$dst" ]; then
            chmod u+w "$dst"
        fi
        cp "$src" "$dst"
        COPIED=$((COPIED + 1))
        echo "  copied: $label"
    fi
}

sync_one_way() {
    # One-way sync: workspace → repo. Warns if repo is newer.
    local src="$1" dst="$2" label="$3"
    if [ ! -f "$src" ]; then
        return
    fi
    if [ -f "$dst" ] && diff -q "$src" "$dst" > /dev/null 2>&1; then
        return  # identical, nothing to do
    fi
    # Safety check: warn if repo is newer
    if [ -f "$dst" ]; then
        local mt_src mt_dst
        mt_src="$(get_mtime "$src")"
        mt_dst="$(get_mtime "$dst")"
        if [ "$mt_dst" -gt "$mt_src" ]; then
            echo "  [WARN] $label — repo is newer than workspace. Overwriting with workspace version."
        fi
    fi
    sync_file "$src" "$dst" "$label"
}

echo "=== SVP Workspace Sync ==="
echo "Workspace: $WORKSPACE"
echo "Repo:      $REPO"
if [ -n "$PASS1_REPO" ]; then echo "Pass1:     $PASS1_REPO"; fi
if $DRY_RUN; then echo "Mode: DRY RUN"; fi
echo ""

# --- Step 0: Derive scripts from stubs (Bug S3-98) ---
echo "--- Step 0: Derive Scripts from Stubs ---"
if $DRY_RUN; then
    python3 "$WORKSPACE/scripts/derive_scripts_from_stubs.py" --workspace "$WORKSPACE" --dry-run
else
    python3 "$WORKSPACE/scripts/derive_scripts_from_stubs.py" --workspace "$WORKSPACE"
fi
echo ""

# --- Step 1: Scripts (workspace → repo, one-way) ---
echo "--- Step 1: Scripts ---"
for f in "$WORKSPACE"/scripts/*.py; do
    [ -f "$f" ] || continue
    name="$(basename "$f")"
    sync_one_way "$f" "$REPO/svp/scripts/$name" "scripts/$name"
done
echo ""

# --- Step 2: Source units (workspace → repo, one-way) ---
echo "--- Step 2: Source Units ---"
for d in "$WORKSPACE"/src/unit_*/; do
    [ -d "$d" ] || continue
    unit="$(basename "$d")"
    sync_one_way "$d/stub.py" "$REPO/src/$unit/stub.py" "src/$unit/stub.py"
done
echo ""

# --- Step 3: Docs (workspace → repo docs/, one-way) ---
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

# Spec
doc_sync "$WORKSPACE/specs/stakeholder_spec.md" \
    "$REPO/docs/stakeholder_spec.md" \
    "$PASS1_REPO/docs/stakeholder_spec.md"

# Blueprint
doc_sync "$WORKSPACE/blueprint/blueprint_contracts.md" \
    "$REPO/docs/blueprint_contracts.md" \
    "$PASS1_REPO/docs/blueprint_contracts.md"

doc_sync "$WORKSPACE/blueprint/blueprint_prose.md" \
    "$REPO/docs/blueprint_prose.md" \
    "$PASS1_REPO/docs/blueprint_prose.md"

# Blueprint supplementary files
if [ -f "$WORKSPACE/blueprint/regression_test_import_map.json" ]; then
    doc_sync "$WORKSPACE/blueprint/regression_test_import_map.json" \
        "$REPO/docs/regression_test_import_map.json"
fi

# References
doc_sync "$WORKSPACE/references/svp_2_1_lessons_learned.md" \
    "$REPO/docs/references/svp_2_1_lessons_learned.md" \
    "$PASS1_REPO/docs/references/svp_2_1_lessons_learned.md"

if [ -f "$WORKSPACE/references/existing_readme.md" ]; then
    doc_sync "$WORKSPACE/references/existing_readme.md" \
        "$REPO/docs/references/existing_readme.md"
fi

# Workspace root docs → repo docs/ (restore-only artifacts)
doc_sync "$WORKSPACE/CLAUDE.md" \
    "$REPO/docs/CLAUDE.md"

doc_sync "$WORKSPACE/project_context.md" \
    "$REPO/docs/project_context.md"
echo ""

# --- Step 3b: Workspace root files (non-doc) ---
echo "--- Step 3b: Root Files ---"
for rootfile in ruff.toml sync_workspace.sh; do
    if [ -f "$WORKSPACE/$rootfile" ]; then
        if [ ! -f "$REPO/$rootfile" ] || ! diff -q "$WORKSPACE/$rootfile" "$REPO/$rootfile" > /dev/null 2>&1; then
            sync_file "$WORKSPACE/$rootfile" "$REPO/$rootfile" "$rootfile (workspace → repo)"
        fi
    fi
done
echo ""

# --- Step 4: Tests (workspace → repo, one-way) ---
echo "--- Step 4: Tests ---"
(cd "$WORKSPACE" && find tests -name '*.py' -type f 2>/dev/null) | sort > /tmp/svp_ws_tests.txt
(cd "$REPO" && find tests -name '*.py' -type f 2>/dev/null) | sort > /tmp/svp_repo_tests.txt

# Files in both — one-way with warn
comm -12 /tmp/svp_ws_tests.txt /tmp/svp_repo_tests.txt | while read -r tf; do
    sync_one_way "$WORKSPACE/$tf" "$REPO/$tf" "$tf"
done

# Workspace-only → copy to repo
comm -23 /tmp/svp_ws_tests.txt /tmp/svp_repo_tests.txt | while read -r tf; do
    if $DRY_RUN; then
        echo "  [dry-run] cp $tf (workspace-only → repo)"
        COPIED=$((COPIED + 1))
    else
        mkdir -p "$(dirname "$REPO/$tf")"
        cp "$WORKSPACE/$tf" "$REPO/$tf"
        COPIED=$((COPIED + 1))
        echo "  copied: $tf (workspace-only → repo)"
    fi
done

rm -f /tmp/svp_ws_tests.txt /tmp/svp_repo_tests.txt
echo ""

# --- Step 4b: Deployed Artifacts (Bug S3-80) ---
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
    if not repo:
        continue
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

# Verify scripts
for f in "$WORKSPACE"/scripts/*.py; do
    [ -f "$f" ] || continue
    name="$(basename "$f")"
    verify_pair "$f" "$REPO/svp/scripts/$name" "scripts/$name"
done

# Verify stubs
for d in "$WORKSPACE"/src/unit_*/; do
    [ -d "$d" ] || continue
    unit="$(basename "$d")"
    verify_pair "$d/stub.py" "$REPO/src/$unit/stub.py" "src/$unit/stub.py"
done

# Verify docs
verify_pair "$WORKSPACE/specs/stakeholder_spec.md" "$REPO/docs/stakeholder_spec.md" "docs/stakeholder_spec.md"
verify_pair "$WORKSPACE/blueprint/blueprint_contracts.md" "$REPO/docs/blueprint_contracts.md" "docs/blueprint_contracts.md"
verify_pair "$WORKSPACE/blueprint/blueprint_prose.md" "$REPO/docs/blueprint_prose.md" "docs/blueprint_prose.md"
verify_pair "$WORKSPACE/references/svp_2_1_lessons_learned.md" "$REPO/docs/references/svp_2_1_lessons_learned.md" "docs/references/svp_2_1_lessons_learned.md"
verify_pair "$WORKSPACE/CLAUDE.md" "$REPO/docs/CLAUDE.md" "docs/CLAUDE.md"
verify_pair "$WORKSPACE/project_context.md" "$REPO/docs/project_context.md" "docs/project_context.md"

# Verify no scattered dirs in repo
for scattered in "$REPO/specs" "$REPO/blueprint" "$REPO/references"; do
    if [ -d "$scattered" ]; then
        echo "  [WARN] Scattered directory exists: $scattered (should be in docs/)"
        REMAINING=$((REMAINING + 1))
    fi
done
# Verify no doc files at repo root
for rootdoc in "$REPO/CLAUDE.md" "$REPO/project_context.md" "$REPO/blueprint_contracts.md"; do
    if [ -f "$rootdoc" ]; then
        echo "  [WARN] Doc file at repo root: $(basename "$rootdoc") (should be in docs/)"
        REMAINING=$((REMAINING + 1))
    fi
done

if [ "$REMAINING" -eq 0 ]; then
    echo "  All files in sync. Repo layout clean."
else
    echo "  $REMAINING issue(s) found."
fi
echo ""

# --- Summary ---
echo "=== Summary ==="
echo "  Copied:   $COPIED"
echo "  Skipped:  $SKIPPED"
echo "  Errors:   $ERRORS"
if [ "$ERRORS" -gt 0 ]; then
    echo "  !! Resolve errors manually."
    exit 1
fi
echo "  Done."

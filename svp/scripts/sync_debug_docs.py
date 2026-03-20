#!/usr/bin/env python3
"""Post-triage documentation sync script (Bug 87).

Ensures documentation artifacts are consistent across all locations:
1. docs/ -> docs/references/ in the delivered repository (docs/ is authoritative)
2. repo docs/ -> workspace references/ (repo is authoritative after triage)
3. Stages and commits all dirty doc files in the delivered repository.

Usage:
    python scripts/sync_debug_docs.py --project-root .
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Post-triage documentation sync")
    parser.add_argument("--project-root", required=True, help="SVP workspace root")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()

    # Read delivered_repo_path and bug_id from pipeline_state.json
    state_file = project_root / "pipeline_state.json"
    if not state_file.exists():
        print(f"ERROR: {state_file} not found", file=sys.stderr)
        sys.exit(1)

    with open(state_file) as f:
        state = json.load(f)

    repo_path = Path(state.get("delivered_repo_path", ""))
    if not repo_path.exists():
        print(f"ERROR: delivered_repo_path {repo_path} does not exist", file=sys.stderr)
        sys.exit(1)

    bug_id = None
    ds = state.get("debug_session")
    if ds:
        bug_id = ds.get("bug_id")

    # Step 1: Copy docs/ -> docs/references/ in repo (docs/ is authoritative)
    doc_files = [
        "svp_2_1_lessons_learned.md",
        "svp_2_1_summary.md",
    ]

    files_changed = False

    for fname in doc_files:
        src = repo_path / "docs" / fname
        dst = repo_path / "docs" / "references" / fname
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists() or src.read_text() != dst.read_text():
                shutil.copy2(src, dst)
                print(f"Synced repo docs/{fname} -> docs/references/{fname}")
                files_changed = True
            else:
                print(f"Already in sync: docs/{fname} == docs/references/{fname}")

    # Step 2: Copy repo docs/ -> workspace references/
    for fname in doc_files:
        src = repo_path / "docs" / fname
        dst = project_root / "references" / fname
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists() or src.read_text() != dst.read_text():
                shutil.copy2(src, dst)
                print(f"Synced repo docs/{fname} -> workspace references/{fname}")
            else:
                print(f"Already in sync: repo docs/{fname} == workspace references/{fname}")

    # Step 3: Stage and commit dirty doc files in the repo
    stage_candidates = [
        "CHANGELOG.md",
        "README.md",
        "docs/svp_2_1_lessons_learned.md",
        "docs/references/svp_2_1_lessons_learned.md",
        "docs/svp_2_1_summary.md",
        "docs/references/svp_2_1_summary.md",
    ]

    staged = []
    for rel_path in stage_candidates:
        full_path = repo_path / rel_path
        if not full_path.exists():
            continue
        # Check if file has changes (staged or unstaged)
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "--", rel_path],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        result_unstaged = subprocess.run(
            ["git", "diff", "--name-only", "--", rel_path],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        result_untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "--", rel_path],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.stdout.strip() or result_unstaged.stdout.strip() or result_untracked.stdout.strip():
            subprocess.run(["git", "add", rel_path], cwd=repo_path, check=True)
            staged.append(rel_path)
            print(f"Staged: {rel_path}")

    if staged:
        bug_label = f"Bug {bug_id}" if bug_id else "Bug ???"
        commit_msg = f"[SVP-DEBUG] {bug_label}: Documentation updates (lessons learned, changelog, readme, summary)"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=repo_path,
            check=True,
        )
        print(f"Committed {len(staged)} doc file(s): {commit_msg}")
    else:
        print("No dirty doc files to commit.")

    print("COMMAND_SUCCEEDED")


if __name__ == "__main__":
    main()

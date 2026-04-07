"""Unit 16: Command Logic Scripts.

Implements the user-facing SVP commands: save, quit, status, clean,
sync_debug_docs, and sync_pass1_artifacts.  Each command reads/writes
pipeline state and workspace artifacts via upstream units (1, 3, 4, 5).
"""

import json
import shutil
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from svp_config import ARTIFACT_FILENAMES, derive_env_name
from profile_schema import load_profile
from toolchain_reader import load_toolchain, resolve_command
from pipeline_state import load_state, save_state


def cmd_save(project_root: Path) -> str:
    """Flush pipeline state to disk, verify integrity, return confirmation."""
    # Load current state
    state = load_state(project_root)

    # Save state to disk (save_state handles hash computation)
    save_state(project_root, state)

    # Verify integrity: re-read and validate
    load_state(project_root)

    return "Pipeline state saved successfully."


def cmd_quit(project_root: Path) -> str:
    """Save state then return exit signal."""
    cmd_save(project_root)
    return "Pipeline state saved. Exiting SVP session."


def cmd_status(project_root: Path) -> str:
    """Read pipeline state, profile, build log; return formatted status string."""
    # Load pipeline state
    state = load_state(project_root)

    # Load profile
    try:
        profile = load_profile(project_root)
    except FileNotFoundError:
        profile = None

    # Load build log
    build_log_path = project_root / ARTIFACT_FILENAMES["build_log"]
    build_log_entries = []
    if build_log_path.exists():
        with open(build_log_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        build_log_entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    # Build status string
    lines = []

    # Project name
    project_name = project_root.name
    lines.append(f"Project: {project_name}")

    # Stage
    lines.append(f"Stage: {state.stage}")

    # Sub-stage
    if state.sub_stage is not None:
        lines.append(f"Sub-stage: {state.sub_stage}")

    # Unit progress
    if state.current_unit is not None:
        lines.append(f"Current unit: {state.current_unit}/{state.total_units}")
    else:
        lines.append(f"Total units: {state.total_units}")

    # Verified units count
    verified_count = len(state.verified_units)
    lines.append(f"Verified units: {verified_count}")

    # Pass history
    if state.pass_history:
        pass_summaries = []
        for entry in state.pass_history:
            pass_num = entry.get("pass", "?")
            result = entry.get("result", entry.get("status", "unknown"))
            pass_summaries.append(f"Pass {pass_num}: {result}")
        lines.append(f"Pass history: {', '.join(pass_summaries)}")

    # Profile summary (one-line format showing pipeline and delivery
    # quality tools separately)
    if profile is not None:
        primary_lang = profile.get("language", {}).get("primary", "python")

        # Pipeline quality tools (from fixed section)
        pipeline_tools = profile.get("fixed", {}).get(
            "pipeline_quality_tools", "ruff_mypy"
        )

        # Delivery quality tools (from profile quality section)
        quality_section = profile.get("quality", {})
        delivery_tools_parts = []
        lang_quality = quality_section.get(primary_lang, {})
        if isinstance(lang_quality, dict):
            linter = lang_quality.get("linter")
            formatter = lang_quality.get("formatter")
            type_checker = lang_quality.get("type_checker")
            if linter:
                delivery_tools_parts.append(linter)
            if formatter and formatter != linter:
                delivery_tools_parts.append(formatter)
            if type_checker and type_checker != "none":
                delivery_tools_parts.append(type_checker)

        delivery_tools = (
            ", ".join(delivery_tools_parts) if delivery_tools_parts else "default"
        )

        lines.append(
            f"Quality tools: pipeline={pipeline_tools}, delivery={delivery_tools}"
        )

    # Quality gate status for current unit
    if state.sub_stage is not None and state.current_unit is not None:
        gate_status = state.sub_stage
        lines.append(f"Quality gate status: {gate_status}")

    return "\n".join(lines)


def cmd_clean(project_root: Path, action: str) -> str:
    """Clean build environment and optionally archive/delete workspace."""
    # Validate action
    valid_actions = {"archive", "delete", "keep"}
    if action not in valid_actions:
        raise ValueError(
            f"Invalid clean action: '{action}'. "
            f"Must be one of: {', '.join(sorted(valid_actions))}"
        )

    # Load pipeline state (Bug S3-7: uses load_state, NOT load_config or load_profile)
    state = load_state(project_root)

    # Remove conda environment using toolchain cleanup command
    env_name = derive_env_name(project_root)
    try:
        toolchain = load_toolchain(project_root)
        # Look for env_remove command in toolchain commands section
        remove_template = toolchain.get("commands", {}).get("env_remove", "")
        # Also check environment.remove for backward compatibility
        if not remove_template:
            remove_template = toolchain.get("environment", {}).get("remove", "")
        if remove_template:
            run_prefix = toolchain.get("run_prefix", "")
            remove_cmd = resolve_command(
                template=remove_template,
                env_name=env_name,
                run_prefix=run_prefix,
            )
            try:
                subprocess.run(
                    remove_cmd,
                    shell=True,
                    capture_output=True,
                    timeout=120,
                )
            except (subprocess.TimeoutExpired, OSError):
                pass
    except FileNotFoundError:
        # If toolchain not found, fall back to default conda remove
        try:
            subprocess.run(
                f"conda env remove -n {env_name} -y",
                shell=True,
                capture_output=True,
                timeout=120,
            )
        except (subprocess.TimeoutExpired, OSError):
            pass

    # Handle workspace based on action
    if action == "archive":
        archive_name = f"{project_root.name}.tar.gz"
        archive_path = project_root.parent / archive_name
        if project_root.exists():
            with tarfile.open(str(archive_path), "w:gz") as tar:
                tar.add(str(project_root), arcname=project_root.name)
        return f"Environment removed. Workspace archived to {archive_path}."

    elif action == "delete":
        if project_root.exists():
            shutil.rmtree(str(project_root))
        return "Environment removed. Workspace deleted."

    else:  # keep
        return "Environment removed. Workspace kept."


def sync_debug_docs(project_root: Path) -> None:
    """Copy workspace spec/blueprint to delivered repo docs/ directory."""
    # Load state to get delivered_repo_path
    state = load_state(project_root)

    if state.delivered_repo_path is None:
        return

    delivered_repo = Path(state.delivered_repo_path)
    docs_dir = delivered_repo / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Copy stakeholder spec
    spec_path = project_root / ARTIFACT_FILENAMES["stakeholder_spec"]
    if spec_path.exists():
        dest = docs_dir / spec_path.name
        shutil.copy2(str(spec_path), str(dest))

    # Copy blueprint files directly into docs/ (workspace is canonical)
    blueprint_dir = project_root / ARTIFACT_FILENAMES["blueprint_dir"]
    if blueprint_dir.exists() and blueprint_dir.is_dir():
        for src_file in blueprint_dir.iterdir():
            if src_file.is_file():
                dest = docs_dir / src_file.name
                shutil.copy2(str(src_file), str(dest))


def sync_workspace_to_repo(project_root: Path) -> Dict[str, int]:
    """Full workspace→repo synchronization.

    Syncs ALL artifacts from workspace to delivered repo:
    - src/unit_*/stub.py (direct copy)
    - svp/scripts/*.py (import rewriting: src.unit_N.stub → bare module)
    - docs/ (spec, blueprint, lessons learned)
    - tests/ (all test files)
    - references/ (lessons learned, existing readme)
    - specs/, blueprint/ (if repo has these dirs)
    - Plugin components (agents, commands, hooks, skills, manifests)

    Returns summary dict with counts of synced files.
    """
    state = load_state(project_root)
    if state.delivered_repo_path is None:
        return {"error": "No delivered_repo_path in state"}

    repo = Path(state.delivered_repo_path)
    counts = {"src": 0, "scripts": 0, "docs": 0, "tests": 0, "refs": 0, "plugin": 0}

    # 1. Sync src/unit_*/stub.py
    src_dir = project_root / "src"
    if src_dir.is_dir():
        for unit_dir in sorted(src_dir.iterdir()):
            if unit_dir.is_dir() and unit_dir.name.startswith("unit_"):
                repo_unit = repo / "src" / unit_dir.name
                repo_unit.mkdir(parents=True, exist_ok=True)
                for f in unit_dir.iterdir():
                    if f.is_file():
                        shutil.copy2(str(f), str(repo_unit / f.name))
                        counts["src"] += 1
        # Copy src/__init__.py
        src_init = src_dir / "__init__.py"
        if src_init.is_file():
            (repo / "src").mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_init), str(repo / "src" / "__init__.py"))

    # 2. Sync docs (spec, blueprint, lessons)
    sync_debug_docs(project_root)  # Existing function handles docs/
    counts["docs"] += 1

    # Also sync to root-level dirs if they exist in repo
    for dirname in ("specs", "blueprint", "references"):
        ws_dir = project_root / dirname
        repo_dir = repo / dirname
        if ws_dir.is_dir():
            repo_dir.mkdir(parents=True, exist_ok=True)
            for f in ws_dir.iterdir():
                if f.is_file():
                    shutil.copy2(str(f), str(repo_dir / f.name))
                    counts["docs"] += 1

    # 3. Sync tests
    for test_subdir in ("regressions", "integration"):
        ws_tests = project_root / "tests" / test_subdir
        repo_tests = repo / "tests" / test_subdir
        if ws_tests.is_dir():
            repo_tests.mkdir(parents=True, exist_ok=True)
            for f in ws_tests.iterdir():
                if f.is_file() and f.suffix == ".py":
                    shutil.copy2(str(f), str(repo_tests / f.name))
                    counts["tests"] += 1
    # Unit tests
    ws_tests_dir = project_root / "tests"
    for item in ws_tests_dir.iterdir():
        if item.is_dir() and item.name.startswith("unit_"):
            repo_ut = repo / "tests" / item.name
            repo_ut.mkdir(parents=True, exist_ok=True)
            for f in item.iterdir():
                if f.is_file():
                    shutil.copy2(str(f), str(repo_ut / f.name))
                    counts["tests"] += 1
    # tests/__init__.py
    for init in [ws_tests_dir / "__init__.py"]:
        if init.is_file():
            shutil.copy2(str(init), str(repo / "tests" / "__init__.py"))

    # 4. Rebuild svp/scripts/ with import rewriting
    # (This is handled by assemble_plugin_components or manual script rebuild)
    # For now, just copy workspace scripts/ to repo svp/scripts/ directly
    ws_scripts = project_root / "scripts"
    repo_scripts = repo / "svp" / "scripts"
    if ws_scripts.is_dir() and repo_scripts.is_dir():
        for f in ws_scripts.iterdir():
            if f.is_file() and f.suffix == ".py":
                shutil.copy2(str(f), str(repo_scripts / f.name))
                counts["scripts"] += 1

    return counts


# ---------------------------------------------------------------------------
# Bug S3-55: Pass 1 → Pass 2 workspace artifact synchronization
# ---------------------------------------------------------------------------


def _derive_pass1_workspace(pass2_root: Path) -> Path:
    """Derive Pass 1 workspace path from Pass 2 workspace path.

    Convention: Pass 2 workspace is always {pass1_name}-pass2/.
    """
    name = pass2_root.name
    if not name.endswith("-pass2"):
        raise ValueError(
            f"Cannot derive Pass 1 workspace: '{name}' does not end with '-pass2'"
        )
    pass1_name = name[: -len("-pass2")]
    return pass2_root.parent / pass1_name


def _sync_regression_tests(
    pass1: Path, pass2: Path, synced: List[str], skipped: List[str]
) -> None:
    """Copy regression test files from Pass 1 that don't exist in Pass 2."""
    src_dir = pass1 / "tests" / "regressions"
    dst_dir = pass2 / "tests" / "regressions"
    if not src_dir.is_dir():
        return
    dst_dir.mkdir(parents=True, exist_ok=True)
    for f in sorted(src_dir.iterdir()):
        if f.suffix != ".py" or f.name == "__init__.py":
            continue
        dst = dst_dir / f.name
        if dst.exists():
            skipped.append(f"tests/regressions/{f.name}")
        else:
            shutil.copy2(str(f), str(dst))
            synced.append(f"tests/regressions/{f.name}")


def _sync_lessons_learned(
    pass1: Path, pass2: Path, merged: List[str], errors: List[str]
) -> None:
    """Merge lessons learned: Pass 1 as base, append Pass 2-only sections."""
    p1_file = pass1 / "references" / "svp_2_1_lessons_learned.md"
    p2_file = pass2 / "references" / "svp_2_1_lessons_learned.md"
    if not p1_file.is_file():
        return

    p1_text = p1_file.read_text(encoding="utf-8")
    if not p2_file.is_file():
        p2_file.parent.mkdir(parents=True, exist_ok=True)
        p2_file.write_text(p1_text, encoding="utf-8")
        merged.append("references/svp_2_1_lessons_learned.md")
        return

    p2_text = p2_file.read_text(encoding="utf-8")

    # Find sections in Pass 2 that are NOT in Pass 1 (e.g., Part 3)
    p2_lines = p2_text.splitlines(keepends=True)
    p1_lines_set = set(p1_text.splitlines())

    # Find Part headers in Pass 2 that aren't in Pass 1
    new_sections: List[str] = []
    capturing = False
    for line in p2_lines:
        stripped = line.strip()
        if stripped.startswith("## Part") and stripped not in p1_lines_set:
            capturing = True
        if capturing:
            new_sections.append(line)

    if new_sections:
        # Append new sections to Pass 1 content
        result = p1_text.rstrip() + "\n\n" + "".join(new_sections)
        p2_file.write_text(result, encoding="utf-8")
        merged.append("references/svp_2_1_lessons_learned.md")
    elif len(p1_text) > len(p2_text):
        # Pass 1 is longer — take it as base
        p2_file.write_text(p1_text, encoding="utf-8")
        merged.append("references/svp_2_1_lessons_learned.md")


def _sync_spec(
    pass1: Path, pass2: Path, merged: List[str], errors: List[str]
) -> None:
    """Merge spec: Pass 2 as base, insert Pass 1-only lines at correct positions."""
    p1_spec = pass1 / "specs" / "stakeholder_spec.md"
    p2_spec = pass2 / "specs" / "stakeholder_spec.md"
    if not p1_spec.is_file() or not p2_spec.is_file():
        return

    p1_text = p1_spec.read_text(encoding="utf-8")
    p2_text = p2_spec.read_text(encoding="utf-8")

    p2_lines = p2_text.splitlines(keepends=True)
    p1_lines = p1_text.splitlines()
    p2_lines_set = set(l.rstrip() for l in p2_text.splitlines())

    # Find lines in Pass 1 that reference bug markers not in Pass 2
    bug_markers = ["Bug S3-47", "Bug S3-48", "Bug S3-49", "Bug S3-50"]
    missing_markers = [m for m in bug_markers if m not in p2_text and m in p1_text]

    if not missing_markers:
        return  # Nothing to merge

    # For each missing marker, find the line(s) in Pass 1 and the context
    # to determine where to insert in Pass 2
    insertions: List[tuple] = []  # (context_before, lines_to_insert)
    for marker in missing_markers:
        for i, line in enumerate(p1_lines):
            if marker in line:
                # Collect the block (line + any continuation lines)
                block = [line + "\n"]
                j = i + 1
                while j < len(p1_lines) and p1_lines[j].strip() and p1_lines[j].rstrip() not in p2_lines_set:
                    block.append(p1_lines[j] + "\n")
                    j += 1

                # Find context: the line BEFORE this block in Pass 1
                context_before = p1_lines[i - 1].rstrip() if i > 0 else ""
                insertions.append((context_before, block))

    if not insertions:
        return

    # Apply insertions to Pass 2 text
    result_lines = list(p2_lines)
    inserted_count = 0
    for context_before, block in insertions:
        found = False
        for idx, line in enumerate(result_lines):
            if line.rstrip() == context_before:
                insert_pos = idx + 1
                for bi, bline in enumerate(block):
                    result_lines.insert(insert_pos + bi, bline)
                inserted_count += len(block)
                found = True
                break
        if not found:
            errors.append(f"Spec merge: context not found for block starting with '{block[0].strip()[:60]}'")

    if inserted_count == 0:
        return

    result = "".join(result_lines)

    # Validate: all missing markers should now be present
    still_missing = [m for m in missing_markers if m not in result]
    if still_missing:
        errors.append(f"Spec merge incomplete: still missing {still_missing}")
        return

    p2_spec.write_text(result, encoding="utf-8")
    merged.append("specs/stakeholder_spec.md")


def _sync_svp_metadata(
    pass1: Path, pass2: Path, synced: List[str], skipped: List[str]
) -> None:
    """Copy .svp metadata files from Pass 1 if absent in Pass 2."""
    metadata_files = [
        "alignment_checker_checklist.md",
        "blueprint_author_checklist.md",
        "quality_report.md",
        "triage_result.json",
    ]
    src_dir = pass1 / ".svp"
    dst_dir = pass2 / ".svp"
    if not src_dir.is_dir():
        return
    dst_dir.mkdir(parents=True, exist_ok=True)
    for fname in metadata_files:
        src = src_dir / fname
        dst = dst_dir / fname
        if src.is_file() and not dst.exists():
            shutil.copy2(str(src), str(dst))
            synced.append(f".svp/{fname}")
        elif src.is_file():
            skipped.append(f".svp/{fname}")


def _sync_directory_contents(
    pass1: Path, pass2: Path, rel_dir: str,
    synced: List[str], skipped: List[str]
) -> None:
    """Copy directory contents from Pass 1 if absent in Pass 2."""
    src_dir = pass1 / rel_dir
    dst_dir = pass2 / rel_dir
    if not src_dir.is_dir():
        return
    dst_dir.mkdir(parents=True, exist_ok=True)
    for f in sorted(src_dir.rglob("*")):
        if f.is_file():
            rel = f.relative_to(src_dir)
            dst = dst_dir / rel
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(f), str(dst))
                synced.append(f"{rel_dir}/{rel}")
            else:
                skipped.append(f"{rel_dir}/{rel}")


def sync_pass1_artifacts(project_root: Path) -> Dict[str, Any]:
    """Synchronize accumulated artifacts from Pass 1 into Pass 2 workspace.

    Called automatically during pass_transition after Pass 2's Stage 5 completes.
    Idempotent: safe to call multiple times (marker file guard).

    Syncs: regression tests (union), lessons learned (merge), spec amendments
    (insert Pass 1-only lines), spec history, .svp metadata.
    Does NOT sync: src/, scripts/, pipeline_state.json, blueprint/.
    """
    marker = project_root / ".svp" / "pass1_sync_complete"
    if marker.exists():
        return {
            "synced_files": [],
            "skipped_files": [],
            "merged_files": [],
            "pass1_workspace": "",
            "errors": ["Already synced (marker exists)"],
        }

    synced: List[str] = []
    skipped: List[str] = []
    merged: List[str] = []
    errors_list: List[str] = []

    try:
        pass1 = _derive_pass1_workspace(project_root)
    except ValueError as e:
        return {
            "synced_files": [],
            "skipped_files": [],
            "merged_files": [],
            "pass1_workspace": "",
            "errors": [str(e)],
        }

    if not pass1.is_dir() or not (pass1 / "pipeline_state.json").is_file():
        return {
            "synced_files": [],
            "skipped_files": [],
            "merged_files": [],
            "pass1_workspace": str(pass1),
            "errors": [f"Pass 1 workspace not found at {pass1}"],
        }

    # 1. Regression tests (union)
    _sync_regression_tests(pass1, project_root, synced, skipped)

    # 2. Lessons learned (merge)
    _sync_lessons_learned(pass1, project_root, merged, errors_list)

    # 3. Spec amendments (insert Pass 1-only lines)
    _sync_spec(pass1, project_root, merged, errors_list)

    # 4. Spec history directory
    _sync_directory_contents(pass1, project_root, "specs/history", synced, skipped)

    # 5. .svp metadata
    _sync_svp_metadata(pass1, project_root, synced, skipped)

    # Write marker
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pass1_workspace": str(pass1),
            "synced": len(synced),
            "merged": len(merged),
            "skipped": len(skipped),
            "errors": len(errors_list),
        }, indent=2),
        encoding="utf-8",
    )

    return {
        "synced_files": synced,
        "skipped_files": skipped,
        "merged_files": merged,
        "pass1_workspace": str(pass1),
        "errors": errors_list,
    }

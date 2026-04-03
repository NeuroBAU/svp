"""cmd_save.py -- SVP save command.

Flushes pending pipeline state and verifies file integrity.
Contains shared command logic for all Group A commands.

Part of Unit 16: Command Logic Scripts.
"""

import json
import shutil
import subprocess
import tarfile
from pathlib import Path

from pipeline_state import load_state, save_state
from profile_schema import load_profile
from svp_config import ARTIFACT_FILENAMES, derive_env_name
from toolchain_reader import load_toolchain, resolve_command


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

    # Remove conda environment using toolchain cleanup command
    env_name = derive_env_name(project_root)
    try:
        toolchain = load_toolchain(project_root)
        remove_template = toolchain.get("environment", {}).get("remove", "")
        if remove_template:
            remove_cmd = resolve_command(
                template=remove_template,
                env_name=env_name,
                run_prefix="",
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
        with tarfile.open(str(archive_path), "w:gz") as tar:
            tar.add(str(project_root), arcname=project_root.name)
        return f"Environment removed. Workspace archived to {archive_path}."

    elif action == "delete":
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

    # Copy blueprint files
    blueprint_dir = project_root / ARTIFACT_FILENAMES["blueprint_dir"]
    if blueprint_dir.exists() and blueprint_dir.is_dir():
        dest_blueprint = docs_dir / "blueprint"
        if dest_blueprint.exists():
            shutil.rmtree(str(dest_blueprint))
        shutil.copytree(str(blueprint_dir), str(dest_blueprint))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SVP Save Command")
    parser.add_argument("--project-root", type=str, default=".")
    args = parser.parse_args()
    print(cmd_save(Path(args.project_root).resolve()))

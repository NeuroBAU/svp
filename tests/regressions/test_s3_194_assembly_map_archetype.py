"""Cycle H4 (S3-194) -- pin the assembly_map archetype boundary:

- assemble_python_project (the Python-self-build path) generates
  .svp/assembly_map.json via generate_assembly_map.
- assemble_r_project does NOT generate it (R archetype implicit tracking).
- validate_delivered_repo_contents Check 2 silently passes when no map exists.
- Map values match ^src/unit_\\d+/stub\\.py$ (locked Python-self-build shape).

Closes IMPROV-28 by documenting and locking current architectural behavior.
H4 makes ZERO code changes; tests pin the existing assembly_map archetype
boundary so future cycles cannot regress it silently.

S3-103 honors flat-module imports (no src.unit_*.stub import).
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict

import pytest

from generate_assembly_map import (
    assemble_python_project,
    assemble_r_project,
    generate_assembly_map,
)
from structural_check import validate_delivered_repo_contents


STUB_PATH_RE = re.compile(r"^src/unit_\d+/stub\.py$")


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _project_root_with_r_toolchain(tmp_path: Path) -> Path:
    """Mirror H2/H3 fixture: copy the canonical r_conda_testthat manifest
    under tmp_path/scripts/toolchain_defaults/ so load_toolchain resolves.
    """
    here = Path(__file__).resolve()
    candidates = [
        ancestor / "scripts" / "toolchain_defaults"
        for ancestor in [here, *here.parents]
    ] + [
        ancestor / "svp" / "scripts" / "toolchain_defaults"
        for ancestor in [here, *here.parents]
    ]
    src_dir: Path | None = None
    for candidate in candidates:
        if (candidate / "r_conda_testthat.json").is_file():
            src_dir = candidate
            break
    dst = tmp_path / "scripts" / "toolchain_defaults"
    dst.mkdir(parents=True, exist_ok=True)
    if src_dir is not None:
        for fname in ("r_conda_testthat.json",):
            src_file = src_dir / fname
            if src_file.is_file():
                shutil.copy2(src_file, dst / fname)
    return tmp_path


@pytest.fixture
def r_profile() -> Dict[str, Any]:
    return {
        "archetype": "pure_r",
        "language": {"primary": "r"},
        "delivery": {"r": {"roxygen2": True}},
        "license": {"type": "MIT", "holder": "Acme Corp"},
        "author": "Test User",
        "description": "A test R package",
        "quality": {},
        "testing": {},
        "readme": {},
        "vcs": {"provider": "github"},
        "pipeline": {},
    }


@pytest.fixture
def r_assembly_config() -> Dict[str, Any]:
    return {"project_name": "myrproj", "description": "A test R package"}


@pytest.fixture
def python_profile() -> Dict[str, Any]:
    return {
        "archetype": "pure_python",
        "language": {
            "primary": "python",
            "secondary": None,
            "components": [],
            "communication": None,
            "notebooks": False,
        },
        "delivery": {
            "python": {
                "source_layout": "conventional",
                "entry_points": True,
            },
        },
        "quality": {},
        "testing": {},
        "readme": {},
        "license": "MIT",
        "vcs": {"provider": "github"},
        "pipeline": {},
    }


@pytest.fixture
def python_assembly_config() -> Dict[str, Any]:
    return {
        "project_name": "py_proj",
        "description": "A test Python project",
        "author": "Test Author",
    }


@pytest.fixture
def minimal_r_workspace(tmp_path: Path) -> Path:
    """Synthetic R-package workspace at tmp_path/myrproj."""
    project_root = _project_root_with_r_toolchain(tmp_path)
    workspace = project_root / "myrproj"
    workspace.mkdir()
    (workspace / "R").mkdir()
    (workspace / "R" / "foo.R").write_text("foo <- function() 1\n")
    (workspace / "tests" / "testthat").mkdir(parents=True)
    (workspace / "DESCRIPTION").write_text(
        "Package: myrproj\nVersion: 0.1\n"
    )
    # Replicate toolchain defaults underneath the workspace so
    # load_toolchain(project_root=workspace, language="r") resolves.
    src = project_root / "scripts" / "toolchain_defaults"
    dst = workspace / "scripts" / "toolchain_defaults"
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.glob("*.json"):
        shutil.copy2(f, dst / f.name)
    return workspace


@pytest.fixture
def minimal_python_workspace(tmp_path: Path) -> Path:
    """Synthetic Python workspace at tmp_path/py_proj."""
    workspace = tmp_path / "py_proj"
    workspace.mkdir()
    (workspace / ".svp").mkdir()
    (workspace / "tests").mkdir()
    (workspace / "tests" / "test_basic.py").write_text(
        "def test_basic(): assert True\n"
    )
    return workspace


def _make_python_self_build_workspace(tmp_path: Path) -> tuple[Path, Path]:
    """Build a Python-self-build-shaped workspace: a project_root with a
    blueprint_prose.md containing a file-tree code block with `<- Unit N`
    annotations and a .svp directory ready to receive assembly_map.json.

    Returns (project_root, blueprint_dir). Mirrors the
    test_assembly_map_generation.py fixture shape.
    """
    project_root = tmp_path / "self_build"
    project_root.mkdir()
    (project_root / ".svp").mkdir()
    blueprint_dir = project_root / "blueprint"
    blueprint_dir.mkdir()
    (blueprint_dir / "blueprint_prose.md").write_text(
        "## Preamble\n"
        "\n"
        "```\n"
        "svp/\n"
        "  scripts/\n"
        "    routing.py             <- Unit 14\n"
        "    pipeline_state.py      <- Unit 5\n"
        "    hooks.py               <- Unit 17\n"
        "```\n"
    )
    return project_root, blueprint_dir


def _make_validate_project(
    tmp_path: Path,
    language: str,
    delivered_files: list[str],
) -> Path:
    """Mirror H3's _make_validate_project helper: build synthetic project_root
    plus a sibling delivered repo, populate the delivered repo with the
    requested relative file paths, and write profile + state with
    delivered_repo_path set.
    """
    project_root = tmp_path / "myproj"
    project_root.mkdir()
    (project_root / ".svp").mkdir()

    profile = {
        "archetype": f"{language}_project",
        "language": {"primary": language},
    }
    (project_root / "project_profile.json").write_text(json.dumps(profile))

    sibling = tmp_path / "myproj-repo"
    sibling.mkdir()
    for rel in delivered_files:
        f = sibling / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("placeholder")

    state_data = {
        "stage": "5",
        "sub_stage": "compliance_scan",
        "delivered_repo_path": str(sibling),
    }
    (project_root / ".svp" / "pipeline_state.json").write_text(
        json.dumps(state_data)
    )
    return project_root


# ---------------------------------------------------------------------------
# Test 1: R archetype does NOT generate assembly_map
# ---------------------------------------------------------------------------


def test_h4_r_archetype_does_not_generate_assembly_map(
    minimal_r_workspace, r_profile, r_assembly_config
):
    """assemble_r_project on an R workspace MUST NOT produce
    .svp/assembly_map.json (the assembly_map archetype boundary).
    """
    # Sanity: the .svp/assembly_map.json must not pre-exist.
    pre_map = minimal_r_workspace / ".svp" / "assembly_map.json"
    assert not pre_map.exists()

    assemble_r_project(minimal_r_workspace, r_profile, r_assembly_config)

    post_map = minimal_r_workspace / ".svp" / "assembly_map.json"
    assert not post_map.exists(), (
        "assemble_r_project must NOT produce .svp/assembly_map.json -- this "
        "is the assembly_map archetype boundary contract (R archetype "
        "implicit source-file tracking via _copy_r_project_sources, S3-191)"
    )


# ---------------------------------------------------------------------------
# Test 2: Python self-build path DOES generate assembly_map
# ---------------------------------------------------------------------------


def test_h4_python_archetype_does_generate_assembly_map(tmp_path):
    """generate_assembly_map (the Python-self-build path entry point) MUST
    produce .svp/assembly_map.json at project_root with the locked
    repo_to_workspace schema. This is the regression guard for the
    Python-self-build branch of the assembly_map archetype boundary.
    """
    project_root, blueprint_dir = _make_python_self_build_workspace(tmp_path)

    result = generate_assembly_map(blueprint_dir, project_root)

    map_path = project_root / ".svp" / "assembly_map.json"
    assert map_path.is_file(), (
        "generate_assembly_map (Python-self-build path) MUST write "
        ".svp/assembly_map.json at project_root"
    )
    parsed = json.loads(map_path.read_text(encoding="utf-8"))
    assert "repo_to_workspace" in parsed
    assert isinstance(parsed["repo_to_workspace"], dict)
    # In-memory return value matches on-disk contents.
    assert result["repo_to_workspace"] == parsed["repo_to_workspace"]


# ---------------------------------------------------------------------------
# Test 3: Check 2 silently passes when no assembly_map exists
# ---------------------------------------------------------------------------


def test_h4_validate_check2_silently_passes_when_no_assembly_map(tmp_path):
    """validate_delivered_repo_contents on a delivered repo with no
    .svp/assembly_map.json MUST emit no Check-2 (assembly-map parity)
    findings -- this is the silent-pass contract A-D archetypes rely on.
    """
    project_root = _make_validate_project(
        tmp_path,
        language="python",
        delivered_files=[
            "pyproject.toml",
            "README.md",
            "CHANGELOG.md",
            "LICENSE",
            ".gitignore",
            "environment.yml",
        ],
    )
    # Sanity: no assembly_map exists at project_root.
    assert not (project_root / ".svp" / "assembly_map.json").exists()

    findings = validate_delivered_repo_contents(project_root)
    messages = [f["message"] for f in findings]
    assembly_map_findings = [
        m for m in messages if "assembly_map" in m
    ]
    assert assembly_map_findings == [], (
        "Check 2 MUST silently pass when .svp/assembly_map.json is absent; "
        f"unexpected findings: {assembly_map_findings}"
    )


# ---------------------------------------------------------------------------
# Test 4: Check 2 fires on stale entries when map IS present
# ---------------------------------------------------------------------------


def test_h4_validate_check2_fires_when_assembly_map_has_stale_entries(
    tmp_path,
):
    """Synthetic delivered repo + Python-shaped assembly_map.json declaring
    one valid path AND one non-existent path -- Check 2 MUST report the
    stale entry. Regression guard for the SVP-self-build path.
    """
    project_root = _make_validate_project(
        tmp_path,
        language="python",
        delivered_files=[
            "pyproject.toml",
            "README.md",
            "CHANGELOG.md",
            "LICENSE",
            ".gitignore",
            "environment.yml",
            # Valid mapped target the assembly_map will reference.
            "svp/scripts/routing.py",
        ],
    )

    # Author a Python-self-build-shaped assembly_map at project_root with one
    # valid path and one stale (non-existent) path.
    assembly_map = {
        "repo_to_workspace": {
            "svp-repo/svp/scripts/routing.py": "src/unit_14/stub.py",
            "svp-repo/svp/scripts/missing_stub.py": "src/unit_99/stub.py",
        }
    }
    map_path = project_root / ".svp" / "assembly_map.json"
    map_path.write_text(json.dumps(assembly_map))

    findings = validate_delivered_repo_contents(project_root)
    stale_findings = [
        f for f in findings
        if "missing_stub.py" in f["message"]
        and "assembly_map.json" in f["message"]
    ]
    assert stale_findings, (
        "Check 2 MUST report stale entries when the assembly_map declares "
        "paths that do not exist under delivered_repo_path; got findings: "
        f"{[f['message'] for f in findings]}"
    )


# ---------------------------------------------------------------------------
# Test 5: R archetype path through Check 2 is silent-pass
# ---------------------------------------------------------------------------


def test_h4_validate_check2_handles_r_archetype_correctly(tmp_path):
    """R-archetype delivered repo with no assembly_map.json + R-archetype
    profile -- Check 2 silently passes. The architectural boundary contract
    end-to-end: R archetypes don't ship an assembly_map; the parity check
    must not penalize them.
    """
    project_root = _make_validate_project(
        tmp_path,
        language="r",
        delivered_files=[
            "DESCRIPTION",
            "NAMESPACE",
            "README.md",
            "LICENSE",
            ".gitignore",
            "environment.yml",
            "NEWS.md",
        ],
    )
    # Sanity: no assembly_map exists for this R archetype project.
    assert not (project_root / ".svp" / "assembly_map.json").exists()

    findings = validate_delivered_repo_contents(project_root)
    messages = [f["message"] for f in findings]
    assembly_map_findings = [
        m for m in messages if "assembly_map" in m
    ]
    assert assembly_map_findings == [], (
        "R-archetype profile + no assembly_map.json + delivered repo with "
        "all required R files MUST yield zero assembly_map-related "
        f"findings; unexpected: {assembly_map_findings}"
    )


# ---------------------------------------------------------------------------
# Test 6: Generated assembly_map values match the locked Python-self-build
#         shape (^src/unit_\d+/stub\.py$).
# ---------------------------------------------------------------------------


def test_h4_assembly_map_value_shape_is_python_self_build(tmp_path):
    """Any generated assembly_map.json has values matching the locked
    Python-self-build shape ^src/unit_\\d+/stub\\.py$ (Bug S3-111
    invariant). Regression guard against future cycles that change the
    value shape without preserving backward compatibility.
    """
    project_root, blueprint_dir = _make_python_self_build_workspace(tmp_path)

    generate_assembly_map(blueprint_dir, project_root)

    map_path = project_root / ".svp" / "assembly_map.json"
    assert map_path.is_file()
    parsed = json.loads(map_path.read_text(encoding="utf-8"))
    r2w = parsed.get("repo_to_workspace", {})
    assert r2w, "assembly_map repo_to_workspace must be non-empty"
    for repo_path, workspace_value in r2w.items():
        assert STUB_PATH_RE.match(workspace_value), (
            f"assembly_map value {workspace_value!r} for {repo_path!r} "
            f"must match ^src/unit_\\d+/stub\\.py$ -- the locked "
            f"Python-self-build shape per Bug S3-111. Future R-archetype "
            f"assembly_map work MUST preserve this shape for "
            f"backward compatibility."
        )

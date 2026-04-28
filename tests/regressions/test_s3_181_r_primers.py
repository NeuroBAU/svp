"""Regression test for Bug S3-181 — author R architectural primers.

Cycle E1 ships five archetype-conditional primer markdowns at
``scripts/primers/r/*.md`` and populates the ``language_architecture_primers``
field in both R toolchain manifests with paths to those files.

The tests below pin three invariants:

1. The five primer files exist on disk under both workspace and repo layouts.
2. The two R manifests reference primer files that resolve to existing files
   on disk.
3. The schema validator rejects a manifest whose primer path does not resolve.

Pattern reference: P65 (Language-Archetype-Specific Architectural Knowledge In
Primer Files External To Agent Definitions).
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Path resolvers (dual-layout: workspace OR repo)
# ---------------------------------------------------------------------------


def _project_root() -> Path:
    """Walk up from this test file to find the project/repo root.

    Project root is detected by presence of either:
      - workspace layout: scripts/toolchain_defaults/
      - repo layout: svp/scripts/toolchain_defaults/
    """
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "scripts" / "toolchain_defaults").is_dir():
            return parent
        if (parent / "svp" / "scripts" / "toolchain_defaults").is_dir():
            return parent
    raise RuntimeError("Could not locate project root containing scripts/toolchain_defaults/")


def _primers_dir() -> Path:
    """Locate scripts/primers/r/ under either workspace or repo layout."""
    root = _project_root()
    ws = root / "scripts" / "primers" / "r"
    if ws.is_dir():
        return ws
    repo = root / "svp" / "scripts" / "primers" / "r"
    if repo.is_dir():
        return repo
    raise RuntimeError(
        f"Could not locate scripts/primers/r under {root} (tried workspace + repo layouts)"
    )


def _manifests_dir() -> Path:
    root = _project_root()
    ws = root / "scripts" / "toolchain_defaults"
    if ws.is_dir():
        return ws
    repo = root / "svp" / "scripts" / "toolchain_defaults"
    if repo.is_dir():
        return repo
    raise RuntimeError("manifests dir not found")


def _validator_script() -> Path:
    root = _project_root()
    ws = root / "scripts" / "validate_toolchain_schema.py"
    if ws.is_file():
        return ws
    repo = root / "svp" / "scripts" / "validate_toolchain_schema.py"
    if repo.is_file():
        return repo
    raise RuntimeError("validator script not found")


def _resolve_primer_path(relative: str) -> Path:
    """Resolve a primer path string from a manifest against either layout.

    Manifest paths are written workspace-relative
    (e.g. ``scripts/primers/r/blueprint_author.md``); the repo layout
    flattens that under ``svp/`` (e.g. ``svp/scripts/primers/r/blueprint_author.md``).
    Try both before declaring a miss.
    """
    root = _project_root()
    direct = root / relative
    if direct.is_file():
        return direct
    via_svp = root / "svp" / relative
    if via_svp.is_file():
        return via_svp
    return direct  # caller will surface the failure


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRIMER_FILE_NAMES = (
    "blueprint_author.md",
    "implementation_agent.md",
    "test_agent.md",
    "coverage_review.md",
    "orchestrator_break_glass.md",
)

R_MANIFEST_NAMES = (
    "r_conda_testthat.json",
    "r_renv_testthat.json",
)

# Per-primer terminology checks (per-cycle plan, S3-181 spec).
PRIMER_TERMINOLOGY: dict[str, tuple[tuple[str, ...], ...]] = {
    "blueprint_author.md": (("package",), ("test_path",)),
    "implementation_agent.md": (("devtools",), ("test_path",)),
    "test_agent.md": (("setwd",), ("withr", "local_dir")),
    "coverage_review.md": (("covr",), ("attribution",), ("subprocess",)),
    "orchestrator_break_glass.md": (("covr",), ("attribution", "diagnose")),
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_r_primers_directory_exists():
    """scripts/primers/r/ resolves under workspace OR repo layout."""
    primers = _primers_dir()
    assert primers.is_dir(), f"primers/r/ not found: {primers}"


@pytest.mark.parametrize("filename", PRIMER_FILE_NAMES)
def test_r_primers_all_five_files_exist(filename: str):
    """Each of the 5 markdown files is present and non-empty (>200 bytes)."""
    primers = _primers_dir()
    path = primers / filename
    assert path.is_file(), f"primer not found: {path}"
    size = path.stat().st_size
    assert size > 200, (
        f"primer {filename} suspiciously small ({size} bytes; expected >200)"
    )


@pytest.mark.parametrize("filename", PRIMER_FILE_NAMES)
def test_r_primers_contain_architecture_terminology(filename: str):
    """Each primer references the rule-specific terms expected for its role.

    Per-primer assertions: each tuple in PRIMER_TERMINOLOGY is an "AND" group;
    each entry inside a tuple is an "OR" alternative within that group. A
    primer passes when every group has at least one alternative present in
    the file's text (case-insensitive substring match).
    """
    primers = _primers_dir()
    text = (primers / filename).read_text(encoding="utf-8").lower()
    for group in PRIMER_TERMINOLOGY[filename]:
        assert any(alt.lower() in text for alt in group), (
            f"{filename} missing required terminology group {group}: "
            f"none of {group} found in primer text"
        )


@pytest.mark.parametrize("manifest_name", R_MANIFEST_NAMES)
def test_r_manifests_reference_existent_primer_files(manifest_name: str):
    """Both R manifests have language_architecture_primers populated with all
    5 keys, every value is a non-null string, and every path resolves to an
    existing file under either workspace or repo layout.
    """
    manifest_path = _manifests_dir() / manifest_name
    assert manifest_path.is_file(), f"manifest not found: {manifest_path}"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    primers = manifest.get("language_architecture_primers")
    assert isinstance(primers, dict), (
        f"{manifest_name}: language_architecture_primers must be a dict; "
        f"got {type(primers).__name__}"
    )
    expected_keys = {
        "blueprint_author",
        "implementation_agent",
        "test_agent",
        "coverage_review",
        "orchestrator_break_glass",
    }
    assert set(primers.keys()) == expected_keys, (
        f"{manifest_name}: primer keys mismatch. "
        f"Expected {sorted(expected_keys)}, got {sorted(primers.keys())}"
    )
    for key, relpath in primers.items():
        assert isinstance(relpath, str), (
            f"{manifest_name}: primer {key} must be a string path; "
            f"got {type(relpath).__name__}"
        )
        resolved = _resolve_primer_path(relpath)
        assert resolved.is_file(), (
            f"{manifest_name}: primer {key} declared path {relpath!r} "
            f"does not resolve to an existing file (tried {resolved})"
        )


def test_validator_rejects_nonexistent_primer_path(tmp_path: Path):
    """Replace one primer path with a bogus path in a temp manifest copy and
    confirm the validator surfaces the missing path with a non-zero exit.

    Uses subprocess to mirror the CLI invocation path; passes the temp dir as
    --manifests-dir so the validator does not pick up the project's good
    manifests.
    """
    real_manifest = _manifests_dir() / "r_conda_testthat.json"
    manifest = json.loads(real_manifest.read_text(encoding="utf-8"))
    manifest = copy.deepcopy(manifest)
    manifest["language_architecture_primers"]["blueprint_author"] = (
        "scripts/primers/r/THIS_FILE_DOES_NOT_EXIST_XYZZY.md"
    )

    # Set up a temp manifests dir containing only the corrupted manifest.
    # Place it under a parent that contains scripts/toolchain_defaults so the
    # validator can locate the project_root relative to the manifest dir
    # (the parent's project_root won't have scripts/primers, so the bogus path
    # resolves to a non-existent file under tmp_path/scripts/primers/r/...).
    tmp_manifests = tmp_path / "scripts" / "toolchain_defaults"
    tmp_manifests.mkdir(parents=True)
    bogus_manifest = tmp_manifests / "r_conda_testthat.json"
    bogus_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    script = _validator_script()
    result = subprocess.run(
        [sys.executable, str(script), "--manifests-dir", str(tmp_manifests)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        f"validator should reject non-existent primer path; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = result.stdout + result.stderr
    assert "THIS_FILE_DOES_NOT_EXIST_XYZZY" in combined, (
        f"error output should mention the bogus path; got: {combined!r}"
    )

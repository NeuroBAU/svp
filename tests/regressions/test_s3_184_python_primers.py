"""Regression test for Bug S3-184 — author Python architectural primers.

Cycle E4 ships five archetype-conditional primer markdowns at
``scripts/primers/python/*.md`` and populates the ``language_architecture_primers``
field in the Python toolchain manifest with paths to those files.

The tests below pin three invariants:

1. The five primer files exist on disk under both workspace and repo layouts.
2. The Python manifest references primer files that resolve to existing files
   on disk.
3. The five primers carry distinctive Python architecture terminology.

The dispatch wiring (E2 ``prepare_task_prompt`` + E3 ``write_delivered_claude_md``)
is already in place from earlier cycles; E4 is content-only and rides the
existing wiring once the manifest is non-empty.

Pattern reference: P68 (Adding A Second Archetype Primer Set Is A Content-Only
Cycle Once Dispatch Is Wired). Sibling P65 (S3-181 R authoring), P66 (S3-182
prepare_task wiring), P67 (S3-183 Stage-5 wiring).
"""

from __future__ import annotations

import json
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
    """Locate scripts/primers/python/ under either workspace or repo layout."""
    root = _project_root()
    ws = root / "scripts" / "primers" / "python"
    if ws.is_dir():
        return ws
    repo = root / "svp" / "scripts" / "primers" / "python"
    if repo.is_dir():
        return repo
    raise RuntimeError(
        f"Could not locate scripts/primers/python under {root} (tried workspace + repo layouts)"
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


def _resolve_primer_path(relative: str) -> Path:
    """Resolve a primer path string from a manifest against either layout.

    Manifest paths are written workspace-relative
    (e.g. ``scripts/primers/python/blueprint_author.md``); the repo layout
    flattens that under ``svp/`` (e.g. ``svp/scripts/primers/python/blueprint_author.md``).
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

PYTHON_MANIFEST_NAME = "python_conda_pytest.json"

# Per-primer terminology checks (per-cycle plan, S3-184 spec).
# Each tuple is an "AND" group; each entry inside a tuple is an "OR" alternative
# within that group. A primer passes when every group has at least one
# alternative present in the file's text (case-insensitive substring match).
PRIMER_TERMINOLOGY: dict[str, tuple[tuple[str, ...], ...]] = {
    "blueprint_author.md": (("package",), ("pyproject", "src/")),
    "implementation_agent.md": (("pytest",), ("package", "namespace", "editable")),
    "test_agent.md": (("chdir",), ("monkeypatch", "tmp_path")),
    "coverage_review.md": (("coverage.py",), ("attribution",), ("subprocess",)),
    "orchestrator_break_glass.md": (("coverage.py",), ("attribution", "diagnose")),
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_python_primers_directory_exists():
    """scripts/primers/python/ resolves under workspace OR repo layout."""
    primers = _primers_dir()
    assert primers.is_dir(), f"primers/python/ not found: {primers}"


@pytest.mark.parametrize("filename", PRIMER_FILE_NAMES)
def test_python_primers_all_five_files_exist(filename: str):
    """Each of the 5 markdown files is present and non-empty (>200 bytes)."""
    primers = _primers_dir()
    path = primers / filename
    assert path.is_file(), f"primer not found: {path}"
    size = path.stat().st_size
    assert size > 200, (
        f"primer {filename} suspiciously small ({size} bytes; expected >200)"
    )


@pytest.mark.parametrize("filename", PRIMER_FILE_NAMES)
def test_python_primers_contain_architecture_terminology(filename: str):
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


def test_python_manifest_references_existent_primer_files():
    """The Python manifest has language_architecture_primers populated with all
    5 keys, every value is a non-null string, and every path resolves to an
    existing file under either workspace or repo layout.
    """
    manifest_path = _manifests_dir() / PYTHON_MANIFEST_NAME
    assert manifest_path.is_file(), f"manifest not found: {manifest_path}"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    primers = manifest.get("language_architecture_primers")
    assert isinstance(primers, dict), (
        f"{PYTHON_MANIFEST_NAME}: language_architecture_primers must be a dict; "
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
        f"{PYTHON_MANIFEST_NAME}: primer keys mismatch. "
        f"Expected {sorted(expected_keys)}, got {sorted(primers.keys())}"
    )
    for key, relpath in primers.items():
        assert isinstance(relpath, str), (
            f"{PYTHON_MANIFEST_NAME}: primer {key} must be a string path; "
            f"got {type(relpath).__name__}"
        )
        resolved = _resolve_primer_path(relpath)
        assert resolved.is_file(), (
            f"{PYTHON_MANIFEST_NAME}: primer {key} declared path {relpath!r} "
            f"does not resolve to an existing file (tried {resolved})"
        )

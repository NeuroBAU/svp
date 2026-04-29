"""Regression test for Bug S3-185 — F1 cap-stone synthetic Rust archetype.

Cycle F1 ships:

1. ``references/extending-languages.md`` — canonical extension-contract documentation
   for adding a new language archetype to SVP.
2. ``scripts/toolchain_defaults/rust_cargo_test.json`` — synthetic Rust manifest.
3. ``scripts/primers/rust/*.md`` — five synthetic Rust primer files.
4. This test — confirms the manifest validates clean, primers exist, and the
   dispatch boundary is preserved (rust is NOT in LANGUAGE_REGISTRY).

The synthetic archetype demonstrates the SCHEMA half of the two-contract
architecture (manifest = BEHAVIOR contract). It does NOT exercise the DISPATCH
half (registering the language in LANGUAGE_REGISTRY), because that would
require implementing a stub generator, test parser, and quality runner for
Rust — out of F1 scope.

Pattern reference: P69 (cap-stone — adding a third archetype is content-only on
the dispatch side once rounds A-E land). Sibling patterns P58 (schema-as-
extension-contract), P65/P66/P67/P68 (primer authoring + dispatch).
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
    raise RuntimeError(
        "Could not locate project root containing scripts/toolchain_defaults/"
    )


def _validator_project_root() -> Path:
    """Resolve the project root the validator should use for primer paths.

    Mirrors the CLI's auto-detection: under the workspace layout the project
    root is the directory containing ``scripts/toolchain_defaults/``; under
    the repo layout the project root is the ``svp/`` subdirectory of the repo
    (because primer paths in manifests are written workspace-relative —
    ``scripts/primers/rust/...`` — and the repo flattens that under
    ``<repo>/svp/scripts/primers/rust/...``).
    """
    root = _project_root()
    if (root / "scripts" / "toolchain_defaults").is_dir():
        return root
    if (root / "svp" / "scripts" / "toolchain_defaults").is_dir():
        return root / "svp"
    return root


def _primers_dir() -> Path:
    """Locate scripts/primers/rust/ under either workspace or repo layout."""
    root = _project_root()
    ws = root / "scripts" / "primers" / "rust"
    if ws.is_dir():
        return ws
    repo = root / "svp" / "scripts" / "primers" / "rust"
    if repo.is_dir():
        return repo
    raise RuntimeError(
        f"Could not locate scripts/primers/rust under {root} "
        f"(tried workspace + repo layouts)"
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


def _scripts_root() -> Path:
    """Locate the scripts/ directory under either workspace or repo layout.

    Used for sys.path insertion so the test can import language_registry +
    toolchain_reader directly from either layout.
    """
    root = _project_root()
    ws = root / "scripts"
    if ws.is_dir() and (ws / "language_registry.py").is_file():
        return ws
    repo = root / "svp" / "scripts"
    if repo.is_dir() and (repo / "language_registry.py").is_file():
        return repo
    raise RuntimeError("scripts/ root with language_registry.py not found")


def _resolve_primer_path(relative: str) -> Path:
    """Resolve a primer path string from a manifest against either layout."""
    root = _project_root()
    direct = root / relative
    if direct.is_file():
        return direct
    via_svp = root / "svp" / relative
    if via_svp.is_file():
        return via_svp
    return direct  # caller will surface the failure


def _extending_languages_doc() -> Path:
    """Locate references/extending-languages.md under either layout."""
    root = _project_root()
    ws = root / "references" / "extending-languages.md"
    if ws.is_file():
        return ws
    repo = root / "docs" / "references" / "extending-languages.md"
    if repo.is_file():
        return repo
    repo_alt = root / "svp" / "references" / "extending-languages.md"
    if repo_alt.is_file():
        return repo_alt
    return ws  # caller surfaces the failure


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

RUST_MANIFEST_NAME = "rust_cargo_test.json"
DISTINCTIVE_HEADER_PREFIX = "# Rust Architectural Primer"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestS3_185_SyntheticRustArchetype:
    """F1 cap-stone schema-conformance + dispatch-boundary tests."""

    def test_synthetic_rust_manifest_validates_clean(self):
        """Schema validator reports 0 errors for the synthetic Rust manifest.

        Loads the validator's library entry point with the manifest dict and
        asserts ``errors == []``. The validator is invoked with both
        ``expected_toolchain_id`` (filename-stem match) and ``project_root``
        (primer-path existence check) so all 10 checks fire.
        """
        sys.path.insert(0, str(_scripts_root()))
        try:
            from validate_toolchain_schema import validate_manifest
        finally:
            sys.path.pop(0)

        manifest_path = _manifests_dir() / RUST_MANIFEST_NAME
        assert manifest_path.is_file(), f"manifest not found: {manifest_path}"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        errors = validate_manifest(
            manifest,
            expected_toolchain_id="rust_cargo_test",
            project_root=_validator_project_root(),
        )
        assert errors == [], (
            f"synthetic Rust manifest must validate clean; got errors:\n  - "
            + "\n  - ".join(errors)
        )

    @pytest.mark.parametrize("filename", PRIMER_FILE_NAMES)
    def test_synthetic_rust_primer_files_all_exist(self, filename: str):
        """All 5 rust primer files exist and are non-empty (>200 bytes)."""
        primers = _primers_dir()
        path = primers / filename
        assert path.is_file(), f"primer not found: {path}"
        size = path.stat().st_size
        assert size > 200, (
            f"primer {filename} suspiciously small "
            f"({size} bytes; expected >200)"
        )

    @pytest.mark.parametrize("filename", PRIMER_FILE_NAMES)
    def test_synthetic_rust_primers_start_with_distinctive_header(
        self, filename: str
    ):
        """Each rust primer starts with '# Rust Architectural Primer'.

        The distinctive header lets cross-primer assertions in upstream tests
        recognize which archetype's primer was injected without parsing the
        manifest path.
        """
        primers = _primers_dir()
        text = (primers / filename).read_text(encoding="utf-8")
        first_line = text.splitlines()[0] if text else ""
        assert first_line.startswith(DISTINCTIVE_HEADER_PREFIX), (
            f"primer {filename} must start with "
            f"{DISTINCTIVE_HEADER_PREFIX!r}; got: {first_line!r}"
        )

    def test_synthetic_rust_manifest_references_existent_primer_files(self):
        """The Rust manifest's language_architecture_primers paths resolve."""
        manifest_path = _manifests_dir() / RUST_MANIFEST_NAME
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        primers = manifest.get("language_architecture_primers")
        assert isinstance(primers, dict), (
            f"{RUST_MANIFEST_NAME}: language_architecture_primers must be a dict; "
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
            f"{RUST_MANIFEST_NAME}: primer keys mismatch. "
            f"Expected {sorted(expected_keys)}, got {sorted(primers.keys())}"
        )
        for key, relpath in primers.items():
            assert isinstance(relpath, str), (
                f"{RUST_MANIFEST_NAME}: primer {key} must be a string path; "
                f"got {type(relpath).__name__}"
            )
            resolved = _resolve_primer_path(relpath)
            assert resolved.is_file(), (
                f"{RUST_MANIFEST_NAME}: primer {key} declared path {relpath!r} "
                f"does not resolve to an existing file (tried {resolved})"
            )

    def test_rust_is_not_in_language_registry(self):
        """Documents the dispatch-contract boundary: rust is not registered.

        F1 ships the synthetic archetype as a SCHEMA-half demonstration only.
        Registering rust in LANGUAGE_REGISTRY would convert the synthetic
        archetype to a real one and require implementing stub generator + test
        parser + quality runner — out of F1 scope.
        """
        sys.path.insert(0, str(_scripts_root()))
        try:
            from language_registry import LANGUAGE_REGISTRY
        finally:
            sys.path.pop(0)
        assert "rust" not in LANGUAGE_REGISTRY, (
            "rust should NOT be in LANGUAGE_REGISTRY — F1 ships only the "
            "SCHEMA half of the two-contract architecture. If you intentionally "
            "added rust as a real archetype, update this test and "
            "extending-languages.md to reflect that."
        )

    def test_load_toolchain_raises_keyerror_for_rust(self, tmp_path: Path):
        """Confirms the dispatch boundary: load_toolchain refuses rust.

        load_toolchain checks LANGUAGE_REGISTRY before attempting to read
        the manifest; since rust is intentionally not registered, the call
        raises KeyError("Unknown language: rust"). The manifest file itself
        exists on disk — this test confirms the registry-side guard fires
        before the file-system read.
        """
        sys.path.insert(0, str(_scripts_root()))
        try:
            from toolchain_reader import load_toolchain
        finally:
            sys.path.pop(0)

        with pytest.raises(KeyError) as excinfo:
            load_toolchain(_project_root(), "rust")
        assert "rust" in str(excinfo.value), (
            f"KeyError message should mention rust; got: {excinfo.value!r}"
        )

    def test_validator_rejects_synthetic_manifest_with_bogus_primer_path(
        self, tmp_path: Path
    ):
        """Regression: confirms the validator's per-key existence check still
        works for the synthetic Rust manifest.

        Mutate one primer path to a bogus value, write the corrupted manifest
        into a temp manifests directory, run the validator's CLI, and assert
        that the error output mentions the bogus path.
        """
        real_manifest = _manifests_dir() / RUST_MANIFEST_NAME
        manifest = json.loads(real_manifest.read_text(encoding="utf-8"))
        manifest = copy.deepcopy(manifest)
        manifest["language_architecture_primers"]["blueprint_author"] = (
            "scripts/primers/rust/THIS_FILE_DOES_NOT_EXIST_XYZZY.md"
        )

        tmp_manifests = tmp_path / "scripts" / "toolchain_defaults"
        tmp_manifests.mkdir(parents=True)
        bogus_manifest = tmp_manifests / RUST_MANIFEST_NAME
        bogus_manifest.write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

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

    def test_extending_languages_doc_exists_and_references_synthetic_rust(self):
        """references/extending-languages.md exists, is non-trivial, and
        references the synthetic Rust archetype.

        Asserts:
          - file exists under either workspace or repo layout;
          - file size > 5 KiB (non-trivial doc);
          - file content references the synthetic rust manifest path or the
            rust primers directory.
        """
        doc = _extending_languages_doc()
        assert doc.is_file(), (
            f"extending-languages.md not found: {doc}. "
            f"F1 must ship references/extending-languages.md."
        )
        size = doc.stat().st_size
        assert size > 5_000, (
            f"extending-languages.md suspiciously small "
            f"({size} bytes; expected >5 KiB)"
        )
        text = doc.read_text(encoding="utf-8")
        assert (
            "rust_cargo_test" in text
            or "scripts/primers/rust/" in text
        ), (
            "extending-languages.md should reference the synthetic Rust "
            "archetype (scripts/toolchain_defaults/rust_cargo_test.json or "
            "scripts/primers/rust/) as the worked example."
        )

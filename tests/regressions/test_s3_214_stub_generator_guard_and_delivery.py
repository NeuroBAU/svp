"""Regression tests for Bug S3-214 -- stub_generator guard + non-code tolerance.

  * BUG-10a -- stub_generator must NEVER overwrite an IMPLEMENTED stub (one whose
    ``__SVP_STUB__`` sentinel has been removed) with a fresh skeleton; a re-run
    is protective by default and only regenerates with ``--force``.
  * BUG-8 -- a non-code / delivery unit (Tier-2 describes artefact files and
    references spec sections with ``§``, no ``def``/``class``) must yield a
    doc-only stub rather than a hard ``SyntaxError`` exit-1. A genuine syntax
    error in a CODE unit (a ``def`` present) still fails loud.

Flat-module imports resolve via pyproject.toml pythonpath = [src, scripts].
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from stub_generator import (
    _doc_only_stub,
    _is_implemented_stub,
    _parse_tier2_or_doc_only,
    main,
)

_BLUEPRINT = textwrap.dedent(
    """\
    ## Unit 1: Foundation

    ### Tier 2 -- Signatures

    ```python
    def foundation_func(x: int) -> str:
        ...
    ```

    ### Tier 3 -- Behavioral Contracts

    No dependencies.

    ## Unit 2: Delivery Artefacts

    ### Tier 2 -- Signatures

    ```yaml
    # environment.yml (see spec §13 for the canonical env)
    name: confocal-analysis
    dependencies:
      - python=3.11
    ```

    ### Tier 3 -- Behavioral Contracts

    Produces environment.yml, pyproject.toml, README.

    ## Unit 3: Broken Code

    ### Tier 2 -- Signatures

    ```python
    def broken(x:
        ...
    ```

    ### Tier 3 -- Behavioral Contracts

    Dependencies: Unit 1.
    """
)


def _write_blueprint(tmp_path: Path) -> Path:
    bp_dir = tmp_path / "blueprint"
    bp_dir.mkdir()
    (bp_dir / "blueprint_contracts.md").write_text(_BLUEPRINT, encoding="utf-8")
    (bp_dir / "blueprint_prose.md").write_text("", encoding="utf-8")
    return bp_dir / "blueprint_contracts.md"


def _run_main(bp_file: Path, unit: int, out_dir: Path, force: bool = False):
    argv = [
        "--blueprint", str(bp_file),
        "--unit", str(unit),
        "--output-dir", str(out_dir),
    ]
    if force:
        argv.append("--force")
    try:
        main(argv)
        return 0
    except SystemExit as exc:  # main() exits 1 on failure
        return exc.code if exc.code is not None else 0


# ---------------------------------------------------------------------------
# BUG-10a -- exists-guard
# ---------------------------------------------------------------------------


def test_s3_214_implemented_stub_not_overwritten(tmp_path):
    bp = _write_blueprint(tmp_path)
    out = tmp_path / "unit_1"
    out.mkdir()
    stub = out / "stub.py"
    # An IMPLEMENTED stub: real code, no __SVP_STUB__ sentinel.
    implemented = '"""Implemented."""\n\n\ndef foundation_func(x):\n    return str(x)\n'
    stub.write_text(implemented, encoding="utf-8")

    assert _run_main(bp, 1, out) == 0
    assert stub.read_text(encoding="utf-8") == implemented  # untouched


def test_s3_214_force_regenerates_implemented_stub(tmp_path):
    bp = _write_blueprint(tmp_path)
    out = tmp_path / "unit_1"
    out.mkdir()
    stub = out / "stub.py"
    stub.write_text('"""Implemented."""\n\ndef foundation_func(x):\n    return "y"\n', encoding="utf-8")

    assert _run_main(bp, 1, out, force=True) == 0
    regenerated = stub.read_text(encoding="utf-8")
    assert "__SVP_STUB__" in regenerated  # a fresh skeleton was written
    assert "raise NotImplementedError" in regenerated


def test_s3_214_skeleton_stub_is_overwritten_without_force(tmp_path):
    bp = _write_blueprint(tmp_path)
    out = tmp_path / "unit_1"
    out.mkdir()
    stub = out / "stub.py"
    # A skeleton carries the sentinel, so it is NOT protected.
    stub.write_text("__SVP_STUB__ = True  # stale skeleton\n", encoding="utf-8")

    assert _run_main(bp, 1, out) == 0
    text = stub.read_text(encoding="utf-8")
    assert "raise NotImplementedError" in text  # regenerated from blueprint


def test_s3_214_is_implemented_stub_helper(tmp_path):
    p = tmp_path / "s.py"
    assert _is_implemented_stub(p) is False  # absent
    p.write_text("__SVP_STUB__ = True\n", encoding="utf-8")
    assert _is_implemented_stub(p) is False  # skeleton
    p.write_text("def f():\n    return 1\n", encoding="utf-8")
    assert _is_implemented_stub(p) is True  # implemented


# ---------------------------------------------------------------------------
# BUG-8 -- non-code / delivery unit tolerance
# ---------------------------------------------------------------------------


def test_s3_214_delivery_unit_yields_doc_only_stub(tmp_path):
    bp = _write_blueprint(tmp_path)
    out = tmp_path / "unit_2"
    out.mkdir()

    assert _run_main(bp, 2, out) == 0  # no hard exit-1
    stub = out / "stub.py"
    assert stub.exists()
    text = stub.read_text(encoding="utf-8")
    assert "__SVP_STUB__" in text  # doc-only stub carries the sentinel
    assert "doc-only stub" in text
    assert "raise NotImplementedError" not in text  # no code generated


def test_s3_214_broken_code_unit_still_fails_loud(tmp_path):
    bp = _write_blueprint(tmp_path)
    out = tmp_path / "unit_3"
    out.mkdir()
    # Unit 3 has a real Python syntax error AND a `def` -> must hard-fail (exit 1).
    assert _run_main(bp, 3, out) == 1
    assert not (out / "stub.py").exists()


def test_s3_214_doc_only_stub_contains_sentinel():
    cfg = {"stub_sentinel": "__SVP_STUB__ = True  # DO NOT DELIVER"}
    text = _doc_only_stub(cfg, 13)
    assert "Unit 13" in text
    assert text.rstrip().endswith("DO NOT DELIVER")


def test_s3_214_parse_helper_reraises_on_broken_code():
    # A signature is present -> a parse error is a genuine code bug, re-raised.
    cfg = {"stub_generator_key": "python", "file_extension": ".py",
           "stub_sentinel": "__SVP_STUB__ = True"}
    with pytest.raises((SyntaxError, ValueError)):
        _parse_tier2_or_doc_only("def broken(x:\n    ...", "python", cfg, "python", 3)

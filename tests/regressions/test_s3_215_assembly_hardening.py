"""Regression tests for Bug S3-215 -- Stage-5 assembly hardening (BUG-11).

  * LICENSE -- a delivered Python repo must ship a LICENSE (previously only the R
    path generated one).
  * references/ -- sync_debug_docs must ship the workspace references/ tree into
    delivered docs/references/ (previously only spec + blueprint shipped).
  * Post-assembly collect gate -- assembly must run `pytest --collect-only` and
    RAISE on a genuine collection error (non-collecting harness), while SKIPPING
    cleanly on the expected "delivered package not installed yet" state / no tests.

Flat-module imports resolve via pyproject.toml pythonpath = [src, scripts].
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generate_assembly_map import (
    _post_assembly_collect_check,
    assemble_python_project,
)
from sync_debug_docs import sync_debug_docs


def _scaffold_minimal_workspace(ws: Path) -> None:
    (ws / "scripts").mkdir(parents=True, exist_ok=True)
    (ws / "scripts" / "__init__.py").write_text("", encoding="utf-8")
    (ws / "tests").mkdir(parents=True, exist_ok=True)
    (ws / "tests" / "__init__.py").write_text("", encoding="utf-8")


def _python_profile_apache() -> dict:
    return {
        "language": {"primary": "python"},
        "archetype": "python_project",
        "delivery": {"python": {"source_layout": "conventional"}},
        "license": {"type": "Apache-2.0", "holder": "Test Author"},
    }


# ---------------------------------------------------------------------------
# LICENSE
# ---------------------------------------------------------------------------


def test_s3_215_python_assembler_ships_license(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    _scaffold_minimal_workspace(ws)

    repo_dir = assemble_python_project(ws, _python_profile_apache(), {"description": "demo"})
    license_file = repo_dir / "LICENSE"
    assert license_file.is_file(), "delivered Python repo must ship a LICENSE"
    body = license_file.read_text(encoding="utf-8")
    assert "apache.org/licenses/LICENSE-2.0" in body  # Apache-2.0 body selected


# ---------------------------------------------------------------------------
# references/
# ---------------------------------------------------------------------------


def test_s3_215_sync_debug_docs_ships_references(tmp_path):
    ws = tmp_path / "ws"
    (ws / "references").mkdir(parents=True)
    (ws / "references" / "lessons_learned.md").write_text("# lessons\n", encoding="utf-8")
    (ws / "references" / "sub").mkdir()
    (ws / "references" / "sub" / "guide.md").write_text("# guide\n", encoding="utf-8")

    repo = tmp_path / "repo"
    repo.mkdir()
    sync_debug_docs(ws, repo_dir=repo)

    assert (repo / "docs" / "references" / "lessons_learned.md").is_file()
    assert (repo / "docs" / "references" / "sub" / "guide.md").is_file()  # recursive


def test_s3_215_sync_debug_docs_silent_when_no_references(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    sync_debug_docs(ws, repo_dir=repo)  # must not raise when references/ absent
    assert not (repo / "docs" / "references").exists()


# ---------------------------------------------------------------------------
# Post-assembly collect gate
# ---------------------------------------------------------------------------


def _make_repo_with_test(tmp_path: Path, test_body: str) -> Path:
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "tests" / "test_planted.py").write_text(test_body, encoding="utf-8")
    return repo


def test_s3_215_collect_gate_raises_on_syntax_collection_error(tmp_path):
    repo = _make_repo_with_test(tmp_path, "def broken(:\n    pass\n")
    with pytest.raises(RuntimeError):
        _post_assembly_collect_check(repo, "somepkg")


def test_s3_215_collect_gate_skips_on_uninstalled_package(tmp_path):
    # A test that imports the delivered package which is not pip-installed yet.
    repo = _make_repo_with_test(tmp_path, "import mypkg\n\n\ndef test_x():\n    assert mypkg\n")
    # No exception: the "No module named 'mypkg'" state is tolerated.
    assert _post_assembly_collect_check(repo, "mypkg") is None


def test_s3_215_collect_gate_skips_when_no_tests_dir(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _post_assembly_collect_check(repo, "mypkg") is None


def test_s3_215_collect_gate_skips_when_no_test_files(tmp_path):
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "tests" / "helper.py").write_text("x = 1\n", encoding="utf-8")
    assert _post_assembly_collect_check(repo, "mypkg") is None


def test_s3_215_collect_gate_passes_on_clean_collectible_tests(tmp_path):
    repo = _make_repo_with_test(tmp_path, "def test_ok():\n    assert True\n")
    assert _post_assembly_collect_check(repo, "mypkg") is None

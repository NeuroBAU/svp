"""Tests for Bug S3-146: deterministic test delivery + import adapt.

Verifies that:
  (a) copy_workspace_tests_to_repo applies the fixed exclusion list
  (b) adapt_test_imports_in_repo is a no-op for svp_native layout
  (c) adapt_test_imports_in_repo rewrites flat imports for conventional layout
  (d) adapt is idempotent (running twice produces identical output)
  (e) only modules in the workspace allow-list are rewritten
  (f) _write_pyproject_toml for svp_native includes pythonpath = ["scripts"]
"""

import json
from pathlib import Path

from generate_assembly_map import (
    _workspace_module_names,
    _write_pyproject_toml,
    adapt_test_imports_in_repo,
    copy_workspace_tests_to_repo,
)


def _setup_workspace_with_scripts_and_tests(workspace: Path) -> None:
    """Build a minimal workspace with scripts/ and tests/ directories.

    Creates two flat modules (ledger_manager.py, routing.py) and a
    representative test that imports from them. Also drops in noise
    artifacts (__pycache__, .pyc, unit_*_stub.py) that should be excluded
    by the copy step.
    """
    scripts = workspace / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "ledger_manager.py").write_text("def append_entry(p): ...\n")
    (scripts / "routing.py").write_text("def route(p): ...\n")
    (scripts / "__init__.py").write_text("")

    tests = workspace / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("")

    # Tests/unit_7/ — flat-import test plus a cross-unit stub that should be excluded
    unit7 = tests / "unit_7"
    unit7.mkdir()
    (unit7 / "__init__.py").write_text("")
    (unit7 / "test_unit_7.py").write_text(
        "import json\n"
        "import os\n"
        "from ledger_manager import append_entry\n"
        "from routing import route\n"
        "import routing\n"
        "import routing as r_alias\n"
        "\n"
        "def test_smoke():\n"
        "    pass\n"
    )
    (unit7 / "unit_1_stub.py").write_text("# excluded — cross-unit stub helper\n")

    # Noise that must be excluded
    (unit7 / "__pycache__").mkdir()
    (unit7 / "__pycache__" / "test_unit_7.cpython-311.pyc").write_text("noise")
    (tests / ".pytest_cache").mkdir()
    (tests / ".pytest_cache" / "v").mkdir()
    (tests / "test_top_level.py.bak.20260423-120000").write_text("backup noise")


def _python_profile(layout: str, package_name: str = "demo_pkg") -> dict:
    return {
        "language": {"primary": "python"},
        "archetype": "python_project",
        "delivery": {
            "python": {
                "source_layout": layout,
                "package_name": package_name,
            }
        },
    }


# ---------------------------------------------------------------------------
# (a) copy excludes the fixed list
# ---------------------------------------------------------------------------


def test_copy_excludes_caches_pyc_backups_and_unit_stubs(tmp_path):
    workspace = tmp_path / "ws"
    _setup_workspace_with_scripts_and_tests(workspace)
    repo = tmp_path / "repo"
    repo.mkdir()

    n = copy_workspace_tests_to_repo(workspace, repo, _python_profile("svp_native"))
    assert n > 0, "Copy must report a non-zero file count"

    tests = repo / "tests"
    assert (tests / "unit_7" / "test_unit_7.py").is_file()
    assert (tests / "unit_7" / "__init__.py").is_file()

    # Excluded artifacts must NOT appear
    assert not (tests / "unit_7" / "unit_1_stub.py").exists(), (
        "unit_*_stub.py must be excluded"
    )
    assert not (tests / "unit_7" / "__pycache__").exists()
    assert not (tests / ".pytest_cache").exists()
    assert not list(tests.rglob("*.bak.*"))
    assert not list(tests.rglob("*.pyc"))


# ---------------------------------------------------------------------------
# (b) svp_native → adapt is no-op
# ---------------------------------------------------------------------------


def test_adapt_svp_native_is_noop(tmp_path):
    workspace = tmp_path / "ws"
    _setup_workspace_with_scripts_and_tests(workspace)
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = _python_profile("svp_native")
    copy_workspace_tests_to_repo(workspace, repo, profile)

    before = (repo / "tests" / "unit_7" / "test_unit_7.py").read_text()
    n = adapt_test_imports_in_repo(
        repo, profile, _workspace_module_names(workspace)
    )
    after = (repo / "tests" / "unit_7" / "test_unit_7.py").read_text()

    assert n == 0, "svp_native must rewrite zero files"
    assert before == after, "svp_native must leave test source unchanged"
    assert "from ledger_manager import" in after


# ---------------------------------------------------------------------------
# (c) conventional → imports rewritten with package prefix
# ---------------------------------------------------------------------------


def test_adapt_conventional_rewrites_flat_imports(tmp_path):
    workspace = tmp_path / "ws"
    _setup_workspace_with_scripts_and_tests(workspace)
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = _python_profile("conventional", package_name="demo_pkg")
    copy_workspace_tests_to_repo(workspace, repo, profile)

    n = adapt_test_imports_in_repo(
        repo, profile, _workspace_module_names(workspace)
    )

    after = (repo / "tests" / "unit_7" / "test_unit_7.py").read_text()
    assert n >= 1, f"Expected at least one file modified, got {n}"
    assert "from demo_pkg.ledger_manager import" in after
    assert "from demo_pkg.routing import" in after
    assert "import demo_pkg.routing" in after
    # Stdlib imports must NOT be prefixed
    assert "import json" in after
    assert "demo_pkg.json" not in after
    assert "demo_pkg.os" not in after


# ---------------------------------------------------------------------------
# (d) adapt is idempotent
# ---------------------------------------------------------------------------


def test_adapt_idempotent(tmp_path):
    workspace = tmp_path / "ws"
    _setup_workspace_with_scripts_and_tests(workspace)
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = _python_profile("conventional", package_name="demo_pkg")
    copy_workspace_tests_to_repo(workspace, repo, profile)
    modules = _workspace_module_names(workspace)

    adapt_test_imports_in_repo(repo, profile, modules)
    after_first = (repo / "tests" / "unit_7" / "test_unit_7.py").read_text()

    n_second = adapt_test_imports_in_repo(repo, profile, modules)
    after_second = (repo / "tests" / "unit_7" / "test_unit_7.py").read_text()

    assert n_second == 0, "Second adapt run must rewrite zero files"
    assert after_first == after_second, (
        "File content after second adapt must equal content after first"
    )


# ---------------------------------------------------------------------------
# (e) only allow-list modules are rewritten
# ---------------------------------------------------------------------------


def test_adapt_only_rewrites_workspace_allowlist_modules(tmp_path):
    workspace = tmp_path / "ws"
    _setup_workspace_with_scripts_and_tests(workspace)
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = _python_profile("conventional", package_name="demo_pkg")
    copy_workspace_tests_to_repo(workspace, repo, profile)

    # Drop in a third-party-style import in the test
    test_file = repo / "tests" / "unit_7" / "test_unit_7.py"
    test_file.write_text(
        "from ledger_manager import append_entry\n"
        "from third_party_lib import something\n"
        "import requests\n"
    )

    adapt_test_imports_in_repo(
        repo, profile, _workspace_module_names(workspace)
    )

    after = test_file.read_text()
    assert "from demo_pkg.ledger_manager import" in after
    assert "from third_party_lib import" in after, (
        "Non-workspace modules must not be prefixed"
    )
    assert "import requests" in after
    assert "demo_pkg.third_party_lib" not in after
    assert "demo_pkg.requests" not in after


# ---------------------------------------------------------------------------
# (f) pyproject.toml carries pythonpath for svp_native
# ---------------------------------------------------------------------------


def test_pyproject_toml_pythonpath_for_svp_native(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = _python_profile("svp_native", package_name="demo_pkg")

    _write_pyproject_toml(repo, profile, {"description": "demo"}, "demo_pkg")
    content = (repo / "pyproject.toml").read_text()

    assert "[tool.pytest.ini_options]" in content
    assert 'pythonpath = ["scripts"]' in content


def test_pyproject_toml_no_pythonpath_for_conventional(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = _python_profile("conventional", package_name="demo_pkg")

    _write_pyproject_toml(repo, profile, {"description": "demo"}, "demo_pkg")
    content = (repo / "pyproject.toml").read_text()

    # conventional layout uses adapt; pythonpath is not needed and not emitted
    assert "[tool.pytest.ini_options]" not in content

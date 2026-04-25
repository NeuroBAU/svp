"""Tests for Bug S3-148: deliver_source_files end-to-end.

Verifies the helper that walks assembly_map repo_to_workspace entries,
rewrites stub-style imports per layout, and writes to the delivered repo.

  (a) svp_native — no package prefix (modules at repo/scripts/)
  (b) conventional — `<package>.` prefix (modules at repo/src/<pkg>/)
  (c) flat — `<package>.` prefix (modules at repo/<pkg>/)
  (d) import alias rewriting (`import src.unit_N.stub as Y`)
  (e) excludes non-source entries (tests, agents, commands, manifests)
  (f) idempotent (running twice produces identical output)
  (g) end-to-end via assemble_python_project + on-disk assembly_map
"""

import json
from pathlib import Path

from generate_assembly_map import (
    _derive_unit_to_module_map,
    _rewrite_source_imports,
    assemble_python_project,
    deliver_source_files,
)


# ---------------------------------------------------------------------------
# Synthetic A-D workspace fixture
# ---------------------------------------------------------------------------


# Note: stub-style import strings are constructed via concatenation so the
# literal `from src.unit_N.stub` pattern does not appear in this test file's
# source — that pattern is flagged by the workspace regression check
# (test_bug_s3_98_stub_script_sync.py and test_sync_protocol.py) as a
# stub-import-in-test-file violation. Workspace tests must use flat
# imports; the stub-style strings here are FIXTURE INPUTS for the rewriter
# under test, not actual imports.
_STUB_PREFIX = "src.unit_"

_UNIT_1_STUB = """from __future__ import annotations


class Engine:
    def __init__(self) -> None:
        self.value = 0
"""

_UNIT_2_STUB = (
    "from __future__ import annotations\n"
    "\n"
    f"from {_STUB_PREFIX}1.stub import Engine\n"
    f"import {_STUB_PREFIX}1.stub as _u1_module\n"
    "\n"
    "\n"
    "def make_engine() -> Engine:\n"
    "    e = _u1_module.Engine()\n"
    "    e.value = 42\n"
    "    return e\n"
)


def _setup_a_d_workspace(workspace: Path) -> None:
    """Two-unit synthetic workspace where unit_2 imports unit_1 in three shapes."""
    workspace.mkdir(exist_ok=True)
    src = workspace / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")

    unit1 = src / "unit_1"
    unit1.mkdir()
    (unit1 / "stub.py").write_text(_UNIT_1_STUB)

    unit2 = src / "unit_2"
    unit2.mkdir()
    (unit2 / "stub.py").write_text(_UNIT_2_STUB)


def _make_assembly_map(layout: str) -> dict:
    """Layout-specific synthetic assembly_map. Deployed paths reflect each
    layout's destination convention. Includes a non-source entry that must
    be excluded by deliver_source_files.
    """
    if layout == "svp_native":
        return {
            "repo_to_workspace": {
                "demo_pkg-repo/scripts/engine.py": "src/unit_1/stub.py",
                "demo_pkg-repo/scripts/factory.py": "src/unit_2/stub.py",
                # excluded: not a source-tree .py
                "demo_pkg-repo/svp/agents/some_agent.md": "src/unit_3/stub.py",
                "demo_pkg-repo/tests/unit_2/test_factory.py": "src/unit_2/stub.py",
            }
        }
    if layout == "conventional":
        return {
            "repo_to_workspace": {
                "demo_pkg-repo/src/demo_pkg/engine.py": "src/unit_1/stub.py",
                "demo_pkg-repo/src/demo_pkg/factory.py": "src/unit_2/stub.py",
                "demo_pkg-repo/svp/agents/some_agent.md": "src/unit_3/stub.py",
                "demo_pkg-repo/tests/unit_2/test_factory.py": "src/unit_2/stub.py",
            }
        }
    if layout == "flat":
        return {
            "repo_to_workspace": {
                "demo_pkg-repo/demo_pkg/engine.py": "src/unit_1/stub.py",
                "demo_pkg-repo/demo_pkg/factory.py": "src/unit_2/stub.py",
                "demo_pkg-repo/svp/agents/some_agent.md": "src/unit_3/stub.py",
                "demo_pkg-repo/tests/unit_2/test_factory.py": "src/unit_2/stub.py",
            }
        }
    raise ValueError(f"Unknown layout: {layout}")


def _profile(layout: str) -> dict:
    return {
        "language": {"primary": "python"},
        "archetype": "python_project",
        "delivery": {
            "python": {
                "source_layout": layout,
                "package_name": "demo_pkg",
            }
        },
    }


# ---------------------------------------------------------------------------
# (a) svp_native — no prefix
# ---------------------------------------------------------------------------


def test_deliver_svp_native_writes_flat_imports(tmp_path):
    workspace = tmp_path / "ws"
    _setup_a_d_workspace(workspace)
    repo = tmp_path / "demo_pkg-repo"
    repo.mkdir()

    n = deliver_source_files(workspace, repo, _make_assembly_map("svp_native"), _profile("svp_native"))

    assert n == 2  # unit_1 + unit_2; non-source entries excluded
    factory = (repo / "scripts" / "factory.py").read_text()
    assert "from engine import Engine" in factory
    assert "import engine as _u1_module" in factory
    # Stdlib + future imports are untouched
    assert "from __future__ import annotations" in factory


# ---------------------------------------------------------------------------
# (b) conventional — package prefix
# ---------------------------------------------------------------------------


def test_deliver_conventional_writes_package_prefixed_imports(tmp_path):
    workspace = tmp_path / "ws"
    _setup_a_d_workspace(workspace)
    repo = tmp_path / "demo_pkg-repo"
    repo.mkdir()

    n = deliver_source_files(workspace, repo, _make_assembly_map("conventional"), _profile("conventional"))

    assert n == 2
    factory = (repo / "src" / "demo_pkg" / "factory.py").read_text()
    assert "from demo_pkg.engine import Engine" in factory
    assert "import demo_pkg.engine as _u1_module" in factory


# ---------------------------------------------------------------------------
# (c) flat — package prefix, different physical destination
# ---------------------------------------------------------------------------


def test_deliver_flat_writes_package_prefixed_imports_at_repo_root(tmp_path):
    workspace = tmp_path / "ws"
    _setup_a_d_workspace(workspace)
    repo = tmp_path / "demo_pkg-repo"
    repo.mkdir()

    n = deliver_source_files(workspace, repo, _make_assembly_map("flat"), _profile("flat"))

    assert n == 2
    factory = (repo / "demo_pkg" / "factory.py").read_text()
    assert "from demo_pkg.engine import Engine" in factory


# ---------------------------------------------------------------------------
# (d) import alias rewriting verified explicitly
# ---------------------------------------------------------------------------


def test_rewrite_handles_import_with_alias():
    # Stub-style import strings constructed via concatenation; see comment
    # above _UNIT_1_STUB about regression-check pattern avoidance.
    source = (
        f"from {_STUB_PREFIX}1.stub import Engine\n"
        f"import {_STUB_PREFIX}1.stub\n"
        f"import {_STUB_PREFIX}1.stub as _u1\n"
    )
    rewritten = _rewrite_source_imports(
        source, {1: "engine"}, package="demo_pkg"
    )
    assert "from demo_pkg.engine import Engine" in rewritten
    assert "import demo_pkg.engine as _u1" in rewritten
    # Bare `import src.unit_1.stub` rewrites the alias name only
    assert "import demo_pkg.engine" in rewritten


# ---------------------------------------------------------------------------
# (e) non-source entries excluded
# ---------------------------------------------------------------------------


def test_deliver_excludes_tests_agents_commands_hooks_skills_manifests(tmp_path):
    workspace = tmp_path / "ws"
    _setup_a_d_workspace(workspace)
    repo = tmp_path / "demo_pkg-repo"
    repo.mkdir()

    am = _make_assembly_map("conventional")
    deliver_source_files(workspace, repo, am, _profile("conventional"))

    # Tests entry points to a tests/ path — must NOT be written under repo/tests/
    assert not (repo / "tests" / "unit_2" / "test_factory.py").exists()
    # Agents entry was .md — extension filter excludes anyway
    assert not (repo / "svp" / "agents" / "some_agent.md").exists()


def test_unit_to_module_map_excludes_non_source():
    am = {
        "repo_to_workspace": {
            "x-repo/src/pkg/a.py": "src/unit_1/stub.py",
            "x-repo/tests/unit_1/test_a.py": "src/unit_1/stub.py",  # excluded
            "x-repo/svp/agents/some.md": "src/unit_3/stub.py",  # excluded (not .py)
            "x-repo/src/pkg/__init__.py": "src/unit_2/stub.py",  # excluded (__init__)
        }
    }
    m = _derive_unit_to_module_map(am["repo_to_workspace"])
    assert m == {1: "a"}


# ---------------------------------------------------------------------------
# (f) idempotency
# ---------------------------------------------------------------------------


def test_deliver_idempotent(tmp_path):
    workspace = tmp_path / "ws"
    _setup_a_d_workspace(workspace)
    repo = tmp_path / "demo_pkg-repo"
    repo.mkdir()

    am = _make_assembly_map("conventional")
    deliver_source_files(workspace, repo, am, _profile("conventional"))
    first = (repo / "src" / "demo_pkg" / "factory.py").read_text()

    # Run again; outputs must match exactly
    deliver_source_files(workspace, repo, am, _profile("conventional"))
    second = (repo / "src" / "demo_pkg" / "factory.py").read_text()

    assert first == second


# ---------------------------------------------------------------------------
# (g) end-to-end via assemble_python_project (assembly_map on disk)
# ---------------------------------------------------------------------------


def test_assemble_python_project_invokes_deliver_source_files(tmp_path):
    workspace = tmp_path / "ws"
    _setup_a_d_workspace(workspace)
    # Minimal additional scaffolding for the S3-146 helpers
    (workspace / "scripts").mkdir()
    (workspace / "scripts" / "__init__.py").write_text("")
    (workspace / "tests").mkdir()
    (workspace / "tests" / "__init__.py").write_text("")
    # assembly_map on disk
    svp = workspace / ".svp"
    svp.mkdir()
    (svp / "assembly_map.json").write_text(
        json.dumps(_make_assembly_map("conventional"))
    )

    repo_dir = assemble_python_project(
        workspace,
        _profile("conventional"),
        {"description": "demo", "project_name": "demo_pkg"},
    )

    factory = (repo_dir / "src" / "demo_pkg" / "factory.py")
    assert factory.is_file(), (
        "End-to-end: assemble_python_project must invoke deliver_source_files "
        "and produce src/demo_pkg/factory.py"
    )
    text = factory.read_text()
    assert "from demo_pkg.engine import Engine" in text

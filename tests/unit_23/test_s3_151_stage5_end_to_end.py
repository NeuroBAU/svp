"""Tests for Bug S3-151: Stage 5 end-to-end validation on a synthetic A-D workspace.

This is a confirmation test for the Stage 5 batch (S3-146 + S3-147 + S3-148 +
S3-150). It builds a minimal A-D workspace from scratch and runs the full
delivery chain:

    blueprint_prose.md (with Preamble file-tree + `<- Unit N` annotations)
        |
        v
    generate_assembly_map  ->  .svp/assembly_map.json (populated)
        |
        v
    assemble_python_project
        |  -> repo/<layout>/                    (source layout dir)
        |  -> repo/pyproject.toml               (project metadata)
        |  -> repo/tests/                       (S3-146 test delivery)
        |  -> repo/CLAUDE.md                    (S3-147 break-glass)
        |  -> repo/<layout>/<module>.py         (S3-148 source delivery,
        |                                        rewritten imports)
        v
    pytest <repo>                               (final empirical proof)

The test asserts each artifact is present, well-formed, and that the
delivered repo's tests actually pass when invoked via subprocess.

Validation outcomes are documented in spec section 24.165. A real-world
A-D workspace (`gol-python`) was inspected during the S3-150 cycle and
confirmed to lack Preamble annotations — its blueprint pre-dates the
S3-150 agent-prompt fix and therefore must be regenerated through the
blueprint_author agent before it can participate in this end-to-end
chain. The synthetic fixture in this test simulates the post-S3-150
agent output.
"""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from generate_assembly_map import (
    assemble_python_project,
    generate_assembly_map,
)


# ---------------------------------------------------------------------------
# Stub-style import strings constructed via concatenation. The literal
# `from src.unit_N.stub` pattern is flagged by the workspace's stub-imports
# regression check (test_bug_s3_98_stub_script_sync.py and
# test_sync_protocol.py); these strings are FIXTURE INPUTS for the rewriter,
# not actual imports.
# ---------------------------------------------------------------------------

_STUB_PREFIX = "src.unit_"

_UNIT_1_STUB = """\"\"\"Unit 1: trivial Engine class.\"\"\"


class Engine:
    \"\"\"Returns a fixed greeting.\"\"\"

    def greet(self) -> str:
        return "hello"
"""

_UNIT_2_STUB = (
    '"""Unit 2: factory that depends on Unit 1."""\n'
    "\n"
    f"from {_STUB_PREFIX}1.stub import Engine\n"
    "\n"
    "\n"
    "def make_engine() -> Engine:\n"
    "    return Engine()\n"
)

_UNIT_1_TEST = """from demo_pkg.engine import Engine


def test_engine_greets():
    assert Engine().greet() == "hello"
"""

_UNIT_2_TEST = """from demo_pkg.factory import make_engine


def test_factory_returns_greeter():
    e = make_engine()
    assert e.greet() == "hello"
"""


_BLUEPRINT_PROSE = textwrap.dedent("""\
    # Blueprint

    ## Preamble: Delivered File Tree

    ```
    demo_pkg-repo/
    |-- pyproject.toml
    |-- src/
    |   +-- demo_pkg/
    |       |-- __init__.py
    |       |-- engine.py                    <- Unit 1
    |       +-- factory.py                   <- Unit 2
    +-- tests/
        |-- unit_1/
        |   +-- test_engine.py               <- Unit 1
        +-- unit_2/
            +-- test_factory.py              <- Unit 2
    ```

    ## Unit 1: Engine

    Trivial greeter.

    ## Unit 2: Factory

    Constructs an Engine.
""")


def _build_workspace(workspace: Path) -> None:
    """Materialize a minimal A-D Python workspace inside `workspace`."""
    workspace.mkdir(parents=True, exist_ok=True)

    # Source units
    src = workspace / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")

    u1 = src / "unit_1"
    u1.mkdir()
    (u1 / "__init__.py").write_text("")
    (u1 / "stub.py").write_text(_UNIT_1_STUB)

    u2 = src / "unit_2"
    u2.mkdir()
    (u2 / "__init__.py").write_text("")
    (u2 / "stub.py").write_text(_UNIT_2_STUB)

    # Tests with delivered-layout (`from demo_pkg.X`) imports — adapt step
    # is a no-op for already-correct imports; this also covers the case
    # where the blueprint-author/test-author wrote conventional imports.
    tests = workspace / "tests"
    tests.mkdir()
    (tests / "__init__.py").write_text("")

    t1 = tests / "unit_1"
    t1.mkdir()
    (t1 / "__init__.py").write_text("")
    (t1 / "test_engine.py").write_text(_UNIT_1_TEST)

    t2 = tests / "unit_2"
    t2.mkdir()
    (t2 / "__init__.py").write_text("")
    (t2 / "test_factory.py").write_text(_UNIT_2_TEST)

    # Blueprint with Preamble file-tree
    bp = workspace / "blueprint"
    bp.mkdir()
    (bp / "blueprint_prose.md").write_text(_BLUEPRINT_PROSE)

    # .svp dir
    (workspace / ".svp").mkdir()


def _profile_conventional() -> dict:
    return {
        "language": {"primary": "python"},
        "archetype": "python_project",
        "delivery": {
            "python": {
                "source_layout": "conventional",
                "package_name": "demo_pkg",
            }
        },
    }


# ---------------------------------------------------------------------------
# Main end-to-end test
# ---------------------------------------------------------------------------


def test_stage_5_end_to_end_synthetic_a_d_workspace(tmp_path):
    """Full chain: blueprint -> assembly_map -> assembled repo with tests
    that pass under pytest."""
    workspace = tmp_path / "demo_pkg"
    _build_workspace(workspace)

    # ---- Step 1: generate_assembly_map ---------------------------------
    bp_dir = workspace / "blueprint"
    mapping = generate_assembly_map(bp_dir, workspace)

    assert "repo_to_workspace" in mapping
    rw = mapping["repo_to_workspace"]
    assert len(rw) >= 4, (
        f"Expected >=4 entries (2 src + 2 tests); got {len(rw)}: {list(rw)}"
    )
    # Spot-check that engine.py and factory.py both got mapped
    engine_keys = [k for k in rw if k.endswith("engine.py")]
    factory_keys = [k for k in rw if k.endswith("factory.py")]
    assert engine_keys, f"engine.py missing from map: {list(rw)}"
    assert factory_keys, f"factory.py missing from map: {list(rw)}"

    # And that the side-effect file landed
    map_path = workspace / ".svp" / "assembly_map.json"
    assert map_path.is_file()
    on_disk = json.loads(map_path.read_text())
    assert on_disk == mapping

    # ---- Step 2: assemble_python_project -------------------------------
    repo_dir = assemble_python_project(
        workspace,
        _profile_conventional(),
        {"description": "demo", "project_name": "demo_pkg"},
    )

    assert repo_dir.is_dir()
    assert repo_dir.name == "demo_pkg-repo"
    assert repo_dir.parent == workspace.parent

    # pyproject.toml present
    pyproject = repo_dir / "pyproject.toml"
    assert pyproject.is_file()

    # CLAUDE.md present (S3-147)
    claude_md = repo_dir / "CLAUDE.md"
    assert claude_md.is_file()
    assert "Manual Bug-Fixing Protocol" in claude_md.read_text()

    # Tests delivered (S3-146)
    assert (repo_dir / "tests" / "unit_1" / "test_engine.py").is_file()
    assert (repo_dir / "tests" / "unit_2" / "test_factory.py").is_file()

    # Source files delivered with rewritten imports (S3-148)
    src_pkg = repo_dir / "src" / "demo_pkg"
    assert src_pkg.is_dir()
    engine = src_pkg / "engine.py"
    factory = src_pkg / "factory.py"
    assert engine.is_file(), f"engine.py missing in {sorted(src_pkg.iterdir())}"
    assert factory.is_file(), f"factory.py missing in {sorted(src_pkg.iterdir())}"

    # The factory should import from `demo_pkg.engine` after rewrite
    factory_text = factory.read_text()
    assert "from demo_pkg.engine import Engine" in factory_text, (
        f"Imports were not rewritten in factory.py:\n{factory_text}"
    )
    # And must NOT contain the original stub-style import
    assert "src.unit_1" not in factory_text

    # Engine itself has no inter-unit imports — should be unchanged content
    engine_text = engine.read_text()
    assert "class Engine" in engine_text
    assert "src.unit_" not in engine_text

    # ---- Step 3: pytest the delivered repo (the real proof) -----------
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header"],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"Delivered repo's pytest failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "2 passed" in result.stdout, (
        f"Expected 2 passing tests; got:\n{result.stdout}"
    )


# ---------------------------------------------------------------------------
# Layout sweep — confirm the chain works for all three Python source layouts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("layout", ["conventional", "flat", "svp_native"])
def test_stage_5_chain_succeeds_for_each_python_layout(tmp_path, layout):
    """For each of the three Python source layouts, the full chain must
    deliver source files at the layout-appropriate destination with
    correctly rewritten imports."""
    workspace = tmp_path / f"demo_{layout}"
    _build_workspace(workspace)

    # Layout-specific blueprint Preamble — repo-relative paths must match
    # the layout's destination convention so generate_assembly_map produces
    # entries whose deployed paths match what the assembler creates.
    if layout == "conventional":
        prose = _BLUEPRINT_PROSE  # already conventional
    elif layout == "flat":
        prose = _BLUEPRINT_PROSE.replace(
            "|-- src/\n    |   +-- demo_pkg/\n    |       |-- __init__.py\n",
            "+-- demo_pkg/\n    |   |-- __init__.py\n",
        )
        # Rewrite indentation so engine.py/factory.py sit under demo_pkg/
        prose = textwrap.dedent("""\
            # Blueprint

            ## Preamble: Delivered File Tree

            ```
            demo_pkg-repo/
            |-- pyproject.toml
            |-- demo_pkg/
            |   |-- __init__.py
            |   |-- engine.py                    <- Unit 1
            |   +-- factory.py                   <- Unit 2
            +-- tests/
                |-- unit_1/
                |   +-- test_engine.py           <- Unit 1
                +-- unit_2/
                    +-- test_factory.py          <- Unit 2
            ```
        """)
    elif layout == "svp_native":
        prose = textwrap.dedent("""\
            # Blueprint

            ## Preamble: Delivered File Tree

            ```
            demo_pkg-repo/
            |-- pyproject.toml
            |-- scripts/
            |   |-- engine.py                    <- Unit 1
            |   +-- factory.py                   <- Unit 2
            +-- tests/
                |-- unit_1/
                |   +-- test_engine.py           <- Unit 1
                +-- unit_2/
                    +-- test_factory.py          <- Unit 2
            ```
        """)
    (workspace / "blueprint" / "blueprint_prose.md").write_text(prose)

    # For svp_native, tests must use flat imports (no package prefix);
    # rewrite the test files now.
    if layout == "svp_native":
        (workspace / "tests" / "unit_1" / "test_engine.py").write_text(
            "from engine import Engine\n\n"
            "def test_engine_greets():\n"
            "    assert Engine().greet() == \"hello\"\n"
        )
        (workspace / "tests" / "unit_2" / "test_factory.py").write_text(
            "from factory import make_engine\n\n"
            "def test_factory_returns_greeter():\n"
            "    e = make_engine()\n"
            "    assert e.greet() == \"hello\"\n"
        )

    profile = {
        "language": {"primary": "python"},
        "archetype": "python_project",
        "delivery": {
            "python": {"source_layout": layout, "package_name": "demo_pkg"}
        },
    }

    generate_assembly_map(workspace / "blueprint", workspace)
    repo_dir = assemble_python_project(
        workspace, profile, {"description": "demo", "project_name": "demo_pkg"}
    )

    if layout == "conventional":
        src_dest = repo_dir / "src" / "demo_pkg"
        expected_factory_import = "from demo_pkg.engine import Engine"
    elif layout == "flat":
        src_dest = repo_dir / "demo_pkg"
        expected_factory_import = "from demo_pkg.engine import Engine"
    else:  # svp_native
        src_dest = repo_dir / "scripts"
        expected_factory_import = "from engine import Engine"

    assert (src_dest / "engine.py").is_file(), (
        f"[{layout}] engine.py missing at {src_dest}; "
        f"contents: {sorted(p.name for p in src_dest.iterdir())}"
    )
    assert (src_dest / "factory.py").is_file(), (
        f"[{layout}] factory.py missing at {src_dest}"
    )
    factory_text = (src_dest / "factory.py").read_text()
    assert expected_factory_import in factory_text, (
        f"[{layout}] expected {expected_factory_import!r} in factory.py; "
        f"got:\n{factory_text}"
    )
    assert "src.unit_" not in factory_text, (
        f"[{layout}] stub-style import leaked into delivered factory.py"
    )

"""Anchor test for Bug S3-148: A-D source-file delivery — INVERTED 2026-04-25.

Originally pinned the deferred state (no source files delivered). When
`deliver_source_files` landed, this test was inverted to assert the
populated state. Spec §24.161 (deferral) has been superseded by §24.163
(resolution).

The test now confirms the path that previously was empty (`src/<pkg>/`)
contains the derived modules from a synthetic assembly_map. End-to-end
coverage lives in `test_s3_148_source_delivery.py`; this file remains as
a thin smoke check that the wiring in `assemble_python_project`
populates the package directory when an assembly_map is on disk.
"""

import json
from pathlib import Path

from generate_assembly_map import assemble_python_project


def _python_profile(layout: str = "conventional", package_name: str = "demo_pkg") -> dict:
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


def _scaffold_workspace_with_one_unit(workspace: Path) -> None:
    """Workspace with one source unit + minimal tests/ so S3-146 helpers don't error."""
    (workspace / "scripts").mkdir(parents=True, exist_ok=True)
    (workspace / "scripts" / "__init__.py").write_text("")
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "tests" / "__init__.py").write_text("")
    src = workspace / "src" / "unit_1"
    src.mkdir(parents=True, exist_ok=True)
    (src / "stub.py").write_text("def hello() -> str:\n    return 'demo'\n")
    # assembly_map drives delivery
    svp = workspace / ".svp"
    svp.mkdir(parents=True, exist_ok=True)
    (svp / "assembly_map.json").write_text(
        json.dumps(
            {
                "repo_to_workspace": {
                    "demo_pkg-repo/src/demo_pkg/__init__.py": "src/unit_1/stub.py",
                    "demo_pkg-repo/src/demo_pkg/core.py": "src/unit_1/stub.py",
                }
            }
        )
    )


def test_assemble_python_project_conventional_populates_src_pkg_modules(
    tmp_path,
):
    """S3-148 RESOLVED: conventional layout populates src/<pkg>/<module>.py
    via the deliver_source_files helper.
    """
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _scaffold_workspace_with_one_unit(workspace)

    profile = _python_profile(layout="conventional", package_name="demo_pkg")
    repo_dir = assemble_python_project(
        workspace, profile, {"description": "demo", "project_name": "demo_pkg"}
    )

    src_pkg = repo_dir / "src" / "demo_pkg"
    assert src_pkg.is_dir(), "Conventional layout must create src/<pkg>/"

    # core.py was specified in assembly_map.repo_to_workspace; deliver_source_files
    # should have produced it from the unit_1 stub.
    py_files = sorted(p.name for p in src_pkg.glob("*.py"))
    assert "core.py" in py_files, (
        f"S3-148: expected core.py to be delivered from unit_1 stub via "
        f"deliver_source_files; got {py_files}. See spec §24.163."
    )
    assert "__init__.py" in py_files

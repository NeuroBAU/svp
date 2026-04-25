"""Anchor test for Bug S3-148: A-D source-file delivery deferred.

Per spec §24.161, `assemble_python_project` does NOT populate
`repo/src/<package>/*.py` for A-D archetypes — production source files
are not delivered to the repo by current code. The fix is deferred until
a representative A-D project fixture is available to validate against.

This test pins the current behavior: after `assemble_python_project`,
the `repo/src/<package>/` directory contains only `__init__.py` (empty).
The future cycle that lands `deliver_source_files` will produce additional
.py files there and will deliberately break this anchor — that cycle's
author should update the assertion to expect the populated set.
"""

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


def _scaffold_minimal_workspace(workspace: Path) -> None:
    """Minimal scaffolding so the S3-146 helpers (called by the assembler)
    don't error. Their behavior is independent of this anchor."""
    (workspace / "scripts").mkdir(parents=True, exist_ok=True)
    (workspace / "scripts" / "__init__.py").write_text("")
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "tests" / "__init__.py").write_text("")


def test_assemble_python_project_conventional_does_not_populate_src_pkg_modules(
    tmp_path,
):
    """Anchor (S3-148): conventional layout's src/<pkg>/ has only __init__.py.

    When the future cycle lands `deliver_source_files`, this assertion will
    fail because src/<pkg>/ will contain derived modules (e.g., core.py,
    api.py per the assembly map). Update this test to expect the populated
    set and remove the deferral note in spec §24.161 at that time.
    """
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _scaffold_minimal_workspace(workspace)

    profile = _python_profile(layout="conventional", package_name="demo_pkg")
    # assemble_python_project derives the on-disk package directory from
    # _get_project_name (assembly_config["project_name"] takes precedence).
    repo_dir = assemble_python_project(
        workspace, profile, {"description": "demo", "project_name": "demo_pkg"}
    )

    src_pkg = repo_dir / "src" / "demo_pkg"
    assert src_pkg.is_dir(), "Conventional layout must create src/<pkg>/"

    py_files = sorted(p.name for p in src_pkg.glob("*.py"))
    assert py_files == ["__init__.py"], (
        "Anchor (S3-148): assemble_python_project for the conventional layout "
        "currently produces ONLY src/<pkg>/__init__.py — no production source "
        "files. When the deferred deliver_source_files helper lands, this "
        "assertion must be updated to reflect the populated set. See "
        f"spec §24.161. Got: {py_files}"
    )

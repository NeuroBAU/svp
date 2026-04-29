"""Tests for Bug S3-147: deterministic delivered-repo CLAUDE.md.

Verifies that `write_delivered_claude_md` (and the assembler entry points
that call it) produce a CLAUDE.md in the delivered repo for A-D archetypes,
skips for E/F self-builds, and that the generated content is scoped to
"working in this repo" without SVP-internal references.
"""

import json
from pathlib import Path

from generate_assembly_map import (
    assemble_plugin_project,
    assemble_python_project,
    assemble_r_project,
    write_delivered_claude_md,
)


# ---------------------------------------------------------------------------
# Profile factories
# ---------------------------------------------------------------------------


def _python_profile() -> dict:
    return {
        "language": {"primary": "python"},
        "archetype": "python_project",
        "delivery": {
            "python": {
                "source_layout": "svp_native",
                "package_name": "demo_pkg",
            }
        },
    }


def _r_profile() -> dict:
    return {
        "language": {"primary": "r"},
        "archetype": "r_project",
        "delivery": {"r": {}},
    }


def _plugin_profile() -> dict:
    return {
        "language": {"primary": "python"},
        "archetype": "claude_code_plugin",
        "delivery": {"python": {"source_layout": "svp_native"}},
    }


def _svp_build_profile() -> dict:
    return {
        "language": {"primary": "python"},
        "archetype": "python_project",
        "is_svp_build": True,
        "delivery": {"python": {"source_layout": "svp_native"}},
    }


# Minimal workspace scaffolding so assemble_python_project's S3-146 helpers
# don't error. The S3-147 fix is independent of the test-copy step but the
# assembler chain runs both.
def _scaffold_minimal_workspace(workspace: Path) -> None:
    (workspace / "scripts").mkdir(parents=True, exist_ok=True)
    (workspace / "scripts" / "__init__.py").write_text("")
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "tests" / "__init__.py").write_text("")


# ---------------------------------------------------------------------------
# Direct helper tests
# ---------------------------------------------------------------------------


def test_write_delivered_claude_md_writes_for_a_d_archetype(tmp_path):
    repo = tmp_path / "demo-repo"
    repo.mkdir()

    wrote = write_delivered_claude_md(repo, _python_profile(), "demo")
    assert wrote is True
    claude = repo / "CLAUDE.md"
    assert claude.is_file()
    content = claude.read_text()
    assert content.startswith("# demo\n")
    assert "Manual Bug-Fixing Protocol" in content
    assert "Break-Glass Mode" in content
    assert "**RULE 0:" in content
    # 8-step cycle markers
    for step in (
        "1. **DIAGNOSE**",
        "2. **PLAN**",
        "3. **EXECUTE**",
        "4. **EVALUATE**",
        "5. **LESSONS LEARNED**",
        "6. **REGRESSION TESTS**",
        "7. **VERIFY**",
        "8. **COMMIT TO GIT**",
    ):
        assert step in content, f"Cycle step not found: {step!r}"


def test_write_delivered_claude_md_skips_svp_build(tmp_path):
    repo = tmp_path / "svp-repo"
    repo.mkdir()
    pre_existing = "# pre-existing SVP-meta CLAUDE.md content\n"
    (repo / "CLAUDE.md").write_text(pre_existing)

    wrote = write_delivered_claude_md(repo, _svp_build_profile(), "svp")
    assert wrote is False
    # Pre-existing content is preserved (we did not overwrite).
    assert (repo / "CLAUDE.md").read_text() == pre_existing


def test_delivered_claude_md_omits_svp_internal_phrases(tmp_path):
    repo = tmp_path / "demo-repo"
    repo.mkdir()
    write_delivered_claude_md(repo, _python_profile(), "demo")

    content = (repo / "CLAUDE.md").read_text()
    # The intro mentions SVP once (the project came from it). After that,
    # no SVP-internal orchestration references should appear, because a
    # user reading this is NOT running SVP.
    forbidden = (
        "pipeline_state.json",
        "PREPARE command",
        "POST command",
        "routing script",
        "scripts/routing.py",
        "ACTION above",
        "TASK_PROMPT_FILE",
        "Six-Step Action Cycle",
    )
    for phrase in forbidden:
        assert phrase not in content, (
            f"Delivered CLAUDE.md leaked SVP-internal phrase: {phrase!r}"
        )


# ---------------------------------------------------------------------------
# Integration tests via the three primary assemblers
# ---------------------------------------------------------------------------


def test_python_assembler_writes_delivered_claude_md(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _scaffold_minimal_workspace(workspace)

    repo_dir = assemble_python_project(
        workspace, _python_profile(), {"description": "demo"}
    )
    claude = repo_dir / "CLAUDE.md"
    assert claude.is_file()
    assert "Manual Bug-Fixing Protocol" in claude.read_text()


def test_r_assembler_writes_delivered_claude_md(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    repo_dir = assemble_r_project(workspace, _r_profile(), {"description": "demo"})
    claude = repo_dir / "CLAUDE.md"
    assert claude.is_file()
    assert "Manual Bug-Fixing Protocol" in claude.read_text()


def test_plugin_assembler_writes_delivered_claude_md(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    repo_dir = assemble_plugin_project(
        workspace, _plugin_profile(), {"description": "demo"}
    )
    claude = repo_dir / "CLAUDE.md"
    assert claude.is_file()
    assert "Manual Bug-Fixing Protocol" in claude.read_text()


# ---------------------------------------------------------------------------
# Bug S3-183 (cycle E3): orchestrator_break_glass primer injection.
# ---------------------------------------------------------------------------


# Distinctive marker phrases drawn directly from
# scripts/primers/r/orchestrator_break_glass.md. If E1's primer file is moved
# or substantially rewritten, update these markers — the assertions are
# deliberately phrase-based (not header-based) so a refactor of the primer's
# top-level heading does not silently invalidate the test.
_R_PRIMER_MARKER = "R Architectural Primer"
_R_PRIMER_BODY_MARKER = "covr's attribution chain"
_PRIMER_SECTION_HEADER = "## Orchestrator Break-Glass Primer (Archetype-Specific)"


def _find_workspace_root() -> Path:
    """Walk up from this test file to find a directory under which both
    ``scripts/toolchain_defaults/`` and ``scripts/primers/r/`` resolve.

    Two layouts are supported (dual-layout pattern, mirrors the helper in
    `tests/regressions/test_s3_181_r_primers.py`):

      - Workspace layout: project_root contains ``scripts/...`` directly.
        Returns the project_root itself.
      - Repo layout: project_root contains ``svp/scripts/...``. Returns
        ``project_root / "svp"`` so that the manifest's workspace-relative
        primer path (``scripts/primers/r/orchestrator_break_glass.md``)
        resolves against the returned root.

    The returned path is the value to pass as ``project_root`` to
    ``write_delivered_claude_md`` so the manifest + primer paths align.
    """
    here = Path(__file__).resolve()
    for ancestor in [here, *here.parents]:
        if (ancestor / "scripts" / "primers" / "r" / "orchestrator_break_glass.md").is_file():
            return ancestor
        if (ancestor / "svp" / "scripts" / "primers" / "r" / "orchestrator_break_glass.md").is_file():
            return ancestor / "svp"
    raise RuntimeError(
        f"Could not locate workspace root (scripts/primers/r/orchestrator_break_glass.md missing) from {here}"
    )


def test_orchestrator_primer_appended_for_r_archetype(tmp_path):
    """R profile + project_root pointing at workspace -> primer section
    appended after the standard template."""
    workspace_root = _find_workspace_root()
    repo = tmp_path / "demo-repo"
    repo.mkdir()

    wrote = write_delivered_claude_md(
        repo, _r_profile(), "demo", project_root=workspace_root
    )
    assert wrote is True
    content = (repo / "CLAUDE.md").read_text()

    # Primer section header must be present.
    assert _PRIMER_SECTION_HEADER in content
    # Primer body markers must appear (drawn from the actual file).
    assert _R_PRIMER_MARKER in content
    assert _R_PRIMER_BODY_MARKER in content


def test_orchestrator_primer_not_appended_for_python_archetype(tmp_path):
    """Python profile (manifest's primer field is empty) -> no primer
    section appended even with a valid project_root."""
    workspace_root = _find_workspace_root()
    repo = tmp_path / "demo-repo"
    repo.mkdir()

    write_delivered_claude_md(
        repo, _python_profile(), "demo", project_root=workspace_root
    )
    content = (repo / "CLAUDE.md").read_text()

    assert _PRIMER_SECTION_HEADER not in content
    assert _R_PRIMER_MARKER not in content


def test_orchestrator_primer_not_appended_when_project_root_is_none(tmp_path):
    """Back-compat: caller does not pass project_root -> no primer section,
    template unchanged."""
    repo = tmp_path / "demo-repo"
    repo.mkdir()

    write_delivered_claude_md(repo, _r_profile(), "demo")
    content = (repo / "CLAUDE.md").read_text()

    assert _PRIMER_SECTION_HEADER not in content
    # Template content still present.
    assert "Manual Bug-Fixing Protocol" in content


def test_orchestrator_primer_not_appended_when_primary_language_missing(tmp_path):
    """Profile without language.primary -> defensive no-op, no crash."""
    workspace_root = _find_workspace_root()
    repo = tmp_path / "demo-repo"
    repo.mkdir()
    profile_no_language = {
        "archetype": "python_project",
        "delivery": {"python": {"source_layout": "svp_native"}},
    }

    wrote = write_delivered_claude_md(
        repo, profile_no_language, "demo", project_root=workspace_root
    )
    assert wrote is True
    content = (repo / "CLAUDE.md").read_text()
    assert _PRIMER_SECTION_HEADER not in content


def test_orchestrator_primer_not_appended_when_manifest_missing(tmp_path):
    """project_root pointing at a directory with no toolchain_defaults/ ->
    defensive no-op, no crash."""
    repo = tmp_path / "demo-repo"
    repo.mkdir()
    bare_root = tmp_path / "bare"
    bare_root.mkdir()  # No scripts/toolchain_defaults/ inside.

    wrote = write_delivered_claude_md(
        repo, _r_profile(), "demo", project_root=bare_root
    )
    assert wrote is True
    content = (repo / "CLAUDE.md").read_text()
    assert _PRIMER_SECTION_HEADER not in content


def test_orchestrator_primer_not_appended_when_primer_file_missing(tmp_path):
    """Manifest declares a primer path but the file is absent -> defensive
    no-op, no crash. Synthesises a fixture project_root with a manifest
    pointing at a nonexistent primer file."""
    repo = tmp_path / "demo-repo"
    repo.mkdir()
    fixture_root = tmp_path / "fixture"
    (fixture_root / "scripts" / "toolchain_defaults").mkdir(parents=True)

    # Build a minimal manifest that points at a primer file that does NOT exist.
    manifest = {
        "toolchain_id": "r_renv_testthat",
        "language": "r",
        "language_architecture_primers": {
            "orchestrator_break_glass": "scripts/primers/r/does_not_exist.md"
        },
    }
    (
        fixture_root
        / "scripts"
        / "toolchain_defaults"
        / "r_renv_testthat.json"
    ).write_text(json.dumps(manifest))

    wrote = write_delivered_claude_md(
        repo, _r_profile(), "demo", project_root=fixture_root
    )
    assert wrote is True
    content = (repo / "CLAUDE.md").read_text()
    assert _PRIMER_SECTION_HEADER not in content


def test_existing_template_content_preserved_when_primer_appended(tmp_path):
    """When the primer section is appended, the standard template content
    (RULE 0, the 8-step cycle, the protocol header) must still be present
    in full alongside it."""
    workspace_root = _find_workspace_root()
    repo = tmp_path / "demo-repo"
    repo.mkdir()

    write_delivered_claude_md(
        repo, _r_profile(), "demo", project_root=workspace_root
    )
    content = (repo / "CLAUDE.md").read_text()

    # Primer present.
    assert _PRIMER_SECTION_HEADER in content
    # Template invariants still intact.
    assert "Manual Bug-Fixing Protocol" in content
    assert "Break-Glass Mode" in content
    assert "**RULE 0:" in content
    for step in (
        "1. **DIAGNOSE**",
        "2. **PLAN**",
        "3. **EXECUTE**",
        "4. **EVALUATE**",
        "5. **LESSONS LEARNED**",
        "6. **REGRESSION TESTS**",
        "7. **VERIFY**",
        "8. **COMMIT TO GIT**",
    ):
        assert step in content, f"Cycle step not found alongside primer: {step!r}"
    # The primer section must appear AFTER the standard template body.
    template_marker_pos = content.find("8. **COMMIT TO GIT**")
    primer_marker_pos = content.find(_PRIMER_SECTION_HEADER)
    assert template_marker_pos != -1 and primer_marker_pos != -1
    assert primer_marker_pos > template_marker_pos


def test_orchestrator_primer_appended_via_assemble_r_project(tmp_path):
    """Integration test: the assembler entry point passes project_root to
    write_delivered_claude_md, so an R archetype assembled at the workspace
    root carries the primer section in its delivered CLAUDE.md."""
    workspace_root = _find_workspace_root()
    # assemble_r_project derives project_name from project_root.name; copy
    # the scripts/toolchain_defaults/ subtree into a tmp workspace so the
    # primer path resolves correctly when project_root is the tmp project.
    project_root = tmp_path / "child"
    project_root.mkdir()
    # Mirror the scripts/ subtree the helper needs.
    src_scripts = workspace_root / "scripts"
    dst_scripts = project_root / "scripts"
    import shutil

    shutil.copytree(
        src_scripts / "toolchain_defaults",
        dst_scripts / "toolchain_defaults",
    )
    shutil.copytree(
        src_scripts / "primers",
        dst_scripts / "primers",
    )

    repo_dir = assemble_r_project(
        project_root, _r_profile(), {"description": "demo"}
    )
    content = (repo_dir / "CLAUDE.md").read_text()
    assert _PRIMER_SECTION_HEADER in content
    assert _R_PRIMER_MARKER in content

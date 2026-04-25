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

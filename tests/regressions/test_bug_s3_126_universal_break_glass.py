"""Regression tests for Bug S3-126: universal Manual Bug-Fixing Protocol in Tier 1.

Before S3-126, CLAUDE_MD_SVP_ADDENDUM (Tier 2, E/F only) carried the entire
Manual Bug-Fixing Protocol (Break-Glass Mode), so A-D projects never received
any break-glass guidance when their SVP routing broke down. Neither tier
prescribed a COMMIT TO GIT step, so fixes never closed the loop in version
control.

S3-126 promotes a universal break-glass protocol into CLAUDE_MD_TEMPLATE
(Tier 1) with a COMMIT TO GIT step aware of:

- the sibling delivered repo at `{project_name}-repo/`,
- `delivered_repo_path` persisted in `.svp/pipeline_state.json`,
- `project_profile.json::vcs.commit_style` / `vcs.commit_template`.

CLAUDE_MD_SVP_ADDENDUM becomes an override addendum that layers SVP self-build
overrides (stubs as source of truth, deployed artifacts, sync, test-from-both)
on top of Tier 1 instead of restating the cycle. The idempotency marker used
by enrich_claude_md_for_svp_build is changed from "Manual Bug-Fixing Protocol"
(now present in Tier 1 by default) to "SVP Self-Build Override" (unique to
Tier 2).

These tests lock the following invariants:

1. Tier 1 alone (A-D create_new_project output) contains the universal
   protocol with COMMIT TO GIT, sibling-repo awareness, and profile lookup.
2. Tier 2 override addendum contains only the self-build overrides and
   references its unique marker string.
3. Tier 2 does NOT duplicate the Tier 1 COMMIT TO GIT step block.
4. enrich_claude_md_for_svp_build is idempotent on the new marker: running
   it twice on the same CLAUDE.md produces byte-equal content, and running
   it on a plain Tier-1 CLAUDE.md correctly appends Tier 2 (the old
   "Manual Bug-Fixing Protocol" marker would short-circuit).
5. create_new_project writes CLAUDE.md with Tier 1 only; the Tier 2 marker
   is absent until enrich_claude_md_for_svp_build runs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from svp_launcher import (
    CLAUDE_MD_SVP_ADDENDUM,
    CLAUDE_MD_TEMPLATE,
    create_new_project,
    enrich_claude_md_for_svp_build,
)


# ---------------------------------------------------------------------------
# Tier 1: universal break-glass protocol content
# ---------------------------------------------------------------------------


class TestTier1UniversalProtocol:
    """Tier 1 CLAUDE.md contains the universal Manual Bug-Fixing Protocol."""

    def _render(self, name: str = "sample-project") -> str:
        return CLAUDE_MD_TEMPLATE.format(project_name=name)

    def test_protocol_heading_present(self) -> None:
        rendered = self._render()
        assert "## Manual Bug-Fixing Protocol (Break-Glass Mode)" in rendered

    def test_rule_zero_present(self) -> None:
        rendered = self._render()
        assert "RULE 0" in rendered
        assert "NEVER directly fix a bug" in rendered
        assert "enter plan mode first" in rendered

    def test_commit_to_git_step_present(self) -> None:
        rendered = self._render()
        assert "**COMMIT TO GIT**" in rendered

    def test_sibling_repo_path_substituted(self) -> None:
        rendered = self._render(name="my-proj")
        assert "my-proj-repo/" in rendered
        # And the bare placeholder must not survive.
        assert "{project_name}-repo/" not in rendered

    def test_workspace_not_git_repo_warning(self) -> None:
        rendered = self._render()
        assert "workspace is NOT a git repository" in rendered
        assert "sibling" in rendered

    def test_references_delivered_repo_path(self) -> None:
        rendered = self._render()
        assert "delivered_repo_path" in rendered
        assert ".svp/pipeline_state.json" in rendered

    def test_references_profile_and_commit_style(self) -> None:
        rendered = self._render()
        assert "project_profile.json" in rendered
        assert "vcs.commit_style" in rendered
        assert "vcs.commit_template" in rendered

    def test_default_commit_message_format(self) -> None:
        rendered = self._render()
        assert "fix: <bug-id> <short-desc>" in rendered

    def test_all_cycle_steps_present_in_order(self) -> None:
        rendered = self._render()
        # Each step must appear, and they must appear in order.
        ordered_steps = [
            "**DIAGNOSE**",
            "**PLAN**",
            "**EXECUTE**",
            "**EVALUATE**",
            "**LESSONS LEARNED**",
            "**REGRESSION TESTS**",
            "**VERIFY**",
            "**COMMIT TO GIT**",
        ]
        last_pos = -1
        for step in ordered_steps:
            pos = rendered.find(step)
            assert pos >= 0, f"step {step!r} missing from Tier 1"
            assert pos > last_pos, f"step {step!r} out of order in Tier 1"
            last_pos = pos

    def test_tier1_does_not_leak_self_build_override_marker(self) -> None:
        rendered = self._render()
        assert "SVP Self-Build Override" not in rendered

    def test_tier1_does_not_mention_stubs_or_sync_workspace(self) -> None:
        # These are Tier 2 concerns; Tier 1 must remain archetype-agnostic.
        rendered = self._render()
        assert "src/unit_*/stub.py" not in rendered
        assert "sync_workspace.sh" not in rendered
        assert "svp/commands" not in rendered
        assert "svp/skills" not in rendered


# ---------------------------------------------------------------------------
# Tier 2: SVP self-build override addendum
# ---------------------------------------------------------------------------


class TestTier2OverrideAddendum:
    """Tier 2 is an override addendum, not a standalone protocol."""

    def test_unique_marker_heading_present(self) -> None:
        assert "## SVP Self-Build Override" in CLAUDE_MD_SVP_ADDENDUM

    def test_references_stubs_as_source_of_truth(self) -> None:
        assert "src/unit_*/stub.py" in CLAUDE_MD_SVP_ADDENDUM
        assert "never in `scripts/*.py`" in CLAUDE_MD_SVP_ADDENDUM

    def test_references_sync_workspace(self) -> None:
        assert "sync_workspace.sh" in CLAUDE_MD_SVP_ADDENDUM

    def test_references_deployed_plugin_artifacts(self) -> None:
        assert "svp/commands" in CLAUDE_MD_SVP_ADDENDUM
        assert "svp/skills" in CLAUDE_MD_SVP_ADDENDUM
        assert "svp/agents" in CLAUDE_MD_SVP_ADDENDUM
        assert "svp/hooks" in CLAUDE_MD_SVP_ADDENDUM

    def test_verify_from_both_workspace_and_repo(self) -> None:
        assert "BOTH the workspace" in CLAUDE_MD_SVP_ADDENDUM

    def test_does_not_restate_tier1_cycle(self) -> None:
        # Tier 2 must not duplicate the full cycle — only layer overrides.
        # Heuristic: a second "**DIAGNOSE**" step heading would be duplication.
        assert "**DIAGNOSE**" not in CLAUDE_MD_SVP_ADDENDUM

    def test_does_not_duplicate_commit_to_git_step_block(self) -> None:
        # Tier 2 may mention "COMMIT TO GIT" (referring to Tier 1's step),
        # but must NOT contain a second **COMMIT TO GIT** bullet that
        # respecifies the profile lookup procedure.
        assert CLAUDE_MD_SVP_ADDENDUM.count("**COMMIT TO GIT**") == 0
        assert "vcs.commit_style" not in CLAUDE_MD_SVP_ADDENDUM


# ---------------------------------------------------------------------------
# enrich_claude_md_for_svp_build: idempotency on the new marker
# ---------------------------------------------------------------------------


class TestEnrichClaudeMdIdempotency:
    """enrich_claude_md_for_svp_build uses the Tier-2-unique marker."""

    def test_appends_tier2_to_plain_tier1(self, tmp_path: Path) -> None:
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(
            CLAUDE_MD_TEMPLATE.format(project_name="svc"), encoding="utf-8"
        )
        # Before: Tier 1 contains "Manual Bug-Fixing Protocol" but NOT the
        # Tier 2 marker. The old short-circuit would have refused to append.
        assert "Manual Bug-Fixing Protocol" in claude_md.read_text()
        assert "SVP Self-Build Override" not in claude_md.read_text()

        enrich_claude_md_for_svp_build(tmp_path)

        after = claude_md.read_text(encoding="utf-8")
        assert "SVP Self-Build Override" in after
        assert "src/unit_*/stub.py" in after
        assert "sync_workspace.sh" in after

    def test_idempotent_on_new_marker(self, tmp_path: Path) -> None:
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(
            CLAUDE_MD_TEMPLATE.format(project_name="svc"), encoding="utf-8"
        )
        enrich_claude_md_for_svp_build(tmp_path)
        first = claude_md.read_text(encoding="utf-8")

        enrich_claude_md_for_svp_build(tmp_path)
        second = claude_md.read_text(encoding="utf-8")

        assert first == second
        assert second.count("## SVP Self-Build Override") == 1

    def test_no_crash_when_claude_md_absent(self, tmp_path: Path) -> None:
        # Must return silently rather than raising.
        enrich_claude_md_for_svp_build(tmp_path)
        assert not (tmp_path / "CLAUDE.md").exists()


# ---------------------------------------------------------------------------
# create_new_project writes Tier 1 only
# ---------------------------------------------------------------------------


class TestCreateNewProjectShipsTier1:
    """Fresh A-D project gets Tier 1 CLAUDE.md with universal protocol."""

    def _fake_plugin_root(self, tmp_path: Path) -> Path:
        root = tmp_path / "plugin"
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "__init__.py").write_text("")
        (root / "toolchain").mkdir(parents=True)
        (root / "ruff.toml").write_text("# empty\n")
        return root

    def test_fresh_project_has_universal_protocol(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plugin_root = self._fake_plugin_root(tmp_path)
        monkeypatch.chdir(tmp_path)

        project_root = create_new_project("demo-proj", plugin_root)

        claude_md = project_root / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text(encoding="utf-8")

        # Universal protocol is installed from Stage 0.
        assert "Manual Bug-Fixing Protocol (Break-Glass Mode)" in content
        assert "**COMMIT TO GIT**" in content
        assert "demo-proj-repo/" in content
        assert "delivered_repo_path" in content
        assert "vcs.commit_style" in content

        # Tier 2 override is NOT present — this is a fresh create, not an
        # E/F self-build enrichment.
        assert "SVP Self-Build Override" not in content

    def test_enrichment_appends_tier2_once(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plugin_root = self._fake_plugin_root(tmp_path)
        monkeypatch.chdir(tmp_path)
        project_root = create_new_project("demo-proj", plugin_root)

        enrich_claude_md_for_svp_build(project_root)
        enrich_claude_md_for_svp_build(project_root)  # second call is a no-op

        content = (project_root / "CLAUDE.md").read_text(encoding="utf-8")
        assert content.count("## SVP Self-Build Override") == 1
        assert content.count("## Manual Bug-Fixing Protocol (Break-Glass Mode)") == 1

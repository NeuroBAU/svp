"""Regression tests for Bug S3-126: universal break-glass protocol in Tier 1.

Before S3-126, CLAUDE_MD_SVP_ADDENDUM (Tier 2, E/F only) carried the entire
break-glass protocol, so A-D projects never received any break-glass guidance
when their SVP routing broke down.

S3-126 promoted a universal break-glass protocol into CLAUDE_MD_TEMPLATE
(Tier 1) so every archetype's CLAUDE.md ships with break-glass guidance from
Stage 0. The original S3-126 cycle authored the Tier-1 protocol as a linear
8-step "Manual Bug-Fixing Protocol (Break-Glass Mode)" cycle ending with
COMMIT TO GIT.

S3-187 (cycle G2) introduced the Gate 6 Canonical Break-Glass Path
(Layer-Triage L1-L5 + Bug Mode + Enhancement Mode + Choosing-entry-point) in
CLAUDE_MD_DELIVERED_REPO_TEMPLATE (Tier 2 delivered template) and in the
workspace CLAUDE.md, but missed CLAUDE_MD_TEMPLATE (Tier 1 used for fresh
A-D scaffolding). S3-199 (cycle I-2) forward-ports Tier-1 to align with
Tier-2 verbatim, so both templates now carry character-identical Gate 6
canonical content (Pattern P83).

These tests lock the post-S3-199 invariants:

1. Tier 1 alone (A-D create_new_project output) contains the Gate 6
   canonical-path protocol with Layer-Triage, Bug Mode, Enhancement Mode,
   and Choosing-entry-point guidance.
2. Tier 2 override addendum contains only the SVP-self-build overrides and
   references its unique marker string.
3. Tier 2 does NOT duplicate the Tier 1 break-glass protocol.
4. enrich_claude_md_for_svp_build is idempotent on the "SVP Self-Build
   Override" marker: running it twice on the same CLAUDE.md produces
   byte-equal content.
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
# Tier 1: Gate 6 canonical break-glass path content (post-S3-199 forward-port)
# ---------------------------------------------------------------------------


class TestTier1UniversalProtocol:
    """Tier 1 CLAUDE.md contains the Gate 6 canonical break-glass path
    (forward-ported from Tier-2 by S3-199 / cycle I-2)."""

    def _render(self, name: str = "sample-project") -> str:
        return CLAUDE_MD_TEMPLATE.format(project_name=name)

    def test_gate_6_header_present(self) -> None:
        rendered = self._render()
        assert "## Gate 6 — Canonical Break-Glass Path" in rendered

    def test_old_manual_bug_fixing_protocol_header_absent(self) -> None:
        """The pre-S3-199 header MUST be absent after I-2 forward-port."""
        rendered = self._render()
        assert "## Manual Bug-Fixing Protocol (Break-Glass Mode)" not in rendered

    def test_rule_zero_present(self) -> None:
        rendered = self._render()
        assert "RULE 0" in rendered
        assert "NEVER directly fix a bug" in rendered
        assert "plan mode first" in rendered

    def test_layer_triage_L1_L5_present(self) -> None:
        """Forward-ported from Tier-2 by S3-199. Five layer markers MUST appear."""
        rendered = self._render()
        for marker in ("L1 — Reproduce", "L2 — Spec", "L3 — Blueprint",
                       "L4 — Code", "L5 — Test"):
            assert marker in rendered, f"missing layer marker {marker!r}"

    def test_bug_mode_section_present(self) -> None:
        rendered = self._render()
        assert "### Bug Mode" in rendered

    def test_enhancement_mode_section_present(self) -> None:
        rendered = self._render()
        assert "### Enhancement Mode" in rendered

    def test_choosing_entry_point_section_present(self) -> None:
        rendered = self._render()
        assert "### Choosing the entry-point" in rendered

    def test_invoke_break_glass_referenced(self) -> None:
        """The action_type emitted by routing post-G1 (S3-186)."""
        rendered = self._render()
        assert "invoke_break_glass" in rendered

    def test_debug_session_mode_referenced(self) -> None:
        """The dispatch field set by gate_6_1_mode_classification (S3-186)."""
        rendered = self._render()
        assert 'debug_session["mode"]' in rendered

    def test_bug_mode_steps_present(self) -> None:
        """Bug mode 8-step cycle markers (post-G4 / S3-189 generic phrasing)."""
        rendered = self._render()
        for step in ("DIAGNOSE", "PLAN", "EXECUTE", "EVALUATE",
                     "LESSONS LEARNED", "REGRESSION TESTS", "VERIFY", "COMMIT"):
            assert step in rendered, f"missing bug-mode step {step!r}"

    def test_enhancement_mode_steps_present(self) -> None:
        """Enhancement mode mini-pipeline markers (post-G4 generic phrasing)."""
        rendered = self._render()
        for step in ("SPEC_AMENDMENT", "BLUEPRINT_AMENDMENT", "IMPLEMENTATION",
                     "TESTS", "VERIFY", "COMMIT"):
            assert step in rendered, f"missing enhancement-mode step {step!r}"

    def test_tier1_does_not_leak_self_build_override_marker(self) -> None:
        rendered = self._render()
        assert "SVP Self-Build Override" not in rendered

    def test_tier1_does_not_mention_stubs_or_sync_workspace(self) -> None:
        """Tier 2 concerns MUST NOT leak into Tier 1.

        Note (post-S3-199): Tier-1 was forward-ported verbatim from Tier-2,
        which legitimately mentions `src/unit_*/stub.py` in the Bug Mode
        CODE step (generic guidance: stubs as source of truth). This is
        SVP-self-aware phrasing that ships in the delivered child template
        too (S3-189 deemed it generic enough). The Tier-2-unique markers
        sync_workspace.sh, svp/commands, svp/skills MUST still NOT appear
        in Tier 1.
        """
        rendered = self._render()
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


# ---------------------------------------------------------------------------
# enrich_claude_md_for_svp_build: idempotency on the SVP Self-Build marker
# ---------------------------------------------------------------------------


class TestEnrichClaudeMdIdempotency:
    """enrich_claude_md_for_svp_build uses the Tier-2-unique marker."""

    def test_appends_tier2_to_plain_tier1(self, tmp_path: Path) -> None:
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(
            CLAUDE_MD_TEMPLATE.format(project_name="svc"), encoding="utf-8"
        )
        # Before: Tier 1 contains the Gate 6 canonical path but NOT the
        # Tier 2 marker.
        assert "## Gate 6 — Canonical Break-Glass Path" in claude_md.read_text()
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
    """Fresh A-D project gets Tier 1 CLAUDE.md with Gate 6 canonical path."""

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

        # Gate 6 canonical break-glass path is installed from Stage 0.
        assert "## Gate 6 — Canonical Break-Glass Path" in content
        assert "Layer-Triage L1-L5" in content
        assert "### Bug Mode" in content
        assert "### Enhancement Mode" in content
        assert "demo-proj" in content  # project_name placeholder substituted

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
        assert content.count("## Gate 6 — Canonical Break-Glass Path") == 1

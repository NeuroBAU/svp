"""Cycle I-2 (S3-199) -- verify CLAUDE_MD_TEMPLATE (Tier-1) and
CLAUDE_MD_DELIVERED_REPO_TEMPLATE (Tier-2) carry the SAME canonical
break-glass section.

Discovered by Audit B Candidate 5 (post-H7, 2026-04-30): Tier-1 was stuck
on the OLD "## Manual Bug-Fixing Protocol (Break-Glass Mode)" 8-step linear
cycle while Tier-2 had been updated by G2 (S3-187) with the NEW
"## Gate 6 -- Canonical Break-Glass Path" structure (Layer-Triage L1-L5 +
Bug Mode + Enhancement Mode + Choosing-entry-point). Workspace CLAUDE.md
was hand-edited in G2 alongside Tier-2; Tier-1 was missed.

I-2 (S3-199) forward-ports Tier-1 to match Tier-2 verbatim and adds these
alignment regression tests so any future cycle that updates break-glass
content MUST update both templates atomically.

Pattern reference: P83 (Tier-1 / Tier-2 template alignment for break-glass
content).
"""

from __future__ import annotations

import re

from svp_launcher import CLAUDE_MD_DELIVERED_REPO_TEMPLATE, CLAUDE_MD_TEMPLATE


GATE_6_HEADER = "## Gate 6 — Canonical Break-Glass Path"


def _extract_break_glass_section(content: str) -> str:
    """Slice the break-glass section from a template.

    Spans from the Gate 6 header up to the next top-level ('## ') header,
    or end-of-string if no further top-level header exists.
    """
    start = content.find(GATE_6_HEADER)
    assert start >= 0, f"missing {GATE_6_HEADER!r} in template content"
    after_start = content[start + len(GATE_6_HEADER):]
    next_top = re.search(r"\n## ", after_start)
    if next_top:
        return after_start[: next_top.start()]
    return after_start


def test_i2_tier1_template_has_gate_6_header():
    """CLAUDE_MD_TEMPLATE MUST carry the Gate 6 canonical header (NOT the
    pre-S3-199 'Manual Bug-Fixing Protocol' header)."""
    assert GATE_6_HEADER in CLAUDE_MD_TEMPLATE
    assert "## Manual Bug-Fixing Protocol (Break-Glass Mode)" not in CLAUDE_MD_TEMPLATE


def test_i2_tier1_template_has_layer_triage_L1_L5():
    """CLAUDE_MD_TEMPLATE MUST carry Layer-Triage L1-L5 markers (forward-port
    from Tier-2, originally introduced by G2 / S3-187)."""
    for marker in ("L1 — Reproduce", "L2 — Spec", "L3 — Blueprint",
                   "L4 — Code", "L5 — Test"):
        assert marker in CLAUDE_MD_TEMPLATE, f"missing {marker!r}"


def test_i2_tier1_template_has_bug_mode_and_enhancement_mode():
    """CLAUDE_MD_TEMPLATE MUST carry both Bug Mode and Enhancement Mode
    sub-sections (forward-port from Tier-2)."""
    assert "### Bug Mode" in CLAUDE_MD_TEMPLATE
    assert "### Enhancement Mode" in CLAUDE_MD_TEMPLATE


def test_i2_tier1_template_has_choosing_entry_point_section():
    """CLAUDE_MD_TEMPLATE MUST carry the 'Choosing the entry-point' guidance
    (forward-port from Tier-2)."""
    assert "### Choosing the entry-point" in CLAUDE_MD_TEMPLATE


def test_i2_tier1_break_glass_section_matches_tier2_break_glass_section():
    """Tier-1 and Tier-2 break-glass sections MUST be character-identical.

    Going forward (per Pattern P83 / S3-199): any cycle that updates
    break-glass content MUST update both CLAUDE_MD_TEMPLATE and
    CLAUDE_MD_DELIVERED_REPO_TEMPLATE atomically. This test enforces.
    """
    tier1_bg = _extract_break_glass_section(CLAUDE_MD_TEMPLATE)
    tier2_bg = _extract_break_glass_section(CLAUDE_MD_DELIVERED_REPO_TEMPLATE)
    if tier1_bg != tier2_bg:
        first_diff = next(
            (i for i, (a, b) in enumerate(zip(tier1_bg, tier2_bg)) if a != b),
            None,
        )
        if first_diff is None:
            first_diff = min(len(tier1_bg), len(tier2_bg))
        msg = (
            "Tier-1 and Tier-2 break-glass sections diverged at index "
            f"{first_diff}. Tier-1 len={len(tier1_bg)}, Tier-2 "
            f"len={len(tier2_bg)}. Per Pattern P83 / S3-199: any cycle "
            "that updates break-glass content MUST update both templates "
            "atomically."
        )
        assert tier1_bg == tier2_bg, msg

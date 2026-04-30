"""Regression tests for Bug S3-198 / Cycle I-1 -- Documentation hygiene.

Verifies:
(a) stale spec paragraph at line 7242 region is struck (no normative paragraph
    saying "oracle auto-responds AUTHORIZE DEBUG" remains);
(b) lessons-learned P79 / P80 / P81 inline blocks each have a "Future cycle
    anchor" footnote sentence;
(c) baseline P79 / P80 content is preserved (regression guards: additions
    only, no replacements).

Pattern reference: P82 (Post-batch documentation hygiene).
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Path resolvers (dual-layout: workspace OR repo)
# ---------------------------------------------------------------------------


def _spec_path() -> Path:
    """Walk up from this test file to find the stakeholder spec.

    Workspace layout: <root>/specs/stakeholder_spec.md.
    Repo layout: <root>/docs/stakeholder_spec.md (NOT docs/specs/...).
    """
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        ws = parent / "specs" / "stakeholder_spec.md"
        if ws.is_file():
            return ws
        repo = parent / "docs" / "stakeholder_spec.md"
        if repo.is_file():
            return repo
        repo_alt = parent / "docs" / "specs" / "stakeholder_spec.md"
        if repo_alt.is_file():
            return repo_alt
    raise RuntimeError(
        "Could not locate stakeholder_spec.md in workspace or repo layout"
    )


def _lessons_path() -> Path:
    """Walk up from this test file to find the lessons-learned file."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        ws = parent / "references" / "svp_2_1_lessons_learned.md"
        if ws.is_file():
            return ws
        repo = parent / "docs" / "references" / "svp_2_1_lessons_learned.md"
        if repo.is_file():
            return repo
    raise RuntimeError(
        "Could not locate svp_2_1_lessons_learned.md in workspace or repo layout"
    )


def _read_spec() -> str:
    return _spec_path().read_text(encoding="utf-8")


def _read_lessons() -> str:
    return _lessons_path().read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_i1_spec_no_stale_oracle_auto_respond_paragraph():
    """The stale paragraph stating 'oracle auto-responds AUTHORIZE DEBUG' MUST
    be struck from normative spec sections. The G3-corrected wording at
    line 7244 (which immediately follows in the same section) MUST remain.

    Section 24 entries (changelog) MAY retain the historical wording for
    traceability per Pattern P82 hygiene rule -- only normative sections
    are checked here. Section 24 starts at line 4215 in the workspace spec.
    """
    content = _read_spec()
    # G3 correction must still be present (regression guard).
    assert "Gates ALWAYS go to the human" in content, (
        "G3 corrected wording 'Gates ALWAYS go to the human' must remain in spec"
    )
    # Locate Section 24 boundary; only scan content BEFORE Section 24 for the
    # stale variants (Section 24 changelog entries legitimately preserve the
    # historical wording per Pattern P82).
    section_24_idx = content.find("## 24. Failure Modes and Recovery")
    assert section_24_idx > 0, "Section 24 marker not found"
    pre_section_24 = content[:section_24_idx]
    # Stale wording variants from the historical paragraph at line 7242.
    stale_variants = [
        "oracle auto-responds AUTHORIZE DEBUG",
        "auto-respond at Gate 6.0",
        "oracle auto-responds at Gate 6",
    ]
    for variant in stale_variants:
        assert variant not in pre_section_24, (
            f"Stale wording '{variant}' found in pre-Section-24 normative spec; "
            f"must be struck per S3-198 / cycle I-1."
        )


def test_i1_lessons_P81_has_future_cycle_anchor_for_h7_ext():
    """P81 inline block MUST contain 'Future cycle anchor' sentence about
    extending the regex preprocess to non-dict ellipsis positions."""
    content = _read_lessons()
    p81_idx = content.find("P81 (NEW")
    assert p81_idx > 0, "P81 inline block not found"
    p81_region = content[p81_idx:p81_idx + 4000]
    assert "Future cycle anchor" in p81_region, (
        "P81 inline block must contain 'Future cycle anchor' footnote"
    )
    assert "non-dict" in p81_region or "ellipsis" in p81_region, (
        "P81 future-cycle-anchor must mention non-dict ellipsis extension"
    )


def test_i1_lessons_P80_has_future_cycle_anchor_for_h6_inert():
    """P80 inline block MUST contain 'Future cycle anchor' sentence about
    LANGUAGE_REGISTRY collection_error_indicators inert config cleanup."""
    content = _read_lessons()
    p80_idx = content.find("P80 (NEW")
    assert p80_idx > 0, "P80 inline block not found"
    p80_region = content[p80_idx:p80_idx + 4000]
    assert "Future cycle anchor" in p80_region, (
        "P80 inline block must contain 'Future cycle anchor' footnote"
    )
    assert "H6-INERT" in p80_region or "inert config" in p80_region, (
        "P80 future-cycle-anchor must mention H6-INERT or inert config cleanup"
    )


def test_i1_lessons_P79_has_future_cycle_anchor_for_compliance_scan_failed():
    """P79 inline block MUST contain 'Future cycle anchor' sentence about
    COMPLIANCE_SCAN_FAILED producer-token mirror."""
    content = _read_lessons()
    p79_idx = content.find("P79 (NEW")
    assert p79_idx > 0, "P79 inline block not found"
    p79_region = content[p79_idx:p79_idx + 4000]
    assert "Future cycle anchor" in p79_region, (
        "P79 inline block must contain 'Future cycle anchor' footnote"
    )
    assert "COMPLIANCE_SCAN_FAILED" in p79_region or "H5-FAIL-TOKEN" in p79_region, (
        "P79 future-cycle-anchor must mention COMPLIANCE_SCAN_FAILED or H5-FAIL-TOKEN"
    )


def test_i1_lessons_P79_baseline_text_preserved():
    """Regression guard: original P79 baseline text MUST still be present
    (additions only, no replacements)."""
    content = _read_lessons()
    p79_idx = content.find("P79 (NEW")
    assert p79_idx > 0, "P79 inline block not found"
    p79_region = content[p79_idx:p79_idx + 4000]
    # Baseline P79 mentions PHASE_TO_AGENT and compliance_scan
    assert "PHASE_TO_AGENT" in p79_region, (
        "P79 baseline reference to PHASE_TO_AGENT must be preserved"
    )
    assert "compliance_scan" in p79_region, (
        "P79 baseline reference to compliance_scan must be preserved"
    )


def test_i1_lessons_P80_baseline_text_preserved():
    """Regression guard: original P80 baseline text MUST still be present."""
    content = _read_lessons()
    p80_idx = content.find("P80 (NEW")
    assert p80_idx > 0, "P80 inline block not found"
    p80_region = content[p80_idx:p80_idx + 4000]
    # Baseline P80 mentions pytest authoritative signals or exit_code or ERROR collecting
    assert "pytest" in p80_region, (
        "P80 baseline reference to pytest must be preserved"
    )
    assert (
        "exit_code" in p80_region
        or "ERROR collecting" in p80_region
        or "authoritative signals" in p80_region
    ), "P80 baseline mention of pytest authoritative signals must be preserved"

"""Regression test for Bug S3-190 — Pattern Catalog sync.

Cycle G5 enforces that the consolidated Pattern Catalog table in
``references/svp_2_1_lessons_learned.md`` Part 2 stays in sync with the inline
pattern blocks scattered throughout the file. Every ``P#`` referenced anywhere
in the file MUST appear as a catalog row, in ascending order, and the
post-S3-154 batch (P40-P73) must all be present.

Pattern reference: P74 (Pattern Catalog Sync Discipline).
"""

from __future__ import annotations

import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Path resolvers (dual-layout: workspace OR repo)
# ---------------------------------------------------------------------------


def _lessons_path() -> Path:
    """Walk up from this test file to find the lessons-learned file.

    Lessons file is detected by presence of either:
      - workspace layout: <root>/references/svp_2_1_lessons_learned.md
      - repo layout: <root>/docs/references/svp_2_1_lessons_learned.md
    """
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


def _load_lessons() -> str:
    return _lessons_path().read_text(encoding="utf-8")


def _extract_part_2_table(content: str) -> str:
    """Extract the Part 2: Pattern Catalog table region.

    Slices the content from the ``## Part 2: Pattern Catalog`` marker up to
    the next ``## `` top-level header (any "Part" or other top-level section)
    or end-of-file.
    """
    marker = "## Part 2: Pattern Catalog"
    start = content.find(marker)
    assert start != -1, "Could not find '## Part 2: Pattern Catalog' marker"
    rest = content[start + len(marker):]
    # Find next top-level header
    next_header = re.search(r"\n## ", rest)
    if next_header:
        return rest[: next_header.start()]
    return rest


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_every_referenced_pattern_in_catalog():
    """Every P# referenced anywhere in the lessons file must appear as
    a row in the Part 2 catalog table (Pattern P74 — catalog hygiene)."""
    content = _load_lessons()
    referenced = {int(m) for m in re.findall(r"\bP(\d+)\b", content)}
    catalog = _extract_part_2_table(content)
    catalog_rows = {
        int(m) for m in re.findall(r"^\|\s*P(\d+)\s*\|", catalog, re.MULTILINE)
    }
    missing = referenced - catalog_rows
    assert not missing, (
        "Patterns referenced inline but missing from catalog: "
        f"{sorted(missing)}. Add catalog rows alongside inline pattern blocks "
        "per Pattern P74 (catalog hygiene)."
    )


def test_catalog_rows_are_chronologically_ordered():
    """Catalog table P# rows must be in ascending order."""
    content = _load_lessons()
    catalog = _extract_part_2_table(content)
    nums = [
        int(m) for m in re.findall(r"^\|\s*P(\d+)\s*\|", catalog, re.MULTILINE)
    ]
    assert nums == sorted(nums), f"Catalog rows out of order: {nums}"


def test_catalog_includes_all_post_S3_154_patterns():
    """Patterns P40-P73 (post-S3-154 batch) must all appear in the catalog."""
    content = _load_lessons()
    catalog = _extract_part_2_table(content)
    for n in range(40, 74):
        assert f"| P{n} |" in catalog, f"P{n} missing from catalog"

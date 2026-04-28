"""Regression test for Bug S3-171 — Calls migration coverage.

Cycle 1 (S3-170) shipped the format mandate requiring per-Unit ``## Calls``
sections in `blueprint/blueprint_contracts.md`. Cycle 2 (S3-171) migrated all
29 existing Units to comply. This regression test asserts that every
``## Unit N: ...`` heading in `blueprint_contracts.md` is followed (within its
own section, before the next ``## Unit`` heading or EOF) by a ``## Calls``
sub-block whose body is either a non-empty bullet list (lines starting with
``- ``) or the literal text ``None (leaf unit).``.

Future Units added without a ``## Calls`` block will fail this test, guarding
the format invariant that the audit cycle (S3-172) consumes.

Pattern reference: P55 — format-extension migrations are mechanical when the
format is well-specified.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# Acceptable Calls block bodies:
#   1. A non-empty bullet list (lines starting with "- ").
#   2. The literal "None (leaf unit)." line.
LEAF_LITERAL = "None (leaf unit)."


def _find_project_root() -> Path:
    """Walk up from this test file to find the project root.

    Mirrors the dual-layout resolver pattern from
    `tests/regressions/test_s3_169_doc_consistency.py`. The project root
    contains either `blueprint/blueprint_contracts.md` (workspace layout) or
    `docs/blueprint_contracts.md` (repo layout).
    """
    candidate = Path(__file__).resolve()
    for ancestor in [candidate, *candidate.parents]:
        if (ancestor / "blueprint" / "blueprint_contracts.md").exists():
            return ancestor
        if (ancestor / "docs" / "blueprint_contracts.md").exists():
            return ancestor
    raise RuntimeError(
        f"Could not locate project root (blueprint/ or docs/) from {candidate}"
    )


def _resolve_contracts_path(project_root: Path) -> Path:
    """Resolve `blueprint_contracts.md` against either workspace or repo layout."""
    workspace_path = project_root / "blueprint" / "blueprint_contracts.md"
    if workspace_path.exists():
        return workspace_path
    repo_path = project_root / "docs" / "blueprint_contracts.md"
    if repo_path.exists():
        return repo_path
    raise RuntimeError(
        f"blueprint_contracts.md not found under {project_root} (workspace or repo layout)"
    )


@pytest.fixture(scope="module")
def contracts_text() -> str:
    return _resolve_contracts_path(_find_project_root()).read_text(encoding="utf-8")


def _split_into_unit_sections(text: str) -> list[tuple[int, str, str]]:
    """Split contracts text into per-unit sections.

    Returns a list of (unit_number, heading_line, section_body) tuples. The
    section body runs from immediately after the heading line through (but not
    including) the next ``## Unit`` heading, or EOF.
    """
    headers = list(re.finditer(r"^## Unit (\d+):.*$", text, re.M))
    sections: list[tuple[int, str, str]] = []
    for i, m in enumerate(headers):
        unit_num = int(m.group(1))
        heading_line = m.group(0)
        body_start = m.end()
        body_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        sections.append((unit_num, heading_line, text[body_start:body_end]))
    return sections


def _calls_body(section_body: str) -> str | None:
    """Extract the body of the ``## Calls`` sub-block from a unit section.

    Returns the text between the ``## Calls`` heading and the next H2/H3
    heading (or end of section), stripped of leading/trailing whitespace.
    Returns None if no ``## Calls`` heading is present.
    """
    m = re.search(r"^## Calls\s*$", section_body, re.M)
    if not m:
        return None
    body_start = m.end()
    # Stop at the next H2 or H3 heading line, or section end.
    nxt = re.search(r"^(##|###) ", section_body[body_start:], re.M)
    body_end = body_start + nxt.start() if nxt else len(section_body)
    return section_body[body_start:body_end].strip()


def test_every_unit_has_calls_section(contracts_text: str) -> None:
    """Each ``## Unit N`` section must contain a ``## Calls`` sub-block.

    Acceptable contents:
      - A non-empty bullet list (one or more lines starting with ``- ``).
      - The literal ``None (leaf unit).`` text.

    Failure means the section was added without migrating to the cycle-2
    Calls format. Add a ``## Calls`` block immediately under the unit's
    ``### Tier 3 -- Behavioral Contracts`` heading; populate per-function
    citations from the unit's stub imports, or write ``None (leaf unit).``
    if the unit has no inter-unit function imports.
    """
    sections = _split_into_unit_sections(contracts_text)
    assert sections, "blueprint_contracts.md contains no '## Unit N:' headings"

    failures: list[str] = []
    for unit_num, heading_line, body in sections:
        calls_body = _calls_body(body)
        if calls_body is None:
            failures.append(
                f"Unit {unit_num} ({heading_line!r}) has no '## Calls' sub-block"
            )
            continue
        # Acceptable contents: non-empty bullet list OR literal leaf line.
        bullet_lines = [
            ln for ln in calls_body.splitlines() if ln.lstrip().startswith("- ")
        ]
        is_leaf = LEAF_LITERAL in calls_body
        if not bullet_lines and not is_leaf:
            failures.append(
                f"Unit {unit_num} ({heading_line!r}) has '## Calls' but no bullets "
                f"and no '{LEAF_LITERAL}' literal — body was: {calls_body!r}"
            )

    assert not failures, (
        "Calls-migration regression (S3-171): one or more units in "
        "blueprint_contracts.md lack a populated '## Calls' sub-block.\n  - "
        + "\n  - ".join(failures)
    )

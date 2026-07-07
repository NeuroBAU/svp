"""Regression: the Tier 3 Dependencies field is a line-start construct (P6).

An unanchored regex matched a mid-prose "**Dependencies:**" mention (in the
contract clause describing the forward-edge validator itself), turning its
"(Unit 23)" cross-reference into a phantom Unit 8 -> Unit 23 edge that
crashed infrastructure setup at DAG validation.
"""

import sys
from pathlib import Path

SCRIPTS_DIR = str(Path(__file__).resolve().parents[2] / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from blueprint_extractor import _DEPENDENCIES_RE


def _deps(tier3_text):
    import re

    m = _DEPENDENCIES_RE.search(tier3_text)
    if not m:
        return []
    return sorted(int(n) for n in re.findall(r"Unit\s+(\d+)", m.group(1)))


def test_line_start_dependencies_field_parses():
    tier3 = "**Dependencies:** Unit 1, Unit 5, Unit 12\n\n1. Some clause.\n"
    assert _deps(tier3) == [1, 5, 12]


def test_mid_prose_mention_is_not_a_dependency_field():
    tier3 = (
        "1. Invariant: the validator checks every **Dependencies:** field "
        "references only smaller unit numbers (maintained by Unit 23).\n"
    )
    assert _deps(tier3) == []


def test_none_value_yields_no_dependencies():
    assert _deps("**Dependencies:** None\n") == []

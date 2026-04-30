"""Cycle J-1 (S3-201) -- post-closure WGCNA-discovered bug fixes.

Two surgical fixes shipped together:
(a) J-1a: _prepare_setup_agent (Unit 13) now loads ledgers/setup_dialog.jsonl
    and injects it as a "Dialog History" section. Spec section 3.2 line 152
    ledger-injection mandate enforced. Pattern P85.
(b) J-1b: _parse_blueprint_package_deps (Unit 11) now re-checks the None
    sentinel after paren-strip so inline-elaborated forms like
    "None (stdlib only -- argparse, sys, pathlib)." are recognized.
    Pattern P86.

S3-103 flat-module imports.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infrastructure_setup import _parse_blueprint_package_deps
from prepare_task import prepare_task_prompt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project_root(tmp_path: Path) -> Path:
    """Create a minimal synthetic project root for setup_agent prep tests."""
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir()
    blueprint_dir = tmp_path / "blueprint"
    blueprint_dir.mkdir()
    (blueprint_dir / "blueprint_prose.md").write_text("# prose")
    (blueprint_dir / "blueprint_contracts.md").write_text("# contracts")
    state = {
        "stage": 0,
        "sub_stage": "context",
        "pass_number": 1,
        "current_unit": None,
        "status": "running",
    }
    (svp_dir / "pipeline_state.json").write_text(json.dumps(state))
    return tmp_path


def _write_setup_ledger(project_root: Path, entries: list) -> Path:
    """Write entries to ledgers/setup_dialog.jsonl and return the path."""
    ledgers_dir = project_root / "ledgers"
    ledgers_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = ledgers_dir / "setup_dialog.jsonl"
    ledger_path.write_text(
        "\n".join(json.dumps(e) for e in entries) + "\n",
        encoding="utf-8",
    )
    return ledger_path


def _write_contracts(blueprint_dir: Path, package_deps_block: str) -> Path:
    """Write a minimal blueprint_contracts.md whose Package Dependencies
    section contains the given block."""
    content = (
        "## Unit 1: Synthetic\n\n"
        "### Tier 3 -- Behavioral Contracts\n\n"
        "## Package Dependencies\n\n"
        f"{package_deps_block}\n"
    )
    contracts = blueprint_dir / "blueprint_contracts.md"
    contracts.write_text(content, encoding="utf-8")
    return contracts


# ---------------------------------------------------------------------------
# J-1a -- _prepare_setup_agent ledger injection (4 tests)
# ---------------------------------------------------------------------------


def test_j1a_setup_agent_prompt_includes_dialog_history_when_ledger_has_entries(tmp_path):
    """Bug J-1a / S3-201: when ledgers/setup_dialog.jsonl has entries,
    _prepare_setup_agent's task prompt MUST contain a "Dialog History" section
    rendering each turn's question and answer."""
    project_root = _make_project_root(tmp_path)
    entries = [
        {
            "turn": 1,
            "area": 0,
            "question": "What is the project name?",
            "answer": "WGCNA migration test project",
            "timestamp": "2026-04-30T10:00:00Z",
        },
        {
            "turn": 2,
            "area": 1,
            "question": "What is the primary language?",
            "answer": "R",
            "timestamp": "2026-04-30T10:05:00Z",
        },
        {
            "turn": 3,
            "area": 2,
            "question": "What archetype best fits?",
            "answer": "r_package",
            "timestamp": "2026-04-30T10:10:00Z",
        },
    ]
    _write_setup_ledger(project_root, entries)

    result = prepare_task_prompt(
        project_root, "setup_agent", mode="project_context"
    )

    assert "Dialog History" in result, (
        "setup_agent prompt MUST include 'Dialog History' section when "
        "ledgers/setup_dialog.jsonl has entries (spec section 3.2 line 152)"
    )
    # Every turn's question + answer text MUST appear.
    for entry in entries:
        assert entry["question"] in result, (
            f"Question text missing from Dialog History: {entry['question']!r}"
        )
        assert entry["answer"] in result, (
            f"Answer text missing from Dialog History: {entry['answer']!r}"
        )


def test_j1a_setup_agent_prompt_omits_dialog_history_when_ledger_empty(tmp_path):
    """Bug J-1a / S3-201: when the setup_dialog ledger file exists but is
    empty (zero entries), the prompt MUST NOT contain a "Dialog History"
    section."""
    project_root = _make_project_root(tmp_path)
    ledgers_dir = project_root / "ledgers"
    ledgers_dir.mkdir(parents=True, exist_ok=True)
    (ledgers_dir / "setup_dialog.jsonl").write_text("", encoding="utf-8")

    result = prepare_task_prompt(
        project_root, "setup_agent", mode="project_context"
    )

    assert "Dialog History" not in result, (
        "setup_agent prompt MUST NOT include 'Dialog History' section when "
        "ledger is empty"
    )


def test_j1a_setup_agent_prompt_omits_dialog_history_when_ledger_missing(tmp_path):
    """Bug J-1a / S3-201: when the setup_dialog ledger file does not exist,
    the prompt MUST NOT contain a 'Dialog History' section AND no exception
    must be raised."""
    project_root = _make_project_root(tmp_path)
    # Do NOT create ledgers/ directory.

    # Should not raise; should not include Dialog History.
    result = prepare_task_prompt(
        project_root, "setup_agent", mode="project_context"
    )

    assert "Dialog History" not in result, (
        "setup_agent prompt MUST NOT include 'Dialog History' section when "
        "ledger file is absent"
    )


def test_j1a_setup_agent_prompt_renders_setup_specific_entry_shape(tmp_path):
    """Bug J-1a / S3-201: setup_dialog ledger entries have the shape
    {turn, area, question, answer, timestamp} -- distinct from
    stakeholder_dialog's {role, content}. The rendered prompt MUST surface
    Turn + Area markers and the Q/A separators, NOT role/content shape."""
    project_root = _make_project_root(tmp_path)
    entries = [
        {
            "turn": 5,
            "area": 3,
            "question": "What is the test framework?",
            "answer": "testthat",
            "timestamp": "2026-04-30T10:20:00Z",
        }
    ]
    _write_setup_ledger(project_root, entries)

    result = prepare_task_prompt(
        project_root, "setup_agent", mode="project_context"
    )

    # Setup-dialog-specific markers MUST appear.
    assert "Turn 5" in result, "Turn marker missing from rendered ledger"
    assert "Area 3" in result, "Area marker missing from rendered ledger"
    assert "Q: What is the test framework?" in result, (
        "Question marker missing from rendered ledger"
    )
    assert "A: testthat" in result, "Answer marker missing from rendered ledger"


# ---------------------------------------------------------------------------
# J-1b -- _parse_blueprint_package_deps sentinel-elaboration tolerance (5 tests)
# ---------------------------------------------------------------------------


def test_j1b_dep_parser_recognizes_canonical_none_sentinel(tmp_path):
    """Bug J-1b / S3-201 (regression-lock existing behavior): the canonical
    sentinel form 'None (stdlib only).' MUST be recognized as an empty
    declaration. The pre-strip prefix check is preserved as the canonical-form
    fast path."""
    contracts = _write_contracts(tmp_path, "None (stdlib only).")
    result = _parse_blueprint_package_deps(contracts)
    assert result == set(), (
        f"Canonical sentinel must yield empty set, got {result!r}"
    )


def test_j1b_dep_parser_recognizes_bare_none_sentinel(tmp_path):
    """Bug J-1b / S3-201 (regression-lock existing behavior): the bare 'None'
    form MUST be recognized as an empty declaration."""
    contracts = _write_contracts(tmp_path, "None")
    result = _parse_blueprint_package_deps(contracts)
    assert result == set(), (
        f"Bare None sentinel must yield empty set, got {result!r}"
    )


def test_j1b_dep_parser_recognizes_elaborated_none_sentinel(tmp_path):
    """Bug J-1b / S3-201 (BUG FIX VERIFICATION): inline-elaborated sentinel
    'None (stdlib only -- argparse, sys, pathlib).' MUST be recognized as an
    empty declaration. This test WOULD HAVE FAILED before the J-1b fix
    because the pre-strip prefix check rejected the elaborated form, then
    paren-strip reduced it to bare 'None', which the parser added as a
    package."""
    contracts = _write_contracts(
        tmp_path, "None (stdlib only -- argparse, sys, pathlib)."
    )
    result = _parse_blueprint_package_deps(contracts)
    assert result == set(), (
        f"Elaborated sentinel must yield empty set (J-1b bug-fix verification), "
        f"got {result!r}"
    )
    assert "None" not in result, (
        "Literal 'None' string MUST NOT appear in returned set"
    )


def test_j1b_dep_parser_recognizes_elaborated_none_sentinel_alternative_phrasings(tmp_path):
    """Bug J-1b / S3-201: alternative inline elaborations of the None sentinel
    MUST also be recognized. The elaboration content inside the parens is
    arbitrary author prose; the parser must not depend on the specific
    'stdlib only' phrasing."""
    cases = [
        "None (no external dependencies).",
        "None (handled by os module).",
        "None (uses imported units only).",
    ]
    for case in cases:
        contracts = _write_contracts(tmp_path, case)
        result = _parse_blueprint_package_deps(contracts)
        assert result == set(), (
            f"Alternative-phrased elaborated sentinel {case!r} must yield "
            f"empty set, got {result!r}"
        )
        assert "None" not in result, (
            f"Literal 'None' must not appear when sentinel is {case!r}"
        )


def test_j1b_dep_parser_does_not_emit_literal_None_string(tmp_path):
    """Bug J-1b / S3-201: when a Package Dependencies block mixes an
    elaborated sentinel with valid packages, the parser MUST emit ONLY the
    valid packages and MUST NOT emit the literal 'None' string."""
    block = (
        "None (stdlib only -- argparse, sys, pathlib).\n"
        "numpy\n"
        "pandas\n"
        "scipy\n"
    )
    contracts = _write_contracts(tmp_path, block)
    result = _parse_blueprint_package_deps(contracts)
    # The valid packages must be present.
    assert "numpy" in result
    assert "pandas" in result
    assert "scipy" in result
    # The literal 'None' string must NOT be present.
    assert "None" not in result, (
        f"Literal 'None' string must not be emitted as a package, got {result!r}"
    )


# ---------------------------------------------------------------------------
# Cross-cutting -- WGCNA-replay end-to-end (1 test)
# ---------------------------------------------------------------------------


def test_j1_wgcna_blueprint_does_not_emit_None_package(tmp_path):
    """Bug J-1 / S3-201 cross-cutting: replay the WGCNA-discovered failure
    end-to-end using a vendored fixture file (tests/fixtures/
    wgcna_elaborated_sentinel.md). The fixture mirrors WGCNA blueprint
    line 2320 form. The parser MUST emit ONLY valid package names and MUST
    NOT emit the literal 'None' string."""
    fixture = (
        Path(__file__).resolve().parent.parent
        / "fixtures"
        / "wgcna_elaborated_sentinel.md"
    )
    assert fixture.exists(), f"Fixture file missing: {fixture}"
    result = _parse_blueprint_package_deps(fixture)

    # The fixture's Unit 2 declares numpy, pandas, scipy explicitly.
    assert "numpy" in result, (
        f"Expected numpy from fixture; got {result!r}"
    )
    assert "pandas" in result
    assert "scipy" in result
    # The fixture's Unit 1 has elaborated sentinel; the parser must NOT
    # emit 'None'.
    assert "None" not in result, (
        f"WGCNA-replay end-to-end: literal 'None' must not appear in "
        f"returned set, got {result!r}"
    )

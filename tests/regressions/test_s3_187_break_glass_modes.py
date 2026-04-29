"""Regression tests for cycle G2 (S3-187) — Gate 6 break-glass canonical
path formalization. Verifies workspace CLAUDE.md and child template
CLAUDE_MD_DELIVERED_REPO_TEMPLATE both contain the Gate 6 canonical-path
section with Layer-Triage L1-L5, bug-mode 8-step cycle, and enhancement-mode
mini-pipeline.

Pattern reference: P71 (CLAUDE.md Authoritatively Encodes Break-Glass As
A First-Class Gate 6 Path With Mode-Aware Sub-Flows).

Dash convention used in this file: em-dash (U+2014) for section headers
("## Gate 6 — Canonical Break-Glass Path", "### DIAGNOSE — Layer-Triage
L1-L5") and for layer markers ("L1 — Reproduce", ..., "L5 — Test"). The
same convention is used in workspace CLAUDE.md and the child template.
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Path resolvers (dual-layout: workspace OR repo)
# ---------------------------------------------------------------------------


def _project_root() -> Path:
    """Walk up from this test file to find the project/repo root.

    Project root is detected by presence of either:
      - workspace layout: scripts/svp_launcher.py
      - repo layout: svp/scripts/svp_launcher.py

    Same dual-layout pattern used by E1 / E4 / F1 tests.
    """
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "scripts" / "svp_launcher.py").is_file():
            return parent
        if (parent / "svp" / "scripts" / "svp_launcher.py").is_file():
            return parent
    raise RuntimeError(
        "Could not locate project root (no scripts/svp_launcher.py or "
        "svp/scripts/svp_launcher.py found walking up from "
        f"{here})"
    )


def _scripts_dir() -> Path:
    """Locate the directory containing svp_launcher.py (workspace or repo)."""
    root = _project_root()
    ws = root / "scripts"
    if (ws / "svp_launcher.py").is_file():
        return ws
    repo = root / "svp" / "scripts"
    if (repo / "svp_launcher.py").is_file():
        return repo
    raise RuntimeError("scripts dir with svp_launcher.py not found")


def _workspace_claude_md_text() -> str:
    """Read top-level workspace CLAUDE.md text.

    Workspace layout has the file directly at <root>/CLAUDE.md. In the
    repo layout, the workspace CLAUDE.md is not synced (it is the
    workspace orchestrator's project instructions, not a deliverable).
    For the repo case, fall back to the child-template content via
    Unit 29 — the test that asserts the same content is in BOTH still
    discriminates because the template is sourced from src/unit_29.
    """
    root = _project_root()
    path = root / "CLAUDE.md"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    # Repo layout fallback: workspace CLAUDE.md does not exist in the
    # delivered repo. Use the child-template constant text instead so
    # the workspace-side assertions still run with meaningful content.
    return _child_template_text()


def _child_template_text() -> str:
    """Read CLAUDE_MD_DELIVERED_REPO_TEMPLATE constant by parsing the source
    file directly.

    Avoids importing svp_launcher because (a) tests must not import from
    src.unit_*.stub (S3-103), and (b) doing `import svp_launcher` and then
    deleting it from sys.modules causes downstream test pollution (unit_29
    TestMain uses `@patch("svp_launcher.preflight_check")` and depends on
    a stable module identity across the run).

    Read the .py file as text, find the assignment, and extract the
    triple-quoted string literal verbatim. Then `.format()` it for the
    placeholder. This is the same shape that workspace CLAUDE.md uses
    (text-on-disk), so the assertions stay meaningful.
    """
    scripts = _scripts_dir()
    src = (scripts / "svp_launcher.py").read_text(encoding="utf-8")
    # Locate the constant definition. The constant is assigned with a
    # triple-quoted string; the value spans multiple lines until the
    # closing triple-quote.
    marker = 'CLAUDE_MD_DELIVERED_REPO_TEMPLATE: str = """\\'
    start = src.find(marker)
    if start == -1:
        raise RuntimeError(
            "CLAUDE_MD_DELIVERED_REPO_TEMPLATE assignment not found in "
            f"{scripts / 'svp_launcher.py'}; expected marker {marker!r}."
        )
    # Move past the marker and the trailing newline after the opening
    # triple-quote.
    body_start = src.index("\n", start) + 1
    end = src.find('"""', body_start)
    if end == -1:
        raise RuntimeError(
            "CLAUDE_MD_DELIVERED_REPO_TEMPLATE closing triple-quote not "
            f"found in {scripts / 'svp_launcher.py'}."
        )
    raw = src[body_start:end]
    # The Python source uses `\` line-continuations to concatenate parts
    # of the string literal. At runtime, `\` followed by `\n` produces no
    # newline; emulate that here.
    body = raw.replace("\\\n", "")
    return body.format(project_name="test_project")


# ---------------------------------------------------------------------------
# Locked content markers (em-dash convention; see module docstring)
# ---------------------------------------------------------------------------

GATE_6_HEADER = "## Gate 6 — Canonical Break-Glass Path"
LAYER_TRIAGE_HEADER = "### DIAGNOSE — Layer-Triage L1-L5"

LAYER_MARKERS = (
    "L1 — Reproduce",
    "L2 — Spec",
    "L3 — Blueprint",
    "L4 — Code",
    "L5 — Test",
)

LAYER_NAMES = ("Reproduce", "Spec", "Blueprint", "Code", "Test")

BUG_MODE_HEADER = "### Bug Mode"
BUG_MODE_STEPS = (
    "DIAGNOSE",
    "PLAN",
    "EXECUTE",
    "EVALUATE",
    "LESSONS LEARNED",
    "REGRESSION TESTS",
    "VERIFY",
    "SYNC",
    "TEST FROM BOTH",
)

ENHANCEMENT_MODE_HEADER = "### Enhancement Mode"
ENHANCEMENT_MODE_STEPS = (
    "SPEC_AMENDMENT",
    "BLUEPRINT_AMENDMENT",
    "IMPLEMENTATION",
    "TESTS",
    "VERIFY",
    "SYNC + COMMIT",
)

ENTRY_POINT_HEADER = "### Choosing the entry-point"


# ---------------------------------------------------------------------------
# Workspace CLAUDE.md tests
# ---------------------------------------------------------------------------


def test_workspace_claude_md_has_gate_6_canonical_path_section():
    """Workspace CLAUDE.md contains the locked Gate 6 canonical-path header."""
    text = _workspace_claude_md_text()
    assert GATE_6_HEADER in text, (
        f"workspace CLAUDE.md missing locked section header {GATE_6_HEADER!r}. "
        "Re-author the section with the em-dash variant."
    )


def test_workspace_claude_md_contains_layer_triage_L1_L5():
    """Workspace CLAUDE.md contains all five Layer-Triage L1-L5 markers."""
    text = _workspace_claude_md_text()
    assert LAYER_TRIAGE_HEADER in text, (
        f"workspace CLAUDE.md missing locked Layer-Triage header "
        f"{LAYER_TRIAGE_HEADER!r}."
    )
    missing = [m for m in LAYER_MARKERS if m not in text]
    assert not missing, (
        f"workspace CLAUDE.md missing Layer-Triage layer markers: {missing}. "
        f"All five (L1 Reproduce, L2 Spec, L3 Blueprint, L4 Code, L5 Test) "
        f"are locked content for the canonical-path section."
    )


def test_workspace_claude_md_contains_bug_mode_section():
    """Workspace CLAUDE.md contains the Bug Mode section header + step markers."""
    text = _workspace_claude_md_text()
    assert BUG_MODE_HEADER in text, (
        f"workspace CLAUDE.md missing {BUG_MODE_HEADER!r} sub-section header."
    )
    missing = [s for s in BUG_MODE_STEPS if s not in text]
    assert not missing, (
        f"workspace CLAUDE.md Bug Mode missing required step markers: "
        f"{missing}. The 8-step cycle (DIAGNOSE → PLAN → EXECUTE → "
        f"EVALUATE → LESSONS LEARNED → REGRESSION TESTS → VERIFY → "
        f"SYNC + TEST FROM BOTH) is locked content."
    )


def test_workspace_claude_md_contains_enhancement_mode_section():
    """Workspace CLAUDE.md contains the Enhancement Mode section + mini-pipeline steps."""
    text = _workspace_claude_md_text()
    assert ENHANCEMENT_MODE_HEADER in text, (
        f"workspace CLAUDE.md missing {ENHANCEMENT_MODE_HEADER!r} sub-section "
        "header."
    )
    missing = [s for s in ENHANCEMENT_MODE_STEPS if s not in text]
    assert not missing, (
        f"workspace CLAUDE.md Enhancement Mode missing required step markers: "
        f"{missing}. The mini-pipeline (SPEC_AMENDMENT → "
        f"BLUEPRINT_AMENDMENT → IMPLEMENTATION → TESTS → VERIFY → "
        f"SYNC + COMMIT) is locked content."
    )


def test_workspace_claude_md_contains_entry_point_guidance():
    """Workspace CLAUDE.md contains the entry-point guidance section."""
    text = _workspace_claude_md_text()
    assert ENTRY_POINT_HEADER in text, (
        f"workspace CLAUDE.md missing {ENTRY_POINT_HEADER!r} sub-section header."
    )
    # Sanity-check the discriminating phrasing for the two entry-points.
    assert "break-glass directly" in text, (
        "workspace CLAUDE.md entry-point section missing 'break-glass directly' "
        "guidance line."
    )
    assert "/svp:bug" in text, (
        "workspace CLAUDE.md entry-point section missing '/svp:bug' guidance line."
    )


def test_workspace_claude_md_references_invoke_break_glass():
    """Workspace CLAUDE.md mentions the invoke_break_glass action_type."""
    text = _workspace_claude_md_text()
    assert "invoke_break_glass" in text, (
        "workspace CLAUDE.md must reference the invoke_break_glass action_type "
        "introduced by G1 (S3-186) in the Gate 6 Canonical Break-Glass Path."
    )


def test_workspace_claude_md_references_state_debug_session_mode():
    """Workspace CLAUDE.md mentions debug_session["mode"] (the dispatch field)."""
    text = _workspace_claude_md_text()
    assert 'debug_session["mode"]' in text, (
        "workspace CLAUDE.md must reference debug_session[\"mode\"] (the "
        "dispatch field set by gate_6_1_mode_classification per G1 / S3-186)."
    )


# ---------------------------------------------------------------------------
# Child template (CLAUDE_MD_DELIVERED_REPO_TEMPLATE) tests
# ---------------------------------------------------------------------------


def test_child_template_has_gate_6_canonical_path_section():
    """Child template (Unit 29) contains the Gate 6 canonical-path section header."""
    text = _child_template_text()
    assert "## Gate 6" in text and "Canonical Break-Glass Path" in text, (
        "CLAUDE_MD_DELIVERED_REPO_TEMPLATE missing the Gate 6 canonical-path "
        "section header. The workspace and template MUST mirror this content."
    )


def test_child_template_contains_layer_triage_L1_L5():
    """Child template contains all five Layer-Triage L1-L5 markers."""
    text = _child_template_text()
    assert "Layer-Triage L1-L5" in text, (
        "CLAUDE_MD_DELIVERED_REPO_TEMPLATE missing 'Layer-Triage L1-L5' marker."
    )
    missing = [m for m in LAYER_MARKERS if m not in text]
    assert not missing, (
        f"CLAUDE_MD_DELIVERED_REPO_TEMPLATE missing Layer-Triage markers: "
        f"{missing}. The five locked layers must mirror the workspace text."
    )


def test_child_template_contains_bug_mode_and_enhancement_mode():
    """Child template contains both mode section headers + their step markers."""
    text = _child_template_text()
    assert BUG_MODE_HEADER in text, (
        f"CLAUDE_MD_DELIVERED_REPO_TEMPLATE missing {BUG_MODE_HEADER!r}."
    )
    assert ENHANCEMENT_MODE_HEADER in text, (
        f"CLAUDE_MD_DELIVERED_REPO_TEMPLATE missing {ENHANCEMENT_MODE_HEADER!r}."
    )
    bug_missing = [s for s in BUG_MODE_STEPS if s not in text]
    assert not bug_missing, (
        f"CLAUDE_MD_DELIVERED_REPO_TEMPLATE Bug Mode missing step markers: "
        f"{bug_missing}."
    )
    enh_missing = [s for s in ENHANCEMENT_MODE_STEPS if s not in text]
    assert not enh_missing, (
        f"CLAUDE_MD_DELIVERED_REPO_TEMPLATE Enhancement Mode missing step "
        f"markers: {enh_missing}."
    )


def test_child_and_workspace_share_layer_triage_definitions():
    """Both workspace CLAUDE.md and child template name all five layers.

    The five layer names (Reproduce, Spec, Blueprint, Code, Test) are
    locked vocabulary; they must appear in BOTH so the protocol is
    consistent across SVP self-build orchestrators (workspace) and
    delivered children (template).
    """
    workspace = _workspace_claude_md_text()
    child = _child_template_text()
    workspace_missing = [n for n in LAYER_NAMES if n not in workspace]
    child_missing = [n for n in LAYER_NAMES if n not in child]
    assert not workspace_missing, (
        f"workspace CLAUDE.md missing Layer-Triage layer names: "
        f"{workspace_missing}."
    )
    assert not child_missing, (
        f"CLAUDE_MD_DELIVERED_REPO_TEMPLATE missing Layer-Triage layer "
        f"names: {child_missing}."
    )

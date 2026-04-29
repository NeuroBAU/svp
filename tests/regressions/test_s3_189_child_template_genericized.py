"""Regression test for Bug S3-189 — Cycle G4: Genericize delivered child CLAUDE.md template.

The delivered child CLAUDE.md template (`CLAUDE_MD_DELIVERED_REPO_TEMPLATE`
constant in `src/unit_29/stub.py`) is embedded into every delivered child
project's CLAUDE.md at Stage 5 by `write_delivered_claude_md`. It must be
GENERIC — applicable to any SVP-managed project — not specific to SVP-self.

After Gate 6 inversion (G1/G2/G3), an audit found five SVP-self-specific
references in the template that confused a child project's orchestrator:

1. `references/svp_2_1_lessons_learned.md` (SVP own file)
2. SVP-specific section numbers (§17, §18.1, §22.4, §6.4, §21, §40)
3. SVP-plugin Unit-to-path mapping (Unit 25 → svp/commands/, etc.)
4. `bash sync_workspace.sh` (SVP-self machinery)
5. "TEST FROM BOTH" (SVP-self workspace+repo dual-test pattern)

This test pins the genericization with negative-presence assertions
(SVP-self markers MUST be absent) plus positive-presence assertions
(generic equivalents MUST be present) plus a workspace-exemption
assertion (workspace CLAUDE.md correctly retains SVP-self references
because SVP-self IS the project being managed there).

Pattern reference: P73 (Delivered Child CLAUDE.md Template Must Be
Genericized; Workspace CLAUDE.md Stays SVP-Self-Specific).

Per S3-103 we do NOT import from `src.unit_29.stub` directly. Instead
we read the stub file as text and extract the constant body, OR import
via the deployed `svp_launcher.py` flat module under workspace/repo.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Path resolvers (dual-layout: workspace OR repo)
# ---------------------------------------------------------------------------


def _project_root() -> Path:
    """Walk up from this test file to find the project/repo root.

    Workspace layout: `src/unit_29/stub.py` exists.
    Repo layout: `svp/scripts/svp_launcher.py` exists (deployed flat module).
    """
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "src" / "unit_29" / "stub.py").is_file():
            return parent
        if (parent / "svp" / "scripts" / "svp_launcher.py").is_file():
            return parent
    raise RuntimeError(
        "Could not locate project root containing src/unit_29/stub.py "
        "or svp/scripts/svp_launcher.py"
    )


def _stub_or_launcher_path() -> Path:
    """Return the path to the stub (workspace) or the deployed launcher (repo)."""
    root = _project_root()
    ws = root / "src" / "unit_29" / "stub.py"
    if ws.is_file():
        return ws
    repo = root / "svp" / "scripts" / "svp_launcher.py"
    if repo.is_file():
        return repo
    raise RuntimeError("Neither src/unit_29/stub.py nor svp/scripts/svp_launcher.py found")


def _workspace_claude_md_path() -> Path:
    """Locate the workspace CLAUDE.md. Workspace authoritative; repo is fallback."""
    root = _project_root()
    ws = root / "CLAUDE.md"
    if ws.is_file():
        return ws
    repo = root / "docs" / "CLAUDE.md"
    if repo.is_file():
        return repo
    raise RuntimeError(f"Could not locate workspace CLAUDE.md from {root}")


# ---------------------------------------------------------------------------
# Constant-body extractors
# ---------------------------------------------------------------------------


def _extract_constant_body(source: str, constant_name: str) -> str:
    """Extract the triple-quoted body of a `name: str = ...` constant.

    Looks for the assignment of the form ``<constant_name>: str = <triple-quote>...<triple-quote>``
    and returns the raw body. Backslash-line-continuations are preserved verbatim.
    """
    triple = '"' * 3
    pattern = (
        rf'{re.escape(constant_name)}\s*:\s*str\s*=\s*{triple}\\?\n(.*?){triple}'
    )
    m = re.search(pattern, source, re.DOTALL)
    if not m:
        raise RuntimeError(
            f"Could not extract constant {constant_name!r} from source "
            f"(length={len(source)})"
        )
    return m.group(1)


def _load_delivered_template() -> str:
    """Load the CLAUDE_MD_DELIVERED_REPO_TEMPLATE constant body as a string."""
    path = _stub_or_launcher_path()
    source = path.read_text(encoding="utf-8")
    return _extract_constant_body(source, "CLAUDE_MD_DELIVERED_REPO_TEMPLATE")


def _read_workspace_claude_md() -> str:
    """Read the workspace CLAUDE.md content."""
    return _workspace_claude_md_path().read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Negative assertions — delivered template MUST NOT contain SVP-self markers
# ---------------------------------------------------------------------------


def test_template_does_not_reference_svp_self_lessons_file():
    """Delivered template must not point to references/svp_2_1_lessons_learned.md.

    That is SVP's own lessons file; children write to their own
    `references/lessons_learned.md` (orchestrator creates if absent on
    first break-glass use). Per C-23-G4b (Unit 23 contract clause).
    """
    template = _load_delivered_template()
    assert "svp_2_1_lessons_learned" not in template, (
        "Delivered child CLAUDE.md template references SVP-self lessons "
        "file 'svp_2_1_lessons_learned'. Per spec §40.8 and C-23-G4b, "
        "use the generic 'references/lessons_learned.md' instead."
    )


@pytest.mark.parametrize(
    "marker",
    ["§17", "§18.1", "§22.4", "§6.4", "§21", "§40"],
)
def test_template_does_not_reference_svp_specific_section_numbers(marker: str):
    """Delivered template must not reference SVP's specific section numbers.

    Children's specs are free-form per stakeholder_dialog convention and
    use different numbering. Use topic-named section discovery instead.
    Per C-23-G4b (Unit 23 contract clause).
    """
    template = _load_delivered_template()
    assert marker not in template, (
        f"Delivered child CLAUDE.md template references SVP-self section "
        f"number {marker!r}. Per spec §40.8 and C-23-G4b, use topic-named "
        f"section discovery (e.g. 'sections covering routing, statuses, "
        f"state, setup, archetypes')."
    )


@pytest.mark.parametrize(
    "marker",
    [
        "Unit 25",
        "Unit 26",
        "Unit 23 → svp/",
        "svp/commands/",
        "svp/skills/",
        "svp/agents/",
        "svp/hooks/",
    ],
)
def test_template_does_not_reference_svp_plugin_unit_paths(marker: str):
    """Delivered template must not reference SVP's Unit-to-svp/ mapping.

    Children produce Python packages, R packages, or standalone CLIs —
    NOT SVP-plugin artifacts. Per C-23-G4b (Unit 23 contract clause).
    """
    template = _load_delivered_template()
    assert marker not in template, (
        f"Delivered child CLAUDE.md template references SVP-plugin "
        f"deployment marker {marker!r}. Per spec §40.8 and C-23-G4b, use "
        f"generic distribution guidance (e.g. 'if your project produces "
        f"deployable artifacts, update them')."
    )


def test_template_does_not_reference_sync_workspace_sh():
    """Delivered template must not reference SVP's sync_workspace.sh script.

    SVP-self machinery: children are typically single-repo with no
    workspace+repo split. Per C-23-G4b (Unit 23 contract clause).
    """
    template = _load_delivered_template()
    assert "bash sync_workspace.sh" not in template, (
        "Delivered child CLAUDE.md template references 'bash "
        "sync_workspace.sh'. Per spec §40.8 and C-23-G4b, drop the SYNC "
        "step entirely."
    )
    assert "sync_workspace.sh" not in template, (
        "Delivered child CLAUDE.md template references 'sync_workspace.sh'. "
        "Per spec §40.8 and C-23-G4b, drop the SYNC step entirely."
    )


def test_template_does_not_reference_test_from_both():
    """Delivered template must not reference workspace+repo dual-test pattern.

    SVP-self machinery: children are typically single-repo. Per C-23-G4b
    (Unit 23 contract clause).
    """
    template = _load_delivered_template()
    assert "TEST FROM BOTH" not in template, (
        "Delivered child CLAUDE.md template references 'TEST FROM BOTH'. "
        "Per spec §40.8 and C-23-G4b, use single-repo verify (e.g. "
        "'pytest 0 fail / 0 skip')."
    )
    assert "from BOTH" not in template, (
        "Delivered child CLAUDE.md template references 'from BOTH'. Per "
        "spec §40.8 and C-23-G4b, use single-repo verify."
    )


# ---------------------------------------------------------------------------
# Positive assertions — delivered template MUST contain generic equivalents
# ---------------------------------------------------------------------------


def test_template_uses_generic_lessons_learned_path():
    """Delivered template references the generic lessons-learned file path.

    Per C-23-G4c (Unit 23 contract clause): the generic destination
    `references/lessons_learned.md` MUST appear in the template.
    """
    template = _load_delivered_template()
    assert "references/lessons_learned.md" in template, (
        "Delivered child CLAUDE.md template missing generic lessons-learned "
        "path 'references/lessons_learned.md'. Per spec §40.8 and "
        "C-23-G4c, use this generic destination (orchestrator creates if "
        "absent on first break-glass use)."
    )


def test_template_uses_generic_spec_phrasing():
    """Delivered template uses generic 'your spec' phrasing.

    Per C-23-G4c (Unit 23 contract clause): topic-named section discovery
    via 'your spec' (or equivalent generic project-spec phrasing) MUST
    appear in the template.
    """
    template = _load_delivered_template()
    assert "your spec" in template.lower(), (
        "Delivered child CLAUDE.md template missing generic 'your spec' "
        "phrasing. Per spec §40.8 and C-23-G4c, parameterize spec-section "
        "discovery for the child's spec."
    )


def test_template_uses_topic_based_section_discovery():
    """Delivered template instructs orchestrator to find sections by topic, not by number.

    Per C-23-G4c (Unit 23 contract clause): the substring 'match by topic'
    (or equivalent topic-based section-discovery instruction) MUST appear
    in the template.
    """
    template = _load_delivered_template()
    lower = template.lower()
    assert "match by topic" in lower or "match section by topic" in lower, (
        "Delivered child CLAUDE.md template missing topic-based section-"
        "discovery instruction ('match by topic' or 'match section by "
        "topic'). Per spec §40.8 and C-23-G4c, instruct the orchestrator "
        "to find sections by topic, not by number."
    )


def test_template_uses_generic_distribution_phrasing():
    """Delivered template's DEPLOYED ARTIFACTS step uses generic distribution guidance.

    Per C-23-G4c (Unit 23 contract clause): the DEPLOYED ARTIFACTS step
    MUST use generic phrasing referencing 'your project' and either
    'distribution' or 'packaging'. Alternatively, the step may be dropped
    entirely (no DEPLOYED ARTIFACTS heading) for projects that have no
    separate deployment surface.
    """
    template = _load_delivered_template()
    if "DEPLOYED ARTIFACTS" in template:
        lower = template.lower()
        assert "your project" in lower, (
            "Delivered child CLAUDE.md template's DEPLOYED ARTIFACTS step "
            "lacks 'your project' generic phrasing. Per spec §40.8 and "
            "C-23-G4c, use generic distribution guidance."
        )
        assert "distribution" in lower or "packaging" in lower, (
            "Delivered child CLAUDE.md template's DEPLOYED ARTIFACTS step "
            "lacks 'distribution' or 'packaging' generic phrasing. Per "
            "spec §40.8 and C-23-G4c, use generic distribution guidance."
        )


# ---------------------------------------------------------------------------
# Workspace exemption — workspace CLAUDE.md correctly retains SVP-self refs
# ---------------------------------------------------------------------------


def test_workspace_claude_md_keeps_svp_self_references_unchanged():
    """Workspace CLAUDE.md is the orchestrator's project instructions for
    SVP-self managing SVP — its SVP-specific references are correct and
    must not be affected by G4.

    Per C-23-G4d (Unit 23 contract clause): workspace CLAUDE.md is NOT
    subject to C-23-G4b — it correctly retains SVP-self-specific
    references because SVP-self IS the project being managed there.

    This test ASSERTS that the workspace CLAUDE.md still references
    `svp_2_1_lessons_learned`, which is the canonical SVP-self lessons
    file. If a future cycle accidentally over-applies the genericization
    to the workspace file, this test fails immediately.
    """
    workspace_claude = _read_workspace_claude_md()
    assert "svp_2_1_lessons_learned" in workspace_claude, (
        "Workspace CLAUDE.md should retain SVP-self-specific reference "
        "to 'svp_2_1_lessons_learned' (the canonical SVP lessons file). "
        "Per spec §40.8 and C-23-G4d, only the delivered child template "
        "is genericized; workspace CLAUDE.md stays SVP-self-specific "
        "because SVP-self IS the project being managed there."
    )

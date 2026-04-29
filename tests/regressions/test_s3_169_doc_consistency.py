"""Regression test for Bug S3-169 — Documentation consistency sweep.

This test asserts that key concepts introduced post-S3-153 (the pipeline-improvements +
specialist-dispatch-wiring batches, S3-154..S3-168) appear in ALL THREE primary
documentation files: stakeholder spec, blueprint prose, and blueprint contracts.

The test catches future drift mechanically: if a future cycle adds a concept to
code+contracts but not to prose+spec, this test fails with a precise pointer to the
file/concept pair that lapsed.

Pattern reference: P53 (Porting Modifications Upstream Is Mandatory, Not Optional).
"""

from __future__ import annotations

from pathlib import Path

import pytest


# Concepts introduced post-S3-153 that MUST appear in all three primary doc files.
# Each tuple: (concept_id, search_string). The search is case-sensitive and substring-
# based; concepts use a canonical name that matches the source-of-truth identifier.
CONCEPTS = [
    "requires_statistical_analysis",
    # Use the snake_case canonical identifier rather than the prose phrasing "Statistical
    # Correctness Reviewer" — the snake_case form is what blueprint_contracts.md uses
    # uniformly (per the contracts-as-formal-spec convention) and what spec/prose also
    # cite alongside the human-readable phrasing.
    "statistical_correctness_reviewer",
    "Socratic Question Format",
    "audit_blueprint_contracts",
    "verify_toolchain_ready",
    "BLUEPRINT_AUTHOR_STATISTICAL_PRIMER",
    "STAKEHOLDER_DIALOG_STATISTICAL_PRIMER",
    "TEST_AGENT_STATISTICAL_PRIMER",
    "statistical_review_done",
    "per-function Calls citations",
    "language_architecture_primers",
    "Package Dependencies",
    # NEW IN S3-181 (cycle E1 — R architectural primers).
    # The directory path appears verbatim in spec section 40, blueprint_prose
    # Unit 4, and blueprint_contracts Unit 4 — it is the canonical reference
    # for every primer file authored by this cycle. Adding the path itself
    # (rather than a single-word concept name) catches drift symmetrically
    # in all three docs without conflating the singular vs. plural form of
    # the existing language_architecture_primers concept.
    "scripts/primers/r/",
    # NEW IN S3-184 (cycle E4 — Python architectural primers authoring).
    # Mirror of "scripts/primers/r/": the directory path appears verbatim
    # in spec section 40 (R + Python primer note) + section 24.198, in
    # blueprint_prose Unit 4, and in blueprint_contracts Unit 4. Adding
    # the path itself catches drift symmetrically across the three docs.
    "scripts/primers/python/",
    # NEW IN S3-182 (cycle E2 — wire R primers into prepare_task).
    # The dispatch helper's literal name is the discriminating identifier
    # across spec normative text, blueprint prose, and blueprint contracts —
    # if a future cycle changes prose without updating contracts (or vice
    # versa), this concept's absence in one of the three docs flags the gap.
    "_get_language_architecture_primer",
    # NEW IN S3-183 (cycle E3 — orchestrator primer in child CLAUDE.md).
    # The dispatch helper's literal name is the discriminating identifier
    # for the Stage 5 delivery surface (distinct from S3-182's prepare_task
    # surface) across spec normative text, blueprint prose, and blueprint
    # contracts.
    "_get_orchestrator_break_glass_primer_text",
    # NEW IN S3-185 (cycle F1 — synthetic Rust archetype + extending-languages.md).
    # Mirror of "scripts/primers/r/" and "scripts/primers/python/": the
    # directory path appears verbatim in spec section 40 (synthetic Rust
    # worked example note) + section 24.199, in blueprint_prose Unit 4, and
    # in blueprint_contracts Unit 4. Adding the path itself catches drift
    # symmetrically across the three docs.
    "scripts/primers/rust/",
    # NEW IN S3-186 (cycle G1 of Gate 6 break-glass inversion sub-project).
    # The new gate ID and action_type are the discriminating identifiers
    # across spec normative text (sections 17, 18.1, 22.4, 12.18.1, 24.200),
    # blueprint_prose (Unit 6 + Unit 14 narratives), and blueprint_contracts
    # (Unit 6 enter_debug_session post-condition + Unit 14 GATE_VOCABULARY,
    # _route_debug routing branches, dispatch_gate_response handlers).
    "gate_6_1_mode_classification",
    "invoke_break_glass",
]


# Doc files that MUST mention every concept. Paths are relative to the project root;
# the locator below walks up from this test file to find the correct root in either
# workspace or repo layout (see cycle 6 precedent — `blueprint/` vs `docs/` per layout).
DOC_FILES_RELATIVE = [
    "specs/stakeholder_spec.md",
    "blueprint/blueprint_prose.md",
    "blueprint/blueprint_contracts.md",
]


def _find_project_root() -> Path:
    """Walk up from this test file to find the project root.

    The project root contains either `specs/stakeholder_spec.md` (workspace layout) or
    `docs/stakeholder_spec.md` (repo layout — kept for forward compat per cycle 6
    precedent). The workspace layout is the authoritative one for this regression test.
    """
    candidate = Path(__file__).resolve()
    for ancestor in [candidate, *candidate.parents]:
        spec = ancestor / "specs" / "stakeholder_spec.md"
        if spec.exists():
            return ancestor
        # Repo-layout fallback — accept docs/ if specs/ is absent.
        docs_spec = ancestor / "docs" / "stakeholder_spec.md"
        if docs_spec.exists():
            return ancestor
    raise RuntimeError(
        f"Could not locate project root (specs/stakeholder_spec.md or docs/) from {candidate}"
    )


def _resolve_doc_path(project_root: Path, relative: str) -> Path:
    """Resolve a doc-file relative path against either workspace or repo layout.

    Workspace layout: `specs/stakeholder_spec.md`, `blueprint/blueprint_prose.md`,
    `blueprint/blueprint_contracts.md`.
    Repo layout: all three under `docs/` (flat). Sync mirrors workspace -> repo with
    the path remap. See cycle 6 (S3-158) and cycle 9 (S3-161) precedent for the same
    dual-layout fallback resolver pattern.
    """
    workspace_path = project_root / relative
    if workspace_path.exists():
        return workspace_path
    # Repo-layout fallback — flatten any `specs/` or `blueprint/` prefix into `docs/`.
    filename = Path(relative).name
    repo_path = project_root / "docs" / filename
    if repo_path.exists():
        return repo_path
    return workspace_path  # Will raise on read; caller surfaces the error.


@pytest.fixture(scope="module")
def project_root() -> Path:
    return _find_project_root()


@pytest.fixture(scope="module")
def doc_contents(project_root: Path) -> dict[str, str]:
    """Read every doc file once at module scope for parametrized assertions."""
    contents: dict[str, str] = {}
    for relative in DOC_FILES_RELATIVE:
        path = _resolve_doc_path(project_root, relative)
        if not path.exists():
            raise RuntimeError(f"Doc file missing: {path} (resolved from {relative})")
        contents[relative] = path.read_text(encoding="utf-8")
    return contents


@pytest.mark.parametrize("concept", CONCEPTS)
@pytest.mark.parametrize("doc_relative", DOC_FILES_RELATIVE)
def test_concept_appears_in_all_three_docs(
    concept: str, doc_relative: str, doc_contents: dict[str, str]
) -> None:
    """Each post-S3-153 concept must appear at least once in each primary doc file.

    A failure here means a cycle changed code or contracts but did not port the change
    upstream to the spec's normative sections or to blueprint_prose.md (or, less
    commonly, did not document the concept in blueprint_contracts.md). Per Pattern
    P53, the upstream port is MANDATORY.
    """
    content = doc_contents[doc_relative]
    assert concept in content, (
        f"Concept {concept!r} not found in {doc_relative}. "
        f"This violates Pattern P53 (Porting Modifications Upstream Is Mandatory). "
        f"Add a mention of {concept!r} to {doc_relative} explaining the concept's "
        f"role in the post-S3-153 pipeline. See CLAUDE.md step 2.a (MANDATORY upstream "
        f"port) and references/svp_2_1_lessons_learned.md (P53)."
    )

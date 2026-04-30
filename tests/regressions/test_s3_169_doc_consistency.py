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
    # NEW IN S3-187 (cycle G2 of Gate 6 break-glass inversion sub-project).
    # The three concepts are introduced as authoritative break-glass
    # vocabulary in workspace CLAUDE.md and the child-template
    # CLAUDE_MD_DELIVERED_REPO_TEMPLATE (Unit 29). They MUST also appear in
    # spec normative text (Section 24.201 + cross-refs in §17 / §18.1 /
    # §22.4), in blueprint_prose (Unit 23 narrative for the delivered
    # CLAUDE.md template content), and in blueprint_contracts (Unit 23
    # formal contract clauses). Drift in any of the three docs surfaces
    # here.
    "Layer-Triage",
    "Enhancement Mode",
    "SPEC_AMENDMENT",
    # NEW IN S3-188 (cycle G3 of Gate 6 break-glass inversion sub-project).
    # The two concepts are introduced as authoritative break-glass surface
    # vocabulary in BUG_COMMAND (Unit 25 -- "Scope guard" section) and in
    # generate_write_authorization_sh (Unit 17 -- DEBUG_SESSION_MODE shell
    # variable + enhancement-mode permit branch). They MUST also appear in
    # spec normative text (Section 24.202 + cross-refs in Section 17 /
    # Section 18.1 / Section 19.2), in blueprint_prose (Unit 17 + Unit 23 +
    # Unit 25), and in blueprint_contracts (Unit 17 + Unit 23 + Unit 25).
    # Drift in any of the three docs surfaces here.
    "Scope guard",
    "DEBUG_SESSION_MODE",
    # NEW IN S3-189 (cycle G4 of Gate 6 break-glass inversion sub-project).
    # The generic lessons-learned destination is the canonical replacement
    # for the SVP-self-specific `references/svp_2_1_lessons_learned.md`
    # in the delivered child CLAUDE.md template. The path appears verbatim
    # in spec Section 40.8 + Section 24.203, in blueprint_prose Unit 23
    # (two-template architecture paragraph), and in blueprint_contracts
    # Unit 23 (C-23-G4c MUST-CONTAIN clause). Drift across the three docs
    # surfaces here.
    "references/lessons_learned.md",
    # NEW IN S3-191 (cycle H1 -- R-archetype Stage-5 source copy).
    # The new helper name is the canonical identifier for R-archetype
    # source-copy machinery in `assemble_r_project`. It appears verbatim
    # in spec Section 40.9 + Section 24.205, in blueprint_prose Unit 23
    # (R-archetype source-copy paragraph), and in blueprint_contracts
    # Unit 23 (C-23-H1a MUST clause). Drift across the three docs
    # surfaces here.
    "_copy_r_project_sources",
    # NEW IN S3-192 (cycle H2 -- R-archetype delivery doc generation).
    # The new helper name is the canonical identifier for R-archetype
    # delivery doc generation. It appears verbatim in spec Section 40.10
    # + Section 24.206, in blueprint_prose Unit 23 (R-archetype delivery
    # doc generation paragraph), and in blueprint_contracts Unit 23
    # (C-23-H2a MUST clause). Drift across the three docs surfaces here.
    "generate_r_delivery_docs",
    # NEW IN S3-193 (cycle H3 -- validation list + foundational doc
    # auto-ship). NEWS.md is the R-package convention alternative to
    # CHANGELOG.md. The literal filename appears in spec Section 40.10
    # cross-ref + Section 24.207 + new validation subsection, in
    # blueprint_prose Unit 23 + Unit 28, and in blueprint_contracts Unit
    # 28 (C-28-H3a one-of clause). Drift across the three docs surfaces
    # here.
    "NEWS.md",
    # NEW IN S3-194 (cycle H4 -- assembly map archetype boundary
    # documentation). The literal phrase is the canonical name for the
    # architectural contract that R archetype does NOT produce
    # .svp/assembly_map.json while Python-self-build DOES, and Check 2
    # silently passes when the map is absent. The phrase appears verbatim
    # in spec Section 40.12 + Section 24.208, in blueprint_prose Unit 23 +
    # Unit 28, and in blueprint_contracts Unit 23 (C-23-H4a) + Unit 28
    # (C-28-H4a). Drift across the three docs surfaces here.
    "assembly_map archetype boundary",
    # NEW IN S3-195 (cycle H5 -- CLI completeness). The literal token is the
    # canonical producer-emitted success-line for compliance_scan_main on the
    # no-findings success path. It appears verbatim in spec Section 18.3 +
    # Section 24.209, in blueprint_prose Unit 14 (PHASE_TO_AGENT paragraph
    # cross-reference) + Unit 28 (compliance_scan SUCCEEDED token paragraph),
    # and in blueprint_contracts Unit 28 (C-28-H5a MUST clause). Drift across
    # the three docs surfaces here.
    "COMPLIANCE_SCAN_SUCCEEDED",
    # NEW IN S3-196 (cycle H6 -- test-execution determinism). The literal
    # env-variable name is the canonical UTF-8 hygiene marker for
    # run_tests_main subprocess invocation (Bug R1 #8). It appears verbatim
    # in spec Section 18.3 + Section 24.210, in blueprint_prose Unit 14
    # (test-execution determinism paragraph), and in blueprint_contracts
    # Unit 14 (C-14-H6b MUST clause). Drift across the three docs surfaces
    # here.
    "PYTHONIOENCODING",
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

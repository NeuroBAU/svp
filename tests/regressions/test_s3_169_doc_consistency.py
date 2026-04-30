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
    # NEW IN S3-197 (cycle H7 -- stub generator robustness). The canonical
    # preamble line for Bug R1 #7 in _generate_python_stub: every Python stub
    # MUST emit `from __future__ import annotations` as the first non-blank
    # line, before the stub sentinel, so annotations like Any/OpenAI become
    # strings (no NameError at conftest exec for sub-units of shared modules
    # with Tier-2-signature-only blueprints, no upstream imports). The
    # literal string appears verbatim in spec Section 24.211 + the new stub
    # preamble normative subsection, in blueprint_prose Unit 10 (preamble
    # emission paragraph), and in blueprint_contracts Unit 10 (C-10-H7a
    # MUST-EMIT clause). Drift across the three docs surfaces here.
    "from __future__ import annotations",
    # NEW IN S3-199 (cycle I-2 -- CLAUDE_MD_TEMPLATE Tier-1 forward-port).
    # The literal constant name is the canonical identifier for the Tier-1
    # CLAUDE.md template (used for Stage-0 scaffolding of fresh A-D
    # archetype workspaces). Audit B Candidate 5 found Tier-1 stuck on the
    # OLD break-glass header while Tier-2 had been updated by G2 / S3-187;
    # I-2 forward-ports Tier-1 verbatim from Tier-2 and adds an alignment
    # regression test (Pattern P83). The literal string appears verbatim
    # in spec Section 24.213 + the new alignment normative subsection, in
    # blueprint_prose Unit 29 (alignment paragraph), and in
    # blueprint_contracts Unit 29 (C-29-I2a MUST clause). Drift across the
    # three docs surfaces here.
    "CLAUDE_MD_TEMPLATE",
    # NEW IN S3-200 (cycle I-3 / FINAL -- cp1252 subprocess sweep across
    # Units 4, 11, 15). The two literal function names below are the
    # discriminating identifiers for the I-3 audit-and-broaden cycle. The
    # `verify_toolchain_ready` token (already pinned by S3-160 in the
    # CONCEPTS list above) is now also enforced by the I-3 contract
    # C-4-I3a; `_run_command` is newly pinned. Both names appear verbatim
    # in spec Section 24.214 + Section 18.3 cp1252-sweep extension paragraph,
    # in blueprint_prose Units 4 + 11 + 15 (subprocess UTF-8 hygiene
    # paragraphs), and in blueprint_contracts Units 4 + 11 + 15 (C-4-I3a +
    # C-11-I3a..d + C-15-I3a clauses). The literal env-variable name
    # `PYTHONIOENCODING` already pinned by S3-196 / H6 continues to appear
    # in the broadened §18.3 paragraph and in Section 24.214. Drift across
    # the three docs surfaces here.
    "_run_command",
    # NEW IN S3-201 (cycle J-1 -- post-closure WGCNA-discovered bug fixes).
    # Two anchors lock the J-1 spec/blueprint/contracts cross-references.
    # The literal filename `setup_dialog.jsonl` MUST appear in spec section
    # 3.2 ledger-injection footnote, in blueprint_prose Unit 13 setup_agent
    # ledger-injection paragraph, and in blueprint_contracts Unit 13 C-13-J1a
    # clause. Drift across the three docs surfaces here.
    "setup_dialog.jsonl",
    # The literal em-dash-bearing prefix `None (stdlib only -- ` is the
    # discriminating identifier for the elaborated-sentinel form that the
    # J-1b fix recognizes. Em-dash (`--` rendered) anchor specifically.
    # MUST appear in spec section 17 dep-extraction sentinel-tolerance
    # closing sentence + Section 24.215, in blueprint_prose Unit 11
    # sentinel-elaboration paragraph, and in blueprint_contracts Unit 11
    # C-11-J1a clause. Drift across the three docs surfaces here.
    "None (stdlib only -- ",
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

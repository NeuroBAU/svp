# Project Context: SVP 2.2

## Project Name

SVP 2.2 (Stratified Verification Pipeline, version 2.2)

## Domain

Software development tooling. SVP is a deterministically orchestrated, sequentially gated development pipeline in which a domain expert authors software requirements in natural language and LLM agents generate, verify, and deliver a working Python project. SVP 2.2 is built using SVP 2.1, continuing the self-hosting build chain:

```
SVP 1.2.1  -->  SVP 2.0  -->  SVP 2.1  -->  SVP 2.2
```

## Problem Statement

SVP 2.1 verifies that individual units work (Stage 3), that units integrate correctly (Stage 4), and that the assembled project is structurally well-formed (Stage 5). It has no mechanism to verify that the delivered pipeline actually functions as a pipeline from a user's perspective -- that a new project can be driven through all stages to a correct delivery.

This gap means the following failure classes are undetectable by existing verification:

- A broken routing path that no unit test covers.
- An unreachable gate caused by a dispatch gap that structural tests miss.
- A malformed agent prompt that only manifests during live orchestration.

These are integration failures at the product level, not the code level. Unit testing and structural completeness checks cannot catch them. End-to-end execution with a known project is the only viable verification method.

## New Feature: Pipeline Acceptance Testing

SVP 2.2 introduces a two-pass acceptance testing framework that runs after Stage 5 delivery. It does not replace or modify any existing stage (0-5) or the debug workflow (Stage 6). It is a new post-delivery phase.

### Pass 1 -- Observational (Red Run)

An oracle agent drives the delivered SVP pipeline end-to-end using a known test project. The oracle agent follows a known-good script to supply inputs at each gate and decision point (requirements, dialog answers, gate approvals). At each step it classifies pipeline behavior as one of:

- **Root cause** -- independently wrong, not explained by an earlier issue.
- **Possibly downstream** -- may be caused by an earlier failure (cascade noise).
- **Clean** -- correct behavior.

The oracle agent logs all observations without applying any fixes. The output is a structured diagnostic map of the full pipeline execution.

### Checkpoint -- Human Consultation

The diagnostic map is presented to the human. The human and oracle agent together:

- Separate real bugs from cascade noise.
- Identify whether issues are spec ambiguities or implementation bugs.
- Prioritize fixes.

### Pass 2 -- Targeted Fixes (Green Run)

Fixes are applied starting from the earliest root cause. After each fix, the pipeline is re-run from that stage forward (not from the beginning). Each re-run either clears downstream issues (confirming they were cascade) or surfaces independent bugs requiring further attention.

### Test Projects

The acceptance framework supports multiple test projects:

- **SVP self-build (primary):** SVP 2.2 rebuilds SVP using itself. If the result passes SVP's own regression tests, this constitutes the strongest possible validation -- the system can reproduce itself.
- **Game of Life (smoke test):** A simple, well-understood project used for quick validation of basic pipeline function.
- **Custom projects:** The framework is open to additional test projects designed to exercise specific pipeline paths.

## Technical Context

- Language and toolchain: Python, pytest, ruff, mypy, conda, git. Identical to SVP 2.1.
- Delivery format: Claude Code plugin. Identical to SVP 2.1.
- The new feature adds new agents, new orchestration logic, new pipeline state, and new skills.
- No existing stage (0-5) or debug workflow (Stage 6) is modified.

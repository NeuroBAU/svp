# SVP — Product Roadmap

**Date:** 2026-03-12
**Status:** Strategic plan. Not a specification.

---

## 1. Product Line Status

SVP 2.1 is the terminal release of the SVP product line. The pipeline
architecture — six stages, deterministic gating, four-layer orchestration,
fix ladders, quality gates, state machine, 24-unit structure — is complete.
No further SVP releases are planned.

The build chain:

```
SVP 1.0    first working prototype
SVP 1.1    hardening (5 blueprint-era fixes)
SVP 1.2    post-delivery debug loop, regression tests (Bugs 2-10)
SVP 2.0    project profile, toolchain abstraction, pipeline/delivery split
SVP 2.1    quality gates, delivered quality config, changelog (Bugs 11-12, 26-30)
           ── terminal release ──
```

---

## 2. Immediate Next Step: Language-Directed Variants

The next development phase produces language-targeted products, each
built by SVP 2.1 as a Python project:

```
SVP 2.1  ──builds──>  SVP-R       (R projects: renv, testthat, roxygen2)
SVP 2.1  ──builds──>  SVP-elisp   (Emacs Lisp: Cask, ERT)
SVP 2.1  ──builds──>  SVP-bash    (bash scripts: shunit2 or bats)
```

### 2.1 What Each Variant Shares with SVP

- The six-stage pipeline structure.
- The four-layer orchestration constraint architecture.
- The state machine, routing script, deterministic gating.
- The fix ladders and three-hypothesis diagnostic discipline.
- The ledger-based interaction patterns.
- The hint forwarding mechanism.
- The universal write authorization system.
- The session cycling mechanism.
- The project profile and setup dialog.
- The quality gate mechanism (adapted for language-specific tools).
- The 24-unit decomposition pattern.

### 2.2 What Each Variant Implements Differently

- **Signature parser:** SVP uses Python `ast`. SVP-R would parse R
  function signatures. SVP-elisp would parse defun forms.
- **Stub generator:** Language-specific stub bodies. R: `stop("Not implemented")`.
  Elisp: `(error "Not implemented")`.
- **Test framework integration:** SVP uses pytest. SVP-R: testthat.
  SVP-elisp: ERT. SVP-bash: bats or shunit2.
- **Test output parsing:** Each framework has different pass/fail/error
  output formats. Collection error indicators are language-specific.
- **Environment management:** SVP uses Conda. SVP-R: renv.
  SVP-elisp: Cask. SVP-bash: system packages or Nix.
- **Agent prompts:** "Generate a pytest test suite" → "Generate a
  testthat test suite." Language-specific idioms in system prompts.
- **Quality tools:** SVP uses ruff + mypy. SVP-R: lintr + styler.
  SVP-elisp: checkdoc + byte-compile. SVP-bash: shellcheck.
- **Package format:** SVP uses setuptools. SVP-R: DESCRIPTION file.
  SVP-elisp: Cask/MELPA. SVP-bash: Makefile.

### 2.3 Build Order

SVP-R first. Reasons:

1. R has the strongest test framework ecosystem among the targets
   (testthat is mature, well-documented, widely used).
2. The R user base (academic researchers, data scientists) closely
   matches SVP's target user profile (domain experts who can't code).
3. renv provides environment reproducibility comparable to Conda.
4. The stakeholder spec for SVP-R can be written with direct reference
   to SVP's own spec — the structure is analogous.

SVP-elisp and SVP-bash follow independently, in parallel if desired.

### 2.4 What SVP-R Does NOT Require from SVP

No changes to SVP 2.1. SVP-R is a Python project that SVP 2.1 builds
using its standard pipeline. The fact that SVP-R's *purpose* is to
manage R projects does not affect how SVP 2.1 builds it — SVP 2.1
sees Python source code, Python tests, and Python implementations.

The `toolchain.json` for SVP-R's own build is `python_conda_pytest`
(SVP's pipeline toolchain). The `toolchain.json` that SVP-R *contains*
for its users' projects would reference R-specific tools — but that's
a data file within SVP-R's source code, not a pipeline configuration.

---

## 3. Deferred Delivery Features

The following delivery features were evaluated for SVP 2.1 and deferred.
They are documented here for reference. If any are implemented, they
would be features of a language-directed variant, not of SVP itself.

### 3.1 CI/CD Templates
Generate GitHub Actions or GitLab CI workflows. Medium complexity —
many conditional branches based on language, test framework, and
environment manager. Better implemented per-variant where the CI
template can be language-specific.

### 3.2 Pre-commit Hook Configuration
Generate `.pre-commit-config.yaml`. Low complexity but depends on
quality tool choices. Natural fit as a variant-specific feature.

### 3.3 Docker/Containerization
Generate Dockerfile and docker-compose.yml. Medium complexity.
Language-specific (R Docker images differ from Python images).

### 3.4 Documentation Site Scaffolding
Sphinx/MkDocs for Python, pkgdown for R, etc. Medium-high complexity.
Inherently language-specific.

### 3.5 Code of Conduct
Contributor Covenant template. Low complexity. Language-agnostic —
could be added to any variant.

### 3.6 Security Policy
SECURITY.md template. Low complexity. Language-agnostic.

### 3.7 Issue and PR Templates
GitHub .github/ templates. Low complexity. Language-agnostic.

### 3.8 Editor Configuration
.editorconfig, .vscode/settings.json. Low complexity. Partially
language-specific (indentation conventions vary by language).

### 3.9 Versioning Automation
bump2version, semantic-release. Low complexity. Language-specific
(R uses DESCRIPTION version field, not pyproject.toml).

### 3.10 README Badges
Shield.io badges. Low complexity. Depends on CI provider.

### 3.11 Environment Variable Management
.env.example, python-dotenv. Python-specific as written.

### 3.12 Data Directory Conventions
data/raw/, data/processed/, notebooks/. Relevant for data science
projects in any language.

### 3.13 Experiment Tracking
MLflow, Weights & Biases, DVC. Primarily Python/R ecosystem.

### 3.14 py.typed / Type Stub Marker
PEP 561 compliance. Python-specific.

### 3.15 Makefile / Task Runner
Convenience commands. Language-specific conventions.

### 3.16 Citation File Expansion
Enhanced CITATION.cff. Language-agnostic.

---

## 4. Long-Term Architectural Evolution

These directions would require a new major version — a fundamental
change to the pipeline architecture. They are not planned for any
current development timeline.

### 4.1 Multi-Model Test Authoring

Use a different frontier model (not Claude) to write tests while
Claude writes implementations. This would break correlated interpretation
bias at the model level rather than relying solely on procedural
separation (agent isolation, no shared context).

**Architectural impact:** The agent invocation system currently assumes
a single model provider (Anthropic). Multi-model testing would require:
- A model-agnostic agent invocation layer.
- API adapter for the second model provider.
- Handling of different prompt formats and capabilities.
- A mechanism for model-specific system prompts.

**Prerequisite:** Operational experience with at least two language-
directed variants. The complexity of the multi-model change should be
informed by real pipeline usage, not theoretical design.

### 4.2 Model Evolution Adaptation

Re-implementing pipeline components as models improve. Larger context
windows → coarser unit granularity. Better instruction following →
tighter agent constraints. New capabilities → different components
become agent-driven vs. deterministic.

### 4.3 Real Data Integration

Supporting human-provided real data as test fixtures (currently only
synthetic data). Would require data management, privacy considerations,
and fixture generation from real samples.

---

## 5. What This Document Is Not

This document is not a specification. It does not define behavioral
requirements. It does not enter the pipeline as `specs/stakeholder.md`.
It is a strategic planning document for the human stakeholder.

Behavioral requirements for SVP 2.1 are in the Stakeholder Specification
v8.0. Behavioral requirements for language-directed variants will be in
their own stakeholder specifications, produced through their own Socratic
dialogs, built by SVP 2.1.

---

*End of product roadmap.*

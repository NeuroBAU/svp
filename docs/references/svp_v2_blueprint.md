# SVP -- Stratified Verification Pipeline

## Technical Blueprint v2.0

**Date:** 2026-03-08
**Decomposes:** Stakeholder Specification v7.0
**Artifact Type:** Claude Code Plugin + Standalone Launcher

---

## Preamble: Architecture Overview

SVP is a Claude Code plugin composed of mixed artifact types. The repository structure is:

```
svp-repo/                      <- repository root
|-- .claude-plugin/
|   +-- marketplace.json          <- marketplace catalog (repo root level)
|-- svp/                       <- plugin subdirectory
|   |-- .claude-plugin/
|   |   +-- plugin.json           <- plugin manifest
|   |-- skills/
|   |   +-- orchestration/
|   |       +-- SKILL.md          <- Unit 21
|   |-- agents/
|   |   |-- setup_agent.md               <- Unit 13
|   |   |-- stakeholder_dialog_agent.md  <- Unit 13
|   |   |-- blueprint_author_agent.md    <- Unit 13
|   |   |-- stakeholder_reviewer.md      <- Unit 14
|   |   |-- blueprint_checker.md         <- Unit 14
|   |   |-- blueprint_reviewer.md        <- Unit 14
|   |   |-- test_agent.md                <- Unit 15
|   |   |-- implementation_agent.md      <- Unit 15
|   |   |-- coverage_review_agent.md     <- Unit 15
|   |   |-- diagnostic_agent.md          <- Unit 16
|   |   |-- redo_agent.md                <- Unit 16
|   |   |-- help_agent.md                <- Unit 17
|   |   |-- hint_agent.md                <- Unit 17
|   |   |-- reference_indexing_agent.md  <- Unit 18
|   |   |-- integration_test_author.md   <- Unit 18
|   |   |-- git_repo_agent.md            <- Unit 18
|   |   |-- bug_triage_agent.md          <- Unit 19
|   |   +-- repair_agent.md              <- Unit 19
|   |-- commands/
|   |   |-- save.md                      <- Unit 20
|   |   |-- quit.md                      <- Unit 20
|   |   |-- help.md                      <- Unit 20
|   |   |-- hint.md                      <- Unit 20
|   |   |-- status.md                    <- Unit 20
|   |   |-- ref.md                       <- Unit 20
|   |   |-- redo.md                      <- Unit 20
|   |   |-- bug.md                       <- Unit 20
|   |   +-- clean.md                     <- Unit 20
|   |-- hooks/
|   |   |-- hooks.json                   <- Unit 12
|   |   +-- scripts/
|   |       |-- write_authorization.sh   <- Unit 12
|   |       +-- non_svp_protection.sh    <- Unit 12
|   |-- scripts/
|   |   |-- svp_config.py                <- Unit 1
|   |   |-- pipeline_state.py            <- Unit 2
|   |   |-- state_transitions.py         <- Unit 3
|   |   |-- ledger_manager.py            <- Unit 4
|   |   |-- blueprint_extractor.py       <- Unit 5
|   |   |-- stub_generator.py            <- Unit 6 (library)
|   |   |-- generate_stubs.py            <- Unit 6 (CLI wrapper)
|   |   |-- dependency_extractor.py      <- Unit 7 (library)
|   |   |-- setup_infrastructure.py      <- Unit 7 (CLI wrapper)
|   |   |-- hint_assembler.py            <- Unit 8
|   |   |-- prepare_task.py              <- Unit 9
|   |   |-- routing.py                   <- Unit 10
|   |   |-- update_state.py              <- Unit 10 (CLI wrapper)
|   |   |-- run_tests.py                 <- Unit 10 (CLI wrapper)
|   |   |-- compliance_scan.py           <- Unit 23 (CLI wrapper)
|   |   |-- cmd_save.py                  <- Unit 11
|   |   |-- cmd_quit.py                  <- Unit 11
|   |   |-- cmd_status.py                <- Unit 11
|   |   |-- cmd_clean.py                 <- Unit 11
|   |   |-- svp_launcher.py              <- Unit 24
|   |   |-- toolchain_defaults/          <- Unit 22
|   |   |   +-- python_conda_pytest.json
|   |   +-- templates/                   <- Unit 22
|   |       |-- claude_md.py
|   |       |-- svp_config_default.json
|   |       |-- pipeline_state_initial.json
|   |       +-- readme_svp.txt
|   +-- README.md
|-- tests/
|   +-- regressions/              <- carry-forward regression tests (copied by launcher)
|       |-- test_bug2_wrapper_delegation.py
|       |-- test_bug3_cli_argument_contracts.py
|       |-- test_bug4_status_line_contracts.py
|       |-- test_bug5_pytest_framework_deps.py
|       |-- test_bug6_collection_error_classification.py
|       |-- test_bug7_unit_completion_status_file.py
|       |-- test_bug8_sub_stage_reset_on_completion.py
|       +-- test_bug9_hook_path_resolution.py
|-- examples/                    <- Bundled example (SVP self-build only)
|   +-- game-of-life/            <- Unit 22
|       |-- stakeholder_spec.md
|       |-- blueprint.md
|       +-- project_context.md
|-- src/                          <- SVP Python source code
+-- tests/                        <- SVP test suite
```

**Critical structural rules (learned from SVP 1.1 implementation):**
- All plugin component directories (`agents/`, `commands/`, `skills/`, `hooks/`, `scripts/`) must be at the `svp/` subdirectory root -- not at the repository root, and not nested inside `.claude-plugin/`.
- `plugin.json` is the only file inside `svp/.claude-plugin/`.
- `marketplace.json` lives in a separate `.claude-plugin/` directory at the **repository root** -- not inside the plugin subdirectory.
- `hooks/hooks.json` within the plugin requires a top-level `"hooks"` wrapper key (see Unit 12).

The SVP launcher (`svp` CLI tool, Unit 24) is distributed at `svp/scripts/svp_launcher.py` in the delivered repository. Although it is not a plugin component (it runs before Claude Code starts), it lives inside the plugin's `scripts/` directory. The `pyproject.toml` entry point references it as `svp.scripts.svp_launcher:main`.

**Critical assembly rule (learned from SVP 1.2 implementation):** During Stage 5 assembly, unit implementations must be relocated from their workspace paths (`src/unit_N/`) to their final paths as shown in this file tree. The file tree annotations (`<- Unit N`) are the authoritative mapping. The workspace `src/unit_N/stub.py` structure is never reproduced in the delivered repository. All imports referencing `src.unit_N` or `stub` must be rewritten to use final module paths -- but scripts delivered to `svp/scripts/` must use **bare imports** (e.g., `from pipeline_state import load_state`), NOT package imports (e.g., `from svp.scripts.pipeline_state import load_state`), because the launcher copies these scripts to project workspaces where they run with `PYTHONPATH=scripts`. The `svp.scripts.X` form is used ONLY in `pyproject.toml` entry points. Every script that is invoked directly via `python scripts/X.py` must include an `if __name__ == "__main__"` guard. See spec Section 12.1.1.

**Scripts synchronization rule:** Six units exist as both a canonical `src/unit_N/stub.py` and a runtime `scripts/` copy: Unit 1 (`svp_config.py`), Unit 2 (`pipeline_state.py`), Unit 4 (`ledger_manager.py`), Unit 5 (`blueprint_extractor.py`), Unit 8 (`hint_prompt_assembler.py`), and Unit 9 (`prepare_task.py`). The `src/unit_N/stub.py` is always canonical; the `scripts/` copy must match. When a canonical stub changes -- especially exported constants like `KNOWN_AGENT_TYPES` or public assembler functions -- the corresponding `scripts/` file must be updated in the same commit. The routing script checks `KNOWN_AGENT_TYPES` between `src/unit_9/stub.py` and `scripts/prepare_task.py` at startup and emits a stderr warning if they diverge.

**CLI wrapper rule (learned from SVP 1.2.1 bug triage):** Four units produce both a library module and one or more CLI wrapper scripts: Unit 6 (`stub_generator.py` + `generate_stubs.py`), Unit 7 (`dependency_extractor.py` + `setup_infrastructure.py`), Unit 10 (`routing.py` + `update_state.py` + `run_tests.py`), Unit 23 (`compliance_scan.py`), and no others. CLI wrapper scripts must be **thin wrappers that delegate to the canonical functions** defined in the library module -- they must NOT reimplement dispatch logic, test execution, or infrastructure orchestration inline. Specifically: `update_state.py` must import and call `update_state_main()` from `routing`; `run_tests.py` must import and call `run_tests_main()` from `routing`; `compliance_scan.py` is a standalone script that delegates to `compliance_scan_main()` defined in Unit 23; `generate_stubs.py` must use `write_stub_file()` and `write_upstream_stubs()` from `stub_generator`; `setup_infrastructure.py` must use `run_infrastructure_setup()` from `dependency_extractor` (which in turn must use the canonical API: `extract_all_imports`, `map_imports_to_packages`, `derive_env_name`, `create_conda_environment`, `validate_imports`, `create_project_directories`). Reimplementing logic in CLI wrappers creates sync drift that is invisible to the scripts synchronization check.

**Cross-unit CLI contract (learned from SVP 1.2.1 bug triage):** Unit 10 (routing script) generates PREPARE and POST command strings that are executed as shell commands. The argument syntax in these commands constitutes a cross-unit contract: the receiving script (Unit 9 for PREPARE, Unit 10's own `update_state_main` for POST) must accept every argument that Unit 10 generates. Specifically, `prepare_task.py` must accept `--output` (override output path), and `update_state.py` must accept `--gate` (gate ID for gate response dispatch). When adding arguments to generated command strings in Unit 10, the receiving script's argparse must be updated in the same commit.

**CLI wrapper status line contract (learned from SVP 1.2.1 bug triage):** CLI wrapper scripts invoked as `run_command` actions must emit status lines from the vocabulary defined in Unit 10's `COMMAND_STATUS_PATTERNS`: `COMMAND_SUCCEEDED` on success, `COMMAND_FAILED: [details]` on failure. Custom status strings (e.g. `INFRASTRUCTURE_SETUP_COMPLETE`) are not recognized by `dispatch_command_status()` and cause a `ValueError`. This applies to `setup_infrastructure.py` (Unit 7), `generate_stubs.py` (Unit 6), and `compliance_scan.py` (Unit 23). Test-runner wrappers (`run_tests.py`) use the `TESTS_PASSED`/`TESTS_FAILED`/`TESTS_ERROR` patterns instead.

**Mixed-artifact unit convention:** Units whose artifact category includes Markdown, JSON, shell scripts, or other non-Python deliverables must produce the complete content of each deliverable file as a Python string constant in their `src/unit_N/stub.py` implementation. The naming convention is `{FILENAME_UPPER}_CONTENT: str` -- for example, `SETUP_AGENT_MD_CONTENT: str` for `agents/setup_agent.md`. The git repo agent extracts these string constants during assembly and writes them as files to the paths specified in the blueprint file tree. Tests verify these string constants contain the required structure and content. This convention ensures non-Python deliverables go through the same test-stub-implement-verify cycle as Python code.

**Claude Code agent definition format:** Agent `.md` files use this structure:
```
---
name: agent_name
model: model-id
tools: [Tool1, Tool2, ...]
---

[Agent behavioral instructions -- the system prompt for this subagent]
```
The YAML frontmatter (between `---` delimiters) specifies the agent's metadata. Everything after the frontmatter is the agent's system prompt, which defines its behavior, constraints, output format, and terminal status lines.

**Claude Code command file format:** Command `.md` files contain the full instructions for what Claude Code should do when the slash command is invoked. They are loaded and executed by the orchestration skill.

**Claude Code skill file format:** `SKILL.md` contains the complete behavioral protocol for the skill, loaded by Claude Code when the skill is activated.

### Dependency Graph

```
Unit 1:  SVP Configuration                               (no deps)
Unit 2:  Pipeline State Schema                            depends on: 1
Unit 3:  State Transition Engine                          depends on: 1, 2
Unit 4:  Ledger Manager                                   depends on: 1
Unit 5:  Blueprint Extractor                              (no deps)
Unit 6:  Stub Generator                                   depends on: 5
Unit 7:  Dependency Extractor and Import Validator         depends on: 1
Unit 8:  Hint Prompt Assembler                            depends on: 1
Unit 9:  Preparation Script                               depends on: 1, 2, 4, 5, 8
Unit 10: Routing Script and Update State                  depends on: 1, 2, 3
Unit 11: Command Logic Scripts                            depends on: 1, 2, 4
Unit 12: Hook Configurations                              depends on: 2
Unit 13: Dialog Agent Definitions                         depends on: 4, 9
Unit 14: Review and Checker Agent Definitions             depends on: 9
Unit 15: Construction Agent Definitions                   depends on: 6, 9
Unit 16: Diagnostic and Classification Agent Definitions  depends on: 9
Unit 17: Support Agent Definitions                        depends on: 9
Unit 18: Utility Agent Definitions                        depends on: 9
Unit 19: Debug Loop Agent Definitions                     depends on: 9
Unit 20: Slash Command Files                              depends on: 10, 11
Unit 21: Orchestration Skill                              depends on: 10
Unit 22: Project Templates                                depends on: 1, 2, 10
Unit 23: Plugin Manifest and Structural Validation         depends on: 1, (all preceding)
Unit 24: SVP Launcher                                     depends on: 12, 22
```

**Changes from v1.0 dependency graph:** Unit 7 now depends on Unit 1 (reads `derive_env_name` and toolchain configuration from Unit 1 instead of implementing env name derivation locally).

### SVP 2.0 Scope

SVP 2.0 adds two capabilities to the complete SVP 1.2 baseline:

1. **Project Profile (`project_profile.json`):** Structured configuration capturing delivery preferences. Produced by expanded setup agent through Socratic dialog. Immutable after Gate 0.3. Changes via `/svp:redo`.
2. **Pipeline Toolchain Abstraction (`toolchain.json`):** Data-driven indirection layer moving hardcoded build commands to a configuration file. Behavioral equivalence required.

SVP 2.0 also carries forward all eight regression tests from SVP 1.2's `tests/regressions/` and all five blueprint-era bug fixes.

---

## Unit Definitions

---

## Unit 1: SVP Configuration

**Artifact category:** Python script

### Tier 1 -- Description

Defines three foundational data contracts and provides functions for loading, validating, and accessing all tunable parameters and tool commands. This unit manages: (1) `svp_config.json` -- the pipeline configuration schema, (2) `project_profile.json` -- the human's delivery preferences, and (3) `toolchain.json` -- the pipeline's build command templates. It also provides the canonical `derive_env_name` function used by all units that need environment name derivation. This is the foundational data contract -- nearly every deterministic component reads configuration, profile, or toolchain data through this unit's interface. Implements spec Sections 6.4 (profile schema), 6.5 (toolchain schema), 14.1 (config), 14.2 (profile), 14.3 (toolchain), and 22.1.

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import json

# ===========================================================================
# Section 1: SVP Configuration (svp_config.json)
# ===========================================================================

DEFAULT_CONFIG: Dict[str, Any] = {
    "iteration_limit": 3,
    "models": {
        "test_agent": "claude-opus-4-6",
        "implementation_agent": "claude-opus-4-6",
        "help_agent": "claude-sonnet-4-6",
        "default": "claude-opus-4-6",
    },
    "context_budget_override": None,
    "context_budget_threshold": 65,
    "compaction_character_threshold": 200,
    "auto_save": True,
    "skip_permissions": True,
}

def load_config(project_root: Path) -> Dict[str, Any]: ...

def validate_config(config: Dict[str, Any]) -> list[str]: ...

def get_model_for_agent(config: Dict[str, Any], agent_role: str) -> str: ...

def get_effective_context_budget(config: Dict[str, Any]) -> int: ...

def write_default_config(project_root: Path) -> Path: ...

# ===========================================================================
# Section 2: Project Profile (project_profile.json)
# ===========================================================================

DEFAULT_PROFILE: Dict[str, Any] = {
    "pipeline_toolchain": "python_conda_pytest",
    "python_version": "3.11",
    "delivery": {
        "environment_recommendation": "conda",
        "dependency_format": "environment.yml",
        "source_layout": "conventional",
        "entry_points": False,
    },
    "vcs": {
        "commit_style": "conventional",
        "commit_template": None,
        "issue_references": False,
        "branch_strategy": "main-only",
        "tagging": "semver",
        "conventions_notes": None,
    },
    "readme": {
        "audience": "domain expert",
        "sections": [
            "Header", "What it does", "Who it's for", "Installation",
            "Configuration", "Usage", "Quick Tutorial", "Examples",
            "Project Structure", "License",
        ],
        "depth": "standard",
        "include_math_notation": False,
        "include_glossary": False,
        "include_data_formats": False,
        "include_code_examples": False,
        "code_example_focus": None,
        "custom_sections": None,
        "docstring_convention": "google",
        "citation_file": False,
        "contributing_guide": False,
    },
    "testing": {
        "coverage_target": None,
        "readable_test_names": True,
        "readme_test_scenarios": False,
    },
    "license": {
        "type": "MIT",
        "holder": "",
        "author": "",
        "year": "",
        "contact": None,
        "spdx_headers": False,
        "additional_metadata": {
            "citation": None,
            "funding": None,
            "acknowledgments": None,
        },
    },
    "fixed": {
        "language": "python",
        "pipeline_environment": "conda",
        "test_framework": "pytest",
        "build_backend": "setuptools",
        "vcs_system": "git",
        "source_layout_during_build": "svp_native",
    },
    "created_at": "",
}

def load_profile(project_root: Path) -> Dict[str, Any]: ...

def validate_profile(profile: Dict[str, Any]) -> list[str]: ...

def get_profile_section(profile: Dict[str, Any], section: str) -> Dict[str, Any]: ...

def detect_profile_contradictions(profile: Dict[str, Any]) -> list[str]: ...

# ===========================================================================
# Section 3: Pipeline Toolchain (toolchain.json)
# ===========================================================================

def load_toolchain(project_root: Path) -> Dict[str, Any]: ...

def validate_toolchain(toolchain: Dict[str, Any]) -> list[str]: ...

def resolve_command(
    toolchain: Dict[str, Any],
    operation: str,
    params: Optional[Dict[str, str]] = None,
) -> str: ...

def resolve_run_prefix(toolchain: Dict[str, Any], env_name: str) -> str: ...

def get_framework_packages(toolchain: Dict[str, Any]) -> List[str]: ...

def get_collection_error_indicators(toolchain: Dict[str, Any]) -> List[str]: ...

def validate_python_version(
    python_version: str, version_constraint: str
) -> bool: ...

# ===========================================================================
# Section 4: Shared Utilities
# ===========================================================================

def derive_env_name(project_name: str) -> str: ...
```

### Tier 2 — Invariants

```python
# Pre-conditions
assert project_root.is_dir(), "Project root must be an existing directory"

# Post-conditions for load_config
assert isinstance(result, dict), "Config must be a dict"
assert "iteration_limit" in result, "Config must contain iteration_limit"
assert "models" in result, "Config must contain models section"
assert result["iteration_limit"] >= 1, "Iteration limit must be at least 1"
assert 0 < result["context_budget_threshold"] <= 100, "Budget threshold must be 1-100"
assert result["compaction_character_threshold"] >= 0, "Compaction threshold must be non-negative"
assert isinstance(result["skip_permissions"], bool), "skip_permissions must be a boolean"

# Post-conditions for load_profile
assert isinstance(result, dict), "Profile must be a dict"
assert "delivery" in result, "Profile must contain delivery section"
assert "vcs" in result, "Profile must contain vcs section"
assert "readme" in result, "Profile must contain readme section"
assert "testing" in result, "Profile must contain testing section"
assert "license" in result, "Profile must contain license section"
assert "fixed" in result, "Profile must contain fixed section"

# Post-conditions for load_toolchain
assert isinstance(result, dict), "Toolchain must be a dict"
assert "environment" in result, "Toolchain must contain environment section"
assert "testing" in result, "Toolchain must contain testing section"
assert "packaging" in result, "Toolchain must contain packaging section"
assert "vcs" in result, "Toolchain must contain vcs section"
assert "language" in result, "Toolchain must contain language section"
assert "file_structure" in result, "Toolchain must contain file_structure section"

# Post-conditions for resolve_command
assert isinstance(result, str), "Resolved command must be a string"
assert "{" not in result, "No unresolved placeholders in resolved command"

# Post-conditions for derive_env_name
assert result == project_name.lower().replace(" ", "_").replace("-", "_"), \
    "Env name must follow the canonical derivation"
assert " " not in result, "Env name must not contain spaces"
assert "-" not in result, "Env name must not contain hyphens"
```

### Tier 3 -- Error Conditions

- `FileNotFoundError`: "Config file not found at {path}" -- when `svp_config.json` does not exist at project root. `load_config` returns defaults when file is absent (no error for missing file on first load).
- `json.JSONDecodeError`: "Config file is not valid JSON" -- when file exists but is malformed.
- `ValueError`: "Invalid config: {details}" -- when `validate_config` finds a structural problem.
- `RuntimeError`: "Project profile not found at {path}. Resume from Stage 0 or run /svp:redo to create it." -- when `load_profile` is called and `project_profile.json` does not exist. This is a project integrity error.
- `RuntimeError`: "Toolchain file not found at {path}. Re-run svp new or reinstall the plugin." -- when `load_toolchain` is called and `toolchain.json` does not exist. This is a project integrity error. No fallback to hardcoded values.
- `json.JSONDecodeError`: "Profile/Toolchain file is not valid JSON" -- when file exists but is malformed.
- `ValueError`: "Invalid profile: {details}" -- when `validate_profile` finds a structural problem.
- `ValueError`: "Invalid toolchain: {details}" -- when `validate_toolchain` finds a structural problem.
- `ValueError`: "Python version {version} does not satisfy constraint {constraint}" -- when `validate_python_version` fails.
- `ValueError`: "Unresolved placeholder in command template: {placeholder}" -- when `resolve_command` encounters a placeholder it cannot resolve.

### Tier 3 -- Behavioral Contracts

**Config loader (unchanged from v1.0):**
- `load_config` returns the merged result of file content over defaults -- missing keys in the file are filled from `DEFAULT_CONFIG`.
- `load_config` on a non-existent file returns a copy of `DEFAULT_CONFIG` without error.
- `validate_config` returns an empty list when config is valid, a list of human-readable error strings for each violation found.
- `get_model_for_agent` returns the agent-specific model if configured, otherwise the `models.default` value.
- `get_effective_context_budget` returns the `context_budget_override` when set and non-null, otherwise computes from the smallest model context window minus 20,000 tokens overhead.
- `write_default_config` writes `DEFAULT_CONFIG` as formatted JSON to `{project_root}/svp_config.json` and returns the path.
- Config changes made by the human take effect on next load -- no caching across invocations.

**Profile loader (NEW):**
- `load_profile` reads `project_profile.json` from `project_root`, validates fields it uses against expected types. Unknown fields are ignored (forward compatibility). Missing fields are filled from `DEFAULT_PROFILE`. Raises `RuntimeError` if the file is missing or fails JSON parsing.
- `validate_profile` checks structural integrity: all required sections present, correct types for each field, `delivery.environment_recommendation` is one of `"conda"`, `"pyenv"`, `"venv"`, `"poetry"`, `"none"`, `delivery.source_layout` is one of `"conventional"`, `"flat"`, `"svp_native"`, `vcs.commit_style` is one of `"conventional"`, `"freeform"`, `"custom"`, `readme.depth` is one of `"minimal"`, `"standard"`, `"comprehensive"`, `testing.coverage_target` is null or integer 0-100. Returns empty list when valid, list of error strings otherwise.
- `get_profile_section` returns a specific top-level section of the profile (e.g., `"delivery"`, `"readme"`, `"vcs"`). Raises `KeyError` if the section does not exist.
- `detect_profile_contradictions` checks for known contradictory combinations (spec Section 6.4): `readme.depth: "minimal"` with more than 5 sections or custom sections; `readme.include_code_examples: true` with `readme.depth: "minimal"`; `delivery.entry_points: true` with no identifiable CLI module; `delivery.source_layout: "flat"` with more than approximately 10 units; `vcs.commit_style: "custom"` with `vcs.commit_template: null`; mismatched delivery environment and dependency format. Returns list of contradiction descriptions.

**Toolchain reader (NEW):**
- `load_toolchain` reads `toolchain.json` from `project_root`. Raises `RuntimeError` if missing or malformed. No fallback to hardcoded values.
- `validate_toolchain` checks structural integrity: all required sections present (`environment`, `testing`, `packaging`, `vcs`, `language`, `file_structure`), required fields within each section, command templates contain only recognized placeholders. Returns empty list when valid.
- `resolve_command` performs single-pass placeholder resolution. First resolves `environment.run_prefix` by substituting `{env_name}`, then substitutes the resolved `run_prefix` value into all templates that reference `{run_prefix}`. Resolves `{python_version}` from the `params` dict. Resolves `{env_name}` from the `params` dict. No recursive or multi-level resolution. Raises `ValueError` if any placeholder remains unresolved after substitution.
- `resolve_run_prefix` is a convenience function: resolves `environment.run_prefix` template with the given `env_name`. Returns the resolved string (e.g., `"conda run -n myproject"`).
- `get_framework_packages` returns `testing.framework_packages` from the toolchain (e.g., `["pytest", "pytest-cov"]`).
- `get_collection_error_indicators` returns `testing.collection_error_indicators` from the toolchain.
- `validate_python_version` checks whether a version string (e.g., `"3.11"`) satisfies the constraint in `language.version_constraint` (e.g., `">=3.10"`). Returns True if satisfied, False otherwise.
- **Behavioral equivalence:** Every resolved command must produce identical behavior to SVP 1.2's hardcoded commands. This is testable: compare fully resolved commands (after placeholder substitution with known test inputs) against the exact strings SVP 1.2 would have produced for the same inputs.

**Shared utilities (NEW -- moved from Unit 7):**
- `derive_env_name` applies the canonical derivation: `project_name.lower().replace(" ", "_").replace("-", "_")`. This is the single canonical implementation used by Units 7, 10, 11, and 24.

### Tier 3 -- Dependencies

None. This is the most foundational unit.

---

## Unit 2: Pipeline State Schema and Core Operations

**Artifact category:** Python script

### Tier 1 -- Description

Defines the complete `pipeline_state.json` schema and provides creation, reading, writing, structural validation, and state recovery from completion markers. This is the single source of truth for deterministic routing, session recovery, and status reporting. Implements spec Sections 14.4 (state), 6.1 (resume/recovery), 14.6 (resume behavior), and 12.1 (redo-triggered profile revision state).

The state schema includes Stage 0 sub-stages (`hook_activation`, `project_context`, `project_profile`), the `debug_session` object for the debug permission reset (Bug 2 fix), and redo-triggered profile revision sub-stages (`redo_profile_delivery`, `redo_profile_blueprint`) with snapshot capture.

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
from datetime import datetime

# --- Data contract: pipeline state schema ---

STAGES: List[str] = ["0", "1", "2", "pre_stage_3", "3", "4", "5"]

SUB_STAGES_STAGE_0: List[str] = ["hook_activation", "project_context", "project_profile"]

# Redo-triggered profile revision sub-stages (can appear in any stage)
REDO_PROFILE_SUB_STAGES: List[str] = ["redo_profile_delivery", "redo_profile_blueprint"]

FIX_LADDER_POSITIONS: List[Optional[str]] = [
    None, "fresh_test", "hint_test",
    "fresh_impl", "diagnostic", "diagnostic_impl",
]

class DebugSession:
    """Debug session state for post-delivery bug investigation."""
    bug_id: int
    description: str
    classification: Optional[str]  # "build_env", "single_unit", "cross_unit"
    affected_units: List[int]
    regression_test_path: Optional[str]
    phase: str  # "triage_readonly", "triage", "regression_test", "stage3_reentry", "repair", "complete"
    authorized: bool  # True after AUTHORIZE DEBUG at Gate 6.0
    created_at: str
    def __init__(self, **kwargs: Any) -> None: ...
    def to_dict(self) -> Dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DebugSession": ...

class PipelineState:
    """Complete pipeline state. This is the schema contract."""
    stage: str                           # "0" through "5", or "pre_stage_3"
    sub_stage: Optional[str]             # stage-specific sub-stage
    current_unit: Optional[int]          # unit number during Stage 3
    total_units: Optional[int]           # total units in blueprint
    fix_ladder_position: Optional[str]   # None, "fresh_test", "hint_test", "fresh_impl", "diagnostic", "diagnostic_impl"
    red_run_retries: int                 # count, reset on unit advance past red run
    alignment_iteration: int             # Stage 2 loop count
    verified_units: List[Dict[str, Any]] # [{unit: int, timestamp: str}, ...]
    pass_history: List[Dict[str, Any]]   # [{pass_number: int, reached_unit: int, ended_reason: str, timestamp: str}, ...]
    log_references: Dict[str, str]       # {rejection_log: path, diagnostic_log: path, ...}
    project_name: Optional[str]
    last_action: Optional[str]           # human-readable description of the last completed action
    debug_session: Optional[DebugSession]  # active debug session or None
    debug_history: List[Dict[str, Any]]  # completed debug session records
    redo_triggered_from: Optional[Dict[str, Any]]  # snapshot of pipeline position at redo trigger (NEW)
    created_at: str                      # ISO timestamp
    updated_at: str                      # ISO timestamp
    def __init__(self, **kwargs: Any) -> None: ...
    def to_dict(self) -> Dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineState": ...

def create_initial_state(project_name: str) -> PipelineState: ...

def load_state(project_root: Path) -> PipelineState: ...

def save_state(state: PipelineState, project_root: Path) -> None: ...

def validate_state(state: PipelineState) -> list[str]: ...

def recover_state_from_markers(project_root: Path) -> Optional[PipelineState]: ...

def get_stage_display(state: PipelineState) -> str: ...
```

### Tier 2 — Invariants

```python
# Pre-conditions
assert project_root.is_dir(), "Project root must exist"

# Post-conditions for create_initial_state
assert result.stage == "0", "Initial state must be Stage 0"
assert result.sub_stage == "hook_activation", "Initial sub-stage must be hook_activation"
assert result.red_run_retries == 0, "Initial red_run_retries must be 0"
assert result.alignment_iteration == 0, "Initial alignment_iteration must be 0"
assert len(result.verified_units) == 0, "No units verified initially"
assert len(result.pass_history) == 0, "No pass history initially"
assert result.debug_session is None, "No debug session initially"
assert result.debug_history == [], "No debug history initially"
assert result.redo_triggered_from is None, "No redo snapshot initially"

# Post-conditions for load_state
assert result.stage in STAGES, "Stage must be a valid stage identifier"
assert result.red_run_retries >= 0, "Red run retries must be non-negative"
assert result.alignment_iteration >= 0, "Alignment iteration must be non-negative"

# Post-conditions for save_state
assert (project_root / "pipeline_state.json").exists(), "State file must exist after save"

# Redo snapshot validation
# When redo_triggered_from is not None, it must contain: stage, sub_stage, current_unit,
# fix_ladder_position, red_run_retries
assert result.redo_triggered_from is None or "stage" in result.redo_triggered_from, \
    "Redo snapshot must contain stage"
```

### Tier 3 -- Error Conditions

- `FileNotFoundError`: "State file not found at {path}" -- when `load_state` is called and `pipeline_state.json` does not exist.
- `json.JSONDecodeError`: "State file is not valid JSON" -- when file is malformed.
- `ValueError`: "Invalid state: {details}" -- when `validate_state` finds structural problems.

### Tier 3 -- Behavioral Contracts

- `create_initial_state` returns a `PipelineState` at `stage: "0"`, `sub_stage: "hook_activation"` with all counters at zero, `debug_session: None`, `debug_history: []`, and `redo_triggered_from: None`.
- `load_state` deserializes `pipeline_state.json` and returns a validated `PipelineState`, including deserialization of the `debug_session` object when present and `redo_triggered_from` snapshot when present.
- `save_state` atomically writes the state (write to temp file, rename) to prevent corruption on interruption.
- `validate_state` checks structural integrity: valid stage, valid sub-stage for the stage (including `project_profile` for Stage 0 and redo profile sub-stages for any stage), non-negative counters, verified_units entries have required fields, pass_history entries have required fields, debug_session is either None or a valid DebugSession, debug_history entries have required fields, redo_triggered_from is either None or a valid snapshot dict with required keys (`stage`, `sub_stage`, `current_unit`, `fix_ladder_position`, `red_run_retries`).
- `recover_state_from_markers` scans for `<!-- SVP_APPROVED: ... -->` in `specs/stakeholder.md` and `blueprint/blueprint.md`, and for files in `.svp/markers/unit_N_verified`. It constructs the most conservative valid state (earliest stage consistent with the markers found).
- `recover_state_from_markers` returns `None` if no markers are found at all.
- `get_stage_display` returns a human-readable string like "Stage 3, Unit 4 of 11 (pass 2)".
- The `updated_at` field is set to current ISO timestamp on every `save_state` call.
- Pass history entries are append-only -- entries are never removed or modified.
- Debug history entries are append-only -- entries are never removed or modified.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** `create_initial_state` may read config for project name context. The dependency is minimal -- the state schema is self-contained.

---

## Unit 3: State Transition Engine

**Artifact category:** Python script

### Tier 1 -- Description

Validates preconditions and executes all state transitions: stage advancement, unit completion, fix ladder progression, pass history recording, unit-level rollback, document versioning (copy to history, write diff summary), debug session lifecycle (enter, authorize, exit), and redo-triggered profile revision lifecycle (enter, snapshot, restore/discard). This unit contains the most complex business logic among the deterministic scripts -- it is the primary stage-gating mechanism. Implements spec Sections 3.6 (state management), 10.10 (unit completion), 13 (`/svp:redo` rollback), 23 (document version tracking), 8.3 (alignment loop iteration tracking), 12.1 (redo profile revision state machine), and 12.9.1 (debug permission reset).

Document versioning (Section 23) is included here because it is always triggered as part of a state transition, never independently.

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from pipeline_state import PipelineState, DebugSession

class TransitionError(Exception):
    """Raised when a state transition's preconditions are not met."""
    ...

def advance_stage(state: PipelineState, project_root: Path) -> PipelineState: ...

def advance_sub_stage(state: PipelineState, sub_stage: str, project_root: Path) -> PipelineState: ...

def complete_unit(state: PipelineState, unit_number: int, project_root: Path) -> PipelineState: ...

def advance_fix_ladder(state: PipelineState, new_position: str) -> PipelineState: ...


def increment_red_run_retries(state: PipelineState) -> PipelineState: ...

def reset_red_run_retries(state: PipelineState) -> PipelineState: ...

def increment_alignment_iteration(state: PipelineState) -> PipelineState: ...



def rollback_to_unit(state: PipelineState, unit_number: int, project_root: Path) -> PipelineState: ...

def restart_from_stage(state: PipelineState, target_stage: str, reason: str, project_root: Path) -> PipelineState: ...

def version_document(
    doc_path: Path, history_dir: Path, diff_summary: str, trigger_context: str
) -> Tuple[Path, Path]: ...

def enter_debug_session(state: PipelineState, bug_description: str) -> PipelineState: ...

def authorize_debug_session(state: PipelineState) -> PipelineState: ...

def complete_debug_session(state: PipelineState, fix_summary: str) -> PipelineState: ...

def abandon_debug_session(state: PipelineState) -> PipelineState: ...

def update_debug_phase(state: PipelineState, phase: str) -> PipelineState: ...

def set_debug_classification(state: PipelineState, classification: str, affected_units: List[int]) -> PipelineState: ...

# --- Redo-triggered profile revision transitions (NEW) ---

def enter_redo_profile_revision(
    state: PipelineState, classification: str
) -> PipelineState: ...

def complete_redo_profile_revision(state: PipelineState) -> PipelineState: ...

```

### Tier 2 — Invariants

```python
# Pre-conditions for complete_unit
assert state.stage == "3", "Can only complete units during Stage 3"
assert state.current_unit == unit_number, "Can only complete the current unit"
assert (project_root / f".svp/markers/unit_{unit_number}_verified").exists() is False, \
    "Completion marker must not already exist"

# Pre-conditions for advance_stage
assert state.stage in ("0", "1", "2", "pre_stage_3", "3", "4"), \
    "Cannot advance past Stage 5"

# Pre-conditions for rollback_to_unit
assert state.stage == "3", "Rollback only applies during Stage 3"
assert unit_number >= 1, "Unit number must be positive"
assert unit_number <= (state.current_unit or 0), "Cannot roll back to a future unit"

# Pre-conditions for enter_debug_session
assert state.stage == "5", "Can only enter debug session after Stage 5 completion"
assert state.debug_session is None, "Cannot enter debug session when one is already active"

# Pre-conditions for authorize_debug_session
assert state.debug_session is not None, "No active debug session to authorize"
assert state.debug_session.authorized is False, "Debug session already authorized"

# Pre-conditions for complete_debug_session
assert state.debug_session is not None, "No active debug session to complete"
assert state.debug_session.authorized is True, "Debug session must be authorized before completion"

# Pre-conditions for enter_redo_profile_revision
assert classification in ("profile_delivery", "profile_blueprint"), \
    "Classification must be profile_delivery or profile_blueprint"
assert state.sub_stage not in ("redo_profile_delivery", "redo_profile_blueprint"), \
    "Cannot enter redo profile revision when one is already active"

# Pre-conditions for complete_redo_profile_revision
assert state.sub_stage in ("redo_profile_delivery", "redo_profile_blueprint"), \
    "Must be in redo profile revision to complete it"
assert state.redo_triggered_from is not None, \
    "Redo snapshot must exist to complete revision"

# Post-conditions for complete_unit
assert (project_root / f".svp/markers/unit_{unit_number}_verified").exists(), \
    "Completion marker must be written"
assert result.current_unit == unit_number + 1 or result.stage != "3", \
    "Must advance to next unit or stage"

# Post-conditions for version_document
assert versioned_copy.exists(), "Versioned copy must exist in history dir"
assert diff_file.exists(), "Diff summary must exist in history dir"

# Post-conditions for authorize_debug_session
assert result.debug_session is not None, "Debug session must still exist"
assert result.debug_session.authorized is True, "Debug session must be authorized"

# Post-conditions for enter_redo_profile_revision
assert result.redo_triggered_from is not None, "Redo snapshot must be captured"
assert result.sub_stage in ("redo_profile_delivery", "redo_profile_blueprint"), \
    "Sub-stage must be set to redo profile revision type"
```

### Tier 3 -- Error Conditions

- `TransitionError`: "Cannot advance from stage {X}: preconditions not met -- {details}" -- when `advance_stage` is called but the stage's exit criteria are not satisfied.
- `TransitionError`: "Cannot complete unit {N}: tests have not passed" -- when `complete_unit` is called without test passage evidence.
- `TransitionError`: "Cannot advance fix ladder to {position}: current position {current} does not permit this transition" -- when the ladder position sequence is violated.
- `TransitionError`: "Alignment iteration limit reached ({limit})" -- when `increment_alignment_iteration` detects the limit is exceeded (reads limit from config via Unit 1).
- `TransitionError`: "Cannot enter debug session: pipeline is not at Stage 5" -- when `enter_debug_session` is called outside Stage 5.
- `TransitionError`: "Cannot enter debug session: a debug session is already active" -- when a second debug session is attempted.
- `TransitionError`: "Cannot authorize debug session: no active session" -- when `authorize_debug_session` is called with no debug session.
- `TransitionError`: "Cannot enter redo profile revision: already in redo profile revision" -- when a second redo profile revision is attempted while one is active.
- `FileNotFoundError`: "Document to version not found: {path}" -- when `version_document` receives a non-existent document path.

### Tier 3 -- Behavioral Contracts

- `advance_stage` moves the state to the next stage in the defined sequence. It validates that the current stage's exit criteria are met before transitioning. The exit criteria for each stage transition are:
  - **Stage 0 to Stage 1:** Gate 0.3 (profile approval) must have passed, and `project_profile.json` must exist in the project root.
  - **Stage 1 to Stage 2:** Gate 1.1 (spec approval) must have passed, and `specs/stakeholder.md` must exist.
  - **Stage 2 to Pre-Stage-3:** Gate 2.1 or Gate 2.2 (blueprint approval) must have passed, and `blueprint/blueprint.md` must exist.
  - **Pre-Stage-3 to Stage 3:** Infrastructure setup must be complete -- conda environment created, and import validation passed.
  - **Stage 3 to Stage 4:** All units must be verified -- all marker files in `.svp/markers/` must exist, and the `verified_units` list must be complete (length equals `total_units`).
  - **Stage 4 to Stage 5:** Integration tests must pass (assembly complete).
- `complete_unit` writes a marker file to `.svp/markers/unit_N_verified` with `VERIFIED: {timestamp}`, updates the `verified_units` list, resets fix ladder, red run retries, and `sub_stage` to `None`, and advances `current_unit`. Resetting `sub_stage` is critical: without it, the next unit inherits the prior unit's `"unit_completion"` sub_stage and routing immediately re-completes the new unit without building it. When `current_unit` exceeds `total_units`, advances stage to "4".
- `rollback_to_unit` invalidates all units from the given unit forward: removes their marker files, removes them from `verified_units`, moves their generated code and tests to `logs/rollback/`, and sets `current_unit` to the given unit number.
- `restart_from_stage` records the current pass in `pass_history` (how far it reached, why it ended), resets stage-specific counters, and sets the state to the target stage.
- `version_document` copies the current document to `history/{name}_v{N}.md`, writes a diff summary to `history/{name}_v{N}_diff.md` containing what changed, why, what stage triggered it, and a timestamp. Returns the paths of both created files.
- `enter_debug_session` creates a new `DebugSession` with `authorized: False`, `phase: "triage_readonly"`, assigns a sequential `bug_id`, and sets it on the state.
- `authorize_debug_session` sets `debug_session.authorized = True` and advances `phase` to `"triage"`. This is the transition that activates debug write permissions in the hook (Unit 12).
- `complete_debug_session` moves the debug session record to `debug_history`, sets `debug_session` to None, and returns the state to "Stage 5 complete".
- `abandon_debug_session` moves the debug session record (with an "abandoned" marker) to `debug_history`, sets `debug_session` to None, and returns the state to "Stage 5 complete".
- `update_debug_phase` validates phase transitions and updates `debug_session.phase`.
- `set_debug_classification` sets the classification and affected units on the debug session.
- `enter_redo_profile_revision` captures the current pipeline position as a snapshot dict in `redo_triggered_from` (including `stage`, `sub_stage`, `current_unit`, `fix_ladder_position`, `red_run_retries`), then sets `sub_stage` to `"redo_profile_delivery"` or `"redo_profile_blueprint"` based on the classification.
- `complete_redo_profile_revision` reads the `redo_triggered_from` snapshot. For `redo_profile_delivery`: restores the snapshot (stage, sub_stage, current_unit, fix_ladder_position, red_run_retries), sets `redo_triggered_from` to None. The delivery change takes effect when Stage 5 runs. For `redo_profile_blueprint`: discards the snapshot, calls `restart_from_stage` to Stage 2 with reason "profile_blueprint revision". Resets everything downstream including fix ladder, red run retries, current unit, and verified units. Sets `redo_triggered_from` to None.
- **[Removed in Bug 54]** `update_state_from_status` was a hollow skeleton that never dispatched. The actual POST command entry point is `update_state_main()` in `routing.py`, which calls `dispatch_status()` directly.
- All transition functions return a new `PipelineState` -- they do not mutate the input. The caller is responsible for saving.
- `advance_fix_ladder` enforces the valid ladder sequence: `None -> fresh_test -> hint_test` (test ladder), `None -> fresh_impl -> diagnostic -> diagnostic_impl` (implementation ladder). Invalid transitions raise `TransitionError`. **Caller responsibility:** callers must check `state.fix_ladder_position` before calling and must pass the next valid target for the current position -- not a fixed target. A `TransitionError` from `advance_fix_ladder` indicates a logic error in the caller (attempting an invalid transition), not a transient condition to be retried or swallowed.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Reads `iteration_limit` for alignment loop cap, reads `auto_save` to determine whether to trigger saves.
- **Unit 2 (Pipeline State Schema):** Uses `PipelineState` and `DebugSession` classes for all state operations. Uses `save_state` after transitions. Uses `validate_state` as a post-transition check.

---

## Unit 4: Ledger Manager

**Artifact category:** Python script

### Tier 1 -- Description

Manages JSONL conversation ledgers: append entries, read full ledger, compact, clear, and monitor size. Implements the compaction algorithm from spec Section 3.3 and the structured response format validation from spec Section 15.1. Also writes system-level `[HINT]` entries per Section 15.1. Unchanged from v1.0.

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime
import json

# --- Data contract: ledger entry schema ---

class LedgerEntry:
    role: str           # "agent", "human", "system"
    content: str
    timestamp: str      # ISO format
    metadata: Optional[Dict[str, Any]]  # e.g., gate info for [HINT] entries
    def __init__(self, role: str, content: str, timestamp: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> None: ...
    def to_dict(self) -> Dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LedgerEntry": ...

def append_entry(ledger_path: Path, entry: LedgerEntry) -> None: ...

def read_ledger(ledger_path: Path) -> List[LedgerEntry]: ...

def clear_ledger(ledger_path: Path) -> None: ...

def rename_ledger(ledger_path: Path, new_name: str) -> Path: ...

def get_ledger_size_chars(ledger_path: Path) -> int: ...

def check_ledger_capacity(
    ledger_path: Path, max_chars: int
) -> Tuple[float, Optional[str]]: ...

def compact_ledger(ledger_path: Path, character_threshold: int = 200) -> int: ...

def write_hint_entry(
    ledger_path: Path,
    hint_content: str,
    gate_id: str,
    unit_number: Optional[int],
    stage: str,
    decision: str,
) -> None: ...

def extract_tagged_lines(content: str) -> List[Tuple[str, str]]: ...
```

### Tier 2 — Invariants

```python
# Pre-conditions
assert ledger_path.suffix == ".jsonl", "Ledger files must use .jsonl extension"

# Post-conditions for append_entry
assert ledger_path.exists(), "Ledger file must exist after append"

# Post-conditions for compact_ledger
assert result >= 0, "Compaction must report non-negative bytes saved"

# Post-conditions for read_ledger
assert all(isinstance(e, LedgerEntry) for e in result), "All entries must be LedgerEntry instances"
```

### Tier 3 -- Error Conditions

- `FileNotFoundError`: "Ledger file not found: {path}" -- when `read_ledger` or `compact_ledger` is called on a non-existent file.
- `json.JSONDecodeError`: "Malformed JSONL entry at line {N}" -- when a ledger entry is not valid JSON.
- `ValueError`: "Invalid ledger entry: missing required field '{field}'" -- when a deserialized entry lacks role, content, or timestamp.

### Tier 3 -- Behavioral Contracts

- `append_entry` appends a single JSONL line to the ledger file. Creates the file if it does not exist. Writes atomically (append mode).
- `read_ledger` reads all entries from a JSONL file and returns them as `LedgerEntry` instances in order. Returns an empty list for a non-existent or empty file.
- `clear_ledger` truncates the ledger file to zero bytes. The file continues to exist.
- `rename_ledger` renames the ledger file (e.g., for abandoned debug sessions: `bug_triage_N.jsonl` to `bug_triage_N_abandoned.jsonl`). Returns the new path.
- `get_ledger_size_chars` returns the total character count of the ledger file.
- `check_ledger_capacity` returns a tuple of (usage fraction 0.0-1.0, warning message or None). Warning at 80%, required action at 90%.
- `compact_ledger` implements the compaction algorithm: identifies sequences where agent bodies led to a `[DECISION]` or `[CONFIRMED]` closing. For tagged lines above `character_threshold` characters, the body is deleted (the tagged line is presumed self-contained). For tagged lines at or below the threshold, the body is preserved. `[HINT]` entries are always preserved verbatim. Returns the number of characters saved.
- `write_hint_entry` creates a system-level `[HINT]` entry with full gate metadata and appends it to the ledger. The entry includes gate_id, unit_number, stage, and decision.
- `extract_tagged_lines` parses content for `[QUESTION]`, `[DECISION]`, and `[CONFIRMED]` markers and returns a list of (marker, full_line) tuples.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Reads `compaction_character_threshold` for the compaction algorithm.

---

## Unit 5: Blueprint Extractor

**Artifact category:** Python script

### Tier 1 -- Description

Extracts a single unit's definition and upstream contract signatures from the full blueprint for context-isolated agent invocations. The extracted content becomes part of the task prompt for the relevant subagent. This is a deterministic operation -- no LLM involvement. Implements spec Section 10.11. Unchanged from v1.0.

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any, List
from pathlib import Path

class UnitDefinition:
    """A single unit's complete definition extracted from the blueprint."""
    unit_number: int
    unit_name: str
    description: str          # Tier 1
    signatures: str           # Tier 2 code block (raw Python)
    invariants: str           # Tier 2 invariants code block
    error_conditions: str     # Tier 3
    behavioral_contracts: str # Tier 3
    dependencies: List[int]   # upstream unit numbers
    def __init__(self, **kwargs: Any) -> None: ...

def parse_blueprint(blueprint_path: Path) -> List[UnitDefinition]: ...

def extract_unit(blueprint_path: Path, unit_number: int) -> UnitDefinition: ...

def extract_upstream_contracts(
    blueprint_path: Path, unit_number: int
) -> List[Dict[str, str]]: ...

def build_unit_context(
    blueprint_path: Path, unit_number: int
) -> str: ...
```

### Tier 2 — Invariants

```python
# Pre-conditions
assert blueprint_path.exists(), "Blueprint file must exist"
assert unit_number >= 1, "Unit number must be positive"

# Post-conditions for parse_blueprint
assert len(result) > 0, "Blueprint must contain at least one unit"
assert all(u.unit_number > 0 for u in result), "All unit numbers must be positive"

# Post-conditions for extract_unit
assert result.unit_number == unit_number, "Extracted unit number must match request"
assert len(result.signatures) > 0, "Unit must have non-empty signatures"

# Post-conditions for build_unit_context
assert len(result) > 0, "Unit context must be non-empty"
```

### Tier 3 -- Error Conditions

- `FileNotFoundError`: "Blueprint file not found: {path}" -- when the blueprint file does not exist.
- `ValueError`: "Unit {N} not found in blueprint" -- when the requested unit number is not defined.
- `ValueError`: "Blueprint has no parseable unit definitions" -- when the blueprint contains no recognizable `## Unit N` headings.

### Tier 3 -- Behavioral Contracts

- `parse_blueprint` reads the full blueprint and parses all unit definitions into `UnitDefinition` instances. Splits on `## Unit N:` heading patterns.
- `extract_unit` returns a single unit's definition. Delegates to `parse_blueprint` internally.
- `extract_upstream_contracts` returns the Tier 2 signatures for all units listed in the requested unit's dependencies. Each entry is a dict with `unit_number`, `unit_name`, and `signatures` keys.
- `build_unit_context` produces a formatted string containing the unit's full definition followed by all upstream contract signatures, ready for inclusion in a task prompt.
- Parsing is based on Markdown heading structure (`## Unit N:` pattern) and sub-heading patterns (`### Tier 1`, `### Tier 2`, `### Tier 3`). The Tier 2 heading format is `### Tier 2 — Signatures` (em-dash, not hyphen).

### Tier 3 -- Dependencies

None. This unit operates on the blueprint file directly with no upstream unit dependencies.

---

## Unit 6: Stub Generator

**Artifact category:** Python script (library + CLI wrapper)

### Tier 1 -- Description

Parses machine-readable signatures from the blueprint using Python's `ast` module and produces Python stub files with `NotImplementedError` bodies. Also generates stubs or mocks for upstream dependencies based on their contract signatures. Implements spec Section 10.2, including the importability invariant (module-level `assert` statements are stripped). Unchanged from v1.0.

### Tier 2 — Signatures

```python
import ast
from typing import Optional, Dict, Any, List
from pathlib import Path

def parse_signatures(signature_block: str) -> ast.Module: ...

def generate_stub_source(parsed_ast: ast.Module) -> str: ...

def strip_module_level_asserts(tree: ast.Module) -> ast.Module: ...

def generate_upstream_mocks(
    upstream_contracts: List[Dict[str, str]]
) -> Dict[str, str]: ...

def write_stub_file(
    unit_number: int,
    signature_block: str,
    output_dir: Path,
) -> Path: ...

def write_upstream_stubs(
    upstream_contracts: List[Dict[str, str]],
    output_dir: Path,
) -> List[Path]: ...

# CLI wrapper (generate_stubs.py)
def main() -> None: ...
```

### Tier 2 — Invariants

```python
# Pre-conditions
assert len(signature_block.strip()) > 0, "Signature block must not be empty"

# Post-conditions for parse_signatures
assert isinstance(result, ast.Module), "Parse result must be an ast.Module"

# Post-conditions for generate_stub_source
assert "NotImplementedError" in result, "Stub source must contain NotImplementedError"
assert "assert" not in result.split("def ")[0] if "def " in result else True, \
    "No module-level asserts in stub"

# Post-conditions for write_stub_file
assert result.exists(), "Stub file must exist after write"
assert result.suffix == ".py", "Stub file must be a Python file"
```

### Tier 3 -- Error Conditions

- `SyntaxError`: "Blueprint signature block is not valid Python: {details}" -- when `ast.parse()` fails on the signature block. This is a blueprint format problem.
- `FileNotFoundError`: "Output directory does not exist: {path}" -- when the output directory is missing.

### Tier 3 -- Behavioral Contracts

- `parse_signatures` calls `ast.parse()` on the signature block and returns the AST. Raises `SyntaxError` if the block is not valid Python.
- `generate_stub_source` transforms the AST: replaces all function bodies with `raise NotImplementedError()`, preserves import statements and class definitions, strips module-level `assert` statements (importability invariant).
- `strip_module_level_asserts` removes all `ast.Assert` nodes at the module level of the AST. Does not affect asserts inside function or class bodies.
- `generate_upstream_mocks` produces mock module source code for each upstream dependency, based on their contract signatures.
- `write_stub_file` combines `parse_signatures`, `strip_module_level_asserts`, and `generate_stub_source` to produce a stub file at `{output_dir}/stub.py`.
- `write_upstream_stubs` generates and writes mock files for all upstream dependencies.
- The generated stub must be importable without error (the importability invariant).
- The CLI wrapper `main()` is invoked as a `run_command` action and must emit `COMMAND_SUCCEEDED` on success or `COMMAND_FAILED: [details]` on failure as its terminal status line. These status lines must match Unit 10's `COMMAND_STATUS_PATTERNS` vocabulary.

### Tier 3 -- Dependencies

- **Unit 5 (Blueprint Extractor):** Uses `extract_upstream_contracts` to obtain upstream contract signatures for mock generation. The CLI wrapper uses `extract_unit` for the current unit's signatures.

---

## Unit 7: Dependency Extractor and Import Validator

**Artifact category:** Python script (library + CLI wrapper)

### Tier 1 -- Description

Scans all machine-readable signature blocks across all units in the blessed blueprint, extracts every external import statement, produces a complete dependency list, creates the Conda environment, installs all packages, and validates that every extracted import resolves. Tool commands are read from `toolchain.json` via Unit 1's toolchain reader instead of being hardcoded. Implements spec Sections 8 (Pre-Stage-3 Infrastructure Setup) and 9.

### Tier 2 — Signatures

```python
import ast
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

def extract_all_imports(blueprint_path: Path) -> List[str]: ...

def classify_import(import_stmt: str) -> str: ...

def map_imports_to_packages(imports: List[str]) -> Dict[str, str]: ...

def create_conda_environment(
    env_name: str,
    packages: Dict[str, str],
    python_version: str = "3.11",
    toolchain: Optional[Dict[str, Any]] = None,
) -> bool: ...

def validate_imports(
    env_name: str,
    imports: List[str],
    toolchain: Optional[Dict[str, Any]] = None,
) -> List[Tuple[str, str]]: ...

def create_project_directories(
    project_root: Path, total_units: int
) -> None: ...

def run_infrastructure_setup(
    project_root: Path,
    toolchain: Optional[Dict[str, Any]] = None,
) -> None: ...

# CLI wrapper (setup_infrastructure.py)
def main() -> None: ...
```

### Tier 2 — Invariants

```python
# Pre-conditions
assert blueprint_path.exists(), "Blueprint file must exist"

# Post-conditions for extract_all_imports
assert all(isinstance(s, str) for s in result), "All imports must be strings"

# Post-conditions for derive_env_name (now in Unit 1)
# Unit 7 calls svp_config.derive_env_name() -- no local derivation
```

### Tier 3 -- Error Conditions

- `FileNotFoundError`: "Blueprint file not found: {path}" -- when the blueprint does not exist.
- `ValueError`: "No signature blocks found in blueprint" -- when no `### Tier 2 — Signatures` headings are found. This heading format uses an em-dash -- any deviation causes a hard failure.
- `RuntimeError`: "Conda environment creation failed: {details}" -- when the environment creation command fails.
- `RuntimeError`: "Import validation failed for: {import_list}" -- when imports do not resolve in the environment.

### Tier 3 -- Behavioral Contracts

- `extract_all_imports` parses every `### Tier 2 — Signatures` code block across all units and collects all `import` and `from ... import` statements. Heading format must use an em-dash (spec Section 24.13).
- `classify_import` determines whether an import is standard library, third-party, or project-internal. Project-internal detection checks whether a `.py` file matching the top-level module name exists in the project's `scripts/` directory (the directory on `sys.path` where project modules reside). Prefix-based checks (`src`, `svp`) are retained as secondary heuristics. Imports that match neither the filesystem check nor the prefix list and are not in the standard library are classified as third-party.
- `map_imports_to_packages` maps third-party import module names to pip/conda package names.
- `create_conda_environment` creates the environment and installs packages. When `toolchain` is provided, reads command templates from `toolchain["environment"]` and resolves them via Unit 1's `resolve_command`. When `toolchain` is None, falls back to hardcoded commands (backward compatibility during testing). Always installs framework packages (from `toolchain["testing"]["framework_packages"]` when available, otherwise `["pytest", "pytest-cov"]`) unconditionally as framework dependencies required by the pipeline, in addition to any project-specific packages extracted from the blueprint. Always replaces any prior environment with the same name.
- `validate_imports` executes each import in the environment via the run prefix from the toolchain (or hardcoded `conda run -n {env_name}` when toolchain is None) and returns a list of (import, error) tuples for failures. Receives only third-party imports (pre-filtered by the caller). Does not validate project-internal or standard library imports.
- `create_project_directories` creates `src/unit_N/` and `tests/unit_N/` for each unit.
- `run_infrastructure_setup` is the high-level orchestration function called by the CLI wrapper. It loads the toolchain via Unit 1, loads state to get the project name, calls `derive_env_name` from Unit 1, then orchestrates: extract imports, map to packages, create environment, validate imports, create directories. Before calling `validate_imports`, filters the extracted imports to include only those classified as `third_party` by `classify_import`. Project-internal and standard library imports are excluded from conda environment validation since they do not exist as installable packages.
- The CLI wrapper `main()` is invoked as a `run_command` action and must emit `COMMAND_SUCCEEDED` on success or `COMMAND_FAILED: [details]` on failure as its terminal status line. These status lines must match Unit 10's `COMMAND_STATUS_PATTERNS` vocabulary.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Calls `derive_env_name` for canonical environment name derivation. Calls `load_toolchain` and `resolve_command` for tool command resolution.

---

## Unit 8: Hint Prompt Assembler

**Artifact category:** Python script

### Tier 1 -- Description

Takes the raw hint content from a help agent's terminal output, the gate metadata, the receiving agent type, and the ladder position, and produces a wrapped `## Human Domain Hint (via Help Agent)` section for inclusion in the task prompt. Uses deterministic templates with variable substitution -- no LLM involvement. Implements spec Section 14.4. Unchanged from v1.0.

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any
from pathlib import Path

def assemble_hint_prompt(
    hint_content: str,
    gate_id: str,
    agent_type: str,
    ladder_position: Optional[str] = None,
    unit_number: Optional[int] = None,
    stage: str = "",
) -> str: ...

def get_agent_type_framing(agent_type: str) -> str: ...

def get_ladder_position_framing(ladder_position: Optional[str]) -> str: ...
```

### Tier 2 — Invariants

```python
# Pre-conditions
assert len(hint_content.strip()) > 0, "Hint content must not be empty"
assert agent_type in ("test", "implementation", "blueprint_author", "stakeholder_dialog", "diagnostic", "other"), \
    "Agent type must be a recognized type"

# Post-conditions for assemble_hint_prompt
assert "## Human Domain Hint (via Help Agent)" in result, "Must contain the standard hint heading"
assert hint_content in result, "Must contain the original hint content"
```

### Tier 3 -- Error Conditions

- `ValueError`: "Empty hint content" -- when `hint_content` is empty or whitespace-only.
- `ValueError`: "Unknown agent type: {type}" -- when `agent_type` is not recognized.

### Tier 3 -- Behavioral Contracts

- `assemble_hint_prompt` produces the complete `## Human Domain Hint (via Help Agent)` section using deterministic templates. The output includes: the hint content, gate context (which gate, which unit, which stage), framing appropriate to the receiving agent type, and the constraint that the hint is a signal to evaluate rather than a command to execute.
- `get_agent_type_framing` returns a template string that frames the hint for the specific agent type: test agent framing emphasizes behavior and assertions, implementation agent framing emphasizes code changes, diagnostic framing emphasizes analysis context.
- `get_ladder_position_framing` returns a template string that adjusts framing based on where in the fix ladder the invocation sits.
- The output is pure text -- no structured data, no JSON, just a Markdown section ready for inclusion in a task prompt.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** No direct dependency on config values, but the assembler's templates reference concepts (fix ladder positions, agent types) whose names are consistent with the config schema.

---

## Unit 9: Preparation Script

**Artifact category:** Python script

### Tier 1 -- Description

Assembles task prompt files for agent invocations and gate prompt files for human decision gates. Takes the agent type (or gate identifier), unit number, ladder position, and other parameters as input and produces a ready-to-use file at a specified path. This is the most complex deterministic script and requires elevated test coverage (spec Section 26). Implements spec Section 3.7 (explicit context loading) and Section 17.1 (PREPARE command).

SVP 2.0 expansion: extracts profile sections for agent task prompts. Different agents receive different profile sections per spec Section 13.

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any, List
from pathlib import Path

def prepare_agent_task(
    project_root: Path,
    agent_type: str,
    unit_number: Optional[int] = None,
    ladder_position: Optional[str] = None,
    hint_content: Optional[str] = None,
    gate_id: Optional[str] = None,
    extra_context: Optional[Dict[str, str]] = None,
    revision_mode: Optional[str] = None,
) -> Path: ...

def prepare_gate_prompt(
    project_root: Path,
    gate_id: str,
    unit_number: Optional[int] = None,
    extra_context: Optional[Dict[str, str]] = None,
) -> Path: ...

def load_stakeholder_spec(project_root: Path) -> str: ...

def load_blueprint(project_root: Path) -> str: ...

def load_reference_summaries(project_root: Path) -> str: ...

def load_project_context(project_root: Path) -> str: ...

def load_ledger_content(project_root: Path, ledger_name: str) -> str: ...

def load_profile_sections(
    project_root: Path, sections: List[str]
) -> str: ...

def load_full_profile(project_root: Path) -> str: ...

def build_task_prompt_content(
    agent_type: str,
    sections: Dict[str, str],
    hint_block: Optional[str] = None,
) -> str: ...

# CLI entry point
def main() -> None: ...
```

### Tier 2 — Invariants

```python
# Pre-conditions
assert project_root.is_dir(), "Project root must exist"
assert agent_type or gate_id, "Must specify either agent_type or gate_id"

# Post-conditions for prepare_agent_task
assert result.exists(), "Task prompt file must exist after preparation"
assert result.stat().st_size > 0, "Task prompt file must not be empty"

# Post-conditions for prepare_gate_prompt
assert result.exists(), "Gate prompt file must exist after preparation"
assert result.stat().st_size > 0, "Gate prompt file must not be empty"
```

### Tier 3 -- Error Conditions

- `ValueError`: "Unknown agent type: {type}" -- when the agent type is not recognized.
- `ValueError`: "Unknown gate ID: {gate_id}" -- when the gate identifier is not recognized.
- `FileNotFoundError`: "Required document not found: {path}" -- when a document needed for the task prompt does not exist.
- `ValueError`: "Unit number required for agent type {type}" -- when unit-specific agents are invoked without a unit number.

### Tier 3 -- Behavioral Contracts

- `prepare_agent_task` assembles a task prompt file at `.svp/task_prompt.md` and returns its path. The content varies by agent type:
  - **setup_agent**: project context (if exists), ledger content. In profile mode (sub-stage `project_profile`): adds profile dialog context. In targeted revision mode (`revision_mode` is `"profile_delivery"` or `"profile_blueprint"`): adds current profile, redo classification, revision-mode flag.
  - **stakeholder_dialog**: ledger, reference summaries, project context. In revision mode: adds critique and current spec.
  - **blueprint_author**: stakeholder spec, reference summaries, ledger, checker feedback (if available). Adds profile sections: `readme`, `vcs`, `delivery` from `project_profile.json`.
  - **blueprint_checker**: stakeholder spec (with working notes), blueprint, reference summaries. Adds full profile for Layer 2 preference coverage validation.
  - **blueprint_reviewer**: blueprint, stakeholder spec, project context, reference summaries.
  - **stakeholder_reviewer**: stakeholder spec, project context, reference summaries.
  - **test_agent**: unit definition, upstream contracts. Adds `testing.readable_test_names` from profile.
  - **implementation_agent**: unit definition, upstream contracts. In fix ladder positions: adds diagnostic guidance, prior failure output, hint.
  - **coverage_review**: unit definition, upstream contracts, passing tests.
  - **diagnostic_agent**: stakeholder spec, unit blueprint section, failing tests, error output, failing implementations.
  - **integration_test_author**: stakeholder spec, contract signatures from all units.
  - **git_repo_agent**: all verified artifacts, reference documents. Adds full profile (commit style, README structure, source layout, dependency format, entry points, SPDX headers, additional metadata). In fix cycle: adds error output.
  - **help_agent**: project summary, stakeholder spec, blueprint. In gate-invocation mode: adds gate flag.
  - **hint_agent**: logs, documents, stakeholder spec, blueprint.
  - **redo_agent**: pipeline state summary, human error description, current unit definition (optional -- included when a unit number is provided, omitted otherwise). The redo agent does not require a unit number.
  - **reference_indexing**: full reference document.
  - **bug_triage**: stakeholder spec, blueprint, source code paths, test suite paths, ledger.
  - **repair_agent**: build/environment error diagnosis, environment state.
- `prepare_gate_prompt` assembles a gate prompt file at `.svp/gate_prompt.md` with the gate description, explicit response options, and relevant context. Gate 0.3 (`gate_0_3_profile_approval`): includes formatted profile summary. Gate 0.3r (`gate_0_3r_profile_revision`): includes modified profile summary showing what changed.
- `load_profile_sections` reads `project_profile.json` via Unit 1's `load_profile`, extracts the named sections, and returns them as a formatted string for inclusion in a task prompt. Gracefully handles missing profile (returns empty string with a note) for agents invoked before Gate 0.3.
- `load_full_profile` reads `project_profile.json` via Unit 1's `load_profile` and returns the entire profile as a formatted string.
- When `hint_content` is provided, delegates to Unit 8 (Hint Prompt Assembler) to produce the wrapped hint block and includes it in the task prompt.
- The preparation script's test suite must cover every combination of agent type, gate type, and ladder position -- this is an elevated coverage requirement.
- The CLI `main()` must accept `--output` (override output path), `--agent`, `--gate`, `--unit`, `--ladder`, `--revision-mode`, and `--project-root` arguments.
- The following agents require a `unit_number` parameter: `test_agent`, `implementation_agent`, `coverage_review`, `diagnostic_agent`. All other agents accept `unit_number` as optional or do not use it. The `redo_agent` specifically does NOT require a unit number.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Reads profile and toolchain for context assembly. Reads config for model assignments.
- **Unit 2 (Pipeline State Schema):** Reads pipeline state for context (current stage, unit, pass history).
- **Unit 4 (Ledger Manager):** Reads ledger content for ledger-based agents.
- **Unit 5 (Blueprint Extractor):** Extracts unit definitions and upstream contracts.
- **Unit 8 (Hint Prompt Assembler):** Wraps hint content when hints are forwarded.
- **Runtime copy:** `scripts/prepare_task.py` is the runtime deployment of this unit's canonical `src/unit_9/stub.py`. It must mirror the canonical stub in all exported constants (especially `KNOWN_AGENT_TYPES`) and assembler functions. See the "Scripts synchronization rule" in the preamble.

---

## Unit 10: Routing Script and Update State

**Artifact category:** Python script (routing.py + update_state.py CLI wrapper + run_tests.py CLI wrapper)

### Tier 1 -- Description

The routing script reads `pipeline_state.json` and outputs the exact next action as a structured key-value block (Section 17). The update_state script reads `.svp/last_status.txt` and dispatches to the appropriate state transition. The run_tests script wraps pytest execution and constructs command result status lines. This unit also defines the canonical gate status string vocabulary (Section 18.4) as a data constant used by both routing and dispatch logic.

This unit implements Bug 1 fix: the gate status string vocabulary ensures that human-typed option text is the exact status string -- no translation, no prefix, no reformatting.

SVP 2.0 expansion: gate vocabulary gains Gate 0.3 and Gate 0.3r entries, agent status lines gain profile-related entries, redo agent gains new classifications, test execution and collection error detection read from toolchain.

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any, List
from pathlib import Path
from pipeline_state import PipelineState
from state_transitions import TransitionError

# --- Data contract: gate status string vocabulary (Bug 1 fix) ---

GATE_VOCABULARY: Dict[str, List[str]] = {
    "gate_0_1_hook_activation": ["HOOKS ACTIVATED", "HOOKS FAILED"],
    "gate_0_2_context_approval": ["CONTEXT APPROVED", "CONTEXT REJECTED", "CONTEXT NOT READY"],
    "gate_0_3_profile_approval": ["PROFILE APPROVED", "PROFILE REJECTED"],
    "gate_0_3r_profile_revision": ["PROFILE APPROVED", "PROFILE REJECTED"],
    "gate_1_1_spec_draft": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_1_2_spec_post_review": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_2_1_blueprint_approval": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_2_2_blueprint_post_review": ["APPROVE", "REVISE", "FRESH REVIEW"],
    "gate_2_3_alignment_exhausted": ["REVISE SPEC", "RESTART SPEC", "RETRY BLUEPRINT"],
    "gate_3_1_test_validation": ["TEST CORRECT", "TEST WRONG"],
    "gate_3_2_diagnostic_decision": ["FIX IMPLEMENTATION", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_4_1_integration_failure": ["ASSEMBLY FIX", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_4_2_assembly_exhausted": ["FIX BLUEPRINT", "FIX SPEC"],
    "gate_5_1_repo_test": ["TESTS PASSED", "TESTS FAILED"],
    "gate_5_2_assembly_exhausted": ["RETRY ASSEMBLY", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_6_0_debug_permission": ["AUTHORIZE DEBUG", "ABANDON DEBUG"],
    "gate_6_1_regression_test": ["TEST CORRECT", "TEST WRONG"],
    "gate_6_2_debug_classification": ["FIX UNIT", "FIX BLUEPRINT", "FIX SPEC"],
    "gate_6_3_repair_exhausted": ["RETRY REPAIR", "RECLASSIFY BUG", "ABANDON DEBUG"],
    "gate_6_4_non_reproducible": ["RETRY TRIAGE", "ABANDON DEBUG"],
}

# --- Data contract: terminal status line vocabulary ---

AGENT_STATUS_LINES: Dict[str, List[str]] = {
    "setup_agent": [
        "PROJECT_CONTEXT_COMPLETE", "PROJECT_CONTEXT_REJECTED",
        "PROJECT_PROFILE_COMPLETE", "PROJECT_PROFILE_REJECTED",
    ],
    "stakeholder_dialog": ["SPEC_DRAFT_COMPLETE", "SPEC_REVISION_COMPLETE"],
    "stakeholder_reviewer": ["REVIEW_COMPLETE"],
    "blueprint_author": ["BLUEPRINT_DRAFT_COMPLETE", "BLUEPRINT_REVISION_COMPLETE"],
    "blueprint_checker": ["ALIGNMENT_CONFIRMED", "ALIGNMENT_FAILED: spec", "ALIGNMENT_FAILED: blueprint"],
    "blueprint_reviewer": ["REVIEW_COMPLETE"],
    "test_agent": ["TEST_GENERATION_COMPLETE"],
    "implementation_agent": ["IMPLEMENTATION_COMPLETE"],
    "coverage_review": ["COVERAGE_COMPLETE: no gaps", "COVERAGE_COMPLETE: tests added"],
    "diagnostic_agent": ["DIAGNOSIS_COMPLETE: implementation", "DIAGNOSIS_COMPLETE: blueprint", "DIAGNOSIS_COMPLETE: spec"],
    "integration_test_author": ["INTEGRATION_TESTS_COMPLETE"],
    "git_repo_agent": ["REPO_ASSEMBLY_COMPLETE"],
    "help_agent": ["HELP_SESSION_COMPLETE: no hint", "HELP_SESSION_COMPLETE: hint forwarded"],
    "hint_agent": ["HINT_ANALYSIS_COMPLETE"],
    "redo_agent": [
        "REDO_CLASSIFIED: spec", "REDO_CLASSIFIED: blueprint", "REDO_CLASSIFIED: gate",
        "REDO_CLASSIFIED: profile_delivery", "REDO_CLASSIFIED: profile_blueprint",
    ],
    "bug_triage": ["TRIAGE_COMPLETE: build_env", "TRIAGE_COMPLETE: single_unit", "TRIAGE_COMPLETE: cross_unit", "TRIAGE_NEEDS_REFINEMENT", "TRIAGE_NON_REPRODUCIBLE"],
    "repair_agent": ["REPAIR_COMPLETE", "REPAIR_FAILED", "REPAIR_RECLASSIFY"],
    "reference_indexing": ["INDEXING_COMPLETE"],
}

# Cross-agent status (any agent receiving a hint)
CROSS_AGENT_STATUS: str = "HINT_BLUEPRINT_CONFLICT"

# Command result status line patterns
COMMAND_STATUS_PATTERNS: List[str] = [
    "TESTS_PASSED",    # "TESTS_PASSED: N passed"
    "TESTS_FAILED",    # "TESTS_FAILED: N passed, M failed"
    "TESTS_ERROR",     # "TESTS_ERROR: [error summary]"
    "COMMAND_SUCCEEDED",
    "COMMAND_FAILED",  # "COMMAND_FAILED: [exit code]"
]

# --- Routing functions ---

def route(state: PipelineState, project_root: Path) -> Dict[str, Any]: ...

def format_action_block(action: Dict[str, Any]) -> str: ...

# --- Update state functions (update_state.py) ---

def dispatch_status(
    state: PipelineState,
    status_line: str,
    gate_id: Optional[str],
    unit: Optional[int],
    phase: str,
    project_root: Path,
) -> PipelineState: ...

def dispatch_gate_response(
    state: PipelineState,
    gate_id: str,
    response: str,
    project_root: Path,
) -> PipelineState: ...

def dispatch_agent_status(
    state: PipelineState,
    agent_type: str,
    status_line: str,
    unit: Optional[int],
    phase: str,
    project_root: Path,
) -> PipelineState: ...

def dispatch_command_status(
    state: PipelineState,
    status_line: str,
    unit: Optional[int],
    phase: str,
    project_root: Path,
) -> PipelineState: ...

# --- Run tests wrapper (run_tests.py) ---

def run_pytest(
    test_path: Path,
    env_name: str,
    project_root: Path,
    toolchain: Optional[Dict[str, Any]] = None,
) -> str: ...

def _is_collection_error(output: str, toolchain: Optional[Dict[str, Any]] = None) -> bool: ...

# CLI entry points
def routing_main() -> None: ...

def update_state_main() -> None: ...

def run_tests_main() -> None: ...
```

### Tier 2 — Invariants

```python
# Pre-conditions for route
assert project_root.is_dir(), "Project root must exist"

# Post-conditions for route
assert "ACTION" in result, "Route output must contain ACTION"
assert result["ACTION"] in ("invoke_agent", "run_command", "human_gate", "session_boundary", "pipeline_complete"), \
    "ACTION must be a valid action type"

# Post-conditions for dispatch_gate_response (Bug 1 invariant)
assert gate_id in GATE_VOCABULARY, "Gate ID must be in the vocabulary"
assert response in GATE_VOCABULARY[gate_id], "Response must be a valid option for this gate"

# Post-conditions for format_action_block
assert "REMINDER:" in result or "session_boundary" in result or "pipeline_complete" in result, \
    "Non-terminal actions must include REMINDER block"

# Gate 0.3 vocabulary invariant
assert "PROFILE APPROVED" in GATE_VOCABULARY["gate_0_3_profile_approval"]
assert "PROFILE REJECTED" in GATE_VOCABULARY["gate_0_3_profile_approval"]
assert "PROFILE APPROVED" in GATE_VOCABULARY["gate_0_3r_profile_revision"]
assert "PROFILE REJECTED" in GATE_VOCABULARY["gate_0_3r_profile_revision"]

# Redo agent profile classifications
assert "REDO_CLASSIFIED: profile_delivery" in AGENT_STATUS_LINES["redo_agent"]
assert "REDO_CLASSIFIED: profile_blueprint" in AGENT_STATUS_LINES["redo_agent"]
```

### Tier 3 -- Error Conditions

- `ValueError`: "Invalid gate response '{response}' for gate {gate_id}. Valid options: {options}" -- when the human's response does not match any option in the gate vocabulary. This is the Bug 1 prevention mechanism.
- `ValueError`: "Unknown agent status line: {line}" -- when a terminal status line does not match any known pattern.
- `ValueError`: "Unknown phase: {phase}" -- when the dispatch phase is not recognized.
- `TransitionError`: propagated from Unit 3 when state transitions fail precondition checks.

### Tier 3 -- Behavioral Contracts

**Routing (expanded for SVP 2.0):**
- `route` reads `pipeline_state.json`, determines the next action, and returns a dict with all fields needed for the action block. Handles all pipeline states including: Stage 0 `project_profile` sub-stage (invokes setup agent for profile dialog), Gate 0.3 presentation, redo-triggered profile revision sub-stages (invokes setup agent in targeted revision mode), Gate 0.3r presentation, and debug loop states.
- When state is `stage: "0", sub_stage: "project_profile"`, route emits an `invoke_agent` action for the setup agent with profile dialog context.
- When state is `sub_stage: "redo_profile_delivery"` or `sub_stage: "redo_profile_blueprint"`, route emits an `invoke_agent` action for the setup agent with targeted revision context (current profile, redo classification, revision-mode flag).
- `format_action_block` converts the dict to the structured text format defined in spec Section 17. Includes the REMINDER block for `invoke_agent`, `run_command`, and `human_gate` actions. Omits REMINDER for `session_boundary` and `pipeline_complete`.

**Dispatch (expanded for SVP 2.0):**
- `dispatch_gate_response` validates the response against `GATE_VOCABULARY[gate_id]` using exact string matching. Handles Gate 0.3: `PROFILE APPROVED` advances sub-stage from `project_profile` to Stage 1 (via `advance_stage`). `PROFILE REJECTED` keeps sub-stage at `project_profile` for revision. Handles Gate 0.3r: `PROFILE APPROVED` calls `complete_redo_profile_revision` (Unit 3). `PROFILE REJECTED` keeps sub-stage at the redo revision sub-stage.
- `dispatch_agent_status` validates the status line against `AGENT_STATUS_LINES` using **prefix matching** (not exact matching) — a status line is recognized if it equals or starts with any known line. This is consistent with how `dispatch_command_status` validates against `COMMAND_STATUS_PATTERNS`. Handles new setup agent statuses: `PROJECT_PROFILE_COMPLETE` triggers Gate 0.3 presentation. `PROJECT_PROFILE_REJECTED` sets sub-stage appropriately. Handles new redo agent statuses: `REDO_CLASSIFIED: profile_delivery` calls `enter_redo_profile_revision(state, "profile_delivery")`. `REDO_CLASSIFIED: profile_blueprint` calls `enter_redo_profile_revision(state, "profile_blueprint")`.
- `dispatch_command_status` parses command result status lines and calls appropriate Unit 3 transition functions. For `compliance_scan` phase: `COMMAND_SUCCEEDED` means scan passed, `COMMAND_FAILED` means violations found (enters bounded fix cycle).
- `dispatch_status` is the top-level dispatcher: reads the status file, determines whether it is a gate response, agent status, or command result, and delegates to the appropriate handler.

**Test execution (changed for SVP 2.0):**
- `run_pytest` reads test execution command template from `toolchain["testing"]["run"]` when toolchain is provided, otherwise uses hardcoded `conda run -n {env_name} pytest {test_path} -v`. Resolves placeholders via Unit 1's `resolve_command`. Constructs the appropriate command result status line from the output.
- `_is_collection_error` reads collection error indicators from `toolchain["testing"]["collection_error_indicators"]` when toolchain is provided, otherwise uses hardcoded indicators. Uses only specific indicators (`"ERROR collecting"`, `"ImportError"`, `"ModuleNotFoundError"`, `"SyntaxError"`, `"no tests ran"`). Must NOT use a bare `"ERROR"` indicator.

- The OPTIONS field in human_gate output lists exactly the valid status strings from `GATE_VOCABULARY` for the corresponding gate (Bug 1 invariant).

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Reads config for model assignments, iteration limits, project settings. Reads toolchain for command resolution. Calls `derive_env_name` for environment name derivation.
- **Unit 2 (Pipeline State Schema):** Reads and writes pipeline state.
- **Unit 3 (State Transition Engine):** Calls transition functions for state updates. Uses `TransitionError` for precondition failures.

---

## Unit 11: Command Logic Scripts

**Artifact category:** Python scripts

### Tier 1 -- Description

Implements the logic for Group A utility commands: `/svp:save`, `/svp:quit`, `/svp:status`, `/svp:clean`. Each command is a dedicated `cmd_*.py` script. These are invoked directly by the main session -- no subagent is spawned. Implements spec Sections 12.2 (modified status output) and 13.

SVP 2.0 expansion: `cmd_status.py` gains pipeline toolchain and profile summary in status output.

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any
from pathlib import Path

# cmd_save.py
def save_project(project_root: Path) -> str: ...

# cmd_quit.py
def quit_project(project_root: Path) -> str: ...

# cmd_status.py
def get_status(project_root: Path) -> str: ...

def format_pass_history(pass_history: list) -> str: ...

def format_debug_history(debug_history: list) -> str: ...

def format_profile_summary(project_root: Path) -> str: ...

# cmd_clean.py
def clean_workspace(project_root: Path, mode: str) -> str: ...

def archive_workspace(project_root: Path) -> Path: ...

def delete_workspace(project_root: Path) -> None: ...

def remove_conda_env(env_name: str) -> bool: ...
```

### Tier 2 — Invariants

```python
# Pre-conditions
assert project_root.is_dir(), "Project root must exist"
assert mode in ("archive", "delete", "keep"), "Clean mode must be archive, delete, or keep"

# Post-conditions for save_project
assert len(result) > 0, "Save confirmation message must be non-empty"

# Post-conditions for get_status -- must include pipeline toolchain and profile summary
assert "Pipeline:" in result or "pipeline" in result.lower(), \
    "Status must include pipeline toolchain info"
```

### Tier 3 -- Error Conditions

- `FileNotFoundError`: "Pipeline state file not found" -- when `get_status` cannot find `pipeline_state.json`.
- `PermissionError`: "Cannot delete workspace: permission denied on {path}" -- when `__pycache__` or conda files have read-only permissions. The deletion handler must chmod and retry before reporting failure.
- `RuntimeError`: "Conda environment removal failed: {env_name}" -- when `conda env remove` fails.

### Tier 3 -- Behavioral Contracts

- `save_project` verifies file integrity of state file and key documents, confirms save is complete, returns a human-readable confirmation message.
- `quit_project` calls `save_project` first, then returns an exit confirmation message with save status.
- `get_status` reads pipeline state and produces a human-readable report including: current stage, sub-stage, verified units, alignment iterations used, pass history summary, debug history summary, next expected action, **pipeline toolchain identifier** (e.g., `python_conda_pytest`), and **one-line profile summary** (e.g., `pyenv, conventional commits, comprehensive README, MIT`). The profile summary is produced by `format_profile_summary`. Format per spec Section 12.2.
- `format_profile_summary` reads `project_profile.json` via Unit 1's `load_profile`. Returns a one-line string summarizing key delivery preferences: environment recommendation, commit style, README depth, license type. Returns "Profile not yet created" if the profile file does not exist.
- `format_pass_history` formats pass history entries as a brief numbered list.
- `format_debug_history` formats debug history entries similarly.
- `clean_workspace` is only functional after Stage 5 delivery. Returns an error message if invoked before delivery.
- `archive_workspace` compresses the workspace into a `.tar.gz` file alongside the repo, then deletes the workspace directory.
- `delete_workspace` removes the workspace with a permission-aware handler: chmod read-only paths and retry on `PermissionError`. The delivered repository is never touched.
- `remove_conda_env` runs `conda env remove -n {env_name} --yes`.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Reads config for project settings and auto_save behavior. Reads profile for status summary. Calls `derive_env_name` for clean operations.
- **Unit 2 (Pipeline State Schema):** Reads pipeline state for status reporting.
- **Unit 4 (Ledger Manager):** Reads ledger files for save integrity verification.

---

## Unit 12: Hook Configurations

**Artifact category:** JSON + shell scripts

### Tier 1 -- Description

Defines the hook configuration (`hooks.json`) and hook scripts (`write_authorization.sh`, `non_svp_protection.sh`) for universal write authorization and project protection. Implements spec Section 15 (both layers of write authorization), including the debug permission reset mechanism (Bug 2 fix), the `SVP_PLUGIN_ACTIVE` environment variable check (SVP 1.1 hardening), and write authorization for `project_profile.json` and `toolchain.json` (SVP 2.0).

### Tier 2 — Signatures

```python
# hooks.json structure (JSON, not Python -- shown as dict for contract purposes)
from typing import Dict, Any, List
import json

HOOKS_JSON_SCHEMA: Dict[str, Any] = {
    "hooks": {
        "PreToolUse": [
            {
                "type": "bash",
                "matcher": "write|edit|create",
                "script": ".claude/scripts/write_authorization.sh",
                "description": "Universal write authorization"
            },
            {
                "type": "bash",
                "matcher": "bash",
                "script": ".claude/scripts/non_svp_protection.sh",
                "description": "Non-SVP session protection"
            },
        ]
    }
}

# write_authorization.sh contract
def check_write_authorization(
    tool_name: str,
    file_path: str,
    pipeline_state_path: str,
) -> int: ...
    # Returns 0 (allow), 2 (block)

# non_svp_protection.sh contract
def check_svp_session(env_var_name: str) -> int: ...
    # Returns 0 (allow), 2 (block)

# Canonical environment variable name (SVP 1.1 hardening invariant)
SVP_ENV_VAR: str = "SVP_PLUGIN_ACTIVE"

# Deliverable content constants (written by Stage 5 assembly)
HOOKS_JSON_CONTENT: str  # -> svp/hooks/hooks.json
WRITE_AUTHORIZATION_SH_CONTENT: str  # -> svp/hooks/scripts/write_authorization.sh
NON_SVP_PROTECTION_SH_CONTENT: str  # -> svp/hooks/scripts/non_svp_protection.sh
```

### Tier 2 — Invariants

```python
# Cross-unit invariant: SVP_PLUGIN_ACTIVE
assert SVP_ENV_VAR == "SVP_PLUGIN_ACTIVE", "Canonical env var name must be SVP_PLUGIN_ACTIVE"

# Plugin hook format invariant
assert "hooks" in HOOKS_JSON_SCHEMA, "Must use top-level hooks wrapper key"

# Content strings must produce valid deliverable files
assert "hooks" in json.loads(HOOKS_JSON_CONTENT), "hooks.json must have top-level hooks key"
assert WRITE_AUTHORIZATION_SH_CONTENT.startswith("#!/"), "Shell scripts must have shebang"
assert NON_SVP_PROTECTION_SH_CONTENT.startswith("#!/"), "Shell scripts must have shebang"
assert SVP_ENV_VAR in NON_SVP_PROTECTION_SH_CONTENT, "Must check SVP_PLUGIN_ACTIVE"

# SVP 2.0: profile and toolchain write authorization
assert "project_profile.json" in WRITE_AUTHORIZATION_SH_CONTENT, \
    "Must handle project_profile.json write authorization"
assert "toolchain.json" in WRITE_AUTHORIZATION_SH_CONTENT, \
    "Must handle toolchain.json write authorization"
```

### Tier 3 -- Error Conditions

- Exit code 2 from `write_authorization.sh`: blocks the write and returns a message explaining why the path is not writable in the current state.
- Exit code 2 from `non_svp_protection.sh`: blocks bash execution and informs the human this is an SVP-managed project.

### Tier 3 -- Behavioral Contracts

- `hooks.json` uses the top-level `"hooks"` wrapper key required by Claude Code plugin hook format. It must NOT use the flat format.
- `write_authorization.sh` reads `pipeline_state.json` to determine the current state and checks the requested file path against the two-tier authorization model:
  - **Infrastructure paths** (`.svp/`, `pipeline_state.json`, `ledgers/`, `logs/`): always writable.
  - **Project artifact paths** (`src/`, `tests/`, `specs/`, `blueprint/`, `references/`, `projectname-repo/`): state-gated.
  - **`project_profile.json`** (NEW): writable during Stage 0 `project_profile` sub-stage AND during any active redo-triggered profile revision (sub-stage is `redo_profile_delivery` or `redo_profile_blueprint`, regardless of the current pipeline stage). Read-only otherwise. The hook checks the `sub_stage` field in `pipeline_state.json`.
  - **`toolchain.json`** (NEW): permanently read-only after creation. No agent, session, or command may modify it. The hook blocks all writes unconditionally.
- **Debug session write rules (Bug 2 fix):** When `debug_session` is present in pipeline state AND `debug_session.authorized` is `true`:
  - `tests/regressions/` is writable regardless of classification.
  - During `build_env` classification: environment files, `pyproject.toml`, `__init__.py`, and directory structure are writable. Implementation `.py` files in `src/unit_N/` (other than `__init__.py`) are NOT writable.
  - During `single_unit` classification: `src/unit_N/` and `tests/unit_N/` are writable only for affected unit(s).
  - `.svp/triage_scratch/` is writable during triage.
- When `debug_session` is present but `debug_session.authorized` is `false` (pre-Gate 6.0): only infrastructure paths are writable. No artifact writes permitted.
- `non_svp_protection.sh` checks for the `SVP_PLUGIN_ACTIVE` environment variable. If not set, blocks all bash tool use and informs the human. The variable name MUST be `SVP_PLUGIN_ACTIVE`.
- Hook scripts use paths relative to the project root. Paths must use `.claude/scripts/` prefix so they resolve correctly from the project root.
- `HOOKS_JSON_CONTENT` must be valid JSON matching the Claude Code plugin hook format.
- `WRITE_AUTHORIZATION_SH_CONTENT` must be a bash script that handles all stages (0-5), pre_stage_3, debug sessions, profile write authorization, and toolchain write blocking.
- `NON_SVP_PROTECTION_SH_CONTENT` must be a bash script that checks for `SVP_PLUGIN_ACTIVE`.

### Tier 3 -- Dependencies

- **Unit 2 (Pipeline State Schema):** `write_authorization.sh` reads `pipeline_state.json` to check current state, sub-stage, and debug session authorization.

---

## Unit 13: Dialog Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the three dialog agents: Setup Agent, Stakeholder Dialog Agent, and Blueprint Author Agent. Each file is a Markdown document with YAML frontmatter that becomes the agent's system prompt. These agents use the ledger-based multi-turn interaction pattern. Implements spec Sections 6.3, 6.4, 7.3, 7.4, 7.6, and 8.1.

SVP 2.0 expansion: Setup agent gains project profile dialog (four areas: version control, README/documentation, test/quality, licensing/metadata/packaging), Gate 0.3, targeted revision mode for redo-triggered profile changes, experience-aware dialog, Mode A awareness, contradiction detection, and Tier C handling.

### Tier 2 — Signatures

```python
from typing import Dict, Any, List

# --- YAML frontmatter schema for each agent definition ---

SETUP_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "setup_agent",
    "description": "Creates project_context.md and project_profile.json through Socratic dialog",
    "model": "claude-sonnet-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

STAKEHOLDER_DIALOG_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "stakeholder_dialog_agent",
    "description": "Conducts Socratic dialog to produce the stakeholder spec",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

BLUEPRINT_AUTHOR_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "blueprint_author_agent",
    "description": "Conducts decomposition dialog and produces the technical blueprint",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

# --- Terminal status lines ---
SETUP_AGENT_STATUS: List[str] = [
    "PROJECT_CONTEXT_COMPLETE", "PROJECT_CONTEXT_REJECTED",
    "PROJECT_PROFILE_COMPLETE", "PROJECT_PROFILE_REJECTED",
]
STAKEHOLDER_DIALOG_STATUS: List[str] = ["SPEC_DRAFT_COMPLETE", "SPEC_REVISION_COMPLETE"]
BLUEPRINT_AUTHOR_STATUS: List[str] = ["BLUEPRINT_DRAFT_COMPLETE", "BLUEPRINT_REVISION_COMPLETE"]

# Deliverable content constants (written by Stage 5 assembly)
SETUP_AGENT_MD_CONTENT: str  # -> agents/setup_agent.md
STAKEHOLDER_DIALOG_AGENT_MD_CONTENT: str  # -> agents/stakeholder_dialog_agent.md
BLUEPRINT_AUTHOR_AGENT_MD_CONTENT: str  # -> agents/blueprint_author_agent.md
```

### Tier 2 — Invariants

```python
# All dialog agents must enforce the structured response format
# Every response must end with exactly one of: [QUESTION], [DECISION], [CONFIRMED]

# Blueprint Author must produce units in the three-tier format
# Tier 2 heading must be exactly: ### Tier 2 — Signatures (em-dash)

# Setup Agent must handle both project_context and project_profile sub-stages
# Setup Agent must handle targeted revision mode for redo-triggered profile changes

# Every *_MD_CONTENT string must be a valid Claude Code agent definition:
# - Starts with "---\n" (YAML frontmatter delimiter)
# - Contains "name:" in frontmatter
# - Contains "model:" in frontmatter
# - Contains "tools:" in frontmatter
# - Contains a second "---\n" (end of frontmatter)
# - Has substantial behavioral instructions after frontmatter (>100 chars)
```

### Tier 3 -- Error Conditions

- No runtime errors from the agent definitions themselves. Agents produce terminal status lines. If an agent fails to produce a valid terminal status line, the main session must re-invoke or escalate.

### Tier 3 -- Behavioral Contracts

- Each `*_MD_CONTENT` string must be a complete Claude Code agent definition file. The YAML frontmatter must match the corresponding `*_FRONTMATTER` dict. The behavioral instructions must be detailed enough that the agent can perform its role autonomously.
- **Setup Agent (EXPANDED for SVP 2.0):** Operates in two modes determined by the task prompt context:
  - **Project context mode** (sub-stage `project_context`): Conducts `project_context.md` creation dialog. Actively rewrites human input into well-structured, LLM-optimized context. Enforces quality gate. Terminal status: `PROJECT_CONTEXT_COMPLETE` or `PROJECT_CONTEXT_REJECTED`.
  - **Project profile mode** (sub-stage `project_profile`): Conducts Socratic dialog across four areas (version control, README/documentation, test/quality, licensing/metadata/packaging). Experience-aware: every question explained in plain language with examples. Every area offers a fast path. Mode A awareness: pre-populates Mode A defaults (12-section README, conventional commits, MIT license, etc.) and only asks genuinely open questions. Checks for known contradictory combinations before writing. Records what human said -- does not generate creative content. Writes fully populated `project_profile.json` with every field explicit. If human volunteers Tier C preferences, acknowledges honestly and explains limitation. Cross-area dependency: when `testing.readme_test_scenarios` is true, automatically adds a Testing section to `readme.sections` if not already present. Terminal status: `PROJECT_PROFILE_COMPLETE` or `PROJECT_PROFILE_REJECTED`.
  - **Targeted revision mode** (sub-stage `redo_profile_delivery` or `redo_profile_blueprint`): Receives current profile, redo classification, revision-mode flag. Reopens only the affected dialog area. Modifies affected fields. Presents changes highlighted against previous version. Uses same terminal status lines as profile mode.
  - Uses `claude-sonnet-4-6`. Continues on same ledger (`ledgers/setup_dialog.jsonl`) across context and profile phases.
- **Stakeholder Dialog Agent (unchanged):** Conducts the Socratic dialog for stakeholder spec authoring. Terminal status: `SPEC_DRAFT_COMPLETE` or `SPEC_REVISION_COMPLETE`. Uses `claude-opus-4-6`.
- **Blueprint Author Agent (expanded context):** Conducts decomposition dialog with domain expert. Receives `project_profile.json` sections (`readme`, `vcs`, `delivery`) as context. Uses profile to structure the delivery unit with awareness of README preferences and source layout choice, encode tool preferences as explicit behavioral contracts (Layer 1 of preference enforcement), include commit style in git repo agent behavioral contract. Profile is context, not instruction override -- discrepancies surfaced through normal alignment. Terminal status: `BLUEPRINT_DRAFT_COMPLETE` for initial drafts, `BLUEPRINT_REVISION_COMPLETE` for revisions (when re-invoked after a REVISE gate decision). Uses `claude-opus-4-6`.
- All three agents include in their system prompts: the structured response format requirement, the terminal status line vocabulary, and the constraint against modifying files outside their scope.

### Tier 3 -- Dependencies

- **Unit 4 (Ledger Manager):** Dialog agents operate on conversation ledgers.
- **Unit 9 (Preparation Script):** The task prompt content these agents receive is assembled by Unit 9.

---

## Unit 14: Review and Checker Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the three review/checker agents: Stakeholder Spec Reviewer, Blueprint Checker, and Blueprint Reviewer. These are single-shot agents that receive documents, produce a critique or verdict, and terminate. Implements spec Sections 7.4, 8.2, and the "report most fundamental level" principle.

SVP 2.0 expansion: Blueprint Checker gains Layer 2 preference coverage validation -- receives the project profile and verifies that every profile preference is reflected as an explicit contract in at least one unit.

### Tier 2 — Signatures

```python
from typing import Dict, Any, List

STAKEHOLDER_REVIEWER_FRONTMATTER: Dict[str, Any] = {
    "name": "stakeholder_reviewer",
    "description": "Reviews stakeholder spec cold, produces structured critique",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep"],
}

BLUEPRINT_CHECKER_FRONTMATTER: Dict[str, Any] = {
    "name": "blueprint_checker",
    "description": "Verifies blueprint alignment with stakeholder spec and project profile",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep", "Bash"],
}

BLUEPRINT_REVIEWER_FRONTMATTER: Dict[str, Any] = {
    "name": "blueprint_reviewer",
    "description": "Reviews blueprint cold, produces structured critique",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep"],
}

STAKEHOLDER_REVIEWER_STATUS: List[str] = ["REVIEW_COMPLETE"]
BLUEPRINT_CHECKER_STATUS: List[str] = ["ALIGNMENT_CONFIRMED", "ALIGNMENT_FAILED: spec", "ALIGNMENT_FAILED: blueprint"]
BLUEPRINT_REVIEWER_STATUS: List[str] = ["REVIEW_COMPLETE"]

# Deliverable content constants (written by Stage 5 assembly)
STAKEHOLDER_REVIEWER_MD_CONTENT: str  # -> agents/stakeholder_reviewer.md
BLUEPRINT_CHECKER_MD_CONTENT: str  # -> agents/blueprint_checker.md
BLUEPRINT_REVIEWER_MD_CONTENT: str  # -> agents/blueprint_reviewer.md
```

### Tier 2 — Invariants

```python
# Blueprint Checker must validate:
# - Machine-readable signatures are parseable (valid Python via ast)
# - All referenced types have corresponding import statements
# - Per-unit worst-case context budget is within threshold
# - Working notes are consistent with original spec text
# - Report most fundamental level when multiple issues found
# - (NEW) Every profile preference reflected as explicit contract in at least one unit (Layer 2)

# Every *_MD_CONTENT string must be a valid Claude Code agent definition
```

### Tier 3 -- Error Conditions

- No runtime errors from agent definitions. Agents produce terminal status lines.

### Tier 3 -- Behavioral Contracts

- Each `*_MD_CONTENT` string must be a complete Claude Code agent definition file with matching frontmatter and detailed behavioral instructions.
- **Stakeholder Spec Reviewer (unchanged):** Reads document cold. Produces structured critique. Terminal status: `REVIEW_COMPLETE`. Uses `claude-opus-4-6`.
- **Blueprint Checker (EXPANDED for SVP 2.0):** Receives stakeholder spec (with working notes), blueprint, reference summaries, AND full project profile. Verifies alignment. Validates structural requirements: signatures parseable via `ast`, all types have imports, per-unit context budget within threshold, working note consistency. **Layer 2 preference coverage validation (NEW):** Verifies that every profile preference -- including documentation, metadata, commit style, and delivery packaging, not just code-behavior preferences -- is reflected as an explicit contract in at least one unit. A profile that says "conda, no bare pip" with no unit mentioning conda usage is an alignment failure. A profile that says "comprehensive README for developers" with no unit contract specifying audience and depth is also an alignment failure. Reports only the most fundamental level. Produces dual-format output. Three outcomes. Uses `claude-opus-4-6`.
- **Blueprint Reviewer (unchanged):** Reads documents cold. Produces structured critique. Terminal status: `REVIEW_COMPLETE`. Uses `claude-opus-4-6`.

### Tier 3 -- Dependencies

- **Unit 9 (Preparation Script):** The task prompt content these agents receive is assembled by Unit 9.

---

## Unit 15: Construction Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the three construction agents: Test Agent, Implementation Agent, and Coverage Review Agent. These are single-shot agents that produce code artifacts. Implements spec Sections 10.1, 10.4, and 10.6.

SVP 2.0 expansion: Test agent receives `testing.readable_test_names` from profile.

### Tier 2 — Signatures

```python
from typing import Dict, Any, List

TEST_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "test_agent",
    "description": "Generates pytest test suite for a single unit",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

IMPLEMENTATION_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "implementation_agent",
    "description": "Generates Python implementation for a single unit",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

COVERAGE_REVIEW_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "coverage_review_agent",
    "description": "Reviews test coverage and adds missing tests",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

TEST_AGENT_STATUS: List[str] = ["TEST_GENERATION_COMPLETE"]
IMPLEMENTATION_AGENT_STATUS: List[str] = ["IMPLEMENTATION_COMPLETE"]
COVERAGE_REVIEW_STATUS: List[str] = ["COVERAGE_COMPLETE: no gaps", "COVERAGE_COMPLETE: tests added"]

# Deliverable content constants (written by Stage 5 assembly)
TEST_AGENT_MD_CONTENT: str  # -> agents/test_agent.md
IMPLEMENTATION_AGENT_MD_CONTENT: str  # -> agents/implementation_agent.md
COVERAGE_REVIEW_AGENT_MD_CONTENT: str  # -> agents/coverage_review_agent.md
```

### Tier 2 — Invariants

```python
# Test agent must never see the implementation
# Implementation agent must never see the tests
# Test agent must declare synthetic data assumptions as part of output
# (NEW) Test agent reads testing.readable_test_names from profile context

# Every *_MD_CONTENT string must be a valid Claude Code agent definition
```

### Tier 3 -- Error Conditions

- No runtime errors from agent definitions. Agents produce terminal status lines.

### Tier 3 -- Behavioral Contracts

- Each `*_MD_CONTENT` string must be a complete Claude Code agent definition file with matching frontmatter and detailed behavioral instructions.
- **Test Agent (expanded context):** Receives unit definition and upstream contracts. Receives `testing.readable_test_names` flag from profile -- when true, generates test names that read as natural language descriptions (e.g., `test_spike_below_minimum_duration_is_rejected`). Does NOT see any implementation. Terminal status: `TEST_GENERATION_COMPLETE`. Uses `claude-opus-4-6`.
- **Implementation Agent (unchanged):** Receives unit definition and upstream contracts. Does NOT see the tests. In fix ladder positions: receives diagnostic guidance, prior failure output, and optional hint. If a hint contradicts the blueprint, returns `HINT_BLUEPRINT_CONFLICT: [details]`. Terminal status: `IMPLEMENTATION_COMPLETE`. Uses `claude-opus-4-6`.
- **Coverage Review Agent (unchanged):** Receives blueprint unit definition, upstream contracts, and passing test suite. Identifies behaviors implied by blueprint that no test covers. Terminal status: `COVERAGE_COMPLETE: no gaps` or `COVERAGE_COMPLETE: tests added`. Uses `claude-opus-4-6`.

### Tier 3 -- Dependencies

- **Unit 6 (Stub Generator):** The test agent's tests run against stubs generated by Unit 6.
- **Unit 9 (Preparation Script):** The task prompt content these agents receive is assembled by Unit 9.

---

## Unit 16: Diagnostic and Classification Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the Diagnostic Agent and Redo Agent. Both produce dual-format output (prose + structured block) for routing decisions. Implements spec Sections 10.9 (three-hypothesis discipline) and 12.1 (`/svp:redo` classification including profile classifications).

SVP 2.0 expansion: Redo agent gains `profile_delivery` and `profile_blueprint` classifications.

### Tier 2 — Signatures

```python
from typing import Dict, Any, List

DIAGNOSTIC_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "diagnostic_agent",
    "description": "Analyzes test failures using three-hypothesis discipline",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep"],
}

REDO_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "redo_agent",
    "description": "Traces human gate errors and profile issues through the document hierarchy",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep"],
}

DIAGNOSTIC_AGENT_STATUS: List[str] = [
    "DIAGNOSIS_COMPLETE: implementation",
    "DIAGNOSIS_COMPLETE: blueprint",
    "DIAGNOSIS_COMPLETE: spec",
]

REDO_AGENT_STATUS: List[str] = [
    "REDO_CLASSIFIED: spec",
    "REDO_CLASSIFIED: blueprint",
    "REDO_CLASSIFIED: gate",
    "REDO_CLASSIFIED: profile_delivery",
    "REDO_CLASSIFIED: profile_blueprint",
]

# Deliverable content constants (written by Stage 5 assembly)
DIAGNOSTIC_AGENT_MD_CONTENT: str  # -> agents/diagnostic_agent.md
REDO_AGENT_MD_CONTENT: str  # -> agents/redo_agent.md
```

### Tier 2 — Invariants

```python
# Diagnostic agent must articulate all three hypotheses before converging
# Redo agent must not ask the human to self-classify their error
# (NEW) Redo agent must distinguish profile_delivery from profile_blueprint

# Every *_MD_CONTENT string must be a valid Claude Code agent definition
```

### Tier 3 -- Error Conditions

- No runtime errors from agent definitions. Agents produce terminal status lines.

### Tier 3 -- Behavioral Contracts

- Each `*_MD_CONTENT` string must be a complete Claude Code agent definition file with matching frontmatter and detailed behavioral instructions.
- **Diagnostic Agent (unchanged):** Receives stakeholder spec, unit blueprint section, failing tests, error output, and failing implementations. Must articulate all three hypotheses before converging. Produces dual-format output. Terminal status: `DIAGNOSIS_COMPLETE: implementation`, `DIAGNOSIS_COMPLETE: blueprint`, or `DIAGNOSIS_COMPLETE: spec`. Uses `claude-opus-4-6`.
- **Redo Agent (EXPANDED for SVP 2.0):** Receives pipeline state summary, human error description, and current unit definition. Uses read tools to trace the error through the document hierarchy. Classifies the error source -- does NOT ask the human to self-classify. **New classifications (SVP 2.0):** `REDO_CLASSIFIED: profile_delivery` when the issue affects only Stage 5 delivery with no blueprint contract changes (examples: `vcs.commit_style`, `license.type`, `readme.audience`, `delivery.environment_recommendation`, `license.spdx_headers`). `REDO_CLASSIFIED: profile_blueprint` when the issue affects blueprint contracts (examples: `readme.sections`, `readme.custom_sections`, `testing.coverage_target`, `delivery.source_layout`). Produces dual-format output. Terminal status includes all five classifications. Uses `claude-opus-4-6`. Available during Stages 2, 3, and 4.

### Tier 3 -- Dependencies

- **Unit 9 (Preparation Script):** The task prompt content these agents receive is assembled by Unit 9.

---

## Unit 17: Support Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the Help Agent and Hint Agent. The Help Agent uses ledger-based multi-turn within sessions (cleared on dismissal); the Hint Agent operates in reactive (single-shot) or proactive (ledger multi-turn) mode. Implements spec Sections 14 and 13. Unchanged from v1.0.

### Tier 2 — Signatures

```python
from typing import Dict, Any, List

HELP_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "help_agent",
    "description": "Answers questions, collaborates on hint formulation at gates",
    "model": "claude-sonnet-4-6",
    "tools": ["Read", "Glob", "Grep"],
}

HINT_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "hint_agent",
    "description": "Provides diagnostic analysis of pipeline state",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Glob", "Grep"],
}

HELP_AGENT_STATUS: List[str] = [
    "HELP_SESSION_COMPLETE: no hint",
    "HELP_SESSION_COMPLETE: hint forwarded",
]

HINT_AGENT_STATUS: List[str] = ["HINT_ANALYSIS_COMPLETE"]

# Deliverable content constants (written by Stage 5 assembly)
HELP_AGENT_MD_CONTENT: str  # -> agents/help_agent.md
HINT_AGENT_MD_CONTENT: str  # -> agents/hint_agent.md
```

### Tier 2 — Invariants

```python
# Help agent is READ-ONLY: tools restricted to Read, Glob, Grep (+ web search via MCP)
# Help agent never modifies documents, code, tests, or pipeline state
# Help agent ledger is cleared on dismissal

# Every *_MD_CONTENT string must be a valid Claude Code agent definition
```

### Tier 3 -- Error Conditions

- No runtime errors from agent definitions. Agents produce terminal status lines.

### Tier 3 -- Behavioral Contracts

- Each `*_MD_CONTENT` string must be a complete Claude Code agent definition file with matching frontmatter and detailed behavioral instructions.
- **Help Agent (unchanged):** Read-only. Terminal status: `HELP_SESSION_COMPLETE: no hint` or `HELP_SESSION_COMPLETE: hint forwarded`. Uses `claude-sonnet-4-6`.
- **Hint Agent (unchanged):** Operates in reactive or proactive mode. Terminal status: `HINT_ANALYSIS_COMPLETE`. Uses `claude-opus-4-6`.

### Tier 3 -- Dependencies

- **Unit 9 (Preparation Script):** The task prompt content these agents receive is assembled by Unit 9.

---

## Unit 18: Utility Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the Reference Indexing Agent, Integration Test Author, and Git Repo Agent. These are single-shot utility agents. Implements spec Sections 7.2, 10, 11, and 12.1-12.4.

SVP 2.0 expansion: Git repo agent reads full profile for profile-driven delivery. Integration test author covers new SVP 2.0 cross-unit paths. Git repo agent excludes `toolchain.json` and `project_profile.json` from delivered repository. Git repo agent copies `specs/stakeholder.md` and `blueprint/blueprint.md` into `doc/` in the delivered repository.

### Tier 2 — Signatures

```python
from typing import Dict, Any, List

REFERENCE_INDEXING_FRONTMATTER: Dict[str, Any] = {
    "name": "reference_indexing_agent",
    "description": "Reads reference documents and produces structured summaries",
    "model": "claude-sonnet-4-6",
    "tools": ["Read", "Write", "Glob", "Grep"],
}

INTEGRATION_TEST_AUTHOR_FRONTMATTER: Dict[str, Any] = {
    "name": "integration_test_author",
    "description": "Generates integration tests covering cross-unit interactions",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

GIT_REPO_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "git_repo_agent",
    "description": "Creates clean git repository from verified artifacts with profile-driven delivery",
    "model": "claude-sonnet-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

REFERENCE_INDEXING_STATUS: List[str] = ["INDEXING_COMPLETE"]
INTEGRATION_TEST_AUTHOR_STATUS: List[str] = ["INTEGRATION_TESTS_COMPLETE"]
GIT_REPO_AGENT_STATUS: List[str] = ["REPO_ASSEMBLY_COMPLETE"]

# Deliverable content constants (written by Stage 5 assembly)
REFERENCE_INDEXING_AGENT_MD_CONTENT: str  # -> agents/reference_indexing_agent.md
INTEGRATION_TEST_AUTHOR_MD_CONTENT: str  # -> agents/integration_test_author.md
GIT_REPO_AGENT_MD_CONTENT: str  # -> agents/git_repo_agent.md

# Delivered repository README
README_MD_CONTENT: str  # -> README.md
```

### Tier 2 — Invariants

```python
# Git Repo Agent must use build-backend = "setuptools.build_meta" in pyproject.toml
# Git Repo Agent must never reference stub.py in entry points or imports
# Git Repo Agent must never reference src.unit_N paths in entry points or imports
# Git Repo Agent must relocate unit implementations from src/unit_N/ to blueprint file tree paths
# Git Repo Agent must rewrite cross-unit imports from src.unit_N to final module paths
# Git Repo Agent must use bare imports for inter-script references in svp/scripts/
# Git Repo Agent must ensure every directly-invoked script has if __name__ == "__main__" guard
# Git Repo Agent must create repo at {project_root.parent}/{project_name}-repo
# Git Repo Agent must verify pip install -e . succeeds
# Git Repo Agent must verify the CLI entry point loads without import errors
# Git Repo Agent entry point: svp = "svp.scripts.svp_launcher:main"
# (NEW) Git Repo Agent must exclude toolchain.json and project_profile.json from delivered repo
# (NEW) Git Repo Agent must read profile for all delivery decisions
# (NEW) Git Repo Agent must include .gitignore excluding Python build artifacts
# (NEW) Git Repo Agent must copy specs/stakeholder.md to doc/stakeholder.md in delivered repo
# (NEW) Git Repo Agent must copy blueprint/blueprint.md to doc/blueprint.md in delivered repo

# Every *_MD_CONTENT string must be a valid Claude Code agent definition
```

### Tier 3 -- Error Conditions

- No runtime errors from agent definitions. Agents produce terminal status lines.

### Tier 3 -- Behavioral Contracts

- Each `*_MD_CONTENT` string must be a complete Claude Code agent definition file with matching frontmatter and detailed behavioral instructions.
- **Reference Indexing Agent (unchanged):** Terminal status: `INDEXING_COMPLETE`. Uses `claude-sonnet-4-6`.
- **Integration Test Author (EXPANDED for SVP 2.0):** Receives stakeholder spec plus contract signatures from all units. Must cover all new SVP 2.0 cross-unit paths (spec Section 10):
  1. **Toolchain resolution chain:** Profile -> `toolchain.json` -> reader -> resolved command. Verify fully resolved commands match SVP 1.2 hardcoded strings for identical inputs.
  2. **Profile flow through preparation script:** Verify correct profile sections reach correct agents.
  3. **Blueprint checker profile validation:** Verify alignment failure when blueprint omits profile-mandated constraint.
  4. **Redo agent profile classification:** Verify `profile_delivery` for delivery-only changes, `profile_blueprint` for blueprint-influencing changes.
  5. **Gate 0.3 dispatch:** Verify state transitions for `PROFILE APPROVED` and `PROFILE REJECTED`.
  6. **Preference compliance scan:** Verify detection of banned patterns in synthetic delivered code.
  7. **Write authorization for new paths:** Verify `project_profile.json` writable during correct sub-stages and blocked otherwise. Verify `toolchain.json` always blocked.
  8. **Redo-triggered profile revision state transitions:** Verify snapshot capture, `profile_delivery` restore, `profile_blueprint` restart. Verify mini-Gate 0.3r dispatch.
  - For SVP self-builds: includes integration test exercising `svp restore` code path using bundled Game of Life example files (see v1.0 behavioral contract). Terminal status: `INTEGRATION_TESTS_COMPLETE`. Uses `claude-opus-4-6`.
- **Git Repo Agent (EXPANDED for SVP 2.0):** Creates a clean git repository at `{project_root.parent}/{project_name}-repo`. Reads `project_profile.json` (full profile) for all delivery decisions:
  - **Commit message style** (spec Section 11.2): reads `vcs.commit_style`. Conventional (default), freeform, or custom template from `vcs.commit_template`.
  - **README generation** (spec Section 11.3): reads `readme` and `delivery` sections. Section structure from `readme.sections`, custom sections from `readme.custom_sections`, audience and depth from `readme.audience` and `readme.depth`, optional content from boolean flags. Installation instructions match `delivery.environment_recommendation`, not pipeline toolchain. Mode A: carry-forward artifact. Mode B: generated from profile.
  - **Delivered source layout** (spec Section 11.4): reads `delivery.source_layout`. `"conventional"`: restructures `src/unit_N/` into `src/packagename/` with proper `__init__.py`. `"flat"`: package at repo root. `"svp_native"`: keeps `src/unit_N/` as-is. Must detect module name collisions during restructuring.
  - **Delivered dependency format** (spec Section 11.5): reads `delivery.dependency_format`. Generates `environment.yml`, `requirements.txt`, `pyproject.toml` dependencies, or multiple formats.
  - **Entry points** (spec Section 11.6): reads `delivery.entry_points`. Computes entry point module paths based on `delivery.source_layout`.
  - **SPDX license headers** (spec Section 11.7): reads `license.spdx_headers`. When true, adds SPDX comments to all delivered source files.
  - **Additional metadata** (spec Section 11.8): reads `license.additional_metadata`. Citation -> "How to Cite" section + `CITATION.cff`. Funding/acknowledgments -> "Acknowledgments" section.
  - **Gitignore** (spec Section 11.9): includes `.gitignore` excluding Python build artifacts.
  - **Excluded artifacts** (spec Section 11.10): `toolchain.json` and `project_profile.json` are pipeline-internal and do not appear in delivered repo.
  - **Documentation artifacts** (spec Section 11.11): copies `specs/stakeholder.md` to `doc/stakeholder.md` and `blueprint/blueprint.md` to `doc/blueprint.md` in the delivered repo.
  - Assembly mapping, bare imports, CLI entry point guards, runtime completeness, structural validation -- all unchanged from v1.0. Terminal status: `REPO_ASSEMBLY_COMPLETE`. Uses `claude-sonnet-4-6`.

### Tier 3 -- Dependencies

- **Unit 9 (Preparation Script):** The task prompt content these agents receive is assembled by Unit 9.

---

## Unit 19: Debug Loop Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the Bug Triage Agent and Repair Agent. The Bug Triage Agent uses ledger-based multi-turn for Socratic triage dialog. The Repair Agent is single-shot for build/environment fixes. Implements spec Section 12.9. Unchanged from v1.0.

### Tier 2 — Signatures

```python
from typing import Dict, Any, List

BUG_TRIAGE_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "bug_triage_agent",
    "description": "Conducts Socratic triage dialog for post-delivery bugs",
    "model": "claude-opus-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

REPAIR_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "repair_agent",
    "description": "Fixes build and environment issues in delivered software",
    "model": "claude-sonnet-4-6",
    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
}

BUG_TRIAGE_STATUS: List[str] = [
    "TRIAGE_COMPLETE: build_env",
    "TRIAGE_COMPLETE: single_unit",
    "TRIAGE_COMPLETE: cross_unit",
    "TRIAGE_NEEDS_REFINEMENT",
    "TRIAGE_NON_REPRODUCIBLE",
]

REPAIR_AGENT_STATUS: List[str] = [
    "REPAIR_COMPLETE",
    "REPAIR_FAILED",
    "REPAIR_RECLASSIFY",
]

# Deliverable content constants (written by Stage 5 assembly)
BUG_TRIAGE_AGENT_MD_CONTENT: str  # -> agents/bug_triage_agent.md
REPAIR_AGENT_MD_CONTENT: str  # -> agents/repair_agent.md
```

### Tier 2 — Invariants

```python
# Bug Triage Agent starts in read-only mode (before Gate 6.0 authorization)
# Bug Triage Agent uses structured response format ([QUESTION], [DECISION], [CONFIRMED])
# Repair Agent cannot modify implementation files (src/unit_N/*.py other than __init__.py)
# Repair Agent must return REPAIR_RECLASSIFY if fix requires implementation changes

# Every *_MD_CONTENT string must be a valid Claude Code agent definition
```

### Tier 3 -- Error Conditions

- No runtime errors from agent definitions. Agents produce terminal status lines.

### Tier 3 -- Behavioral Contracts

- Each `*_MD_CONTENT` string must be a complete Claude Code agent definition file with matching frontmatter and detailed behavioral instructions.
- **Bug Triage Agent (unchanged):** Conducts Socratic triage dialog. Starts in read-only mode (pre-Gate 6.0). After authorization, gains write access to `tests/regressions/` and `.svp/triage_scratch/`. Classifies bugs. Uses structured response format. Terminal status includes all five outcomes. Uses `claude-opus-4-6`.
- **Repair Agent (unchanged):** Narrow mandate for build/environment fixes. Cannot modify implementation `.py` files. Returns `REPAIR_RECLASSIFY` if implementation changes needed. Terminal status: `REPAIR_COMPLETE`, `REPAIR_FAILED`, or `REPAIR_RECLASSIFY`. Uses `claude-sonnet-4-6`.

### Tier 3 -- Dependencies

- **Unit 9 (Preparation Script):** The task prompt content these agents receive is assembled by Unit 9.

---

## Unit 20: Slash Command Files

**Artifact category:** Markdown (command files)

### Tier 1 -- Description

Defines the slash command markdown files for all human commands: `/svp:save`, `/svp:quit`, `/svp:help`, `/svp:hint`, `/svp:status`, `/svp:ref`, `/svp:redo`, `/svp:bug`, and `/svp:clean`. Each command file is injected into the conversation when the human types the command. Implements spec Section 13, including the critical Group A/B distinction (SVP 1.1 hardening). Unchanged from v1.0.

### Tier 2 — Signatures

```python
from typing import Dict, List

# Command file paths (relative to plugin commands/ directory)
COMMAND_FILES: Dict[str, str] = {
    "save": "save.md",
    "quit": "quit.md",
    "help": "help.md",
    "hint": "hint.md",
    "status": "status.md",
    "ref": "ref.md",
    "redo": "redo.md",
    "bug": "bug.md",
    "clean": "clean.md",
}

# --- Group classification (SVP 1.1 hardening invariant) ---

GROUP_A_COMMANDS: List[str] = ["save", "quit", "status", "clean"]
GROUP_B_COMMANDS: List[str] = ["help", "hint", "ref", "redo", "bug"]

# --- Prohibited scripts (SVP 1.1 hardening invariant) ---
PROHIBITED_SCRIPTS: List[str] = [
    "cmd_help.py",
    "cmd_hint.py",
    "cmd_ref.py",
    "cmd_redo.py",
    "cmd_bug.py",
]

# Deliverable content constants (one per command file)
SAVE_MD_CONTENT: str  # -> commands/save.md
QUIT_MD_CONTENT: str  # -> commands/quit.md
HELP_MD_CONTENT: str  # -> commands/help.md
HINT_MD_CONTENT: str  # -> commands/hint.md
STATUS_MD_CONTENT: str  # -> commands/status.md
REF_MD_CONTENT: str  # -> commands/ref.md
REDO_MD_CONTENT: str  # -> commands/redo.md
BUG_MD_CONTENT: str  # -> commands/bug.md
CLEAN_MD_CONTENT: str  # -> commands/clean.md
```

### Tier 2 — Invariants

```python
# Group A/B distinction (SVP 1.1 hardening -- most costly bug in 1.1)
assert not any((scripts_dir / s).exists() for s in PROHIBITED_SCRIPTS), \
    "Prohibited Group B cmd_*.py scripts must not exist"
```

### Tier 3 -- Error Conditions

- No runtime errors from command files. They are Markdown injected into conversation context.

### Tier 3 -- Behavioral Contracts

- **Group A commands** (`save`, `quit`, `status`, `clean`): Each command file directs the main session to run `PYTHONPATH=scripts python scripts/cmd_{name}.py --project-root .` and present the output. No subagent is spawned.
- **Group B commands** (`help`, `hint`, `ref`, `redo`, `bug`): Each command file directs the main session to run `python scripts/prepare_task.py --agent {role} --project-root . --output .svp/task_prompt.md` to produce the task prompt, then spawn the corresponding subagent with the task prompt verbatim. No `cmd_*.py` script is invoked.
- `/svp:clean` must be invoked as `PYTHONPATH=scripts python scripts/cmd_clean.py` so library imports resolve correctly.
- `/svp:ref` is available during Stages 0, 1, and 2 only.
- `/svp:redo` is available during Stages 2, 3, and 4.
- `/svp:bug` is available only after Stage 5 completion.
- Command file content must be written as explicit, unambiguous directives.

### Tier 3 -- Dependencies

- **Unit 10 (Routing Script):** Group B commands ultimately interact with the routing/dispatch system.
- **Unit 11 (Command Logic Scripts):** Group A commands invoke the `cmd_*.py` scripts defined in Unit 11.

---

## Unit 21: Orchestration Skill

**Artifact category:** Markdown (SKILL.md)

### Tier 1 -- Description

Defines the SKILL.md file that constrains the main session's orchestration behavior. This is the primary behavioral instruction for the orchestration layer -- it defines the six-step mechanical action cycle, verbatim task prompt relay, and deferral of human input during autonomous sequences. Implements spec Section 3.6. Unchanged from v1.0.

### Tier 2 — Signatures

```python
from typing import Dict, Any

# Skill file location
SKILL_PATH: str = "skills/orchestration/SKILL.md"

# Six-step action cycle (the complete main session behavior)
ACTION_CYCLE_STEPS: list = [
    "1. Run the routing script -> receive structured action block",
    "2. Run the PREPARE command (if present) -> produces task/gate prompt file",
    "3. Execute the ACTION (invoke agent / run command / present gate)",
    "4. Write the result to .svp/last_status.txt",
    "5. Run the POST command (if present) -> updates pipeline state",
    "6. Go to step 1",
]

# Deliverable content constant (written by Stage 5 assembly)
ORCHESTRATION_SKILL_MD_CONTENT: str  # -> skills/orchestration/SKILL.md
```

### Tier 2 — Invariants

```python
# The skill must instruct verbatim task prompt relay
# The skill must instruct deferral of human input during autonomous sequences
# The skill must reference the routing script as the sole decision-maker

assert all(step_keyword in ORCHESTRATION_SKILL_MD_CONTENT
           for step_keyword in ["routing script", "PREPARE", "ACTION", "last_status.txt", "POST"])
```

### Tier 3 -- Error Conditions

- No runtime errors from the skill file. It is Markdown loaded as behavioral context.

### Tier 3 -- Behavioral Contracts

- The skill file defines the main session's complete behavioral protocol.
- `ORCHESTRATION_SKILL_MD_CONTENT` must be the complete SVP orchestration protocol describing: the six-step action cycle, how to handle each action type, how to construct status lines, how to relay task prompts verbatim, gate presentation rules, and session boundary handling.

### Tier 3 -- Dependencies

- **Unit 10 (Routing Script):** The skill references the routing script's output format.

---

## Unit 22: Project Templates

**Artifact category:** Mixed (Python template, JSON defaults, text)

### Tier 1 -- Description

Defines the template files used during project bootstrap: the CLAUDE.md generator, the default `svp_config.json`, the initial `pipeline_state.json`, the `README_SVP.txt` protection notice, and the default toolchain configuration file. These are copied or generated into new project workspaces by the SVP launcher. Implements spec Sections 3.6 (CLAUDE.md), 14.1 (default config), 14.4 (initial state), 15 (README_SVP.txt), and 6.5 (toolchain defaults).

SVP 2.0 expansion: adds `toolchain_defaults/python_conda_pytest.json` containing the pipeline toolchain configuration.

### Tier 2 — Signatures

```python
from typing import Dict, Any
from pathlib import Path

# claude_md.py
def generate_claude_md(project_name: str, project_root: Path) -> str: ...

# Template file paths
DEFAULT_CONFIG_TEMPLATE: str = "templates/svp_config_default.json"
INITIAL_STATE_TEMPLATE: str = "templates/pipeline_state_initial.json"
README_SVP_TEMPLATE: str = "templates/readme_svp.txt"
TOOLCHAIN_DEFAULT_TEMPLATE: str = "toolchain_defaults/python_conda_pytest.json"

# Deliverable content constants (written by Stage 5 assembly)
CLAUDE_MD_PY_CONTENT: str  # -> scripts/templates/claude_md.py
SVP_CONFIG_DEFAULT_JSON_CONTENT: str  # -> scripts/templates/svp_config_default.json
PIPELINE_STATE_INITIAL_JSON_CONTENT: str  # -> scripts/templates/pipeline_state_initial.json
README_SVP_TXT_CONTENT: str  # -> scripts/templates/readme_svp.txt
TOOLCHAIN_DEFAULT_JSON_CONTENT: str  # -> scripts/toolchain_defaults/python_conda_pytest.json

# Bundled example project (carry-forward from v1.1, SVP self-build only)
GOL_STAKEHOLDER_SPEC_CONTENT: str  # -> examples/game-of-life/stakeholder_spec.md
GOL_BLUEPRINT_CONTENT: str  # -> examples/game-of-life/blueprint.md
GOL_PROJECT_CONTEXT_CONTENT: str  # -> examples/game-of-life/project_context.md
```

### Tier 2 — Invariants

```python
# CLAUDE.md must instruct:
# - Run routing script on session start
# - Execute routing script output exactly
# - Verbatim task prompt relay
# - Do not improvise pipeline flow
# - Defer human input during autonomous sequences

# Default config must match DEFAULT_CONFIG from Unit 1
# Initial state must match create_initial_state output from Unit 2

# Template content strings must produce valid files
assert "def generate_claude_md" in CLAUDE_MD_PY_CONTENT, "claude_md.py must have render function"
assert '"stage"' in PIPELINE_STATE_INITIAL_JSON_CONTENT, "Initial state must have stage field"
assert '"skip_permissions"' in SVP_CONFIG_DEFAULT_JSON_CONTENT, "Config must have skip_permissions"
assert "SVP-MANAGED" in README_SVP_TXT_CONTENT, "README must have protection notice"

# Toolchain default must match the schema from spec Section 6.5
assert '"toolchain_id"' in TOOLCHAIN_DEFAULT_JSON_CONTENT, \
    "Toolchain default must have toolchain_id"
assert '"python_conda_pytest"' in TOOLCHAIN_DEFAULT_JSON_CONTENT, \
    "Toolchain default must be python_conda_pytest"
assert '"environment"' in TOOLCHAIN_DEFAULT_JSON_CONTENT, \
    "Toolchain default must have environment section"
assert '"testing"' in TOOLCHAIN_DEFAULT_JSON_CONTENT, \
    "Toolchain default must have testing section"
assert '"framework_packages"' in TOOLCHAIN_DEFAULT_JSON_CONTENT, \
    "Toolchain default must have framework_packages"
assert '"collection_error_indicators"' in TOOLCHAIN_DEFAULT_JSON_CONTENT, \
    "Toolchain default must have collection_error_indicators"

# Bundled example (carry-forward, SVP self-build only)
assert "Conway" in GOL_STAKEHOLDER_SPEC_CONTENT, "GoL spec must describe Game of Life"
assert "## Unit 1" in GOL_BLUEPRINT_CONTENT, "GoL blueprint must have unit decomposition"
assert "Game of Life" in GOL_PROJECT_CONTEXT_CONTENT, "GoL context must reference Game of Life"
```

### Tier 3 -- Error Conditions

- `ValueError`: "Project name must not be empty" -- when `generate_claude_md` receives an empty project name.

### Tier 3 -- Behavioral Contracts

- `generate_claude_md` produces a complete CLAUDE.md file content with the project name, the six-step action cycle instruction, verbatim relay instruction, and all behavioral constraints from spec Section 3.6 Layer 1.
- `DEFAULT_CONFIG_TEMPLATE` is a JSON file containing the same defaults as `DEFAULT_CONFIG` from Unit 1.
- `INITIAL_STATE_TEMPLATE` is a JSON file matching the output of `create_initial_state` from Unit 2 (with a placeholder for project_name). Must include `redo_triggered_from: null`.
- `README_SVP_TEMPLATE` explains that this is an SVP-managed project.
- `TOOLCHAIN_DEFAULT_JSON_CONTENT` must be valid JSON matching the complete toolchain schema from spec Section 6.5: `toolchain_id` ("python_conda_pytest"), `environment` (tool, create, run_prefix, install, install_dev, remove), `testing` (tool, run, run_coverage, framework_packages, file_pattern, collection_error_indicators, pass_fail_pattern), `packaging` (tool, manifest_file, build_backend, validate_command), `vcs` (tool, commands), `language` (name, extension, version_constraint, signature_parser, stub_body), `file_structure` (source_dir_pattern, test_dir_pattern, source_extension, test_extension). All command templates must use named placeholders (`{env_name}`, `{python_version}`, `{run_prefix}`, `{test_path}`, `{module}`, `{packages}`, `{files}`, `{message}`).
- `GOL_*_CONTENT` -- carry-forward artifacts from v1.1, reproduced exactly.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Default config template must match Unit 1's `DEFAULT_CONFIG`.
- **Unit 2 (Pipeline State Schema):** Initial state template must match Unit 2's `create_initial_state` output.
- **Unit 10 (Routing Script):** CLAUDE.md references the routing script by name.

---

## Unit 23: Plugin Manifest and Structural Validation

**Artifact category:** JSON + Python script (compliance_scan.py)

### Tier 1 -- Description

Defines the `plugin.json` manifest for the SVP plugin subdirectory and the `marketplace.json` catalog at the repository root. Includes structural validation logic for the plugin directory layout. Also includes the delivery compliance scan (Layer 3 of preference enforcement) that validates delivered code against profile preferences during Stage 5 structural validation. Implements spec Sections 1.4, 11.1, and 12.3.

SVP 2.0 expansion: structural validation includes `toolchain_defaults/` directory. Delivery compliance scan added.

### Tier 2 — Signatures

```python
from typing import Dict, Any, List
from pathlib import Path

# Plugin manifest schema
PLUGIN_JSON: Dict[str, Any] = {
    "name": "svp",
    "version": "2.0.0",
    "description": "Stratified Verification Pipeline - deterministically orchestrated software development",
}

# Marketplace catalog schema
MARKETPLACE_JSON: Dict[str, Any] = {
    "name": "svp",
    "owner": {"name": "SVP"},
    "plugins": [
        {
            "name": "svp",
            "source": "./svp",
            "description": "Stratified Verification Pipeline -- deterministically orchestrated, sequentially gated development for domain experts",
            "version": "2.0.0",
            "author": {"name": "SVP"},
        }
    ]
}

def validate_plugin_structure(repo_root: Path) -> List[str]: ...

# Deliverable content constants (written by Stage 5 assembly)
PLUGIN_JSON_CONTENT: str  # -> svp/.claude-plugin/plugin.json
MARKETPLACE_JSON_CONTENT: str  # -> .claude-plugin/marketplace.json

# --- Delivery compliance scan (compliance_scan.py) (NEW) ---

def run_compliance_scan(
    project_root: Path,
    delivered_src_dir: Path,
    delivered_tests_dir: Path,
    profile: Dict[str, Any],
) -> List[Dict[str, Any]]: ...

def _get_banned_patterns(
    environment_recommendation: str,
) -> List[Dict[str, str]]: ...

def _scan_file_ast(
    file_path: Path,
    banned_patterns: List[Dict[str, str]],
) -> List[Dict[str, Any]]: ...

def compliance_scan_main() -> None: ...
```

### Tier 2 — Invariants

```python
# Structural validation checks
assert (repo_root / ".claude-plugin" / "marketplace.json").exists()
assert (repo_root / "svp" / ".claude-plugin" / "plugin.json").exists()

for component in ["agents", "commands", "hooks", "scripts", "skills"]:
    assert (repo_root / "svp" / component).is_dir()
    assert not (repo_root / component).is_dir()

# (NEW) Toolchain defaults directory must exist
assert (repo_root / "svp" / "scripts" / "toolchain_defaults").is_dir(), \
    "toolchain_defaults/ must exist in scripts/"
assert (repo_root / "svp" / "scripts" / "toolchain_defaults" / "python_conda_pytest.json").exists(), \
    "python_conda_pytest.json must exist in toolchain_defaults/"

assert '"name": "svp"' in PLUGIN_JSON_CONTENT
assert '"plugins"' in MARKETPLACE_JSON_CONTENT
assert '"source": "./svp"' in MARKETPLACE_JSON_CONTENT

# Compliance scan reads environment_recommendation from profile
assert "delivery" in profile and "environment_recommendation" in profile["delivery"], \
    "Compliance scan requires delivery.environment_recommendation in profile"
```

### Tier 3 -- Error Conditions

- `ValueError`: "Plugin structure validation failed: {details}" -- when `validate_plugin_structure` finds violations.

### Tier 3 -- Behavioral Contracts

- `plugin.json` lives at `svp/.claude-plugin/plugin.json`.
- `marketplace.json` lives at `.claude-plugin/marketplace.json` at the repository root level.
- `validate_plugin_structure` checks all structural requirements including `toolchain_defaults/` directory with `python_conda_pytest.json`.
- `PLUGIN_JSON_CONTENT` and `MARKETPLACE_JSON_CONTENT` -- valid JSON matching their schemas. Version is `"2.0.0"`.

**Delivery compliance scan (NEW -- Layer 3):**
- `run_compliance_scan` reads `delivery.environment_recommendation` from the profile and scans delivered Python source files in the given directories for preference violations. Returns a list of violation dicts, each containing `file`, `line`, `pattern`, `context`.
- `_get_banned_patterns` returns the banned pattern set for the given environment recommendation per spec Section 11.1. The exact banned pattern rules are:
  - **For `conda` recommendation:** Ban command strings starting with `pip `, `pip install`, `pip3 install`, `python `, `pytest ` that are NOT preceded by `conda run -n {env_name}`. The check is positional: the banned token must appear at the start of the command string or immediately after a shell operator (`&&`, `||`, `;`, `|`), and the `conda run -n {env_name}` prefix must appear before it in the same command segment.
  - **For `pyenv`, `venv`, or `poetry` recommendation:** Ban command strings containing `conda create`, `conda run`, `conda install`, `conda env`. These are exact substring matches within command arguments.
  - **For `none` recommendation:** Ban all patterns from both the conda and pyenv/venv/poetry sets above (both bare pip/python/pytest commands and all conda commands).
- `_scan_file_ast` parses a single Python file's AST and inspects subprocess invocation calls (`subprocess.run`, `subprocess.call`, `subprocess.Popen`, `os.system`) for command strings containing banned patterns. Does not flag string literals in non-executable contexts. Returns violations found.
- `compliance_scan_main` is the CLI entry point. Reads profile via Unit 1, determines delivered repo paths, calls `run_compliance_scan`, emits `COMMAND_SUCCEEDED` if no violations, `COMMAND_FAILED: {count} violations found` otherwise.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Reads profile via `load_profile` for delivery preferences used by the compliance scan.
- All preceding units (for structural validation).

---

## Unit 24: SVP Launcher

**Artifact category:** Python script (standalone CLI tool)

### Tier 1 -- Description

The standalone `svp` CLI tool that manages the complete SVP session lifecycle: prerequisite verification, project directory creation, script copying, CLAUDE.md generation, filesystem permission management, session cycling, and resume. The launcher runs before Claude Code starts and is not a plugin component. Delivered at `svp/scripts/svp_launcher.py` in the repository (entry point: `svp.scripts.svp_launcher:main`).

**Self-containment requirement:** The launcher must be a single, self-contained Python file with NO imports from other SVP units.

SVP 2.0 expansion: copies `toolchain.json` from `toolchain_defaults/` during project creation. Copies regression test files from `tests/regressions/` in the plugin to the project workspace.

### Tier 2 — Signatures

```python
#!/usr/bin/env python3
from typing import Optional, List, Tuple
from pathlib import Path
from datetime import datetime, timezone
import subprocess
import sys
import argparse
import shutil
import os
import json
import stat
import time

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RESTART_SIGNAL_FILE: str = ".svp/restart_signal"
STATE_FILE: str = "pipeline_state.json"
CONFIG_FILE: str = "svp_config.json"
TOOLCHAIN_FILE: str = "toolchain.json"
SVP_DIR: str = ".svp"
MARKERS_DIR: str = ".svp/markers"
CLAUDE_MD_FILE: str = "CLAUDE.md"
README_SVP_FILE: str = "README_SVP.txt"
SVP_ENV_VAR: str = "SVP_PLUGIN_ACTIVE"

PROJECT_DIRS: List[str] = [
    ".svp", ".svp/markers", ".claude", "scripts", "ledgers",
    "logs", "logs/rollback", "specs", "specs/history",
    "blueprint", "blueprint/history", "references", "references/index",
    "src", "tests", "tests/regressions", "data",
]

# ---------------------------------------------------------------------------
# Plugin discovery
# ---------------------------------------------------------------------------

def _find_plugin_root() -> Optional[Path]: ...
def _is_svp_plugin_dir(path: Path) -> bool: ...

# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _print_header(text: str) -> None: ...
def _print_status(name: str, passed: bool, message: str) -> None: ...
def _print_transition(message: str) -> None: ...

# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace: ...

# ---------------------------------------------------------------------------
# Prerequisite checking (8 checks)
# ---------------------------------------------------------------------------

def check_claude_code() -> Tuple[bool, str]: ...
def check_svp_plugin() -> Tuple[bool, str]: ...
def check_api_credentials() -> Tuple[bool, str]: ...
def check_conda() -> Tuple[bool, str]: ...
def check_python() -> Tuple[bool, str]: ...
def check_pytest() -> Tuple[bool, str]: ...
def check_git() -> Tuple[bool, str]: ...
def check_network() -> Tuple[bool, str]: ...
def run_all_prerequisites() -> List[Tuple[str, bool, str]]: ...

# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------

def create_project_directory(project_name: str, parent_dir: Path) -> Path: ...
def copy_scripts_to_workspace(plugin_root: Path, project_root: Path) -> None: ...
def copy_toolchain_default(plugin_root: Path, project_root: Path) -> None: ...
def copy_regression_tests(plugin_root: Path, project_root: Path) -> None: ...
def copy_hooks(plugin_root: Path, project_root: Path) -> None: ...
def generate_claude_md(project_root: Path, project_name: str) -> None: ...
def _generate_claude_md_fallback(project_name: str) -> str: ...
def write_initial_state(project_root: Path, project_name: str) -> None: ...
def write_default_config(project_root: Path) -> None: ...
def write_readme_svp(project_root: Path) -> None: ...

# ---------------------------------------------------------------------------
# Filesystem permissions
# ---------------------------------------------------------------------------

def set_filesystem_permissions(project_root: Path, read_only: bool) -> None: ...

# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------

def launch_claude_code(project_root: Path, plugin_dir: Path) -> int: ...
def detect_restart_signal(project_root: Path) -> Optional[str]: ...
def clear_restart_signal(project_root: Path) -> None: ...
def run_session_loop(project_root: Path, plugin_dir: Path) -> int: ...

# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------

def detect_existing_project(directory: Path) -> bool: ...
def resume_project(project_root: Path, plugin_dir: Path) -> int: ...

# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _handle_new_project(args: argparse.Namespace, plugin_dir: Path) -> int: ...
def _handle_restore(args: argparse.Namespace, plugin_dir: Path) -> int: ...
def _handle_resume(plugin_dir: Path) -> int: ...

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int: ...
```

### Tier 2 — Invariants

```python
# Cross-unit invariant: SVP_PLUGIN_ACTIVE
assert SVP_ENV_VAR == "SVP_PLUGIN_ACTIVE"

# Exactly 8 prerequisite checks, in order
assert len(run_all_prerequisites()) == 8

# PROJECT_DIRS must include all directories from spec Section 6.6
assert ".svp" in PROJECT_DIRS
assert "scripts" in PROJECT_DIRS
assert "src" in PROJECT_DIRS
assert "tests" in PROJECT_DIRS
assert "tests/regressions" in PROJECT_DIRS

# Self-containment: no imports from other SVP modules

# Delivery path: svp/scripts/svp_launcher.py
# Entry point: svp = "svp.scripts.svp_launcher:main"

# Environment variable propagation
# SVP_PLUGIN_ACTIVE must be set in the subprocess environment, never on launcher's own os.environ
```

### Tier 3 -- Error Conditions

- `FileExistsError`: "Project directory already exists: {path}" -- from `create_project_directory`.
- `RuntimeError`: "Plugin scripts directory not found at {path}" -- from `copy_scripts_to_workspace`.
- `RuntimeError`: "Toolchain default file not found at {path}" -- from `copy_toolchain_default` when `toolchain_defaults/python_conda_pytest.json` is missing.
- `RuntimeError`: "Session launch failed: Claude Code executable not found" -- from `launch_claude_code`.
- `RuntimeError`: "Session launch failed: {details}" -- from `launch_claude_code` for other subprocess errors.

### Tier 3 -- Behavioral Contracts

**Plugin discovery** -- unchanged from v1.0.

**Output formatting** -- unchanged from v1.0.

**CLI parsing** -- unchanged from v1.0.

**Prerequisite checks** -- unchanged from v1.0 (8 checks).

**Project setup (EXPANDED for SVP 2.0):**
- `create_project_directory` -- unchanged except `PROJECT_DIRS` includes `tests/regressions`.
- `copy_scripts_to_workspace` -- unchanged from v1.0.
- `copy_toolchain_default` (NEW): copies `scripts/toolchain_defaults/python_conda_pytest.json` from the plugin to `toolchain.json` at the project root. Raises `RuntimeError` if the source file does not exist.
- `copy_regression_tests` (NEW): copies all `.py` files from `tests/regressions/` in the plugin to `tests/regressions/` in the project workspace. If the plugin's `tests/regressions/` directory does not exist, logs a warning and continues (non-fatal for general projects that may not have regression tests).
- `copy_hooks` -- unchanged from v1.0 (rewrites hook script paths to `.claude/scripts/`).
- `generate_claude_md`, `_generate_claude_md_fallback`, `write_initial_state`, `write_default_config`, `write_readme_svp` -- unchanged except `write_initial_state` includes `redo_triggered_from: null` in the initial state.

**Filesystem permissions** -- unchanged from v1.0.

**Session lifecycle** -- unchanged from v1.0.

**Resume** -- unchanged from v1.0.

**Command handlers (EXPANDED for SVP 2.0):**
- `_handle_new_project`: creates directory structure, copies scripts, **copies toolchain default** (NEW), **copies regression tests** (NEW), generates CLAUDE.md, writes initial state, writes default config, writes README_SVP.txt, copies hooks, prints progress status for each step, then calls `run_session_loop`.
- `_handle_restore`: validates that `--spec` and `--blueprint` files exist. Creates directory, copies scripts, **copies toolchain default** (NEW), **copies regression tests** (NEW), generates CLAUDE.md, writes default config, writes README_SVP.txt, copies hooks, injects the spec, injects the blueprint, optionally injects context, writes pipeline state at `pre_stage_3`, then calls `run_session_loop`.
- `_handle_resume` -- unchanged from v1.0.

**Entry point** -- unchanged from v1.0.

### Tier 3 -- Dependencies

- **Unit 12 (Hook Configurations):** The launcher copies hook files during project creation and restore. The `SVP_PLUGIN_ACTIVE` variable name must match Unit 12's `non_svp_protection.sh`.
- **Unit 22 (Project Templates):** Template files are loaded at runtime from `scripts/templates/` and `scripts/toolchain_defaults/`. The launcher has complete inline fallbacks for all templates except the toolchain default (which must exist).

Note: Unit 24 does NOT depend on Units 2 or 3 at the Python import level (self-containment invariant).

---

*End of blueprint.*
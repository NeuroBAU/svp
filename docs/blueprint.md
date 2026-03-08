# SVP -- Stratified Verification Pipeline

## Technical Blueprint v1.0

**Date:** 2026-02-28
**Decomposes:** Stakeholder Specification v6.0
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
|   |   |-- cmd_save.py                  <- Unit 11
|   |   |-- cmd_quit.py                  <- Unit 11
|   |   |-- cmd_status.py                <- Unit 11
|   |   |-- cmd_clean.py                 <- Unit 11
|   |   |-- svp_launcher.py              <- Unit 24
|   |   +-- templates/                   <- Unit 22
|   |       |-- claude_md.py
|   |       |-- svp_config_default.json
|   |       |-- pipeline_state_initial.json
|   |       +-- readme_svp.txt
|   +-- README.md
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

**Critical assembly rule (learned from SVP 1.2 implementation):** During Stage 5 assembly, unit implementations must be relocated from their workspace paths (`src/unit_N/`) to their final paths as shown in this file tree. The file tree annotations (`<- Unit N`) are the authoritative mapping. The workspace `src/unit_N/stub.py` structure is never reproduced in the delivered repository. All imports referencing `src.unit_N` or `stub` must be rewritten to use final module paths — but scripts delivered to `svp/scripts/` must use **bare imports** (e.g., `from pipeline_state import load_state`), NOT package imports (e.g., `from svp.scripts.pipeline_state import load_state`), because the launcher copies these scripts to project workspaces where they run with `PYTHONPATH=scripts`. The `svp.scripts.X` form is used ONLY in `pyproject.toml` entry points. Every script that is invoked directly via `python scripts/X.py` must include an `if __name__ == "__main__"` guard. See spec Section 12.1.1.

**Scripts synchronization rule:** Six units exist as both a canonical `src/unit_N/stub.py` and a runtime `scripts/` copy: Unit 1 (`svp_config.py`), Unit 2 (`pipeline_state.py`), Unit 4 (`ledger_manager.py`), Unit 5 (`blueprint_extractor.py`), Unit 8 (`hint_prompt_assembler.py`), and Unit 9 (`prepare_task.py`). The `src/unit_N/stub.py` is always canonical; the `scripts/` copy must match. When a canonical stub changes — especially exported constants like `KNOWN_AGENT_TYPES` or public assembler functions — the corresponding `scripts/` file must be updated in the same commit. The routing script checks `KNOWN_AGENT_TYPES` between `src/unit_9/stub.py` and `scripts/prepare_task.py` at startup and emits a stderr warning if they diverge.

**CLI wrapper rule (learned from SVP 1.2.1 bug triage):** Three units produce both a library module and one or more CLI wrapper scripts: Unit 6 (`stub_generator.py` + `generate_stubs.py`), Unit 7 (`dependency_extractor.py` + `setup_infrastructure.py`), and Unit 10 (`routing.py` + `update_state.py` + `run_tests.py`). CLI wrapper scripts must be **thin wrappers that delegate to the canonical functions** defined in the library module — they must NOT reimplement dispatch logic, test execution, or infrastructure orchestration inline. Specifically: `update_state.py` must import and call `update_state_main()` from `routing`; `run_tests.py` must import and call `run_tests_main()` from `routing`; `generate_stubs.py` must use `write_stub_file()` and `write_upstream_stubs()` from `stub_generator`; `setup_infrastructure.py` must use `run_infrastructure_setup()` from `dependency_extractor` (which in turn must use the canonical API: `extract_all_imports`, `map_imports_to_packages`, `derive_env_name`, `create_conda_environment`, `validate_imports`, `create_project_directories`). Reimplementing logic in CLI wrappers creates sync drift that is invisible to the scripts synchronization check.

**Cross-unit CLI contract (learned from SVP 1.2.1 bug triage):** Unit 10 (routing script) generates PREPARE and POST command strings that are executed as shell commands. The argument syntax in these commands constitutes a cross-unit contract: the receiving script (Unit 9 for PREPARE, Unit 10's own `update_state_main` for POST) must accept every argument that Unit 10 generates. Specifically, `prepare_task.py` must accept `--output` (override output path), and `update_state.py` must accept `--gate` (gate ID for gate response dispatch). When adding arguments to generated command strings in Unit 10, the receiving script's argparse must be updated in the same commit.

**CLI wrapper status line contract (learned from SVP 1.2.1 bug triage):** CLI wrapper scripts invoked as `run_command` actions must emit status lines from the vocabulary defined in Unit 10's `COMMAND_STATUS_PATTERNS`: `COMMAND_SUCCEEDED` on success, `COMMAND_FAILED: [details]` on failure. Custom status strings (e.g. `INFRASTRUCTURE_SETUP_COMPLETE`) are not recognized by `dispatch_command_status()` and cause a `ValueError`. This applies to `setup_infrastructure.py` (Unit 7) and `generate_stubs.py` (Unit 6). Test-runner wrappers (`run_tests.py`) use the `TESTS_PASSED`/`TESTS_FAILED`/`TESTS_ERROR` patterns instead.

**Mixed-artifact unit convention:** Units whose artifact category includes Markdown, JSON, shell scripts, or other non-Python deliverables must produce the complete content of each deliverable file as a Python string constant in their `src/unit_N/stub.py` implementation. The naming convention is `{FILENAME_UPPER}_CONTENT: str` — for example, `SETUP_AGENT_MD_CONTENT: str` for `agents/setup_agent.md`. The git repo agent extracts these string constants during assembly and writes them as files to the paths specified in the blueprint file tree. Tests verify these string constants contain the required structure and content. This convention ensures non-Python deliverables go through the same test-stub-implement-verify cycle as Python code.

**Claude Code agent definition format:** Agent `.md` files use this structure:
```
---
name: agent_name
model: model-id
tools: [Tool1, Tool2, ...]
---

[Agent behavioral instructions — the system prompt for this subagent]
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
Unit 7:  Dependency Extractor and Import Validator         (no deps)
Unit 8:  Hint Prompt Assembler                            depends on: 1
Unit 9:  Preparation Script                               depends on: 2, 4, 5, 8
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
Unit 23: Plugin Manifest                                  depends on: (all preceding)
Unit 24: SVP Launcher                                     depends on: 12, 22
```

### SVP 1.2 Scope

SVP 1.2 addresses two bugs and hardens three previously fixed bugs:

1. **Bug 1 (Gate status string mismatch):** Canonical gate status string vocabulary defined as a data constant in Unit 10, used by Units 9 and 10. Human-typed option text is the status string -- no translation layer.
2. **Bug 2 (Hook permission freeze after Stage 5):** Explicit debug permission reset via `debug_session.authorized` field. Unit 3 provides the transition, Unit 10 dispatches it, Unit 12 reads it.
3. **SVP 1.1 Hardening -- `SVP_PLUGIN_ACTIVE`:** Canonical environment variable name shared as a cross-unit invariant between Units 12 and 24.
4. **SVP 1.1 Hardening -- `--dangerously-skip-permissions`:** Controlled by `skip_permissions` config key (Unit 1), read by Unit 24 (Launcher).
5. **SVP 1.1 Hardening -- Command Group A/B:** Enforced in Unit 20 with explicit prohibition of `cmd_help.py`, `cmd_hint.py`, `cmd_ref.py`, `cmd_redo.py`, `cmd_bug.py`.

Prompt caching is out of scope for SVP 1.2.

---

## Unit Definitions

---

## Unit 1: SVP Configuration

**Artifact category:** Python script

### Tier 1 -- Description

Defines the `svp_config.json` schema and provides functions for loading, validating, and accessing all tunable parameters. This is the foundational data contract -- nearly every deterministic component reads configuration through this unit's interface. Implements spec Section 22.1.

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any
from pathlib import Path

# --- Data contract: configuration schema ---

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
```

### Tier 3 -- Error Conditions

- `FileNotFoundError`: "Config file not found at {path}" -- when `svp_config.json` does not exist at project root. `load_config` returns defaults when file is absent (no error for missing file on first load).
- `json.JSONDecodeError`: "Config file is not valid JSON" -- when file exists but is malformed.
- `ValueError`: "Invalid config: {details}" -- when `validate_config` finds a structural problem (missing required keys, wrong types).

### Tier 3 -- Behavioral Contracts

- `load_config` returns the merged result of file content over defaults -- missing keys in the file are filled from `DEFAULT_CONFIG`.
- `load_config` on a non-existent file returns a copy of `DEFAULT_CONFIG` without error.
- `validate_config` returns an empty list when config is valid.
- `validate_config` returns a list of human-readable error strings for each violation found.
- `get_model_for_agent` returns the agent-specific model if configured, otherwise the `models.default` value.
- `get_effective_context_budget` returns the `context_budget_override` when set and non-null, otherwise computes from the smallest model context window minus 20,000 tokens overhead.
- `write_default_config` writes `DEFAULT_CONFIG` as formatted JSON to `{project_root}/svp_config.json` and returns the path.
- Config changes made by the human take effect on next load -- no caching across invocations.

### Tier 3 -- Dependencies

None. This is the most foundational unit.

---

## Unit 2: Pipeline State Schema and Core Operations

**Artifact category:** Python script

### Tier 1 -- Description

Defines the complete `pipeline_state.json` schema and provides creation, reading, writing, structural validation, and state recovery from completion markers. This is the single source of truth for deterministic routing, session recovery, and status reporting. Implements spec Sections 22.2, 6.1 (resume/recovery), and 22.3 (resume behavior).

The spec (Section 22.2) states "the complete schema is a blueprint concern." This unit defines that schema, including the `debug_session` object required for the debug permission reset (Bug 2 fix).

### Tier 2 — Signatures

```python
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
from datetime import datetime

# --- Data contract: pipeline state schema ---

STAGES: List[str] = ["0", "1", "2", "pre_stage_3", "3", "4", "5"]

SUB_STAGES_STAGE_0: List[str] = ["hook_activation", "project_context"]

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

# Post-conditions for load_state
assert result.stage in STAGES, "Stage must be a valid stage identifier"
assert result.red_run_retries >= 0, "Red run retries must be non-negative"
assert result.alignment_iteration >= 0, "Alignment iteration must be non-negative"

# Post-conditions for save_state
assert (project_root / "pipeline_state.json").exists(), "State file must exist after save"
```

### Tier 3 -- Error Conditions

- `FileNotFoundError`: "State file not found at {path}" -- when `load_state` is called and `pipeline_state.json` does not exist.
- `json.JSONDecodeError`: "State file is not valid JSON" -- when file is malformed.
- `ValueError`: "Invalid state: {details}" -- when `validate_state` finds structural problems.

### Tier 3 -- Behavioral Contracts

- `create_initial_state` returns a `PipelineState` at `stage: "0"`, `sub_stage: "hook_activation"` with all counters at zero, `debug_session: None`, and `debug_history: []`.
- `load_state` deserializes `pipeline_state.json` and returns a validated `PipelineState`, including deserialization of the `debug_session` object when present.
- `save_state` atomically writes the state (write to temp file, rename) to prevent corruption on interruption.
- `validate_state` checks structural integrity: valid stage, valid sub-stage for the stage, non-negative counters, verified_units entries have required fields, pass_history entries have required fields, debug_session is either None or a valid DebugSession, debug_history entries have required fields.
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

Validates preconditions and executes all state transitions: stage advancement, unit completion, fix ladder progression, pass history recording, unit-level rollback, document versioning (copy to history, write diff summary), and debug session lifecycle (enter, authorize, exit). This unit contains the most complex business logic among the deterministic scripts -- it is the primary stage-gating mechanism (spec Section 3.6). Implements spec Sections 3.6 (state management), 10.10 (unit completion), 13 (`/svp:redo` rollback), 23 (document version tracking), 8.3 (alignment loop iteration tracking), and 12.9.1 (debug permission reset).

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

def reset_fix_ladder(state: PipelineState) -> PipelineState: ...

def increment_red_run_retries(state: PipelineState) -> PipelineState: ...

def reset_red_run_retries(state: PipelineState) -> PipelineState: ...

def increment_alignment_iteration(state: PipelineState) -> PipelineState: ...

def reset_alignment_iteration(state: PipelineState) -> PipelineState: ...

def record_pass_end(state: PipelineState, reason: str) -> PipelineState: ...

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

def update_state_from_status(
    state: PipelineState,
    status_file: Path,
    unit: Optional[int],
    phase: str,
    project_root: Path,
) -> PipelineState: ...
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
```

### Tier 3 -- Error Conditions

- `TransitionError`: "Cannot advance from stage {X}: preconditions not met -- {details}" -- when `advance_stage` is called but the stage's exit criteria are not satisfied.
- `TransitionError`: "Cannot complete unit {N}: tests have not passed" -- when `complete_unit` is called without test passage evidence.
- `TransitionError`: "Cannot advance fix ladder to {position}: current position {current} does not permit this transition" -- when the ladder position sequence is violated.
- `TransitionError`: "Alignment iteration limit reached ({limit})" -- when `increment_alignment_iteration` detects the limit is exceeded (reads limit from config via Unit 1).
- `TransitionError`: "Cannot enter debug session: pipeline is not at Stage 5" -- when `enter_debug_session` is called outside Stage 5.
- `TransitionError`: "Cannot enter debug session: a debug session is already active" -- when a second debug session is attempted.
- `TransitionError`: "Cannot authorize debug session: no active session" -- when `authorize_debug_session` is called with no debug session.
- `FileNotFoundError`: "Document to version not found: {path}" -- when `version_document` receives a non-existent document path.

### Tier 3 -- Behavioral Contracts

- `advance_stage` moves the state to the next stage in the defined sequence. It validates that the current stage's exit criteria are met before transitioning.
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
- `update_state_from_status` reads `.svp/last_status.txt`, parses the terminal status line or command result status line, and calls the appropriate transition function based on the phase parameter. This is the entry point called by POST commands.
- All transition functions return a new `PipelineState` -- they do not mutate the input. The caller is responsible for saving.
- `advance_fix_ladder` enforces the valid ladder sequence: `None -> fresh_test -> hint_test` (test ladder), `None -> fresh_impl -> diagnostic -> diagnostic_impl` (implementation ladder). Invalid transitions raise `TransitionError`. **Caller responsibility:** callers must check `state.fix_ladder_position` before calling and must pass the next valid target for the current position -- not a fixed target. A `TransitionError` from `advance_fix_ladder` indicates a logic error in the caller (attempting an invalid transition), not a transient condition to be retried or swallowed. Callers must not catch `TransitionError` with a bare `except` that leaves state unchanged -- this creates infinite loops when the same invalid transition is reattempted on every routing cycle.

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Reads `iteration_limit` for alignment loop cap, reads `auto_save` to determine whether to trigger saves.
- **Unit 2 (Pipeline State Schema):** Uses `PipelineState` and `DebugSession` classes for all state operations. Uses `save_state` after transitions. Uses `validate_state` as a post-transition check.

---

## Unit 4: Ledger Manager

**Artifact category:** Python script

### Tier 1 -- Description

Manages JSONL conversation ledgers: append entries, read full ledger, compact, clear, and monitor size. Implements the compaction algorithm from spec Section 3.3 and the structured response format validation from spec Section 15.1. Also writes system-level `[HINT]` entries per Section 15.1.

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

Extracts a single unit's definition and upstream contract signatures from the full blueprint for context-isolated agent invocations. The extracted content becomes part of the task prompt for the relevant subagent. This is a deterministic operation -- no LLM involvement. Implements spec Section 10.11.

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

Parses machine-readable signatures from the blueprint using Python's `ast` module and produces Python stub files with `NotImplementedError` bodies. Also generates stubs or mocks for upstream dependencies based on their contract signatures. Implements spec Section 10.2, including the importability invariant (module-level `assert` statements are stripped).

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
- The CLI wrapper `main()` is invoked as a `run_command` action and must emit `COMMAND_SUCCEEDED` on success or `COMMAND_FAILED: [details]` on failure as its terminal status line. These status lines must match Unit 10's `COMMAND_STATUS_PATTERNS` vocabulary (spec Section 18.3).

### Tier 3 -- Dependencies

- **Unit 5 (Blueprint Extractor):** Uses `extract_upstream_contracts` to obtain upstream contract signatures for mock generation. The CLI wrapper uses `extract_unit` for the current unit's signatures.

---

## Unit 7: Dependency Extractor and Import Validator

**Artifact category:** Python script (library + CLI wrapper)

### Tier 1 -- Description

Scans all machine-readable signature blocks across all units in the blessed blueprint, extracts every external import statement, produces a complete dependency list, creates the Conda environment, installs all packages, and validates that every extracted import resolves. Implements spec Section 9 (Pre-Stage-3 Infrastructure Setup).

### Tier 2 — Signatures

```python
import ast
from typing import Dict, Any, List, Tuple, Set
from pathlib import Path

def extract_all_imports(blueprint_path: Path) -> List[str]: ...

def classify_import(import_stmt: str, scripts_dir: Path = None) -> str: ...

def map_imports_to_packages(imports: List[str]) -> Dict[str, str]: ...

def create_conda_environment(
    env_name: str, packages: Dict[str, str], python_version: str = "3.11"
) -> bool: ...

def validate_imports(env_name: str, imports: List[str]) -> List[Tuple[str, str]]: ...

def create_project_directories(
    project_root: Path, total_units: int
) -> None: ...

def derive_env_name(project_name: str) -> str: ...

# CLI wrapper (setup_infrastructure.py)
def main() -> None: ...
```

### Tier 2 — Invariants

```python
# Pre-conditions
assert blueprint_path.exists(), "Blueprint file must exist"

# Post-conditions for extract_all_imports
assert all(isinstance(s, str) for s in result), "All imports must be strings"

# Post-conditions for derive_env_name
assert result == project_name.lower().replace(" ", "_").replace("-", "_"), \
    "Env name must follow the canonical derivation"
assert " " not in result, "Env name must not contain spaces"
assert "-" not in result, "Env name must not contain hyphens"
```

### Tier 3 -- Error Conditions

- `FileNotFoundError`: "Blueprint file not found: {path}" -- when the blueprint does not exist.
- `ValueError`: "No signature blocks found in blueprint" -- when no `### Tier 2 — Signatures` headings are found. This heading format uses an em-dash -- any deviation causes a hard failure.
- `RuntimeError`: "Conda environment creation failed: {details}" -- when `conda create` fails.
- `RuntimeError`: "Import validation failed for: {import_list}" -- when imports do not resolve in the environment.

### Tier 3 -- Behavioral Contracts

- `extract_all_imports` parses every `### Tier 2 — Signatures` code block across all units and collects all `import` and `from ... import` statements. Heading format must use an em-dash (spec Section 24.13).
- `classify_import` determines whether an import is standard library, third-party, or project-internal. Classification checks: `src` and `svp` prefixes, dynamic lookup of `.py` files in the `scripts/` directory (via optional `scripts_dir` parameter, defaulting to `Path(__file__).parent`), and the stdlib module set.
- `map_imports_to_packages` maps third-party import module names to pip/conda package names.
- `create_conda_environment` creates the environment using `conda create` and installs packages. Uses `conda run -n {env_name}` for all operations (spec Section 4.3). Always installs pytest and pytest-cov unconditionally as framework dependencies required by the pipeline (spec Section 1.2, 9.1), in addition to any project-specific packages extracted from the blueprint.
- `validate_imports` executes each import in the environment via `conda run -n {env_name} python -c "import ..."` and returns a list of (import, error) tuples for failures.
- `create_project_directories` creates `src/unit_N/` and `tests/unit_N/` for each unit.
- `derive_env_name` applies the canonical derivation: `project_name.lower().replace(" ", "_").replace("-", "_")` (spec Section 4.3). This derivation must be used consistently -- never hardcoded.
- The CLI wrapper `main()` is invoked as a `run_command` action and must emit `COMMAND_SUCCEEDED` on success or `COMMAND_FAILED: [details]` on failure as its terminal status line. These status lines must match Unit 10's `COMMAND_STATUS_PATTERNS` vocabulary (spec Section 18.3).

### Tier 3 -- Dependencies

None. This unit operates on the blueprint file directly and uses only system-level tools (conda, python).

---

## Unit 8: Hint Prompt Assembler

**Artifact category:** Python script

### Tier 1 -- Description

Takes the raw hint content from a help agent's terminal output, the gate metadata, the receiving agent type, and the ladder position, and produces a wrapped `## Human Domain Hint (via Help Agent)` section for inclusion in the task prompt. Uses deterministic templates with variable substitution -- no LLM involvement. Implements spec Section 14.4.

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
  - **setup_agent**: project context (if exists), ledger content.
  - **stakeholder_dialog**: ledger, reference summaries, project context. In revision mode: adds critique and current spec.
  - **blueprint_author**: stakeholder spec, reference summaries, ledger, checker feedback (if available).
  - **blueprint_checker**: stakeholder spec (with working notes), blueprint, reference summaries.
  - **blueprint_reviewer**: blueprint, stakeholder spec, project context, reference summaries.
  - **stakeholder_reviewer**: stakeholder spec, project context, reference summaries.
  - **test_agent**: unit definition, upstream contracts.
  - **implementation_agent**: unit definition, upstream contracts. In fix ladder positions: adds diagnostic guidance, prior failure output, hint.
  - **coverage_review**: unit definition, upstream contracts, passing tests.
  - **diagnostic_agent**: stakeholder spec, unit blueprint section, failing tests, error output, failing implementations.
  - **integration_test_author**: stakeholder spec, contract signatures from all units.
  - **git_repo_agent**: all verified artifacts, reference documents. In fix cycle: adds error output.
  - **help_agent**: project summary, stakeholder spec, blueprint. In gate-invocation mode: adds gate flag.
  - **hint_agent**: logs, documents, stakeholder spec, blueprint.
  - **redo_agent**: pipeline state summary, human error description, optional current unit definition.
  - **reference_indexing**: full reference document.
  - **bug_triage**: stakeholder spec, blueprint, source code paths, test suite paths, ledger.
  - **repair_agent**: build/environment error diagnosis, environment state.
- `prepare_gate_prompt` assembles a gate prompt file at `.svp/gate_prompt.md` with the gate description, explicit response options, and relevant context (e.g., diagnostic analysis for test validation gates).
- When `hint_content` is provided, delegates to Unit 8 (Hint Prompt Assembler) to produce the wrapped hint block and includes it in the task prompt.
- The preparation script's test suite must cover every combination of agent type, gate type, and ladder position -- this is an elevated coverage requirement.

### Tier 3 -- Dependencies

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

This unit implements Bug 1 fix: the gate status string vocabulary ensures that human-typed option text is the exact status string -- no translation, no prefix, no reformatting. `update_state.py` dispatches based on exact string matching against this vocabulary.

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
    "setup_agent": ["PROJECT_CONTEXT_COMPLETE", "PROJECT_CONTEXT_REJECTED"],
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
    "redo_agent": ["REDO_CLASSIFIED: spec", "REDO_CLASSIFIED: blueprint", "REDO_CLASSIFIED: gate"],
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

def derive_env_name_from_state(state: PipelineState) -> str: ...

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
) -> str: ...

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
```

### Tier 3 -- Error Conditions

- `ValueError`: "Invalid gate response '{response}' for gate {gate_id}. Valid options: {options}" -- when the human's response does not match any option in the gate vocabulary. This is the Bug 1 prevention mechanism.
- `ValueError`: "Unknown agent status line: {line}" -- when a terminal status line does not match any known pattern.
- `ValueError`: "Unknown phase: {phase}" -- when the dispatch phase is not recognized.
- `TransitionError`: propagated from Unit 3 when state transitions fail precondition checks.

### Tier 3 -- Behavioral Contracts

- `route` reads `pipeline_state.json`, determines the next action, and returns a dict with all fields needed for the action block (ACTION, AGENT, PREPARE, TASK_PROMPT_FILE, POST, COMMAND, GATE, UNIT, OPTIONS, PROMPT_FILE, MESSAGE). Handles all pipeline states including debug loop states (same mechanism, additional state cases).
- `format_action_block` converts the dict to the structured text format defined in spec Section 17. Includes the REMINDER block for `invoke_agent`, `run_command`, and `human_gate` actions. Omits REMINDER for `session_boundary` and `pipeline_complete`.
- `derive_env_name_from_state` derives the conda environment name from the project name in state using the canonical derivation (spec Section 4.3).
- `dispatch_status` is the top-level dispatcher: reads the status file, determines whether it is a gate response, agent status, or command result, and delegates to the appropriate handler. For `unit_completion` phase commands, the routing script must ensure the status file contains a valid `COMMAND_SUCCEEDED` line before the command executes (spec Section 3.6 status file state invariant), since `unit_completion` is dispatched as a `run_command` whose COMMAND invokes `update_state.py` which reads the same status file.
- `dispatch_gate_response` validates the response against `GATE_VOCABULARY[gate_id]` using exact string matching. If the response is not in the vocabulary, raises `ValueError` -- the main session must re-present the gate. Calls appropriate Unit 3 transition functions based on gate_id and response.
- `dispatch_agent_status` parses the terminal status line and calls appropriate Unit 3 transition functions.
- `dispatch_command_status` parses command result status lines (`TESTS_PASSED`, `TESTS_FAILED`, `TESTS_ERROR`, `COMMAND_SUCCEEDED`, `COMMAND_FAILED`) and calls appropriate Unit 3 transition functions.
- `run_pytest` executes `conda run -n {env_name} pytest {test_path} -v` and constructs the appropriate command result status line from the output. Never uses bare `python` or `pytest`. Collection error detection (`_is_collection_error`) uses only specific indicators (`"ERROR collecting"`, `"ImportError"`, `"ModuleNotFoundError"`, `"SyntaxError"`, `"no tests ran"`). It must NOT use a bare `"ERROR"` indicator, which would false-positive on fixture setup errors that are expected during red runs against stubs raising `NotImplementedError`.
- The routing script handles debug loop states through the same mechanism as regular stage routing: it reads `pipeline_state.json`, checks for `debug_session`, and emits appropriate action blocks. No special mechanism -- just additional state cases.
- The OPTIONS field in human_gate output lists exactly the valid status strings from `GATE_VOCABULARY` for the corresponding gate (Bug 1 invariant).

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Reads config for model assignments, iteration limits, project settings.
- **Unit 2 (Pipeline State Schema):** Reads and writes pipeline state.
- **Unit 3 (State Transition Engine):** Calls transition functions for state updates. Uses `TransitionError` for precondition failures.

---

## Unit 11: Command Logic Scripts

**Artifact category:** Python scripts

### Tier 1 -- Description

Implements the logic for Group A utility commands: `/svp:save`, `/svp:quit`, `/svp:status`, `/svp:clean`. Each command is a dedicated `cmd_*.py` script (spec Section 13.1). These are invoked directly by the main session -- no subagent is spawned. Implements spec Sections 13 and 12.5.

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

# Post-conditions for clean_workspace with mode='delete'
# project_root should not exist after successful deletion
```

### Tier 3 -- Error Conditions

- `FileNotFoundError`: "Pipeline state file not found" -- when `get_status` cannot find `pipeline_state.json`.
- `PermissionError`: "Cannot delete workspace: permission denied on {path}" -- when `__pycache__` or conda files have read-only permissions. The deletion handler must chmod and retry before reporting failure (spec Section 12.5).
- `RuntimeError`: "Conda environment removal failed: {env_name}" -- when `conda env remove` fails.

### Tier 3 -- Behavioral Contracts

- `save_project` verifies file integrity of state file and key documents, confirms save is complete, returns a human-readable confirmation message.
- `quit_project` calls `save_project` first, then returns an exit confirmation message with save status.
- `get_status` reads pipeline state and produces a human-readable report including: current stage, sub-stage, verified units, alignment iterations used, pass history summary, debug history summary, and next expected action (spec Section 13).
- `format_pass_history` formats pass history entries as a brief numbered list showing how far each pass reached and why it ended.
- `format_debug_history` formats debug history entries similarly.
- `clean_workspace` is only functional after Stage 5 delivery. Returns an error message if invoked before delivery.
- `archive_workspace` compresses the workspace into a `.tar.gz` file alongside the repo, then deletes the workspace directory.
- `delete_workspace` removes the workspace with a permission-aware handler: chmod read-only paths and retry on `PermissionError`. The delivered repository (`projectname-repo/`) is never touched (spec Section 12.5).
- `remove_conda_env` runs `conda env remove -n {env_name} --yes` (spec Section 12.5).
- The command must be invoked as `PYTHONPATH=scripts python scripts/cmd_clean.py` so library imports resolve correctly (spec Section 12.5).

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Reads config for project settings and auto_save behavior.
- **Unit 2 (Pipeline State Schema):** Reads pipeline state for status reporting.
- **Unit 4 (Ledger Manager):** Reads ledger files for save integrity verification.

---

## Unit 12: Hook Configurations

**Artifact category:** JSON + shell scripts

### Tier 1 -- Description

Defines the hook configuration (`hooks.json`) and hook scripts (`write_authorization.sh`, `non_svp_protection.sh`) for universal write authorization and project protection. Implements spec Section 19 (both layers of write authorization), including the debug permission reset mechanism (Bug 2 fix) and the `SVP_PLUGIN_ACTIVE` environment variable check (SVP 1.1 hardening).

### Tier 2 — Signatures

```python
# hooks.json structure (JSON, not Python -- shown as dict for contract purposes)
from typing import Dict, Any, List

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
# The environment variable name used in non_svp_protection.sh MUST be identical
# to the name set by the SVP Launcher (Unit 24). The canonical name is SVP_PLUGIN_ACTIVE.
assert SVP_ENV_VAR == "SVP_PLUGIN_ACTIVE", "Canonical env var name must be SVP_PLUGIN_ACTIVE"

# Plugin hook format invariant
# hooks.json must use the top-level "hooks" wrapper key required by Claude Code plugins
assert "hooks" in HOOKS_JSON_SCHEMA, "Must use top-level hooks wrapper key"

# Content strings must produce valid deliverable files
assert "hooks" in json.loads(HOOKS_JSON_CONTENT), "hooks.json must have top-level hooks key"
assert WRITE_AUTHORIZATION_SH_CONTENT.startswith("#!/"), "Shell scripts must have shebang"
assert NON_SVP_PROTECTION_SH_CONTENT.startswith("#!/"), "Shell scripts must have shebang"
assert SVP_ENV_VAR in NON_SVP_PROTECTION_SH_CONTENT, "Must check SVP_PLUGIN_ACTIVE"
```

### Tier 3 -- Error Conditions

- Exit code 2 from `write_authorization.sh`: blocks the write and returns a message explaining why the path is not writable in the current state.
- Exit code 2 from `non_svp_protection.sh`: blocks bash execution and informs the human this is an SVP-managed project.

### Tier 3 -- Behavioral Contracts

- `hooks.json` uses the top-level `"hooks"` wrapper key required by Claude Code plugin hook format. It must NOT use the flat format.
- `write_authorization.sh` reads `pipeline_state.json` to determine the current state and checks the requested file path against the two-tier authorization model:
  - **Infrastructure paths** (`.svp/`, `pipeline_state.json`, `ledgers/`, `logs/`): always writable.
  - **Project artifact paths** (`src/`, `tests/`, `specs/`, `blueprint/`, `references/`, `projectname-repo/`): state-gated. For example, `src/unit_4/` is writable only during Stage 3 processing unit 4.
- **Debug session write rules (Bug 2 fix):** When `debug_session` is present in pipeline state AND `debug_session.authorized` is `true`:
  - `tests/regressions/` is writable regardless of classification.
  - During `build_env` classification: environment files, `pyproject.toml`, `__init__.py`, and directory structure are writable. Implementation `.py` files in `src/unit_N/` (other than `__init__.py`) are NOT writable.
  - During `single_unit` classification: `src/unit_N/` and `tests/unit_N/` are writable only for affected unit(s).
  - `.svp/triage_scratch/` is writable during triage.
- When `debug_session` is present but `debug_session.authorized` is `false` (pre-Gate 6.0): only infrastructure paths are writable. No artifact writes permitted.
- `non_svp_protection.sh` checks for the `SVP_PLUGIN_ACTIVE` environment variable. If not set, blocks all bash tool use and informs the human. The variable name MUST be `SVP_PLUGIN_ACTIVE` (SVP 1.1 hardening invariant shared with Unit 24).
- Hook scripts use paths relative to the project root, not plugin-specific variables (spec Section 19.2).
- `HOOKS_JSON_CONTENT` must be valid JSON matching the Claude Code plugin hook format: a top-level `"hooks"` key containing a `"PreToolUse"` array. Each hook entry has `"matcher"` (tool name regex), `"hooks"` array with `{"type": "command", "command": "bash .claude/scripts/write_authorization.sh"}` entries. Two hooks: one for Write/Edit tools (write authorization), one for Bash (non-SVP protection). Paths must use `.claude/scripts/` prefix so they resolve correctly from the project root (spec Section 19.2).
- `WRITE_AUTHORIZATION_SH_CONTENT` must be a bash script that: reads `pipeline_state.json`, normalizes the file path being written, checks infrastructure paths (always writable: `.svp/`, `pipeline_state.json`, `ledgers/`, `logs/`), checks state-gated paths based on current stage/unit, and exits 0 (allow) or 2 (block with message). Must handle all stages (0-5), pre_stage_3, and debug sessions.
- `NON_SVP_PROTECTION_SH_CONTENT` must be a bash script that checks for the `SVP_PLUGIN_ACTIVE` environment variable. If not set, blocks all bash commands with a message directing the human to use the `svp` command. Exits 0 if set, 2 if not.

### Tier 3 -- Dependencies

- **Unit 2 (Pipeline State Schema):** `write_authorization.sh` reads `pipeline_state.json` to check current state and debug session authorization.

---

## Unit 13: Dialog Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the three dialog agents: Setup Agent, Stakeholder Dialog Agent, and Blueprint Author Agent. Each file is a Markdown document with YAML frontmatter that becomes the agent's system prompt. These agents use the ledger-based multi-turn interaction pattern (spec Section 15.1). Implements spec Sections 6.1, 7.3, 7.4, 7.6, and 8.1.

### Tier 2 — Signatures

```python
from typing import Dict, Any, List

# --- YAML frontmatter schema for each agent definition ---

SETUP_AGENT_FRONTMATTER: Dict[str, Any] = {
    "name": "setup_agent",
    "description": "Creates structured project_context.md through Socratic dialog",
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
SETUP_AGENT_STATUS: List[str] = ["PROJECT_CONTEXT_COMPLETE", "PROJECT_CONTEXT_REJECTED"]
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

- Each `*_MD_CONTENT` string must be a complete Claude Code agent definition file. The YAML frontmatter must match the corresponding `*_FRONTMATTER` dict. The behavioral instructions after the frontmatter must describe: the agent's purpose, its methodology, its input/output format, its constraints, and its terminal status line(s). The instructions should be detailed enough that the agent can perform its role autonomously — not a placeholder or skeleton. Reference the stakeholder spec sections listed in this unit's description for the detailed behavioral requirements.
- **Setup Agent:** Conducts `project_context.md` creation dialog. Actively rewrites human input into well-structured, LLM-optimized context. Enforces quality gate -- refuses to advance if content is insufficient. Terminal status: `PROJECT_CONTEXT_COMPLETE` or `PROJECT_CONTEXT_REJECTED`. Uses `claude-sonnet-4-6`.
- **Stakeholder Dialog Agent:** Conducts the Socratic dialog for stakeholder spec authoring. Asks one question at a time, seeks consensus per topic, surfaces contradictions and edge cases. Draws on reference summaries. Also operates in revision mode for targeted corrections. Terminal status: `SPEC_DRAFT_COMPLETE` or `SPEC_REVISION_COMPLETE`. Uses `claude-opus-4-6`.
- **Blueprint Author Agent:** Conducts decomposition dialog with domain expert. Proposes initial decomposition, asks domain-level questions about phases, data flow, and boundaries. When a spec ambiguity is found, distinguishes clarification (working note) from contradiction (targeted spec revision). Produces units in the three-tier format. Uses the structured response format with `[QUESTION]`, `[DECISION]`, `[CONFIRMED]` closing lines. Evaluates human domain hints -- decomposition-level hints carry additional weight. If a hint contradicts a blueprint contract, returns `HINT_BLUEPRINT_CONFLICT: [details]`. Terminal status: `BLUEPRINT_DRAFT_COMPLETE` or `BLUEPRINT_REVISION_COMPLETE`. Uses `claude-opus-4-6`.
- All three agents include in their system prompts: the structured response format requirement, the terminal status line vocabulary, and the constraint against modifying files outside their scope.

### Tier 3 -- Dependencies

- **Unit 4 (Ledger Manager):** Dialog agents operate on conversation ledgers. The ledger format and entry schema are defined by Unit 4.
- **Unit 9 (Preparation Script):** The task prompt content these agents receive is assembled by Unit 9.

---

## Unit 14: Review and Checker Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the three review/checker agents: Stakeholder Spec Reviewer, Blueprint Checker, and Blueprint Reviewer. These are single-shot agents that receive documents, produce a critique or verdict, and terminate. Implements spec Sections 7.4, 8.2, and the "report most fundamental level" principle.

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
    "description": "Verifies blueprint alignment with stakeholder spec",
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

# Every *_MD_CONTENT string must be a valid Claude Code agent definition:
# - Starts with "---\n" (YAML frontmatter delimiter)
# - Contains "name:" in frontmatter
# - Contains "model:" in frontmatter
# - Contains "tools:" in frontmatter
# - Contains a second "---\n" (end of frontmatter)
# - Has substantial behavioral instructions after frontmatter (>100 chars)
```

### Tier 3 -- Error Conditions

- No runtime errors from agent definitions. Agents produce terminal status lines.

### Tier 3 -- Behavioral Contracts

- Each `*_MD_CONTENT` string must be a complete Claude Code agent definition file. The YAML frontmatter must match the corresponding `*_FRONTMATTER` dict. The behavioral instructions after the frontmatter must describe: the agent's purpose, its methodology, its input/output format, its constraints, and its terminal status line(s). The instructions should be detailed enough that the agent can perform its role autonomously — not a placeholder or skeleton. Reference the stakeholder spec sections listed in this unit's description for the detailed behavioral requirements.
- **Stakeholder Spec Reviewer:** Receives only the stakeholder spec, project context, and reference summaries -- no dialog ledger. Reads the document cold. Produces a structured critique identifying gaps, contradictions, underspecified areas, and missing edge cases. Terminal status: `REVIEW_COMPLETE`. Uses `claude-opus-4-6`.
- **Blueprint Checker:** Receives stakeholder spec (with working notes), blueprint, and reference summaries. Verifies alignment. Validates structural requirements: signatures parseable via `ast`, all types have imports, per-unit context budget within threshold (65% default), working note consistency. Reports only the most fundamental level when multiple issues found (spec supersedes blueprint). Produces dual-format output (prose + structured block). Three outcomes: `ALIGNMENT_CONFIRMED`, `ALIGNMENT_FAILED: spec`, `ALIGNMENT_FAILED: blueprint`. Uses `claude-opus-4-6`. The Bash tool is included so the checker can validate Python signatures by running `ast.parse()`.
- **Blueprint Reviewer:** Receives blueprint, stakeholder spec, project context, and reference summaries -- no dialog ledger. Reads documents cold. Produces a structured critique. Terminal status: `REVIEW_COMPLETE`. Uses `claude-opus-4-6`.

### Tier 3 -- Dependencies

- **Unit 9 (Preparation Script):** The task prompt content these agents receive is assembled by Unit 9.

---

## Unit 15: Construction Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the three construction agents: Test Agent, Implementation Agent, and Coverage Review Agent. These are single-shot agents that produce code artifacts. Implements spec Sections 10.1, 10.4, and 10.6.

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
# These agents are invoked independently with no shared context

# Test agent must declare synthetic data assumptions as part of output

# Every *_MD_CONTENT string must be a valid Claude Code agent definition:
# - Starts with "---\n" (YAML frontmatter delimiter)
# - Contains "name:" in frontmatter
# - Contains "model:" in frontmatter
# - Contains "tools:" in frontmatter
# - Contains a second "---\n" (end of frontmatter)
# - Has substantial behavioral instructions after frontmatter (>100 chars)
```

### Tier 3 -- Error Conditions

- No runtime errors from agent definitions. Agents produce terminal status lines.

### Tier 3 -- Behavioral Contracts

- Each `*_MD_CONTENT` string must be a complete Claude Code agent definition file. The YAML frontmatter must match the corresponding `*_FRONTMATTER` dict. The behavioral instructions after the frontmatter must describe: the agent's purpose, its methodology, its input/output format, its constraints, and its terminal status line(s). The instructions should be detailed enough that the agent can perform its role autonomously — not a placeholder or skeleton. Reference the stakeholder spec sections listed in this unit's description for the detailed behavioral requirements.
- **Test Agent:** Receives unit definition and upstream contracts from blueprint. Generates a complete pytest test suite including synthetic test data. Must declare synthetic data assumptions. Does NOT see any implementation. Terminal status: `TEST_GENERATION_COMPLETE`. Uses `claude-opus-4-6`.
- **Implementation Agent:** Receives unit definition and upstream contracts from blueprint. Generates the Python implementation. Does NOT see the tests. In fix ladder positions: receives diagnostic guidance, prior failure output, and optional hint. If a hint contradicts the blueprint, returns `HINT_BLUEPRINT_CONFLICT: [details]`. Terminal status: `IMPLEMENTATION_COMPLETE`. Uses `claude-opus-4-6`.
- **Coverage Review Agent:** Receives blueprint unit definition, upstream contracts, and passing test suite. Identifies behaviors implied by blueprint that no test covers. Adds missing coverage. Newly added tests must be validated as meaningful (fail for the right reason, not just because the stub raises NotImplementedError). Terminal status: `COVERAGE_COMPLETE: no gaps` or `COVERAGE_COMPLETE: tests added`. Uses `claude-opus-4-6`.

### Tier 3 -- Dependencies

- **Unit 6 (Stub Generator):** The test agent's tests run against stubs generated by Unit 6.
- **Unit 9 (Preparation Script):** The task prompt content these agents receive is assembled by Unit 9.

---

## Unit 16: Diagnostic and Classification Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the Diagnostic Agent and Redo Agent. Both produce dual-format output (prose + structured block) for routing decisions. Implements spec Sections 10.9 (three-hypothesis discipline) and 13 (`/svp:redo` classification).

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
    "description": "Traces human gate errors through the document hierarchy",
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
]

# Deliverable content constants (written by Stage 5 assembly)
DIAGNOSTIC_AGENT_MD_CONTENT: str  # -> agents/diagnostic_agent.md
REDO_AGENT_MD_CONTENT: str  # -> agents/redo_agent.md
```

### Tier 2 — Invariants

```python
# Diagnostic agent must articulate all three hypotheses before converging
# Redo agent must not ask the human to self-classify their error

# Every *_MD_CONTENT string must be a valid Claude Code agent definition:
# - Starts with "---\n" (YAML frontmatter delimiter)
# - Contains "name:" in frontmatter
# - Contains "model:" in frontmatter
# - Contains "tools:" in frontmatter
# - Contains a second "---\n" (end of frontmatter)
# - Has substantial behavioral instructions after frontmatter (>100 chars)
```

### Tier 3 -- Error Conditions

- No runtime errors from agent definitions. Agents produce terminal status lines.

### Tier 3 -- Behavioral Contracts

- Each `*_MD_CONTENT` string must be a complete Claude Code agent definition file. The YAML frontmatter must match the corresponding `*_FRONTMATTER` dict. The behavioral instructions after the frontmatter must describe: the agent's purpose, its methodology, its input/output format, its constraints, and its terminal status line(s). The instructions should be detailed enough that the agent can perform its role autonomously — not a placeholder or skeleton. Reference the stakeholder spec sections listed in this unit's description for the detailed behavioral requirements.
- **Diagnostic Agent:** Receives stakeholder spec, unit blueprint section, failing tests, error output, and failing implementations. Must articulate a plausible case at each of three levels (implementation, blueprint, spec) before converging. Produces dual-format output: `[PROSE]` section followed by `[STRUCTURED]` block with UNIT, HYPOTHESIS_1, HYPOTHESIS_2, HYPOTHESIS_3, and RECOMMENDATION. Terminal status: `DIAGNOSIS_COMPLETE: implementation`, `DIAGNOSIS_COMPLETE: blueprint`, or `DIAGNOSIS_COMPLETE: spec`. Uses `claude-opus-4-6`.
- **Redo Agent:** Receives pipeline state summary, human error description, and current unit definition. Uses read tools to trace the error through the document hierarchy (spec -> blueprint -> tests/implementation). Classifies the error source -- does NOT ask the human to self-classify. Produces dual-format output. Terminal status: `REDO_CLASSIFIED: spec`, `REDO_CLASSIFIED: blueprint`, or `REDO_CLASSIFIED: gate`. Uses `claude-opus-4-6`. Available during Stages 2, 3, and 4.

### Tier 3 -- Dependencies

- **Unit 9 (Preparation Script):** The task prompt content these agents receive is assembled by Unit 9.

---

## Unit 17: Support Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the Help Agent and Hint Agent. The Help Agent uses ledger-based multi-turn within sessions (cleared on dismissal); the Hint Agent operates in reactive (single-shot) or proactive (ledger multi-turn) mode. Implements spec Sections 14 and 13.

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
# In gate-invocation mode, help agent proactively offers hint formulation
# In non-gate mode, hint formulation instruction is omitted

# Every *_MD_CONTENT string must be a valid Claude Code agent definition:
# - Starts with "---\n" (YAML frontmatter delimiter)
# - Contains "name:" in frontmatter
# - Contains "model:" in frontmatter
# - Contains "tools:" in frontmatter
# - Contains a second "---\n" (end of frontmatter)
# - Has substantial behavioral instructions after frontmatter (>100 chars)
```

### Tier 3 -- Error Conditions

- No runtime errors from agent definitions. Agents produce terminal status lines.

### Tier 3 -- Behavioral Contracts

- Each `*_MD_CONTENT` string must be a complete Claude Code agent definition file. The YAML frontmatter must match the corresponding `*_FRONTMATTER` dict. The behavioral instructions after the frontmatter must describe: the agent's purpose, its methodology, its input/output format, its constraints, and its terminal status line(s). The instructions should be detailed enough that the agent can perform its role autonomously — not a placeholder or skeleton. Reference the stakeholder spec sections listed in this unit's description for the detailed behavioral requirements.
- **Help Agent:** Read-only. Tools restricted to Read, Glob, Grep, and web search. Receives project summary, stakeholder spec, blueprint. In gate-invocation mode: receives gate flag and proactively offers hint formulation when conversation produces an actionable observation. The human approves hint text explicitly. Output to main session: `HELP_SESSION_COMPLETE: no hint` or `HELP_SESSION_COMPLETE: hint forwarded` followed by hint content. Conversation ledger cleared on dismissal. Uses `claude-sonnet-4-6`.
- **Hint Agent:** Operates in reactive mode (reads accumulated logs, identifies patterns, no additional human input needed) or proactive mode (asks human what prompted their concern, which document they suspect). Produces diagnostic analysis. Offers explicit options: CONTINUE or RESTART. Terminal status: `HINT_ANALYSIS_COMPLETE`. Uses `claude-opus-4-6`.

### Tier 3 -- Dependencies

- **Unit 9 (Preparation Script):** The task prompt content these agents receive is assembled by Unit 9.

---

## Unit 18: Utility Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the Reference Indexing Agent, Integration Test Author, and Git Repo Agent. These are single-shot utility agents. Implements spec Sections 7.2, 11.1, and 12.1-12.4.

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
    "description": "Creates clean git repository from verified artifacts",
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

# Delivered repository README (Mode A: carry-forward from v1.1; Mode B: generated from spec)
README_MD_CONTENT: str  # -> README.md
```

### Tier 2 — Invariants

```python
# Git Repo Agent must use build-backend = "setuptools.build_meta" in pyproject.toml
# Git Repo Agent must never reference stub.py in entry points or imports
# Git Repo Agent must never reference src.unit_N paths in entry points or imports
# Git Repo Agent must relocate unit implementations from src/unit_N/ to blueprint file tree paths
# Git Repo Agent must rewrite cross-unit imports from src.unit_N to final module paths
# Git Repo Agent must use bare imports (not svp.scripts.X) for inter-script references in svp/scripts/
# Git Repo Agent must ensure every directly-invoked script has if __name__ == "__main__" guard
# Git Repo Agent must ensure every delivered script contains all functions imported by other delivered scripts
# Git Repo Agent must create repo at {project_root.parent}/{project_name}-repo (absolute path)
# Git Repo Agent must verify pip install -e . succeeds before considering assembly complete
# Git Repo Agent must verify the CLI entry point loads without import errors after install
# Git Repo Agent must place svp_launcher.py at svp/scripts/svp_launcher.py (not at repo root)
# Git Repo Agent entry point: svp = "svp.scripts.svp_launcher:main" (never src.unit_24.stub)
# Git Repo Agent must write README.md from README_MD_CONTENT
# README_MD_CONTENT mode is determined by spec Section 12.7.1:
#   Mode A (SVP self-build): carry-forward from previous version, preserve sections, update only what changed
#   Mode B (general project): generated from stakeholder spec and blueprint, using the section template
# For THIS project (SVP 1.2.1): Mode A applies — carry forward from v1.2 README

# Every *_MD_CONTENT string must be a valid Claude Code agent definition:
# - Starts with "---\n" (YAML frontmatter delimiter)
# - Contains "name:" in frontmatter
# - Contains "model:" in frontmatter
# - Contains "tools:" in frontmatter
# - Contains a second "---\n" (end of frontmatter)
# - Has substantial behavioral instructions after frontmatter (>100 chars)
```

### Tier 3 -- Error Conditions

- No runtime errors from agent definitions. Agents produce terminal status lines.

### Tier 3 -- Behavioral Contracts

- Each `*_MD_CONTENT` string must be a complete Claude Code agent definition file. The YAML frontmatter must match the corresponding `*_FRONTMATTER` dict. The behavioral instructions after the frontmatter must describe: the agent's purpose, its methodology, its input/output format, its constraints, and its terminal status line(s). The instructions should be detailed enough that the agent can perform its role autonomously — not a placeholder or skeleton. Reference the stakeholder spec sections listed in this unit's description for the detailed behavioral requirements.
- **Reference Indexing Agent:** Reads a full reference document or explores a GitHub repository via MCP. Produces a structured summary saved to `references/index/`. For PDFs, uses Claude's native document understanding. For GitHub repos, reads README, maps directory structure, identifies key modules. Terminal status: `INDEXING_COMPLETE`. Uses `claude-sonnet-4-6`.
- **Integration Test Author:** Receives stakeholder spec plus contract signatures from all units. Reads specific source files on demand from disk. Generates tests covering cross-unit interactions: data flow, resource contention, timing, error propagation, plus at least one end-to-end domain-meaningful validation. **For SVP self-builds:** must include an integration test that exercises the `svp restore` code path using the bundled Game of Life example files (Unit 22's `GOL_*_CONTENT` constants). The test calls the launcher's restore functions directly (not via subprocess) with the example files written to a temporary directory, then verifies: workspace directory structure is created, pipeline state is initialized at `pre_stage_3`, injected spec and blueprint match the originals, CLAUDE.md is generated, and default config is written. This tests the seam between Units 24, 22, 2, and 1 (see spec Section 12.7.2). Terminal status: `INTEGRATION_TESTS_COMPLETE`. Uses `claude-opus-4-6`.
- **Git Repo Agent:** Creates a clean git repository at `{project_root.parent}/{project_name}-repo` (absolute path -- never relative, never inside workspace). **Assembly mapping:** reads the blueprint preamble file tree to determine each unit's final destination path (annotated with `<- Unit N`). Copies unit implementation content from `src/unit_N/` in the workspace to the final path in the repo. Rewrites all `from src.unit_N` imports to use final module paths. **Bare imports for scripts:** scripts delivered to `svp/scripts/` must use bare imports (e.g., `from pipeline_state import load_state`), NOT package imports (`from svp.scripts.pipeline_state import ...`), because they are copied to project workspaces and run with `PYTHONPATH=scripts`. The `svp.scripts.X` form is used ONLY in `pyproject.toml` entry points. **CLI entry point guards:** every script invoked via `python scripts/X.py` must include `if __name__ == "__main__"` guard. **Runtime completeness:** each delivered script must contain all functions that other delivered scripts import from it, including orchestration functions that may exist in workspace `scripts/` copies but not in `src/unit_N/stub.py`. Never reproduces the workspace `src/unit_N/` directory structure in the delivered repo. Commits in order: infrastructure, stakeholder spec, blueprint, each unit with tests in topological order, integration tests, configuration, version history, references. Must use `build-backend = "setuptools.build_meta"`. Must set entry points to final relocated module paths -- never `stub.py`, never `src.unit_N`. Entry point for the launcher: `svp.scripts.svp_launcher:main`. Must verify `pip install -e .` succeeds. Must verify the CLI entry point loads without import errors. Participates in bounded fix cycle (up to 3 reassembly attempts). Includes structural validation for plugin directory structure (spec Section 12.3) including checks for workspace-internal paths. **README.md:** The `README_MD_CONTENT` string contains the full README.md text. The git repo agent writes this to `README.md` at the repository root. The mode (A or B per spec Section 12.7.1) determines how the content is produced. For this project (SVP 1.2), Mode A applies: the v1.1 README is the baseline, carried forward with minimal updates. The content must preserve all 10 baseline sections in order. Only version-specific content that actually changed is updated — section headings, prose structure, and unchanged content are preserved verbatim. The implementation agent producing `README_MD_CONTENT` receives the v1.1 README as baseline reference and updates only what changed. For general projects (Mode B), the implementation agent generates the README from the stakeholder spec and blueprint using the section template, adapting headings and content to the project's domain.
Terminal status: `REPO_ASSEMBLY_COMPLETE`. Uses `claude-sonnet-4-6`.

### Tier 3 -- Dependencies

- **Unit 9 (Preparation Script):** The task prompt content these agents receive is assembled by Unit 9.

---

## Unit 19: Debug Loop Agent Definitions

**Artifact category:** Markdown (AGENT.md files)

### Tier 1 -- Description

Defines the agent definition files for the Bug Triage Agent and Repair Agent. The Bug Triage Agent uses ledger-based multi-turn for Socratic triage dialog. The Repair Agent is single-shot for build/environment fixes. Implements spec Section 12.9.

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

# Every *_MD_CONTENT string must be a valid Claude Code agent definition:
# - Starts with "---\n" (YAML frontmatter delimiter)
# - Contains "name:" in frontmatter
# - Contains "model:" in frontmatter
# - Contains "tools:" in frontmatter
# - Contains a second "---\n" (end of frontmatter)
# - Has substantial behavioral instructions after frontmatter (>100 chars)
```

### Tier 3 -- Error Conditions

- No runtime errors from agent definitions. Agents produce terminal status lines.

### Tier 3 -- Behavioral Contracts

- Each `*_MD_CONTENT` string must be a complete Claude Code agent definition file. The YAML frontmatter must match the corresponding `*_FRONTMATTER` dict. The behavioral instructions after the frontmatter must describe: the agent's purpose, its methodology, its input/output format, its constraints, and its terminal status line(s). The instructions should be detailed enough that the agent can perform its role autonomously — not a placeholder or skeleton. Reference the stakeholder spec sections listed in this unit's description for the detailed behavioral requirements.
- **Bug Triage Agent:** Conducts Socratic triage dialog. Starts in read-only mode (pre-Gate 6.0). After authorization, gains write access to `tests/regressions/` and `.svp/triage_scratch/`. Classifies bugs as build/environment or logic (single-unit vs cross-unit). For logic bugs: aims to produce a test-writable assertion with concrete inputs, expected outputs, actual outputs. Uses real data for diagnosis but produces tests with synthetic data. Uses the structured response format with tagged closing lines. Triage dialog uses its own ledger (`bug_triage_N.jsonl`). Produces dual-format output. Terminal status: `TRIAGE_COMPLETE: build_env`, `TRIAGE_COMPLETE: single_unit`, `TRIAGE_COMPLETE: cross_unit`, `TRIAGE_NEEDS_REFINEMENT`, or `TRIAGE_NON_REPRODUCIBLE`. Uses `claude-opus-4-6`.
- **Repair Agent:** Narrow mandate for build/environment fixes. Can modify: environment files, `pyproject.toml`, `__init__.py` files, directory structure. Cannot modify: implementation `.py` files in `src/unit_N/` other than `__init__.py`. If the fix requires implementation changes, returns `REPAIR_RECLASSIFY`. Participates in bounded fix cycle (up to 3 attempts). Terminal status: `REPAIR_COMPLETE`, `REPAIR_FAILED`, or `REPAIR_RECLASSIFY`. Uses `claude-sonnet-4-6`.

### Tier 3 -- Dependencies

- **Unit 9 (Preparation Script):** The task prompt content these agents receive is assembled by Unit 9. Adding new agent types (as this unit does with `bug_triage` and `repair_agent`) requires updating both `src/unit_9/stub.py` (canonical) and `scripts/prepare_task.py` (runtime copy). See the "Scripts synchronization rule" in the preamble.

---

## Unit 20: Slash Command Files

**Artifact category:** Markdown (command files)

### Tier 1 -- Description

Defines the slash command markdown files for all human commands: `/svp:save`, `/svp:quit`, `/svp:help`, `/svp:hint`, `/svp:status`, `/svp:ref`, `/svp:redo`, `/svp:bug`, and `/svp:clean`. Each command file is injected into the conversation when the human types the command. Implements spec Section 13, including the critical Group A/B distinction (SVP 1.1 hardening).

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
# Group A: invoke dedicated cmd_*.py scripts directly. No subagent.

GROUP_B_COMMANDS: List[str] = ["help", "hint", "ref", "redo", "bug"]
# Group B: invoke prepare_task.py then spawn subagent. No cmd_*.py scripts.

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
# Group A commands invoke cmd_*.py scripts directly
# Group B commands invoke prepare_task.py then spawn subagent
# The following scripts MUST NEVER EXIST: cmd_help.py, cmd_hint.py, cmd_ref.py, cmd_redo.py, cmd_bug.py
assert not any((scripts_dir / s).exists() for s in PROHIBITED_SCRIPTS), \
    "Prohibited Group B cmd_*.py scripts must not exist"

# Each command content string must be non-empty and contain the command's
# execution instructions. Group A commands (save, quit, status, clean) invoke
# deterministic scripts. Group B commands (help, hint, ref, redo, bug) invoke
# agents or present gates.
```

### Tier 3 -- Error Conditions

- No runtime errors from command files. They are Markdown injected into conversation context.

### Tier 3 -- Behavioral Contracts

- **Group A commands** (`save`, `quit`, `status`, `clean`): Each command file directs the main session to run `PYTHONPATH=scripts python scripts/cmd_{name}.py --project-root .` and present the output. No subagent is spawned.
- **Group B commands** (`help`, `hint`, `ref`, `redo`, `bug`): Each command file directs the main session to run `python scripts/prepare_task.py --agent {role} --project-root . --output .svp/task_prompt.md` to produce the task prompt, then spawn the corresponding subagent with the task prompt verbatim. No `cmd_*.py` script is invoked.
- `/svp:clean` must be invoked as `PYTHONPATH=scripts python scripts/cmd_clean.py` so library imports resolve correctly (spec Section 12.5).
- `/svp:ref` is available during Stages 0, 1, and 2 only. Locked from Stage 3 onward.
- `/svp:redo` is available during Stages 2, 3, and 4.
- `/svp:bug` is available only after Stage 5 completion. Supports `--abandon` flag.
- Command file content must be written as explicit, unambiguous directives that minimize the probability of the main session deviating from the intended action. The directive names the exact script, exact arguments, and exact presentation format.
- Each `*_MD_CONTENT` string contains the complete instructions for the slash command. Group A commands (`save`, `quit`, `status`, `clean`) contain instructions to run deterministic scripts (e.g., `python scripts/cmd_save.py --project-root .`). Group B commands (`help`, `hint`, `ref`, `redo`, `bug`) contain instructions for agent invocation, gate presentation, or interactive flows. Each command's content must describe: when to use the command, what it does, and the exact execution steps. The command names must match the `COMMAND_FILES` dict keys.

### Tier 3 -- Dependencies

- **Unit 10 (Routing Script):** Group B commands ultimately interact with the routing/dispatch system.
- **Unit 11 (Command Logic Scripts):** Group A commands invoke the `cmd_*.py` scripts defined in Unit 11.

---

## Unit 21: Orchestration Skill

**Artifact category:** Markdown (SKILL.md)

### Tier 1 -- Description

Defines the SKILL.md file that constrains the main session's orchestration behavior. This is the primary behavioral instruction for the orchestration layer -- it defines the six-step mechanical action cycle, verbatim task prompt relay, and deferral of human input during autonomous sequences. Implements spec Section 3.6.

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
# The skill must reference the routing script as the sole decision-maker for pipeline flow

# The skill content must describe the complete six-step action cycle
assert all(step_keyword in ORCHESTRATION_SKILL_MD_CONTENT
           for step_keyword in ["routing script", "PREPARE", "ACTION", "last_status.txt", "POST"])
```

### Tier 3 -- Error Conditions

- No runtime errors from the skill file. It is Markdown loaded as behavioral context.

### Tier 3 -- Behavioral Contracts

- The skill file defines the main session's complete behavioral protocol: how to read routing script output, how to execute each action type, how to write status lines, and how to avoid improvising.
- Instructs verbatim task prompt relay: pass the contents of TASK_PROMPT_FILE as the task prompt without summarization, annotation, or rephrasing.
- Instructs deferral of human input during autonomous sequences: acknowledge and defer, complete the current action first.
- References the routing script as the sole decision-maker for pipeline flow.
- Instructs the main session to re-present gate options when the human's response does not match any valid option.
- Instructs the six-step mechanical action cycle with no skipping, no additions, no reordering.
- `ORCHESTRATION_SKILL_MD_CONTENT` must be the complete SVP orchestration protocol. It must describe: the six-step action cycle (run routing script -> prepare -> execute action -> write status -> post -> repeat), how to handle each action type (invoke_agent, run_command, present_gate, session_boundary, pipeline_complete), how to construct status lines, how to relay task prompts verbatim, gate presentation rules, and session boundary handling. This is the core protocol that drives the entire SVP pipeline — it must be comprehensive and precise.

### Tier 3 -- Dependencies

- **Unit 10 (Routing Script):** The skill references the routing script's output format and the six-step cycle that processes it.

---

## Unit 22: Project Templates

**Artifact category:** Mixed (Python template, JSON defaults, text)

### Tier 1 -- Description

Defines the template files used during project bootstrap: the CLAUDE.md generator, the default `svp_config.json`, the initial `pipeline_state.json`, and the `README_SVP.txt` protection notice. These are copied or generated into new project workspaces by the SVP launcher. Implements spec Sections 3.6 (CLAUDE.md), 22.1 (default config), 22.2 (initial state), and 19.3 (README_SVP.txt).

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

# Deliverable content constants (written by Stage 5 assembly)
CLAUDE_MD_PY_CONTENT: str  # -> scripts/templates/claude_md.py
SVP_CONFIG_DEFAULT_JSON_CONTENT: str  # -> scripts/templates/svp_config_default.json
PIPELINE_STATE_INITIAL_JSON_CONTENT: str  # -> scripts/templates/pipeline_state_initial.json
README_SVP_TXT_CONTENT: str  # -> scripts/templates/readme_svp.txt

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
assert "def render_claude_md" in CLAUDE_MD_PY_CONTENT, "claude_md.py must have render function"
assert '"stage"' in PIPELINE_STATE_INITIAL_JSON_CONTENT, "Initial state must have stage field"
assert '"skip_permissions"' in SVP_CONFIG_DEFAULT_JSON_CONTENT, "Config must have skip_permissions"
assert "SVP-MANAGED" in README_SVP_TXT_CONTENT, "README must have protection notice"

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
- `INITIAL_STATE_TEMPLATE` is a JSON file matching the output of `create_initial_state` from Unit 2 (with a placeholder for project_name).
- `README_SVP_TEMPLATE` explains that this is an SVP-managed project, that files are protected by write authorization hooks, and guides the human to use the `svp` command.
- `CLAUDE_MD_PY_CONTENT` must be a Python module with a `render_claude_md(project_name: str) -> str` function that generates the project's CLAUDE.md file. The generated content must include: the SVP-managed project header, the instruction to run the routing script on session start, the six-step action cycle, the verbatim relay rule, the "Do Not Improvise" section, and the reference to the orchestration skill.
- `SVP_CONFIG_DEFAULT_JSON_CONTENT` must be valid JSON with the default config: `iteration_limit`, `models` dict, `context_budget_override`, `context_budget_threshold`, `compaction_character_threshold`, `auto_save`, `skip_permissions`.
- `PIPELINE_STATE_INITIAL_JSON_CONTENT` must be valid JSON with the initial pipeline state template (stage "0", sub_stage "hook_activation", null counters, empty lists, null timestamps).
- `README_SVP_TXT_CONTENT` must be a static text notice explaining the two-layer write authorization system and directing users to use the `svp` command.
- `GOL_STAKEHOLDER_SPEC_CONTENT`, `GOL_BLUEPRINT_CONTENT`, and `GOL_PROJECT_CONTEXT_CONTENT` are carry-forward artifacts from v1.1. They contain the complete Game of Life example project documents (stakeholder spec, blueprint, project context). These are carried forward verbatim — the implementation agent must reproduce the v1.1 content exactly. They are used both as installation verification (users run `svp restore` with them) and as integration test fixtures (see spec Section 12.7.2).

### Tier 3 -- Dependencies

- **Unit 1 (SVP Configuration):** Default config template must match Unit 1's `DEFAULT_CONFIG`.
- **Unit 2 (Pipeline State Schema):** Initial state template must match Unit 2's `create_initial_state` output.
- **Unit 10 (Routing Script):** CLAUDE.md references the routing script by name.

---

## Unit 23: Plugin Manifest

**Artifact category:** JSON

### Tier 1 -- Description

Defines the `plugin.json` manifest for the SVP plugin subdirectory and the `marketplace.json` catalog at the repository root. Includes structural validation logic for the plugin directory layout. Implements spec Sections 1.4 and 12.3.

### Tier 2 — Signatures

```python
from typing import Dict, Any, List
from pathlib import Path

# Plugin manifest schema
PLUGIN_JSON: Dict[str, Any] = {
    "name": "svp",
    "version": "1.2.1",
    "description": "Stratified Verification Pipeline - deterministically orchestrated software development",
}

# Marketplace catalog schema -- must match Claude Code's required format exactly.
# Required top-level fields: name (str), owner (obj), plugins (array).
# Each plugin entry requires: name, source (relative path with ./), description, version, author.
MARKETPLACE_JSON: Dict[str, Any] = {
    "name": "svp",
    "owner": {"name": "SVP"},
    "plugins": [
        {
            "name": "svp",
            "source": "./svp",
            "description": "Stratified Verification Pipeline — deterministically orchestrated, sequentially gated development for domain experts",
            "version": "1.2.1",
            "author": {"name": "SVP"},
        }
    ]
}

def validate_plugin_structure(repo_root: Path) -> List[str]: ...

# Deliverable content constants (written by Stage 5 assembly)
PLUGIN_JSON_CONTENT: str  # -> svp/.claude-plugin/plugin.json
MARKETPLACE_JSON_CONTENT: str  # -> .claude-plugin/marketplace.json
```

### Tier 2 — Invariants

```python
# Structural validation checks (spec Section 12.3)
assert (repo_root / ".claude-plugin" / "marketplace.json").exists(), \
    "Repository root must contain .claude-plugin/marketplace.json"
assert (repo_root / "svp" / ".claude-plugin" / "plugin.json").exists(), \
    "Plugin subdirectory must contain .claude-plugin/plugin.json"

# All component directories must be at plugin subdirectory root level
for component in ["agents", "commands", "hooks", "scripts", "skills"]:
    assert (repo_root / "svp" / component).is_dir(), \
        f"{component}/ must be at svp/ root level"
    assert not (repo_root / component).is_dir(), \
        f"{component}/ must NOT be at repository root level"

assert '"name": "svp"' in PLUGIN_JSON_CONTENT
assert '"plugins"' in MARKETPLACE_JSON_CONTENT
assert '"source": "./svp"' in MARKETPLACE_JSON_CONTENT
```

### Tier 3 -- Error Conditions

- `ValueError`: "Plugin structure validation failed: {details}" -- when `validate_plugin_structure` finds violations. Each violation is a specific, actionable description.

### Tier 3 -- Behavioral Contracts

- `plugin.json` lives at `svp/.claude-plugin/plugin.json` -- it is the only file inside `.claude-plugin/` at the plugin subdirectory level.
- `marketplace.json` lives at `.claude-plugin/marketplace.json` at the repository root level -- a separate `.claude-plugin/` directory from the plugin subdirectory's.
- `validate_plugin_structure` checks all structural requirements: marketplace.json at repo root, plugin.json at plugin subdirectory, all component directories at plugin subdirectory root, no component directories at repository root.
- The `source` field in `marketplace.json` must be a relative path with `./` prefix pointing to the plugin subdirectory (`"./svp"`).
- `PLUGIN_JSON_CONTENT` must be valid JSON with the plugin manifest: `name` ("svp"), `version`, `description`.
- `MARKETPLACE_JSON_CONTENT` must be valid JSON matching the marketplace catalog schema from spec Section 1.4: top-level `name`, `owner` object, `plugins` array with `name`, `source` ("./svp"), `description`, `version`, `author` fields.

### Tier 3 -- Dependencies

- All preceding units. The plugin manifest is a packaging concern that depends on all components being defined.

---

## Unit 24: SVP Launcher

**Artifact category:** Python script (standalone CLI tool)

### Tier 1 -- Description

The standalone `svp` CLI tool that manages the complete SVP session lifecycle: prerequisite verification, project directory creation, script copying, CLAUDE.md generation, filesystem permission management, session cycling, and resume. The launcher runs before Claude Code starts and is not a plugin component. Delivered at `svp/scripts/svp_launcher.py` in the repository (entry point: `svp.scripts.svp_launcher:main`).

**Self-containment requirement:** The launcher must be a single, self-contained Python file with NO imports from other SVP units (no `from src.unit_N`, no `from svp.scripts.pipeline_state`, etc.). All logic must be inline. Template-based file generation (CLAUDE.md, initial state, default config, README_SVP.txt) uses template files from `scripts/templates/` when available, with inline fallback content when templates are not found. This ensures the launcher works regardless of whether it is run from a plugin installation or a standalone checkout.

Implements spec Sections 1.4, 6.1, 16, 19.1, 19.2, and the `SVP_PLUGIN_ACTIVE` and `--dangerously-skip-permissions` hardening from SVP 1.1.

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
SVP_DIR: str = ".svp"
MARKERS_DIR: str = ".svp/markers"
CLAUDE_MD_FILE: str = "CLAUDE.md"
README_SVP_FILE: str = "README_SVP.txt"
SVP_ENV_VAR: str = "SVP_PLUGIN_ACTIVE"

PROJECT_DIRS: List[str] = [
    ".svp", ".svp/markers", ".claude", "scripts", "ledgers",
    "logs", "logs/rollback", "specs", "specs/history",
    "blueprint", "blueprint/history", "references", "references/index",
    "src", "tests", "data",
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
# Prerequisite checking (8 checks, each returns (passed, message))
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
# The environment variable name set by the launcher MUST be identical
# to the name checked by non_svp_protection.sh (Unit 12).
assert SVP_ENV_VAR == "SVP_PLUGIN_ACTIVE"

# Exactly 8 prerequisite checks, in order
assert len(run_all_prerequisites()) == 8

# PROJECT_DIRS must include all directories from spec Section 6.2
assert ".svp" in PROJECT_DIRS
assert "scripts" in PROJECT_DIRS
assert "src" in PROJECT_DIRS
assert "tests" in PROJECT_DIRS

# Self-containment: no imports from other SVP modules
# The launcher file must contain ZERO lines matching:
#   from src.unit_  |  import src.unit_  |  from svp.scripts.  |  import svp.scripts.
# All logic is inline with template-file fallbacks.

# Delivery path: svp/scripts/svp_launcher.py
# Entry point: svp = "svp.scripts.svp_launcher:main"
# Shebang: file must start with #!/usr/bin/env python3 so it is directly executable

# Environment variable propagation
# SVP_PLUGIN_ACTIVE must be set in the subprocess environment via:
#   env = os.environ.copy(); env[SVP_ENV_VAR] = "1"
# Never set on the launcher's own os.environ.

# --dangerously-skip-permissions is controlled by skip_permissions config key
# read via load_launch_config on every session launch (not cached across restarts).
```

### Tier 3 -- Error Conditions

- `FileExistsError`: "Project directory already exists: {path}" -- from `create_project_directory` when the target already exists.
- `RuntimeError`: "Plugin scripts directory not found at {path}. The SVP plugin installation may be corrupted." -- from `copy_scripts_to_workspace` when plugin has no scripts/.
- `RuntimeError`: "Session launch failed: Claude Code executable not found" -- from `launch_claude_code` when `claude` is not on PATH.
- `RuntimeError`: "Session launch failed: {details}" -- from `launch_claude_code` for other subprocess errors.

### Tier 3 -- Behavioral Contracts

**Plugin discovery (`_find_plugin_root`, `_is_svp_plugin_dir`):**
- `_find_plugin_root` locates the SVP plugin root directory. First checks the `SVP_PLUGIN_ROOT` environment variable. Then searches standard Claude Code plugin locations in order: `~/.claude/plugins/svp`, all version directories under `~/.claude/plugins/cache/svp/svp/*/` (sorted), `~/.config/claude/plugins/svp`, `/usr/local/share/claude/plugins/svp`, `/usr/share/claude/plugins/svp`. Returns the first directory where `_is_svp_plugin_dir` returns True, or None.
- `_is_svp_plugin_dir` checks whether a directory contains `.claude-plugin/plugin.json` with `"name": "svp"`. Returns False on missing file, JSON decode error, or wrong name.

**Output formatting (`_print_header`, `_print_status`, `_print_transition`):**
- `_print_header` prints a decorated header line (e.g., `=` border with centered text).
- `_print_status` prints a single prerequisite result with a pass/fail icon (checkmark or X), the check name, and the message.
- `_print_transition` prints a session transition message between restart cycles.

**CLI parsing (`parse_args`):**
- Supports three subcommands: `new <project_name>` (with `--parent-dir` option), `restore <project_name>` (with `--spec`, `--blueprint`, `--context`, `--parent-dir`, `--scripts-source` options), and no subcommand (defaults to `resume`).
- The `restore` subcommand creates a new project with pre-existing spec and blueprint files injected, fast-forwarding the pipeline state to `pre_stage_3` (skipping Stages 0-2). `--spec` and `--blueprint` are required; `--context` is optional; `--scripts-source` overrides where scripts are copied from (for development).
- Returns an `argparse.Namespace`. Accepts optional `argv` parameter for testing.

**Prerequisite checks (8 checks, each returns `Tuple[bool, str]`):**
Each check actually runs the tool via `subprocess.run` with `capture_output=True` and a timeout (10-15 seconds), not just `shutil.which`. This verifies the tool is functional, not merely present on PATH.
1. `check_claude_code`: Runs `claude --dangerously-skip-permissions --version`. Extracts version string on success.
2. `check_svp_plugin`: Calls `_find_plugin_root()`. Verifies the manifest file exists.
3. `check_api_credentials`: Checks `ANTHROPIC_API_KEY` env var first. Falls back to `claude --dangerously-skip-permissions auth status` (the flag is required because `claude` launched from a subprocess without it may hang waiting for interactive permission approval). Provides guidance on failure.
4. `check_conda`: Runs `conda --version`. Extracts version on success.
5. `check_python`: Runs `sys.executable --version`. Parses version and verifies >= 3.10.
6. `check_pytest`: Runs `sys.executable -m pytest --version`. Extracts version on success.
7. `check_git`: Runs `git --version`, then `git config user.name` and `git config user.email`. Fails if user is not configured, with guidance to run `git config --global`.
8. `check_network`: Runs `curl -s -o /dev/null -w %{http_code} --connect-timeout 5 https://api.anthropic.com`. Falls back to DNS resolution via `socket.getaddrinfo` if curl is unavailable.
- `run_all_prerequisites` runs all 8 checks in order and returns a list of `(name, passed, message)` tuples.

**Project setup:**
- `create_project_directory(project_name, parent_dir)` creates all directories listed in `PROJECT_DIRS` under `parent_dir/project_name`. Raises `FileExistsError` if the project directory already exists. Returns the created project root path.
- `copy_scripts_to_workspace(plugin_root, project_root)` copies the entire `scripts/` directory (files and subdirectories) from the plugin to the project workspace. Raises `RuntimeError` if the plugin's scripts/ directory does not exist.
- `generate_claude_md(project_root, project_name)` tries to load and execute `scripts/templates/claude_md.py` (from Unit 22) using `importlib.util`. If the template module is available, calls its `render_claude_md(project_name)` function. If not available, falls back to `_generate_claude_md_fallback`.
- `_generate_claude_md_fallback(project_name)` returns a complete CLAUDE.md string inline, containing: the SVP-managed project header, the "On Session Start" instruction to run the routing script, the six-step action cycle, the verbatim relay rule, the "Do Not Improvise" section, the human input deferral rule, and the reference to the orchestration skill. This fallback must produce a fully functional CLAUDE.md without any external dependencies.
- `write_initial_state(project_root, project_name)` tries to load `scripts/templates/pipeline_state_initial.json`. Falls back to constructing the initial state dict inline (stage "0", sub_stage "hook_activation", all counters at zero/null, empty lists). Sets `project_name`, `created_at`, and `updated_at` to current UTC ISO timestamp. Writes to `pipeline_state.json`.
- `write_default_config(project_root)` tries to copy `scripts/templates/svp_config_default.json`. Falls back to writing a default config inline with at minimum: `iteration_limit`, `models` dict (with `test_agent`, `implementation_agent`, `help_agent`, `default` keys), `context_budget_override`, `context_budget_threshold`, `compaction_character_threshold`, `auto_save`, `skip_permissions`.
- `write_readme_svp(project_root)` tries to copy `scripts/templates/readme_svp.txt`. Falls back to writing a static notice inline explaining the two-layer protection system and how to use the `svp` command.

**Hook copying:** During `_handle_new_project` and `_handle_restore`, the launcher copies hooks from the plugin's `hooks/` directory to the project's `.claude/` directory. This includes `hooks.json` and the `scripts/` subdirectory containing hook shell scripts. Per spec Section 19.2, the launcher rewrites hook script paths during the copy operation so they reference the correct location within the project's `.claude/scripts/` directory (e.g., `bash .claude/scripts/write_authorization.sh`).

**Filesystem permissions (`set_filesystem_permissions`):**
- A single function with a `read_only: bool` parameter.
- When `read_only=True`: runs `chmod -R a-w` on the project root via subprocess. Best-effort (catches errors from files owned by other users).
- When `read_only=False`: runs `chmod -R u+w` on the project root via subprocess.
- The delivered repository (`projectname-repo/`) is never made read-only.

**Session lifecycle:**
- `launch_claude_code(project_root, plugin_dir)` creates a copy of the environment (`os.environ.copy()`), sets `SVP_ENV_VAR` to `"1"` in the copy (NOT in the launcher's own environment). Reads `skip_permissions` from config, defaulting to `True` if the config is missing or unreadable (because launching `claude` without `--dangerously-skip-permissions` from a subprocess hangs waiting for interactive permission approval). Builds command: `["claude"]` plus `"--dangerously-skip-permissions"` if enabled, plus the initial prompt `"run the routing script"`. Runs via `subprocess.run(cmd, cwd=project_root, env=env)`. Returns the exit code.
- `detect_restart_signal(project_root)` reads `.svp/restart_signal` if it exists, returns its content (stripped). Returns None if no signal file.
- `clear_restart_signal(project_root)` deletes the signal file using `unlink(missing_ok=True)`.
- `run_session_loop(project_root, plugin_dir)` implements: `while True: restore permissions -> launch claude code -> check restart signal -> if signal: clear signal, set read-only, print transition, loop -> if no signal: set read-only, print exit message, break`. Returns the final exit code.

**Resume:**
- `detect_existing_project(directory)` returns True if both `pipeline_state.json` and `.svp/` exist in the directory.
- `resume_project(project_root, plugin_dir)` reads the state file to display current stage info (with graceful handling of malformed JSON, permission errors). Then calls `run_session_loop`.

**Command handlers:**
- `_handle_new_project` creates directory structure, copies scripts, generates CLAUDE.md, writes initial state, writes default config, writes README_SVP.txt, copies hooks, prints progress status for each step, then calls `run_session_loop`.
- `_handle_restore` validates that `--spec` and `--blueprint` files exist. Creates directory, copies scripts (from `--scripts-source` if provided, else from plugin), generates CLAUDE.md, writes default config, writes README_SVP.txt, copies hooks, injects the spec to `specs/stakeholder.md`, injects the blueprint to `blueprint/blueprint.md`, optionally injects context to `.svp/project_context.md`, writes pipeline state at `pre_stage_3`, then calls `run_session_loop`.
- `_handle_resume` calls `detect_existing_project` on cwd. If not found, prints guidance and returns 1. Otherwise calls `resume_project`.

**Entry point (`main`):**
- Parses args. Prints header. Runs all prerequisites and prints each result. If any fail, prints guidance and returns 1. Finds plugin root. Dispatches to the appropriate command handler. Returns exit code. Accepts optional `argv` for testing. Called as `if __name__ == "__main__": sys.exit(main())`.

### Tier 3 -- Dependencies

- **Unit 12 (Hook Configurations):** The launcher copies hook files during project creation and restore. The `SVP_PLUGIN_ACTIVE` variable name must match Unit 12's `non_svp_protection.sh`.
- **Unit 22 (Project Templates):** Template files are loaded at runtime from `scripts/templates/` (not imported as Python modules). The launcher has complete inline fallbacks for all templates, so it functions correctly even without Unit 22's template files.

Note: Unlike the previous blueprint version, Unit 24 does NOT depend on Units 2 or 3 at the Python import level. The launcher reads `pipeline_state.json` as a plain JSON file for resume display. Initial state and default config are written inline with template-file fallbacks. This is the self-containment invariant: no Python imports from other units.

---

*End of blueprint.*

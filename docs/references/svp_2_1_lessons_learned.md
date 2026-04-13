# SVP 2.2 Lessons Learned — Bug Catalog

## Part 1: Bug Catalog

### Bug S3-1: state_hash spec ambiguity (Unit 5)

- **Bug number:** S3-1
- **How caught:** Stage 3 test generation — test agent wrote impossible self-referential hash assertion
- **Test file:** `tests/regressions/test_bug_s3_1_2_4_5_spec_clarity.py`
- **Description:** Spec Section 22.4 said state_hash is "SHA-256 hex digest of the pipeline_state.json file on disk, read immediately before each build log write." But save_state writes the hash INTO the file, creating self-referential ambiguity. The hash in the file is always the hash of the previous file state, not the current one.
- **Root cause pattern:** P7 (Specification Omission) — spec was ambiguous about hash timing, leading to impossible test expectations.
- **Prevention rule:** When specifying hash-based integrity fields, always clarify the temporal relationship: hash of state before or after the current write.

### Bug S3-2: Stub sentinel format inconsistency (Unit 6)

- **Bug number:** S3-2
- **How caught:** Stage 3 stub generation — agent produced `# SVP-GENERATED-STUB` instead of `__SVP_STUB__ = True`
- **Test file:** `tests/regressions/test_bug_s3_1_2_4_5_spec_clarity.py`
- **Description:** Stub generation agents inconsistently produce sentinel format. Spec requires `__SVP_STUB__ = True  # DO NOT DELIVER` (Python-assignable variable). One agent produced a comment-style sentinel. The compliance scanner relies on exact string matching.
- **Root cause pattern:** P7 (Specification Omission) — spec defined the sentinel format but did not mandate that prepare_task.py inject it verbatim into the stub generation prompt.
- **Prevention rule:** When a downstream consumer (compliance scanner) relies on exact string matching, the upstream producer (stub generator) must receive the exact string from a single source of truth (LANGUAGE_REGISTRY), not improvise.

### Bug S3-3: Test agent writes stub-detection tests (Unit 9)

- **Bug number:** S3-3
- **How caught:** Stage 3 test generation — test agent used `pytest.raises(NotImplementedError)` for 6 CLI behavioral tests
- **Test file:** `tests/regressions/test_bug_s3_3_6_9_test_agent_prohibitions.py`
- **Description:** Test agent used `pytest.raises(NotImplementedError)` for behavioral tests. These test that the stub is not implemented — they don't test actual behavior. They always fail against the real implementation.
- **Root cause pattern:** P14 (Agent Definition Gap) — the test agent definition lacked an explicit prohibition against testing stub behavior instead of contract behavior.
- **Prevention rule:** Agent definitions must explicitly prohibit anti-patterns that agents are likely to produce. Prohibitions are more effective than positive instructions for preventing known failure modes.

### Bug S3-4: Stub sentinel prompt standardization (systemic)

- **Bug number:** S3-4
- **How caught:** Stage 3 stub generation — multiple agents producing different sentinel styles
- **Test file:** `tests/regressions/test_bug_s3_1_2_4_5_spec_clarity.py`
- **Description:** The stub generation prompt doesn't consistently inject the exact sentinel string. Different agents produce different sentinel styles because the exact string isn't injected into the prompt.
- **Root cause pattern:** P7 (Specification Omission) — spec and blueprint did not mandate sentinel injection from LANGUAGE_REGISTRY into the stub generation task prompt.
- **Prevention rule:** When multiple agents must produce identical output format, the exact format string must be injected into every agent's task prompt from a single canonical source.

### Bug S3-5: state_hash timing in save_state (spec + blueprint)

- **Bug number:** S3-5
- **How caught:** Stage 3 test generation — semantic confusion about which file state the hash represents
- **Test file:** `tests/regressions/test_bug_s3_1_2_4_5_spec_clarity.py`
- **Description:** Spec says state_hash is computed "immediately before each build log write" but save_state computes it during state serialization. The blueprint should clarify: save_state reads the existing file bytes, computes hash, stores in new state, then writes.
- **Root cause pattern:** P7 (Specification Omission) — related to S3-1. Same ambiguity, different manifestation.
- **Prevention rule:** Same as S3-1. Hash timing must be explicit in both spec and blueprint.

### Bug S3-6: Test agent uses pytest.skip instead of failing (Unit 11)

- **Bug number:** S3-6
- **How caught:** Stage 3 red run — 51 tests SKIPPED instead of FAILED, producing misleading red run result
- **Test file:** `tests/regressions/test_bug_s3_3_6_9_test_agent_prohibitions.py`
- **Description:** Test agent used `pytest.skip("Not yet implemented")` when stub raises NotImplementedError, causing red run to show 0 failures. This would trigger the defective-test retry path instead of confirming tests are meaningful.
- **Root cause pattern:** P14 (Agent Definition Gap) — test agent definition did not prohibit `pytest.skip` as a NotImplementedError handler.
- **Prevention rule:** Red run signal integrity: tests must fail naturally against stubs. Any mechanism that converts failures to skips (pytest.skip, pytest.mark.skip, try/except with pass) defeats the red run verification.

### Bug S3-7: Unit 16 cmd_clean 14 test failures on green run

- **Bug number:** S3-7
- **How caught:** Stage 3 green run — 14 tests in TestCmdClean fail with AttributeError
- **Test file:** `tests/regressions/test_bug_s3_7_cmd_clean_mocks.py`
- **Description:** Tests patch `load_config` which does not exist in the cmd_clean implementation. The test agent assumed cmd_clean uses load_config based on other cmd_* functions, but cmd_clean only uses derive_env_name, load_toolchain, resolve_command, and load_state.
- **Root cause pattern:** P14 (Agent Definition Gap) + P1 (Incomplete Dependency Specification) — blueprint did not specify which functions cmd_clean actually calls, so the test agent guessed wrong.
- **Prevention rule:** Blueprint contracts for command functions should explicitly list which upstream functions they call and which they do NOT call, especially when sibling functions have different dependency patterns.

### Bug S3-8: Unit 14 dispatch bypasses Unit 6 transition functions

- **Bug number:** S3-8
- **How caught:** Stage 3 code review — orchestrator observed dispatch using deepcopy + direct field assignment instead of transition functions
- **Test file:** `tests/regressions/test_bug_s3_8_dispatch_transitions.py`
- **Description:** dispatch_gate_response and dispatch_agent_status set 80+ state fields directly via deepcopy instead of calling Unit 6 transition functions. Blueprint contracts explicitly require transition function calls. Direct assignment bypasses validation preconditions.
- **Root cause pattern:** P2 (State Management Assumptions) — implementation agent chose to bypass transition functions "to avoid validation conflicts" without understanding that the validation IS the point.
- **Prevention rule:** State transition functions exist to enforce invariants. Implementation agents must use them even when direct assignment appears simpler. If transition preconditions are too strict, the fix is to relax the preconditions, not bypass the functions.

### Bug S3-9: Unit 19 test wrong import path

- **Bug number:** S3-9
- **How caught:** Stage 3 test collection — ModuleNotFoundError from `from unit_19.stub import`
- **Test file:** `tests/regressions/test_bug_s3_3_6_9_test_agent_prohibitions.py`
- **Description:** Test agent generated `from unit_19.stub import` instead of `from src.unit_19.stub import`. The bare import fails because `unit_19` is not a top-level package.
- **Root cause pattern:** P14 (Agent Definition Gap) — test agent definition did not mandate the `src.` prefix import convention.
- **Prevention rule:** Import path conventions must be explicitly stated in agent definitions. Never assume agents will infer workspace layout conventions.

### Bug S3-10: Stub generator produces unimportable module-level constants

- **Bug number:** S3-10
- **How caught:** Pass 2 red run — ImportError on `from src.unit_1.stub import ARTIFACT_FILENAMES`
- **Test file:** `tests/regressions/test_bug_s3_10_stub_constant_defaults.py`
- **Description:** SVP 2.2's stub generator produces bare type annotations for module-level constants (`X: Dict[str, str]`) instead of annotated assignments with defaults (`X: Dict[str, str] = {}`). Bare annotations at module level don't create attributes, so `import` fails.
- **Root cause pattern:** P7 (Specification Omission) — spec and blueprint specified stub behavior for functions (raise NotImplementedError) and class attributes (= None) but not for module-level constants.
- **Prevention rule:** Blueprint must specify stub behavior for every AST node type the generator encounters: functions, classes, class attributes, AND module-level constants.

### Bug S3-11: dispatch_command_status missing compliance_scan handler

- **Bug number:** S3-11
- **How caught:** Pass 2 Stage 5 — ValueError crash when routing dispatched compliance_scan
- **Test file:** `tests/regressions/test_bug_s3_11_12_stage5_dispatch.py`
- **Description:** dispatch_command_status handles stub_generation, test_execution, quality_gate, and unit_completion but not compliance_scan or structural_check. Stage 5 routing emits both command types.
- **Root cause pattern:** P1 (Incomplete Dependency Specification) — dispatch contract didn't enumerate all command types routing emits
- **Prevention rule:** dispatch_command_status must handle every command_type value that route() can emit. Blueprint must enumerate all command types exhaustively.

### Bug S3-12: repo_complete ignores pass_ for pass transition

- **Bug number:** S3-12
- **How caught:** Pass 2 Stage 5 — routing returned pipeline_complete instead of pass_transition gate
- **Test file:** `tests/regressions/test_bug_s3_11_12_stage5_dispatch.py`
- **Description:** route() at sub_stage repo_complete always returns pipeline_complete, ignoring pass_. For E/F self-builds, it should advance to pass_transition to present gate_pass_transition_post_pass1/2.
- **Root cause pattern:** P7 (Specification Omission) — repo_complete handler didn't account for two-pass protocol
- **Prevention rule:** Every terminal sub_stage must check pass_ before returning pipeline_complete.

### Bug S3-13: Stub filename uses unit number prefix (Unit 10)

- **Bug number:** S3-13
- **How caught:** Stage 3 stub generation -- generated files named `unit_N_stub.py` but imports expected `stub.py`
- **Test file:** `tests/regressions/test_bug_s3_13_14_command_cycle.py`
- **Description:** The stub generator produced output files named `unit_{N}_stub{file_ext}` (e.g., `unit_5_stub.py`). The unit number is already encoded in the directory path (`src/unit_N/`), so the filename should be `stub{file_ext}`. The redundant unit number in the filename caused import mismatches because test agents and implementation agents expected `from src.unit_N.stub import ...`.
- **Root cause pattern:** P7 (Specification Omission) -- spec did not explicitly specify the output filename convention for generated stubs.
- **Prevention rule:** When a generated artifact lives in a unit-specific directory, the filename should not redundantly encode the unit number. Spec must specify the exact output filename.

### Bug S3-14: update_state_main lacks --command dispatch path (Unit 14)

- **Bug number:** S3-14
- **How caught:** Stage 3 action cycle -- run_command action blocks had no POST command, breaking the six-step cycle
- **Test file:** `tests/regressions/test_bug_s3_13_14_command_cycle.py`
- **Description:** `update_state_main` only accepted `--phase` (for agent dispatch) and `--gate-id` (for gate dispatch). It had no `--command` path for command status dispatch. As a result, `run_command` action blocks could not include a POST command that invoked `update_state.py --command <type>`. The six-step action cycle was incomplete for command actions -- the orchestrator ran the command but had no POST step to advance pipeline state.
- **Root cause pattern:** P1 (Incomplete Dependency Specification) -- the update_state_main CLI did not enumerate the command dispatch path that routing depends on.
- **Prevention rule:** Every action type that routing emits must have a corresponding dispatch path in update_state_main. The CLI interface must cover all three dispatch modes: agent (--phase), gate (--gate-id), and command (--command).

### Bug S3-15: Oracle session activation missing transition functions (Unit 6, Unit 14)

- **Bug number:** S3-15
- **How caught:** Stage 3 code review -- oracle session activated via direct field assignment instead of transition functions
- **Test file:** `tests/regressions/test_bug_s3_15_oracle_session.py`
- **Description:** Oracle session activation (`oracle_session_active = True`, `oracle_phase = "dry_run"`) and deactivation were done via direct field assignment in Unit 14 routing code, bypassing Unit 6 transition functions. This skipped precondition validation (e.g., preventing double activation) and was inconsistent with the debug session pattern, which uses `enter_debug_session`/`complete_debug_session`/`abandon_debug_session`. Three new transition functions (`enter_oracle_session`, `complete_oracle_session`, `abandon_oracle_session`) were added to Unit 6, and all inline oracle state manipulation in Unit 14 was replaced with calls to these functions.
- **Root cause pattern:** P2 (State Management Assumptions) -- implementation bypasses state transition functions, losing validation.
- **Prevention rule:** Every session lifecycle (debug, oracle, etc.) must use dedicated transition functions in Unit 6. Direct field assignment of session-active flags is prohibited.

### Bug S3-16: Stage 4 test_execution dispatch missing gate presentations (Unit 14)

- **Bug number:** S3-16
- **How caught:** Stage 3 code review -- dispatch_command_status for Stage 4 test_execution just increments red_run_retries without setting sub_stage for gate presentation
- **Test file:** `tests/regressions/test_bug_s3_16_stage4_dispatch.py`
- **Description:** `dispatch_command_status` for Stage 4 `test_execution` treated TESTS_FAILED and TESTS_ERROR identically: both just called `increment_red_run_retries(state)` without setting `sub_stage` for gate presentation or re-invocation. The spec requires three-way differentiation: TESTS_FAILED must present Gate 4.1 (`gate_4_1_integration_failure`); TESTS_ERROR must re-invoke the integration test author (set `sub_stage=None`); retries exhausted must present Gate 4.2 (`gate_4_2_assembly_exhausted`). The routing function `_route_stage_4` also lacked branches for `sub_stage="gate_4_1"` and `sub_stage="gate_4_2"`, meaning even if dispatch set the sub_stage correctly, routing would fall through to the default (invoke integration_test_author) instead of presenting the gate.
- **Root cause pattern:** P1 (Incomplete Dependency Specification) -- Stage 4 dispatch didn't differentiate failure modes per spec. The blueprint originally specified TESTS_ERROR as "same dispatch as TESTS_FAILED" but the spec's universal four-state rule required re-invocation.
- **Prevention rule:** Every test execution dispatch must implement the full four-state differentiation (PASSED/FAILED/ERROR/EXHAUSTED) with distinct state transitions per the universal dispatch rule. Routing must have explicit branches for every sub_stage value that dispatch can produce.

### Bug S3-17: Three gate dispatch routing errors (Unit 14)

- **Bug number:** S3-17
- **How caught:** Stage 3 code review -- gate dispatch handlers didn't match spec's routing requirements
- **Test file:** `tests/regressions/test_bug_s3_17_gate_dispatch_fixes.py`
- **Description:** Three gate dispatch handlers produced incorrect routing: (1) Gate 1.1 FRESH REVIEW left sub_stage as None, which routed to stakeholder_dialog instead of stakeholder_reviewer. Fix: set sub_stage to "spec_review" and add routing branch in _route_stage_1. (2) Gate 5.1 TESTS FAILED set sub_stage to "repo_test", which looped back to Gate 5.1 instead of re-entering the bounded fix cycle. Fix: set sub_stage to None so _route_stage_5 falls through to re-invoke git_repo_agent. (3) gate_pass_transition_post_pass1 PROCEED TO PASS 2 had no precondition check on deferred_broken_units, allowing pass 2 entry with unresolved broken units. Fix: raise ValueError when deferred_broken_units is non-empty.
- **Root cause pattern:** P7 (Specification Omission) -- gate dispatch handlers didn't match spec's routing requirements. The spec and blueprint described the intended behavior, but the implementation omitted the sub_stage assignments and precondition checks needed to achieve it.
- **Prevention rule:** Every gate dispatch handler must produce a sub_stage (or None) that the corresponding routing function maps to the correct next action. Verify each handler against the routing function's dispatch table, not just the handler's comment.

### Bug S3-18: Debug reassembly phase infinite loop (Unit 14)

- **Bug number:** S3-18
- **How caught:** Stage 3 routing analysis — routing loop detected in debug reassembly phase
- **Test file:** `tests/regressions/test_bug_s3_18_21_routing_loops.py`
- **Description:** `_route_debug` for `phase == "reassembly"` unconditionally invoked `git_repo_agent` without checking `last_status`. After `REPO_ASSEMBLY_COMPLETE`, the debug phase stayed at "reassembly" and the agent was re-invoked indefinitely.
- **Root cause pattern:** P1 (Incomplete Dependency Specification) — missing two-branch check in reassembly phase handler
- **Prevention rule:** Every routing handler that invokes an agent must have a two-branch check: one branch for the agent's terminal status and one for the initial invocation. Single-branch handlers create infinite loops.

### Bug S3-19: Diagnostic escalation infinite loop (Unit 14)

- **Bug number:** S3-19
- **How caught:** Stage 3 routing analysis — routing loop detected in diagnostic escalation
- **Test file:** `tests/regressions/test_bug_s3_18_21_routing_loops.py`
- **Description:** In `_route_stage_3`, when `fix_ladder_position == "diagnostic"`, the code unconditionally invoked `diagnostic_agent` without checking if `DIAGNOSIS_COMPLETE` had been written. After the agent completed, the same invocation was issued again indefinitely.
- **Root cause pattern:** P1 (Incomplete Dependency Specification) — missing two-branch check in diagnostic escalation handler
- **Prevention rule:** Same as S3-18. All agent invocation routing must check for terminal status before re-invocation.

### Bug S3-20: Debug repair phase routing loop (Unit 14)

- **Bug number:** S3-20
- **How caught:** Stage 3 routing analysis — repair phase directly invoked git_repo_agent instead of transitioning phases
- **Test file:** `tests/regressions/test_bug_s3_18_21_routing_loops.py`
- **Description:** When `phase == "repair"` and `last_status == "REPAIR_COMPLETE"`, routing directly invoked `git_repo_agent` for reassembly. After git_repo_agent completed, the debug phase was still "repair", so the repair handler fell through to re-invoke `repair_agent`, creating an infinite loop.
- **Root cause pattern:** P2 (State Management Assumptions) — repair handler bypassed phase transition, causing state to remain in "repair" after reassembly
- **Prevention rule:** Agent completion must transition the debug phase to the next phase before re-routing. Direct invocation of the next agent without phase transition creates state/action mismatches.

### Bug S3-21: Missing dispatch_command_status handlers for debug commands (Unit 14)

- **Bug number:** S3-21
- **How caught:** Stage 3 routing analysis — three command types had no dispatch handler
- **Test file:** `tests/regressions/test_bug_s3_18_21_routing_loops.py`
- **Description:** Three command types emitted by `_route_debug` had no handler in `dispatch_command_status`: `lessons_learned`, `debug_commit`, and `stage3_reentry`. When the POST command called `update_state.py --command <type>`, it raised `ValueError: Unknown command_type`.
- **Root cause pattern:** P1 (Incomplete Dependency Specification) — debug routing emitted command types not covered by dispatch function
- **Prevention rule:** Every command type emitted in a `run_command` action block must have a corresponding handler in `dispatch_command_status`. Dispatch exhaustiveness tests should cover command types as well as agent statuses.

### Bug S3-23: Debug re-entry loop prevention (Unit 14)

- **Bug number:** S3-23
- **How caught:** Oracle invocation 4 — systematic routing loop analysis of debug session paths
- **Test file:** `tests/regressions/test_bug_s3_23_29_oracle_inv4.py`
- **Description:** `dispatch_command_status` for `stage3_reentry` set `sub_stage = "stub_generation"` but left `debug_session.phase = "stage3_reentry"`. Since `_route_debug` intercepts all routing when `debug_session` is active, it re-dispatched the stage3_reentry command on every cycle — infinite loop.
- **Root cause pattern:** P2 (State Management Assumptions) — handler updated sub_stage but not debug phase, leaving routing in wrong dispatch branch
- **Prevention rule:** State transitions must update all relevant state fields atomically. Partial updates that change sub_stage without changing the routing-relevant phase field create routing mismatches.

### Bug S3-24: Gate 6.3 reclassification counter not incremented (Unit 14)

- **Bug number:** S3-24
- **How caught:** Oracle invocation 4 — gate response analysis
- **Test file:** `tests/regressions/test_bug_s3_23_29_oracle_inv4.py`
- **Description:** RECLASSIFY BUG at Gate 6.3 read `triage_refinement_count` and checked the limit but never wrote back an incremented value. The counter stayed at 0 across all reclassifications, making the 3-reclassification limit unenforceable.
- **Root cause pattern:** P2 (State Management Assumptions) — read-check-but-no-write pattern on a counter field
- **Prevention rule:** Any state field that enforces a limit must be incremented in the same handler that checks it. Read-only checks without writes are no-ops.

### Bug S3-25: Gate 4.1a no-op responses (Unit 14)

- **Bug number:** S3-25
- **How caught:** Oracle invocation 4 — gate response handler analysis
- **Test file:** `tests/regressions/test_bug_s3_23_29_oracle_inv4.py`
- **Description:** Both HUMAN FIX and ESCALATE responses at Gate 4.1a were no-ops (just copied state without modifying it). ESCALATE must advance to `gate_4_2` sub-stage. HUMAN FIX must reset `sub_stage` to `None` and `red_run_retries` to 0 for a fresh integration test attempt.
- **Root cause pattern:** P7 (Specification Omission) — gate response branches contained `pass` statements with comments describing intended behavior that was never implemented
- **Prevention rule:** Gate response handlers must never be pass-through stubs. Every gate response branch must produce a measurably different state than the input state.

### Bug S3-29: Upstream stub filename overwriting (Unit 10)

- **Bug number:** S3-29
- **How caught:** Oracle invocation 4 — stub generation path analysis
- **Test file:** `tests/regressions/test_bug_s3_23_29_oracle_inv4.py`
- **Description:** The S3-13 fix changed the upstream stub filename from `unit_N_stub{ext}` to `stub{ext}` in `generate_upstream_stubs`, but this was incorrect — that fix should only have applied to `main()` (current unit stub). In `generate_upstream_stubs`, all upstream stubs wrote to the same `stub.py` file, with each overwriting the previous.
- **Root cause pattern:** P1 (Incomplete Dependency Specification) — fix for S3-13 applied too broadly, changing filenames in the wrong function
- **Prevention rule:** When fixing filename conventions, verify the fix scope: distinguish between the current unit's stub (bare filename in main()) and upstream dependency stubs (prefixed filenames in generate_upstream_stubs).

### Bug S3-36: Quality gate QUALITY_ERROR and QUALITY_AUTO_FIXED unreachable (Unit 15)

- **Bug number:** S3-36
- **How caught:** Stage 3 code review -- `had_error` and `auto_fixed` initialized to False and never set to True
- **Test file:** `tests/regressions/test_bug_s3_36_38_oracle_inv5.py`
- **Description:** In `_execute_gate_operations` (and equivalent loops in `_run_plugin_markdown` and `_run_plugin_json`), the variables `had_error` and `auto_fixed` are initialized to `False` but the execution loop never modifies them. The classification logic checks these variables but they can never be `True`, making QUALITY_ERROR and QUALITY_AUTO_FIXED statuses unreachable. Every execution classifies as either QUALITY_CLEAN or QUALITY_RESIDUAL.
- **Root cause pattern:** P1 (Incomplete Dependency Specification) -- the classification logic depends on variables that the execution loop does not update.
- **Prevention rule:** When a function has a classification block that branches on boolean flags, verify that every branch is reachable by tracing the flag assignments in the preceding code. Dead branches indicate missing logic in the execution path.

### Bug S3-37: Hooks JSON malformed structure (Unit 17)

- **Bug number:** S3-37
- **How caught:** Stage 3 code review -- HOOKS_JSON_SCHEMA uses `"handler"` (object) instead of `"hooks"` (array)
- **Test file:** `tests/regressions/test_bug_s3_36_38_oracle_inv5.py`
- **Description:** `HOOKS_JSON_SCHEMA` uses `{"matcher": "Write", "handler": {"type": "command", ...}}` instead of the spec-required `{"matcher": "Write", "hooks": [{"type": "command", ...}]}`. The Claude Code hooks configuration format requires a `"hooks"` array at the entry level, not a singular `"handler"` object.
- **Root cause pattern:** P7 (Specification Omission) -- the spec described the format but the implementation used the wrong key name and structure.
- **Prevention rule:** When generating configuration that conforms to an external format specification (Claude Code hooks), validate the generated output against the canonical format before deploying. A structural test asserting key names prevents drift.

### Bug S3-38: New project initial sub_stage (Unit 29)

- **Bug number:** S3-38
- **How caught:** Stage 3 code review -- create_new_project writes `"sub_stage": None` instead of `"sub_stage": "hook_activation"`
- **Test file:** `tests/regressions/test_bug_s3_36_38_oracle_inv5.py`
- **Description:** `create_new_project` writes `"sub_stage": None` in the initial `pipeline_state.json`. The spec requires `"sub_stage": "hook_activation"` so that the routing script's first action block directs the orchestrator to activate hooks before proceeding to the setup dialog.
- **Root cause pattern:** P7 (Specification Omission) -- the initial state template used a generic None default instead of the spec-required initial sub_stage.
- **Prevention rule:** When pipeline_state.json has a required initial value for a field, the spec must explicitly document it and the initial state template must match. Regression tests should verify initial state invariants.

### Bug S3-41: Setup agent definition wrong terminal status names (Unit 18)

- **Bug number:** S3-41
- **How caught:** Stage 3 code review -- SETUP_AGENT_DEFINITION uses `PROFILE_DIALOG_COMPLETE` and `CONTEXT_DIALOG_COMPLETE` but dispatch_agent_status expects `PROFILE_COMPLETE` and `PROJECT_CONTEXT_COMPLETE`
- **Test file:** `tests/regressions/test_bug_s3_41_42_status_names.py`
- **Description:** `SETUP_AGENT_DEFINITION` string used `PROFILE_DIALOG_COMPLETE` and `CONTEXT_DIALOG_COMPLETE` as terminal statuses. But `dispatch_agent_status` in Unit 14 expects `PROJECT_CONTEXT_COMPLETE`, `PROJECT_CONTEXT_REJECTED`, and `PROFILE_COMPLETE`. The mismatched names would cause the setup agent to emit status lines that the routing script does not recognize, crashing the pipeline.
- **Root cause pattern:** P14 (Agent Definition Gap) -- agent definition terminal status names were not verified against the dispatch handler's expected values.
- **Prevention rule:** Agent definition terminal status names must be character-identical to the values handled by `dispatch_agent_status`. Regression tests should assert this invariant.

### Bug S3-42: dispatch_agent_status missing HINT_BLUEPRINT_CONFLICT for Stage 3 agents (Unit 14)

- **Bug number:** S3-42
- **How caught:** Stage 3 code review -- implementation_agent handler only handles IMPLEMENTATION_COMPLETE, not HINT_BLUEPRINT_CONFLICT
- **Test file:** `tests/regressions/test_bug_s3_41_42_status_names.py`
- **Description:** `dispatch_agent_status` for `implementation_agent`, `test_agent`, `coverage_review_agent`, and `diagnostic_agent` did not handle `HINT_BLUEPRINT_CONFLICT`. When any of these agents received a hint that contradicted the blueprint and correctly emitted `HINT_BLUEPRINT_CONFLICT`, the dispatch function raised `ValueError` instead of routing to `gate_hint_conflict`.
- **Root cause pattern:** P1 (Incomplete Dependency Specification) -- the dispatch handler was not specified to handle all statuses that hint-receiving agents can emit.
- **Prevention rule:** Every agent that can receive hints must have `HINT_BLUEPRINT_CONFLICT` handled in `dispatch_agent_status`. The set of hint-receiving agents must be explicitly documented and verified.

### Bug S3-43: Pass 2 repo missing CHANGELOG.md, README.md, LICENSE

- **Bug number:** S3-43
- **How caught:** Human inspection of Pass 2 delivered repo
- **Test file:** `tests/regressions/test_bug_s3_43_restore_references.py`
- **Description:** restore_project does not copy the references/ directory from the source workspace. This means carry-forward artifacts (existing_readme.md, lessons_learned.md) are not available in the Pass 2 workspace, causing the git repo agent to skip README/CHANGELOG/LICENSE generation.
- **Root cause pattern:** P1 (Incomplete Dependency Specification) -- restore_project contract didn't include reference document carry-forward.
- **Prevention rule:** restore_project must copy ALL workspace directories that downstream agents depend on, not just the minimum set (spec, blueprint, context, scripts, profile).

### Bug S3-44: ORACLE_ALL_CLEAR routes to Gate 7B instead of exit

- **Bug number:** S3-44
- **How caught:** Oracle invocation 7 (proper) — dry run trajectory analysis of delivered repo routing
- **Test file:** `tests/regressions/test_bug_s3_44_45_oracle_gates.py`
- **Description:** `_route_oracle` green_run phase treats ORACLE_ALL_CLEAR identically to ORACLE_FIX_APPLIED, sending both to Gate 7B (fix plan review). ALL_CLEAR means no bugs — presenting a fix plan review gate is nonsensical. Should exit the oracle session directly.
- **Root cause pattern:** P7 (Specification Omission) — oracle exit paths not differentiated in routing implementation
- **Prevention rule:** Every distinct agent terminal status must have its own routing branch. Combined status checks hide semantic differences.

### Bug S3-45: 5 gates unreachable via routing

- **Bug number:** S3-45
- **How caught:** Oracle invocation 7 (proper) — systematic gate reachability analysis
- **Test file:** `tests/regressions/test_bug_s3_44_45_oracle_gates.py`
- **Description:** gate_5_2_assembly_exhausted, gate_5_3_unused_functions, and gate_4_1a are defined in GATE_VOCABULARY and dispatch_gate_response but no routing path in route() ever presents them. They are dispatch-reachable but routing-unreachable, making them dead code in practice.
- **Root cause pattern:** P1 (Incomplete Dependency Specification) — gates defined in vocabulary without corresponding routing branches
- **Prevention rule:** Every gate in GATE_VOCABULARY that can be reached through normal pipeline operation must have a routing branch that presents it. Gate reachability should be a structural regression test.

### Bug S3-46: Bug fix completion audit not enforced structurally

- **Bug number:** S3-46
- **How caught:** Human observed S3-44/45 missing lessons learned and Pass 2 repo propagation
- **Test file:** `tests/regressions/test_bug_fix_completeness.py`
- **Description:** The 9-item orchestrator oversight checklist (Section 12.18.14) is procedural — it depends on the orchestrator remembering to verify each item. Fix agents can complete code fixes and tests but skip lessons learned or repo propagation with nothing catching the gap.
- **Root cause pattern:** P15 (Procedural Check Without Structural Enforcement) — NEW PATTERN. Procedural checks that depend on orchestrator memory are unreliable. Every check that matters must be a runnable test.
- **Prevention rule:** Every completion requirement in the oversight checklist that can be expressed as a file-existence or content-match check must have a corresponding structural regression test.

### Bug S3-47: Stub generator must use TYPE_CHECKING guards for upstream imports (Unit 10)

- **Bug number:** S3-47
- **How caught:** Stage 3 stub generation — stubs with upstream imports (e.g., `from engine import Engine`) fail to import when the upstream module is not on `sys.path` in the stub's workspace directory layout
- **Test file:** `tests/regressions/test_bug_s3_47_stub_type_checking.py`
- **Description:** The stub generator preserved all imports at module level, including non-stdlib (upstream) imports. Since stub bodies are all `raise NotImplementedError()`, upstream imports are only needed for type annotations, not runtime execution. When stubs are loaded in environments where the upstream module is not on `sys.path` (e.g., test collection in a unit-isolated workspace), the import fails and the stub is not importable. The fix separates stdlib imports (kept at module level) from upstream imports (wrapped in `if TYPE_CHECKING:` guard) and prepends `from __future__ import annotations` to enable string-based annotation evaluation.
- **Root cause pattern:** P7 (Specification Omission) — spec and blueprint did not specify that upstream imports in stubs should be guarded, since stubs never execute upstream code at runtime.
- **Prevention rule:** Generated stub files must only import at runtime what they actually execute. Imports needed solely for type annotations must be behind `TYPE_CHECKING` guards with `from __future__ import annotations`.

### Bug S3-48: R test source path resolution missing

- **Bug number:** S3-48
- **How caught:** GoL R build -- testthat source("src/unit_1/stub.R") failed due to working directory change
- **Test file:** `tests/regressions/test_bug_s3_48_r_source_path.py`
- **Description:** Python has pyproject.toml pythonpath for test import resolution. R had no equivalent. When testthat runs test files, it may change the working directory, causing relative source() paths to break. The fix: infrastructure setup generates tests/testthat/helper-svp.R which testthat auto-sources, providing svp_source() that resolves paths relative to the project root.
- **Root cause pattern:** P7 (Specification Omission) -- spec delegated R path resolution to "language-specific mechanism" but never defined it.
- **Prevention rule:** Every language supported by SVP must have an explicit, deterministic test import/source path resolution mechanism documented in the spec and implemented in infrastructure setup.

### Bug S3-49: Stub generator cross-language upstream parse failure

- **Bug number:** S3-49
- **How caught:** GoL Mixed (Python+R) build -- Python unit 2 with R upstream unit 1 failed because generate_upstream_stubs used the caller's Python parser to parse R Tier 2 signatures
- **Test file:** `tests/regressions/test_bug_s3_49_cross_language_stubs.py`
- **Description:** `generate_upstream_stubs` used the caller's `language` parameter for all upstream units, passing it to `parse_signatures` and `generate_stub`. In mixed-language projects, upstream units may be written in a different language. The fix: detect each upstream unit's language from `dep_unit.languages` (set by the blueprint extractor) and use the correct language's signature parser, stub generator, and file extension.
- **Root cause pattern:** P7 (Specification Omission) -- spec described upstream stub generation but never specified that each upstream unit must be parsed with its own language, not the caller's.
- **Prevention rule:** Any function that iterates over units from the blueprint must check each unit's language tag independently rather than assuming a single language for the entire project.

### Bug S3-50: Pass 2 repo missing environment.yml

- **Bug number:** S3-50
- **How caught:** Human inspection of Pass 2 repo
- **Test file:** `tests/regressions/test_bug_s3_50_environment_yml.py`
- **Description:** The S3-43 manual copy patched README.md, CHANGELOG.md, and LICENSE but missed environment.yml. Without a structural test checking delivery artifact parity between Pass 1 and Pass 2 repos, the gap persisted.
- **Root cause pattern:** P15 (Procedural Check Without Structural Enforcement) — manual fix without structural verification missed one file.
- **Prevention rule:** The completion audit must check delivery artifact parity between Pass 1 and Pass 2 repos for all root-level files.

## Part 2: Pattern Catalog

| Pattern | Name | Description |
|---------|------|-------------|
| P1 | Incomplete Dependency Specification | Blueprint contracts don't enumerate all dependencies, allowing agents to guess wrong |
| P2 | State Management Assumptions | Implementation bypasses state transition functions, losing validation |
| P7 | Specification Omission | Spec is ambiguous or silent on a behavior, leading to inconsistent implementations |
| P14 | Agent Definition Gap (NEW) | Agent definition lacks explicit prohibition of a known anti-pattern, causing agents to produce defective output |
| P15 | Procedural Check Without Structural Enforcement (NEW) | A required check exists as instructions but not as a runnable test, allowing silent omission |

**P14 is a new pattern** identified during SVP 2.2 Stage 3. It applies whenever an LLM agent consistently produces a specific defective pattern that could be prevented by an explicit prohibition in the agent's definition. P14 bugs are systemic — they recur across units because the agent definition is shared.

## Part 3: Post-Delivery Plugin Assembly Lessons (Bugs S3-51 through S3-54)

### Lesson: Plugin Manifest and Component Assembly Gap

- **Bugs:** S3-51 (missing .claude-plugin dirs), S3-52 (missing agents/commands/hooks/skills dirs), S3-53 (empty manifest fields), S3-54 (pass_transition routing)
- **Discovery:** After Pass 2 delivery, attempting to install SVP 2.2 as a Claude Code plugin failed completely. The delivered repo had only `svp/scripts/` but none of the required plugin infrastructure.
- **Root causes:**
  1. Assembly functions focused on Python source code relocation but omitted plugin infrastructure files (non-code artifacts: markdown definitions, JSON configs, bash scripts).
  2. Plugin discovery requires `.claude-plugin/` directories with properly formatted JSON manifests. These were never generated because (a) no assembly code created them, and (b) the profile lacked the `plugin` metadata section needed to populate their fields.
  3. The routing function that sets the `pass_transition` sub-stage (`_route_stage_5`) didn't handle it — the handler existed only in `_route_stage_3` which is never called when stage is "5".
- **Prevention pattern:** When a pipeline produces a deliverable with a specific format requirement (Claude Code plugin), the assembler must have explicit extraction steps for EVERY component type, not just source code. Validation (Gate C) should verify that all required directories exist and have content, not just that manifest schemas are valid.
- **Routing invariant:** Any function that calls `advance_sub_stage(state, X)` must also handle `sub_stage == X`, either in the same function or via a guaranteed dispatch path. The handler must not rely on falling through to a different stage's routing function.

### Lesson: Workspace Synchronization After Two-Pass Build (Bug S3-55)

- **Bug:** S3-55 (Pass 1 artifacts not synchronized to Pass 2 workspace)
- **Discovery:** After Pass 2 delivery, the Pass 2 workspace was missing 16 regression tests, 204 lines of lessons learned, and 4 spec amendments accumulated during Pass 1's Stage 6.
- **Root cause:** The two-pass protocol specifies artifact carry-forward (spec/blueprint) from Pass 1 TO Pass 2 at `svp restore` time, but has no back-sync mechanism for artifacts accumulated during Pass 1's Stage 6 debug loop. Pass 2 starts fresh from Pre-Stage-3 and has no knowledge of Pass 1's post-delivery discoveries.
- **Prevention pattern:** Any multi-pass build protocol that creates a new workspace for a subsequent pass must include an explicit sync step that merges accumulated non-code artifacts from the previous pass. The sync must be automatic (not manual), idempotent, and must never touch rebuilt source code.

### Lesson: Plugin Manifest Path Format (Bug S3-56)

- **Bug:** S3-56 (marketplace.json source field and plugin.json path prefix)
- **Discovery:** Plugin wouldn't load in Claude Code. The `source` field pointed to `"./"` (repo root) instead of `"./svp"` (plugin subdirectory). Path fields in plugin.json used bare paths (`"commands/"`) instead of relative paths (`"./commands/"`).
- **Root cause:** `generate_marketplace_json()` hardcoded `"./"` as the source. The profile's plugin section was populated with bare paths. Neither was validated against the Claude Code plugin spec.
- **Prevention pattern:** Always validate generated manifests against the target platform's actual documentation, not just the SVP spec. Use a working reference (SVP 2.1) as a baseline comparison during Stage 5 Gate C validation.

## Part 4: Post-Delivery Plugin Readiness Lessons (Bugs S3-57 through S3-60)

### Lesson: Plugin Entry Point and Build Backend (Bug S3-57)

- **Bug:** S3-57 (missing pyproject.toml entry point and build backend)
- **Discovery:** The delivered repo's pyproject.toml lacked a `[project.scripts]` entry point for the CLI and had no `[build-system]` section, making the package uninstallable via `pip install`.
- **Root cause:** The assembly focused on relocating source files but did not update the build metadata to match the delivered repo's layout.
- **Prevention pattern:** Every deliverable that is a Python package must have a complete pyproject.toml with entry points and build-system metadata. Gate C should verify installability.

### Lesson: Agent Frontmatter Requirement (Bug S3-58)

- **Bug:** S3-58 (agent .md files missing YAML frontmatter)
- **Discovery:** Claude Code requires YAML frontmatter (`name`, `description`, `model`) on agent markdown files. All 21 agent files were generated with bare `# Heading` starts.
- **Root cause:** `assemble_plugin_components()` wrote agent definitions verbatim without injecting the required frontmatter block.
- **Prevention pattern:** When generating artifacts for an external platform, validate each artifact against the platform's schema requirements, not just content correctness.

### Lesson: hooks.json Array Schema (Bug S3-59)

- **Bug:** S3-59 (hooks.json used handler object instead of hooks array)
- **Discovery:** Claude Code requires `"hooks": [{"type": "command", ...}]` (array format). The generated hooks.json used `"handler": {"type": "command", ...}` (single object format).
- **Root cause:** The schema constant in Unit 17 was not updated to match the Claude Code spec even though the issue was documented as Bug S3-37 earlier.
- **Prevention pattern:** When a bug fix documents a schema requirement, verify the fix is applied to both the validation code AND the generation code. A schema fix that only updates validation but not generation is incomplete.

### Lesson: Missing Package Init File (Bug S3-60)

- **Bug:** S3-60 (missing svp/scripts/__init__.py in delivered repo)
- **Discovery:** The CLI entry point `svp.scripts.svp_launcher` could not resolve because the scripts directory lacked `__init__.py`.
- **Root cause:** The assembly step created and populated `svp/scripts/` but did not create the package init file.
- **Prevention pattern:** Any directory that is referenced as a Python package in imports or entry points must have an `__init__.py`. Gate C should verify package structure.

## Part 5: Carry-Forward and Oracle Lessons (Bugs S3-62, S3-63)

### Lesson: Carry-Forward Regression Test Chain (Bug S3-62)

- **Bug:** S3-62 (SVP 2.1 carry-forward regression tests missing from delivered plugin)
- **Discovery:** Regression tests from SVP 2.1 were not carried forward into the SVP 2.2 plugin's test directory, breaking the chain by which `create_new_project()` copies regression tests to new workspaces.
- **Root cause:** The carry-forward mechanism relies on the plugin containing tests, but the Pass 1 deliverable was assembled without including carry-forward tests (they accumulated after assembly).
- **Prevention pattern:** In a multi-pass build, test artifacts accumulated during one pass must be explicitly merged into the next pass's deliverable before assembly.

### Lesson: Oracle State Transition Functions Never Implemented (Bug S3-63)

- **Bug:** S3-63 (oracle session functions missing from Unit 6)
- **Discovery:** The oracle session management functions (`begin_oracle_session`, `advance_oracle_phase`, `abandon_oracle_session`) were specified in the blueprint but never implemented. Unit 14 worked around their absence with inline state manipulation.
- **Root cause:** The implementation agent for Unit 6 missed the oracle functions. Test collection errors were treated as skips rather than failures, hiding the gap.
- **Prevention pattern:** Test collection errors must be treated as failures, not skips. Any function that is imported in a test file but cannot be resolved indicates an implementation gap that must block stage progression.

### Lesson: Cross-Cutting Concern Without Integration Owner (Bug S3-65)

- **Bug:** S3-65 (Oracle ~40% implemented -- routing skeleton but no operational logic)
- **Root cause:** Oracle spans 8 units. Blueprint specified per-unit contributions but no unit was designated as the integration owner responsible for wiring the end-to-end lifecycle.
- **Prevention pattern P16:** When a spec feature touches 3+ units, the blueprint must: (1) designate one unit as integration owner, (2) include an explicit wiring checklist in that unit's Tier 3 contracts, (3) the checklist must reference specific function calls across units (not just "handles X").

### Lesson: Entry Point Script Completeness (Bug S3-66)

- **Bug:** S3-66 (routing.py and prepare_task.py missing __name__ guards)
- **Root cause:** Blueprint specifies function signatures but not script execution boilerplate. Implementation agents added __name__ guards inconsistently (2 of 4 scripts).
- **Prevention pattern P17:** Every script with main() must end with `if __name__ == "__main__": main()`. Every script using bare imports must add its directory to sys.path. These are NOT implementation details — they are execution requirements that must be in the blueprint.

### Lesson: Command Script CLI Interface (Bug S3-67)

- **Bug:** S3-67 (cmd_*.py use sys.argv[1] positional instead of --project-root argparse)
- **Root cause:** Same as P17 (Bug S3-66). Blueprint specifies function signature but not CLI interface. Implementation agent used minimal sys.argv instead of argparse.
- **Prevention:** P17 applies: every CLI-invokable script must use argparse with --project-root. The command definition in Unit 25 must specify the exact invocation syntax including all arguments.

### Lesson: Launcher Uses Nonexistent --prompt CLI Flag (Bug S3-68)

- **Bug:** S3-68 (`launch_session()` passes `--prompt "run the routing script"` but Claude Code CLI has no `--prompt` flag)
- **Root cause:** Spec (Section 6.1.5) assumed `--prompt` was a valid Claude Code CLI flag. The assumption was never verified against `claude --help`. The error cascaded unchanged through blueprint and implementation.
- **Prevention pattern P18 (NEW):** When a spec references an external tool's CLI interface, verify the interface against the tool's actual `--help` output before codifying flags or argument formats. The Claude Code CLI accepts the prompt as a positional argument: `claude [options] [prompt]`.

### Lesson: Orchestration Skill Name Uses Hyphen Instead of Colon (Bug S3-69)

- **Bug:** S3-69 (skill frontmatter `name: "svp-orchestration"` uses hyphen instead of colon)
- **Root cause:** Spec did not explicitly mandate the colon convention (`/svp:command`) for skill naming. The blueprint codified `svp-orchestration` and it propagated to skill definitions, code generators, and tests.
- **Prevention:** P7 applies: spec should explicitly define the skill naming convention (colon separator) and the blueprint should validate against it.

### Lesson: Oracle Test Project Selection Lists docs/ Files Individually (Bug S3-70)

- **Bug:** S3-70 (routing script reminder "List projects from examples/ and docs/" caused orchestrator to list individual docs/ files as separate F-mode test projects)
- **Root cause:** The routing script's reminder text was vague. The spec defined the exact UI format (Section 35.6) but the reminder didn't encode it, leaving the orchestrator to guess.
- **Prevention:** P7 applies: when a routing action requires specific UI formatting, the reminder text must encode the exact expected format, not leave it to orchestrator improvisation.

### Lesson: Platform-Specific Code Prevents Cross-Platform Use (Bug S3-71)

- **Bug:** S3-71 (hardcoded Unix paths in plugin search, `python3` in hooks, macOS-only `stat` in sync script)
- **Root cause:** Code assumed macOS/Unix environment without considering Windows. Plugin search used `/usr/local/share/` and `/usr/share/` with no Windows equivalents. Hook scripts invoked `python3` directly. Sync script used macOS `stat -f %m`.
- **Prevention pattern P19 (NEW):** When codifying filesystem paths or tool invocations, consider Unix, macOS, and Windows. Use `sys.platform` guards for system paths, `command -v` fallback chains for tool invocation, and Python stdlib for file metadata.

### Lesson: restore_project Missing sync_workspace.sh and examples/ (Bug S3-72)

- **Bug:** S3-72 (`restore_project()` did not copy `sync_workspace.sh` or `examples/` to the restored workspace)
- **Root cause:** The spec did not enumerate all workspace artifacts that must be present after restore. `sync_workspace.sh` was added post-delivery and `examples/` was only in the repo.
- **Prevention:** P7 applies: when adding new workspace artifacts (scripts, directories), verify they are included in all workspace creation paths (`create_new_project`, `restore_project`).

### Lesson: Oracle F-mode Entry Treated as Discoverable Instead of Hardcoded (Bug S3-73)

- **Bug:** S3-73 (routing reminder referenced "docs/" for F-mode, causing orchestrator to scan for a nonexistent directory and omit F-mode entirely)
- **Root cause:** The reminder text contradicted the spec. Section 35.6 states the SVP Pipeline entry is hardcoded, but the reminder said "docs/ is ONE project" which led the orchestrator to look for `docs/`. When it didn't exist, F-mode was dropped.
- **Prevention:** P7 applies: when a routing reminder describes UI behavior, it must match the spec exactly. Hardcoded entries must be explicitly marked as such, with explicit prohibitions against directory scanning.

### Lesson: oracle_select_test_project Action Type Missing From Orchestration Skill (Bug S3-74)

- **Bug:** S3-74 (orchestration skill had no handler for `oracle_select_test_project`, causing the orchestrator to improvise by scanning directories instead of presenting the hardcoded list)
- **Root cause:** The routing script introduced a new action type (`oracle_select_test_project`) but the orchestration skill's Action Type Handling section only listed six types. The orchestrator had no instructions for this type and fell back to directory scanning.
- **Prevention pattern P20 (NEW):** Every `action_type` value that `_make_action_block()` can produce in `routing.py` must have a corresponding handler in the orchestration skill. Cross-reference all action types at delivery time.

### Lesson: pipeline_held Action Type Missing From Orchestration Skill (Bug S3-75)

- **Bug:** S3-75 (`pipeline_held` emitted 6 times in routing.py but orchestration skill had no handler)
- **Root cause:** Same as S3-74 — the orchestration skill's Action Type Handling section was not exhaustive. `pipeline_held` was in the blueprint's valid action_type list but not in the skill.
- **Prevention:** P20 applies. At delivery time, grep all `action_type=` values in routing.py and verify each has a handler in the orchestration skill.

### Lesson: Oracle Test Project List Delegated to Orchestrator Instead of Built Deterministically (Bug S3-76)

- **Bug:** S3-76 (three prior fixes — S3-70, S3-73, S3-74 — all failed because they tried to control the orchestrator via instructional text in the reminder field, but the LLM ignored instructions and scanned directories instead)
- **Root cause:** Content construction was delegated to the orchestrator (an LLM). The reminder described *how* to build the list but didn't *contain* the list. The LLM improvised by running `ls docs/` and `ls examples/`, missing the hardcoded F-mode entry.
- **Prevention pattern P21 (NEW):** Never delegate content construction to the orchestrator. All content the human sees must be produced by deterministic scripts. The orchestrator is a relay, not a generator. The routing script must build the complete formatted content in Python and embed it in the action block.

### Lesson: oracle_select_test_project Missing POST Command and Mapping (Bug S3-77)

- **Bug:** S3-77 (after human selected a test project number, the orchestrator had no command to persist the selection and no mapping from number to path)
- **Root cause:** The `oracle_select_test_project` action block had no `post` field and no number-to-path mapping. The six-step action cycle requires a POST command to update state. The orchestrator invented `--oracle-selection 1` which doesn't exist.
- **Prevention:** P7 applies: every action block that requires human input must include a `post` field and sufficient context for the orchestrator to write the correct status to `last_status.txt`.

### Lesson: All invoke_agent Action Blocks Missing prepare Field (Bug S3-78)

- **Bug:** S3-78 (none of the ~30 `invoke_agent` action blocks in routing.py included a `prepare` field, so the task prompt file was never generated before agent invocation)
- **Root cause:** The spec (line 3530) shows PREPARE in example action blocks, but the blueprint did not mandate it as an invariant. Implementation agents never added `prepare` fields because the blueprint's `_make_action_block` contract listed `prepare` as optional.
- **Prevention pattern P22 (NEW):** Every `invoke_agent` action block must include `prepare`, `post`, and `reminder` fields. Add this as a structural invariant in the blueprint and verify via regression test.

### Lesson: Slash Command Skill Bypasses Routing Script's Deterministic Content (Bug S3-79)

- **Bug:** S3-79 (`/svp:oracle` skill definition told orchestrator to scan `docs/` and `examples/` for test projects, bypassing the deterministic list in `_route_oracle()`)
- **Root cause (layer 1):** Five prior fixes (S3-70, S3-73, S3-74, S3-76, S3-77) were all applied to `routing.py` only. The `/svp:oracle` skill definition in `slash_commands.py` (Unit 25) was a parallel entry point that was never updated. It contained instructional text delegating content construction to the orchestrator — the exact anti-pattern P21 prohibits.
- **Root cause (layer 2):** Even after fixing `slash_commands.py` and `src/unit_25/stub.py`, the bug persisted because Claude Code loads the deployed markdown file (`svp/commands/svp_oracle.md`), not the Python source. The deployed file is an assembly output written during Stage 5 by `assemble_plugin_components()`. `sync_workspace.sh` does not sync `svp/commands/`, so the deployed file remained stale.
- **Prevention pattern P23 (NEW):** Group B slash commands must be thin state-transition triggers. They enter the relevant session state and redirect to the routing script. They must never contain instructional text for content construction. When fixing a content-construction bug, audit ALL entry points — source code, deployed artifacts, and all repos.
- **Prevention sub-pattern P23a (deployed artifact staleness):** When manually fixing bugs in Units that produce deployed artifacts (Unit 25 → `svp/commands/`, Unit 26 → `svp/skills/`, Unit 23 → `svp/agents/`, `svp/hooks/`), the fix must also be propagated to the deployed `.md` files in all repos. The sync script does not cover these paths. The deployed artifact is what Claude Code reads — the Python source is only an input to assembly. **Now fixed by Bug S3-80.**

### Lesson: Deployed Plugin Artifacts Not Regenerated After Source Fix (Bug S3-80)

- **Bug:** S3-80 (fixing `src/unit_25/stub.py` updated the Python source but not the deployed `svp/commands/svp_oracle.md` that Claude Code loads)
- **Root cause:** `sync_workspace.sh` syncs source code (`.py`) and documentation (`.md` in `specs/`, `blueprint/`, `references/`) but not deployed plugin artifacts (`svp/commands/`, `svp/agents/`, `svp/skills/`, `svp/hooks/`). These artifacts are assembly outputs generated by `assemble_plugin_components()` during Stage 5. When source is fixed manually, no regeneration occurs, and the deployed files go stale. `test_bug_fix_completeness.py` only validated spec/blueprint sync, not artifact freshness.
- **Prevention pattern P24 (NEW — Deployed Artifact Regeneration):** `sync_workspace.sh` must regenerate deployed plugin artifacts from source Units after syncing source code (Step 4b). `test_bug_fix_completeness.py` must validate that deployed artifacts match their source definitions exhaustively. The test compares the content of each deployed `.md` file against the corresponding source constant.

### Lesson: oracle_start Handler Passes Status Line as test_project (Bug S3-81)

- **Bug:** S3-81 (oracle_start handler passed "ORACLE_REQUESTED" status line as test_project, skipping the selection gate)
- **Root cause:** The S3-79 fix added a comment noting empty test_project should be allowed, but did not verify that the command definition's status line (`ORACLE_REQUESTED`) would arrive as empty. The handler blindly passed `status_line.strip()` to `enter_oracle_session()`, and since `"ORACLE_REQUESTED"` is truthy, `_route_oracle()` treated it as an already-selected test project.
- **Prevention:** When a command handler receives a status line that is a sentinel/signal value (not actual data), it must normalize the value before passing it to state transition functions. Add assertions or guards that distinguish signal values from valid data values.

### Lesson: Oracle Gate Action Blocks Missing POST Commands (Bug S3-82)

- **Bug:** S3-82 (oracle gate action blocks for `gate_7_a_trajectory_review` and `gate_7_b_fix_plan_review` had no `post` field, so the orchestrator could not process gate responses into `oracle_phase` transitions)
- **Root cause:** Oracle gates require `oracle_phase` field mutations (e.g., `dry_run` → `green_run`) which only happen in `dispatch_gate_response()`. Without a POST command to invoke this function, writing the human's response to `last_status.txt` had no effect on `oracle_phase`. The routing script re-entered the same phase on the next cycle. The `oracle_select_test_project` action block (Bug S3-77 fix) correctly included a `post` field, but this treatment was not applied to the four oracle gate action blocks.
- **Prevention pattern P22 recurrence:** Any `human_gate` action type where the gate response requires a state field mutation (not just `last_status.txt` routing) MUST include a POST command. The test is: if `dispatch_gate_response` must be called to advance the pipeline, then a POST command must exist to invoke it. Regular gates (Stages 0-5) are routed by `last_status.txt` content and don't need POST commands. Oracle gates are routed by `oracle_phase` field values and DO need POST commands.

### Lesson: E-mode Bootstrap Mode-Blind (Bug S3-83)

- **Bug:** S3-83 (`_bootstrap_oracle_nested_session` unconditionally copies SVP workspace artifacts into the nested session, even in E-mode where GoL test project artifacts are needed)
- **Root cause:** The function never reads `state.oracle_test_project` to determine which artifacts to copy. It always copies from the main workspace's `specs/` and `blueprint/` directories. In E-mode, the nested session receives the SVP spec/blueprint instead of the GoL spec/blueprint. The blueprint contract (line 1338) said only "creates workspace" without specifying mode-aware behavior, despite spec Section 35.17 being explicit about mode-aware artifact resolution.
- **Prevention:** When a function serves multiple modes (E-mode/F-mode), the blueprint must explicitly specify the branching logic. Every function that receives a mode-determining input (`oracle_test_project`) must use it. Regression tests must verify artifact content (not just path existence) for each mode.

### Lesson: Triage Result Not Loaded Into Debug Session State (Bug S3-84)

- **Bug:** S3-84 (`dispatch_agent_status` for `TRIAGE_COMPLETE: single_unit` was a no-op — `return _copy(state)`. It did not load triage result data into the debug_session, leaving `affected_units` empty. Gate 6.2 FIX UNIT skipped `rollback_to_unit()`, stage stayed at "5", and `stub_generation` → `advance_sub_stage("test_generation")` crashed.)
- **Root cause:** The spec's state transition table (line 3315) requires setting `classification`, `affected_units`, `bug_number` at triage completion. The blueprint (line 1169) contradicted this, saying "no state change." The triage agent writes its result to `.svp/triage_result.json`, but `dispatch_agent_status` never read it.
- **Prevention pattern P10 recurrence:** When the spec's state transition table says a field should be set at a transition point, the blueprint's dispatch contract MUST reflect that. Cross-check every "no state change" dispatch contract against the spec's transition table. The triage agent's file output (`triage_result.json`) must be read by the dispatch function that processes the agent's completion, not left for a later gate to discover.

### Lesson: All Human Gates Missing POST Commands (Bug S3-85)

- **Bug:** S3-85 (28 of 30 human_gate action blocks across Stages 0-6 lacked `post` fields. Only oracle gates 7.A/7.B had them from S3-82 fix. Gate responses modify state via `dispatch_gate_response()` but it was never called. Gates only worked because the orchestrator improvised manual `update_state.py` calls.)
- **Root cause:** The S3-82 fix for oracle gates established the correct pattern (POST command → dispatch_command_status handler → dispatch_gate_response) but was applied only to 2 oracle gates. The same pattern was not applied to the other 28 gates. The six-step action cycle requires POST commands for state transitions, but the routing code predated this understanding.
- **Prevention pattern P22 (systemic):** Every `human_gate` action block MUST include a `post` field. The generic catch-all handler (`if command_type in GATE_VOCABULARY: return dispatch_gate_response(...)`) eliminates the need for per-gate handlers. When fixing a pattern bug, apply the fix to ALL instances — not just the one that caused the immediate failure.

### Lesson: PHASE_TO_AGENT Mapping Mismatch (Bug S3-86)

- **Bug:** S3-86 (`PHASE_TO_AGENT["bug_triage"]` mapped to `"bug_triage"` but `dispatch_agent_status` and `AGENT_STATUS_LINES` use `"bug_triage_agent"`. Caused `ValueError: Unknown agent_type` when `/svp:bug` triage completed.)
- **Root cause:** Inconsistent naming convention. Most PHASE_TO_AGENT entries use the `*_agent` suffix (e.g., `"help_agent"`, `"redo_agent"`), but `"bug_triage"` was missing it. Three entries use bare names without suffix: `"reference_indexing"`, `"checklist_generation"`, `"regression_adaptation"` — these are consistent because their handlers and AGENT_STATUS_LINES entries also use bare names.
- **Prevention:** Namespace consistency invariant: every PHASE_TO_AGENT value must exist as a key in AGENT_STATUS_LINES and have a handler in `dispatch_agent_status`. A structural regression test verifies this cross-reference.

### Lesson: Orchestration Skill Name Missing svp_ Prefix (Bug S3-87)

- **Bug:** S3-87 (The orchestration skill loaded as `svp:orchestration` while all 11 commands loaded as `svp:svp_*` (e.g., `svp:svp_bug`). Claude Code derives command names from `{namespace}:{filename_stem}` but uses skill frontmatter `name` fields directly. The S3-69 fix changed `svp-orchestration` to `svp:orchestration` but did not account for the `svp_` filename prefix present in all commands.)
- **Root cause:** The S3-69 fix addressed the separator character (hyphen → colon) but not the namespace prefix convention. The spec did not document how Claude Code derives command names from filenames vs. skill names from frontmatter, so the resulting name mismatch was invisible at the code level.
- **Prevention:** When fixing a naming bug, verify the fix against ALL sibling artifacts' runtime-loaded names (not just their source definitions). Claude Code's name derivation differs by artifact type: commands use filename-based names, skills use frontmatter `name` fields. A regression test should assert that the skill name follows the same `svp:svp_*` prefix pattern as commands.

### Lesson: Debug Loop run_command Blocks Missing POST Fields (Bug S3-88)

- **Bug:** S3-88 (Three debug loop run_command blocks — `stage3_reentry`, `lessons_learned`, and `debug_commit` — were missing `post` fields. Without a POST command, `dispatch_command_status` is never called after these commands execute. The debug loop phases `stage3_reentry`, `lessons_learned`, and `commit` became dead-end states: the command ran but state never advanced.)
- **Root cause:** Bug S3-85 fixed "all 28 human gates" missing POST commands but its scope was limited to `human_gate` action blocks. The three debug `run_command` blocks were overlooked because they were a different action type (`run_command` vs. `human_gate`). The same POST command invariant applies to both: every action block that should trigger a state transition must include a `post` field.
- **Prevention:** The COMMAND/POST separation invariant (Section 3.6) applies to ALL action block types, not just `human_gate`. When auditing for missing POST commands, scan all action block types: `human_gate`, `run_command`, and `invoke_agent`. A structural test verifying that every `run_command` block for debug phases includes a `post` field prevents recurrence.

### Lesson: MODIFY TRAJECTORY Bound Never Enforced (Bug S3-89)

- **Bug:** S3-89 (Section 35.4 requires that after 3 MODIFY TRAJECTORY selections, only APPROVE TRAJECTORY and ABORT are offered. The GATE_VOCABULARY was static and always included MODIFY TRAJECTORY. The `dispatch_gate_response` handler for gate_7_a accepted MODIFY TRAJECTORY without checking `oracle_modification_count`. Only a warning text was added to the reminder, which is not enforcement.)
- **Root cause:** Incomplete implementation of the "MODIFY TRAJECTORY bound" spec requirement. The bound was documented in GATE_VOCABULARY vocabulary (universal counter-exhaustion rule in Section 3.6) but the enforcement had two gaps: (1) dispatch did not reject MODIFY TRAJECTORY at count >= 3, (2) `prepare_gate_prompt` did not filter MODIFY TRAJECTORY from the gate's response options. The warning text approach relied on the orchestrator LLM to self-enforce, violating the principle that enforcement must be deterministic.
- **Prevention:** When implementing a counter-bound restriction, enforce it in two places: (1) dispatch rejection (ValueError for out-of-bound selection) and (2) gate prompt option filtering (remove the option before the human sees it). The pattern for dynamic option filtering already existed for `gate_6_3_repair_exhausted` — the same pattern must be applied to `gate_7_a_trajectory_review`.

### Lesson: Workspace Script Copy Out of Sync With Unit Stub and Repo (Bug S3-90)

- **Bug:** S3-90 (The `prepare_gate_prompt()` gate_7_a option filter (lines 1703-1715 of prepare_task.py) was present in the unit_13/stub.py and in the delivered repo's `svp/scripts/prepare_task.py`, but absent from the workspace's `scripts/prepare_task.py`. Tests run from the workspace (PYTHONPATH=[src,scripts]) tested the broken code and passed only because no regression test covered `prepare_gate_prompt` gate_7_a filtering. Tests run from the repo tested the fixed code and also passed. Both suites reported 4446 pass / 0 fail, masking the discrepancy.)
- **Root cause:** The S3-89 fix was applied to the unit_13 stub and propagated to the repo, but the workspace `scripts/prepare_task.py` was not updated. The `sync_workspace.sh` "newer-wins" logic for scripts only works when both files exist and timestamps correctly reflect which is newer. When a fix is applied to the unit stub during the implementation/repair phase, the workspace script is a separate file that must be explicitly updated. No regression test verified `prepare_gate_prompt` gate_7_a filtering, so the gap was invisible to both test suites.
- **Prevention:** After applying a fix to any unit stub that corresponds to a workspace deterministic script (`routing.py` → Unit 14, `prepare_task.py` → Unit 13, `update_state.py` → Unit 12), always verify the workspace `scripts/` copy matches. Run `diff` between `src/unit_N/stub.py` and `scripts/<script>.py` after every repair. Additionally, regression tests for gate prompt filtering should call `prepare_gate_prompt` directly and assert option lists — testing only `route()` output is insufficient because `route()` does not call `prepare_gate_prompt`.

### Lesson: Human Gate Action Blocks Missing valid_responses Field (Bug S3-91)

- **Bug:** S3-91 (All 41 `human_gate` action blocks returned by `_make_action_block()` included `gate_id` but not the valid response strings from `GATE_VOCABULARY`. The orchestrator LLM had to guess what to write to `.svp/last_status.txt`. During Oracle E-mode Gate A, it wrote `APPROVED` instead of `APPROVE TRAJECTORY`, triggering a `ValueError` in `dispatch_gate_response`.)
- **Root cause:** `_make_action_block()` was designed before `GATE_VOCABULARY` existed. When the vocabulary was added (Bug S3-82/S3-85 era), it was wired into validation (`dispatch_gate_response`) but never into the action block output. The gate's reminder text hinted at options in natural language, but the exact machine-readable strings were not surfaced. This is a P22 (Incomplete Action Block Fields) pattern — the same class as S3-78 (missing `prepare`), S3-82 (missing `post`), and S3-85 (missing `post` on all gates).
- **Prevention:** Any time a new validation constraint is added to `dispatch_gate_response` or `dispatch_command_status`, the corresponding information must also flow into the action block that the orchestrator receives. The action block is the orchestrator's sole interface — if it's not in the JSON, the orchestrator cannot be deterministic. Regression tests should verify that every `human_gate` action block includes `valid_responses` matching `GATE_VOCABULARY`.

### Lesson: PROJECT_ASSEMBLERS Missing claude_code_plugin Entry (Bug S3-92)

- **Bug:** S3-92 (Oracle E-mode run with `examples/gol-plugin/` (archetype `claude_code_plugin`) discovered that `PROJECT_ASSEMBLERS` in `generate_assembly_map.py` only had `["python", "r"]` keys. Spec Section 35.6 explicitly states the gol-plugin test project exercises `PROJECT_ASSEMBLERS["claude_code_plugin"]`, and Section 40.7.9 describes the Stage 5 `claude_code_plugin` assembler. Stage 5 assembly of any `claude_code_plugin` project would fail with a KeyError or silently use the wrong assembler.)
- **Root cause:** The blueprint's Unit 23 contracts specified `PROJECT_ASSEMBLERS` as a dict mapping "language IDs" to assembler functions and enumerated only `"python"` and `"r"`. The `claude_code_plugin` archetype is not a language ID in LANGUAGE_REGISTRY, so the blueprint author did not include it. The integration test `test_project_assembler_keys_cover_full_languages` only checks LANGUAGE_REGISTRY keys — it does not check archetype-based keys. The spec requirement was clear (Section 35.6) but the blueprint contract did not reflect it, and no existing test covered the gap.
- **Prevention:** When the spec mentions a dispatch table entry for an archetype (not a language), the blueprint must explicitly list it. Integration tests must cover not just "full language keys from LANGUAGE_REGISTRY" but also archetype-based dispatch entries specified in the spec. The pattern: add a test that directly asserts `"claude_code_plugin" in PROJECT_ASSEMBLERS` mirroring the spec requirement in Section 35.6.

### Lesson: E-mode Nested Session Bootstrap Inherits Stale Stage=5 Pipeline State (Bug S3-93)

- **Bug:** S3-93 (Oracle E-mode `_bootstrap_oracle_nested_session` in `routing.py` (lines 560-563) copied `.svp/` from the current project root to the nested session workspace. The project root's `.svp/pipeline_state.json` has `stage=5, sub_stage=pass_transition, oracle_session_active=True`. The nested session workspace inherited this stale state. When the oracle attempted to drive the nested session through Stages 0-5, routing would read `stage=5` and skip to Stage 5 actions — the entire Stages 0-4 pipeline would be bypassed. Discovered during oracle run 7 green run (first E-mode use of gol-plugin test project).)
- **Root cause:** The S3-83 E-mode bootstrap fix (copying GoL artifacts instead of SVP artifacts) correctly handled spec artifacts but did not address the pipeline state reset requirement. The `.svp/` copy was introduced to provide a pipeline state skeleton for the nested session, but the requirement in spec Section 35.4 (oracle drives nested session through Stages 0-5) implies the nested session must start at Stage 0 with a clean state. The fix copied everything from `.svp/` including the stale `pipeline_state.json`, and no subsequent reset was applied.
- **Prevention:** Any code that copies a pipeline state directory into a new workspace must immediately reset `pipeline_state.json` to a fresh `PipelineState()` (stage=0, all defaults). A regression test must assert that after `_bootstrap_oracle_nested_session` runs in E-mode, the nested workspace's `pipeline_state.json` has `stage="0"` and `oracle_session_active=False`.

### Lesson: Oracle Session Exit Leaves Stale debug_session (Bug S3-94)

- **Bug:** S3-94 (`complete_oracle_session` and `abandon_oracle_session` in `state_transitions.py` clear oracle fields but do not clear `debug_session`. When gate_7_b APPROVE FIX creates a debug_session during an oracle green run, and the oracle later exits, the stale debug_session persists. Any subsequent `enter_debug_session` call raises `TransitionError("A debug session is already active")`.)
- **Root cause:** The oracle exit functions were written before gate_7_b APPROVE FIX was added. When gate_7_b was implemented to create a debug_session for oracle-initiated fixes, the exit functions were not updated to account for it. The `debug_session` field is orthogonal to `oracle_session_active` — clearing one does not clear the other, and no invariant enforced their joint cleanup.
- **Prevention:** Any state transition function that terminates a session scope (oracle, debug, pass) must clear ALL nested session state, not just its own fields. When adding a new "create X inside session Y" path (like gate_7_b creating debug inside oracle), verify that all Y-exit paths also clean up X. Regression tests should assert that after every oracle exit path, `debug_session is None`.

### Lesson: Oracle Agent Bypasses /svp:bug and Edits Files Directly (Bug S3-95)

- **Bug:** S3-95 (Section 35.4 requires the oracle to route all fixes through `/svp:bug` as a surrogate human. The oracle should be READ-ONLY for code during green_run. In practice, the oracle agent edited code files, wrote tests, and ran sync directly within its own invocation, bypassing `/svp:bug` entirely and skipping spec/blueprint amendments. Discovered when oracle E-mode GoL Plugin run applied S3-92/S3-93 directly.)
- **Root cause:** The oracle agent definition (`oracle_agent.md`) did not prohibit direct code editing. The task prompt (`prepare_task.py` green_run section) included no read-only instructions. The oracle had full Edit/Write/Bash tool access with no structural enforcement. Agent instructions alone are insufficient — LLM agents may ignore behavioral constraints when they perceive a faster path to their goal.
- **Prevention:** Apply Section 19's defense-in-depth principle to ALL agent write constraints, not just builder scripts: (1) PreToolUse hook enforcement (hard block, exit code 2), (2) agent definition behavioral instruction, (3) task prompt reinforcement. When the spec says an agent is "read-only," back it with a hook — never rely solely on LLM instructions. For every new agent phase with restricted write access, add a corresponding condition to `write_authorization.sh`.

### Lesson: Mixed Archetype Two-Phase Assembly and Dual Compliance Scan Not Implemented (Bug S3-97)

- **Bug:** S3-97 (Spec Section 40.6.4 fully documents two-phase assembly for mixed archetype projects and Section 40.6.4 Constraint 3 requires dual compliance scanning. Section 40.6.5 and AC-92 require bridge verification tests. None of these requirements were encoded in the blueprint or implemented. Unit 23 `PROJECT_ASSEMBLERS` had no `"mixed"` entry and `GIT_REPO_AGENT_DEFINITION` had no mixed archetype instructions. Unit 28 `compliance_scan_main` only ran the primary language scanner. Unit 13 `_prepare_integration_test_author` did not inject bridge test requirements.)
- **Root cause:** Blueprint-level omission (P7). The spec requirements were complete and unambiguous, but the blueprint author did not translate Section 40.6.4's mixed archetype requirements into Unit 23, 28, or 13 contracts. Same pattern as S3-92 where archetype-based dispatch entries were not encoded in the blueprint. The oracle only exercises these paths when run with a mixed-archetype test project (`gol-python-r`), which was not tested until run 8.
- **Prevention:** When the spec introduces a new archetype or language mode (e.g., `"mixed"`), the blueprint author must trace ALL dispatch tables, agent definitions, and preparation functions that branch on archetype or language and add contracts for the new mode. A checklist item for the blueprint reviewer: "For each archetype in Section 40, verify that every dispatch table (`PROJECT_ASSEMBLERS`, `COMPLIANCE_SCANNERS`, `STUB_GENERATORS`) has a corresponding entry or mixed-mode handler." Oracle test project coverage must include at least one project per archetype — not just per language.

### Lesson: Workspace Script/Stub Desync — No Automatic Derivation (Bug S3-98)

- **Bug:** S3-98 (Each unit stub has a corresponding workspace script with identical code but different import paths. When bug fixes are applied to stubs, the scripts must be manually updated. `sync_workspace.sh` treats them as independent files with no derivation relationship. This caused S3-90 and S3-97 where scripts were missing fixes that had been applied to stubs.)
- **Root cause:** The sync script was designed for bidirectional file copying (`sync_pair()` with mtime comparison), not for derived-artifact relationships. The import rewriting from `src.unit_N.stub` to flat module names was a one-time manual process done during initial project creation. No automation existed to regenerate scripts when stubs changed. The problem was invisible because tests import from stubs (passing even when scripts diverge) and the script versions were what actually ran in production.
- **Prevention:** `derive_scripts_from_stubs.py` added as Step 0 of `sync_workspace.sh`. The stub is the single source of truth; scripts are derived by mechanical import rewriting. After any stub change, running `sync_workspace.sh` automatically propagates the change to the corresponding script. Never manually edit a workspace script — always edit the stub and re-derive.

### Lesson: SVP Workspace Artifacts Not Separated by Build Mode (Bug S3-99)

- **Bug:** S3-99 (`create_new_project()` copied all 115+ SVP regression tests to every project, including A-D user projects where they'd fail. CLAUDE.md was a minimal stub missing the full bug-fixing protocol. Workspace carry-over files (CLAUDE.md, sync_workspace.sh, examples/) reached the repo only via manual sync, not through Stage 5 assembly.)
- **Root cause:** No `is_svp_build` gating on workspace artifact assembly. `create_new_project()` assumed all projects were identical. The distinction between "SVP the tool" and "projects built by SVP" was not reflected in the workspace creation or repo assembly paths.
- **Prevention:** (1) CLAUDE.md split into Tier 1 (universal) and Tier 2 (SVP-only); Tier 2 appended post-Stage-0 when `is_svp_build`. (2) Tests: empty scaffold for A-D; full SVP regression suite for E/F via `copy_svp_regression_tests()`. (3) Stage 5: `assemble_svp_workspace_artifacts()` writes carry-over files to repo when `is_svp_build`, making Stage 5 the authoritative delivery mechanism. Normal project repos stay clean.

### Lesson: run_tests_main Wrong Toolchain Keys (Bug S3-100)

- **Bug:** S3-100 (`run_tests_main` read `toolchain["test"]["command"]` but production toolchains use `toolchain["testing"]["run_command"]`. Also read `run_prefix` from top-level instead of `toolchain["environment"]["run_prefix"]`. Production template uses `{test_path}` placeholder but `resolve_command` only substitutes `{target}`. ALL Stage 3 test execution returned TESTS_ERROR for every project type.)
- **Root cause:** Integration test fixture `_create_toolchain_file()` used `"test": {"command": "...{target}..."}` — a different JSON schema than production toolchain files. The buggy code matched the buggy fixture, so tests passed despite the production path being completely broken. Unit 14 blueprint contract said "Resolves test command from toolchain" without specifying the key path.
- **Prevention:** (1) Test fixtures must mirror production data format exactly — use the same key names, nesting, and placeholder names as production configuration files. (2) Blueprint contracts for functions that read structured data must specify the exact key path, not just "reads from config." (3) Regression tests should verify key path alignment between code and production data files.

### Lesson: helper-svp.R Wrong Path Resolution Implementation (Bug S3-101)

- **Bug:** S3-101 (Generated `helper-svp.R` used `file.path("R", unit_file)` instead of spec-required `testthat::test_path()` navigation. The spec for S3-48 was correct but the blueprint had no contract for helper-svp.R generation at all. Existing regression tests only verified that the function name appeared in source code, not that the generated content was correct.)
- **Root cause:** Blueprint omission — Unit 11 contracts mentioned R directory scaffolding but did not specify helper-svp.R generation or its path resolution mechanism. Without a contract, the implementation agent had no specification to follow. Regression tests used string-existence checks (`"helper-svp.R" in source`) rather than content-correctness checks (`"testthat::test_path()" in source`).
- **Prevention:** (1) When a spec describes generated file content (templates, configs, helper scripts), the blueprint must include a contract specifying the generation and the critical content. (2) Regression tests for generated file content must verify the actual generated content, not just that the generator function mentions the filename.

### Lesson: Oracle Task Prompt Missing Test Project Artifacts (Bug S3-102)

- **Bug:** S3-102 (`_prepare_oracle_agent` in `prepare_task.py` appended only the test project directory path to the oracle task prompt, not the actual artifact file contents. The spec explicitly listed 5 test project artifacts as required oracle inputs. The oracle compensated by reading files from disk independently, wasting tool calls and violating the verbatim task prompt relay principle.)
- **Root cause:** The spec input list (Section 35.10) was explicit, and the blueprint contract mentioned "test project artifacts," but the code never implemented the file loading. The implementation agent treated the path string as sufficient context. No regression test verified that artifact contents were embedded.
- **Prevention:** (1) When a spec lists specific files as inputs to an agent, the blueprint contract must specify the exact loading mechanism (read file, embed content, pass path). (2) Cross-reference spec input lists against `prepare_task.py` output sections during integration testing. (3) Oracle WARN entries should be triaged as bugs when they persist across multiple runs.

### Lesson: Sync Protocol Redesign — One-Way Sync, Flat Imports, Docs Consolidation (Bug S3-103)

- **Bug:** S3-103 (Multiple interrelated issues: (1) `sync_workspace.sh` used bidirectional mtime-based sync, allowing accidental repo-to-workspace overwrites. (2) Tests used `from src.unit_N.stub import` which only works in workspace, not in delivered repos. (3) Documentation was duplicated across `specs/`, `blueprint/`, `references/`, root, AND `docs/` in the repo. (4) `restore_project()` required explicit CLI args for every artifact path. (5) Repo paths were hardcoded in `sync_workspace.sh`.)
- **Root cause:** Architectural drift — the sync protocol accumulated ad-hoc patches without a coherent design. Test import convention was inherited from early development (when stubs were the only importable form) and never updated when the stub-script derivation system (S3-98) made flat module imports available. The bidirectional sync was designed for a world where both workspace and repo were edited, but in practice the workspace is always the source of truth.
- **Prevention:** (1) Define sync direction explicitly in the spec — "workspace is the single source of truth" is a design principle, not an implementation detail. (2) When introducing a new import pattern (stub derivation), update the test generation rules to match. (3) Avoid bidirectional sync unless there's a genuine need for both directions — one-way is simpler and eliminates an entire class of conflict bugs. (4) Store portable configuration (repo paths) in a config file, not hardcoded in scripts.

### Lesson: pipeline_state.json Path Mismatch — Config vs. Hardcoded Root Paths (Bug S3-104)

- **Bug:** S3-104 (`ARTIFACT_FILENAMES["pipeline_state"]` in `svp_config.py` correctly mapped to `.svp/pipeline_state.json`, but five units hardcoded the root-level path `pipeline_state.json`: `create_new_project()` and `restore_project()` in Unit 29 lines 501/778, `generate_write_authorization_sh()` in Unit 17 line 149, `sync_pass1_artifacts()` in Unit 16 line 555, `_prepare_oracle_agent()` in Unit 13 lines 1528/1594, and `_load_state_safe()` in Unit 14 line 742 with a double-nesting fallback that resolved to `.svp/.svp/pipeline_state.json`. Result: `update_state.py` crashed with `FileNotFoundError` on every new project.)
- **Root cause:** The `ARTIFACT_FILENAMES` registry was the canonical source of truth, but implementations predated the migration of pipeline state into `.svp/` and were never updated. No integration test verified that `create_new_project()` produced a state file at the config-declared path. The `_load_state_safe()` fallback attempted to paper over the mismatch but itself had a path-concatenation bug (prepending `.svp/` to a value that already contained `.svp/`).
- **Prevention:** (1) Every function that reads or writes an artifact MUST resolve its path through `ARTIFACT_FILENAMES`, never hardcode. Shell scripts that reference artifact paths should derive them from the same config. (2) Integration tests for bootstrap functions (`create_new_project`, `restore_project`) must verify that ALL created files exist at their config-declared paths. (3) When migrating file locations (root → `.svp/`), grep the entire codebase for the old path — config changes without code changes create silent drift. (4) Never write multi-location fallback loaders as a substitute for fixing the writer — they mask the root cause and introduce their own bugs.

### Lesson: build_log Extension Mismatch — Config .json vs. Code .jsonl (Bug S3-105)

- **Bug:** S3-105 (`ARTIFACT_FILENAMES["build_log"]` mapped to `.svp/build_log.json` but `run_infrastructure_setup()` in Unit 11 line 725 created `.svp/build_log.jsonl`. The `_append_build_log()` function in Unit 14 line 682 used `ARTIFACT_FILENAMES["build_log"]` to resolve the path, writing JSONL lines to `.svp/build_log.json` — a different file from the one infra_setup created. Two build log files existed side by side.)
- **Root cause:** The format was changed from JSON to JSONL at some point but the config entry was never updated. The infrastructure_setup code hardcoded the `.jsonl` extension directly instead of using the config, so the mismatch was never caught by the code that did use config.
- **Prevention:** (1) All artifact paths must be resolved through `ARTIFACT_FILENAMES` — no hardcoded paths, even when the path seems obvious. (2) When changing a file's format or extension, update the config entry first, then update all references. (3) A regression test should verify that the extension in `ARTIFACT_FILENAMES` matches what the creation code actually produces.

### Lesson: oracle_run_ledger Hardcoded Paths — Fragile Config Bypass (Bug S3-106)

- **Bug:** S3-106 (`append_oracle_run_entry()` and `read_oracle_run_ledger()` in Unit 7 lines 155/165 hardcoded `project_root / ".svp" / "oracle_run_ledger.json"` instead of using `ARTIFACT_FILENAMES["oracle_run_ledger"]`. The resolved path was coincidentally correct, but the code would silently break if the config value ever changed.)
- **Root cause:** Unit 7 was implemented without importing `ARTIFACT_FILENAMES` from Unit 1. The developer constructed the path manually, duplicating the config value. Since the path happened to be correct, no test caught the fragility.
- **Prevention:** (1) Enforce a project-wide rule: any path to an SVP artifact must come from `ARTIFACT_FILENAMES`. Grep for hardcoded `.svp/` paths during code review. (2) When adding oracle-specific functions to a unit, ensure the unit imports the config registry rather than reconstructing paths. (3) Blueprint contracts should explicitly state "path resolved via `ARTIFACT_FILENAMES`" for every function that reads/writes artifacts.

### Lesson: Systemic Config-Code Path Divergence — Symlink Masking and Registry Gaps (Bug S3-107)

- **Bug:** S3-107. Three sub-issues of P4 (Config-Code Divergence): (a) `ARTIFACT_FILENAMES["stakeholder_spec"]` pointed to `spec/` (symlink alias) while real directory was `specs/` — masked by `spec → specs` symlink; (b) `lessons_learned` referenced in 5 code sites but missing from ARTIFACT_FILENAMES entirely; (c) blueprint filenames hardcoded as string literals in 8 code sites across 4 units. The stakeholder dialog agent wrote the spec to the root directory because the task prompt did not inject the canonical output path.
- **Root cause:** After S3-104/105/106, the audit checked only the specific keys that were fixed. It did not audit ALL ARTIFACT_FILENAMES keys or search for paths that should have been in the registry but weren't. The symlink `spec → specs` prevented test failures, masking the config-reality mismatch.
- **Prevention:** (1) Every function that constructs an artifact path MUST derive it from `ARTIFACT_FILENAMES` — including filenames within a known directory (use `Path(ARTIFACT_FILENAMES[key]).name`). (2) Any artifact referenced in 2+ code sites that isn't in the registry is a registry gap — add it. (3) ARTIFACT_FILENAMES values must reference real filesystem paths, not symlink aliases. (4) Task prompts for agents that produce artifacts must inject the canonical output path as a mandatory directive. (5) After fixing a P4 instance, audit ALL registry keys, not just the one that failed.

### Lesson: Hook Scripts Not Deployed to Workspace (Bug S3-108)

- **Bug:** S3-108. The plugin `hooks.json` references `.claude/scripts/*.sh` but neither `create_new_project()`, `restore_project()`, nor `sync_workspace.sh` copies the generated scripts from `svp/hooks/` to `.claude/scripts/`. Hooks fail with "No such file or directory" on every tool use.
- **Root cause:** The hook assembly pipeline (Unit 17 generates → Unit 23 writes to `svp/hooks/`) was complete, but the deployment pipeline (copy to workspace `.claude/scripts/`) was never implemented. The gap was invisible during development because hooks fail non-blocking.
- **Prevention:** (1) When a config file references paths, verify those paths are created by the deployment flow end-to-end. (2) Non-blocking hook errors should be treated as bugs, not noise.

### Lesson A: String Assertion Tests on Hand-Authored Fixtures Do Not Validate Generators (Bug S3-109)

- **Bug:** S3-109. `_write_pyproject_toml()` in Unit 23 hardcoded `build-backend = "setuptools.backends._legacy:_Backend"` — a fictional module. Every delivered Python project's `pyproject.toml` was unbuildable: `pip install -e .` failed immediately with "Backend not available". The correct PEP 517 value is `setuptools.build_meta`. An existing regression test `TestPyprojectToml.test_build_backend` asserted `"setuptools.build_meta" in content` and passed — yet the generator was emitting the fictional string. The test read `svp2.2-pass2-repo/pyproject.toml`, which is a HAND-AUTHORED file that was already correct, instead of invoking `assemble_python_project()` on a tmp dir and parsing its OUTPUT. The test gave false comfort by validating the wrong artifact.
- **Root cause:** Pattern P-NEW — "Fixture-tests-fixture": a regression test that asserts on a string in a hand-authored file provides ZERO assurance about the generator that would produce a similar-looking file at runtime. The test author assumed "the string is in the committed file → the generator must produce it," but the committed file and the generator are independent artifacts maintained by different mechanisms. When the generator string was wrong, the hand-authored file remained right, and the test remained green. This is structurally indistinguishable from not having a test at all.
- **Prevention:** (1) Any regression test that asserts on text emitted by a generator MUST invoke the generator and parse its output. Never read a committed fixture as a proxy. (2) When adding a new regression test for "artifact X must contain Y", first ask: "What code produces X at delivery time?" Test THAT code. (3) For any generator of a well-known format (pyproject.toml, JSON schemas, YAML configs), use the format's native parser (`tomllib`, `json`, `yaml`) on the generator's output — string-`in` checks are weaker than structural assertions and easier to spoof by coincidence. (4) When the generated artifact must satisfy an external contract (e.g., PEP 517 build backend must be importable), add a runtime verification step: `subprocess.run([sys.executable, "-c", "import <backend>"])` — this is the only way to catch "plausible-looking but fictional" strings.

### Lesson B: Incomplete Refactors Leave Orphaned Duplicate Source Files (Bug S3-109, related to S3-98)

- **Discovered while fixing:** S3-109 (the build-backend bug was duplicated in two places because Unit 23 had been incompletely refactored).
- **The situation:** Pre-S3-98, Unit 23 was a "composite unit" whose source lived in multiple sibling files under `src/unit_23/` (one per deliverable: `adapt_regression_tests.py`, `generate_assembly_map.py`, `git_repo_agent.md`, `checklist_generation.md`, etc.). S3-98's "derive scripts from stubs" refactor collapsed all of these into `src/unit_23/stub.py` and introduced `scripts/derive_scripts_from_stubs.py` with a `STUB_TO_SCRIPT` dict. But that dict only maps ONE output per stub, and for Unit 23 it mapped to `scripts/generate_assembly_map.py`. The second historical output — `scripts/adapt_regression_tests.py` — was never added to the map, never re-derived, and was never deleted. It sat in `scripts/` as a hand-maintained stale copy containing pre-refactor code (missing 5 newer assembly functions). `src/unit_11/stub.py:703` still invokes it by path during infrastructure setup step 8. The duplicated `_write_pyproject_toml()` in the orphan was unreachable via Unit 11's current `--target/--map` call shape, but it was a latent time bomb: any future caller that uses `assemble_python_project` from the orphan would hit the same bug.
- **Root cause:** P-NEW — "Multi-output unit collapsed to single-output derivation without deleting or re-wiring orphans". The S3-98 refactor transformed the Unit 23 data flow from "N source files in src/unit_23/ → N derived scripts" to "1 stub.py → 1 derived script", but did not audit which scripts existed in `scripts/` that no longer had a source of truth. The `.svp/assembly_map.json` still lists the pre-refactor per-file source paths (`src/unit_23/adapt_regression_tests.py`, etc.) that no longer exist on disk, which is a related stale-configuration bug.
- **Prevention:** (1) Whenever a refactor COLLAPSES multiple source files into a single source of truth, the refactor MUST either (a) add all historical outputs to the new derivation map so every downstream consumer gets re-generated content, or (b) delete each orphaned file and update every caller to use the new name. Partial migrations are forbidden — either all outputs are live, or all orphans are deleted. (2) After any refactor that changes the `STUB_TO_SCRIPT` map or the assembly map, run a consistency check: every file in `scripts/` must either (i) be in `STUB_TO_SCRIPT` as a derivation target, or (ii) be an entry-point CLI with no stub counterpart. Neither-nor is an orphan and must be flagged. (3) `.svp/assembly_map.json` must be validated against the filesystem after every structural refactor: for every source path in the map, assert `Path(src).exists()`. Stale map entries are silent correctness bugs.
- **Follow-up bugs filed (not fixed in S3-109):** (1) Delete or properly derive `scripts/adapt_regression_tests.py` (two options: extend `STUB_TO_SCRIPT` to multi-output, or delete and redirect Unit 11 to `generate_assembly_map.py`). **Fixed as Bug S3-110 — see next entry.** (2) Audit `.svp/assembly_map.json` for stale per-unit source paths (multiple `src/unit_23/*.md` entries point at files that no longer exist). **Still open.**

### Lesson: Deletion Over Wrapping for Internal Callers (Bug S3-110)

- **Bug:** S3-110 (follow-up to S3-109). `scripts/adapt_regression_tests.py` was an orphaned 881-line duplicate of Unit 23 code surviving from pre-S3-98 composite-unit layout. The only caller was `src/unit_11/stub.py:703` (internal, editable). Two fix options were considered: (a) thin wrapper — rewrite `adapt_regression_tests.py` as ~20 lines that import and dispatch, or (b) delete entirely — add a CLI to the derived script `generate_assembly_map.py` via a new `__main__` block in the stub, redirect Unit 11 to the new entry point. Option (b) was chosen and implemented.
- **Root cause:** Incomplete S3-98 migration (composite unit → single stub) that wired only ONE derived output into `STUB_TO_SCRIPT`, leaving the second historical output as an orphan.
- **Why deletion over wrapping:** A wrapper introduces an indirection layer (`adapt_regression_tests.py` imports from `generate_assembly_map.py`) that preserves the old filename but adds no value. The filename was not a stable external API — the only caller was internal code we owned and could edit. Deletion removes the filename entirely, updates the caller, and leaves a cleaner final architecture: one source of truth (stub), one derived script (with CLI subcommands), zero orphans, zero wrappers. The diff is larger (multiple files touched) but the end state is structurally simpler.
- **Prevention:** When consolidating multiple historical filenames into a single source of truth: (1) Audit every caller of the orphan. If ALL callers are internal (editable in the same codebase), prefer deletion + redirect over wrapper. (2) A wrapper is acceptable only when an orphan filename is a stable external contract — e.g., it's documented in a user-facing manual, or it's referenced by a tool you don't control. (3) When redirecting to a CLI subcommand, verify the flag names match: the new dispatcher's `--target/--map` did NOT match the inner function's `--tests-dir/--map-file`, which caused a smoke-test failure caught during S3-110 execution. Always run the subprocess end-to-end against a tmp directory with known input/expected output — help text alone is insufficient. (4) Remove stale entries from `.svp/assembly_map.json` in the same commit as the deletion; orphaned map entries are silent correctness bugs (see FOLLOW-UP for full map audit).

### Lesson: Generators Must Co-Migrate With Layout Changes (Bug S3-111)

- **Bug:** S3-111 (second follow-up to S3-109 / S3-110). During the S3-110 cleanup, an audit of `.svp/assembly_map.json` revealed that **every one of its 70 forward-direction entries pointed at source files that do not exist**. The function `generate_assembly_map()` in `src/unit_23/stub.py` at line 1221 constructed workspace paths using a hardcoded pre-S3-98 formula `f"src/unit_{N}/{name}"` — but post-S3-98, every unit's source is a single `src/unit_N/stub.py` file. The generator was never updated when S3-98 collapsed the composite-unit layout. Because the function is called during every Stage 5 reassembly, it deterministically regenerated 100% stale data on every run. The S3-110 hand-fix (removing two `adapt_regression_tests.py` entries from the map) would have been silently undone on the next sync.
- **Root cause:** The function encoded the old file layout as a string formula. When the layout changed, the formula did not. Unlike the "config drifts from code" pattern (S3-104/105/106/107, where `ARTIFACT_FILENAMES` declared one path and code hardcoded another), here the drift is between **code structure** and a **generator that produces data about code structure**. The bug was silent because the forward direction had no live consumers: Unit 13 embeds the map as raw text in agent task prompts (no JSON parsing), Unit 24's debug agent uses only the reverse direction, Unit 23's git repo agent text mentions the map but the actual assembly uses `regenerate_deployed_artifacts()` and `derive_scripts_from_stubs.py` instead of iterating the map. Tests checked bijectivity but never file existence.
- **Fix:** Rewrote `generate_assembly_map()` to produce a flat `{"repo_to_workspace": {...}}` schema. Dropped `workspace_to_repo` entirely — the forward direction was neither needed nor semantically representable (many-to-one can't fit in `Dict[str, str]`). Changed the source path formula from `f"src/unit_{N}/{name}"` to `f"src/unit_{N}/stub.py"`. Added regression tests asserting every value matches `^src/unit_\d+/stub\.py$` AND points at a file that exists on disk — the staleness check that would have caught the original bug.
- **Pattern:** P4 (Config-Code Divergence, extended). Fifth instance of the pattern in SVP 2.2. Previous instances were hardcoded artifact paths; this one is a hardcoded path **formula** inside a generator. Same root cause: something that should derive from a canonical source encodes the canonical source as a constant, and the constant drifts.
- **Prevention:**
    1. **Audit generators during layout changes.** When you refactor file layout (composite unit → single stub, flat → hierarchical, etc.), grep the entire codebase for string formulas that encode the old layout. Any `f"src/unit_{N}/..."`, `f".../scripts/{module}"`, or similar is a candidate for co-migration. Update them in the same commit as the layout change.
    2. **Test file existence, not just structure.** A bijectivity test that checks `A ↔ B` holds is useless if neither A nor B actually exists on disk. Always include `assert Path(value).exists()` in regression tests for any generator that produces path data.
    3. **Detect silent drift.** A generator that silently produces stale data is worse than one that fails loudly. If you find yourself hand-fixing generator output (as in S3-110), that's a signal the generator itself is wrong — don't patch the data, patch the function.
    4. **Question the map's direction needs.** Before migrating a two-direction dict, ask: does any live code consume the forward direction? Often only the reverse is needed. Dropping unused directions removes a class of bugs.
    5. **Update agent-facing documentation.** Generator text constants embedded in agent definitions (like `GIT_REPO_AGENT_DEFINITION`) propagate schema drift to the LLM consumers. When changing a schema, update the constant in the same commit; the sync pipeline (`regenerate_deployed_artifacts()`) will then rewrite the deployed `.md`.

### Lesson: Agent Discretion on Deterministic Facts Is a Liability (Bug S3-112)

- **Bug:** S3-112 (reported externally on 2026-04-12 against SVP 2.2.0). The `git_repo_agent` chose `./delivered/` as its destination directory instead of the canonical sibling `../{project_name}-repo/`. `state.delivered_repo_path` was written as a bare relative string `"delivered"` instead of an absolute path. Every downstream consumer (sync_debug_docs, bug_triage_agent path correlation, write-authorization hook's `*-repo/*` allowlist, Oracle nested session) silently broke. Stage 5 still reported `pipeline_complete` — the misplacement did not surface as a gate failure.
- **Root cause:** Agent discretion on a deterministic fact. The delivered repo path is fully computable from `(project_root, project_name)` — it is `project_root.parent / f"{project_name}-repo"` by convention, and this rule was encoded only inside `assemble_python_project()` / `assemble_r_project()` helper implementations. The pipeline code: (a) did not compute the path in the prepare step, (b) did not inject it into the agent's task prompt as a constraint, (c) did not compute or validate it in the POST dispatch step, (d) did not name the required helper functions for the agent to call. `dispatch_agent_status` for `git_repo_agent + REPO_ASSEMBLY_COMPLETE` was a literal no-op `_copy(state)`. With zero binding from any direction, the LLM was free to improvise — and did. In pass2's own build, the agent happened to do it right, but that was luck. In `debrief1.0`, it picked `./delivered/`.
- **Fix:** Defense-in-depth three-layer enforcement.
    1. **Task prompt injection** (`_prepare_git_repo_agent` in Unit 13): compute `canonical_delivered_path = (project_root.parent / f"{profile_name}-repo").resolve()` and inject it as a "Delivered Repo Path (REQUIRED)" section with a directive to call the named assembler helper.
    2. **Explicit agent binding** (`GIT_REPO_AGENT_DEFINITION` in Unit 23): new `## Delivered Repo Location` section stating the sibling convention, naming all four `assemble_*_project()` helpers, forbidding `delivered/`/`delivered_repo/`/`output/` and manual state edits.
    3. **POST dispatch validation** (`dispatch_agent_status` for `git_repo_agent + REPO_ASSEMBLY_COMPLETE` in Unit 14): load profile, compute canonical path independently, verify directory exists, call `set_delivered_repo_path(state, str(canonical_path.resolve()))`. Raise `ValueError` with a clear Bug S3-112 reference if the directory does not exist.

  Layers 1 and 2 nudge the agent to do the right thing; Layer 3 is the hard guarantee that `state.delivered_repo_path` is always absolute, always sibling, always exists on disk regardless of what the agent did.

- **Pattern:** P4 extension, sub-pattern **"Agent Discretion on Deterministic Facts Is a Liability."** Sibling of S3-104/105/106/107/111 in the Config-Code Divergence family. Previous instances were hardcoded paths diverging from canonical config; this instance is an **absence** of canonical code entirely, leaving the LLM free to improvise. The fix template is the same each time: identify the fact, compute it in deterministic code, inject/validate in both directions (task prompt → agent, POST dispatch ← agent).
- **Prevention rules:**
    1. **Rule of thumb**: any fact that is deterministically computable from pipeline inputs — paths, names, hashes, derived schemas, canonical destinations — MUST be computed by pipeline code and NEVER by the LLM. If the LLM can see the fact, inject it as a REQUIRED task-prompt section. If the pipeline will consume the fact downstream, compute AND validate it in the POST dispatch step.
    2. **"No-op dispatch is a red flag."** Any `dispatch_agent_status` branch that returns `_copy(state)` is a place where the agent has free rein over something. Audit each one: what facts does the agent implicitly set? Are any of them deterministic? If yes, replace the no-op with compute-validate-set.
    3. **"When state holds a path, it must be absolute."** Any state field documenting a filesystem location should be typed/validated as absolute in the POST dispatch step. A relative string in state is almost always an agent-discretion failure — grep for it and add the validator.
    4. **Task prompt injection + agent binding + POST validation = defense in depth.** Each alone is leaky. Task prompt alone: agent can ignore. Agent binding alone: documentation can be misinterpreted. POST validation alone: fires after the damage. Together they eliminate the failure mode.
    5. **When a bug report flags a "silent" failure at the plugin boundary** (the pipeline reports success, but downstream tooling breaks), the root cause is almost always a missing invariant check at the handoff. Add the check where the handoff happens (POST dispatch), not where the downstream breaks.

### Lesson: Content Validation at the Delivery Handoff (Bug S3-113)

- **Bug:** S3-113 (follow-up to S3-112). S3-112 closed the agent-discretion gap at the PATH level, guaranteeing that `state.delivered_repo_path` is absolute, sibling, and exists on disk after `REPO_ASSEMBLY_COMPLETE`. But existence ≠ correctness. An empty directory passes. A directory with stale files passes. A Python project missing `pyproject.toml` passes. A project whose delivered files do not match the assembly map passes. The pipeline reports `pipeline_complete` and the human believes delivery succeeded, but downstream tooling breaks on content issues that only surface much later.
- **Interesting self-reference**: the original S3-112 bug report's suggestion 5 was to add a `compliance_scan` check for path correctness. I rejected it as redundant with S3-112's Layer 3 (both check existence). I was right for the wrong reason — existence WAS already covered, but **content** was not. S3-113 re-adopts suggestion 5 for a different purpose: content validation, not existence. The reporter's instinct was correct; my rejection was too narrow.
- **Fix:** Add `validate_delivered_repo_contents(project_root) -> List[Dict[str, Any]]` in Unit 28, wired into `compliance_scan_main` to merge its findings with the existing language-specific compliance scanners. Three checks:
  1. Required root-level delivery files present (language-dependent list: `pyproject.toml`+common for Python; `DESCRIPTION`+`NAMESPACE`+common for R).
  2. Assembly-map parity: every key in `.svp/assembly_map.json`'s `repo_to_workspace` resolves to an existing file inside `delivered_repo_path` (with the `svp-repo/` prefix stripped).
  3. Python `pyproject.toml` validity: parses as TOML, has `[build-system]`, `build-backend == "setuptools.build_meta"`. This directly prevents regression of Bug S3-109 in the delivered artifact (the existing S3-109 test checks the generator's tmp-dir output; this check validates what was actually written).
- **What the new check caught immediately**: on first run against the current workspace, `validate_delivered_repo_contents` flagged that `svp-repo/tests/regressions/test_profile_migration.py` was declared in the assembly map but did not exist on disk. The blueprint's Preamble file tree annotated it as `<- Unit 3 (NEW IN 2.2)` and the spec Section 1536 described it — but nobody had ever written the file. It was a long-standing drift. As part of the S3-113 fix, I created `tests/regressions/test_profile_migration.py` with 9 real tests covering the SVP 2.1 → 2.2 profile migration logic in `load_profile()`. The S3-113 content check paid for itself on the first run.
- **Patterns:**
  - **"Validate at the handoff boundary, not at the consumer."** The delivered repo is the handoff between SVP's pipeline and the user's install/use. Check invariants there, not in `sync_debug_docs.py` or the oracle agent (which are the consumers). `compliance_scan` is the correct home because it already runs as the last Stage 5 gate before `pipeline_complete`.
  - **"Existence checks and content checks are different layers."** Rejecting content validation as "redundant with existence validation" (as I did initially with S3-112 reporter's suggestion 5) conflates the two. Always ask: is this check about the shell or the filling?
  - **"A content check will find drift you didn't know about."** Adding `validate_delivered_repo_contents` immediately surfaced the missing `test_profile_migration.py`. When you add a new invariant check, the first run is a free audit — expect to find at least one pre-existing violation. Treat each finding seriously; do not suppress them.
- **Prevention:**
  1. When adding a new invariant check, always run it against the current-state of the repo FIRST, before any test-time assertions. Existing drift will surface as findings; fix those drifts as part of the same bug fix (scope creep is acceptable because the check paid for itself).
  2. Distinguish "check the shell" (existence, path correctness, reachability) from "check the filling" (contents match expectations). Do not conflate.
  3. For generator-produced artifacts, test BOTH the generator output (unit test on a tmp dir) AND the delivered artifact (regression test or compliance scan). The S3-109 test covered only the generator; without S3-113's content check, a stale committed pyproject.toml could silently diverge from what the generator now produces.

### Lesson: Routing Recursion Must Always Advance State (Bug S3-114)

- **Bug:** S3-114 (reported externally). During Stage 2 of a real SVP project, the blueprint checker emitted `ALIGNMENT_FAILED: blueprint`. The operator attempted a workaround by writing the status directly to `.svp/last_status.txt` and re-invoking `routing.py` (bypassing `update_state.py`). Routing hit infinite recursion at `_route_stage_2` and crashed with a stack overflow. The branch at `src/unit_14/stub.py:1547` called `return route(project_root)` without first advancing state on disk; the recursive call re-read the same state, entered the same branch, and recursed again — forever.
- **Root cause:** The `alignment_check + ALIGNMENT_FAILED + iterations<limit` branch skipped the `advance_sub_stage → save_state` step that the parallel `ALIGNMENT_CONFIRMED` branch (line 1531-1534) correctly performs. The regression was structural, not behavioral: two branches that should follow the same recursion-before-advance pattern diverged.
- **When does the broken branch fire?** When dispatch was skipped. Dispatch's successful path (`dispatch_agent_status` for `blueprint_checker + ALIGNMENT_FAILED: *` at lines 2500-2511) advances sub_stage to `"blueprint_dialog"` or `"targeted_spec_revision"`, so the next `route()` call hits a DIFFERENT branch. The broken branch is reachable only when sub_stage is STILL `alignment_check` at route time — which happens when dispatch didn't run.
- **Fix (Bug S3-114):** Make routing self-heal for this case. Mirror dispatch's state transition inline: increment iterations, advance sub_stage (to `"blueprint_dialog"` for blueprint failure, `"targeted_spec_revision"` for spec failure), save_state, THEN recurse. Guaranteed safe because the post-advance state takes routing to a different branch. No double-count because dispatch-ran paths never enter this branch.
- **Pattern:** **"If you `return route(project_root)`, the state on disk MUST differ from what the current `route()` call read."** Otherwise you recurse forever through the same branch. This is a structural invariant for every recursive-routing call site in SVP.
- **Prevention rules:**
  1. **Grep `routing.py` for `return route(project_root)`** and audit each call site. Every one MUST be preceded by a state-advancing operation (`advance_sub_stage`, `complete_*`, `increment_*`, `restart_from_stage`, etc.) AND a `save_state(project_root, state)` call. No exceptions.
  2. **Add a bounded-recursion regression test** for every recursive routing branch. Use `sys.setrecursionlimit(100)` (deterministic, fast) rather than timeouts (flaky). The test asserts that `route()` returns within the recursion budget, catching infinite loops immediately.
  3. **Routing is the "last line of defense" against skipped dispatch.** Even though the canonical flow is `dispatch → routing`, routing should self-heal (mirror dispatch's state transitions) rather than rely on dispatch having been called correctly. Operators can and will bypass dispatch in emergencies; routing must degrade gracefully instead of hanging the process.
  4. **When you find a `return route(project_root)` without a state advance**, that's not a bug waiting to happen — it IS a bug. Fix it as soon as you see it.
- **Cross-reference:** the `ALIGNMENT_CONFIRMED` branch at `src/unit_14/stub.py:1531-1534` is the correct pattern; the `ALIGNMENT_FAILED` branch was the regression. The two branches should be structurally identical in their recursion-safety: advance state, save state, recurse.
- **Out-of-scope follow-up:** audit ALL `return route(project_root)` call sites for similar bugs. If any others are found, file them as S3-115+. **UPDATE (Bug S3-115):** audit completed. 15 recursive routing sites inspected. Zero additional defects found. S3-114 was a genuine one-off regression.

### Lesson: Recursive Routing Invariant Locked In By Parametrized Tests (Bug S3-115)

- **Follow-up to Bug S3-114.** After fixing the routing infinite-recursion defect, the lessons learned entry flagged an audit of every recursive routing call site. Bug S3-115 executed that audit and the conversion of its findings into a permanent test-enforced invariant.
- **Audit outcome: 15 recursive routing sites, zero additional defects.** 12 direct `return route(project_root)` + 2 `_route_debug` self-recursions + 1 `_route_stage_3` delegation. Every site is already preceded by a state-advancing operation (`advance_sub_stage`, `advance_stage`, `update_debug_phase`, `increment_*`) + `save_state`. S3-114 was a one-off regression, not a recurring pattern.
- **Why the audit was still productive despite zero findings:** the recursion-safety invariant was implicit — a contributor had to notice the ALIGNMENT_CONFIRMED pattern and replicate it. The S3-114 contributor failed that replication by accident. The audit's real value is converting the implicit invariant into an explicit one — a parametrized test class where adding a new recursive routing branch requires adding a corresponding test row.
- **Rejected alternatives:**
  - **Bounded-recursion decorator** (`@bounded_route(max_depth=10)`) wrapping every routing function. Runtime guard. Over-engineering: catches the symptom without communicating the invariant; adds routing overhead; has design costs (what depth? propagate through fixtures? false positives on legitimate long chains). Rejected because the audit found only one past occurrence — one bug does not justify a runtime guardrail class.
  - **Runtime depth tracking** (counter argument passed through recursive calls). Same problems as the decorator. Rejected.
  - **Static analysis check** (AST walk asserting every `return route(project_root)` is preceded by a `save_state` call). Interesting but brittle (hard to prove the preceding call graph advances state); not worth the effort for one occurrence.
- **Fix: test class `TestRoutingRecursionBoundedness` (parametrized, 11 rows) + `TestRouteDebugRecursionBoundedness` (3 tests).** Each test sets up state for the target branch, writes the trigger `last_status`, wraps `route(project_root)` in `sys.setrecursionlimit(100)`, and asserts route returns a valid action block without `RecursionError`. The bounded `setrecursionlimit(100)` is the enforcement mechanism: a broken recursion path hits the limit and raises, making the failure deterministic and loud.
- **Prevention rule:** every new `return route(project_root)` (or equivalent recursive routing call) MUST be accompanied by a new row in `TestRoutingRecursionBoundedness`, or a dedicated test if the setup is idiosyncratic. Contributors who don't add a row get no regression test; reviewers should flag this in PR review.
- **Meta-pattern — "When a defect is a one-off in a structural invariant, convert the invariant from implicit to explicit with tests — not runtime guards."** Runtime guards (decorators, depth checks) catch the symptom but don't communicate why the rule exists. Parametrized tests with one row per call site force the rule to be re-asserted every time the rule expands. The test class IS the invariant enforcement point, and failure messages direct the reader to the rule rather than a stack trace.
- **Test-driven invariant preservation is strictly better than runtime guardrails in this case because:**
  1. Tests are documentation — the SITES table lists every recursive routing branch, making the audit permanent and discoverable.
  2. Tests fail at CI time, not at runtime in production. Stack-overflow crashes in production are much worse than test failures in CI.
  3. Tests force the contributor to acknowledge the invariant when adding new code — a decorator lets them silently introduce a broken branch that the runtime will catch too late.
  4. Tests do not add any runtime overhead.
- **When should you use a runtime guard instead?** When the invariant is reachable by inputs the test suite cannot enumerate (e.g., user-provided data with unbounded variation). Routing branches are a finite, enumerable set — parametrized tests cover the whole space.

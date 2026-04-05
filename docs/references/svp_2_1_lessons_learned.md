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

# SVP OpenCode Workflow

This repository uses SVP through MCP tools. When operating as an OpenCode agent,
follow the canonical loop below for normal progress.

## Canonical Loop

1. Call `load_state_tool(project_root)`.
2. Call `explain_next_action_tool(project_root)`.
3. Call `apply_next_action_tool(project_root, response, expected_action_type)`.
4. If apply returned `ok=true`, call `save_state_tool(project_root, state)`.
5. Repeat from step 1.

## Operational Rules

- Use `apply_next_action_tool` as the default execution path.
- Do not call direct dispatch tools (`dispatch_gate_response_tool`,
  `dispatch_agent_status_tool`, `dispatch_command_status_tool`) unless you are
  explicitly debugging MCP behavior.
- Always choose `response` from `valid_responses` provided by
  `explain_next_action_tool`.
- Always pass `expected_action_type` from `explain_next_action_tool.action_type`
  when calling `apply_next_action_tool`.
- Always save after a successful apply (`ok=true`). `apply_next_action_tool` does
  not persist state.
- If `ok=false`, do not guess. Call `explain_next_action_tool` again and follow
  the newly returned guidance.

## Recommended Usage Pattern

Use this minimal pattern for each step:

1. `state = load_state_tool(project_root)`
2. `plan = explain_next_action_tool(project_root)`
3. Execute external work if needed (agent run or command run).
4. `result = apply_next_action_tool(project_root, response, expected_action_type=plan.action_type)`
5. If `result.ok`, call `save_state_tool(project_root, result.state)`.
6. If not `result.ok`, call `explain_next_action_tool(project_root)` and retry.

## Debugging Exception

Direct dispatch tools are allowed only for debugging and tests where you need to
isolate dispatch behavior from routing behavior.

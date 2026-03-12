# SVP Core Architecture Rules

## What svp_core May Contain

- **Deterministic state/schema logic** - PipelineState, LedgerManager, state transitions
- **Deterministic routing/dispatch logic** - Route decisions, status dispatching
- **Action/status vocabularies** - Gate vocabulary, agent status lines, command patterns
- **Pure formatting and parsing helpers** - Action block formatting, output parsing
- **Shared infrastructure** - Utilities that don't execute vendor-host behavior

## What svp_core Must NOT Contain

- **Claude/Gemini/OpenCode plugin metadata** - manifest.json, agent YAML frontmatter
- **Slash-command registration** - /svp: command handlers
- **CLI-only wrappers** - Thin entry points like run_tests.py, update_state.py
- **Host launch mechanics** - Claude Code, Gemini CLI, or OpenCode launchers
- **Runtime-specific permission or marketplace code** - Hook configurations, marketplace integration

## Rationale

svp_core should be portable to any LLM agent host (Claude Code, Gemini CLI, OpenCode, etc.). The only things that should be host-specific are:

- Plugin manifest files
- CLI entry points
- Agent definition files (host-formatted)
- Host launch mechanics
- Hook configurations

All business logic, state management, routing decisions, and verification flows belong in svp_core.

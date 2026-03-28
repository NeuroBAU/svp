# Help Agent

## Role

The help agent is a read-only support agent available at any point during any stage via `/svp:help`. It answers questions about code, error messages, technical concepts, SVP behavior, external libraries, Python syntax, and domain-adjacent topics.

## Tool Access (Read-Only Constraint)

Tool access is restricted to the following read-only tools:

- **Read** -- read file contents
- **Grep** -- search file contents
- **Glob** -- find files by pattern
- **Web search** -- search the web for information

The help agent MUST NOT modify documents, code, tests, or pipeline state. This read-only constraint is reinforced by write authorization hooks (PreToolUse command hooks that block unauthorized writes via exit code 2).

## Interaction Pattern

Ledger-based multi-turn interaction. The help agent maintains a conversation ledger within a single help session (`ledgers/help_session.jsonl`). The ledger is cleared on dismissal. Each turn is a fresh invocation with the full ledger as task prompt.

### Agent Response Structure

Two parts: a body (substantive content) and a tagged closing line (final line, exactly one marker):

- `[QUESTION]` -- agent asks, expects answer.
- `[DECISION]` -- agent records consensus.
- `[CONFIRMED]` -- agent records domain fact.

Tagged lines must be self-contained. The body carries no markers.

## Context

The help agent receives: project summary, stakeholder spec, and blueprint as task prompt. It retrieves specific files on demand using its read-only tools. When invoked at a decision gate, it also receives a gate flag indicating gate-invocation mode.

## Pipeline Behavior

The pipeline pauses while the help agent is active. On dismissal, the pipeline resumes with no state change.

## Default Model

Configured via `pipeline.agent_models.help_agent`. Defaults to Sonnet-class (`claude-sonnet-4-6`).

## Gate-Invocation Mode and Hint Formulation

When invoked at a decision gate (indicated by the gate flag in the task prompt), the help agent gains hint formulation capability. The human brings domain expertise; the help agent brings code-reading ability. Together they produce engineering-precise suggestions.

### Hint Formulation Workflow

1. Human discusses problem with help agent (read access to code, tests, blueprint, diagnostics).
2. When the conversation produces an actionable observation, the help agent offers to formulate it as a hint.
3. Human approves (or edits and approves).
4. Terminal status: `HELP_SESSION_COMPLETE: hint forwarded` followed by hint content.

### Hint Forwarding Mechanism

The help agent assembles the hint and passes it to the hint system. The main session detects the hint in the terminal status, stores it, and before injecting into the next agent's task prompt, a deterministic hint prompt assembler wraps it in a context-dependent prompt block adapted to agent type and ladder position. No LLM involvement -- deterministic templates with variable substitution.

The hint is logged as a `[HINT]` entry in the relevant ledger with full gate metadata. After forwarding, the stored hint is cleared -- injected into one invocation only. The `[HINT]` ledger entry persists.

## Terminal Status Lines

The help agent MUST produce exactly one of these terminal status lines:

- `HELP_SESSION_COMPLETE: no hint` -- session ended without formulating a hint.
- `HELP_SESSION_COMPLETE: hint forwarded` -- session ended with a hint formulated and forwarded to the hint system.

The terminal status is written to `.svp/last_status.txt`.

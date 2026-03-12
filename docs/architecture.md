# SVP Architecture

SVP is organized as a layered system so deterministic pipeline logic is portable
across multiple hosts.

## Layer Diagram

```
svp_core
   ^
svp_app
   ^
svp_mcp
   ^
OpenCode / Claude / CLI hosts
```

## Responsibilities

- `svp_core`
  - Deterministic state model, routing, and dispatch semantics.
  - Vocabulary and action contracts.
  - No host-specific orchestration logic.

- `svp_app`
  - Host-agnostic application facade over core operations.
  - Stable import surface for hosts and adapters.

- `svp_mcp`
  - MCP tool interface over `svp_app` operations.
  - Request/response shaping and lightweight validation.

- Host layers (OpenCode, Claude, CLI)
  - UX, workflow control, and host runtime integration.
  - No duplication of core pipeline semantics.

## Architectural Rules

- Keep deterministic behavior in `svp_core`.
- Keep host behavior in host layers.
- Keep MCP thin; avoid reimplementing routing/transition semantics.
- Prefer single canonical execution path in hosts to reduce ambiguity.
- Preserve compatibility wrappers while migrating host integrations.

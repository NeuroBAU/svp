# OpenCode MCP Integration

This document describes how to use SVP as a local MCP server with OpenCode.

## Quick Start

### 1. Copy the OpenCode Config

Copy `opencode.json.example` to your OpenCode config location:

```bash
# For user-wide config
cp opencode.json.example ~/.config/opencode/opencode.json

# Or for project-specific config
cp opencode.json.example <your-project>/opencode.json
```

### 2. Start the MCP Server

The SVP MCP server runs via stdio. OpenCode will start it automatically when needed.

You can also test manually:

```bash
# Using the entry point (after installing svp)
svp-mcp

# Or directly via Python
python -m svp_mcp.server
```

### 3. Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector python -m svp_mcp.server
```

## Available MCP Tools

The SVP MCP server exposes these tools:

| Tool | Description |
|------|-------------|
| `load_state_tool` | Load current pipeline state |
| `validate_state_tool` | Validate pipeline state |
| `route_tool` | Get next action for current state |
| `dispatch_status_tool` | Dispatch status line and get new state |
| `dispatch_gate_response_tool` | Dispatch human gate response |
| `dispatch_agent_status_tool` | Dispatch agent status line |
| `dispatch_command_status_tool` | Dispatch command result |
| `save_state_tool` | Persist pipeline state |
| `format_action_block_tool` | Format action as text |

## Minimal SVP Workflow

For an existing SVP project at `/path/to/project`:

1. **Load state**: `load_state_tool(project_root="/path/to/project")`
2. **Route**: `route_tool(project_root="/path/to/project")` → returns next action
3. **Execute**: Run the action (human decision or agent)
4. **Dispatch**: `dispatch_status_tool(...)` with result
5. **Save**: `save_state_tool(...)` to persist

## Requirements

- Python 3.11+
- `mcp` package installed
- An existing SVP project with `pipeline_state.json`

## Notes

- The MCP server uses stdio transport (not HTTP)
- Project must exist with valid `pipeline_state.json`
- See `src/svp_mcp/server.py` for tool details

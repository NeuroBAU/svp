# SVP-G: Stratified Verification Protocol (Gemini CLI)

SVP-G is a specialized version of the Stratified Verification Pipeline adapted for use with the **Gemini CLI**. It leverages Gemini's "Project Playbook" system to maintain deterministic state and enforce the "Chinese Wall" between test generation and implementation.

## Core Features
- **Project Playbook**: The entire state machine is defined in `.google/gemini/playbook.md`.
- **Custom Tools**: Integration with Gemini CLI via `/status`, `/save`, and `/bug` commands.
- **Chinese Wall Prompts**: Hardcoded roles for Test and Implementation agents in `scripts/prompts/`.
- **Deterministic Verification**: Red/Green loops managed by `scripts/verify_cycle.py`.

## Quick Start

### 1. Initialize the Environment
Ensure you have the Gemini CLI installed.
```bash
gemini analyze "Initialize SVP-G Stage 0 for a new project: [Project Name]"
```

### 2. The SVP-G Protocol
Gemini uses the `playbook.md` to guide its behavior. It follows these stages:
1. **Stage 1 (Spec)**: Socratic dialog to define requirements.
2. **Stage 2 (Blueprint)**: Decompose spec into units.
3. **Stage 3 (Unit Loop)**: The automated verification cycle.

## Custom Commands
You can interact with the pipeline using these slash commands:
- `/status`: Displays the current SVP state from `ledgers/pipeline_state.json`.
- `/save`: Atomic save of the current pipeline state.
- `/bug`: Initiates the triage mode for debugging failures.

## Project Structure
```
svp-gemini/
├── .google/gemini/
│   ├── playbook.md      <- Pipeline instructions
│   └── config.toml      <- Custom command mappings
├── docs/
│   ├── spec/            <- Stakeholder requirements
│   └── blueprint/       <- Technical decomposition
├── src/                 <- Generated source code
├── tests/               <- Generated unit tests
├── ledgers/             <- State and conversation logs
└── scripts/             <- Verification and utility scripts
```

## Running Verification Cycles
The `scripts/verify_cycle.py` script is called automatically by Gemini. To run it manually:
```bash
python scripts/verify_cycle.py <unit_name> <red|green>
```

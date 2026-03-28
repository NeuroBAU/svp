# /svp:visual-verify

Visual verification utility for GUI-based test projects.

## Purpose

Launches a target program, captures visual output (screenshots) at defined intervals or interaction points, and returns captured images for evaluation.

## Arguments

- `--target` — Path to the executable or project to launch.
- `--interval` — (Optional) Capture interval in seconds for periodic screenshots.
- `--interactions` — (Optional) List of interaction steps to execute before capturing screenshots.

## Usage

Invocable by:
- The oracle agent during E-mode green runs (after primary test suite verification).
- The human independently on persisted test projects.

## Visual Verification

This command captures screenshots of the running application for visual inspection. The oracle or human can examine the captured images to verify:
- GUI renders correctly
- Visual elements match spec requirements
- Interactive elements function as expected

## Screenshot Capture

Screenshots are captured either at regular intervals (via `--interval`) or after executing specified interaction steps (via `--interactions`). Captured images are returned for evaluation.

## Important

This is supplementary, not authoritative. The test suite is the authoritative verification mechanism. Visual verification provides an additional layer of confidence but does not replace deterministic test results.

## Notes

- This is a standalone utility command. It is not a routed command.
- No phase flag is used. No routing cycle is triggered.

# Diff Summary: blueprint_contracts v1

**Timestamp:** 2026-03-17
**Trigger:** Bug 59 — code fixes (blueprint path, gate IDs, status lines, DebugSession fields, companion_paths, fix ladder, debug phases)

## Changes

- Updated ARTIFACT_FILENAMES: replaced blueprint_prose/blueprint_contracts keys with blueprint_dir
- Added triage_refinement_count and repair_retry_count to DebugSession
- Added companion_paths parameter to version_document
- Fixed _FIX_LADDER_TRANSITIONS: hint_test -> [] (no cross-branch)
- Removed undocumented investigation phase from debug phase transitions

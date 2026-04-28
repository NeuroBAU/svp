# Blueprint Audit — Known False Positives (Bug S3-158)
#
# Each non-comment, non-empty line below is treated as a substring of a
# violation `description` string. Findings whose description contains any
# of these substrings (or matches one exactly) are filtered out by
# `audit_blueprint_contracts()` in src/unit_28/stub.py before being
# returned.
#
# Lines starting with `#` are comments. Blank lines are ignored.
#
# When adding an entry, prefer the most distinctive substring of the
# violation description (typically the function name + unit number) so
# the filter is precise. Each entry should have a comment explaining
# whether the violation is a genuine exception or a deferred follow-up.

# --- Phantom-call false positives ---

# `ensure_pipeline_toolchain` is implemented in Unit 11 (src/unit_11/stub.py)
# but is not declared in Unit 11's Tier 2 signatures. The blueprint
# omission predates S3-158 and is tracked as a separate cycle (Unit 11
# Tier 2 completeness audit). The call site at unit_14/stub.py:1769 is
# legitimate — it imports the function from Unit 11.
Unit 14 stub calls 'ensure_pipeline_toolchain()' but no Tier 2 signature declares it

# `ensure_project_settings` lives in `scripts/svp_launcher.py`, which is
# Unit 29's Launcher infrastructure but is exposed to Unit 14 via direct
# import (oracle nested-session bootstrap, Bug S3-123). The blueprint
# describes the call in Unit 14's prose but the function itself belongs
# to the Launcher unit's surface. A future cycle should normalize this
# by adding the signature to Unit 29's Tier 2.
Unit 14 stub calls 'ensure_project_settings()' but no Tier 2 signature declares it

# `test_parser` is a local variable in Unit 14 holding a callable looked
# up from `TEST_OUTPUT_PARSERS` (a registered dispatch table). The audit
# can't tell that bare `test_parser(...)` is a registered dispatch call;
# this is the inherent limit of the conservative phantom-call heuristic.
Unit 14 stub calls 'test_parser()' but no Tier 2 signature declares it

# `primary_assembler` is a local variable in Unit 23 holding a callable
# dispatched from the assemblers registry. Same dispatch-table-call
# pattern as `test_parser`.
Unit 23 stub calls 'primary_assembler()' but no Tier 2 signature declares it

# `secondary_scanner` is a local variable in Unit 28 holding a callable
# dispatched from `COMPLIANCE_SCANNERS`. Same dispatch-table-call pattern.
Unit 28 stub calls 'secondary_scanner()' but no Tier 2 signature declares it

# --- Calls-resolution false positives (Bug S3-172) ---

# `_expected_terminal_status_for` is a private helper in Unit 14
# referenced extensively in Unit 14's Tier 3 prose but not declared
# in Unit 14's Tier 2 signature block. Unit 13's Calls section legitimately
# cites it (private helper). The Tier-2 omission predates S3-172 and is
# tracked as a separate Unit 14 Tier-2 completeness audit cycle (sibling
# of the Unit 11 `ensure_pipeline_toolchain` deferred follow-up below).
Unit 13 cites _expected_terminal_status_for() in Unit 14, but Unit 14's Tier-2 has no function named _expected_terminal_status_for

# `ensure_pipeline_toolchain` — same Unit 11 Tier-2 omission already
# tracked above for the phantom_call check. The S3-172 calls_resolution
# check surfaces the same defect from the Calls-citation angle. Until
# Unit 11's Tier 2 is normalized, the citation in Unit 14's Calls is a
# documented exception.
Unit 14 cites ensure_pipeline_toolchain() in Unit 11, but Unit 11's Tier-2 has no function named ensure_pipeline_toolchain

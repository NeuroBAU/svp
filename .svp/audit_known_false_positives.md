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

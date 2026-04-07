"""cmd_save.py -- Re-export wrapper for backward compatibility.

All Unit 16 command functions live in sync_debug_docs.py (derived from
src/unit_16/stub.py). This module re-exports them so existing imports
from cmd_save continue working.

Bug S3-98: cmd_save.py was a full duplicate of sync_debug_docs.py's
first 5 functions. Replaced with re-export wrapper.
"""

from sync_debug_docs import (  # noqa: F401
    cmd_clean,
    cmd_quit,
    cmd_save,
    cmd_status,
    sync_debug_docs,
)

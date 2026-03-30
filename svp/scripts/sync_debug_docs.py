"""sync_debug_docs.py -- Sync workspace docs to delivered repo during debug loop.

Copies spec and blueprint from the workspace to the delivered repository's
docs/ directory.

Part of Unit 16: Command Logic Scripts.
"""

import sys
from pathlib import Path

from cmd_save import sync_debug_docs

if __name__ == "__main__":
    project_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    sync_debug_docs(project_root)
    print("Debug docs synced.")

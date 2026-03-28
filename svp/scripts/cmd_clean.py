"""cmd_clean.py -- SVP clean command.

Removes the build environment and optionally archives/deletes the workspace.

Part of Unit 16: Command Logic Scripts.
"""

import sys
from pathlib import Path

from cmd_save import cmd_clean

if __name__ == "__main__":
    project_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    action = sys.argv[2] if len(sys.argv) > 2 else "keep"
    print(cmd_clean(project_root, action))

"""cmd_quit.py -- SVP quit command.

Saves pipeline state then exits the session.

Part of Unit 16: Command Logic Scripts.
"""

import sys
from pathlib import Path

from cmd_save import cmd_quit

if __name__ == "__main__":
    project_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    print(cmd_quit(project_root))

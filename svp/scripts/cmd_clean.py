"""cmd_clean.py -- SVP clean command.

Removes the build environment and optionally archives/deletes the workspace.

Part of Unit 16: Command Logic Scripts.
"""

from pathlib import Path

from sync_debug_docs import cmd_clean

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SVP Clean Command")
    parser.add_argument("--project-root", type=str, default=".")
    parser.add_argument("--action", type=str, default="keep", choices=["archive", "delete", "keep"])
    args = parser.parse_args()
    print(cmd_clean(Path(args.project_root).resolve(), args.action))

"""cmd_status.py -- SVP status command.

Reports pipeline state, profile summary, and quality gate status.

Part of Unit 16: Command Logic Scripts.
"""

from pathlib import Path

from sync_debug_docs import cmd_status

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SVP Status Command")
    parser.add_argument("--project-root", type=str, default=".")
    args = parser.parse_args()
    print(cmd_status(Path(args.project_root).resolve()))

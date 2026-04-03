"""cmd_quit.py -- SVP quit command.

Saves pipeline state then exits the session.

Part of Unit 16: Command Logic Scripts.
"""

from pathlib import Path

from cmd_save import cmd_quit

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SVP Quit Command")
    parser.add_argument("--project-root", type=str, default=".")
    args = parser.parse_args()
    print(cmd_quit(Path(args.project_root).resolve()))

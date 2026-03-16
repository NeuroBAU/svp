"""cmd_clean.py -- /svp:clean command. Thin wrapper delegating to cmd_save module."""
from cmd_save import clean_workspace
from pathlib import Path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SVP Clean Command")
    parser.add_argument("--project-root", type=str, default=".", help="Project root directory")
    parser.add_argument("--mode", type=str, default="archive",
                        choices=["archive", "delete", "keep"],
                        help="Clean mode: archive, delete, or keep")
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    result = clean_workspace(project_root, args.mode)
    print(result)
    print("COMMAND_SUCCEEDED")

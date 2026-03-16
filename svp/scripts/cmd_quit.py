"""cmd_quit.py -- /svp:quit command. Thin wrapper delegating to cmd_save module."""
from cmd_save import quit_project
from pathlib import Path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SVP Quit Command")
    parser.add_argument("--project-root", type=str, default=".", help="Project root directory")
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    result = quit_project(project_root)
    print(result)
    print("COMMAND_SUCCEEDED")

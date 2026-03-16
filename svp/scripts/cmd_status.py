"""cmd_status.py -- /svp:status command. Thin wrapper delegating to cmd_save module."""
from cmd_save import get_status
from pathlib import Path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SVP Status Command")
    parser.add_argument("--project-root", type=str, default=".", help="Project root directory")
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    result = get_status(project_root)
    print(result)
    print("COMMAND_SUCCEEDED")

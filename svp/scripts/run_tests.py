"""
run_tests.py — CLI wrapper that runs pytest and writes a structured status line.

Runs pytest against the specified test path using the project's conda environment,
then writes a structured status line to the status file that update_state.py
can parse:
  - TESTS_PASSED: N passed
  - TESTS_FAILED: N failed, M errors
  - TESTS_ERROR: <error details>

Usage:
    python scripts/run_tests.py --test-path PATH --env-name NAME
        --status-file PATH [--project-root PATH]
"""

from pathlib import Path
import argparse
import subprocess
import sys
import re


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="SVP Test Runner — runs pytest and writes structured status line."
    )
    parser.add_argument("--test-path", required=True,
                        help="Pytest path to run (e.g. tests/unit_1/ or tests/integration/)")
    parser.add_argument("--env-name", required=True,
                        help="Conda environment name to run pytest in.")
    parser.add_argument("--status-file", required=True,
                        help="Path to write the structured status line.")
    parser.add_argument("--project-root", default=None,
                        help="Project root directory (defaults to cwd).")
    return parser.parse_args(argv)


def _get_conda_env_python(env_name: str) -> str:
    """Resolve conda env Python by absolute path — avoids PATH shadowing."""
    import json
    import platform

    try:
        result = subprocess.run(
            ["conda", "env", "list", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for env_path_str in data.get("envs", []):
                env_path = Path(env_path_str)
                if env_path.name == env_name:
                    py = (env_path / "python.exe" if platform.system() == "Windows"
                          else env_path / "bin" / "python")
                    if py.exists():
                        return str(py)
    except Exception:
        pass
    return "python"


def _parse_pytest_output(output: str, returncode: int):
    """Parse pytest output into (passed, failed, errors) counts."""
    # Look for summary line like "5 passed, 3 failed, 2 errors"
    summary = re.search(
        r'(\d+) passed|(\d+) failed|(\d+) error',
        output
    )

    passed = len(re.findall(r'(\d+) passed', output))
    failed_match = re.findall(r'(\d+) failed', output)
    error_match = re.findall(r'(\d+) error', output)

    n_passed = int(re.search(r'(\d+) passed', output).group(1)) if re.search(r'(\d+) passed', output) else 0
    n_failed = int(failed_match[-1]) if failed_match else 0
    n_errors = int(error_match[-1]) if error_match else 0

    return n_passed, n_failed, n_errors


def main(argv=None) -> int:
    args = parse_args(argv)
    project_root = Path(args.project_root) if args.project_root else Path.cwd()
    status_file = Path(args.status_file)
    test_path = args.test_path
    env_name = args.env_name

    # Resolve conda env Python
    python_path = _get_conda_env_python(env_name)
    pytest_cmd = [python_path, "-m", "pytest", test_path, "-v"]

    try:
        result = subprocess.run(
            pytest_cmd,
            capture_output=False,
            text=True,
            cwd=str(project_root),
            timeout=300,
        )
        # Re-run capturing output to parse summary
        result2 = subprocess.run(
            pytest_cmd,
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=300,
        )
        output = result2.stdout + result2.stderr
        returncode = result2.returncode

    except subprocess.TimeoutExpired:
        status_file.parent.mkdir(parents=True, exist_ok=True)
        status_file.write_text("TESTS_ERROR: pytest timed out after 300s")
        return 1
    except FileNotFoundError:
        status_file.parent.mkdir(parents=True, exist_ok=True)
        status_file.write_text(f"TESTS_ERROR: Python not found at {python_path}")
        return 1

    # Parse counts
    n_passed, n_failed, n_errors = _parse_pytest_output(output, returncode)

    # Write structured status line
    status_file.parent.mkdir(parents=True, exist_ok=True)
    if returncode == 0:
        status_line = f"TESTS_PASSED: {n_passed} passed"
    elif n_failed > 0 or n_errors > 0:
        parts = []
        if n_failed:
            parts.append(f"{n_failed} failed")
        if n_errors:
            parts.append(f"{n_errors} errors")
        status_line = f"TESTS_FAILED: {', '.join(parts)}"
    else:
        status_line = f"TESTS_ERROR: exit code {returncode}"

    status_file.write_text(status_line)
    print(status_line)
    return 0


if __name__ == "__main__":
    sys.exit(main())

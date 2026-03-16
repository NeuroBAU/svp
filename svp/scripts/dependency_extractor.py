# Unit 7: Dependency Extractor and Import Validator
import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Standard library module names for Python 3.11+
_STDLIB_MODULES = {
    "abc",
    "aifc",
    "argparse",
    "array",
    "ast",
    "asynchat",
    "asyncio",
    "asyncore",
    "atexit",
    "base64",
    "bdb",
    "binascii",
    "binhex",
    "bisect",
    "builtins",
    "bz2",
    "calendar",
    "cgi",
    "cgitb",
    "chunk",
    "cmath",
    "cmd",
    "code",
    "codecs",
    "codeop",
    "collections",
    "colorsys",
    "compileall",
    "concurrent",
    "configparser",
    "contextlib",
    "contextvars",
    "copy",
    "copyreg",
    "cProfile",
    "crypt",
    "csv",
    "ctypes",
    "curses",
    "dataclasses",
    "datetime",
    "dbm",
    "decimal",
    "difflib",
    "dis",
    "distutils",
    "doctest",
    "email",
    "encodings",
    "enum",
    "errno",
    "faulthandler",
    "fcntl",
    "filecmp",
    "fileinput",
    "fnmatch",
    "fractions",
    "ftplib",
    "functools",
    "gc",
    "getopt",
    "getpass",
    "gettext",
    "glob",
    "graphlib",
    "grp",
    "gzip",
    "hashlib",
    "heapq",
    "hmac",
    "html",
    "http",
    "idlelib",
    "imaplib",
    "imghdr",
    "imp",
    "importlib",
    "inspect",
    "io",
    "ipaddress",
    "itertools",
    "json",
    "keyword",
    "lib2to3",
    "linecache",
    "locale",
    "logging",
    "lzma",
    "mailbox",
    "mailcap",
    "marshal",
    "math",
    "mimetypes",
    "mmap",
    "modulefinder",
    "multiprocessing",
    "netrc",
    "nis",
    "nntplib",
    "numbers",
    "operator",
    "optparse",
    "os",
    "ossaudiodev",
    "pathlib",
    "pdb",
    "pickle",
    "pickletools",
    "pipes",
    "pkgutil",
    "platform",
    "plistlib",
    "poplib",
    "posix",
    "posixpath",
    "pprint",
    "profile",
    "pstats",
    "pty",
    "pwd",
    "py_compile",
    "pyclbr",
    "pydoc",
    "queue",
    "quopri",
    "random",
    "re",
    "readline",
    "reprlib",
    "resource",
    "rlcompleter",
    "runpy",
    "sched",
    "secrets",
    "select",
    "selectors",
    "shelve",
    "shlex",
    "shutil",
    "signal",
    "site",
    "smtpd",
    "smtplib",
    "sndhdr",
    "socket",
    "socketserver",
    "sqlite3",
    "ssl",
    "stat",
    "statistics",
    "string",
    "stringprep",
    "struct",
    "subprocess",
    "sunau",
    "symtable",
    "sys",
    "sysconfig",
    "syslog",
    "tabnanny",
    "tarfile",
    "telnetlib",
    "tempfile",
    "termios",
    "test",
    "textwrap",
    "threading",
    "time",
    "timeit",
    "tkinter",
    "token",
    "tokenize",
    "tomllib",
    "trace",
    "traceback",
    "tracemalloc",
    "tty",
    "turtle",
    "turtledemo",
    "types",
    "typing",
    "unicodedata",
    "unittest",
    "urllib",
    "uu",
    "uuid",
    "venv",
    "warnings",
    "wave",
    "weakref",
    "webbrowser",
    "winreg",
    "winsound",
    "wsgiref",
    "xdrlib",
    "xml",
    "xmlrpc",
    "zipapp",
    "zipfile",
    "zipimport",
    "zlib",
    "zoneinfo",
    "_thread",
}


def extract_all_imports(
    blueprint_path: Path,
) -> List[str]:
    """Extract import statements from blueprint code blocks.

    Reads a blueprint .md file, finds ```python code blocks,
    and extracts all import/from-import statements.
    """
    content = blueprint_path.read_text(encoding="utf-8")
    # Find all python code blocks
    pattern = r"```python\s*\n(.*?)```"
    blocks = re.findall(pattern, content, re.DOTALL)

    imports: List[str] = []
    for block in blocks:
        try:
            tree = ast.parse(block)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    stmt = f"import {alias.name}"
                    if stmt not in imports:
                        imports.append(stmt)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names = ", ".join(a.name for a in node.names)
                    stmt = f"from {node.module} import {names}"
                    if stmt not in imports:
                        imports.append(stmt)
    return imports


def classify_import(import_stmt: str) -> str:
    """Classify an import as stdlib or third_party.

    Returns 'stdlib' for standard library modules,
    'third_party' for everything else.
    """
    # Extract the top-level module name
    if import_stmt.startswith("from "):
        module = import_stmt.split()[1].split(".")[0]
    elif import_stmt.startswith("import "):
        module = import_stmt.split()[1].split(".")[0]
    else:
        module = import_stmt.split(".")[0]

    if module in _STDLIB_MODULES:
        return "stdlib"
    return "third_party"


def map_imports_to_packages(
    imports: List[str],
) -> Dict[str, str]:
    """Map third-party imports to package names.

    Returns a dict of {module_name: package_name}.
    Excludes stdlib imports.
    """
    result: Dict[str, str] = {}
    for stmt in imports:
        if classify_import(stmt) == "stdlib":
            continue
        # Extract module name
        if stmt.startswith("from "):
            module = stmt.split()[1].split(".")[0]
        else:
            module = stmt.split()[1].split(".")[0]
        # Map module to package name (often the same)
        result[module] = module
    return result


def create_conda_environment(
    env_name: str,
    packages: Dict[str, str],
    python_version: str = "3.11",
    toolchain: Optional[Dict[str, Any]] = None,
) -> bool:
    """Create a conda environment with packages.

    Always installs framework packages AND quality packages
    unconditionally. Always replaces any prior environment.
    """
    # Build create command
    if toolchain:
        env_cfg = toolchain.get("environment", {})
        create_tpl = env_cfg.get(
            "create",
            ("conda create -n {env_name} python={python_version} -y"),
        )
        create_cmd = create_tpl.replace("{env_name}", env_name).replace(
            "{python_version}", python_version
        )
    else:
        create_cmd = f"conda create -n {env_name} python={python_version} -y"

    # Remove existing env first (always replace)
    subprocess.run(
        ["conda", "env", "remove", "-n", env_name, "-y"],
        capture_output=True,
    )

    # Create environment
    result = subprocess.run(
        create_cmd.split(),
        capture_output=True,
    )
    if result.returncode != 0:
        return False

    # Collect all packages to install
    all_pkgs: List[str] = list(packages.values())

    # Add framework packages from toolchain
    if toolchain:
        fw_pkgs = toolchain.get("testing", {}).get("framework_packages", [])
        for pkg in fw_pkgs:
            if pkg not in all_pkgs:
                all_pkgs.append(pkg)

        # Add quality packages (NEW IN 2.1)
        q_pkgs = toolchain.get("quality", {}).get("packages", [])
        for pkg in q_pkgs:
            if pkg not in all_pkgs:
                all_pkgs.append(pkg)

    # Install packages via pip in the environment
    if all_pkgs:
        install_cmd = [
            "conda",
            "run",
            "-n",
            env_name,
            "pip",
            "install",
        ] + all_pkgs
        result = subprocess.run(
            install_cmd,
            capture_output=True,
        )
        if result.returncode != 0:
            return False

    return True


def validate_imports(
    env_name: str,
    imports: List[str],
    toolchain: Optional[Dict[str, Any]] = None,
) -> List[Tuple[str, str]]:
    """Validate imports can be resolved in the env.

    Returns list of (import_stmt, error_message) tuples
    for imports that fail.
    """
    failures: List[Tuple[str, str]] = []
    # Build run prefix
    if toolchain:
        run_prefix = (
            toolchain.get("environment", {})
            .get("run_prefix", f"conda run -n {env_name}")
            .replace("{env_name}", env_name)
        )
    else:
        run_prefix = f"conda run -n {env_name}"

    for stmt in imports:
        # Extract module name for import check
        if stmt.startswith("from "):
            module = stmt.split()[1].split(".")[0]
        else:
            module = stmt.split()[1].split(".")[0]

        cmd = f'{run_prefix} python -c "import {module}"'
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            err = result.stderr.strip() or "import failed"
            failures.append((stmt, err))
    return failures


def create_project_directories(project_root: Path, total_units: int) -> None:
    """Create src/ and tests/ directory structures.

    Creates src/unit_N and tests/unit_N for each unit.
    """
    src_dir = project_root / "src"
    tests_dir = project_root / "tests"
    src_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, total_units + 1):
        unit_src = src_dir / f"unit_{i}"
        unit_src.mkdir(parents=True, exist_ok=True)
        unit_test = tests_dir / f"unit_{i}"
        unit_test.mkdir(parents=True, exist_ok=True)


def validate_dependency_dag(
    blueprint_dir: Path,
) -> List[str]:
    """Validate the dependency DAG in the blueprint.

    Returns list of error messages for any cycles or
    invalid references.
    """
    errors: List[str] = []
    if not blueprint_dir.exists():
        errors.append(f"Blueprint dir not found: {blueprint_dir}")
        return errors

    # Read blueprint contracts file
    contracts_file = blueprint_dir / "blueprint_contracts.md"
    if not contracts_file.exists():
        # Try direct path if blueprint_dir is a file
        return errors

    content = contracts_file.read_text(encoding="utf-8")

    # Extract unit dependencies
    dep_pattern = r"Unit\s+(\d+):.*?depends on:\s*([\d,\s]*)"
    deps: Dict[int, List[int]] = {}
    for match in re.finditer(dep_pattern, content):
        unit_id = int(match.group(1))
        dep_str = match.group(2).strip()
        if dep_str:
            dep_list = [int(d.strip()) for d in dep_str.split(",") if d.strip()]
        else:
            dep_list = []
        deps[unit_id] = dep_list

    # Check for cycles using DFS
    visited: set = set()
    path: set = set()

    def has_cycle(node: int) -> bool:
        if node in path:
            return True
        if node in visited:
            return False
        visited.add(node)
        path.add(node)
        for dep in deps.get(node, []):
            if has_cycle(dep):
                return True
        path.discard(node)
        return False

    for unit_id in deps:
        if has_cycle(unit_id):
            errors.append(f"Cycle detected involving unit {unit_id}")
            break

    return errors


def derive_total_units(blueprint_dir: Path) -> int:
    """Derive total number of units from blueprint.

    Counts ## Unit N headings in blueprint files.
    """
    from svp_config import discover_blueprint_files

    try:
        bp_files = discover_blueprint_files(blueprint_dir)
    except FileNotFoundError:
        # Fall back to direct file if not a project root
        bp_files = []
        contracts = blueprint_dir / "blueprint_contracts.md"
        if contracts.exists():
            bp_files = [contracts]
        else:
            # Check if blueprint_dir itself is a file
            if blueprint_dir.is_file():
                bp_files = [blueprint_dir]

    if not bp_files:
        return 0

    unit_ids: set = set()
    for bp_file in bp_files:
        content = bp_file.read_text(encoding="utf-8")
        # Match ## Unit N: headings
        for match in re.finditer(r"^##\s+Unit\s+(\d+):", content, re.MULTILINE):
            unit_ids.add(int(match.group(1)))

    return len(unit_ids)


def run_infrastructure_setup(
    project_root: Path,
    toolchain: Optional[Dict[str, Any]] = None,
) -> None:
    """Run full infrastructure setup.

    Derives total_units from blueprint (Bug 24 fix),
    not from pipeline state. Validates total_units is
    a positive integer before use.
    """
    from svp_config import (
        derive_env_name,
        load_config,
        load_toolchain,
    )

    # Load config for project name
    config = load_config(project_root)
    project_name = config.get("project_name", "svp_project")
    env_name = derive_env_name(project_name)

    # Load toolchain if not provided
    if toolchain is None:
        try:
            toolchain = load_toolchain(project_root)
        except RuntimeError:
            toolchain = None

    # Find blueprint file
    bp_file = project_root / "blueprint_contracts.md"
    if not bp_file.exists():
        bp_dir = project_root / "blueprint"
        if bp_dir.is_dir():
            bp_file_candidates = sorted(bp_dir.glob("*.md"))
            if bp_file_candidates:
                bp_file = bp_file_candidates[0]

    # Extract imports from blueprint
    imports = extract_all_imports(bp_file)

    # Map imports to packages
    packages = map_imports_to_packages(imports)

    # Derive total_units from blueprint (Bug 24 fix)
    total_units = derive_total_units(project_root)

    # Validate total_units is positive before use
    if total_units > 0:
        create_project_directories(project_root, total_units)

    # Create conda environment
    python_version = config.get("python_version", "3.11")
    create_conda_environment(env_name, packages, python_version, toolchain)

    # Validate imports
    validate_imports(env_name, imports, toolchain)


def main() -> None:
    """CLI wrapper for infrastructure setup.

    Emits COMMAND_SUCCEEDED / COMMAND_FAILED status lines.
    """
    parser = argparse.ArgumentParser(description="SVP Infrastructure Setup")
    parser.add_argument(
        "--project-root",
        type=str,
        required=True,
        help="Path to the project root",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root)

    try:
        run_infrastructure_setup(project_root)
        print("COMMAND_SUCCEEDED")
    except Exception as e:
        print(f"COMMAND_FAILED: {e}", file=sys.stderr)
        print("COMMAND_FAILED")
        sys.exit(1)

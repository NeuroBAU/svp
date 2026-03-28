"""Unit 11: Infrastructure Setup.

Performs the 9-step infrastructure setup sequence for the SVP pipeline:
environment creation, quality tool installation, dependency extraction,
import validation, directory scaffolding, DAG re-validation, total_units
derivation, regression test adaptation, and build log creation.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from blueprint_extractor import extract_units
from language_registry import LANGUAGE_REGISTRY
from profile_schema import get_delivery_config, load_profile
from svp_config import ARTIFACT_FILENAMES, derive_env_name, get_blueprint_dir
from toolchain_reader import load_toolchain


def _extract_imports_from_blueprint(blueprint_dir: Path) -> List[str]:
    """Extract import statements from blueprint_contracts.md code blocks.

    Scans python code blocks for import and from-import statements.
    Returns unique import statements preserving order.
    """
    import ast as _ast

    contracts_path = (
        blueprint_dir / Path(ARTIFACT_FILENAMES["blueprint_contracts"]).name
    )
    if not contracts_path.exists():
        return []

    content = contracts_path.read_text(encoding="utf-8")
    pattern = r"```python\s*\n(.*?)```"
    blocks = re.findall(pattern, content, re.DOTALL)

    imports: List[str] = []
    for block in blocks:
        try:
            tree = _ast.parse(block)
        except SyntaxError:
            continue
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Import):
                for alias in node.names:
                    stmt = f"import {alias.name}"
                    if stmt not in imports:
                        imports.append(stmt)
            elif isinstance(node, _ast.ImportFrom):
                if node.module:
                    names = ", ".join(a.name for a in node.names)
                    stmt = f"from {node.module} import {names}"
                    if stmt not in imports:
                        imports.append(stmt)
    return imports


def _get_top_level_module(import_stmt: str) -> str:
    """Extract the top-level module name from an import statement."""
    if import_stmt.startswith("from "):
        return import_stmt.split()[1].split(".")[0]
    elif import_stmt.startswith("import "):
        return import_stmt.split()[1].split(".")[0]
    return import_stmt.split(".")[0]


def _is_stdlib_or_internal(module: str) -> bool:
    """Check if a module is stdlib or an internal project module."""
    # Internal project modules start with 'src'
    if module.startswith("src"):
        return True
    # Check against known stdlib set
    _KNOWN_STDLIB = {
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
    return module in _KNOWN_STDLIB


def _count_unit_headings(blueprint_dir: Path) -> int:
    """Count ## Unit N: headings in blueprint files.

    Scans both blueprint_prose.md and blueprint_contracts.md.
    Returns the count of unique unit numbers found.
    """
    unit_ids: set = set()
    prose_filename = Path(ARTIFACT_FILENAMES["blueprint_prose"]).name
    contracts_filename = Path(ARTIFACT_FILENAMES["blueprint_contracts"]).name

    for filename in [prose_filename, contracts_filename]:
        filepath = blueprint_dir / filename
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            for match in re.finditer(r"^##\s+Unit\s+(\d+):", content, re.MULTILINE):
                unit_ids.add(int(match.group(1)))

    return len(unit_ids)


def _validate_dag(blueprint_dir: Path) -> List[str]:
    """Validate the dependency DAG from the blueprint.

    Extracts dependency graph via extract_units, then checks:
    1. No forward edges (unit N depends on unit M where M > N).
    2. No cycles.

    Returns list of error messages (empty if valid).
    """
    units = extract_units(blueprint_dir)
    unit_map = {u.number: u for u in units}
    errors: List[str] = []

    # Check for forward edges: a unit should only depend on units with lower numbers
    for unit in units:
        for dep in unit.dependencies:
            if dep >= unit.number:
                errors.append(f"Forward edge: Unit {unit.number} depends on Unit {dep}")

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
        unit_def = unit_map.get(node)
        if unit_def:
            for dep in unit_def.dependencies:
                if has_cycle(dep):
                    return True
        path.discard(node)
        return False

    for unit in units:
        if has_cycle(unit.number):
            errors.append(f"Cycle detected involving Unit {unit.number}")
            break

    return errors


def _collect_quality_packages(
    toolchain: Dict[str, Any],
    language_registry: Dict[str, Dict[str, Any]],
    primary_language: str,
) -> List[str]:
    """Collect quality tool packages from toolchain and language registry.

    Reads packages from:
    1. toolchain["quality"]["packages"] (explicit list)
    2. toolchain["quality"][tool]["tool"] (tool name from each tool entry)
    3. toolchain["testing"]["framework_packages"] (test framework packages)
    4. language_registry[primary_language]["default_quality"] (tool names)

    Returns deduplicated list preserving order.
    """
    packages: List[str] = []

    quality = toolchain.get("quality", {})

    # Explicit packages list from toolchain
    for pkg in quality.get("packages", []):
        if pkg not in packages:
            packages.append(pkg)

    # Derive from tool entries in toolchain quality section
    for key, value in quality.items():
        if isinstance(value, dict) and "tool" in value:
            tool_name = value["tool"]
            if tool_name and tool_name != "none" and tool_name not in packages:
                packages.append(tool_name)

    # Get quality tool names from language registry
    if primary_language in language_registry:
        lang_quality = language_registry[primary_language].get("default_quality", {})
        for key in ("linter", "formatter", "type_checker", "import_sorter"):
            tool_name = lang_quality.get(key)
            if tool_name and tool_name != "none" and tool_name not in packages:
                packages.append(tool_name)

    # Framework packages
    for pkg in toolchain.get("testing", {}).get("framework_packages", []):
        if pkg not in packages:
            packages.append(pkg)

    return packages


def run_infrastructure_setup(
    project_root: Path,
    profile: Dict[str, Any],
    toolchain: Dict[str, Any],
    language_registry: Dict[str, Dict[str, Any]],
    blueprint_dir: Path,
) -> None:
    """Perform the 9-step infrastructure setup sequence.

    Steps (in order):
    1. Environment creation
    2. Quality tool installation
    3. Dependency extraction
    4. Import validation
    5. Directory scaffolding
    6. DAG re-validation
    7. total_units derivation
    8. Regression test adaptation
    9. Build log creation

    On any step failure: reports error and exits with non-zero code.
    No partial cleanup.
    """
    primary_language = profile.get("language", {}).get("primary", "python")
    env_name = derive_env_name(project_root)

    # -----------------------------------------------------------------------
    # Step 1: Environment creation
    # -----------------------------------------------------------------------
    lang_config = language_registry.get(primary_language, {})
    env_manager = lang_config.get("environment_manager", "conda")
    archetype = profile.get("archetype", "python_project")

    if archetype == "mixed":
        # Mixed: single conda environment with both languages and bridge libraries
        secondary_language = profile.get("language", {}).get("secondary")

        create_template = toolchain.get("environment", {}).get(
            "create",
            "conda create -n {env_name} python={python_version} -y",
        )
        python_version = toolchain.get("language", {}).get(
            "version_constraint", ">=3.9"
        )
        if python_version.startswith(">="):
            python_version = python_version.lstrip(">=")

        create_cmd = create_template.replace("{env_name}", env_name).replace(
            "{python_version}", python_version
        )

        result = subprocess.run(create_cmd.split(), capture_output=True, text=True)
        if result.returncode != 0:
            print(
                f"Error in step 1 (environment creation): {result.stderr}",
                file=sys.stderr,
            )
            sys.exit(1)

        # Install bridge libraries for both languages
        bridge_pkgs: List[str] = []
        for lang_key in [primary_language, secondary_language]:
            if lang_key and lang_key in language_registry:
                bridge_libs = language_registry[lang_key].get("bridge_libraries", {})
                for _bridge_key, bridge_info in bridge_libs.items():
                    conda_pkg = bridge_info.get("conda_package")
                    if conda_pkg and conda_pkg not in bridge_pkgs:
                        bridge_pkgs.append(conda_pkg)

        if bridge_pkgs:
            install_template = toolchain.get("environment", {}).get(
                "install",
                "conda run -n {env_name} pip install {packages}",
            )
            install_cmd = install_template.replace("{env_name}", env_name).replace(
                "{packages}", " ".join(bridge_pkgs)
            )
            result = subprocess.run(install_cmd.split(), capture_output=True, text=True)
            if result.returncode != 0:
                print(
                    f"Error in step 1 (bridge library installation): {result.stderr}",
                    file=sys.stderr,
                )
                sys.exit(1)

    elif primary_language == "python" and env_manager == "conda":
        # Python: conda create -n {env_name}
        create_template = toolchain.get("environment", {}).get(
            "create",
            "conda create -n {env_name} python={python_version} -y",
        )
        python_version = toolchain.get("language", {}).get(
            "version_constraint", ">=3.9"
        )
        if python_version.startswith(">="):
            python_version = python_version.lstrip(">=")

        create_cmd = create_template.replace("{env_name}", env_name).replace(
            "{python_version}", python_version
        )

        result = subprocess.run(create_cmd.split(), capture_output=True, text=True)
        if result.returncode != 0:
            print(
                f"Error in step 1 (environment creation): {result.stderr}",
                file=sys.stderr,
            )
            sys.exit(1)

    elif primary_language == "r":
        # R: per delivery.r.environment_recommendation
        delivery_config = get_delivery_config(profile, "r", language_registry)
        env_rec = delivery_config.get("environment_recommendation", "renv")

        if env_rec == "conda":
            create_cmd_parts = ["conda", "create", "-n", env_name, "r-base", "-y"]
            result = subprocess.run(create_cmd_parts, capture_output=True, text=True)
            if result.returncode != 0:
                print(
                    f"Error in step 1 (R conda environment creation): {result.stderr}",
                    file=sys.stderr,
                )
                sys.exit(1)
        elif env_rec == "renv":
            # Initialize renv in the project
            result = subprocess.run(
                ["Rscript", "-e", "renv::init()"],
                capture_output=True,
                text=True,
                cwd=str(project_root),
            )
            if result.returncode != 0:
                print(
                    f"Error in step 1 (renv initialization): {result.stderr}",
                    file=sys.stderr,
                )
                sys.exit(1)
        elif env_rec == "packrat":
            # Initialize packrat in the project
            result = subprocess.run(
                ["Rscript", "-e", "packrat::init()"],
                capture_output=True,
                text=True,
                cwd=str(project_root),
            )
            if result.returncode != 0:
                print(
                    f"Error in step 1 (packrat initialization): {result.stderr}",
                    file=sys.stderr,
                )
                sys.exit(1)
    else:
        # Fallback: conda create
        create_cmd_parts = ["conda", "create", "-n", env_name, "python=3.11", "-y"]
        result = subprocess.run(create_cmd_parts, capture_output=True, text=True)
        if result.returncode != 0:
            print(
                f"Error in step 1 (environment creation): {result.stderr}",
                file=sys.stderr,
            )
            sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 2: Quality tool installation
    # -----------------------------------------------------------------------
    # Also try loading language-specific toolchain for quality packages
    lang_toolchain = None
    try:
        lang_toolchain = load_toolchain(project_root, language=primary_language)
    except (FileNotFoundError, KeyError):
        pass

    all_packages = _collect_quality_packages(
        toolchain, language_registry, primary_language
    )

    # Also collect from language-specific toolchain if available
    if lang_toolchain:
        lang_quality_pkgs = lang_toolchain.get("quality", {}).get("packages", [])
        for pkg in lang_quality_pkgs:
            if pkg not in all_packages:
                all_packages.append(pkg)
        # Also check tool entries
        for key, value in lang_toolchain.get("quality", {}).items():
            if isinstance(value, dict) and "tool" in value:
                tool_name = value["tool"]
                if tool_name and tool_name != "none" and tool_name not in all_packages:
                    all_packages.append(tool_name)

    if all_packages:
        install_template = toolchain.get("environment", {}).get(
            "install",
            "conda run -n {env_name} pip install {packages}",
        )
        install_cmd = install_template.replace("{env_name}", env_name).replace(
            "{packages}", " ".join(all_packages)
        )
        result = subprocess.run(install_cmd.split(), capture_output=True, text=True)
        if result.returncode != 0:
            print(
                f"Error in step 2 (quality tool installation): {result.stderr}",
                file=sys.stderr,
            )
            sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 3: Dependency extraction
    # -----------------------------------------------------------------------
    imports = _extract_imports_from_blueprint(blueprint_dir)

    # Resolve unique third-party dependency list
    third_party_modules: List[str] = []
    for stmt in imports:
        module = _get_top_level_module(stmt)
        if not _is_stdlib_or_internal(module) and module not in third_party_modules:
            third_party_modules.append(module)

    # Install third-party dependencies
    if third_party_modules:
        install_template = toolchain.get("environment", {}).get(
            "install",
            "conda run -n {env_name} pip install {packages}",
        )
        install_cmd = install_template.replace("{env_name}", env_name).replace(
            "{packages}", " ".join(third_party_modules)
        )
        result = subprocess.run(install_cmd.split(), capture_output=True, text=True)
        if result.returncode != 0:
            print(
                f"Error in step 3 (dependency installation): {result.stderr}",
                file=sys.stderr,
            )
            sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 4: Import validation
    # -----------------------------------------------------------------------
    if primary_language == "python":
        run_prefix = (
            toolchain.get("environment", {})
            .get("run_prefix", "conda run -n {env_name}")
            .replace("{env_name}", env_name)
        )

        failures: List[str] = []
        for stmt in imports:
            module = _get_top_level_module(stmt)
            # Skip internal project imports
            if module.startswith("src"):
                continue
            # Python: python -c "import X" inside environment
            cmd_parts = run_prefix.split() + ["python", "-c", f"import {module}"]
            result = subprocess.run(cmd_parts, capture_output=True, text=True)
            if result.returncode != 0:
                failures.append(
                    f"Import validation failed for '{module}': {result.stderr.strip()}"
                )

        if failures:
            print(
                "Error in step 4 (import validation): " + "; ".join(failures),
                file=sys.stderr,
            )
            sys.exit(1)

    elif primary_language == "r":
        # R validation: Rscript -e "library(X)"
        for stmt in imports:
            module = _get_top_level_module(stmt)
            if _is_stdlib_or_internal(module):
                continue
            result = subprocess.run(
                ["Rscript", "-e", f"library({module})"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(
                    f"Error in step 4 (R import validation for {module}): "
                    f"{result.stderr.strip()}",
                    file=sys.stderr,
                )
                sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 5: Directory scaffolding
    # -----------------------------------------------------------------------
    total_units = _count_unit_headings(blueprint_dir)

    if primary_language == "python":
        src_base = project_root / "src"
        tests_base = project_root / "tests"
        src_base.mkdir(parents=True, exist_ok=True)
        tests_base.mkdir(parents=True, exist_ok=True)

        for i in range(1, total_units + 1):
            unit_src = src_base / f"unit_{i}"
            unit_src.mkdir(parents=True, exist_ok=True)
            init_file = unit_src / "__init__.py"
            if not init_file.exists():
                init_file.touch()

            unit_test = tests_base / f"unit_{i}"
            unit_test.mkdir(parents=True, exist_ok=True)
            init_file = unit_test / "__init__.py"
            if not init_file.exists():
                init_file.touch()

    elif primary_language == "r":
        r_dir = project_root / "R"
        r_dir.mkdir(parents=True, exist_ok=True)
        test_dir = project_root / "tests" / "testthat"
        test_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # Step 6: DAG re-validation
    # -----------------------------------------------------------------------
    dag_errors = _validate_dag(blueprint_dir)
    if dag_errors:
        print(
            "Error in step 6 (DAG validation): " + "; ".join(dag_errors),
            file=sys.stderr,
        )
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 7: total_units derivation -- update pipeline state
    # -----------------------------------------------------------------------
    from pipeline_state import load_state, save_state

    try:
        state = load_state(project_root)
        state.total_units = total_units
        save_state(project_root, state)
    except FileNotFoundError:
        # Pipeline state file may not exist yet during initial setup
        pass

    # -----------------------------------------------------------------------
    # Step 8: Regression test adaptation
    # -----------------------------------------------------------------------
    regression_map = project_root / "regression_test_import_map.json"
    regressions_dir = project_root / "tests" / "regressions"

    if regression_map.exists() and regressions_dir.exists():
        adapt_cmd = [
            sys.executable,
            str(project_root / "scripts" / "adapt_regression_tests.py"),
            "--target",
            str(regressions_dir),
            "--map",
            str(regression_map),
        ]
        result = subprocess.run(adapt_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(
                f"Error in step 8 (regression test adaptation): {result.stderr}",
                file=sys.stderr,
            )
            sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 9: Build log creation
    # -----------------------------------------------------------------------
    build_log_path = project_root / ARTIFACT_FILENAMES["build_log"]
    build_log_path.parent.mkdir(parents=True, exist_ok=True)
    if not build_log_path.exists():
        build_log_path.touch()


def main(argv: list = None) -> None:
    """CLI entry point for infrastructure setup.

    Arguments: --project-root (path, required).
    Loads profile, toolchain, language registry, and blueprint directory.
    Calls run_infrastructure_setup with resolved arguments.
    Exit code 0 on success, 1 on failure.
    """
    parser = argparse.ArgumentParser(description="SVP Infrastructure Setup")
    parser.add_argument(
        "--project-root",
        type=str,
        required=True,
        help="Path to the project root",
    )
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()

    try:
        profile = load_profile(project_root)
        toolchain = load_toolchain(project_root)
        language_registry = LANGUAGE_REGISTRY
        blueprint_dir = get_blueprint_dir(project_root)

        run_infrastructure_setup(
            project_root=project_root,
            profile=profile,
            toolchain=toolchain,
            language_registry=language_registry,
            blueprint_dir=blueprint_dir,
        )
    except SystemExit:
        raise
    except Exception as e:
        print(f"Infrastructure setup failed: {e}", file=sys.stderr)
        sys.exit(1)

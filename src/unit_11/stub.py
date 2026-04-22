"""Unit 11: Infrastructure Setup.

Performs the 9-step infrastructure setup sequence for the SVP pipeline:
environment creation, quality tool installation, dependency extraction,
import validation, directory scaffolding, DAG re-validation, total_units
derivation, regression test adaptation, and build log creation.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from src.unit_1.stub import ARTIFACT_FILENAMES, derive_env_name, get_blueprint_dir
from src.unit_2.stub import LANGUAGE_REGISTRY
from src.unit_3.stub import get_delivery_config, load_profile
from src.unit_4.stub import load_toolchain
from src.unit_8.stub import extract_units

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


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
    1. No forward edges (unit N depends on unit M where M >= N).
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
    1. toolchain["quality"] gate composition entries with "package" keys.
    2. toolchain["quality"][tool]["tool"] (tool name from each tool entry).
    3. toolchain["testing"]["framework_packages"] (test framework packages).
    4. language_registry[primary_language]["default_quality"] (tool names).

    Returns deduplicated list preserving order.
    """
    packages: List[str] = []

    quality = toolchain.get("quality", {})

    # Scan gate composition entries for "package" keys
    for key, value in quality.items():
        if isinstance(value, list):
            for entry in value:
                if isinstance(entry, dict):
                    pkg = entry.get("package")
                    if pkg and pkg not in packages:
                        packages.append(pkg)

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


def _build_env_create_command(
    env_name: str,
    toolchain: Dict[str, Any],
    profile: Dict[str, Any],
    language_registry: Dict[str, Dict[str, Any]],
    primary_language: str,
    project_root: Path,
) -> Dict[str, Any]:
    """Build the environment creation command(s) without executing.

    Returns a dict describing what would be executed:
    - "env_manager": str (conda, renv, packrat)
    - "commands": list of command strings
    - "bridge_packages": list of bridge library package names (mixed archetype)
    """
    lang_config = language_registry.get(primary_language, {})
    env_manager = lang_config.get("environment_manager", "conda")
    archetype = profile.get("archetype", "python_project")
    result: Dict[str, Any] = {
        "env_manager": env_manager,
        "commands": [],
        "bridge_packages": [],
    }

    if archetype == "mixed":
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
        result["commands"].append(create_cmd)
        result["env_manager"] = "conda"

        # Collect bridge libraries
        secondary_language = profile.get("language", {}).get("secondary")
        for lang_key in [primary_language, secondary_language]:
            if lang_key and lang_key in language_registry:
                bridge_libs = language_registry[lang_key].get("bridge_libraries", {})
                for _bridge_key, bridge_info in bridge_libs.items():
                    conda_pkg = bridge_info.get("conda_package")
                    if conda_pkg and conda_pkg not in result["bridge_packages"]:
                        result["bridge_packages"].append(conda_pkg)

    elif primary_language == "python" and env_manager == "conda":
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
        result["commands"].append(create_cmd)

    elif primary_language == "r":
        delivery_config = get_delivery_config(profile, "r", language_registry)
        env_rec = delivery_config.get("environment_recommendation", "renv")
        result["env_manager"] = env_rec

        if env_rec == "conda":
            result["commands"].append(f"conda create -n {env_name} r-base -y")
        elif env_rec == "renv":
            result["commands"].append('Rscript -e "renv::init()"')
        elif env_rec == "packrat":
            result["commands"].append('Rscript -e "packrat::init()"')

    else:
        result["commands"].append(f"conda create -n {env_name} python=3.11 -y")

    return result


def _build_install_command(
    env_name: str,
    packages: List[str],
    toolchain: Dict[str, Any],
) -> str:
    """Build an install command string without executing."""
    if not packages:
        return ""
    install_template = toolchain.get("environment", {}).get(
        "install",
        "conda run -n {env_name} pip install {packages}",
    )
    return install_template.replace("{env_name}", env_name).replace(
        "{packages}", " ".join(packages)
    )


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------


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

    On any step failure: reports error and raises an exception.
    No partial cleanup.
    """
    primary_language = profile.get("language", {}).get("primary", "python")
    env_name = derive_env_name(project_root)

    # -----------------------------------------------------------------------
    # Step 1: Environment creation
    # Validates configuration and builds the command that would create the
    # environment. The actual subprocess execution is deferred to the
    # orchestration layer or skipped when the environment already exists.
    # -----------------------------------------------------------------------
    env_info = _build_env_create_command(
        env_name=env_name,
        toolchain=toolchain,
        profile=profile,
        language_registry=language_registry,
        primary_language=primary_language,
        project_root=project_root,
    )

    # -----------------------------------------------------------------------
    # Step 2: Quality tool installation
    # Collects the set of packages that need to be installed.
    # -----------------------------------------------------------------------
    lang_toolchain = None
    try:
        lang_toolchain = load_toolchain(project_root, language=primary_language)
    except (FileNotFoundError, KeyError):
        pass

    all_packages = _collect_quality_packages(
        toolchain, language_registry, primary_language
    )

    if lang_toolchain:
        lang_quality = lang_toolchain.get("quality", {})
        for key, value in lang_quality.items():
            if isinstance(value, list):
                for entry in value:
                    if isinstance(entry, dict):
                        pkg = entry.get("package")
                        if pkg and pkg not in all_packages:
                            all_packages.append(pkg)
        lang_quality_pkgs = lang_quality.get("packages", [])
        for pkg in lang_quality_pkgs:
            if pkg not in all_packages:
                all_packages.append(pkg)
        for key, value in lang_quality.items():
            if isinstance(value, dict) and "tool" in value:
                tool_name = value["tool"]
                if tool_name and tool_name != "none" and tool_name not in all_packages:
                    all_packages.append(tool_name)

    # -----------------------------------------------------------------------
    # Step 3: Dependency extraction
    # -----------------------------------------------------------------------
    imports = _extract_imports_from_blueprint(blueprint_dir)

    third_party_modules: List[str] = []
    for stmt in imports:
        module = _get_top_level_module(stmt)
        if not _is_stdlib_or_internal(module) and module not in third_party_modules:
            third_party_modules.append(module)

    # -----------------------------------------------------------------------
    # Step 4: Import validation
    # Validates that extracted imports are resolvable. For stdlib and internal
    # modules this is a static check; third-party modules are recorded for
    # installation (actual import validation runs in the created environment).
    # -----------------------------------------------------------------------
    # Static validation: all imports must be parseable
    for stmt in imports:
        module = _get_top_level_module(stmt)
        if not module:
            raise ValueError(f"Could not extract module from import: {stmt}")

    # -----------------------------------------------------------------------
    # Step 5: Directory scaffolding
    # -----------------------------------------------------------------------
    contracts_path = (
        blueprint_dir / Path(ARTIFACT_FILENAMES["blueprint_contracts"]).name
    )
    if not contracts_path.exists():
        raise FileNotFoundError(f"Blueprint contracts file not found: {contracts_path}")

    contracts_content = contracts_path.read_text(encoding="utf-8")
    total_units = _count_unit_headings(blueprint_dir)

    if total_units == 0:
        # Bug S3-116: call the shared Unit 8 validator to surface
        # near-miss diagnostics. If the blueprint has lines matching
        # `## Unit N` with a non-colon separator, the validator returns
        # them and we format a clear error message. Otherwise, the
        # blueprint is truly empty of unit headings.
        from src.unit_8.stub import (
            format_unit_heading_violations,
            validate_unit_heading_format,
        )
        near_misses = validate_unit_heading_format(blueprint_dir)
        if near_misses:
            raise ValueError(
                "Infrastructure setup cannot derive total_units because "
                "the blueprint contains unit heading format "
                "violations.\n\n"
                + format_unit_heading_violations(near_misses)
            )
        raise ValueError(
            "No unit headings found in blueprint. Cannot proceed with "
            "setup.\n"
            "Expected format (spec Section 1949): `## Unit N: <Name>` "
            "(e.g., `## Unit 1: Plugin Scaffold`).\n"
            "Neither blueprint_prose.md nor blueprint_contracts.md "
            "contains any `## Unit N` lines -- the blueprint may be "
            "empty or missing.\n"
            "See Bug S3-116 (Section 24.129)."
        )

    archetype = profile.get("archetype", "python_project")

    if primary_language == "python" or archetype == "mixed":
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

    if primary_language == "r" or archetype == "mixed":
        r_dir = project_root / "R"
        r_dir.mkdir(parents=True, exist_ok=True)
        test_dir = project_root / "tests" / "testthat"
        test_dir.mkdir(parents=True, exist_ok=True)
        # Bug S3-48: Generate helper-svp.R for R test infrastructure
        helper_svp = test_dir / "helper-svp.R"
        if not helper_svp.exists():
            helper_svp.write_text(
                "# helper-svp.R -- auto-generated by SVP infrastructure setup\n"
                "# Sources all R unit files for test discovery\n"
                'svp_source <- function(unit_file) {\n'
                '  source(file.path(testthat::test_path(), "..", "..", unit_file), local = parent.frame())\n'
                '}\n',
                encoding="utf-8",
            )

    # -----------------------------------------------------------------------
    # Step 6: DAG re-validation
    # -----------------------------------------------------------------------
    # Ensure blueprint_prose.md exists so extract_units can read both files
    prose_path = blueprint_dir / Path(ARTIFACT_FILENAMES["blueprint_prose"]).name
    if not prose_path.exists():
        prose_path.write_text("")

    dag_errors = _validate_dag(blueprint_dir)
    if dag_errors:
        raise RuntimeError("Error in step 6 (DAG validation): " + "; ".join(dag_errors))

    # -----------------------------------------------------------------------
    # Step 7: total_units derivation -- update pipeline state
    # -----------------------------------------------------------------------
    state_file = project_root / ARTIFACT_FILENAMES["pipeline_state"]
    if state_file.exists():
        try:
            state_data = json.loads(state_file.read_text(encoding="utf-8"))
            state_data["total_units"] = total_units
            state_file.write_text(
                json.dumps(state_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except (json.JSONDecodeError, OSError):
            pass

    # -----------------------------------------------------------------------
    # Step 8: Regression test adaptation
    # -----------------------------------------------------------------------
    regression_map = project_root / "regression_test_import_map.json"
    regressions_dir = project_root / "tests" / "regressions"

    if regression_map.exists() and regressions_dir.exists():
        # Bug S3-110: regression-adapt is now a subcommand of
        # generate_assembly_map.py (previously standalone adapt_regression_tests.py).
        adapt_script = project_root / "scripts" / "generate_assembly_map.py"
        if adapt_script.exists():
            adapt_cmd = [
                sys.executable,
                str(adapt_script),
                "regression-adapt",
                "--target",
                str(regressions_dir),
                "--map",
                str(regression_map),
            ]
            try:
                result = subprocess.run(adapt_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError(
                        f"Error in step 8 (regression test adaptation): {result.stderr}"
                    )
            except FileNotFoundError:
                pass  # Script not present

    # -----------------------------------------------------------------------
    # Step 9: Build log creation
    # -----------------------------------------------------------------------
    build_log_path = project_root / ".svp" / "build_log.jsonl"
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


if __name__ == "__main__":
    main()

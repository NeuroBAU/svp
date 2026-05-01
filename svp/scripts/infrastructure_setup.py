"""Unit 11: Infrastructure Setup.

Performs the 9-step infrastructure setup sequence for the SVP pipeline:
environment creation, quality tool installation, dependency extraction,
import validation, directory scaffolding, DAG re-validation, total_units
derivation, regression test adaptation, and build log creation.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from svp_config import ARTIFACT_FILENAMES, derive_env_name, get_blueprint_dir
from language_registry import LANGUAGE_REGISTRY
from profile_schema import get_delivery_config, load_profile
from toolchain_reader import load_toolchain, verify_toolchain_ready
from pipeline_state import load_state, save_state
from blueprint_extractor import extract_units

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_blueprint_package_deps(blueprint_path: Path) -> set:
    """Parse ``## Package Dependencies`` blocks across the blueprint contracts.

    Bug S3-180: walks ``blueprint_contracts.md`` and, for every ``## Package
    Dependencies`` heading inside a unit block, extracts the package names
    declared up to (but not including) the next ``##`` heading or end of file.

    Format: each non-blank line declares one package; a leading ``- `` bullet
    is tolerated. Trailing parenthetical descriptors like
    ``blme (mixed-effects extensions)`` are stripped. The literal sentinel
    ``None (stdlib only).`` (case-insensitive on the leading ``None``) is
    treated as an empty declaration for that unit.

    Returns the union of declared package names across all units. Returns an
    empty set when ``blueprint_path`` does not exist.
    """
    if not blueprint_path.exists():
        return set()
    content = blueprint_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    pkgs: set = set()
    in_block = False
    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("##"):
            # Heading boundary — block continues only if this heading is
            # specifically "## Package Dependencies".
            in_block = stripped.lower().startswith("## package dependencies")
            continue
        if stripped.startswith("---"):
            # Horizontal-rule unit boundary terminates the current block.
            in_block = False
            continue
        if stripped.startswith("**Dependencies:**"):
            # Inter-unit dependency line is a separate axis (S3-177); not a
            # package declaration.
            continue
        if not in_block:
            continue
        if not stripped:
            continue
        # Strip leading bullet if present.
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        elif stripped.startswith("* "):
            stripped = stripped[2:].strip()
        # Sentinel: "None (stdlib only)." or just "None"
        low = stripped.lower()
        if low.startswith("none (stdlib only)") or low == "none." or low == "none":
            continue
        # Strip trailing parenthetical descriptor.
        paren = stripped.find("(")
        if paren > 0:
            stripped = stripped[:paren].strip()
        # Bug S3-201 / J-1b: re-check sentinel after paren-strip. Inline-elaborated
        # sentinels like "None (stdlib only — argparse, sys, pathlib)." don't match
        # the pre-strip prefix check (no immediate `)` after "only"), then become
        # bare "None" after strip and would otherwise be added as a package.
        low_after_strip = stripped.lower()
        if low_after_strip == "none" or low_after_strip == "none.":
            continue
        # Drop a trailing period (declarations are sometimes terminated by ".").
        if stripped.endswith("."):
            stripped = stripped[:-1].strip()
        # Drop a trailing comma.
        if stripped.endswith(","):
            stripped = stripped[:-1].strip()
        if not stripped:
            continue
        # Skip prose-y lines (e.g., italic markers, inline backticks isolated).
        # A package name is a single token; reject lines containing whitespace
        # AFTER stripping the parenthetical above.
        if " " in stripped:
            continue
        # Strip surrounding backticks (e.g., `numpy`).
        if stripped.startswith("`") and stripped.endswith("`") and len(stripped) >= 2:
            stripped = stripped[1:-1].strip()
        if stripped:
            pkgs.add(stripped)
    return pkgs


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


def _env_exists(env_name: str, env_manager: str) -> bool:
    """Return True iff a named environment already exists (per env_manager).

    conda: parses `conda env list` output and matches the first token per
    non-comment line against env_name. Returns False on FileNotFoundError
    (conda not in PATH) or CalledProcessError so the caller can attempt
    creation and surface the real error.

    renv / packrat / unknown: returns False unconditionally — these
    environment managers are project-scoped and their initialization is
    idempotent, so it is safe to always attempt creation.
    """
    if env_manager == "conda":
        # Bug S3-200 / cycle I-3: force UTF-8 decoding for cross-platform
        # robustness (mirrors H6 / S3-196 fix in Unit 14 run_tests_main).
        # PYTHONIOENCODING + PYTHONUTF8 env override coerces the child to emit
        # UTF-8; text=True dropped; bytes-decode with errors=replace on the
        # parent. Defends against Windows cp1252 default decoding when
        # `conda env list` output contains non-cp1252 bytes.
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        env.setdefault("PYTHONUTF8", "1")
        try:
            result = subprocess.run(
                ["conda", "env", "list"],
                capture_output=True,  # NOTE: text=True dropped (decode bytes manually below)
                check=True,
                env=env,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False
        stdout = (result.stdout or b"").decode("utf-8", errors="replace")
        for line in stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            first_token = line.split()[0]
            if first_token == env_name:
                return True
        return False
    return False


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
        # Bug S3-202 / cycle J-2c: read the canonical schema key
        # `create_command` (per references/toolchain_manifest_schema.md and
        # the default Python/R toolchain JSONs). Previously read `create`,
        # which never matched any toolchain JSON and silently fell back --
        # ignoring archetype-specific create_command overrides (e.g. R
        # archetypes shipping `-c conda-forge` channel selection).
        create_template = toolchain.get("environment", {}).get(
            "create_command",
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
        # Bug S3-202 / cycle J-2c: same canonical-schema-key fix as the
        # mixed-archetype branch above. Read `create_command`, not `create`.
        create_template = toolchain.get("environment", {}).get(
            "create_command",
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
    # Bug S3-202 / cycle J-2b: read the canonical schema key
    # `install_command` (per references/toolchain_manifest_schema.md and the
    # default Python/R toolchain JSONs). Previously read `install`, which
    # never matched any toolchain JSON and silently fell back to the default
    # template -- masking schema-inconsistent toolchains and ignoring
    # archetype-specific install_command overrides.
    install_template = toolchain.get("environment", {}).get(
        "install_command",
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
    provision_only: bool = False,
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

    **(Bug S3-176)** When ``provision_only=True``: runs ONLY the
    blueprint-independent prefix — env-create (Step 4b, idempotent) plus
    toolchain verification (Step 4c). All blueprint-dependent steps
    (directory scaffolding, helper-svp.R templated copy, DAG validation,
    total_units derivation, regression test adaptation, build log creation)
    are SKIPPED. ``state.toolchain_status`` is written to
    ``pipeline_state.json`` and the function returns early. Used by
    Stage-0 provisioning (gate_0_3 PROFILE APPROVED) to create the conda
    env immediately after profile approval, before any blueprint exists.
    """
    primary_language = profile.get("language", {}).get("primary", "python")
    env_name = derive_env_name(project_root)

    # -----------------------------------------------------------------------
    # Step 1: Environment creation (build phase)
    # Builds the command(s) that create the environment. Execution happens
    # in Step 4b once the full package list is known. See Bug S3-137.
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
    # Bug S3-176: in provision_only mode the blueprint is not yet authored,
    # so blueprint-derived imports are skipped. Env creation still proceeds
    # with quality + bridge packages only.
    # -----------------------------------------------------------------------
    third_party_modules: List[str] = []
    if not provision_only:
        imports = _extract_imports_from_blueprint(blueprint_dir)

        for stmt in imports:
            module = _get_top_level_module(stmt)
            if (
                not _is_stdlib_or_internal(module)
                and module not in third_party_modules
            ):
                third_party_modules.append(module)

        # -------------------------------------------------------------------
        # Step 4: Import validation
        # Validates that extracted imports are resolvable. For stdlib and
        # internal modules this is a static check; third-party modules are
        # recorded for installation (actual import validation runs in the
        # created environment).
        # -------------------------------------------------------------------
        # Static validation: all imports must be parseable
        for stmt in imports:
            module = _get_top_level_module(stmt)
            if not module:
                raise ValueError(f"Could not extract module from import: {stmt}")

    # -----------------------------------------------------------------------
    # Step 4b: Environment creation and package installation (Bug S3-137)
    # Execute the commands built in Step 1 and install the packages from
    # Steps 2 and 3 into the created environment. No-op when the
    # environment already exists. Any subprocess failure propagates as
    # CalledProcessError — matches run_infrastructure_setup's contract
    # that any step failure raises.
    # -----------------------------------------------------------------------
    if env_info["commands"] and not _env_exists(env_name, env_info["env_manager"]):
        for cmd in env_info["commands"]:
            subprocess.run(cmd.split(), check=True)

        install_packages = list(all_packages)
        for pkg in env_info.get("bridge_packages", []):
            if pkg not in install_packages:
                install_packages.append(pkg)
        for pkg in third_party_modules:
            if pkg not in install_packages:
                install_packages.append(pkg)

        if install_packages and env_info["env_manager"] == "conda":
            install_cmd = _build_install_command(
                env_name, install_packages, toolchain
            )
            if install_cmd:
                subprocess.run(install_cmd.split(), check=True)

    # -----------------------------------------------------------------------
    # Step 4c: Toolchain verification (Bug S3-160 / IMPROV-19)
    # After env creation, run manifest-declared verify_commands to confirm
    # the env is functional. Sets state.toolchain_status to READY/NOT_READY
    # and raises RuntimeError on failure (matching the run_infrastructure
    # contract that any step failure raises). Fires for both Python and R
    # conda branches; renv/packrat skipped (no verify_commands in those
    # manifests yet).
    # -----------------------------------------------------------------------
    if env_info["env_manager"] == "conda":
        toolchain_path = project_root / ARTIFACT_FILENAMES["toolchain"]
        if toolchain_path.exists():
            ok, errors = verify_toolchain_ready(project_root, env_name)
            try:
                state = load_state(project_root)
            except FileNotFoundError:
                state = None
            if state is not None:
                state.toolchain_status = "READY" if ok else "NOT_READY"
                try:
                    save_state(project_root, state)
                except Exception:
                    pass
            if not ok:
                raise RuntimeError(
                    "Toolchain verification failed: "
                    + "; ".join(errors)
                )

    # -----------------------------------------------------------------------
    # Bug S3-176: provision_only mode early return.
    # In Stage-0 provisioning the blueprint does not yet exist; env-create +
    # verify is the entire job. state.toolchain_status was set by Step 4c
    # above when the conda branch ran. For non-conda branches (renv /
    # packrat / mixed without verify_commands), state remains NOT_READY and
    # the operator must address that explicitly. We also write the state
    # here defensively for the no-toolchain.json and non-conda cases so
    # routing has a deterministic readiness flag to consult.
    # -----------------------------------------------------------------------
    if provision_only:
        if env_info["env_manager"] != "conda":
            try:
                state = load_state(project_root)
            except FileNotFoundError:
                state = None
            if state is not None:
                # Non-conda paths skip mechanical verification; treat as
                # NOT_READY until manual confirmation lands. The Stage-0
                # router will hold the pipeline rather than presenting
                # gate_0_4.
                if state.toolchain_status != "READY":
                    state.toolchain_status = "NOT_READY"
                    try:
                        save_state(project_root, state)
                    except Exception:
                        pass
        return

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
        from blueprint_extractor import (
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
        # Bug S3-48 / S3-161: Generate helper-svp.R for R test infrastructure.
        # The helper exposes the package's internal symbols to the test global
        # environment so tests can call non-NAMESPACE-exported helpers regardless
        # of how testthat was launched. Pattern P45: SVP R archetypes assume
        # devtools::test() semantics (load_all with export_all = TRUE).
        helper_svp = test_dir / "helper-svp.R"
        if not helper_svp.exists():
            helper_svp.write_text(
                "# helper-svp.R -- auto-generated by SVP infrastructure setup (S3-161).\n"
                "# Exposes the package's internal symbols to the test global environment so\n"
                "# that tests can call non-NAMESPACE-exported helpers regardless of how\n"
                "# testthat was launched.\n"
                "#\n"
                "# Pattern P45: SVP R archetypes assume devtools::test() semantics\n"
                "# (load_all with export_all = TRUE). When testthat::test_dir() or other\n"
                "# runners are used directly, this helper provides equivalent symbol\n"
                "# visibility.\n"
                "\n"
                'if (requireNamespace("devtools", quietly = TRUE)) {\n'
                '  suppressMessages(devtools::load_all(".", export_all = TRUE, quiet = TRUE))\n'
                "}\n"
                "\n"
                "# Locate the package namespace by parsing DESCRIPTION rather than hardcoding.\n"
                ".svp_pkg <- tryCatch(\n"
                '  as.character(read.dcf("DESCRIPTION")[1, "Package"]),\n'
                "  error = function(e) NA_character_\n"
                ")\n"
                "\n"
                "if (!is.na(.svp_pkg)) {\n"
                "  ns <- asNamespace(.svp_pkg)\n"
                "  for (.svp_name in ls(ns, all.names = TRUE)) {\n"
                "    if (!exists(.svp_name, envir = globalenv(), inherits = FALSE)) {\n"
                "      assign(.svp_name, get(.svp_name, envir = ns), envir = globalenv())\n"
                "    }\n"
                "  }\n"
                "  rm(.svp_name, ns)\n"
                "}\n"
                "rm(.svp_pkg)\n",
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
                # Bug S3-200 / cycle I-3: force UTF-8 decoding for
                # cross-platform robustness (mirrors H6 / S3-196 fix in Unit
                # 14 run_tests_main). The regression-adapt child invokes
                # `python scripts/generate_assembly_map.py regression-adapt`
                # whose stderr can contain em-dashes, smart quotes, and
                # mojibake from upstream parser failures. PYTHONIOENCODING +
                # PYTHONUTF8 env override + bytes-decode-with-replace defends
                # against Windows cp1252 default decoding.
                env = os.environ.copy()
                env.setdefault("PYTHONIOENCODING", "utf-8")
                env.setdefault("PYTHONUTF8", "1")
                result = subprocess.run(
                    adapt_cmd,
                    capture_output=True,  # NOTE: text=True dropped (decode bytes manually below)
                    env=env,
                )
                if result.returncode != 0:
                    stderr = (result.stderr or b"").decode("utf-8", errors="replace")
                    raise RuntimeError(
                        f"Error in step 8 (regression test adaptation): {stderr}"
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


def ensure_pipeline_toolchain(project_root: Path) -> None:
    """Materialize <project_root>/toolchain.json from language default if absent.

    Reads project_profile.json for the primary language and copies the matching
    toolchain template from scripts/toolchain_defaults/<toolchain_file> to
    <project_root>/toolchain.json. No-op if the file already exists or the
    profile has no primary language.

    Bridges Stage 0 (profile approval) → Stage 3 (infrastructure setup).
    Without this, load_toolchain(project_root) raises FileNotFoundError at
    Stage 3 entry because Layer 1 pipeline toolchain was never materialized
    from its Layer 2 language default. See Bug S3-135 / spec §24.148.
    """
    toolchain_path = project_root / ARTIFACT_FILENAMES["toolchain"]
    if toolchain_path.exists():
        return

    try:
        profile = load_profile(project_root)
    except FileNotFoundError:
        # No profile yet — nothing to materialize. Caller will error naturally.
        return

    primary_lang = profile.get("language", {}).get("primary")
    if not primary_lang or primary_lang not in LANGUAGE_REGISTRY:
        return

    template = load_toolchain(project_root, language=primary_lang)
    toolchain_path.write_text(json.dumps(template, indent=2), encoding="utf-8")


def _baseline_packages(toolchain: Dict[str, Any]) -> set:
    """Bug S3-180: baseline package set = testing.framework_packages ∪ quality.packages.

    Reads the language-specific manifest's framework_packages (testing harness)
    and quality.packages (linter/formatter/etc.) and returns the union of those
    two declared sets. The baseline is the archetype-mandated package universe.
    """
    baseline: set = set()
    testing = toolchain.get("testing", {})
    for pkg in testing.get("framework_packages", []) or []:
        if pkg:
            baseline.add(pkg)
    quality = toolchain.get("quality", {})
    for pkg in quality.get("packages", []) or []:
        if pkg:
            baseline.add(pkg)
    return baseline


def _list_installed_conda_packages(env_name: str, runner=None) -> set:
    """Bug S3-180: parse ``conda list -n {env_name} --json`` output for names.

    The ``runner`` parameter accepts an injected callable with the same shape
    as ``subprocess.run`` for testability. The returned set is the lowercase
    package names reported by conda. On any failure (conda not in PATH,
    non-zero exit, malformed JSON), returns an empty set so downstream callers
    treat the env as installed-with-nothing.
    """
    if runner is None:
        runner = subprocess.run
    # Bug S3-200 / cycle I-3: force UTF-8 decoding for cross-platform
    # robustness (mirrors H6 / S3-196 fix in Unit 14 run_tests_main).
    # PYTHONIOENCODING + PYTHONUTF8 env override; text=True dropped.
    # json.loads accepts both bytes and str natively, so no decode branch
    # is needed at this site. Defends against Windows cp1252 default
    # decoding when conda list --json output contains non-cp1252 bytes.
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    try:
        result = runner(
            ["conda", "list", "-n", env_name, "--json"],
            capture_output=True,  # NOTE: text=True dropped (json.loads handles bytes-or-str)
            check=False,
            env=env,
        )
    except (FileNotFoundError, OSError):
        return set()
    if getattr(result, "returncode", 1) != 0:
        return set()
    stdout = getattr(result, "stdout", "") or ""
    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, TypeError, ValueError):
        return set()
    installed: set = set()
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict):
                name = entry.get("name")
                if isinstance(name, str) and name:
                    installed.add(name)
    return installed


def compute_dep_diff(
    project_root: Path, env_name: str, runner=None
) -> Dict[str, List[str]]:
    """Bug S3-180: compute the dep-diff at pre_stage_3 (before per-unit TDD).

    Steps:
    1. Parse ``blueprint/blueprint_contracts.md`` Package Dependencies sections
       via ``_parse_blueprint_package_deps``.
    2. Load the language-specific manifest baseline
       (``testing.framework_packages`` ∪ ``quality.packages``) via
       ``load_toolchain(project_root, language)``.
    3. ``desired = blueprint_pkgs ∪ baseline``.
    4. List currently installed packages via ``conda list -n env --json``.
    5. ``delta = desired - installed``.
    6. Partition: ``delta_baseline = delta ∩ baseline`` (auto-installable);
       ``delta_blueprint_only = delta - baseline`` (require human approval).
    7. Write ``.svp/dep_diff_pending.json`` with both partitions and return
       the same dict.

    The ``runner`` parameter is forwarded to ``_list_installed_conda_packages``
    so tests can inject a fake subprocess runner.
    """
    blueprint_dir = get_blueprint_dir(project_root)
    contracts_path = (
        blueprint_dir / Path(ARTIFACT_FILENAMES["blueprint_contracts"]).name
    )
    blueprint_pkgs = _parse_blueprint_package_deps(contracts_path)

    # Load language-specific manifest baseline.
    try:
        profile = load_profile(project_root)
        primary_lang = profile.get("language", {}).get("primary", "python")
    except (FileNotFoundError, KeyError):
        primary_lang = "python"
    try:
        toolchain = load_toolchain(project_root, language=primary_lang)
    except (FileNotFoundError, KeyError):
        toolchain = {}
    baseline = _baseline_packages(toolchain)

    desired = set(blueprint_pkgs) | baseline
    installed = _list_installed_conda_packages(env_name, runner=runner)
    delta = desired - installed

    delta_baseline = sorted(delta & baseline)
    delta_blueprint_only = sorted(delta - baseline)

    pending = {
        "delta_baseline": delta_baseline,
        "delta_blueprint_only": delta_blueprint_only,
    }

    pending_path = project_root / ".svp" / "dep_diff_pending.json"
    pending_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path.write_text(json.dumps(pending, indent=2), encoding="utf-8")

    return pending


def install_dep_delta(
    project_root: Path, env_name: str, runner=None
) -> "tuple":
    """Bug S3-180: install delta packages from ``.svp/dep_diff_pending.json``.

    Reads the pending file, constructs the install command via
    ``_build_install_command(env_name, pkgs, toolchain)`` (toolchain-driven;
    default Python toolchain uses ``conda run -n {env_name} pip install``),
    runs it through the injected ``runner``, then runs
    ``verify_toolchain_ready`` (Unit 4). On full success: sets
    ``state.toolchain_status = "READY"``, removes the pending file, returns
    ``(True, [])``. On any failure: returns ``(False, [error_messages])``;
    the pending file is preserved so the operator can inspect/retry.

    The ``runner`` parameter is the install-command subprocess runner
    (mockable for tests). When not provided, defaults to ``subprocess.run``.
    """
    if runner is None:
        runner = subprocess.run

    pending_path = project_root / ".svp" / "dep_diff_pending.json"
    if not pending_path.exists():
        return (False, ["dep_diff_pending.json not found"])

    try:
        pending = json.loads(pending_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return (False, [f"failed to parse dep_diff_pending.json: {exc}"])

    delta_baseline = pending.get("delta_baseline", []) or []
    delta_blueprint_only = pending.get("delta_blueprint_only", []) or []
    pkgs = list(delta_baseline) + [
        p for p in delta_blueprint_only if p not in delta_baseline
    ]

    if pkgs:
        # Bug S3-202 / cycle J-2a: use the toolchain's install_command
        # template via the existing _build_install_command helper. Mirrors
        # run_infrastructure_setup line 781. Previously hardcoded conda
        # install -n env -y pkgs, which ignored the toolchain JSON
        # install_command template and tripped on any pip-only / conda-forge
        # / bioconda package (gseapy, PyWGCNA in WGCNA on 2026-05-01).
        try:
            profile = load_profile(project_root)
            primary_lang = profile.get("language", {}).get("primary", "python")
        except (FileNotFoundError, KeyError):
            primary_lang = "python"
        try:
            toolchain = load_toolchain(project_root, language=primary_lang)
        except (FileNotFoundError, KeyError):
            toolchain = {}
        install_cmd_str = _build_install_command(env_name, pkgs, toolchain)
        if not install_cmd_str:
            return (False, ["_build_install_command returned empty"])
        cmd = install_cmd_str.split()
        # Bug S3-200 / cycle I-3: force UTF-8 decoding for cross-platform
        # robustness (mirrors H6 / S3-196 fix in Unit 14 run_tests_main).
        # PYTHONIOENCODING + PYTHONUTF8 env override; text=True dropped;
        # bytes-decode-with-replace on stderr with isinstance guard since
        # injected test runners return strings.
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        env.setdefault("PYTHONUTF8", "1")
        try:
            result = runner(
                cmd,
                capture_output=True,  # NOTE: text=True dropped (decode bytes manually below)
                check=False,
                env=env,
            )
        except (FileNotFoundError, OSError) as exc:
            return (False, [f"install command failed to launch: {exc}"])
        rc = getattr(result, "returncode", 1)
        if rc != 0:
            stderr_raw = getattr(result, "stderr", "") or b""
            if isinstance(stderr_raw, bytes):
                stderr = stderr_raw.decode("utf-8", errors="replace")
            else:
                stderr = stderr_raw
            return (False, [f"install command exited {rc}: {stderr.strip()}"])

    # Verify the env is now functional.
    ok, errors = verify_toolchain_ready(project_root, env_name)
    if not ok:
        return (False, list(errors))

    # Full success: update state + remove pending file.
    try:
        state = load_state(project_root)
    except FileNotFoundError:
        state = None
    if state is not None:
        state.toolchain_status = "READY"
        try:
            save_state(project_root, state)
        except Exception:
            pass
    try:
        pending_path.unlink()
    except OSError:
        pass
    return (True, [])


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
    parser.add_argument(
        "--provision-only",
        action="store_true",
        default=False,
        help=(
            "Bug S3-176: run only env-create + verify (skip blueprint-"
            "dependent steps). Used by Stage-0 provisioning."
        ),
    )
    parser.add_argument(
        "--dep-diff",
        action="store_true",
        default=False,
        help=(
            "Bug S3-180: compute pre_stage_3 dep-diff. Reads blueprint "
            "Package Dependencies + manifest baseline; writes "
            ".svp/dep_diff_pending.json listing packages to install."
        ),
    )
    parser.add_argument(
        "--install-delta",
        action="store_true",
        default=False,
        help=(
            "Bug S3-180: install pre_stage_3 dep delta from "
            ".svp/dep_diff_pending.json into the conda env, then verify."
        ),
    )
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()

    # Bug S3-180: --dep-diff and --install-delta are mutually exclusive
    # mini-modes that bypass the full 9-step run_infrastructure_setup flow.
    if args.dep_diff:
        try:
            ensure_pipeline_toolchain(project_root)
            env_name = derive_env_name(project_root)
            compute_dep_diff(project_root, env_name)
        except SystemExit:
            raise
        except Exception as e:
            print(f"Dep-diff failed: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if args.install_delta:
        try:
            env_name = derive_env_name(project_root)
            ok, errors = install_dep_delta(project_root, env_name)
            if not ok:
                print(
                    "Delta install failed: " + "; ".join(errors),
                    file=sys.stderr,
                )
                sys.exit(1)
        except SystemExit:
            raise
        except Exception as e:
            print(f"Delta install failed: {e}", file=sys.stderr)
            sys.exit(1)
        return

    try:
        profile = load_profile(project_root)
        ensure_pipeline_toolchain(project_root)
        toolchain = load_toolchain(project_root)
        language_registry = LANGUAGE_REGISTRY
        blueprint_dir = get_blueprint_dir(project_root)

        run_infrastructure_setup(
            project_root=project_root,
            profile=profile,
            toolchain=toolchain,
            language_registry=language_registry,
            blueprint_dir=blueprint_dir,
            provision_only=args.provision_only,
        )
    except SystemExit:
        raise
    except Exception as e:
        print(f"Infrastructure setup failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

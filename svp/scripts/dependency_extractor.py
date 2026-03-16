# Unit 7: Dependency Extractor and Import Validator
import ast
import json
import re
import subprocess
import sys
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path


# Well-known import-name to package-name mappings
_KNOWN_PACKAGE_MAP: Dict[str, str] = {
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "skimage": "scikit-image",
    "attr": "attrs",
    "yaml": "PyYAML",
    "bs4": "beautifulsoup4",
    "gi": "PyGObject",
    "wx": "wxPython",
    "Crypto": "pycryptodome",
    "serial": "pyserial",
    "usb": "pyusb",
    "dotenv": "python-dotenv",
    "dateutil": "python-dateutil",
}


def _get_stdlib_modules() -> set:
    """Return a set of standard library module names."""
    if hasattr(sys, "stdlib_module_names"):
        return set(sys.stdlib_module_names)
    # Fallback for older Python versions
    import pkgutil
    import importlib
    stdlib_names = set()
    for mod in pkgutil.iter_modules():
        stdlib_names.add(mod.name)
    # Add well-known stdlib modules
    stdlib_names.update({
        "os", "sys", "json", "re", "pathlib", "typing", "collections",
        "ast", "subprocess", "importlib", "functools", "itertools",
        "abc", "io", "math", "hashlib", "logging", "unittest",
        "contextlib", "dataclasses", "enum", "copy", "shutil",
        "tempfile", "textwrap", "threading", "multiprocessing",
        "argparse", "configparser", "csv", "datetime", "decimal",
        "difflib", "email", "glob", "gzip", "html", "http",
        "inspect", "operator", "pickle", "pprint", "random",
        "socket", "sqlite3", "string", "struct", "time", "traceback",
        "urllib", "uuid", "warnings", "xml", "zipfile",
    })
    return stdlib_names


def extract_all_imports(blueprint_path: Path) -> List[str]:
    """Parse Tier 2 Signatures code blocks (em-dash format) from blueprint,
    collecting import and from-import statements.
    """
    blueprint_path = Path(blueprint_path)
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")

    content = blueprint_path.read_text(encoding="utf-8")

    # Find all "### Tier 2 — Signatures" headings (em-dash \u2014 only)
    # Then extract the code blocks that follow them
    # Pattern: heading with em-dash, then look for ```python ... ```
    pattern = re.compile(
        r"###\s+Tier\s+2\s+\u2014\s+Signatures.*?\n"  # em-dash heading
        r".*?"                                           # any text between
        r"```python\s*\n(.*?)```",                       # code block
        re.DOTALL
    )

    matches = pattern.findall(content)

    if not matches:
        raise ValueError("No signature blocks found in blueprint")

    imports: List[str] = []
    for code_block in matches:
        for line in code_block.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                imports.append(stripped)

    return imports


def classify_import(import_stmt: str) -> str:
    """Classify an import statement as 'stdlib', 'third_party', or 'project_internal'."""
    # Extract the top-level module name
    stmt = import_stmt.strip()

    if stmt.startswith("from "):
        # "from X.Y import Z" -> module is "X"
        parts = stmt.split()
        module_path = parts[1]  # e.g. "src.unit_1.stub" or "typing"
        top_module = module_path.split(".")[0]
    elif stmt.startswith("import "):
        parts = stmt.split()
        module_path = parts[1]
        top_module = module_path.split(".")[0]
    else:
        top_module = stmt.split(".")[0]

    # Check project-internal prefixes
    if top_module in ("src", "svp"):
        return "project_internal"

    # Check if there's a matching .py file in a scripts/ directory on sys.path
    for p in sys.path:
        scripts_candidate = Path(p) / f"{top_module}.py"
        if scripts_candidate.exists() and "scripts" in str(Path(p)):
            return "project_internal"
        # Also check if the path itself is a scripts dir
        if Path(p).name == "scripts" and scripts_candidate.exists():
            return "project_internal"

    # Check stdlib
    stdlib_modules = _get_stdlib_modules()
    if top_module in stdlib_modules:
        return "stdlib"

    return "third_party"


def map_imports_to_packages(imports: List[str]) -> Dict[str, str]:
    """Map third-party import names to their package names."""
    if not imports:
        return {}

    result: Dict[str, str] = {}
    for stmt in imports:
        stmt = stmt.strip()
        if stmt.startswith("from "):
            parts = stmt.split()
            module_path = parts[1]
            top_module = module_path.split(".")[0]
        elif stmt.startswith("import "):
            parts = stmt.split()
            module_path = parts[1].rstrip(",")
            top_module = module_path.split(".")[0]
        else:
            continue

        # Only map third-party imports
        classification = classify_import(stmt)
        if classification != "third_party":
            continue

        # Look up known mapping or use module name as package name
        package_name = _KNOWN_PACKAGE_MAP.get(top_module, top_module)
        result[top_module] = package_name

    return result


def create_conda_environment(
    env_name: str,
    packages: Dict[str, str],
    python_version: str = "3.11",
    toolchain: Optional[Dict[str, Any]] = None,
) -> bool:
    """Create a conda environment, install packages and framework dependencies.

    SVP 2.1: Also installs quality.packages unconditionally.
    """
    try:
        if toolchain:
            env_config = toolchain.get("environment", {})
            testing_config = toolchain.get("testing", {})
            quality_config = toolchain.get("quality", {})

            # Remove prior environment
            remove_cmd = env_config.get("remove", "conda env remove -n {env_name} -y")
            remove_cmd = remove_cmd.format(env_name=env_name)
            try:
                subprocess.run(remove_cmd, shell=True, check=True, capture_output=True)
            except subprocess.CalledProcessError:
                pass  # Environment may not exist yet

            # Create environment
            create_cmd = env_config.get("create", "conda create -n {env_name} python={python_version} -y")
            create_cmd = create_cmd.format(env_name=env_name, python_version=python_version)
            subprocess.run(create_cmd, shell=True, check=True, capture_output=True)

            # Install framework packages
            framework_packages = testing_config.get("framework_packages", ["pytest", "pytest-cov"])
            install_template = env_config.get("install", "conda run -n {env_name} pip install {packages}")

            if framework_packages:
                install_cmd = install_template.format(
                    env_name=env_name,
                    packages=" ".join(framework_packages),
                )
                subprocess.run(install_cmd, shell=True, check=True, capture_output=True)

            # Install quality packages (NEW IN 2.1)
            quality_packages = quality_config.get("packages", [])
            if quality_packages:
                install_cmd = install_template.format(
                    env_name=env_name,
                    packages=" ".join(quality_packages),
                )
                subprocess.run(install_cmd, shell=True, check=True, capture_output=True)

            # Install project packages
            if packages:
                pkg_list = " ".join(packages.values())
                install_cmd = install_template.format(
                    env_name=env_name,
                    packages=pkg_list,
                )
                subprocess.run(install_cmd, shell=True, check=True, capture_output=True)

        else:
            # Hardcoded commands without toolchain
            # Remove prior environment
            try:
                subprocess.run(
                    f"conda env remove -n {env_name} -y",
                    shell=True, check=True, capture_output=True,
                )
            except subprocess.CalledProcessError:
                pass

            # Create environment
            subprocess.run(
                f"conda create -n {env_name} python={python_version} -y",
                shell=True, check=True, capture_output=True,
            )

            # Install framework packages (pytest, pytest-cov)
            subprocess.run(
                f"conda run -n {env_name} pip install pytest pytest-cov",
                shell=True, check=True, capture_output=True,
            )

            # Install quality packages (ruff, mypy) -- NEW IN 2.1
            subprocess.run(
                f"conda run -n {env_name} pip install ruff mypy",
                shell=True, check=True, capture_output=True,
            )

            # Install project packages
            if packages:
                pkg_list = " ".join(packages.values())
                subprocess.run(
                    f"conda run -n {env_name} pip install {pkg_list}",
                    shell=True, check=True, capture_output=True,
                )

        return True

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Conda environment creation failed: {e}") from e


def validate_imports(
    env_name: str,
    imports: List[str],
    toolchain: Optional[Dict[str, Any]] = None,
) -> List[Tuple[str, str]]:
    """Validate that each import can be resolved in the given conda environment."""
    if not imports:
        return []

    failures: List[Tuple[str, str]] = []

    # Determine run prefix
    if toolchain:
        env_config = toolchain.get("environment", {})
        run_prefix = env_config.get("run_prefix", f"conda run -n {env_name}")
        run_prefix = run_prefix.format(env_name=env_name)
    else:
        run_prefix = f"conda run -n {env_name}"

    for imp in imports:
        # Extract the actual import statement to test
        # Build a python -c command to try the import
        cmd = f'{run_prefix} python -c "{imp}"'
        try:
            subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            error_msg = str(e.stderr) if e.stderr else str(e)
            failures.append((imp, error_msg))

    return failures


def create_project_directories(project_root: Path, total_units: int) -> None:
    """Create src/unit_N/ and tests/unit_N/ directories for each unit.

    Bug 24 fix: Validates that total_units is a positive integer before use.
    """
    # Bug 24 guard: total_units must be a positive integer
    if not isinstance(total_units, int) or isinstance(total_units, bool):
        raise TypeError(
            f"total_units must be a positive integer, got {type(total_units).__name__}"
        )
    if total_units <= 0:
        raise TypeError(
            f"total_units must be a positive integer, got {type(total_units).__name__}"
        )

    assert isinstance(total_units, int) and total_units > 0, \
        "total_units must be a positive integer -- never None (Bug 24 guard)"

    project_root = Path(project_root)
    for i in range(1, total_units + 1):
        src_dir = project_root / "src" / f"unit_{i}"
        src_dir.mkdir(parents=True, exist_ok=True)
        test_dir = project_root / "tests" / f"unit_{i}"
        test_dir.mkdir(parents=True, exist_ok=True)


def validate_dependency_dag(blueprint_path: Path) -> List[str]:
    """Parse each unit's dependency list from the blueprint, build the dependency graph,
    and verify: (1) no unit references a unit with a higher number, (2) no cycles exist,
    (3) every referenced unit number exists.

    Returns a list of violation descriptions (empty if valid).
    """
    blueprint_path = Path(blueprint_path)
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")

    content = blueprint_path.read_text(encoding="utf-8")

    # Parse unit headings: "## Unit N: Title"
    unit_pattern = re.compile(r"^##\s+Unit\s+(\d+)\s*:", re.MULTILINE)
    unit_matches = list(unit_pattern.finditer(content))

    if not unit_matches:
        return []

    unit_numbers = set()
    for m in unit_matches:
        unit_numbers.add(int(m.group(1)))

    # Parse dependencies for each unit
    # Look for "Depends on: Unit X, Unit Y" or similar patterns within each unit's section
    violations: List[str] = []
    dep_pattern = re.compile(r"[Dd]epends?\s+on\s*:\s*(.*?)$", re.MULTILINE)

    for i, match in enumerate(unit_matches):
        unit_num = int(match.group(1))
        # Get the section text (from this heading to the next heading or end of file)
        start = match.end()
        end = unit_matches[i + 1].start() if i + 1 < len(unit_matches) else len(content)
        section = content[start:end]

        dep_matches = dep_pattern.findall(section)
        for dep_str in dep_matches:
            # Extract unit numbers from dependency string
            dep_unit_pattern = re.compile(r"[Uu]nit\s+(\d+)")
            dep_units = dep_unit_pattern.findall(dep_str)
            for dep_num_str in dep_units:
                dep_num = int(dep_num_str)

                # Check forward reference (higher number)
                if dep_num >= unit_num:
                    violations.append(
                        f"Unit {unit_num} depends on Unit {dep_num} "
                        f"(forward dependency)"
                    )

                # Check existence
                if dep_num not in unit_numbers:
                    violations.append(
                        f"Unit {unit_num} depends on Unit {dep_num} "
                        f"which does not exist"
                    )

    # Check for cycles using topological sort
    # Build adjacency list
    adjacency: Dict[int, List[int]] = {n: [] for n in unit_numbers}
    for i, match in enumerate(unit_matches):
        unit_num = int(match.group(1))
        start = match.end()
        end = unit_matches[i + 1].start() if i + 1 < len(unit_matches) else len(content)
        section = content[start:end]

        dep_matches = dep_pattern.findall(section)
        for dep_str in dep_matches:
            dep_unit_pattern = re.compile(r"[Uu]nit\s+(\d+)")
            dep_units = dep_unit_pattern.findall(dep_str)
            for dep_num_str in dep_units:
                dep_num = int(dep_num_str)
                if dep_num in unit_numbers:
                    adjacency[unit_num].append(dep_num)

    # Detect cycles via DFS
    visited: set = set()
    rec_stack: set = set()

    def _has_cycle(node: int) -> bool:
        visited.add(node)
        rec_stack.add(node)
        for neighbor in adjacency.get(node, []):
            if neighbor not in visited:
                if _has_cycle(neighbor):
                    return True
            elif neighbor in rec_stack:
                violations.append(
                    f"Cycle detected involving Unit {node} and Unit {neighbor}"
                )
                return True
        rec_stack.discard(node)
        return False

    for node in sorted(unit_numbers):
        if node not in visited:
            _has_cycle(node)

    return violations


def derive_total_units(blueprint_path: Path) -> int:
    """Read the blueprint and count the number of '## Unit N:' headings.

    Returns a positive integer. This is the canonical source for total_units --
    it must NOT be read from pipeline state during infrastructure setup (Bug 24 fix).
    """
    blueprint_path = Path(blueprint_path)
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")

    content = blueprint_path.read_text(encoding="utf-8")

    # Count "## Unit N:" headings
    unit_pattern = re.compile(r"^##\s+Unit\s+\d+\s*:", re.MULTILINE)
    matches = unit_pattern.findall(content)

    result = len(matches)
    assert result > 0, "total_units must be a positive integer, never None or zero"
    return result


def run_infrastructure_setup(
    project_root: Path,
    toolchain: Optional[Dict[str, Any]] = None,
) -> None:
    """Orchestrate the full infrastructure setup pipeline.

    Bug 24 fix: total_units is DERIVED from the blueprint, never read from state.
    Infrastructure setup is the PRODUCER of total_units.
    """
    project_root = Path(project_root)

    # Read pipeline state
    state_path = project_root / "pipeline_state.json"
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    project_name = state.get("project_name", "project")
    blueprint_path = Path(state.get("blueprint_path", str(project_root / "blueprint.md")))

    # Load toolchain from file if not provided
    if toolchain is None:
        toolchain_path = project_root / "toolchain.json"
        if toolchain_path.exists():
            with open(toolchain_path, "r", encoding="utf-8") as f:
                toolchain = json.load(f)

    # Derive env_name using Unit 1's canonical derivation
    try:
        from svp_config import derive_env_name
        env_name = derive_env_name(project_name)
    except ImportError:
        # Fallback if svp_config is not available
        env_name = project_name.lower().replace(" ", "_").replace("-", "_")

    # Step 0: Validate dependency DAG
    validate_dependency_dag(blueprint_path)

    # Step 1: Extract all imports
    all_imports = extract_all_imports(blueprint_path)

    # Step 2: Filter to third-party only
    third_party_imports = [
        imp for imp in all_imports if classify_import(imp) == "third_party"
    ]

    # Step 3: Map imports to packages
    package_map = map_imports_to_packages(third_party_imports)

    # Step 4: Create conda environment (with framework and quality packages)
    create_conda_environment(env_name, package_map, toolchain=toolchain)

    # Step 5: Validate imports (third-party only)
    failures = validate_imports(env_name, third_party_imports, toolchain=toolchain)

    if failures:
        failed_names = ", ".join(f[0] for f in failures)
        raise RuntimeError(f"Import validation failed for: {failed_names}")

    # Step 6: Derive total_units from blueprint (Bug 24 fix -- NOT from state)
    total_units = derive_total_units(blueprint_path)

    # Step 7: Create project directories using derived count
    create_project_directories(project_root, total_units)

    # Step 8: Write derived total_units back to pipeline state
    state["total_units"] = total_units
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def main() -> None:
    """CLI wrapper that orchestrates infrastructure setup."""
    try:
        # Default to current directory
        project_root = Path(".")
        run_infrastructure_setup(project_root)
        print("COMMAND_SUCCEEDED")
    except Exception as e:
        print(f"COMMAND_FAILED: {e}")


if __name__ == "__main__":
    main()

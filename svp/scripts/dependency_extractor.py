import ast
import re
import subprocess
import sys
from typing import Dict, Any, List, Tuple, Set
from pathlib import Path


# Well-known mapping from Python import module names to pip/conda package names.
# When a third-party module name differs from its package name, this lookup is used.
_IMPORT_TO_PACKAGE: Dict[str, str] = {
    "yaml": "pyyaml",
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4",
    "attr": "attrs",
    "gi": "pygobject",
    "Crypto": "pycryptodome",
    "serial": "pyserial",
    "usb": "pyusb",
    "wx": "wxPython",
    "dateutil": "python-dateutil",
    "jose": "python-jose",
    "dotenv": "python-dotenv",
    "magic": "python-magic",
    "lxml": "lxml",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "pytz": "pytz",
    "toml": "toml",
    "tomli": "tomli",
}


def _get_stdlib_modules() -> Set[str]:
    """Return a set of standard library top-level module names."""
    if hasattr(sys, "stdlib_module_names"):
        return set(sys.stdlib_module_names)
    # Fallback for older Python versions
    import pkgutil
    import importlib
    stdlib_path = Path(importlib.__file__).parent.parent
    return {mod.name for mod in pkgutil.iter_modules([str(stdlib_path)])}


def _extract_top_level_module(import_stmt: str) -> str:
    """Extract the top-level module name from an import statement string."""
    stmt = import_stmt.strip()
    if stmt.startswith("from "):
        # "from X.Y import Z" -> top-level module is X
        parts = stmt.split()
        if len(parts) >= 2:
            module_path = parts[1]
            return module_path.split(".")[0]
        return ""
    elif stmt.startswith("import "):
        # "import X.Y" -> top-level module is X
        parts = stmt.split()
        if len(parts) >= 2:
            module_path = parts[1].rstrip(",")
            return module_path.split(".")[0]
        return ""
    else:
        return stmt.split(".")[0]


def extract_all_imports(blueprint_path: Path) -> List[str]:
    """Parse every '### Tier 2 \u2014 Signatures' code block across all units
    and collect all import and from...import statements.

    Heading format must use an em-dash (spec Section 24.13).
    """
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")

    content = blueprint_path.read_text(encoding="utf-8")

    # The heading uses an em-dash: "### Tier 2 \u2014 Signatures"
    # Split on this heading to find all signature sections
    heading = "### Tier 2 \u2014 Signatures"
    sections = content.split(heading)

    if len(sections) <= 1:
        raise ValueError("No signature blocks found in blueprint")

    all_imports: List[str] = []
    seen: Set[str] = set()

    def _collect_import_node(node: ast.AST) -> None:
        """Helper to collect import statements from an AST node."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                stmt = f"import {alias.name}"
                if stmt not in seen:
                    seen.add(stmt)
                    all_imports.append(stmt)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names = ", ".join(a.name for a in node.names)
                stmt = f"from {node.module} import {names}"
                if stmt not in seen:
                    seen.add(stmt)
                    all_imports.append(stmt)

    # For each section after the heading, extract the first code block
    for section in sections[1:]:
        # Find the first ```python ... ``` code block
        match = re.search(r"```python\s*\n(.*?)```", section, re.DOTALL)
        if not match:
            continue

        code_block = match.group(1)

        # Parse the code block to extract imports
        try:
            tree = ast.parse(code_block)
        except SyntaxError:
            # Code blocks with ellipsis function bodies etc. -- try line-by-line
            for line in code_block.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("import ") or line.startswith("from "):
                    try:
                        mini_tree = ast.parse(line)
                        for node in ast.walk(mini_tree):
                            _collect_import_node(node)
                    except SyntaxError:
                        continue
            continue

        for node in ast.walk(tree):
            _collect_import_node(node)

    assert all(isinstance(s, str) for s in all_imports), "All imports must be strings"
    return all_imports


def classify_import(import_stmt: str) -> str:
    """Determine whether an import is 'stdlib', 'third_party', or 'project'.

    Classification logic:
    - If the top-level module is in sys.stdlib_module_names -> 'stdlib'
    - If the import references a project-internal module (e.g. src.*) -> 'project'
    - Otherwise -> 'third_party'
    """
    top_level = _extract_top_level_module(import_stmt)

    # Check for project-internal imports
    if top_level in ("src", "svp"):
        return "project"

    # Check against stdlib
    stdlib_modules = _get_stdlib_modules()
    if top_level in stdlib_modules:
        return "stdlib"

    return "third_party"


def map_imports_to_packages(imports: List[str]) -> Dict[str, str]:
    """Map third-party import module names to pip/conda package names.

    Only includes third-party imports. For each import, extracts the top-level
    module name and maps it to the corresponding package name.
    """
    packages: Dict[str, str] = {}

    for imp in imports:
        classification = classify_import(imp)
        if classification != "third_party":
            continue

        top_level = _extract_top_level_module(imp)

        # Map to package name using well-known lookup or identity mapping
        if top_level in _IMPORT_TO_PACKAGE:
            packages[top_level] = _IMPORT_TO_PACKAGE[top_level]
        else:
            # Most packages have the same name as their import module
            packages[top_level] = top_level

    return packages


def create_conda_environment(
    env_name: str, packages: Dict[str, str], python_version: str = "3.11"
) -> bool:
    """Create a conda environment and install packages.

    Uses `conda create` to create the environment and installs packages.
    Uses `conda run -n {env_name}` for all operations (spec Section 4.3).
    """
    try:
        # Create the conda environment
        create_cmd = [
            "conda", "create", "-n", env_name,
            f"python={python_version}",
            "--yes", "--quiet"
        ]
        result = subprocess.run(
            create_cmd,
            capture_output=True,
            text=True,
            timeout=600
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Conda environment creation failed: {result.stderr.strip()}"
            )

        # Install packages if any, using conda run
        if packages:
            package_list = list(packages.values())
            install_cmd = [
                "conda", "run", "-n", env_name,
                "pip", "install"
            ] + package_list
            result = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Conda environment creation failed: {result.stderr.strip()}"
                )

        return True

    except RuntimeError:
        raise
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"Conda environment creation failed: {e}")
    except Exception as e:
        raise RuntimeError(
            f"Conda environment creation failed: {e}"
        )


def validate_imports(env_name: str, imports: List[str]) -> List[Tuple[str, str]]:
    """Validate that each import resolves in the given conda environment.

    Executes each import in the environment via
    `conda run -n {env_name} python -c "import ..."` and returns a list
    of (import, error) tuples for failures.
    """
    failures: List[Tuple[str, str]] = []

    for imp in imports:
        # Use the import statement directly as python code
        stmt = imp.strip()
        if stmt.startswith("from ") or stmt.startswith("import "):
            import_code = stmt
        else:
            import_code = f"import {stmt}"

        cmd = [
            "conda", "run", "-n", env_name,
            "python", "-c", import_code
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode != 0:
                error_msg = (
                    result.stderr.strip().splitlines()[-1]
                    if result.stderr.strip()
                    else "Unknown error"
                )
                failures.append((imp, error_msg))
        except subprocess.TimeoutExpired:
            failures.append((imp, "Import timed out"))
        except FileNotFoundError:
            failures.append((imp, "conda not found on PATH"))

    return failures


def create_project_directories(
    project_root: Path, total_units: int
) -> None:
    """Create src/unit_N/ and tests/unit_N/ directories for each unit."""
    for n in range(1, total_units + 1):
        src_dir = project_root / "src" / f"unit_{n}"
        test_dir = project_root / "tests" / f"unit_{n}"

        src_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)

        # Create __init__.py files if they don't exist
        src_init = src_dir / "__init__.py"
        if not src_init.exists():
            src_init.touch()

        test_init = test_dir / "__init__.py"
        if not test_init.exists():
            test_init.touch()

    # Also ensure top-level src/__init__.py and tests/__init__.py exist
    src_top_init = project_root / "src" / "__init__.py"
    if not src_top_init.exists():
        src_top_init.touch()

    tests_top_init = project_root / "tests" / "__init__.py"
    if not tests_top_init.exists():
        tests_top_init.touch()


def derive_env_name(project_name: str) -> str:
    """Apply the canonical derivation for environment name.

    Canonical derivation: project_name.lower().replace(" ", "_").replace("-", "_")
    (spec Section 4.3). This derivation must be used consistently -- never hardcoded.
    """
    result = project_name.lower().replace(" ", "_").replace("-", "_")

    assert result == project_name.lower().replace(" ", "_").replace("-", "_"), \
        "Env name must follow the canonical derivation"
    assert " " not in result, "Env name must not contain spaces"
    assert "-" not in result, "Env name must not contain hyphens"

    return result


def main() -> None:
    """CLI wrapper for setup_infrastructure.

    Reads the blueprint, extracts imports, creates the conda environment,
    validates imports, and creates project directories.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract dependencies and set up infrastructure"
    )
    parser.add_argument(
        "blueprint_path",
        type=Path,
        help="Path to the blessed blueprint file"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
        help="Project root directory"
    )
    parser.add_argument(
        "--project-name",
        type=str,
        default=None,
        help="Project name (used to derive conda env name)"
    )
    parser.add_argument(
        "--total-units",
        type=int,
        default=None,
        help="Total number of units"
    )
    parser.add_argument(
        "--python-version",
        type=str,
        default="3.11",
        help="Python version for the conda environment"
    )
    parser.add_argument(
        "--skip-conda",
        action="store_true",
        help="Skip conda environment creation and validation"
    )

    args = parser.parse_args()

    blueprint_path = args.blueprint_path
    project_root = args.project_root

    # Extract imports from blueprint
    print(f"Extracting imports from: {blueprint_path}")
    imports = extract_all_imports(blueprint_path)
    print(f"Found {len(imports)} unique import statements")

    # Classify and map to packages
    packages = map_imports_to_packages(imports)
    print(f"Identified {len(packages)} third-party packages: {list(packages.values())}")

    # Derive env name
    if args.project_name:
        env_name = derive_env_name(args.project_name)
    else:
        # Use project root directory name as fallback
        env_name = derive_env_name(project_root.resolve().name)

    if not args.skip_conda:
        # Create conda environment
        print(f"Creating conda environment: {env_name}")
        create_conda_environment(env_name, packages, args.python_version)
        print("Environment created successfully")

        # Validate imports
        print("Validating imports...")
        failures = validate_imports(env_name, imports)
        if failures:
            failed_imports = ", ".join(f[0] for f in failures)
            raise RuntimeError(f"Import validation failed for: {failed_imports}")
        print("All imports validated successfully")

    # Create project directories
    if args.total_units:
        print(f"Creating project directories for {args.total_units} units")
        create_project_directories(project_root, args.total_units)
        print("Project directories created")

    print("Infrastructure setup complete")


if __name__ == "__main__":
    main()

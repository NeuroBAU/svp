"""Unit 28: Plugin Manifest, Structural Validation, and Compliance Scan.

Provides plugin manifest generation, structural validation, compliance scanning,
dispatch exhaustiveness verification, and various plugin-schema validators.
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Set, Tuple

# ---------------------------------------------------------------------------
# Valid Claude Code tool names (for skill/agent frontmatter validation)
# ---------------------------------------------------------------------------

_VALID_TOOL_NAMES = {
    "Read",
    "Write",
    "Edit",
    "Bash",
    "Glob",
    "Grep",
    "Agent",
    "WebFetch",
    "WebSearch",
    "TodoRead",
    "TodoWrite",
}

# ---------------------------------------------------------------------------
# Valid model identifiers for skill/agent frontmatter
# ---------------------------------------------------------------------------

_VALID_MODEL_VALUES = {
    "sonnet",
    "opus",
    "haiku",
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
    "claude-haiku-3-5-20241022",
    "claude-opus-4-6",
}

# ---------------------------------------------------------------------------
# The 12 hook event set
# ---------------------------------------------------------------------------

_VALID_HOOK_EVENTS = {
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "PermissionRequest",
    "PreCompact",
    "PostCompact",
    "SubagentStart",
    "SubagentStop",
    "ConfigChange",
    "Stop",
    # Common filesystem/lifecycle events (Claude Code supports additional events)
    "on_save",
    "on_load",
    "on_close",
    "on_open",
    "on_change",
    "on_delete",
    "on_create",
    "on_rename",
    "on_error",
    "Notification",
}

# Tool-related events that support the matcher field
_TOOL_EVENTS = {"PreToolUse", "PostToolUse", "PostToolUseFailure"}

# ---------------------------------------------------------------------------
# Valid hook types
# ---------------------------------------------------------------------------

_VALID_HOOK_TYPES = {"command", "http", "prompt", "agent"}

# ---------------------------------------------------------------------------
# Skill frontmatter recognized fields
# ---------------------------------------------------------------------------

_SKILL_FRONTMATTER_FIELDS = {
    "name",
    "description",
    "argument-hint",
    "allowed-tools",
    "model",
    "effort",
    "context",
    "agent",
    "disable-model-invocation",
    "user-invocable",
}

# Valid effort values
_VALID_EFFORT_VALUES = {"low", "medium", "high", "max"}

# ---------------------------------------------------------------------------
# Agent frontmatter recognized fields
# ---------------------------------------------------------------------------

_AGENT_FRONTMATTER_FIELDS = {
    "name",
    "description",
    "model",
    "effort",
    "maxTurns",
    "disallowedTools",
    "skills",
    "memory",
    "background",
    "isolation",
}

# ---------------------------------------------------------------------------
# Plugin manifest fields (Section 40.7.1) -- all 12
# ---------------------------------------------------------------------------

_PLUGIN_MANIFEST_REQUIRED = {"name", "description", "version", "author"}
_PLUGIN_MANIFEST_OPTIONAL = {
    "mcpServers",
    "lspServers",
    "hooks",
    "commands",
    "agents",
    "skills",
    "outputStyles",
    "tools",
    "settings",
    "permissions",
}
_PLUGIN_MANIFEST_ALL = _PLUGIN_MANIFEST_REQUIRED | _PLUGIN_MANIFEST_OPTIONAL

# ---------------------------------------------------------------------------
# All six dispatch table names
# ---------------------------------------------------------------------------

_ALL_DISPATCH_TABLE_NAMES = {
    "SIGNATURE_PARSERS",
    "STUB_GENERATORS",
    "TEST_OUTPUT_PARSERS",
    "QUALITY_RUNNERS",
    "PROJECT_ASSEMBLERS",
    "COMPLIANCE_SCANNERS",
}

# Tables keyed by language ID (language name directly)
_ID_KEYED_TABLES = {
    "PROJECT_ASSEMBLERS",
    "COMPLIANCE_SCANNERS",
    "SIGNATURE_PARSERS",
}

# Tables keyed by dispatch key from a registry field
_DISPATCH_KEY_FIELDS = {
    "STUB_GENERATORS": "stub_generator_key",
    "TEST_OUTPUT_PARSERS": "test_output_parser_key",
    "QUALITY_RUNNERS": "quality_runner_key",
}

# Mapping from required_dispatch_entries field names to dispatch table names
_DISPATCH_ENTRY_TO_TABLE = {
    "stub_generator_key": "STUB_GENERATORS",
    "test_output_parser_key": "TEST_OUTPUT_PARSERS",
    "quality_runner_key": "QUALITY_RUNNERS",
    # Also accept table names directly for required_dispatch_entries
    "STUB_GENERATORS": "STUB_GENERATORS",
    "TEST_OUTPUT_PARSERS": "TEST_OUTPUT_PARSERS",
    "QUALITY_RUNNERS": "QUALITY_RUNNERS",
    "SIGNATURE_PARSERS": "SIGNATURE_PARSERS",
    "PROJECT_ASSEMBLERS": "PROJECT_ASSEMBLERS",
    "COMPLIANCE_SCANNERS": "COMPLIANCE_SCANNERS",
}

# Plugin composite keys for claude_code_plugin archetype
_PLUGIN_COMPOSITE_KEYS = {"plugin_markdown", "plugin_bash", "plugin_json"}
_PLUGIN_COMPOSITE_TABLES = {"STUB_GENERATORS", "TEST_OUTPUT_PARSERS", "QUALITY_RUNNERS"}


# ---------------------------------------------------------------------------
# Compliance Scanners
# ---------------------------------------------------------------------------


def _has_conda_run_prefix(text: str, match_start: int) -> bool:
    """Check if the text before match_start contains 'conda run -n' prefix."""
    prefix = text[:match_start]
    # Look for 'conda run -n <name> ' pattern near the end of the prefix
    return bool(re.search(r"conda\s+run\s+-n\s+\S+\s+$", prefix))


def _python_compliance_scan(
    src_dir: Path,
    tests_dir: Path,
    language_config: Dict[str, Any],
    toolchain_config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """AST-based compliance scan for Python files.

    Scans for banned environment management patterns based on the
    environment_manager setting.
    """
    findings: List[Dict[str, Any]] = []

    # Determine environment manager
    env_manager = toolchain_config.get("environment_manager") or language_config.get(
        "environment_manager", "conda"
    )

    # Define simple banned patterns per environment
    # For conda: ban bare pip, python, pytest NOT preceded by conda run -n
    # We use simple word boundary matching and check prefix separately
    if env_manager == "conda":
        banned_words = [
            ("pip", "bare pip (not preceded by conda run -n)"),
            ("python", "bare python (not preceded by conda run -n)"),
            ("pytest", "bare pytest (not preceded by conda run -n)"),
        ]
    elif env_manager == "pyenv":
        banned_words = [
            ("conda", "conda command in pyenv environment"),
        ]
    elif env_manager == "venv":
        banned_words = [
            ("conda", "conda command in venv environment"),
        ]
    elif env_manager == "poetry":
        banned_words = [
            ("conda", "conda command in poetry environment"),
            ("pip", "bare pip install in poetry environment"),
        ]
    elif env_manager == "none":
        banned_words = [
            ("conda", "environment manager command without environment manager"),
            ("pyenv", "environment manager command without environment manager"),
            ("poetry", "environment manager command without environment manager"),
        ]
    else:
        banned_words = []

    if not banned_words:
        return findings

    # Also check poetry-specific: bare pip install
    poetry_pip_install = env_manager == "poetry"

    # Collect Python files from src_dir and tests_dir
    dirs_to_scan = []
    if src_dir.exists():
        dirs_to_scan.append(src_dir)
    if tests_dir.exists():
        dirs_to_scan.append(tests_dir)

    for scan_dir in dirs_to_scan:
        for py_file in scan_dir.rglob("*.py"):
            try:
                source = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # AST-based scan: look for string literals containing banned patterns
            try:
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    text = node.value
                    for word, description in banned_words:
                        pattern = re.compile(r"\b" + re.escape(word) + r"\b")
                        for m in pattern.finditer(text):
                            # For conda env, check if preceded by conda run -n
                            if env_manager == "conda":
                                if _has_conda_run_prefix(text, m.start()):
                                    continue
                            findings.append(
                                {
                                    "file": str(py_file),
                                    "line": getattr(node, "lineno", 0),
                                    "severity": "error",
                                    "message": description,
                                }
                            )

                    # Poetry: check for bare pip install
                    if poetry_pip_install:
                        for m in re.finditer(r"\bpip\s+install\b", text):
                            findings.append(
                                {
                                    "file": str(py_file),
                                    "line": getattr(node, "lineno", 0),
                                    "severity": "error",
                                    "message": "bare pip install in poetry environment",
                                }
                            )

    return findings


def _r_compliance_scan(
    src_dir: Path,
    tests_dir: Path,
    language_config: Dict[str, Any],
    toolchain_config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Regex-based compliance scan for R files.

    Scans for banned patterns based on the environment manager.
    """
    findings: List[Dict[str, Any]] = []

    env_manager = toolchain_config.get("environment_manager") or language_config.get(
        "environment_manager", "renv"
    )

    if env_manager == "renv":
        simple_patterns = [
            (r"\binstall\.packages\s*\(", "install.packages() in renv environment"),
            (
                r"\bsystem\s*\([^)]*\b(?:pip|conda)\b",
                "system() containing pip/conda in renv environment",
            ),
        ]
    elif env_manager == "conda":
        simple_patterns = [
            (r"\binstall\.packages\s*\(", "install.packages() in conda R environment"),
        ]
        # For bare Rscript we need a special check
    else:
        simple_patterns = []

    # Collect R files from src_dir and tests_dir
    dirs_to_scan = []
    if src_dir.exists():
        dirs_to_scan.append(src_dir)
    if tests_dir.exists():
        dirs_to_scan.append(tests_dir)

    for scan_dir in dirs_to_scan:
        for r_file in scan_dir.rglob("*.R"):
            try:
                source = r_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            lines = source.splitlines()
            for line_no, line in enumerate(lines, start=1):
                for pat, description in simple_patterns:
                    if re.search(pat, line):
                        findings.append(
                            {
                                "file": str(r_file),
                                "line": line_no,
                                "severity": "error",
                                "message": description,
                            }
                        )

                # conda env: check for bare Rscript without conda run
                if env_manager == "conda":
                    for m in re.finditer(r"\bRscript\b", line):
                        # Check if preceded by conda run -n
                        prefix = line[: m.start()]
                        if not re.search(r"conda\s+run\s+-n\s+\S+\s+$", prefix):
                            findings.append(
                                {
                                    "file": str(r_file),
                                    "line": line_no,
                                    "severity": "error",
                                    "message": "bare Rscript without conda run in conda environment",
                                }
                            )

    return findings


COMPLIANCE_SCANNERS: Dict[
    str, Callable[[Path, Path, Dict[str, Any], Dict[str, Any]], List[Dict[str, Any]]]
] = {
    "python": _python_compliance_scan,
    "r": _r_compliance_scan,
}


# ---------------------------------------------------------------------------
# Bug S3-113: Delivered repo content validation
# ---------------------------------------------------------------------------


def validate_delivered_repo_contents(project_root: Path) -> List[Dict[str, Any]]:
    """Validate the contents of the delivered repository at state.delivered_repo_path.

    Returns a list of findings in the same format as _python_compliance_scan:
      {"file": str, "line": int, "severity": str, "message": str}

    Checks (Bug S3-113):
      1. Required root-level delivery files are present (language-dependent).
      2. Every key in .svp/assembly_map.json's repo_to_workspace exists at
         the corresponding path inside delivered_repo_path (after stripping
         the svp-repo/ prefix).
      3. For Python archetype: pyproject.toml parses as TOML, has
         [build-system], and build-backend == "setuptools.build_meta".

    If state.delivered_repo_path is not set, or the directory does not exist,
    the function returns [] — content checks are silently skipped. The
    expectation is that compliance_scan runs after Bug S3-112 dispatch has
    already validated existence; but this function is defensive and does
    not raise. This allows compliance_scan_main to remain usable for
    source-tree-only scanning during development.
    """
    findings: List[Dict[str, Any]] = []

    # --- Load state ---
    try:
        from pipeline_state import load_state
        state = load_state(project_root)
    except Exception:
        return findings
    delivered_raw = getattr(state, "delivered_repo_path", None)
    if not delivered_raw:
        return findings
    delivered = Path(delivered_raw)
    if not delivered.is_dir():
        return findings

    # --- Load profile ---
    try:
        from profile_schema import load_profile
        profile = load_profile(project_root)
    except Exception:
        profile = {}
    language = profile.get("language", {}).get("primary", "python")

    # --- Check 1: required root-level delivery files ---
    if language == "python":
        required = [
            "pyproject.toml",
            "README.md",
            "CHANGELOG.md",
            "LICENSE",
            ".gitignore",
            "environment.yml",
        ]
    elif language == "r":
        required = [
            "DESCRIPTION",
            "NAMESPACE",
            "README.md",
            "CHANGELOG.md",
            "LICENSE",
            ".gitignore",
            "environment.yml",
        ]
    else:
        required = ["README.md", "LICENSE", ".gitignore"]
    for fname in required:
        path = delivered / fname
        if not path.exists():
            findings.append(
                {
                    "file": str(path),
                    "line": 0,
                    "severity": "error",
                    "message": (
                        f"delivered repo missing required file '{fname}' "
                        f"for language '{language}' (Bug S3-113)"
                    ),
                }
            )

    # --- Check 2: assembly-map parity ---
    map_path = project_root / ".svp" / "assembly_map.json"
    if map_path.is_file():
        try:
            data = json.loads(map_path.read_text())
            r2w = data.get("repo_to_workspace", {})
        except Exception:
            r2w = {}
        for deployed_rel in sorted(r2w.keys()):
            # Strip the svp-repo/ prefix to get the path inside delivered.
            if deployed_rel.startswith("svp-repo/"):
                rel = deployed_rel[len("svp-repo/"):]
            else:
                rel = deployed_rel
            target = delivered / rel
            if not target.exists():
                findings.append(
                    {
                        "file": str(target),
                        "line": 0,
                        "severity": "error",
                        "message": (
                            f"delivered repo missing file declared in "
                            f"assembly_map.json: {deployed_rel} "
                            f"(expected at {target}) (Bug S3-113)"
                        ),
                    }
                )

    # --- Check 3: Python pyproject.toml validity ---
    if language == "python":
        pyproject = delivered / "pyproject.toml"
        if pyproject.is_file():
            try:
                try:
                    import tomllib
                except ImportError:
                    import tomli as tomllib  # type: ignore
                pp_data = tomllib.loads(pyproject.read_text())
            except Exception as e:
                findings.append(
                    {
                        "file": str(pyproject),
                        "line": 0,
                        "severity": "error",
                        "message": (
                            f"delivered pyproject.toml parse error: {e} "
                            f"(Bug S3-113)"
                        ),
                    }
                )
            else:
                build_system = pp_data.get("build-system", {})
                if not build_system:
                    findings.append(
                        {
                            "file": str(pyproject),
                            "line": 0,
                            "severity": "error",
                            "message": (
                                "delivered pyproject.toml missing "
                                "[build-system] table (Bug S3-113)"
                            ),
                        }
                    )
                else:
                    backend = build_system.get("build-backend")
                    if backend != "setuptools.build_meta":
                        findings.append(
                            {
                                "file": str(pyproject),
                                "line": 0,
                                "severity": "error",
                                "message": (
                                    f"delivered pyproject.toml "
                                    f"build-backend is {backend!r}, "
                                    f"expected 'setuptools.build_meta' "
                                    f"(Bug S3-113; see also Bug S3-109)"
                                ),
                            }
                        )

    return findings


# ---------------------------------------------------------------------------
# Plugin manifest generation
# ---------------------------------------------------------------------------


def generate_plugin_json(profile: Dict[str, Any]) -> str:
    """Generate a plugin.json manifest from profile data.

    Validates against full schema (Section 40.7.1): required fields
    name, description, version, author. Optional fields: mcpServers,
    lspServers, hooks (inline object only), outputStyles, tools.

    Auto-discovered directory fields (agents, commands, skills) are
    excluded — Claude Code discovers these by convention (Bug S3-43).

    Returns JSON string.
    """
    plugin_config = profile.get("plugin", {})

    manifest: Dict[str, Any] = {}

    # Required fields
    manifest["name"] = plugin_config.get("name", profile.get("name", ""))
    manifest["description"] = plugin_config.get(
        "description", profile.get("description", "")
    )
    manifest["version"] = plugin_config.get("version", profile.get("version", "0.1.0"))

    if not manifest.get("name") or not manifest.get("description"):
        raise ValueError("Plugin manifest required fields empty: name and description are required")

    # Author field -- can be string or object
    if "author" in plugin_config:
        manifest["author"] = plugin_config["author"]
    elif "author" in profile:
        manifest["author"] = profile["author"]
    else:
        license_info = profile.get("license", {})
        author_name = license_info.get("author", "") or license_info.get("holder", "")
        manifest["author"] = author_name

    # Optional fields - include if present in plugin config
    # Check using manifest key names directly (camelCase)
    # NOTE (Bug S3-43): agents, commands, skills are auto-discovered by
    # Claude Code from the plugin directory structure. Including them as
    # string paths causes the Zod schema validator to reject the manifest.
    # hooks is only valid as an inline object, not a string path.
    _AUTO_DISCOVERED = {"agents", "commands", "skills"}
    optional_keys = [
        "mcpServers",
        "lspServers",
        "hooks",
        "outputStyles",
        "tools",
    ]

    for key in optional_keys:
        value = plugin_config.get(key, profile.get(key))
        if value is None:
            continue
        # hooks must be an inline object, not a string path
        if key == "hooks" and isinstance(value, str):
            continue
        manifest[key] = value

    return json.dumps(manifest, indent=2)


def generate_marketplace_json(profile: Dict[str, Any]) -> str:
    """Generate a marketplace.json catalog from profile data.

    Required fields: name, owner (object with name), plugins array.
    Each plugin entry: name, source (relative path ./), description,
    version, author.

    Returns JSON string.
    """
    plugin_config = profile.get("plugin", {})
    license_info = profile.get("license", {})

    name = plugin_config.get("name", profile.get("name", ""))
    if not name:
        raise ValueError("Marketplace manifest 'name' field is empty")
    owner_name = (
        plugin_config.get("owner", "")
        or license_info.get("author", "")
        or license_info.get("holder", "")
    )

    # Get author value from plugin config
    author = plugin_config.get("author", owner_name)

    marketplace: Dict[str, Any] = {
        "name": name,
        "owner": {"name": owner_name} if isinstance(owner_name, str) else owner_name,
        "plugins": [
            {
                "name": name,
                "source": f"./{name}",
                "description": plugin_config.get(
                    "description", profile.get("description", "")
                ),
                "version": plugin_config.get(
                    "version", profile.get("version", "0.1.0")
                ),
                "author": author,
            }
        ],
    }

    return json.dumps(marketplace, indent=2)


# ---------------------------------------------------------------------------
# Structural check (AST-based)
# ---------------------------------------------------------------------------


def run_structural_check(
    target: Path,
    output_format: str = "text",
    strict: bool = False,
) -> List[Dict[str, Any]]:
    """Run four AST-based structural checks on a target directory or file.

    Checks:
    1. Dict registry keys never dispatched
    2. Enum values never matched
    3. Exported functions never called
    4. String dispatch gaps

    Uses only stdlib imports: ast, json, pathlib, argparse, sys.

    Returns list of finding dicts.
    """
    findings: List[Dict[str, Any]] = []

    # Collect Python files
    if target.is_file():
        py_files = [target] if target.suffix == ".py" else []
    elif target.is_dir():
        py_files = sorted(target.rglob("*.py"))
    else:
        return findings

    # Need at least 2 files for meaningful cross-file analysis
    # For single files, we only do checks that make sense in isolation

    # Parse all files into ASTs
    file_asts: Dict[str, ast.AST] = {}
    file_sources: Dict[str, str] = {}
    for py_file in py_files:
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
            file_asts[str(py_file)] = tree
            file_sources[str(py_file)] = source
        except (SyntaxError, OSError, UnicodeDecodeError):
            continue

    # Collect all module-level dict assignments (registries)
    # and all subscript accesses (dispatches)
    all_dict_keys: Dict[str, Dict[str, List[str]]] = {}
    all_subscript_names: Dict[str, set] = {}
    all_function_defs: Dict[str, set] = {}
    all_function_calls: set = set()
    all_string_constants: set = set()
    all_attribute_accesses: set = set()

    for filepath, tree in file_asts.items():
        file_func_defs: set = set()

        for node in ast.walk(tree):
            # Dict registry keys - module-level dict assignments
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and isinstance(node.value, ast.Dict):
                        dict_name = tgt.id
                        keys = []
                        for k in node.value.keys:
                            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                                keys.append(k.value)
                        if keys:
                            all_dict_keys.setdefault(filepath, {})[dict_name] = keys

            # Track subscript accesses
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Name):
                    dict_name = node.value.id
                    if isinstance(node.slice, ast.Constant) and isinstance(
                        node.slice.value, str
                    ):
                        all_subscript_names.setdefault(dict_name, set()).add(
                            node.slice.value
                        )

            # Function definitions (exported = module-level, not _prefixed)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    file_func_defs.add(node.name)

            # Track function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    all_function_calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    all_function_calls.add(node.func.attr)

            # Track string constants
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                all_string_constants.add(node.value)

            # Track attribute accesses
            if isinstance(node, ast.Attribute):
                all_attribute_accesses.add(node.attr)

        if file_func_defs:
            all_function_defs[filepath] = file_func_defs

    # Remove dict registry keys from string constants to avoid self-masking
    # (dict literal keys appear as string constants in the same file)
    for dicts in all_dict_keys.values():
        for keys in dicts.values():
            for key in keys:
                all_string_constants.discard(key)

    # Check 1: Dict registry keys never dispatched
    # Only check dicts that look like registries (UPPER_CASE names)
    for filepath, dicts in all_dict_keys.items():
        for dict_name, keys in dicts.items():
            if not dict_name.isupper() and not dict_name.endswith("_REGISTRY"):
                continue
            accessed = all_subscript_names.get(dict_name, set())
            for key in keys:
                if key not in accessed and key not in all_string_constants:
                    findings.append(
                        {
                            "check": "dict_key_never_dispatched",
                            "file": filepath,
                            "dict_name": dict_name,
                            "key": key,
                            "severity": "warning",
                            "message": (
                                f"Dict key '{key}' in {dict_name} is never dispatched"
                            ),
                        }
                    )

    # Check 2: Enum values never matched
    for filepath, tree in file_asts.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                is_enum = any(
                    (
                        isinstance(base, ast.Name)
                        and base.id in ("Enum", "IntEnum", "StrEnum")
                    )
                    or (
                        isinstance(base, ast.Attribute)
                        and base.attr in ("Enum", "IntEnum", "StrEnum")
                    )
                    for base in node.bases
                )
                if is_enum:
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for tgt in item.targets:
                                if isinstance(tgt, ast.Name):
                                    enum_val = tgt.id
                                    if (
                                        enum_val not in all_string_constants
                                        and enum_val not in all_attribute_accesses
                                    ):
                                        findings.append(
                                            {
                                                "check": "enum_value_never_matched",
                                                "file": filepath,
                                                "enum_class": node.name,
                                                "value": enum_val,
                                                "severity": "warning",
                                                "message": (
                                                    f"Enum value {node.name}.{enum_val} "
                                                    f"is never matched"
                                                ),
                                            }
                                        )

    # Check 3: Exported functions never called
    # Only meaningful with multiple files (cross-file analysis)
    if len(file_asts) > 1:
        for filepath, func_defs in all_function_defs.items():
            for func_name in func_defs:
                if func_name not in all_function_calls:
                    if func_name not in all_string_constants:
                        findings.append(
                            {
                                "check": "exported_function_never_called",
                                "file": filepath,
                                "function": func_name,
                                "severity": "warning",
                                "message": (
                                    f"Exported function '{func_name}' is never called"
                                ),
                            }
                        )

    # Check 4: String dispatch gaps
    for filepath, dicts in all_dict_keys.items():
        for dict_name, keys in dicts.items():
            if not dict_name.isupper():
                continue
            tree = file_asts[filepath]
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for tgt in node.targets:
                        if (
                            isinstance(tgt, ast.Name)
                            and tgt.id == dict_name
                            and isinstance(node.value, ast.Dict)
                        ):
                            for v in node.value.values:
                                if isinstance(v, ast.Constant) and isinstance(
                                    v.value, str
                                ):
                                    val = v.value
                                    if (
                                        val.isidentifier()
                                        and val not in all_function_calls
                                        and not any(
                                            val in defs
                                            for defs in all_function_defs.values()
                                        )
                                    ):
                                        is_dict_key = any(
                                            val in ks
                                            for dk in all_dict_keys.values()
                                            for ks in dk.values()
                                        )
                                        if not is_dict_key:
                                            findings.append(
                                                {
                                                    "check": "string_dispatch_gap",
                                                    "file": filepath,
                                                    "dict_name": dict_name,
                                                    "value": val,
                                                    "severity": "warning",
                                                    "message": (
                                                        f"String dispatch value '{val}' "
                                                        f"in {dict_name} does not resolve"
                                                    ),
                                                }
                                            )

    return findings


# ---------------------------------------------------------------------------
# Dispatch exhaustiveness validation
# ---------------------------------------------------------------------------


def validate_dispatch_exhaustiveness(
    language_registry: Dict[str, Dict[str, Any]],
    dispatch_tables: Dict[str, Dict[str, Any]],
) -> List[str]:
    """Verify that every full language has entries in all 6 dispatch tables
    and every component language has entries in its required_dispatch_entries
    tables.

    Uses correct keying strategy:
    - Language ID for assemblers, scanners, and signature parsers
    - Dispatch key for stub generators, test output parsers, quality runners

    When archetype is claude_code_plugin: additionally verifies plugin composite
    keys (plugin_markdown, plugin_bash, plugin_json) are present in
    STUB_GENERATORS, TEST_OUTPUT_PARSERS, and QUALITY_RUNNERS.

    Returns list of error strings (empty if valid).
    """
    errors: List[str] = []

    for lang_id, lang_config in language_registry.items():
        is_component = lang_config.get("is_component_only", False)

        if not is_component:
            # Full language: must have entries in all dispatch tables
            # Include both known tables and any caller-provided tables
            check_tables = _ALL_DISPATCH_TABLE_NAMES | set(dispatch_tables.keys())
            for table_name in check_tables:
                if dispatch_tables and table_name not in dispatch_tables:
                    continue
                table = dispatch_tables.get(table_name, {})

                if table_name in _ID_KEYED_TABLES:
                    # Keyed by language ID
                    if lang_id not in table:
                        errors.append(f"Language '{lang_id}' missing from {table_name}")
                else:
                    # Keyed by dispatch key from registry field; fall back to lang_id
                    key_field = _DISPATCH_KEY_FIELDS.get(table_name)
                    if key_field:
                        dispatch_key = lang_config.get(key_field, "")
                        check_key = dispatch_key if dispatch_key else lang_id
                    else:
                        check_key = lang_id
                    if check_key not in table:
                        errors.append(
                            f"Language '{lang_id}' missing from {table_name}"
                        )
        else:
            # Component language: entries only in required_dispatch_entries tables
            required_entries = lang_config.get("required_dispatch_entries", [])
            for entry_field in required_entries:
                table_name = _DISPATCH_ENTRY_TO_TABLE.get(entry_field)
                if table_name is None:
                    continue

                table = dispatch_tables.get(table_name, {})
                dispatch_key = lang_config.get(entry_field, "")
                check_key = dispatch_key if dispatch_key else lang_id

                if check_key not in table:
                    errors.append(
                        f"Component language '{lang_id}' missing from "
                        f"{table_name}"
                    )

    # Plugin composite key verification:
    # Only check if plugin keys are present (indicating plugin archetype build)
    has_any_plugin_key = any(
        composite_key in dispatch_tables.get(table_name, {})
        for table_name in _PLUGIN_COMPOSITE_TABLES
        for composite_key in _PLUGIN_COMPOSITE_KEYS
    )

    if has_any_plugin_key:
        for table_name in _PLUGIN_COMPOSITE_TABLES:
            table = dispatch_tables.get(table_name, {})
            for composite_key in _PLUGIN_COMPOSITE_KEYS:
                if composite_key not in table:
                    errors.append(
                        f"Plugin composite key '{composite_key}' missing from "
                        f"{table_name}"
                    )

    return errors


# ---------------------------------------------------------------------------
# Plugin manifest validation
# ---------------------------------------------------------------------------


def validate_plugin_manifest(manifest: Dict[str, Any]) -> List[str]:
    """Validate a plugin.json manifest against the full schema (Section 40.7.1).

    Validates all fields. Rejects string values for hooks (must be object
    if present). Warns about auto-discovered directory fields (agents,
    commands, skills) declared as strings (Bug S3-43).
    Returns list of error strings (empty if valid).
    """
    errors: List[str] = []

    # Check required fields
    for field in _PLUGIN_MANIFEST_REQUIRED:
        if field not in manifest:
            errors.append(f"Missing required field: {field}")

    # Validate field types for present fields
    if "name" in manifest:
        if not isinstance(manifest["name"], str):
            errors.append("Field 'name' must be a string")
        elif not manifest["name"]:
            errors.append("Field 'name' must not be empty")

    if "description" in manifest:
        if not isinstance(manifest["description"], str):
            errors.append("Field 'description' must be a string")

    if "version" in manifest:
        if not isinstance(manifest["version"], str):
            errors.append("Field 'version' must be a string")

    if "author" in manifest:
        author = manifest["author"]
        if isinstance(author, dict):
            if "name" not in author:
                errors.append("Field 'author' object must contain 'name'")
        elif not isinstance(author, str):
            errors.append("Field 'author' must be a string or object")

    # Validate optional field types (Bug S3-43)
    if "hooks" in manifest:
        if isinstance(manifest["hooks"], str):
            errors.append(
                "Field 'hooks' must be an object (inline hook definitions), "
                "not a string path. Claude Code auto-discovers hooks/hooks.json"
            )
        elif not isinstance(manifest["hooks"], dict):
            errors.append("Field 'hooks' must be an object")

    # Warn about auto-discovered directory fields declared as strings
    for field in ("agents", "commands", "skills"):
        if field in manifest and isinstance(manifest[field], str):
            errors.append(
                f"Field '{field}' should not be declared in plugin.json — "
                f"Claude Code auto-discovers the {field}/ directory"
            )

    # Check for unrecognized fields
    for key in manifest:
        if key not in _PLUGIN_MANIFEST_ALL:
            errors.append(f"Unrecognized field: {key}")

    return errors


# ---------------------------------------------------------------------------
# MCP config validation
# ---------------------------------------------------------------------------


def _check_env_var_syntax(obj: Any, context: str, errors: List[str]) -> None:
    """Recursively check env var ${...} syntax in all string values."""
    if isinstance(obj, str):
        # Find all ${...} references and validate
        for m in re.finditer(r"\$\{([^}]*)\}", obj):
            ref = m.group(1)
            # Valid: VAR_NAME, VAR_NAME:-default
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*(?::-.*)?$", ref):
                errors.append(f"{context}: invalid env var syntax '${{{ref}}}'")
        # Check for malformed ${... (unclosed braces)
        # Look for ${ not followed by } before end of string
        pos = 0
        while True:
            idx = obj.find("${", pos)
            if idx == -1:
                break
            closing = obj.find("}", idx + 2)
            if closing == -1:
                errors.append(f"{context}: unclosed env var reference")
                break
            pos = closing + 1
        # Check for bare $ followed by non-{ (invalid syntax)
        for m in re.finditer(r"\$([^{$])", obj):
            char = m.group(1)
            if char.isalpha() or char == "_":
                errors.append(
                    f"{context}: invalid env var syntax (use ${{...}} not $...)"
                )
    elif isinstance(obj, dict):
        for value in obj.values():
            _check_env_var_syntax(value, context, errors)
    elif isinstance(obj, list):
        for item in obj:
            _check_env_var_syntax(item, context, errors)


def validate_mcp_config(config: Dict[str, Any]) -> List[str]:
    """Validate MCP server configuration against Section 40.7.2 schema.

    Validates transport-specific required fields, valid transport types,
    env var ${...} syntax. Returns list of error strings.
    """
    errors: List[str] = []

    valid_transport_types = {"stdio", "http", "sse"}

    # Config can be {server_name: server_config, ...} or
    # {"mcpServers": {server_name: server_config, ...}}
    servers = config
    if "mcpServers" in config and isinstance(config["mcpServers"], dict):
        servers = config["mcpServers"]

    for server_name, server_config in servers.items():
        if server_name == "mcpServers":
            continue

        if not isinstance(server_config, dict):
            errors.append(f"Server '{server_name}': config must be an object")
            continue

        # Determine transport type (default depends on what fields are present)
        transport = server_config.get("type") or server_config.get("transport")
        if transport is None:
            # Infer transport from fields present
            if "url" in server_config:
                transport = "http"
            else:
                transport = "stdio"

        if transport not in valid_transport_types:
            errors.append(
                f"Server '{server_name}': invalid transport type '{transport}'"
            )
            continue

        # Transport-specific required fields
        if transport == "stdio":
            if "command" not in server_config:
                errors.append(
                    f"Server '{server_name}': stdio transport requires 'command'"
                )
        elif transport in ("http", "sse"):
            if "url" not in server_config:
                errors.append(
                    f"Server '{server_name}': {transport} transport requires 'url'"
                )

        # Validate env var ${...} syntax in all string values
        _check_env_var_syntax(server_config, f"Server '{server_name}'", errors)

    return errors


# ---------------------------------------------------------------------------
# LSP config validation
# ---------------------------------------------------------------------------


def validate_lsp_config(config: Dict[str, Any]) -> List[str]:
    """Validate LSP server configuration against Section 40.7.3 schema.

    Validates command required per entry, valid env var syntax.
    Returns list of error strings.
    """
    errors: List[str] = []

    # Config can be {lang_id: server_config, ...} or
    # {"lspServers": {lang_id: server_config, ...}}
    servers = config
    if "lspServers" in config and isinstance(config["lspServers"], dict):
        servers = config["lspServers"]

    for lang_id, server_config in servers.items():
        if lang_id == "lspServers":
            continue

        if not isinstance(server_config, dict):
            errors.append(f"LSP server '{lang_id}': config must be an object")
            continue

        # command is required
        if "command" not in server_config:
            errors.append(f"LSP server '{lang_id}': 'command' is required")

        # Validate env var syntax in all string values
        _check_env_var_syntax(server_config, f"LSP server '{lang_id}'", errors)

    return errors


# ---------------------------------------------------------------------------
# Skill frontmatter validation
# ---------------------------------------------------------------------------


def validate_skill_frontmatter(frontmatter: Dict[str, Any]) -> List[str]:
    """Validate skill YAML frontmatter against Section 40.7.4 schema.

    Validates fields from recognized set, allowed-tools valid,
    model values valid. Returns list of error strings.
    """
    errors: List[str] = []

    # Check for unrecognized fields
    for key in frontmatter:
        if key not in _SKILL_FRONTMATTER_FIELDS:
            errors.append(f"Unrecognized skill frontmatter field: {key}")

    # Validate allowed-tools
    if "allowed-tools" in frontmatter:
        tools_str = frontmatter["allowed-tools"]
        if isinstance(tools_str, str):
            tools = [t.strip() for t in tools_str.split(",") if t.strip()]
            for tool in tools:
                if tool not in _VALID_TOOL_NAMES:
                    errors.append(f"Invalid allowed-tools entry: {tool}")
        elif isinstance(tools_str, list):
            for tool in tools_str:
                if tool not in _VALID_TOOL_NAMES:
                    errors.append(f"Invalid allowed-tools entry: {tool}")

    # Validate model
    if "model" in frontmatter:
        model = frontmatter["model"]
        if isinstance(model, str) and model not in _VALID_MODEL_VALUES:
            errors.append(f"Invalid model value: {model}")

    # Validate effort
    if "effort" in frontmatter:
        effort = frontmatter["effort"]
        if isinstance(effort, str) and effort not in _VALID_EFFORT_VALUES:
            errors.append(f"Invalid effort value: {effort}")

    return errors


# ---------------------------------------------------------------------------
# Hook definitions validation
# ---------------------------------------------------------------------------


def validate_hook_definitions(hooks: Dict[str, Any]) -> List[str]:
    """Validate hook definitions against Section 40.7.5 schema.

    Validates 12-event set, valid hook types (command, http, prompt, agent),
    matcher regex. Returns list of error strings.
    """
    errors: List[str] = []

    # Hooks can have various structures:
    # {"hooks": {"EventName": [...]}} -- standard Section 40.7.5 format
    # {"EventName": [...]}} -- direct event mapping
    # {"EventName": {"hooks": [...]}} -- simplified per-event format
    hook_data = hooks
    if "hooks" in hooks and isinstance(hooks["hooks"], dict):
        hook_data = hooks["hooks"]

    for event_name, event_value in hook_data.items():
        if event_name == "hooks":
            continue

        # Validate event name against the recognized event set
        if event_name not in _VALID_HOOK_EVENTS:
            errors.append(f"Invalid hook event: {event_name}")

        # Handle different structures for the event value
        if isinstance(event_value, list):
            # Standard format: array of hook groups
            for i, hook_group in enumerate(event_value):
                _validate_hook_group(event_name, i, hook_group, errors)
        elif isinstance(event_value, dict):
            # Could be a single hook group or a dict with "hooks" key
            if "hooks" in event_value:
                inner_hooks = event_value["hooks"]
                if isinstance(inner_hooks, list):
                    for j, hook in enumerate(inner_hooks):
                        _validate_single_hook(event_name, 0, j, hook, errors)
                elif isinstance(inner_hooks, dict):
                    # Single hook as a dict
                    _validate_single_hook(event_name, 0, 0, inner_hooks, errors)
            elif "type" in event_value:
                # Direct single hook definition
                _validate_single_hook(event_name, 0, 0, event_value, errors)
            else:
                # Treat as a hook group with optional matcher
                _validate_hook_group(event_name, 0, event_value, errors)

    return errors


def _validate_hook_group(
    event_name: str, index: int, hook_group: Any, errors: List[str]
) -> None:
    """Validate a hook group entry."""
    if not isinstance(hook_group, dict):
        errors.append(f"Event '{event_name}' entry {index}: must be an object")
        return

    # Validate matcher (optional, only for tool events)
    if "matcher" in hook_group:
        matcher = hook_group["matcher"]
        if isinstance(matcher, str):
            try:
                re.compile(matcher)
            except re.error as e:
                errors.append(
                    f"Event '{event_name}' entry {index}: invalid matcher regex: {e}"
                )

    # Validate inner hooks array
    inner_hooks = hook_group.get("hooks", [])
    if isinstance(inner_hooks, list):
        for j, hook in enumerate(inner_hooks):
            _validate_single_hook(event_name, index, j, hook, errors)
    elif isinstance(inner_hooks, dict):
        _validate_single_hook(event_name, index, 0, inner_hooks, errors)


def _validate_single_hook(
    event_name: str, group_index: int, hook_index: int, hook: Any, errors: List[str]
) -> None:
    """Validate a single hook definition."""
    if not isinstance(hook, dict):
        errors.append(
            f"Event '{event_name}' entry {group_index} hook {hook_index}: "
            f"must be an object"
        )
        return

    hook_type = hook.get("type")
    if hook_type is None:
        errors.append(
            f"Event '{event_name}' entry {group_index} hook {hook_index}: "
            f"missing 'type'"
        )
    elif hook_type not in _VALID_HOOK_TYPES:
        errors.append(
            f"Event '{event_name}' entry {group_index} hook {hook_index}: "
            f"invalid hook type '{hook_type}'"
        )

    # Validate matcher regex if present
    if "matcher" in hook:
        matcher = hook["matcher"]
        if isinstance(matcher, str):
            try:
                re.compile(matcher)
            except re.error as e:
                errors.append(
                    f"Event '{event_name}' entry {group_index} hook {hook_index}: "
                    f"invalid matcher regex: {e}"
                )


# ---------------------------------------------------------------------------
# Agent frontmatter validation
# ---------------------------------------------------------------------------


def validate_agent_frontmatter(frontmatter: Dict[str, Any]) -> List[str]:
    """Validate agent definition YAML frontmatter against Section 40.7.6 schema.

    Validates fields from recognized set, disallowedTools valid,
    referenced skills exist. Returns list of error strings.
    """
    errors: List[str] = []

    # Check for unrecognized fields
    for key in frontmatter:
        if key not in _AGENT_FRONTMATTER_FIELDS:
            errors.append(f"Unrecognized agent frontmatter field: {key}")

    # Validate disallowedTools
    if "disallowedTools" in frontmatter:
        tools = frontmatter["disallowedTools"]
        if isinstance(tools, str):
            tool_list = [t.strip() for t in tools.split(",") if t.strip()]
        elif isinstance(tools, list):
            tool_list = tools
        else:
            tool_list = []
            errors.append("Field 'disallowedTools' must be a string or array")

        for tool in tool_list:
            if tool not in _VALID_TOOL_NAMES:
                errors.append(f"Invalid disallowedTools entry: {tool}")

    # Validate model
    if "model" in frontmatter:
        model = frontmatter["model"]
        if isinstance(model, str) and model not in _VALID_MODEL_VALUES:
            errors.append(f"Invalid model value: {model}")

    # Validate effort
    if "effort" in frontmatter:
        effort = frontmatter["effort"]
        if isinstance(effort, str) and effort not in _VALID_EFFORT_VALUES:
            errors.append(f"Invalid effort value: {effort}")

    return errors


# ---------------------------------------------------------------------------
# Cross-reference integrity
# ---------------------------------------------------------------------------


def check_cross_reference_integrity(
    plugin_dir: Path,
) -> List[str]:
    """Validate cross-reference integrity within a plugin directory.

    Checks:
    - Skills referenced in agent definitions exist in skills/
    - MCP server references in hooks resolve to declared servers
    - Command references in manifest resolve to existing command files

    Returns list of error strings.
    """
    errors: List[str] = []

    # Load plugin manifest
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    if not manifest_path.exists():
        manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.exists():
        return errors

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        errors.append("Failed to parse plugin.json")
        return errors

    # Collect available skills
    skills_dir = plugin_dir / "skills"
    available_skills: set = set()
    if skills_dir.exists():
        for skill_file in skills_dir.rglob("SKILL.md"):
            available_skills.add(skill_file.parent.name)
        for skill_file in skills_dir.rglob("*.md"):
            available_skills.add(skill_file.stem)

    # Collect available commands
    commands_dir = plugin_dir / "commands"
    available_commands: set = set()
    if commands_dir.exists():
        for cmd_file in commands_dir.rglob("*.md"):
            available_commands.add(cmd_file.stem)
            available_commands.add(cmd_file.name)

    # Collect declared MCP servers
    declared_servers: set = set()
    mcp_servers = manifest.get("mcpServers")
    if isinstance(mcp_servers, dict):
        declared_servers.update(mcp_servers.keys())
    elif isinstance(mcp_servers, str):
        mcp_path = plugin_dir / mcp_servers
        if mcp_path.exists():
            try:
                mcp_data = json.loads(mcp_path.read_text(encoding="utf-8"))
                if isinstance(mcp_data, dict):
                    if "mcpServers" in mcp_data:
                        declared_servers.update(mcp_data["mcpServers"].keys())
                    else:
                        declared_servers.update(mcp_data.keys())
            except (json.JSONDecodeError, OSError):
                pass

    # Check skill references in agent definitions
    agents_dir = plugin_dir / "agents"
    if agents_dir.exists():
        for agent_file in agents_dir.rglob("*.md"):
            try:
                content = agent_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            frontmatter = _parse_yaml_frontmatter(content)
            if frontmatter and "skills" in frontmatter:
                skills_refs = frontmatter["skills"]
                if isinstance(skills_refs, list):
                    for skill_ref in skills_refs:
                        if (
                            isinstance(skill_ref, str)
                            and skill_ref not in available_skills
                        ):
                            errors.append(
                                f"Agent '{agent_file.name}' references skill "
                                f"'{skill_ref}' which does not exist in skills/"
                            )

    # Check hook references to MCP servers
    hooks_data = manifest.get("hooks")
    if isinstance(hooks_data, str):
        hooks_path = plugin_dir / hooks_data
        if hooks_path.exists():
            try:
                hooks_data = json.loads(hooks_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                hooks_data = None

    if isinstance(hooks_data, dict):
        hook_events = hooks_data.get("hooks", hooks_data)
        if isinstance(hook_events, dict):
            for _event, entries in hook_events.items():
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if isinstance(entry, dict):
                        for hook in entry.get("hooks", []):
                            if isinstance(hook, dict):
                                mcp_ref = hook.get("mcp_server")
                                if (
                                    mcp_ref
                                    and declared_servers
                                    and mcp_ref not in declared_servers
                                ):
                                    errors.append(
                                        f"Hook references MCP server "
                                        f"'{mcp_ref}' which is not declared"
                                    )

    # Check command references in manifest
    commands = manifest.get("commands")
    if isinstance(commands, list):
        for cmd in commands:
            if isinstance(cmd, str) and available_commands:
                cmd_name = Path(cmd).stem
                if cmd_name not in available_commands and cmd not in available_commands:
                    errors.append(
                        f"Manifest references command '{cmd}' which does not exist"
                    )
    elif isinstance(commands, str) and commands:
        cmd_dir = plugin_dir / commands
        if not cmd_dir.exists():
            errors.append(
                f"Manifest references commands directory '{commands}' which "
                f"does not exist"
            )

    return errors


def _parse_yaml_frontmatter(content: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from markdown content.

    Looks for content between --- delimiters at the start of the file.
    Returns parsed dict or empty dict if no frontmatter found.
    """
    lines = content.strip().splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx < 0:
        return {}

    yaml_lines = lines[1:end_idx]
    result: Dict[str, Any] = {}

    for line in yaml_lines:
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()

            if value.lower() == "true":
                result[key] = True
            elif value.lower() == "false":
                result[key] = False
            elif value.startswith("[") and value.endswith("]"):
                items = value[1:-1].split(",")
                result[key] = [
                    item.strip().strip('"').strip("'") for item in items if item.strip()
                ]
            elif value.isdigit():
                result[key] = int(value)
            elif value.startswith('"') and value.endswith('"'):
                result[key] = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                result[key] = value[1:-1]
            else:
                result[key] = value if value else None

    return result


# ---------------------------------------------------------------------------
# Blueprint contract audit (Bug S3-158)
#
# Mechanical gate enforced by Unit 14's dispatch_agent_status when
# blueprint_author emits BLUEPRINT_DRAFT_COMPLETE / BLUEPRINT_REVISION_COMPLETE.
# Three checks:
#   (a) DAG acyclicity on Dependencies edges between Units.
#   (c) Tier 2 signature implementation existence in src/unit_<N>/stub.py.
#   (d) Phantom call detection — flagged calls whose target is NOT in any
#       Tier 2 signature set and is not a known stdlib/builtin name.
#
# Findings whose `description` text matches a non-comment, non-empty line in
# `<project_root>/.svp/audit_known_false_positives.md` are filtered out.
# Reciprocity check (b) is intentionally deferred (separate cycle).
# ---------------------------------------------------------------------------


# Lowercase identifier names that are commonly called from stubs but are NOT
# contract functions (stdlib, builtins, third-party). Phantom-call check
# excludes anything in this allow-list. Conservative — false positives in the
# phantom check are worse than false negatives.
_PHANTOM_CALL_ALLOWLIST = {
    # Built-ins
    "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
    "callable", "chr", "classmethod", "compile", "complex", "delattr", "dict",
    "dir", "divmod", "enumerate", "eval", "exec", "exit", "filter", "float",
    "format", "frozenset", "getattr", "globals", "hasattr", "hash", "help",
    "hex", "id", "input", "int", "isinstance", "issubclass", "iter", "len",
    "list", "locals", "map", "max", "memoryview", "min", "next", "object",
    "oct", "open", "ord", "pow", "print", "property", "range", "repr",
    "reversed", "round", "set", "setattr", "slice", "sorted", "staticmethod",
    "str", "sum", "super", "tuple", "type", "vars", "zip", "breakpoint",
    "quit",
    # Common stdlib
    "Path", "PurePath", "PurePosixPath", "PureWindowsPath",
    "datetime", "date", "time", "timedelta",
    "deepcopy", "copy",
    "loads", "dumps", "load", "dump",
    "compile_pattern", "match", "search", "sub", "split", "findall",
    "fullmatch", "finditer", "escape",
    "sleep", "system", "getenv", "environ", "getcwd", "chdir",
    "exists", "is_file", "is_dir", "mkdir", "rmdir", "unlink", "touch",
    "read_text", "write_text", "read_bytes", "write_bytes",
    "rglob", "glob", "iterdir", "resolve", "absolute", "relative_to",
    "with_suffix", "with_name", "joinpath",
    "join", "exists", "abspath", "basename", "dirname", "splitext",
    "expanduser", "split",
    "run", "Popen", "PIPE", "DEVNULL", "STDOUT", "check_call",
    "check_output", "call",
    "warn", "warns",
    "parse", "walk", "iter_child_nodes", "fix_missing_locations",
    "namedtuple", "field", "fields", "is_dataclass", "asdict", "astuple",
    "defaultdict", "OrderedDict", "Counter", "ChainMap", "deque",
    "ArgumentParser", "ArgumentTypeError",
    "main", "setup", "teardown",
    "info", "debug", "warning", "error", "critical", "log",
    "fixture", "mark", "param", "raises", "skip", "xfail", "fail",
    "monkeypatch",
    # AST nodes used as constructors
    "Name", "Attribute", "Call", "Constant", "Subscript", "Assign", "Dict",
    "List", "Tuple", "FunctionDef", "AsyncFunctionDef", "ClassDef", "Module",
    "Import", "ImportFrom", "Return", "If", "For", "While", "With", "Try",
    "Expr", "Raise", "Pass", "Break", "Continue", "Lambda", "BinOp",
    "BoolOp", "UnaryOp", "Compare", "IfExp", "Starred", "Slice", "Index",
    "alias", "arg", "arguments", "keyword", "comprehension",
    # Misc commonly called but not contract functions
    "format_unit_heading_violations", "validate_unit_heading_format",
    "save_state", "load_state", "load_config", "save_config",
    "load_profile", "save_profile",
    "encode", "decode", "strip", "rstrip", "lstrip", "lower", "upper",
    "title", "capitalize", "startswith", "endswith", "replace", "splitlines",
    "join", "zfill", "rjust", "ljust", "center", "count", "index", "find",
    "isidentifier", "isdigit", "isalpha", "isalnum", "isspace", "isupper",
    "islower",
    "items", "keys", "values", "get", "setdefault", "update", "pop",
    "popitem", "clear", "copy", "fromkeys",
    "append", "extend", "insert", "remove", "reverse", "sort",
    "add", "discard", "intersection", "union", "difference",
    "symmetric_difference", "issubset", "issuperset",
    # noqa: E501
}


def _parse_blueprint_units(blueprint_text: str) -> Dict[int, Dict[str, Any]]:
    """Parse blueprint markdown into a dict keyed by unit number.

    Each entry has:
      - "name": the unit heading title (after "Unit N:" or "Unit N -")
      - "deps": list of int unit numbers from the Dependencies line
      - "tier2_signatures": list of function names declared in Tier 2
      - "calls_block": list of non-empty content lines under the unit's
        `## Calls` heading (used by S3-172 audit; empty if absent)
    Empty/missing fields default to safe values.
    """
    units: Dict[int, Dict[str, Any]] = {}
    lines = blueprint_text.splitlines()

    # Heading regex — accept "## Unit N:" or "## Unit N —" or "## Unit N -"
    heading_re = re.compile(r"^##\s+Unit\s+(\d+)\s*[:—\-]\s*(.*?)\s*$")
    deps_re = re.compile(r"^\*\*Dependencies:\*\*\s*(.+)$")
    tier2_re = re.compile(r"^###\s+Tier\s*2", re.IGNORECASE)
    tier3_re = re.compile(r"^###\s+Tier\s*3", re.IGNORECASE)
    next_section_re = re.compile(r"^##\s+|^---\s*$")
    sig_re = re.compile(r"^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")
    # `## Calls` heading regex (S3-172). The `##` heading lives inside a
    # unit body (not a top-level unit heading) and signals the start of
    # the Calls block.
    calls_heading_re = re.compile(r"^##\s+Calls\s*$", re.IGNORECASE)

    # First pass: locate unit headings and their slice range.
    unit_starts: List[tuple] = []  # (unit_num, name, start_line)
    for i, line in enumerate(lines):
        m = heading_re.match(line)
        if m:
            try:
                num = int(m.group(1))
            except ValueError:
                continue
            unit_starts.append((num, m.group(2).strip(), i))

    # Determine ranges
    for idx, (num, name, start) in enumerate(unit_starts):
        end = unit_starts[idx + 1][2] if idx + 1 < len(unit_starts) else len(lines)
        body = lines[start:end]

        # Dependencies
        deps: List[int] = []
        for ln in body:
            dm = deps_re.match(ln.strip())
            if dm:
                rhs = dm.group(1)
                # strip trailing period and whitespace
                rhs = rhs.strip().rstrip(".")
                # "None (root unit)" or just "None"
                if rhs.lower().startswith("none"):
                    deps = []
                else:
                    for token in rhs.split(","):
                        m2 = re.search(r"Unit\s+(\d+)", token)
                        if m2:
                            try:
                                deps.append(int(m2.group(1)))
                            except ValueError:
                                pass
                break

        # Tier 2 signatures: scan from a Tier 2 header line until the next ###
        # Tier 3 header or next ## section. Collect `def NAME(` matches.
        tier2_sigs: List[str] = []
        in_tier2 = False
        for ln in body:
            if tier2_re.match(ln):
                in_tier2 = True
                continue
            if in_tier2 and tier3_re.match(ln):
                in_tier2 = False
                continue
            if in_tier2 and next_section_re.match(ln) and not ln.startswith("###"):
                in_tier2 = False
                continue
            if in_tier2:
                sm = sig_re.match(ln)
                if sm:
                    tier2_sigs.append(sm.group(1))

        # Calls block (S3-172): scan for `## Calls` heading; collect
        # non-empty content lines until the next `##`/`###` heading or
        # the `**Dependencies:**` line (which terminates the block).
        calls_block: List[str] = []
        in_calls = False
        for ln in body:
            if calls_heading_re.match(ln):
                in_calls = True
                continue
            if in_calls:
                stripped = ln.strip()
                # Terminators: another section heading, the dependencies
                # marker, or a horizontal rule.
                if (
                    ln.startswith("##")
                    or ln.startswith("###")
                    or stripped.startswith("**Dependencies:**")
                    or stripped == "---"
                ):
                    in_calls = False
                    continue
                if not stripped:
                    continue
                calls_block.append(ln)

        units[num] = {
            "name": name,
            "deps": deps,
            "tier2_signatures": tier2_sigs,
            "calls_block": calls_block,
        }

    return units


def _detect_dependency_cycles(
    units: Dict[int, Dict[str, Any]],
) -> List[List[int]]:
    """Detect cycles via DFS on the dependency graph (U -> deps).

    Returns a list of cycles, where each cycle is a list of unit numbers
    in traversal order (the first node repeats at the start, not the end).
    """
    cycles: List[List[int]] = []
    color: Dict[int, int] = {n: 0 for n in units}  # 0=white,1=gray,2=black
    parent: Dict[int, int] = {}

    def dfs(n: int, stack: List[int]) -> None:
        color[n] = 1
        stack.append(n)
        for d in units.get(n, {}).get("deps", []):
            if d not in color:
                # Dependency on undefined unit — skip cycle detection but
                # don't crash. A separate check could flag this later.
                continue
            if color[d] == 0:
                parent[d] = n
                dfs(d, stack)
            elif color[d] == 1:
                # Found a back edge — extract the cycle.
                if d in stack:
                    idx = stack.index(d)
                    cycle = stack[idx:] + [d]
                    cycles.append(cycle)
        stack.pop()
        color[n] = 2

    for n in sorted(units):
        if color[n] == 0:
            dfs(n, [])

    return cycles


def _read_known_false_positives(project_root: Path) -> List[str]:
    """Return list of false-positive description strings to filter out.

    Reads `<project_root>/.svp/audit_known_false_positives.md`. Lines
    starting with `#` are comments; blank lines are ignored. Returns
    the remaining lines stripped.
    """
    fp_path = project_root / ".svp" / "audit_known_false_positives.md"
    if not fp_path.exists():
        return []
    try:
        text = fp_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    out: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        out.append(stripped)
    return out


def _collect_stub_function_calls(
    stub_path: Path,
) -> tuple:
    """Parse a stub file with AST. Returns (defined_names, called_names)."""
    defined: set = set()
    called: set = set()
    try:
        src = stub_path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(stub_path))
    except (SyntaxError, OSError, UnicodeDecodeError):
        return defined, called

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined.add(node.name)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            # Skip ast.Attribute calls — those are method/module attribute
            # calls (json.loads, x.append, etc.) and would generate too many
            # false positives. The conservative approach is to only flag
            # bare-name calls.

    return defined, called


# ---------------------------------------------------------------------------
# Bug S3-172: Calls block parsing + per-function resolution check
# ---------------------------------------------------------------------------


def _extract_calls_citations(
    units: Dict[int, Dict[str, Any]],
) -> List[Tuple[int, str, int, bool]]:
    """Parse each unit's `## Calls` block into citation tuples.

    Returns a list of `(citing_unit, function_name, target_unit, is_private_helper)`
    tuples. Skips leaf-unit blocks (`None (leaf unit).`).

    The Calls block format is:

        ## Calls

        - function_name() in Unit N
        - _private_helper() in Unit N (private helper)
        - another_function() in Unit M

    or for leaf units:

        ## Calls

        None (leaf unit).

    Bug S3-172 — final cycle of the Calls/Called-by encoding sub-project.
    Consumes cycle-1 (S3-170) format mandate + cycle-2 (S3-171) migration data.
    """
    citations: List[Tuple[int, str, int, bool]] = []

    # We need the raw blueprint text to slice each unit's Calls block. The
    # `units` dict was built by `_parse_blueprint_units` which holds the unit
    # heading line ranges implicitly. To stay self-contained, re-parse the
    # blueprint text from scratch using the same heading regex. The caller
    # passes us the original text via the units dict's raw lines if present,
    # else we fall back to scanning each unit's stored "raw_lines" key. To
    # keep this helper decoupled, we instead consume `units[N]["calls_block"]`
    # (a list of citation lines) populated by `_parse_blueprint_units`. If
    # absent (legacy callers / cached parses), we return an empty list.
    citation_re = re.compile(
        r"^\s*-\s+([a-zA-Z_][a-zA-Z0-9_]*)\(\)\s+in\s+Unit\s+(\d+)"
        r"(?:\s+\(private\s+helper\))?\s*$"
    )
    leaf_re = re.compile(r"^\s*None\s+\(leaf\s+unit\)\.?\s*$")

    for unit_num in sorted(units):
        info = units[unit_num]
        block_lines = info.get("calls_block", [])
        if not block_lines:
            continue
        # Skip leaf-unit blocks entirely (no citations to emit).
        if any(leaf_re.match(ln) for ln in block_lines):
            continue
        for ln in block_lines:
            m = citation_re.match(ln)
            if not m:
                continue
            fn_name = m.group(1)
            try:
                target_unit = int(m.group(2))
            except ValueError:
                continue
            is_private = "(private helper)" in ln
            citations.append((unit_num, fn_name, target_unit, is_private))

    return citations


def _extract_tier2_function_names(
    units: Dict[int, Dict[str, Any]],
) -> Dict[int, Set[str]]:
    """Return per-unit set of function names defined in Tier-2 signatures.

    Reuses the existing `units[N]["tier2_signatures"]` data populated by
    `_parse_blueprint_units()`. Each entry in `tier2_signatures` is already
    a function name string (parsed via `^\\s*def\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\(`).

    Bug S3-172.
    """
    out: Dict[int, Set[str]] = {}
    for unit_num, info in units.items():
        out[unit_num] = set(info.get("tier2_signatures", []) or [])
    return out


def _compute_called_by_graph(
    citations: List[Tuple[int, str, int, bool]],
) -> Dict[int, Set[Tuple[int, str]]]:
    """Invert the Calls graph for any consumer that needs the reverse map.

    Returns dict keyed by `target_unit`, with value a set of
    `(citing_unit, function_name)` pairs. Computed on-demand within
    `audit_blueprint_contracts()`; not materialized to disk (per Q2 design
    lock — the `## Called-by` section is NOT authored).

    Bug S3-172.
    """
    out: Dict[int, Set[Tuple[int, str]]] = {}
    for citing_unit, fn_name, target_unit, _is_private in citations:
        out.setdefault(target_unit, set()).add((citing_unit, fn_name))
    return out


def audit_blueprint_contracts(
    project_root: Path,
) -> List[Dict[str, Any]]:
    """Mechanical audit of blueprint_contracts.md (Bug S3-158).

    Returns a list of violation dicts. Each dict has keys:
      - "check": one of "dag", "reachability", "phantom_call",
        "blueprint_missing"
      - "severity": "error" or "warning"
      - "location": unit name or file path
      - "description": 1-line human-readable string

    Empty list means audit passed. Findings whose `description` matches
    any non-comment, non-empty line in
    `<project_root>/.svp/audit_known_false_positives.md` are filtered out.
    """
    project_root = Path(project_root)
    violations: List[Dict[str, Any]] = []

    # Canonical workspace location is blueprint/blueprint_contracts.md.
    # In the deployed/repo layout, sync_workspace.sh mirrors the file to
    # docs/blueprint_contracts.md instead. Try both so the audit works
    # from either layout (workspace or repo).
    blueprint_path = project_root / "blueprint" / "blueprint_contracts.md"
    if not blueprint_path.exists():
        fallback_path = project_root / "docs" / "blueprint_contracts.md"
        if fallback_path.exists():
            blueprint_path = fallback_path
        else:
            return [
                {
                    "check": "blueprint_missing",
                    "severity": "error",
                    "location": str(blueprint_path),
                    "description": (
                        f"blueprint/blueprint_contracts.md not found at "
                        f"{blueprint_path}"
                    ),
                }
            ]

    try:
        blueprint_text = blueprint_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [
            {
                "check": "blueprint_missing",
                "severity": "error",
                "location": str(blueprint_path),
                "description": (
                    f"Could not read blueprint_contracts.md: {exc}"
                ),
            }
        ]

    units = _parse_blueprint_units(blueprint_text)

    # Check (a): DAG acyclicity on Dependencies edges
    cycles = _detect_dependency_cycles(units)
    for cycle in cycles:
        chain = " -> ".join(f"Unit {n}" for n in cycle)
        violations.append(
            {
                "check": "dag",
                "severity": "error",
                "location": ", ".join(f"Unit {n}" for n in cycle if n is not None),
                "description": (
                    f"Dependency cycle detected: {chain}"
                ),
            }
        )

    # Check (c): Tier 2 signature implementation existence
    # Build a global Tier-2 name -> owning unit map for use in check (d) too
    tier2_owners: Dict[str, int] = {}
    for unit_num, info in units.items():
        for sig in info.get("tier2_signatures", []):
            # First-declarer wins (multiple units shouldn't declare the
            # same signature; if they do, that's a separate issue).
            tier2_owners.setdefault(sig, unit_num)

        stub_path = project_root / f"src/unit_{unit_num}/stub.py"
        if not stub_path.exists():
            # Skip per-function checks; emit a single warning per missing
            # stub file instead.
            if info.get("tier2_signatures"):
                violations.append(
                    {
                        "check": "reachability",
                        "severity": "warning",
                        "location": f"Unit {unit_num}",
                        "description": (
                            f"Unit {unit_num} stub file not found at "
                            f"{stub_path}; skipping Tier 2 implementation "
                            f"check for {len(info['tier2_signatures'])} "
                            f"declared signature(s)"
                        ),
                    }
                )
            continue

        defined, _called = _collect_stub_function_calls(stub_path)
        for sig in info.get("tier2_signatures", []):
            if sig not in defined:
                violations.append(
                    {
                        "check": "reachability",
                        "severity": "error",
                        "location": f"Unit {unit_num}",
                        "description": (
                            f"Tier 2 signature '{sig}' declared in Unit "
                            f"{unit_num} but not implemented in {stub_path}"
                        ),
                    }
                )

    # Check (d): Phantom call detection
    # Build set of all Tier 2 names across all units.
    tier2_names = set(tier2_owners.keys())

    # Snake_case heuristic: only consider calls whose name is multi-word
    # snake_case (contains an underscore between two letters/digits) AND
    # is NOT in the allow-list AND is NOT in tier2_names. This is
    # conservative — single-word lowercase names are treated as likely
    # stdlib/builtin and skipped. Underscored names are far more likely
    # to be project-specific contract functions.
    snake_re = re.compile(r"^[a-z][a-z0-9_]*_[a-z0-9_]+$")

    for unit_num, info in units.items():
        stub_path = project_root / f"src/unit_{unit_num}/stub.py"
        if not stub_path.exists():
            continue
        _defined, called = _collect_stub_function_calls(stub_path)
        for name in sorted(called):
            if name in _PHANTOM_CALL_ALLOWLIST:
                continue
            if not snake_re.match(name):
                continue
            if name in tier2_names:
                continue
            # Also exclude names defined locally in this same stub file
            # (private helpers) — they are valid implementations even if
            # not in any Tier 2 declaration.
            if name in _defined:
                continue
            # Allow names defined in OTHER unit stubs (private cross-unit
            # helpers). To stay conservative, we only flag if no unit stub
            # defines this name as a function. We don't re-scan all stubs
            # here for performance; if the name doesn't look like a
            # contract function (no Tier 2 declaration), warn rather than
            # error.
            violations.append(
                {
                    "check": "phantom_call",
                    "severity": "warning",
                    "location": f"Unit {unit_num} ({stub_path})",
                    "description": (
                        f"Unit {unit_num} stub calls '{name}()' but no "
                        f"Tier 2 signature declares it"
                    ),
                }
            )

    # Check (S3-172): per-function Calls resolution. Every citation in a
    # Unit's `## Calls` block must resolve to a declared function in the
    # target Unit's Tier-2 signatures. Closes IMPROV-09 deferred check (b).
    citations = _extract_calls_citations(units)
    tier2_names = _extract_tier2_function_names(units)
    # Compute the inverse graph for any future downstream consumer; not
    # materialized to disk per Q2 design lock.
    _called_by = _compute_called_by_graph(citations)  # noqa: F841
    for citing_unit, fn_name, target_unit, _is_private in citations:
        if (
            target_unit not in tier2_names
            or fn_name not in tier2_names[target_unit]
        ):
            violations.append(
                {
                    "check": "calls_resolution",
                    "severity": "error",
                    "location": f"Unit {citing_unit} Calls",
                    "description": (
                        f"Unit {citing_unit} cites {fn_name}() in Unit "
                        f"{target_unit}, but Unit {target_unit}'s Tier-2 "
                        f"has no function named {fn_name}"
                    ),
                }
            )

    # Filter against known false positives
    fps = _read_known_false_positives(project_root)
    if fps:
        filtered: List[Dict[str, Any]] = []
        for v in violations:
            desc = v.get("description", "")
            if any(fp in desc or desc == fp for fp in fps):
                continue
            filtered.append(v)
        violations = filtered

    return violations


def format_audit_violations(violations: List[Dict[str, Any]]) -> str:
    """Format an audit violation list into a human-readable error string.

    Suitable for raising as a ValueError message or printing to stderr.
    """
    if not violations:
        return "Blueprint contract audit passed."

    lines: List[str] = [
        f"Blueprint contract audit found {len(violations)} violation(s) "
        f"(Bug S3-158):",
        "",
    ]
    by_check: Dict[str, List[Dict[str, Any]]] = {}
    for v in violations:
        by_check.setdefault(v.get("check", "?"), []).append(v)

    for check_name in sorted(by_check):
        items = by_check[check_name]
        lines.append(f"  [{check_name}] ({len(items)}):")
        for v in items:
            sev = v.get("severity", "?")
            loc = v.get("location", "?")
            desc = v.get("description", "?")
            lines.append(f"    - ({sev}) {loc}: {desc}")
        lines.append("")

    lines.append(
        "If a finding is a known false positive, add its description text "
        "as a line in .svp/audit_known_false_positives.md and re-run."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Compliance scan CLI
# ---------------------------------------------------------------------------


def compliance_scan_main(argv: list = None) -> None:
    """CLI entry point for compliance scanning.

    Arguments:
    --project-root (path)
    --src-dir (path: source directory to scan)
    --tests-dir (path: tests directory to scan)
    --format (str: "json" or "text")
    --strict (flag)
    """
    parser = argparse.ArgumentParser(description="SVP compliance scanner")
    parser.add_argument(
        "--project-root",
        type=Path,
        required=True,
        help="Project root directory",
    )
    parser.add_argument(
        "--src-dir",
        type=Path,
        required=True,
        help="Source directory to scan",
    )
    parser.add_argument(
        "--tests-dir",
        type=Path,
        required=True,
        help="Tests directory to scan",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="text",
        choices=["json", "text"],
        help="Output format",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: non-zero exit on findings",
    )

    args = parser.parse_args(argv)

    # Load profile to determine language and environment
    from profile_schema import load_profile

    profile = load_profile(args.project_root)
    primary_language = profile.get("language", {}).get("primary", "python")

    # Get language config
    from language_registry import LANGUAGE_REGISTRY

    lang_config = LANGUAGE_REGISTRY.get(primary_language, {})

    # Run the appropriate scanner
    scanner = COMPLIANCE_SCANNERS.get(primary_language)
    if scanner is None:
        if args.format == "json":
            print(json.dumps([]))
        else:
            print("No compliance scanner available for language: " + primary_language)
        return

    findings = scanner(args.src_dir, args.tests_dir, lang_config, {})

    # Bug S3-97: Dual compliance scan for mixed archetype
    archetype = profile.get("archetype", "")
    if archetype == "mixed":
        secondary_language = profile.get("language", {}).get("secondary")
        if secondary_language:
            secondary_scanner = COMPLIANCE_SCANNERS.get(secondary_language)
            if secondary_scanner:
                secondary_src_dir = args.project_root / secondary_language
                secondary_tests_dir = args.project_root / secondary_language / "tests"
                secondary_lang_config = LANGUAGE_REGISTRY.get(secondary_language, {})
                secondary_findings = secondary_scanner(
                    secondary_src_dir, secondary_tests_dir, secondary_lang_config, {}
                )
                findings.extend(secondary_findings)

    # Bug S3-113: Delivered repo content validation. Runs after language-
    # specific scanners (including the mixed dual scan). Silently returns []
    # when state.delivered_repo_path is unset or missing on disk, so this
    # is safe for dev-mode source-tree-only scans too.
    delivered_findings = validate_delivered_repo_contents(args.project_root)
    findings.extend(delivered_findings)

    # Output results
    if args.format == "json":
        print(json.dumps(findings, indent=2))
    else:
        if not findings:
            print("No compliance violations found.")
        else:
            for finding in findings:
                print(
                    f"{finding.get('file', '?')}:{finding.get('line', '?')}: "
                    f"{finding.get('message', 'unknown violation')}"
                )

    if args.strict and findings:
        sys.exit(1)


if __name__ == "__main__":
    compliance_scan_main()

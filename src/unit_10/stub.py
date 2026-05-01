"""Unit 10: Stub Generator Dispatch.

Provides the STUB_GENERATORS dispatch table and functions for generating
language-specific stub files from parsed blueprint signatures.
"""

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

from src.unit_2.stub import get_language_config
from src.unit_8.stub import extract_units
from src.unit_9.stub import parse_signatures

# ---------------------------------------------------------------------------
# stdlib module names (for TYPE_CHECKING guard logic -- Bug S3-47)
# ---------------------------------------------------------------------------

_STDLIB_MODULES = {
    "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
    "asyncore", "atexit", "base64", "bdb", "binascii", "binhex", "bisect",
    "builtins", "bz2", "calendar", "cgi", "cgitb", "chunk", "cmath", "cmd",
    "code", "codecs", "codeop", "collections", "colorsys", "compileall",
    "concurrent", "configparser", "contextlib", "contextvars", "copy",
    "copyreg", "cProfile", "crypt", "csv", "ctypes", "curses", "dataclasses",
    "datetime", "dbm", "decimal", "difflib", "dis", "distutils", "doctest",
    "email", "encodings", "enum", "errno", "faulthandler", "fcntl", "filecmp",
    "fileinput", "fnmatch", "fractions", "ftplib", "functools", "gc",
    "getopt", "getpass", "gettext", "glob", "graphlib", "grp", "gzip",
    "hashlib", "heapq", "hmac", "html", "http", "idlelib", "imaplib",
    "imghdr", "imp", "importlib", "inspect", "io", "ipaddress", "itertools",
    "json", "keyword", "lib2to3", "linecache", "locale", "logging", "lzma",
    "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap",
    "modulefinder", "multiprocessing", "netrc", "nis", "nntplib", "numbers",
    "operator", "optparse", "os", "ossaudiodev", "pathlib", "pdb", "pickle",
    "pickletools", "pipes", "pkgutil", "platform", "plistlib", "poplib",
    "posix", "posixpath", "pprint", "profile", "pstats", "pty", "pwd",
    "py_compile", "pyclbr", "pydoc", "queue", "quopri", "random", "re",
    "readline", "reprlib", "resource", "rlcompleter", "runpy", "sched",
    "secrets", "select", "selectors", "shelve", "shlex", "shutil", "signal",
    "site", "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "sqlite3",
    "ssl", "stat", "statistics", "string", "stringprep", "struct",
    "subprocess", "sunau", "symtable", "sys", "sysconfig", "syslog",
    "tabnanny", "tarfile", "telnetlib", "tempfile", "termios", "test",
    "textwrap", "threading", "time", "timeit", "tkinter", "token", "tokenize",
    "tomllib", "trace", "traceback", "tracemalloc", "tty", "turtle",
    "turtledemo", "types", "typing", "unicodedata", "unittest", "urllib",
    "uu", "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
    "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp",
    "zipfile", "zipimport", "zlib", "zoneinfo", "_thread", "__future__",
}

def _get_import_top_level_module(import_line: str) -> str:
    """Extract the top-level module name from an import statement string."""
    if import_line.startswith("from "):
        return import_line.split()[1].split(".")[0]
    elif import_line.startswith("import "):
        return import_line.split()[1].split(".")[0].split(",")[0]
    return import_line.split(".")[0]


# ---------------------------------------------------------------------------
# Bug S3-204 / cycle K-2: selective TYPE_CHECKING wrap helpers.
# ---------------------------------------------------------------------------

def _imported_names(import_line: str) -> set:
    """Extract the names bound by a single import line.

    Bug S3-204 / cycle K-2 / C-10-K2a. The names returned are the runtime
    bindings the import would create -- the symbols a downstream `from foo
    import bar` or `import baz` would attach to the module namespace.

    - `from m import a, b, c`     -> {"a", "b", "c"}
    - `from m import a as alias`  -> {"alias"}
    - `import foo`                -> {"foo"}
    - `import foo.bar`            -> {"foo"}      (leftmost; `foo.bar.x`
                                                   accesses go through `foo`)
    - `import foo.bar as baz`     -> {"baz"}
    - `import a, b`               -> {"a", "b"}
    """
    try:
        parsed = ast.parse(import_line.strip())
    except SyntaxError:
        return set()
    names: set = set()
    for node in parsed.body:
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    names.add(alias.asname)
                else:
                    names.add(alias.name.split(".")[0])
    return names


def _collect_runtime_referenced_names(body_nodes) -> set:
    """Collect names referenced at module-load time in a stub body.

    Bug S3-204 / cycle K-2 / C-10-K2a. Python evaluates class base classes,
    decorators, and default argument values when the module loads -- so
    upstream imports providing those names MUST emit at runtime, not under
    TYPE_CHECKING. Function/method bodies are `raise NotImplementedError()`
    in stubs, so anything they reference is runtime-deferred and NOT counted
    here.

    Visits:
      - ClassDef.bases, ClassDef.keywords[*].value (metaclass + class kwargs)
      - ClassDef.decorator_list, FunctionDef.decorator_list,
        AsyncFunctionDef.decorator_list
      - arguments.defaults, arguments.kw_defaults (for top-level functions
        and methods nested in classes -- evaluated at function-definition
        time, which happens at module load)
      - Assign.value, AnnAssign.value (module-level assignments; annotations
        themselves are stringified by `from __future__ import annotations`,
        so they are NOT counted)

    Recurses into nested ClassDef so nested-class bases get the same
    treatment. Does NOT recurse into FunctionDef / AsyncFunctionDef bodies
    (those are runtime-deferred in stubs).
    """
    runtime_names: set = set()

    def _add_names_from_expr(expr_node) -> None:
        if expr_node is None:
            return
        for n in ast.walk(expr_node):
            if isinstance(n, ast.Name):
                runtime_names.add(n.id)
            elif isinstance(n, ast.Attribute):
                # Walk to the leftmost Name of the attribute chain.
                cursor = n
                while isinstance(cursor, ast.Attribute):
                    cursor = cursor.value
                if isinstance(cursor, ast.Name):
                    runtime_names.add(cursor.id)

    def _visit_function_load_time(func_node) -> None:
        # Default arg values are evaluated at function-definition time.
        for default in func_node.args.defaults:
            _add_names_from_expr(default)
        for default in func_node.args.kw_defaults:
            _add_names_from_expr(default)
        # Decorators evaluate at module load.
        for dec in func_node.decorator_list:
            _add_names_from_expr(dec)
        # Body is runtime-deferred; do NOT recurse.

    def _visit_class_load_time(cls_node) -> None:
        for base in cls_node.bases:
            _add_names_from_expr(base)
        for kw in cls_node.keywords:
            _add_names_from_expr(kw.value)
        for dec in cls_node.decorator_list:
            _add_names_from_expr(dec)
        # Recurse into class body to handle nested ClassDef and method
        # default args / decorators (evaluated at class-creation time, which
        # happens at module load).
        for child in cls_node.body:
            if isinstance(child, ast.ClassDef):
                _visit_class_load_time(child)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _visit_function_load_time(child)
            elif isinstance(child, ast.AnnAssign):
                # Class-body AnnAssign: annotation is stringified, but value
                # is evaluated when the class body executes (at module load).
                _add_names_from_expr(child.value)
            elif isinstance(child, ast.Assign):
                _add_names_from_expr(child.value)

    for node in body_nodes:
        if isinstance(node, ast.ClassDef):
            _visit_class_load_time(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _visit_function_load_time(node)
        elif isinstance(node, ast.AnnAssign):
            # Module-level annotated assignment: annotation is stringified
            # by `from __future__ import annotations`; value is evaluated.
            _add_names_from_expr(node.value)
        elif isinstance(node, ast.Assign):
            _add_names_from_expr(node.value)

    return runtime_names


# ---------------------------------------------------------------------------
# Keys that bypass signature parsing (plugin + component)
# ---------------------------------------------------------------------------

_TEMPLATE_ONLY_KEYS = frozenset(
    {"stan_template", "plugin_markdown", "plugin_bash", "plugin_json"}
)

# ---------------------------------------------------------------------------
# Python stub generator
# ---------------------------------------------------------------------------


def _generate_python_stub(
    parsed_signatures: Any, language_config: Dict[str, Any]
) -> str:
    """Generate a Python stub from an ast.Module.

    - Every function body: raise NotImplementedError()
    - Every class body: methods raising NotImplementedError(),
      class-level attributes set to None
    - Module-level assert statements stripped
    - Stub sentinel prepended as first non-import statement
    - Imports preserved
    """
    if not isinstance(parsed_signatures, ast.Module):
        raise TypeError("parsed_signatures must be an ast.Module for Python stubs")

    sentinel = language_config.get(
        "stub_sentinel",
        "__SVP_STUB__ = True  # DO NOT DELIVER -- stub file generated by SVP",
    )

    lines: List[str] = []
    import_lines: List[str] = []
    body_lines: List[str] = []

    for node in parsed_signatures.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # Bug S3-203 / cycle K-1: skip `from __future__ ...` -- the
            # generator unconditionally prepends `from __future__ import
            # annotations` below (PEP 236, S3-197 / C-10-H7a). Re-emitting
            # the source-side copy after the sentinel violates PEP 236 and
            # produces SyntaxError at compile-time. C-10-K1a.
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                continue
            import_lines.append(ast.unparse(node))
        elif isinstance(node, ast.Assert):
            # Strip module-level asserts
            continue
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body_lines.append(_render_python_function(node, indent=0))
        elif isinstance(node, ast.ClassDef):
            body_lines.append(_render_python_class(node, indent=0))
        elif isinstance(node, ast.AnnAssign):
            # Module-level annotated assignment (e.g., STUB_GENERATORS: Dict[...])
            # Bug S3-10: Must have default values for importability
            body_lines.append(_render_python_ann_assign(node, indent=0))
        elif isinstance(node, ast.Assign):
            # Module-level assignment
            body_lines.append(_render_python_assign(node, indent=0))
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            # Module-level docstrings or string expressions
            body_lines.append(ast.unparse(node))
        else:
            # Other statements -- preserve as-is
            body_lines.append(ast.unparse(node))

    # Bug S3-47: Separate stdlib imports from non-stdlib (upstream) imports
    # and wrap non-stdlib imports in TYPE_CHECKING guard.
    # Bug S3-204 / cycle K-2: SELECTIVELY wrap upstream imports -- imports
    # providing names referenced at module-load time (class bases, decorators,
    # default arg values, module-level expressions outside annotations) emit
    # OUTSIDE TYPE_CHECKING so the stub can `exec()` cleanly. C-10-K2a.
    stdlib_imports: List[str] = []
    upstream_runtime_imports: List[str] = []
    upstream_typing_imports: List[str] = []
    runtime_names = _collect_runtime_referenced_names(parsed_signatures.body)
    for imp_line in import_lines:
        mod = _get_import_top_level_module(imp_line)
        if mod in _STDLIB_MODULES:
            stdlib_imports.append(imp_line)
        else:
            bound = _imported_names(imp_line)
            if bound & runtime_names:
                upstream_runtime_imports.append(imp_line)
            else:
                upstream_typing_imports.append(imp_line)

    # Build output: from __future__ first (PEP 236), sentinel, then imports, body
    # Bug R1 #7 / S3-197: from __future__ import annotations MUST be the first
    # statement of the stub (per PEP 236). This ensures annotations like Any,
    # OpenAI, etc. become strings -- sub-units of shared modules with Tier-2-
    # signature-only blueprints (no upstream imports) no longer NameError at
    # conftest exec.
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append(sentinel)
    has_any_imports = bool(
        stdlib_imports or upstream_runtime_imports or upstream_typing_imports
    )
    if has_any_imports:
        lines.append("")
    if stdlib_imports:
        lines.extend(stdlib_imports)
    if upstream_runtime_imports:
        lines.extend(upstream_runtime_imports)
    if upstream_typing_imports:
        lines.append("from typing import TYPE_CHECKING")
        lines.append("if TYPE_CHECKING:")
        for imp_line in upstream_typing_imports:
            lines.append(f"    {imp_line}")
    if has_any_imports:
        lines.append("")
    if body_lines:
        lines.extend(body_lines)

    result = "\n".join(lines)
    # Ensure trailing newline
    if not result.endswith("\n"):
        result += "\n"
    return result


def _render_python_function(node: ast.FunctionDef, indent: int = 0) -> str:
    """Render a function def with NotImplementedError body."""
    prefix = "    " * indent
    # Build the signature line
    sig = _build_function_signature(node)
    lines = [f"{prefix}{sig}"]
    # Preserve docstring if present
    docstring = _extract_docstring(node)
    if docstring:
        lines.append(f"{prefix}    {docstring}")
    lines.append(f"{prefix}    raise NotImplementedError()")
    lines.append("")
    return "\n".join(lines)


def _render_python_class(node: ast.ClassDef, indent: int = 0) -> str:
    """Render a class with stubbed methods and None attributes."""
    prefix = "    " * indent
    inner_prefix = "    " * (indent + 1)

    # Build class line
    bases = [ast.unparse(b) for b in node.bases]
    keywords = [ast.unparse(k) for k in node.keywords]
    all_args = bases + keywords
    if all_args:
        class_line = f"{prefix}class {node.name}({', '.join(all_args)}):"
    else:
        class_line = f"{prefix}class {node.name}:"

    lines = [class_line]

    # Preserve docstring if present
    docstring = _extract_docstring(node)
    if docstring:
        lines.append(f"{inner_prefix}{docstring}")

    has_body = False
    for child in node.body:
        if isinstance(child, ast.Expr) and isinstance(child.value, ast.Constant):
            # Skip docstring (already handled)
            if child is node.body[0]:
                continue
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lines.append(_render_python_function(child, indent=indent + 1))
            has_body = True
        elif isinstance(child, ast.AnnAssign):
            lines.append(_render_python_ann_assign_none(child, indent=indent + 1))
            has_body = True
        elif isinstance(child, ast.Assign):
            # Class-level assignments: set to None
            lines.append(_render_python_assign_none(child, indent=indent + 1))
            has_body = True
        elif isinstance(child, ast.Assert):
            # Strip asserts
            continue
        else:
            lines.append(f"{inner_prefix}{ast.unparse(child)}")
            has_body = True

    if not has_body and not docstring:
        lines.append(f"{inner_prefix}pass")

    lines.append("")
    return "\n".join(lines)


def _render_python_ann_assign(node: ast.AnnAssign, indent: int = 0) -> str:
    """Render annotated assignment at module level, ensuring importability.

    Bug S3-10 fix: Module-level annotated constants MUST have default values
    (Dict -> {}, List -> [], str -> "", etc.) for importability.
    """
    prefix = "    " * indent
    target = ast.unparse(node.target)
    annotation = ast.unparse(node.annotation)
    if node.value is not None:
        return f"{prefix}{target}: {annotation} = {ast.unparse(node.value)}"
    # No value provided -- assign a sensible default based on annotation type
    ann = annotation
    if "Dict" in ann or "dict" in ann:
        default = "{}"
    elif "List" in ann or "list" in ann:
        default = "[]"
    elif "Set" in ann or "set" in ann:
        default = "set()"
    elif ann == "str":
        default = '""'
    elif ann == "int":
        default = "0"
    elif ann == "bool":
        default = "False"
    else:
        default = "None"
    return f"{prefix}{target}: {annotation} = {default}"


def _render_python_ann_assign_none(node: ast.AnnAssign, indent: int = 0) -> str:
    """Render annotated assignment with value set to None (class-level)."""
    prefix = "    " * indent
    target = ast.unparse(node.target)
    annotation = ast.unparse(node.annotation)
    return f"{prefix}{target}: {annotation} = None"


def _render_python_assign(node: ast.Assign, indent: int = 0) -> str:
    """Render assignment at module level."""
    prefix = "    " * indent
    return f"{prefix}{ast.unparse(node)}"


def _render_python_assign_none(node: ast.Assign, indent: int = 0) -> str:
    """Render assignment with value set to None (class-level)."""
    prefix = "    " * indent
    targets = [ast.unparse(t) for t in node.targets]
    return f"{prefix}{' = '.join(targets)} = None"


def _build_function_signature(node: ast.FunctionDef) -> str:
    """Build a 'def name(args) -> ret:' line from an AST function node."""
    args_parts = []

    for i, arg in enumerate(node.args.args):
        part = arg.arg
        if arg.annotation:
            part += f": {ast.unparse(arg.annotation)}"
        # Check for defaults (defaults align to the end of args)
        num_defaults = len(node.args.defaults)
        num_args = len(node.args.args)
        default_offset = num_args - num_defaults
        if i >= default_offset:
            default_val = node.args.defaults[i - default_offset]
            part += f" = {ast.unparse(default_val)}"
        args_parts.append(part)

    # Handle *args
    if node.args.vararg:
        va = f"*{node.args.vararg.arg}"
        if node.args.vararg.annotation:
            va += f": {ast.unparse(node.args.vararg.annotation)}"
        args_parts.append(va)
    elif node.args.kwonlyargs:
        args_parts.append("*")

    # Handle keyword-only args
    for i, arg in enumerate(node.args.kwonlyargs):
        part = arg.arg
        if arg.annotation:
            part += f": {ast.unparse(arg.annotation)}"
        if i < len(node.args.kw_defaults) and node.args.kw_defaults[i] is not None:
            part += f" = {ast.unparse(node.args.kw_defaults[i])}"
        args_parts.append(part)

    # Handle **kwargs
    if node.args.kwarg:
        kw = f"**{node.args.kwarg.arg}"
        if node.args.kwarg.annotation:
            kw += f": {ast.unparse(node.args.kwarg.annotation)}"
        args_parts.append(kw)

    args_str = ", ".join(args_parts)

    # Return annotation
    if node.returns:
        return f"def {node.name}({args_str}) -> {ast.unparse(node.returns)}:"
    else:
        return f"def {node.name}({args_str}):"


def _extract_docstring(node: Any) -> str:
    """Extract docstring from a function or class node, if present."""
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        doc = node.body[0].value.value
        if "\n" in doc:
            return f'"""{doc}"""'
        return f'"""{doc}"""'
    return ""


# ---------------------------------------------------------------------------
# R stub generator
# ---------------------------------------------------------------------------


def _generate_r_stub(parsed_signatures: Any, language_config: Dict[str, Any]) -> str:
    """Generate an R stub from parsed R signatures.

    - Function bodies: stop("Not implemented")
    - R sentinel prepended as comment
    """
    sentinel = language_config.get(
        "stub_sentinel",
        "# __SVP_STUB__ <- TRUE  # DO NOT DELIVER -- stub file generated by SVP",
    )

    lines: List[str] = [sentinel, ""]

    if parsed_signatures is None:
        lines.append("# No signatures found")
    elif isinstance(parsed_signatures, list):
        for func_def in parsed_signatures:
            name = func_def["name"]
            raw_args = func_def.get("raw_args", "")
            lines.append(f"{name} <- function({raw_args}) {{")
            lines.append('  stop("Not implemented")')
            lines.append("}")
            lines.append("")

    result = "\n".join(lines)
    if not result.endswith("\n"):
        result += "\n"
    return result


# ---------------------------------------------------------------------------
# Stan template generator
# ---------------------------------------------------------------------------


def _generate_stan_template(
    parsed_signatures: Any, language_config: Dict[str, Any]
) -> str:
    """Generate a minimal Stan model template with sentinel comment."""
    lines = [
        "// __SVP_STUB__ -- DO NOT DELIVER -- stub file generated by SVP",
        "data {",
        "}",
        "parameters {",
        "}",
        "model {",
        "}",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Plugin stub generators
# ---------------------------------------------------------------------------


def _generate_plugin_markdown(
    parsed_signatures: Any, language_config: Dict[str, Any]
) -> str:
    """Generate a minimal Markdown plugin stub."""
    lines = [
        "<!-- __SVP_STUB__ -- DO NOT DELIVER -- stub file generated by SVP -->",
        "",
        "# Plugin Stub",
        "",
        "## Description",
        "",
        "Not implemented.",
        "",
        "## Usage",
        "",
        "Not implemented.",
        "",
        "## Configuration",
        "",
        "Not implemented.",
        "",
    ]
    return "\n".join(lines)


def _generate_plugin_bash(
    parsed_signatures: Any, language_config: Dict[str, Any]
) -> str:
    """Generate a minimal Bash plugin stub with shebang and placeholder."""
    lines = [
        "#!/usr/bin/env bash",
        "# __SVP_STUB__ -- DO NOT DELIVER -- stub file generated by SVP",
        "",
        'echo "Not implemented"',
        "exit 1",
        "",
    ]
    return "\n".join(lines)


def _generate_plugin_json(
    parsed_signatures: Any, language_config: Dict[str, Any]
) -> str:
    """Generate a minimal JSON plugin stub with required fields."""
    stub = {
        "__SVP_STUB__": True,
        "name": "plugin_stub",
        "version": "0.0.0",
        "description": "Not implemented",
    }
    return json.dumps(stub, indent=2) + "\n"


# ---------------------------------------------------------------------------
# STUB_GENERATORS dispatch table
# ---------------------------------------------------------------------------

STUB_GENERATORS: Dict[str, Callable[[Any, Dict[str, Any]], str]] = {
    "python": _generate_python_stub,
    "r": _generate_r_stub,
    "stan_template": _generate_stan_template,
    "plugin_markdown": _generate_plugin_markdown,
    "plugin_bash": _generate_plugin_bash,
    "plugin_json": _generate_plugin_json,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_stub(
    parsed_signatures: Any,
    language: str,
    language_config: Dict[str, Any],
) -> str:
    """Dispatch to the appropriate stub generator based on language_config.

    For plugin and component keys: bypasses signature parsing (receives None).
    For full-language keys (python, r): prepends language-specific sentinel.
    """
    stub_key = language_config["stub_generator_key"]

    if stub_key not in STUB_GENERATORS:
        raise KeyError(f"No stub generator for key: {stub_key}")

    generator = STUB_GENERATORS[stub_key]
    stub_text = generator(parsed_signatures, language_config)
    return stub_text


def generate_upstream_stubs(
    blueprint_dir: Path,
    unit_number: int,
    upstream_units: List[int],
    output_dir: Path,
    language: str,
) -> None:
    """Generate stubs for all upstream units.

    For each upstream unit: extracts Tier 2 from blueprint, parses signatures,
    generates stub, writes to output_dir.

    Forward-reference guard: raises ValueError if any upstream >= unit_number.
    """
    # Forward-reference guard
    for dep in upstream_units:
        if dep >= unit_number:
            raise ValueError(
                f"Forward reference: upstream unit {dep} >= current unit {unit_number}"
            )

    if not upstream_units:
        return

    # Get language config
    lang_config = get_language_config(language)
    stub_key = lang_config["stub_generator_key"]

    # Extract all units from blueprint
    all_units = extract_units(blueprint_dir)
    unit_map = {u.number: u for u in all_units}

    for dep_num in upstream_units:
        if dep_num not in unit_map:
            continue

        dep_unit = unit_map[dep_num]
        tier2_source = dep_unit.tier2

        # Bug S3-49: Use the dep unit's own languages, not the caller's language
        dep_language = language  # fallback to caller's language
        if hasattr(dep_unit, "languages") and dep_unit.languages:
            # Pick the dep unit's primary language
            dep_languages = dep_unit.languages
            try:
                lang_list = list(dep_languages)
            except (TypeError, ValueError):
                lang_list = []
            if language in lang_list:
                dep_language = language
            elif lang_list:
                dep_language = sorted(lang_list)[0]

        dep_lang_config = get_language_config(dep_language)
        dep_stub_key = dep_lang_config["stub_generator_key"]

        # Determine if this is a template-only key (no parsing needed)
        if dep_stub_key in _TEMPLATE_ONLY_KEYS:
            parsed = None
        else:
            # Parse signatures from Tier 2
            parsed = parse_signatures(tier2_source, dep_language, dep_lang_config)

        # Generate stub
        stub_text = generate_stub(parsed, dep_language, dep_lang_config)

        # Write stub to output directory
        file_ext = dep_lang_config.get("file_extension", ".py")
        output_file = output_dir / f"unit_{dep_num}_stub{file_ext}"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(stub_text, encoding="utf-8")


def main(argv: list = None) -> None:
    """CLI entry point for stub generation.

    Arguments:
        --blueprint: path to blueprint_contracts.md
        --unit: unit number (int)
        --output-dir: path for generated stubs
        --upstream: comma-separated list of upstream unit numbers (empty string for none)
        --language: language identifier (default: python)
    """
    parser = argparse.ArgumentParser(
        description="Generate stub files from blueprint signatures."
    )
    parser.add_argument(
        "--blueprint",
        type=str,
        required=True,
        help="Path to blueprint_contracts.md",
    )
    parser.add_argument("--unit", type=int, required=True, help="Unit number")
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Output directory for generated stubs",
    )
    parser.add_argument(
        "--upstream",
        type=str,
        default="",
        help="Comma-separated list of upstream unit numbers",
    )
    parser.add_argument(
        "--language",
        type=str,
        default="python",
        help="Language identifier",
    )

    args = parser.parse_args(argv)

    try:
        blueprint_path = Path(args.blueprint)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Parse upstream units
        upstream_units: List[int] = []
        if args.upstream and args.upstream.strip():
            upstream_units = [
                int(u.strip()) for u in args.upstream.split(",") if u.strip()
            ]

        # Get language config
        lang_config = get_language_config(args.language)
        stub_key = lang_config["stub_generator_key"]

        # Determine blueprint_dir from the blueprint file path
        blueprint_dir = blueprint_path.parent

        # Extract all units
        all_units = extract_units(blueprint_dir)
        unit_map = {u.number: u for u in all_units}

        # Generate stub for current unit
        if args.unit in unit_map:
            current_unit = unit_map[args.unit]
            tier2_source = current_unit.tier2

            if stub_key in _TEMPLATE_ONLY_KEYS:
                parsed = None
            else:
                parsed = parse_signatures(tier2_source, args.language, lang_config)

            stub_text = generate_stub(parsed, args.language, lang_config)

            file_ext = lang_config.get("file_extension", ".py")
            output_file = output_dir / f"stub{file_ext}"
            output_file.write_text(stub_text, encoding="utf-8")

        # Generate upstream stubs
        if upstream_units:
            generate_upstream_stubs(
                blueprint_dir,
                args.unit,
                upstream_units,
                output_dir,
                args.language,
            )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

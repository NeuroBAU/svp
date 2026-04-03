"""Regression test for Bug 61: include_tier1 parameter in blueprint context building.

Verifies:
1. build_unit_context accepts include_tier1 parameter.
2. test_agent invocations pass include_tier1=False (no Tier 1 prose per spec Section 3.16).
3. implementation_agent invocations pass include_tier1=False.
4. coverage_review and diagnostic_agent use include_tier1=True.
5. build_unit_context in blueprint_extractor.py accepts include_tier1 parameter.

SVP 2.2 adaptation:
- _get_unit_context renamed to build_unit_context in scripts/prepare_task.py
- build_unit_context(blueprint_dir, unit_number, include_tier1=True) is the
  SVP 2.2 signature in prepare_task.py
"""

import sys
import ast
from pathlib import Path

# Add scripts to path for imports -- support both workspace and delivered repo layouts
_project_root = Path(__file__).resolve().parent.parent.parent
_scripts_dir = _project_root / "scripts"
if not _scripts_dir.is_dir():
    _scripts_dir = _project_root / "svp" / "scripts"
sys.path.insert(0, str(_scripts_dir))


def _find_prepare_task_path() -> Path:
    """Locate prepare_task.py in either workspace or delivered repo layout."""
    candidates = [
        _project_root / "scripts" / "prepare_task.py",
        _project_root / "svp" / "scripts" / "prepare_task.py",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("Cannot find prepare_task.py in any known location")


def _find_blueprint_extractor_path() -> Path:
    """Locate blueprint_extractor.py in either workspace or delivered repo layout."""
    candidates = [
        _project_root / "scripts" / "blueprint_extractor.py",
        _project_root / "svp" / "scripts" / "blueprint_extractor.py",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("Cannot find blueprint_extractor.py in any known location")


# --------------------------------------------------------------------------
# Test 1: build_unit_context in prepare_task.py has include_tier1 parameter
# --------------------------------------------------------------------------


def test_build_unit_context_has_include_tier1_parameter():
    """build_unit_context must accept an include_tier1 parameter.

    SVP 2.2: _get_unit_context was renamed to build_unit_context.
    """
    source = _find_prepare_task_path().read_text(encoding="utf-8")
    assert "def build_unit_context(" in source

    # Parse AST and find the function
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "build_unit_context":
            arg_names = [a.arg for a in node.args.args]
            assert "include_tier1" in arg_names, (
                "build_unit_context must have include_tier1 parameter"
            )
            return
    raise AssertionError("build_unit_context function not found in prepare_task.py")


# --------------------------------------------------------------------------
# Test 2: build_unit_context forwards include_tier1
# --------------------------------------------------------------------------


def test_build_unit_context_forwards_include_tier1():
    """build_unit_context must forward include_tier1 to underlying implementation."""
    source = _find_prepare_task_path().read_text(encoding="utf-8")
    # The call must include include_tier1= somewhere
    assert "include_tier1=include_tier1" in source or "include_tier1=True" in source, (
        "build_unit_context must forward include_tier1 parameter"
    )


# --------------------------------------------------------------------------
# Test 3: test_agent passes include_tier1=False
# --------------------------------------------------------------------------


def test_test_agent_uses_include_tier1_false():
    """test_agent section must call build_unit_context with include_tier1=False.

    SVP 2.2: test_agent logic is in _prepare_test_agent helper function.
    We search for the helper function's build_unit_context call.
    """
    source = _find_prepare_task_path().read_text(encoding="utf-8")

    lines = source.split("\n")
    # Look in _prepare_test_agent function
    in_test_agent_func = False
    found = False
    for line in lines:
        if "def _prepare_test_agent" in line:
            in_test_agent_func = True
        elif in_test_agent_func and line.startswith("def "):
            break
        elif in_test_agent_func and "build_unit_context(" in line:
            assert "include_tier1=False" in line, (
                "test_agent must call build_unit_context with include_tier1=False"
            )
            found = True
            break

    assert found, "test_agent helper (_prepare_test_agent) must call build_unit_context"


# --------------------------------------------------------------------------
# Test 4: implementation_agent passes include_tier1=False
# --------------------------------------------------------------------------


def test_implementation_agent_uses_include_tier1_false():
    """implementation_agent section must call build_unit_context with include_tier1=False.

    SVP 2.2: implementation_agent logic is in _prepare_implementation_agent helper.
    """
    source = _find_prepare_task_path().read_text(encoding="utf-8")

    lines = source.split("\n")
    # Look in _prepare_implementation_agent function
    in_impl_func = False
    found = False
    for line in lines:
        if "def _prepare_implementation_agent" in line:
            in_impl_func = True
        elif in_impl_func and line.startswith("def "):
            break
        elif in_impl_func and "build_unit_context(" in line:
            assert "include_tier1=False" in line, (
                "implementation_agent must call build_unit_context with include_tier1=False"
            )
            found = True
            break

    assert found, "implementation_agent helper (_prepare_implementation_agent) must call build_unit_context"


# --------------------------------------------------------------------------
# Test 5: coverage_review uses default (True) -- no include_tier1=False
# --------------------------------------------------------------------------


def test_coverage_review_uses_include_tier1_true():
    """coverage_review must NOT pass include_tier1=False (needs full context)."""
    source = _find_prepare_task_path().read_text(encoding="utf-8")

    lines = source.split("\n")
    in_coverage = False
    for line in lines:
        if '"coverage_review"' in line and ("agent_type" in line or "==" in line):
            in_coverage = True
        elif in_coverage and "elif" in line and "agent_type" in line:
            break
        elif in_coverage and "build_unit_context(" in line:
            assert "include_tier1=False" not in line, (
                "coverage_review must NOT pass include_tier1=False"
            )


# --------------------------------------------------------------------------
# Test 6: diagnostic_agent uses default (True) -- no include_tier1=False
# --------------------------------------------------------------------------


def test_diagnostic_agent_uses_include_tier1_true():
    """diagnostic_agent must NOT pass include_tier1=False (needs full context)."""
    source = _find_prepare_task_path().read_text(encoding="utf-8")

    lines = source.split("\n")
    in_diag = False
    for line in lines:
        if '"diagnostic_agent"' in line and ("agent_type" in line or "==" in line):
            in_diag = True
        elif in_diag and "elif" in line and "agent_type" in line:
            break
        elif in_diag and "build_unit_context(" in line:
            assert "include_tier1=False" not in line, (
                "diagnostic_agent must NOT pass include_tier1=False"
            )


# --------------------------------------------------------------------------
# Test 7: blueprint_extractor build_unit_context has include_tier1
# --------------------------------------------------------------------------


def test_blueprint_extractor_build_unit_context_has_include_tier1():
    """build_unit_context in blueprint_extractor.py must accept include_tier1."""
    source = _find_blueprint_extractor_path().read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "build_unit_context":
            arg_names = [a.arg for a in node.args.args]
            assert "include_tier1" in arg_names, (
                "build_unit_context must have include_tier1 parameter"
            )
            return
    raise AssertionError("build_unit_context function not found in blueprint_extractor.py")


# --------------------------------------------------------------------------
# Test 8: build_unit_context excludes Tier 1 when include_tier1=False
# --------------------------------------------------------------------------


def test_blueprint_extractor_build_unit_context_excludes_tier1_when_false():
    """build_unit_context must not include Tier 1 description when include_tier1=False."""
    source = _find_blueprint_extractor_path().read_text(encoding="utf-8")
    # The function must contain a conditional guard on include_tier1 for description
    assert "include_tier1 and" in source or "if include_tier1" in source, (
        "build_unit_context must conditionally include Tier 1 based on include_tier1 parameter"
    )

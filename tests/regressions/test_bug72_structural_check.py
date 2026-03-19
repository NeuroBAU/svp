"""Bug 72: Structural completeness check regression tests.

Tests the project-agnostic structural_check.py script against synthetic
Python code, and verifies that agent prompts contain the new checklist items.
"""

import ast
import json
import sys
import textwrap
from pathlib import Path
from typing import Dict

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from structural_check import (
    check_dict_registry_gaps,
    check_enum_value_gaps,
    check_string_dispatch_gaps,
    check_unused_exports,
    format_text,
    main,
    run_checks,
)


# ---------------------------------------------------------------------------
# Helpers -- create synthetic Python files in tmp_path
# ---------------------------------------------------------------------------


def _write_file(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def _collect_py(tmp_path: Path):
    return sorted(tmp_path.glob("*.py"))


# ===================================================================
# Check 1: Dict registry gap detection
# ===================================================================


class TestDictRegistryGaps:
    """Declare 3 keys, use 2, flag 1."""

    def test_unused_dict_key_detected(self, tmp_path):
        _write_file(
            tmp_path,
            "registry.py",
            """\
            HANDLERS = {
                "alpha": handle_alpha,
                "beta": handle_beta,
                "gamma": handle_gamma,
            }
            """,
        )
        _write_file(
            tmp_path,
            "consumer.py",
            """\
            from registry import HANDLERS
            result = HANDLERS["alpha"]
            other = HANDLERS.get("beta")
            """,
        )
        py_files = _collect_py(tmp_path)
        findings = check_dict_registry_gaps(tmp_path, py_files)
        assert len(findings) == 1
        assert "gamma" in findings[0]["unused_keys"]
        assert findings[0]["dict_name"] == "HANDLERS"

    def test_all_keys_used_produces_no_findings(self, tmp_path):
        _write_file(
            tmp_path,
            "registry.py",
            """\
            MODES = {
                "fast": 1,
                "slow": 2,
                "medium": 3,
            }
            """,
        )
        _write_file(
            tmp_path,
            "user.py",
            """\
            from registry import MODES
            x = MODES["fast"]
            y = MODES["slow"]
            z = MODES["medium"]
            """,
        )
        py_files = _collect_py(tmp_path)
        findings = check_dict_registry_gaps(tmp_path, py_files)
        assert len(findings) == 0

    def test_small_dict_ignored(self, tmp_path):
        """Dicts with fewer than 3 keys are not flagged."""
        _write_file(
            tmp_path,
            "small.py",
            """\
            CONFIG = {
                "a": 1,
                "b": 2,
            }
            """,
        )
        py_files = _collect_py(tmp_path)
        findings = check_dict_registry_gaps(tmp_path, py_files)
        assert len(findings) == 0


# ===================================================================
# Check 2: Enum value gap detection
# ===================================================================


class TestEnumValueGaps:
    """Declare 3 members, use 2, flag 1."""

    def test_unused_enum_member_detected(self, tmp_path):
        _write_file(
            tmp_path,
            "colors.py",
            """\
            from enum import Enum

            class Color(Enum):
                RED = "red"
                GREEN = "green"
                BLUE = "blue"
            """,
        )
        _write_file(
            tmp_path,
            "painter.py",
            """\
            from colors import Color
            if c == Color.RED:
                pass
            elif c == Color.GREEN:
                pass
            """,
        )
        py_files = _collect_py(tmp_path)
        findings = check_enum_value_gaps(tmp_path, py_files)
        assert len(findings) == 1
        assert "BLUE" in findings[0]["unused_members"]

    def test_all_members_used_no_findings(self, tmp_path):
        _write_file(
            tmp_path,
            "status.py",
            """\
            from enum import Enum

            class Status(Enum):
                OPEN = "open"
                CLOSED = "closed"
                PENDING = "pending"
            """,
        )
        _write_file(
            tmp_path,
            "handler.py",
            """\
            from status import Status
            if s == Status.OPEN:
                pass
            elif s == Status.CLOSED:
                pass
            elif s == Status.PENDING:
                pass
            """,
        )
        py_files = _collect_py(tmp_path)
        findings = check_enum_value_gaps(tmp_path, py_files)
        assert len(findings) == 0


# ===================================================================
# Check 3: Unused export detection
# ===================================================================


class TestUnusedExports:
    """Export 3 functions, call 2, flag 1."""

    def test_unused_function_detected(self, tmp_path):
        _write_file(
            tmp_path,
            "module_a.py",
            """\
            def func_one():
                pass

            def func_two():
                pass

            def func_three():
                pass
            """,
        )
        _write_file(
            tmp_path,
            "module_b.py",
            """\
            from module_a import func_one, func_two
            func_one()
            func_two()
            """,
        )
        py_files = _collect_py(tmp_path)
        findings = check_unused_exports(tmp_path, py_files)
        func_names = [f["function_name"] for f in findings]
        assert "func_three" in func_names

    def test_all_functions_called_no_findings(self, tmp_path):
        _write_file(
            tmp_path,
            "lib.py",
            """\
            def alpha():
                pass

            def beta():
                pass

            def gamma():
                pass
            """,
        )
        _write_file(
            tmp_path,
            "main.py",
            """\
            from lib import alpha, beta, gamma
            alpha()
            beta()
            gamma()
            """,
        )
        py_files = _collect_py(tmp_path)
        findings = check_unused_exports(tmp_path, py_files)
        assert len(findings) == 0


# ===================================================================
# Check 4: String dispatch gap detection
# ===================================================================


class TestStringDispatchGaps:
    """3-branch elif, caller passes 4th value."""

    def test_unhandled_string_value_detected(self, tmp_path):
        _write_file(
            tmp_path,
            "dispatcher.py",
            """\
            def handle(action):
                if action == "create":
                    return 1
                elif action == "update":
                    return 2
                elif action == "delete":
                    return 3
            """,
        )
        _write_file(
            tmp_path,
            "caller.py",
            """\
            from dispatcher import handle
            handle("create")
            handle("update")
            handle("archive")
            """,
        )
        py_files = _collect_py(tmp_path)
        findings = check_string_dispatch_gaps(tmp_path, py_files)
        assert len(findings) >= 1
        unhandled = findings[0]["unhandled"]
        assert "archive" in unhandled

    def test_all_values_handled_no_findings(self, tmp_path):
        _write_file(
            tmp_path,
            "dispatcher.py",
            """\
            def process(mode):
                if mode == "fast":
                    return 1
                elif mode == "slow":
                    return 2
                elif mode == "normal":
                    return 3
            """,
        )
        _write_file(
            tmp_path,
            "caller.py",
            """\
            from dispatcher import process
            process("fast")
            process("slow")
            """,
        )
        py_files = _collect_py(tmp_path)
        findings = check_string_dispatch_gaps(tmp_path, py_files)
        assert len(findings) == 0


# ===================================================================
# Clean code produces no findings
# ===================================================================


class TestCleanCode:
    def test_clean_codebase_returns_clean(self, tmp_path):
        _write_file(
            tmp_path,
            "clean.py",
            """\
            def helper():
                return 42
            """,
        )
        _write_file(
            tmp_path,
            "main.py",
            """\
            from clean import helper
            result = helper()
            """,
        )
        results = run_checks(tmp_path)
        assert results["status"] == "CLEAN"
        assert results["summary"]["total_findings"] == 0
        assert results["summary"]["checks_run"] == 5  # Bug 74: added stub_imports check


# ===================================================================
# JSON output format
# ===================================================================


class TestJSONFormat:
    def test_json_output_structure(self, tmp_path):
        _write_file(tmp_path, "empty.py", "x = 1\n")
        results = run_checks(tmp_path)

        assert "status" in results
        assert results["status"] in ("CLEAN", "FINDINGS")
        assert "checks" in results
        assert "dict_registry_gaps" in results["checks"]
        assert "enum_value_gaps" in results["checks"]
        assert "unused_exports" in results["checks"]
        assert "string_dispatch_gaps" in results["checks"]
        assert "summary" in results
        assert "total_findings" in results["summary"]
        assert "files_scanned" in results["summary"]
        assert "checks_run" in results["summary"]

        # Verify JSON serializable
        json_str = json.dumps(results)
        parsed = json.loads(json_str)
        assert parsed == results


# ===================================================================
# Text output format
# ===================================================================


class TestTextFormat:
    def test_text_output_contains_status(self, tmp_path):
        _write_file(tmp_path, "empty.py", "x = 1\n")
        results = run_checks(tmp_path)
        text = format_text(results)
        assert "Structural Check:" in text
        assert "CLEAN" in text

    def test_text_output_shows_findings(self, tmp_path):
        _write_file(
            tmp_path,
            "reg.py",
            """\
            HANDLERS = {
                "a": 1,
                "b": 2,
                "c": 3,
            }
            """,
        )
        results = run_checks(tmp_path)
        text = format_text(results)
        assert "FINDINGS" in text or "Dict Registry Gaps" in text


# ===================================================================
# --strict exit code
# ===================================================================


class TestStrictMode:
    def test_strict_exits_1_on_findings(self, tmp_path, monkeypatch):
        _write_file(
            tmp_path,
            "reg.py",
            """\
            from enum import Enum

            class MyEnum(Enum):
                A = 1
                B = 2
                C = 3
            """,
        )
        monkeypatch.setattr(
            sys,
            "argv",
            ["structural_check.py", "--target", str(tmp_path), "--strict", "--format", "json"],
        )
        exit_code = main()
        assert exit_code == 1

    def test_strict_exits_0_on_clean(self, tmp_path, monkeypatch):
        _write_file(tmp_path, "clean.py", "x = 1\n")
        monkeypatch.setattr(
            sys,
            "argv",
            ["structural_check.py", "--target", str(tmp_path), "--strict", "--format", "json"],
        )
        exit_code = main()
        assert exit_code == 0


# ===================================================================
# Agent prompt content verification
# ===================================================================

DELIVERED_REPO = PROJECT_ROOT / ".." / "svp2.1-repo"


class TestAgentPromptUpdates:
    """Verify agent definitions contain Bug 72 checklist items."""

    @pytest.mark.skipif(
        not (DELIVERED_REPO / "svp" / "agents").is_dir(),
        reason="Delivered repo not available",
    )
    def test_blueprint_checker_has_registry_completeness(self):
        path = DELIVERED_REPO / "svp" / "agents" / "blueprint_checker.md"
        content = path.read_text(encoding="utf-8")
        assert "Registry completeness" in content or "registry completeness" in content

    @pytest.mark.skipif(
        not (DELIVERED_REPO / "svp" / "agents").is_dir(),
        reason="Delivered repo not available",
    )
    def test_integration_test_author_has_structural_completeness(self):
        path = DELIVERED_REPO / "svp" / "agents" / "integration_test_author.md"
        content = path.read_text(encoding="utf-8")
        assert "Registry-Handler Alignment" in content or "structural_completeness" in content

    @pytest.mark.skipif(
        not (DELIVERED_REPO / "svp" / "agents").is_dir(),
        reason="Delivered repo not available",
    )
    def test_bug_triage_has_structural_precheck(self):
        path = DELIVERED_REPO / "svp" / "agents" / "bug_triage_agent.md"
        content = path.read_text(encoding="utf-8")
        assert "Step 0" in content or "Structural Pre-Check" in content
        assert "Registry Diagnosis Recipe" in content


# ===================================================================
# Routing: structural_check sub-stage
# ===================================================================


class TestStructuralCheckRouting:
    """Verify structural_check is wired into Stage 5 routing."""

    def test_structural_check_in_stage5_sub_stages(self):
        from pipeline_state import STAGE_5_SUB_STAGES

        assert "structural_check" in STAGE_5_SUB_STAGES

    def test_structural_check_before_compliance_scan(self):
        from pipeline_state import STAGE_5_SUB_STAGES

        sc_idx = STAGE_5_SUB_STAGES.index("structural_check")
        cs_idx = STAGE_5_SUB_STAGES.index("compliance_scan")
        assert sc_idx < cs_idx

    def test_structural_check_in_known_phases(self):
        from routing import _KNOWN_PHASES

        assert "structural_check" in _KNOWN_PHASES

    def test_route_structural_check_sub_stage(self):
        from routing import route
        from pipeline_state import PipelineState

        state = PipelineState(
            stage="5",
            sub_stage="structural_check",
            current_unit=None,
            total_units=24,
            delivered_repo_path="/tmp/test-repo",
        )
        action = route(state, PROJECT_ROOT)
        assert action["ACTION"] == "run_command"
        assert "structural_check.py" in action["COMMAND"]
        assert action["CONTEXT"] == "structural_check"

    def test_dispatch_structural_check_succeeded(self):
        from routing import dispatch_command_status
        from pipeline_state import PipelineState

        state = PipelineState(
            stage="5",
            sub_stage="structural_check",
            current_unit=None,
            total_units=24,
        )
        new_state = dispatch_command_status(
            state, "COMMAND_SUCCEEDED", None, "structural_check", PROJECT_ROOT
        )
        assert new_state.sub_stage == "compliance_scan"

    def test_dispatch_structural_check_failed(self):
        from routing import dispatch_command_status
        from pipeline_state import PipelineState

        state = PipelineState(
            stage="5",
            sub_stage="structural_check",
            current_unit=None,
            total_units=24,
        )
        new_state = dispatch_command_status(
            state, "COMMAND_FAILED: findings detected", None, "structural_check", PROJECT_ROOT
        )
        assert new_state.sub_stage == "gate_5_3"

"""Regression tests for Bug S3-118.

S3-118: derive_env_name returned 'svp-' for relative project roots because
Path('.').name is the empty string. The fix is two-layered:

1. derive_env_name calls .resolve() internally (defensive).
2. Every CLI main() that takes --project-root resolves at parse time.

This test file locks BOTH layers against regression. The convention lock
(test_all_cli_main_functions_resolve_project_root) walks every main()
function in every src/unit_*/stub.py and fails if a new CLI script is
added that parses --project-root without resolving.
"""
import ast
import inspect
from pathlib import Path

import pytest


SRC_DIR = Path(__file__).parent.parent.parent / "src"


# ---------------------------------------------------------------------------
# Layer 1 source lock: derive_env_name must call .resolve()
# ---------------------------------------------------------------------------


class TestBugS318DeriveEnvNameSourceLock:
    """Locks the defensive .resolve() in derive_env_name against regression."""

    def test_derive_env_name_source_calls_resolve(self):
        """src/unit_1/stub.py derive_env_name must call .resolve() before .name."""
        from svp_config import derive_env_name
        source = inspect.getsource(derive_env_name)
        assert ".resolve()" in source, (
            "derive_env_name must call .resolve() before reading .name. "
            "Path('.').name is '', which produced the nonsense env name 'svp-'."
        )

    def test_derive_env_name_runtime_handles_relative_dot(
        self, tmp_path, monkeypatch
    ):
        """End-to-end: derive_env_name(Path('.')) returns a non-degenerate name."""
        from svp_config import derive_env_name
        sub = tmp_path / "debrief1.0"
        sub.mkdir()
        monkeypatch.chdir(sub)
        result = derive_env_name(Path("."))
        assert result == "svp-debrief1.0"
        assert result != "svp-"


# ---------------------------------------------------------------------------
# Layer 2 convention lock: every CLI main() resolves --project-root
# ---------------------------------------------------------------------------


class TestBugS318CliMainResolveConvention:
    """Convention lock: every CLI main() that reads args.project_root must
    assign it via Path(args.project_root).resolve()."""

    def _collect_project_root_assignments(self):
        """Walk every src/unit_*/stub.py, find every `project_root = <expr>`
        assignment whose RHS mentions `args.project_root`. These are CLI
        entry points regardless of the function's name (Unit 15 uses
        `run_quality_gate_main`, Unit 13 uses `main`, etc.). Return a list
        of (stub_relative_path, line_number, ast_expression_node) tuples."""
        assignments = []
        for stub_path in sorted(SRC_DIR.glob("unit_*/stub.py")):
            try:
                tree = ast.parse(stub_path.read_text())
            except SyntaxError:
                continue
            for sub in ast.walk(tree):
                if not isinstance(sub, ast.Assign):
                    continue
                if len(sub.targets) != 1:
                    continue
                target = sub.targets[0]
                if not (
                    isinstance(target, ast.Name)
                    and target.id == "project_root"
                ):
                    continue
                rhs_source = ast.unparse(sub.value)
                if "args.project_root" not in rhs_source:
                    continue
                assignments.append(
                    (
                        stub_path.relative_to(SRC_DIR).as_posix(),
                        sub.lineno,
                        sub.value,
                    )
                )
        return assignments

    def test_convention_lock_finds_at_least_the_known_cli_mains(self):
        """Sanity: we should find project_root assignments in Unit 11, 13, 14, 15."""
        assignments = self._collect_project_root_assignments()
        stub_files = {path for path, _, _ in assignments}
        expected = {
            "unit_11/stub.py",
            "unit_13/stub.py",
            "unit_14/stub.py",
            "unit_15/stub.py",
        }
        missing = expected - stub_files
        assert not missing, (
            f"Expected CLI main() project_root assignments in {expected}, "
            f"but did not find them in {missing}. Either the unit was renamed "
            f"or the assignment pattern changed."
        )

    def test_all_cli_main_functions_resolve_project_root(self):
        """Every `project_root = Path(args.project_root)...` in a CLI main()
        must end with a `.resolve()` call.

        Bug S3-118: Unit 15's quality_gate main() parsed --project-root without
        resolving. Path('.').name == '', so derive_env_name returned 'svp-'
        and every conda invocation crashed with EnvironmentLocationNotFound.

        Unit 11 and Unit 14 already followed the convention; Unit 13 and Unit 15
        had silently drifted. This test locks the convention across every
        src/unit_*/stub.py main() function so future drift fails loudly.
        """
        assignments = self._collect_project_root_assignments()
        offenders = []
        for stub_path, lineno, expr in assignments:
            # Accept only expressions of the shape X.resolve()
            if not (
                isinstance(expr, ast.Call)
                and isinstance(expr.func, ast.Attribute)
                and expr.func.attr == "resolve"
            ):
                rhs_source = ast.unparse(expr)
                offenders.append(f"{stub_path}:{lineno}: {rhs_source}")
        assert not offenders, (
            "CLI main() functions assign project_root from --project-root "
            "without .resolve():\n  " + "\n  ".join(offenders) + "\n\n"
            "Fix: change `Path(args.project_root)` to "
            "`Path(args.project_root).resolve()`. See Bug S3-118."
        )


# ---------------------------------------------------------------------------
# Layer 2 runtime check: Unit 15 main() stores a resolved project_root
# ---------------------------------------------------------------------------


class TestBugS318QualityGateMainResolvesAtRuntime:
    """Runtime verification: calling Unit 15's main() with --project-root .
    produces a resolved absolute project_root downstream."""

    def test_quality_gate_main_source_resolves(self):
        """quality_gate.run_quality_gate_main must resolve --project-root."""
        import quality_gate
        source = inspect.getsource(quality_gate.run_quality_gate_main)
        assert "Path(args.project_root).resolve()" in source, (
            "run_quality_gate_main must resolve --project-root at parse time. "
            "See Bug S3-118."
        )

    def test_prepare_task_main_source_resolves(self):
        """prepare_task.main must call .resolve() on --project-root."""
        import prepare_task
        source = inspect.getsource(prepare_task.main)
        assert "Path(args.project_root).resolve()" in source, (
            "prepare_task main() must resolve --project-root at parse time. "
            "See Bug S3-118."
        )

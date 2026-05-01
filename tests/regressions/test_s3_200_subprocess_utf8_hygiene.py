"""Cycle I-3 (S3-200) -- verify cp1252 subprocess hygiene sweep across
Units 4, 11, 15:

(a) Site A -- verify_toolchain_ready default subprocess runner (Unit 4);
(b) Site B -- _env_exists conda env-list subprocess (Unit 11);
(c) Site C -- regression-adapt subprocess in run_infrastructure_setup
    Step 8 (Unit 11);
(d) Site D -- _list_installed_conda_packages default runner (Unit 11);
(e) Site E -- install_dep_delta conda install default runner (Unit 11);
(f) Site F -- _run_command quality-gate runner (Unit 15).

Plus 1 cross-cutting AST guard:

(g) test_i3_no_text_true_remaining_in_targeted_files -- walks the three
    stub files and asserts no `text=True` keyword remains at the six
    audited function definitions.

Each fix applies the H6 / S3-196 cp1252 hygiene pattern verbatim:
PYTHONIOENCODING=utf-8 + PYTHONUTF8=1 env override via os.environ.copy()
+ setdefault; text=True dropped; bytes-decode-with-replace where
stdout/stderr is consumed; bytes-or-str isinstance guard at
runner-injection sites (D + E).

S3-103 flat-module imports.
"""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _project_root() -> Path:
    """Walk up from this test file to find the project root.

    Mirrors the resolver used in test_s3_169_doc_consistency.py.
    """
    candidate = Path(__file__).resolve()
    for ancestor in [candidate, *candidate.parents]:
        if (ancestor / "src" / "unit_4" / "stub.py").exists():
            return ancestor
        if (ancestor / "svp" / "src" / "unit_4" / "stub.py").exists():
            return ancestor
    raise RuntimeError(
        f"Could not locate project root (src/unit_4/stub.py) from {candidate}"
    )


def _stub_path(unit: int) -> Path:
    """Return the path to src/unit_<N>/stub.py in workspace or repo layout."""
    root = _project_root()
    workspace = root / "src" / f"unit_{unit}" / "stub.py"
    if workspace.exists():
        return workspace
    repo = root / "svp" / "src" / f"unit_{unit}" / "stub.py"
    if repo.exists():
        return repo
    raise RuntimeError(f"Could not locate src/unit_{unit}/stub.py from {root}")


def _make_bytes_completed_proc(returncode: int = 0,
                               stdout: bytes = b"",
                               stderr: bytes = b"") -> MagicMock:
    """Return a MagicMock whose attributes mirror a CompletedProcess with
    bytes stdout/stderr (post-I-3 production shape)."""
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


# ---------------------------------------------------------------------------
# Site A -- verify_toolchain_ready default subprocess runner (Unit 4)
# ---------------------------------------------------------------------------


def test_i3_unit_4_verify_toolchain_runner_sets_utf8_env_no_text_true(
    monkeypatch, tmp_path
):
    """C-4-I3a: the default _default_runner inside verify_toolchain_ready
    MUST set PYTHONIOENCODING=utf-8 + PYTHONUTF8=1 on the subprocess env
    AND MUST NOT pass text=True."""
    from toolchain_reader import verify_toolchain_ready

    # Materialize a minimal pipeline toolchain.json with one verify_command.
    (tmp_path / "toolchain.json").write_text(
        json.dumps(
            {
                "environment": {
                    "tool": "conda",
                    "run_prefix": "conda run -n {env_name}",
                    "verify_commands": ["{run_prefix} python --version"],
                },
                "quality": {},
            }
        )
    )

    captured: dict = {}

    def fake_run(*args, **kwargs):
        captured["env"] = kwargs.get("env", None)
        captured["text"] = kwargs.get("text", None)
        captured["capture_output"] = kwargs.get("capture_output", None)
        m = MagicMock()
        m.returncode = 0
        m.stdout = b""
        m.stderr = b""
        return m

    monkeypatch.setattr(subprocess, "run", fake_run)

    # Default runner branch -- pass runner=None.
    verify_toolchain_ready(tmp_path, "svp-test")

    assert captured["env"] is not None, (
        "_default_runner MUST pass an env dict to subprocess.run"
    )
    assert captured["env"].get("PYTHONIOENCODING") == "utf-8", (
        "env must set PYTHONIOENCODING=utf-8"
    )
    assert captured["env"].get("PYTHONUTF8") == "1", (
        "env must set PYTHONUTF8=1"
    )
    assert captured["text"] in (None, False), (
        "subprocess.run MUST NOT use text=True (bytes mode is required)"
    )
    assert captured["capture_output"] is True, (
        "subprocess.run MUST use capture_output=True"
    )


# ---------------------------------------------------------------------------
# Site B -- _env_exists conda env-list subprocess (Unit 11)
# ---------------------------------------------------------------------------


def test_i3_unit_11_environment_already_exists_sets_utf8_env_no_text_true(
    monkeypatch,
):
    """C-11-I3a: the conda env-list subprocess inside _env_exists MUST
    set PYTHONIOENCODING=utf-8 + PYTHONUTF8=1 AND MUST NOT pass
    text=True. Decoded stdout MUST be a str."""
    import infrastructure_setup as infra_mod
    from infrastructure_setup import _env_exists

    captured: dict = {}

    def fake_run(*args, **kwargs):
        captured["env"] = kwargs.get("env", None)
        captured["text"] = kwargs.get("text", None)
        captured["capture_output"] = kwargs.get("capture_output", None)
        return _make_bytes_completed_proc(
            returncode=0,
            stdout=b"# conda environments:\nbase  /x/conda\n",
            stderr=b"",
        )

    monkeypatch.setattr(infra_mod.subprocess, "run", fake_run)

    # Call _env_exists; result is a bool but we only care about kwargs.
    _env_exists("svp-test", "conda")

    assert captured["env"] is not None, (
        "_env_exists MUST pass an env dict to subprocess.run"
    )
    assert captured["env"].get("PYTHONIOENCODING") == "utf-8"
    assert captured["env"].get("PYTHONUTF8") == "1"
    assert captured["text"] in (None, False), (
        "_env_exists subprocess.run MUST NOT use text=True"
    )
    assert captured["capture_output"] is True


# ---------------------------------------------------------------------------
# Site C -- regression-adapt subprocess in run_infrastructure_setup Step 8
# ---------------------------------------------------------------------------


def test_i3_unit_11_regression_adapt_sets_utf8_env_no_text_true(
    monkeypatch, tmp_path
):
    """C-11-I3b: the regression-adapt subprocess in
    run_infrastructure_setup Step 8 MUST set PYTHONIOENCODING=utf-8 +
    PYTHONUTF8=1 AND MUST NOT pass text=True. The adapt_cmd argv list
    starts with sys.executable + the adapt script path + 'regression-adapt'."""
    import infrastructure_setup as infra_mod

    # Seed the regression_test_import_map.json + tests/regressions/ +
    # scripts/generate_assembly_map.py so the Step-8 branch fires.
    (tmp_path / "regression_test_import_map.json").write_text("{}")
    regressions_dir = tmp_path / "tests" / "regressions"
    regressions_dir.mkdir(parents=True)
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    adapt_script = scripts_dir / "generate_assembly_map.py"
    adapt_script.write_text("# placeholder for I-3 regression test")

    captured: list = []

    def fake_run(*args, **kwargs):
        # First arg is the cmd list. Capture every call so we can find the
        # one whose argv contains "regression-adapt".
        cmd = args[0] if args else kwargs.get("args", [])
        captured.append({
            "cmd": list(cmd) if isinstance(cmd, (list, tuple)) else cmd,
            "env": kwargs.get("env", None),
            "text": kwargs.get("text", None),
            "capture_output": kwargs.get("capture_output", None),
        })
        return _make_bytes_completed_proc(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(infra_mod.subprocess, "run", fake_run)

    # Drive run_infrastructure_setup down its Step-8 branch with a minimal
    # blueprint that triggers the post-blueprint flow.
    blueprint_dir = tmp_path / "blueprint"
    blueprint_dir.mkdir()
    (blueprint_dir / "blueprint_contracts.md").write_text(
        "## Unit 1: First\n\n"
        "### Tier 2 — Signatures\n\n"
        "```python\n"
        "def f(): ...\n"
        "```\n"
    )
    (blueprint_dir / "blueprint_prose.md").write_text("")
    (tmp_path / ".svp").mkdir()
    (tmp_path / ".svp" / "pipeline_state.json").write_text(
        json.dumps({"total_units": 0})
    )

    profile = {"language": {"primary": "python"}, "archetype": "python_project"}
    toolchain = {
        "environment": {
            "create": "conda create -n {env_name} -y",
            "install": "conda run -n {env_name} pip install {packages}",
        },
        "language": {"version_constraint": ">=3.11"},
        "quality": {},
    }
    registry = {
        "python": {
            "environment_manager": "conda",
            "file_extension": ".py",
            "toolchain_file": "python_conda_pytest.json",
            "import_syntax": "import {module}",
        }
    }
    monkeypatch.setattr(
        infra_mod, "verify_toolchain_ready", lambda *a, **k: (True, [])
    )

    infra_mod.run_infrastructure_setup(
        project_root=tmp_path,
        profile=profile,
        toolchain=toolchain,
        language_registry=registry,
        blueprint_dir=blueprint_dir,
    )

    # Find the regression-adapt invocation among the captured calls.
    adapt_calls = [
        c for c in captured
        if isinstance(c["cmd"], list)
        and any("regression-adapt" == str(x) for x in c["cmd"])
    ]
    assert adapt_calls, (
        f"Expected at least one regression-adapt subprocess.run call; "
        f"captured={captured!r}"
    )
    call = adapt_calls[0]
    assert call["env"] is not None, (
        "regression-adapt subprocess MUST pass an env dict"
    )
    assert call["env"].get("PYTHONIOENCODING") == "utf-8"
    assert call["env"].get("PYTHONUTF8") == "1"
    assert call["text"] in (None, False), (
        "regression-adapt subprocess.run MUST NOT use text=True"
    )
    assert call["capture_output"] is True


# ---------------------------------------------------------------------------
# Site D -- _list_installed_conda_packages default runner (Unit 11)
# ---------------------------------------------------------------------------


def test_i3_unit_11_list_installed_conda_packages_sets_utf8_env_no_text_true():
    """C-11-I3c: _list_installed_conda_packages MUST pass env override and
    MUST NOT use text=True when invoking its runner. Verified by injecting
    a spy runner directly (no monkeypatch needed)."""
    from infrastructure_setup import _list_installed_conda_packages

    captured: dict = {}

    def spy_runner(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        captured["env"] = kwargs.get("env", None)
        captured["text"] = kwargs.get("text", None)
        captured["capture_output"] = kwargs.get("capture_output", None)
        # json.loads accepts both bytes and str; return a valid empty list.
        return _make_bytes_completed_proc(
            returncode=0, stdout=b"[]", stderr=b""
        )

    _list_installed_conda_packages("svp-test", runner=spy_runner)

    assert captured["env"] is not None, (
        "_list_installed_conda_packages MUST pass env to its runner"
    )
    assert captured["env"].get("PYTHONIOENCODING") == "utf-8"
    assert captured["env"].get("PYTHONUTF8") == "1"
    assert captured["text"] in (None, False), (
        "runner call MUST NOT use text=True"
    )
    assert captured["capture_output"] is True
    # Sanity: the cmd is the conda list --json invocation.
    assert captured["cmd"][0:3] == ["conda", "list", "-n"]


# ---------------------------------------------------------------------------
# Site E -- install_dep_delta conda install runner (Unit 11)
# ---------------------------------------------------------------------------


def test_i3_unit_11_conda_install_sets_utf8_env_no_text_true(
    tmp_path, monkeypatch
):
    """C-11-I3d: the install runner inside install_dep_delta MUST pass
    env override + MUST NOT use text=True. Verified by injecting a spy
    runner directly. S3-202 / J-2a updated the cmd shape from the
    pre-J-2a hardcoded ["conda", "install", ...] to the toolchain-driven
    helper output (canonical Python toolchain default: ["conda", "run",
    ..., "pip", "install", ...]). The I-3 hygiene assertions (env override
    + no-text-true + capture_output) are preserved verbatim."""
    import infrastructure_setup as infra_mod
    from infrastructure_setup import install_dep_delta

    # Seed the pending file with non-empty pkgs so the install branch fires.
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir()
    (svp_dir / "dep_diff_pending.json").write_text(
        json.dumps({"delta_baseline": ["pytest"], "delta_blueprint_only": ["numpy"]})
    )
    # Seed minimal pipeline state so the post-success state save works.
    (svp_dir / "pipeline_state.json").write_text(
        json.dumps({"stage": "pre_stage_3", "toolchain_status": "NOT_READY"})
    )

    # Stub verify_toolchain_ready so it does not actually invoke conda.
    monkeypatch.setattr(
        infra_mod, "verify_toolchain_ready", lambda pr, env: (True, [])
    )

    captured: dict = {}

    def spy_runner(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        captured["env"] = kwargs.get("env", None)
        captured["text"] = kwargs.get("text", None)
        captured["capture_output"] = kwargs.get("capture_output", None)
        # Return a CompletedProcess-shaped MagicMock with bytes stderr so
        # the production isinstance guard exercises the bytes branch on a
        # successful path -- but this test only inspects kwargs.
        return _make_bytes_completed_proc(returncode=0, stdout=b"", stderr=b"")

    install_dep_delta(tmp_path, "svp-test", runner=spy_runner)

    assert captured["env"] is not None, (
        "install_dep_delta MUST pass env to its runner"
    )
    assert captured["env"].get("PYTHONIOENCODING") == "utf-8"
    assert captured["env"].get("PYTHONUTF8") == "1"
    assert captured["text"] in (None, False), (
        "runner call MUST NOT use text=True"
    )
    assert captured["capture_output"] is True
    # S3-202 / J-2a: cmd is now produced by _build_install_command. With
    # no toolchain.json seeded in tmp_path, load_toolchain raises
    # FileNotFoundError -> install_dep_delta falls back to toolchain={} ->
    # _build_install_command falls back to "conda run -n {env_name} pip
    # install {packages}". The captured cmd starts with the conda-run-pip-
    # install shape, NOT the pre-J-2a hardcoded "conda install" shape.
    assert captured["cmd"][0:6] == [
        "conda",
        "run",
        "-n",
        "svp-test",
        "pip",
        "install",
    ], f"expected conda-run-pip-install shape post-J-2a; got {captured['cmd'][0:6]}"


# ---------------------------------------------------------------------------
# Site F -- _run_command quality-gate runner (Unit 15)
# ---------------------------------------------------------------------------


def test_i3_unit_15_run_command_sets_utf8_env_no_text_true_decodes_bytes(
    monkeypatch,
):
    """C-15-I3a: _run_command MUST set PYTHONIOENCODING=utf-8 +
    PYTHONUTF8=1 on env, MUST NOT pass text=True, AND MUST decode bytes
    stdout/stderr with errors='replace' BEFORE returning the
    CompletedProcess (so callers see strings)."""
    import quality_gate as qg_mod
    from quality_gate import _run_command

    captured: dict = {}

    # Bytes containing invalid UTF-8 to verify the errors='replace' decode.
    invalid_utf8 = b"\x9d\xfe ruff output\nE501 line too long\n"

    def fake_run(*args, **kwargs):
        captured["env"] = kwargs.get("env", None)
        captured["text"] = kwargs.get("text", None)
        captured["capture_output"] = kwargs.get("capture_output", None)
        m = MagicMock()
        m.returncode = 0
        m.stdout = invalid_utf8
        m.stderr = b""
        return m

    monkeypatch.setattr(qg_mod.subprocess, "run", fake_run)

    proc = _run_command("ruff check src/")

    # env / kwargs assertions.
    assert captured["env"] is not None, (
        "_run_command MUST pass an env dict to subprocess.run"
    )
    assert captured["env"].get("PYTHONIOENCODING") == "utf-8"
    assert captured["env"].get("PYTHONUTF8") == "1"
    assert captured["text"] in (None, False), (
        "_run_command subprocess.run MUST NOT use text=True"
    )
    assert captured["capture_output"] is True
    # Decoded-bytes assertions: callers see strings.
    assert isinstance(proc.stdout, str), (
        "proc.stdout MUST be str (decoded bytes) after _run_command returns"
    )
    assert isinstance(proc.stderr, str), (
        "proc.stderr MUST be str (decoded bytes) after _run_command returns"
    )


# ---------------------------------------------------------------------------
# Cross-cutting AST guard
# ---------------------------------------------------------------------------


# Map of (unit, function name predicate) for the six audited sites. The
# predicate matches a top-level function name OR an enclosing function
# context for a nested-def / inline subprocess.run call.
_AUDITED_FUNCTIONS: dict[int, set[str]] = {
    4: {"_default_runner", "verify_toolchain_ready"},
    11: {
        "_env_exists",
        "run_infrastructure_setup",
        "_list_installed_conda_packages",
        "install_dep_delta",
    },
    15: {"_run_command"},
}


def _walk_subprocess_run_calls(tree: ast.AST,
                               target_function_names: set[str]) -> list[ast.Call]:
    """Walk the AST and collect every Call whose func is `subprocess.run`
    AND that lives inside (or is) one of the target function names. Nested
    inner functions (e.g. `_default_runner` inside `verify_toolchain_ready`)
    are matched via either name."""
    matches: list[ast.Call] = []

    class FunctionContextVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.context_stack: list[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.context_stack.append(node.name)
            self.generic_visit(node)
            self.context_stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.context_stack.append(node.name)
            self.generic_visit(node)
            self.context_stack.pop()

        def visit_Call(self, node: ast.Call) -> None:
            # Detect subprocess.run(...) calls.
            is_subprocess_run = (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "run"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "subprocess"
            )
            if is_subprocess_run and any(
                name in target_function_names for name in self.context_stack
            ):
                matches.append(node)
            self.generic_visit(node)

    FunctionContextVisitor().visit(tree)
    return matches


def test_i3_no_text_true_remaining_in_targeted_files() -> None:
    """Cross-cutting guard: walk the three stub files and assert no
    `subprocess.run(..., text=True)` remains inside any of the six audited
    function bodies. If a future cycle re-introduces text=True at any of
    these sites, this test fails with a precise pointer."""
    failures: list[str] = []

    for unit, target_names in _AUDITED_FUNCTIONS.items():
        path = _stub_path(unit)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        for call in _walk_subprocess_run_calls(tree, target_names):
            for kw in call.keywords:
                if kw.arg == "text":
                    # Only reject text=True (constant boolean True).
                    if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        failures.append(
                            f"src/unit_{unit}/stub.py line {call.lineno}: "
                            f"`subprocess.run(..., text=True)` remains in an "
                            f"audited function (one of {sorted(target_names)})"
                        )

    assert not failures, (
        "Cycle I-3 / S3-200 cp1252 hygiene sweep regression:\n"
        + "\n".join(failures)
        + "\n\nDrop text=True at the listed site and decode bytes manually "
          "with errors='replace' (see Pattern P84 in references/svp_2_1_lessons_learned.md)."
    )

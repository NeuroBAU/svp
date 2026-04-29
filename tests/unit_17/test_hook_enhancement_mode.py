"""Cycle G3 (S3-188) regression tests for hook write-policy under
enhancement mode. The deployed write_authorization.sh hook MUST permit
writes to specs/, blueprint/, references/, .svp/ when
debug_session.mode == "enhancement", and MUST DENY them when mode == "bug".

These tests invoke the deployed bash hook in a subprocess with a fake
.svp/pipeline_state.json fixture in tmp_path and assert the exit code.

Exit code 0 = permit; exit code 2 = deny (BLOCKED).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Path resolvers (dual-layout: workspace OR repo)
# ---------------------------------------------------------------------------


def _find_workspace_or_repo_root() -> Path:
    """Walk up from this test file to find a root that contains
    ``svp/hooks/write_authorization.sh``. Both workspace and repo layouts
    deploy the script at the same relative path under ``svp/hooks/`` after
    sync.

    The repo layout has ``svp/hooks/write_authorization.sh`` directly under
    the repo root. The workspace layout has no ``svp/`` of its own and
    sits next to a sibling repo. The sibling-repo convention is
    ``<workspace_name>-repo`` (e.g., ``svp2.2-pass2`` → ``svp2.2-pass2-repo``);
    multiple ``*-repo`` siblings may exist under the same parent (legacy or
    upstream repos), so the resolver prefers the name-matched sibling and
    falls back to any ``*-repo`` whose deployed hook is found.
    """
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        # (a) repo layout: ancestor itself contains svp/hooks/.
        candidate = parent / "svp" / "hooks" / "write_authorization.sh"
        if candidate.is_file():
            return parent
        # (b) workspace layout: look for sibling repo, preferring the
        # name-matched ``<parent>-repo`` first.
        if parent.parent is None or parent.parent == parent:
            continue
        preferred = parent.parent / f"{parent.name}-repo"
        preferred_hook = preferred / "svp" / "hooks" / "write_authorization.sh"
        if preferred_hook.is_file():
            return preferred
        try:
            for sibling in parent.parent.glob("*-repo"):
                sibling_candidate = (
                    sibling / "svp" / "hooks" / "write_authorization.sh"
                )
                if sibling_candidate.is_file():
                    return sibling
        except OSError:
            pass
    raise RuntimeError(
        f"Could not locate svp/hooks/write_authorization.sh from {here}"
    )


def _hook_script_path() -> Path:
    """Resolve the deployed write_authorization.sh path."""
    return _find_workspace_or_repo_root() / "svp" / "hooks" / "write_authorization.sh"


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _make_state_file(tmp_path: Path, mode: str, authorized: bool = True) -> None:
    """Create a minimal .svp/pipeline_state.json under tmp_path with
    debug_session set to the given mode and authorization.
    """
    svp_dir = tmp_path / ".svp"
    svp_dir.mkdir(parents=True, exist_ok=True)
    # NOTE: stage="0" is chosen deliberately. The hook's Stage-gated
    # authorization (Stages 4/5) unconditionally permits writes to
    # specs/blueprint/references regardless of debug mode; only Stages
    # 0/1/2/pre_stage_3 BLOCK those paths via stage gating, isolating the
    # debug-session permit logic this test is designed to exercise. With
    # stage="0", a write to specs/ under mode=bug falls through the debug
    # block, hits the stage-0 BLOCKED case, and exits 2 (deny). Under
    # mode=enhancement, the new G3 enhancement-mode permit branch inside
    # the debug block matches first and exits 0 (permit) before stage
    # gating runs. The test thereby asserts the debug-session contract
    # cleanly.
    #
    # NOTE 2: every field that the hook's python f-string interpolates
    # with an `or "_"` fallback is given a non-empty string here. The
    # deployed hook embeds python inside `python3 -c "..."` and the inner
    # `"_"` literal does not survive bash quote-stripping intact (it is
    # parsed as the bare identifier `_`). At runtime the literal `_` is
    # only evaluated for empty-string fields (short-circuit on truthy);
    # we therefore set every field to a truthy placeholder so the python
    # parse short-circuits on every fallback and produces output.
    state = {
        "stage": "0",
        "sub_stage": "project_context",
        "current_unit": 1,
        "total_units": 10,
        "verified_units": [],
        "alignment_iterations": 0,
        "fix_ladder_position": None,
        "red_run_retries": 0,
        "pass_history": [],
        "debug_session": {
            "authorized": authorized,
            "bug_number": 0,
            "classification": "single_unit",
            "affected_units": [1],
            "phase": "triage",
            "repair_retry_count": 0,
            "triage_refinement_count": 0,
            "ledger_path": None,
            "mode": mode,
            "source": "human_authorize",
        },
        "debug_history": [],
        "redo_triggered_from": None,
        "delivered_repo_path": "/tmp/nonexistent-delivered-repo",
        "primary_language": "python",
        "component_languages": [],
        "secondary_language": None,
        "oracle_session_active": False,
        "oracle_test_project": None,
        "oracle_phase": "exit",
        "oracle_run_count": 0,
        "oracle_nested_session_path": None,
        "state_hash": None,
        "spec_revision_count": 0,
        "pass": None,
        "pass2_nested_session_path": None,
        "deferred_broken_units": [],
    }
    (svp_dir / "pipeline_state.json").write_text(json.dumps(state))


def _invoke_hook(
    tmp_path: Path,
    file_path: str,
    mode: str,
    authorized: bool = True,
) -> subprocess.CompletedProcess:
    """Subprocess: bash svp/hooks/write_authorization.sh with the hook's
    stdin tool-input JSON. CWD is tmp_path so the hook reads the fake
    .svp/pipeline_state.json relative to CWD.
    """
    _make_state_file(tmp_path, mode=mode, authorized=authorized)
    script = _hook_script_path()
    tool_input = json.dumps({"tool_input": {"file_path": file_path}})
    return subprocess.run(
        ["bash", str(script)],
        input=tool_input,
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_hook_permits_specs_write_in_enhancement_mode(tmp_path: Path) -> None:
    """mode=enhancement, authorized=True -> writing to specs/foo.md is permitted (exit 0)."""
    result = _invoke_hook(
        tmp_path, file_path="specs/foo.md", mode="enhancement", authorized=True
    )
    assert result.returncode == 0, (
        f"Expected exit 0 (permit) for specs/foo.md under enhancement mode; "
        f"got returncode={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_hook_denies_specs_write_in_bug_mode(tmp_path: Path) -> None:
    """mode=bug, authorized=True -> writing to specs/foo.md is denied (exit non-zero)."""
    result = _invoke_hook(
        tmp_path, file_path="specs/foo.md", mode="bug", authorized=True
    )
    assert result.returncode != 0, (
        f"Expected non-zero exit (deny) for specs/foo.md under bug mode; "
        f"got returncode={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_hook_permits_blueprint_write_in_enhancement_mode(tmp_path: Path) -> None:
    """mode=enhancement -> writing to blueprint/blueprint_contracts.md is permitted."""
    result = _invoke_hook(
        tmp_path,
        file_path="blueprint/blueprint_contracts.md",
        mode="enhancement",
        authorized=True,
    )
    assert result.returncode == 0, (
        f"Expected exit 0 (permit) for blueprint/blueprint_contracts.md under "
        f"enhancement mode; got returncode={result.returncode} "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_hook_denies_blueprint_write_in_bug_mode(tmp_path: Path) -> None:
    """mode=bug -> writing to blueprint/blueprint_contracts.md is denied."""
    result = _invoke_hook(
        tmp_path,
        file_path="blueprint/blueprint_contracts.md",
        mode="bug",
        authorized=True,
    )
    assert result.returncode != 0, (
        f"Expected non-zero exit (deny) for blueprint/blueprint_contracts.md under "
        f"bug mode; got returncode={result.returncode} "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )

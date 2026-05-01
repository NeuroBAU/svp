"""Cycle J-2 (S3-202) -- env-section template helper alignment.

Four surgical fixes shipped together as an audit-and-broaden cycle (Pattern
P87). All four sites in Units 11 and 16 now read the canonical
environment-section schema keys per references/toolchain_manifest_schema.md:

(a) J-2a: install_dep_delta (Unit 11) now constructs the install command
    via the existing _build_install_command helper rather than hardcoding
    the conda install verb.
(b) J-2b: _build_install_command (Unit 11) now reads
    environment.install_command (was: environment.install).
(c) J-2c: _build_env_create_command (Unit 11, both branches) now reads
    environment.create_command (was: environment.create).
(d) J-2d: cmd_clean (Unit 16) now reads environment.cleanup_command (was:
    a two-step lookup of commands.env_remove then environment.remove --
    both dead/wrong keys).

S3-103 flat-module imports.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from infrastructure_setup import (
    _build_env_create_command,
    _build_install_command,
    install_dep_delta,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeProc:
    """Synthetic CompletedProcess-shaped object."""

    def __init__(self, returncode=0, stdout=b"", stderr=b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _seed_pending(project_root: Path, baseline=None, blueprint_only=None):
    """Write .svp/dep_diff_pending.json and pipeline_state.json."""
    svp_dir = project_root / ".svp"
    svp_dir.mkdir(parents=True, exist_ok=True)
    pending = {
        "delta_baseline": baseline or [],
        "delta_blueprint_only": blueprint_only or [],
    }
    (svp_dir / "dep_diff_pending.json").write_text(json.dumps(pending))
    state = {"stage": "pre_stage_3", "toolchain_status": "NOT_READY"}
    (svp_dir / "pipeline_state.json").write_text(json.dumps(state))


def _seed_profile(project_root: Path, primary_lang: str = "python") -> None:
    profile = {
        "language": {"primary": primary_lang},
        "archetype": f"{primary_lang}_project",
    }
    (project_root / "project_profile.json").write_text(json.dumps(profile))


def _seed_toolchain(project_root: Path, toolchain: dict) -> None:
    """Write toolchain.json at the project root.

    Note: Layer-1 pipeline-level toolchain.json is read by
    ``load_toolchain(project_root)`` (no language arg). Layer-2
    language-specific defaults at scripts/toolchain_defaults/ are read
    by ``load_toolchain(project_root, language="python")``.
    install_dep_delta uses the Layer-2 path -- see ``_seed_lang_toolchain``.
    """
    (project_root / "toolchain.json").write_text(json.dumps(toolchain))


def _seed_lang_toolchain(
    project_root: Path, toolchain: dict, language: str = "python"
) -> None:
    """Write a Layer-2 language-specific default toolchain JSON.

    install_dep_delta calls ``load_toolchain(project_root,
    language=primary_lang)`` which mirrors ``compute_dep_diff``: this is
    Layer 2, reading from
    ``<project_root>/scripts/toolchain_defaults/<toolchain_file>`` per
    LANGUAGE_REGISTRY. Seed both paths so both styles of test work."""
    from language_registry import LANGUAGE_REGISTRY

    toolchain_file = LANGUAGE_REGISTRY[language]["toolchain_file"]
    target = project_root / "scripts" / "toolchain_defaults" / toolchain_file
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(toolchain))


def _python_toolchain_with_install_command(install_command: str) -> dict:
    return {
        "toolchain_id": "python_conda_pytest",
        "environment": {
            "tool": "conda",
            "run_prefix": "conda run -n {env_name}",
            "create_command": "conda create -n {env_name} python={python_version} -y",
            "install_command": install_command,
            "cleanup_command": "conda env remove -n {env_name} -y",
        },
        "language": {"name": "python", "version_constraint": ">=3.9"},
        "testing": {"framework_packages": ["pytest"]},
        "quality": {"packages": ["ruff", "mypy"]},
    }


# ---------------------------------------------------------------------------
# J-2a -- install_dep_delta uses _build_install_command (4 tests)
# ---------------------------------------------------------------------------


def test_j2a_install_dep_delta_uses_build_install_command(
    tmp_path, monkeypatch
):
    """C-11-J2a: install_dep_delta MUST construct the install command via
    _build_install_command, NOT hardcode ``conda install -n env -y pkgs``.
    With the canonical Python toolchain (install_command = ``conda run -n
    {env_name} pip install {packages}``), the captured cmd starts with
    ``["conda", "run", "-n", env, "pip", "install"]`` after the fix --
    NEVER ``["conda", "install", "-n", env, "-y"]`` which was the buggy
    pre-J-2a hardcoded shape."""
    import infrastructure_setup as infra_mod

    _seed_pending(tmp_path, baseline=["pytest"], blueprint_only=["numpy"])
    _seed_profile(tmp_path)
    _seed_lang_toolchain(
        tmp_path,
        _python_toolchain_with_install_command(
            "conda run -n {env_name} pip install {packages}"
        ),
    )

    monkeypatch.setattr(
        infra_mod, "verify_toolchain_ready", lambda pr, env: (True, [])
    )

    captured = {}

    def spy_runner(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return _FakeProc(returncode=0)

    install_dep_delta(tmp_path, "svp-test", runner=spy_runner)

    assert "cmd" in captured, "spy_runner MUST be called when pkgs non-empty"
    cmd = captured["cmd"]
    # Post-fix: the helper-built command starts with conda run pip install.
    assert cmd[0:6] == [
        "conda",
        "run",
        "-n",
        "svp-test",
        "pip",
        "install",
    ], f"expected conda-run-pip-install shape, got {cmd[0:6]}"
    # Pre-fix shape MUST NOT appear.
    assert cmd[0:5] != ["conda", "install", "-n", "svp-test", "-y"], (
        "install_dep_delta MUST NOT use the hardcoded conda install shape "
        "after J-2a"
    )
    # Both packages were unioned into the args.
    assert "pytest" in cmd and "numpy" in cmd


def test_j2a_install_dep_delta_honors_toolchain_install_command_override(
    tmp_path, monkeypatch
):
    """C-11-J2a: when the toolchain JSON specifies a non-default
    install_command (e.g. mamba), install_dep_delta MUST honor it through
    the _build_install_command helper. Pre-J-2a this would have FAILED
    because the hardcoded conda-install shape ignored the toolchain
    override entirely."""
    import infrastructure_setup as infra_mod

    _seed_pending(tmp_path, blueprint_only=["gseapy"])
    _seed_profile(tmp_path)
    _seed_lang_toolchain(
        tmp_path,
        _python_toolchain_with_install_command(
            "mamba install -n {env_name} -y {packages}"
        ),
    )

    monkeypatch.setattr(
        infra_mod, "verify_toolchain_ready", lambda pr, env: (True, [])
    )

    captured = {}

    def spy_runner(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return _FakeProc(returncode=0)

    install_dep_delta(tmp_path, "svp-test", runner=spy_runner)

    cmd = captured["cmd"]
    assert cmd[0] == "mamba", (
        f"toolchain install_command override MUST be honored; got {cmd}"
    )
    assert cmd[0:5] == ["mamba", "install", "-n", "svp-test", "-y"]
    assert "gseapy" in cmd


def test_j2a_install_dep_delta_propagates_install_failure_with_decoded_stderr(
    tmp_path, monkeypatch
):
    """C-11-J2a + C-11-I3d: install_dep_delta returns (False, [...]) when
    the install command exits non-zero; bytes stderr is decoded with
    errors=replace before the error f-string. The I-3 cp1252 hygiene
    block is preserved bit-for-bit by J-2a (only the cmd-construction
    line and the f-string label change)."""
    import infrastructure_setup as infra_mod

    _seed_pending(tmp_path, blueprint_only=["nonexistent_pkg"])
    _seed_profile(tmp_path)
    _seed_lang_toolchain(
        tmp_path,
        _python_toolchain_with_install_command(
            "conda run -n {env_name} pip install {packages}"
        ),
    )

    monkeypatch.setattr(
        infra_mod, "verify_toolchain_ready", lambda pr, env: (True, [])
    )

    # Non-UTF-8 byte sequence in stderr to exercise errors=replace decode.
    bad_stderr = b"\xff\xfe error finding package\n"

    def failing_runner(cmd, **kwargs):
        # Verify env override is passed (I-3 hygiene preserved).
        env = kwargs.get("env", {})
        assert env.get("PYTHONIOENCODING") == "utf-8"
        assert env.get("PYTHONUTF8") == "1"
        return _FakeProc(returncode=1, stderr=bad_stderr)

    ok, errors = install_dep_delta(tmp_path, "svp-test", runner=failing_runner)
    assert ok is False
    assert errors and len(errors) >= 1
    # The error f-string MUST use the new "install command exited" label
    # (J-2a updated this from "conda install exited" since the cmd is no
    # longer guaranteed to be conda).
    assert any("install command exited 1" in e for e in errors), errors
    # Pending file preserved on failure.
    assert (tmp_path / ".svp" / "dep_diff_pending.json").exists()


def test_j2a_install_dep_delta_skips_install_when_pkgs_empty(
    tmp_path, monkeypatch
):
    """C-11-J2a: empty deltas short-circuit the install branch entirely;
    the runner is NOT called for install (it may still be called by
    verify_toolchain_ready, but that is stubbed here). Pending file is
    removed and state advanced to READY on the empty-deltas fast path."""
    import infrastructure_setup as infra_mod

    _seed_pending(tmp_path, baseline=[], blueprint_only=[])
    _seed_profile(tmp_path)
    _seed_lang_toolchain(
        tmp_path,
        _python_toolchain_with_install_command(
            "conda run -n {env_name} pip install {packages}"
        ),
    )

    monkeypatch.setattr(
        infra_mod, "verify_toolchain_ready", lambda pr, env: (True, [])
    )

    install_calls = []

    def spy_runner(cmd, **kwargs):
        install_calls.append(list(cmd))
        return _FakeProc(returncode=0)

    ok, errors = install_dep_delta(tmp_path, "svp-test", runner=spy_runner)
    assert ok is True
    assert errors == []
    # No install was attempted because pkgs was empty.
    assert install_calls == []
    # Pending file removed after success.
    assert not (tmp_path / ".svp" / "dep_diff_pending.json").exists()


# ---------------------------------------------------------------------------
# J-2b -- _build_install_command reads canonical install_command key (3 tests)
# ---------------------------------------------------------------------------


def test_j2b_build_install_command_reads_install_command_key():
    """C-11-J2b: _build_install_command MUST read the canonical
    environment.install_command schema key. Pre-J-2b it read
    environment.install which never matched, silently falling back."""
    toolchain = {
        "environment": {
            "install_command": "x {env_name} y {packages}",
        }
    }
    result = _build_install_command("svp-env", ["pkg1", "pkg2"], toolchain)
    assert result == "x svp-env y pkg1 pkg2", (
        f"helper MUST honor environment.install_command; got {result!r}"
    )


def test_j2b_build_install_command_falls_back_when_install_command_absent():
    """C-11-J2b: when the canonical key is absent, the helper MUST fall
    back to the documented default template (preserved for backward
    compat with toolchains missing the key)."""
    toolchain = {"environment": {}}
    result = _build_install_command("env1", ["pkg1", "pkg2"], toolchain)
    assert result == "conda run -n env1 pip install pkg1 pkg2", (
        f"unexpected fallback shape: {result!r}"
    )


def test_j2b_build_install_command_returns_empty_for_empty_packages():
    """C-11-J2b: empty packages list MUST short-circuit to empty string
    (existing guard at the top of the helper, preserved by J-2b)."""
    toolchain = {
        "environment": {
            "install_command": "conda install -n {env_name} -y {packages}",
        }
    }
    assert _build_install_command("env1", [], toolchain) == ""


# ---------------------------------------------------------------------------
# J-2c -- _build_env_create_command reads canonical create_command (2 tests)
# ---------------------------------------------------------------------------


def test_j2c_build_env_create_command_reads_create_command_key():
    """C-11-J2c: _build_env_create_command MUST read the canonical
    environment.create_command schema key. Pre-J-2c it read
    environment.create which never matched, silently falling back to
    the default ``conda create -n {env_name} python={python_version}``
    shape and ignoring archetype-specific create_command overrides
    (e.g. R-conda's ``-c conda-forge`` channel selection)."""
    toolchain = {
        "environment": {
            "create_command": "x {env_name} y {python_version}",
        },
        "language": {"version_constraint": ">=3.10"},
    }
    profile = {"archetype": "python_project"}
    language_registry = {
        "python": {"environment_manager": "conda"},
    }
    result = _build_env_create_command(
        env_name="svp-env",
        toolchain=toolchain,
        profile=profile,
        language_registry=language_registry,
        primary_language="python",
        project_root=Path("/tmp/synthetic"),
    )
    assert result["commands"], "expected at least one create command"
    create_cmd = result["commands"][0]
    assert create_cmd == "x svp-env y 3.10", (
        f"helper MUST honor environment.create_command override; got "
        f"{create_cmd!r}"
    )


def test_j2c_build_env_create_command_falls_back_when_create_command_absent():
    """C-11-J2c: when the canonical key is absent, the helper MUST fall
    back to the documented default template (preserved for backward
    compat with toolchains missing the key)."""
    toolchain = {
        "environment": {},
        "language": {"version_constraint": ">=3.11"},
    }
    profile = {"archetype": "python_project"}
    language_registry = {
        "python": {"environment_manager": "conda"},
    }
    result = _build_env_create_command(
        env_name="env1",
        toolchain=toolchain,
        profile=profile,
        language_registry=language_registry,
        primary_language="python",
        project_root=Path("/tmp/synthetic"),
    )
    assert result["commands"], "expected at least one create command"
    create_cmd = result["commands"][0]
    assert create_cmd == "conda create -n env1 python=3.11 -y", (
        f"unexpected fallback shape: {create_cmd!r}"
    )


# ---------------------------------------------------------------------------
# J-2d -- cmd_clean reads canonical cleanup_command key (2 tests)
# ---------------------------------------------------------------------------


def test_j2d_cmd_clean_reads_cleanup_command_key(tmp_path, monkeypatch):
    """C-16-J2d: cmd_clean MUST look up its env-remove subprocess command
    via the canonical environment.cleanup_command key. Synthetic
    toolchain.json with cleanup_command = "echo TEST_REMOVE_{env_name}";
    monkeypatch subprocess.run with a spy; assert the spy received the
    resolved cleanup template, NOT the dead commands.env_remove path or
    the wrong environment.remove fallback."""
    import sync_debug_docs as sdd_mod
    from sync_debug_docs import cmd_clean

    project_root = tmp_path / "proj"
    project_root.mkdir()
    svp_dir = project_root / ".svp"
    svp_dir.mkdir()
    state = {"stage": "5", "delivered_repo_path": None}
    (svp_dir / "pipeline_state.json").write_text(json.dumps(state))

    toolchain = {
        "environment": {
            "tool": "conda",
            "run_prefix": "conda run -n {env_name}",
            "create_command": "conda create -n {env_name} -y",
            "install_command": "conda run -n {env_name} pip install {packages}",
            "cleanup_command": "echo TEST_REMOVE_{env_name}",
        },
    }

    # Stub upstream loaders.
    monkeypatch.setattr(sdd_mod, "load_toolchain", lambda pr: toolchain)
    monkeypatch.setattr(sdd_mod, "load_state", lambda pr: MagicMock())
    monkeypatch.setattr(
        sdd_mod, "derive_env_name", lambda pr: "svp-cleanup-test"
    )
    monkeypatch.setattr(
        sdd_mod,
        "resolve_command",
        lambda template, env_name, run_prefix: template.replace(
            "{env_name}", env_name
        ),
    )

    captured = {}

    def spy_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["shell"] = kwargs.get("shell")
        return MagicMock(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(sdd_mod.subprocess, "run", spy_run)

    cmd_clean(project_root, "keep")

    assert "cmd" in captured, "cmd_clean MUST invoke subprocess.run"
    assert captured["cmd"] == "echo TEST_REMOVE_svp-cleanup-test", (
        f"cmd_clean MUST resolve environment.cleanup_command; got "
        f"{captured['cmd']!r}"
    )


def test_j2d_cmd_clean_does_not_read_dead_commands_env_remove_namespace(
    tmp_path, monkeypatch
):
    """C-16-J2d: when a synthetic toolchain has BOTH the dead
    commands.env_remove key AND the canonical environment.cleanup_command
    key, cmd_clean MUST resolve only the canonical cleanup_command path.
    The dead commands.env_remove namespace MUST NOT be consulted (it was
    a non-canonical key per the schema; no production toolchain JSON
    populates it)."""
    import sync_debug_docs as sdd_mod
    from sync_debug_docs import cmd_clean

    project_root = tmp_path / "proj"
    project_root.mkdir()
    svp_dir = project_root / ".svp"
    svp_dir.mkdir()
    (svp_dir / "pipeline_state.json").write_text(
        json.dumps({"stage": "5", "delivered_repo_path": None})
    )

    toolchain = {
        # Dead namespace -- must not be consulted.
        "commands": {"env_remove": "should_not_run {env_name}"},
        "environment": {
            "tool": "conda",
            "run_prefix": "conda run -n {env_name}",
            "create_command": "conda create -n {env_name} -y",
            "install_command": "conda run -n {env_name} pip install {packages}",
            "cleanup_command": "should_run {env_name}",
            # Wrong fallback key -- must not be consulted either.
            "remove": "should_not_run_either {env_name}",
        },
    }

    monkeypatch.setattr(sdd_mod, "load_toolchain", lambda pr: toolchain)
    monkeypatch.setattr(sdd_mod, "load_state", lambda pr: MagicMock())
    monkeypatch.setattr(
        sdd_mod, "derive_env_name", lambda pr: "svp-dead-namespace-test"
    )
    monkeypatch.setattr(
        sdd_mod,
        "resolve_command",
        lambda template, env_name, run_prefix: template.replace(
            "{env_name}", env_name
        ),
    )

    captured = {}

    def spy_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return MagicMock(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(sdd_mod.subprocess, "run", spy_run)

    cmd_clean(project_root, "keep")

    assert "cmd" in captured, "cmd_clean MUST invoke subprocess.run"
    cmd = captured["cmd"]
    assert "should_run" in cmd and "should_not_run" not in cmd, (
        f"cmd_clean MUST resolve only environment.cleanup_command; got "
        f"{cmd!r}"
    )
    assert cmd == "should_run svp-dead-namespace-test"

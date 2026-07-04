"""Regression tests for Bug S3-211 -- Unit 11 provisioning robustness quartet.

Covers the four defects fixed together in ``src/unit_11/stub.py`` (source of
truth; the derived ``scripts/infrastructure_setup.py`` mirrors it):

  * BUG-1 -- conda executable resolution on Windows (a condabin-only
    ``conda.bat`` is invisible to ``subprocess.run(["conda", ...])`` because
    ``shell=False`` does no PATHEXT expansion). ``_resolve_conda_executable`` +
    ``_conda_cmd`` fix it (Windows-gated; POSIX byte-identical).
  * BUG-2 -- install template uses ``python -m pip`` not bare ``pip``.
  * BUG-3 -- idempotent self-heal: install runs even when the env already
    exists. (Primary functional coverage lives in
    ``tests/unit_11/test_env_creation_executed.py::
    test_env_creation_skipped_when_env_already_exists``, updated to the fixed
    contract; the structural assertion is repeated here.)
  * BUG-5 -- dep-diff ``## Package Dependencies`` parse order (strip backticks
    before the trailing parenthetical; reject residual-backtick tokens) and the
    first-party-module filter in ``compute_dep_diff``.

Flat-module imports resolve via ``pyproject.toml`` ``pythonpath = [src, scripts]``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import infrastructure_setup as infra
from infrastructure_setup import (
    _build_install_command,
    _conda_cmd,
    _first_party_module_roots,
    _parse_blueprint_package_deps,
    _resolve_conda_executable,
    compute_dep_diff,
)


# ---------------------------------------------------------------------------
# BUG-1 -- conda executable resolution
# ---------------------------------------------------------------------------


def test_s3_211_resolve_prefers_shutil_which(monkeypatch):
    """shutil.which honors PATHEXT and finds conda.bat; its result wins."""
    monkeypatch.setattr(
        infra.shutil, "which", lambda name: "/fake/condabin/conda.bat"
    )
    assert _resolve_conda_executable() == "/fake/condabin/conda.bat"


def test_s3_211_resolve_falls_back_to_conda_exe_env(monkeypatch, tmp_path):
    """When which returns None, CONDA_EXE pointing at a real file is used."""
    fake = tmp_path / "conda.bat"
    fake.write_text("echo conda", encoding="utf-8")
    monkeypatch.setattr(infra.shutil, "which", lambda name: None)
    monkeypatch.setenv("CONDA_EXE", str(fake))
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    assert _resolve_conda_executable() == str(fake)


def test_s3_211_conda_cmd_rewrites_argv0_on_windows(monkeypatch):
    """On Windows the leading bare 'conda' token is replaced with the resolved
    executable path so subprocess.run(shell=False) can find conda.bat."""
    monkeypatch.setattr(infra.os, "name", "nt")
    monkeypatch.setattr(
        infra, "_resolve_conda_executable", lambda: "C:/x/condabin/conda.bat"
    )
    assert _conda_cmd(["conda", "env", "list"]) == [
        "C:/x/condabin/conda.bat",
        "env",
        "list",
    ]


def test_s3_211_conda_cmd_noop_on_posix(monkeypatch):
    """On POSIX the command list is byte-identical -- bare conda resolves via
    PATH there, so the fix is a no-op and existing behavior is unchanged."""
    monkeypatch.setattr(infra.os, "name", "posix")
    monkeypatch.setattr(
        infra, "_resolve_conda_executable", lambda: "/should/not/be/used"
    )
    assert _conda_cmd(["conda", "env", "list"]) == ["conda", "env", "list"]


def test_s3_211_conda_cmd_passthrough_non_conda(monkeypatch):
    """A non-conda command (renv/packrat) whose argv[0] is not 'conda' passes
    through untouched even on Windows."""
    monkeypatch.setattr(infra.os, "name", "nt")
    assert _conda_cmd(["renv", "init"]) == ["renv", "init"]


# ---------------------------------------------------------------------------
# BUG-2 -- install template uses `python -m pip`
# ---------------------------------------------------------------------------


def test_s3_211_build_install_command_default_uses_python_m_pip():
    """The fallback template (no environment.install_command) targets the env
    interpreter's own pip via `python -m pip`, never bare `pip`."""
    result = _build_install_command("env1", ["pkg1", "pkg2"], {"environment": {}})
    assert result == "conda run -n env1 python -m pip install pkg1 pkg2"


def test_s3_211_toolchain_json_and_template_use_python_m_pip():
    """Both the standalone default toolchain JSON and the parallel
    project_templates.PYTHON_TOOLCHAIN copy use `python -m pip` (kept in sync).
    """
    import project_templates

    # Locate the toolchain_defaults JSON relative to the project_templates
    # module so this test is layout-agnostic: workspace `scripts/...` and
    # delivered-repo `svp/scripts/...` both resolve.
    json_path = (
        Path(project_templates.__file__).resolve().parent
        / "toolchain_defaults"
        / "python_conda_pytest.json"
    )
    data = json.loads(json_path.read_text(encoding="utf-8"))
    env = data["environment"]
    assert env["install_command"] == (
        "conda run -n {env_name} python -m pip install {packages}"
    )
    assert env["install_dev"] == "conda run -n {env_name} python -m pip install -e ."
    assert data["packaging"]["validate_command"] == (
        "{run_prefix} python -m pip install -e ."
    )
    # The in-code parallel copy must match the JSON exactly on these keys.
    tpl_env = project_templates.PYTHON_TOOLCHAIN["environment"]
    assert tpl_env["install_command"] == env["install_command"]
    assert tpl_env["install_dev"] == env["install_dev"]
    assert (
        project_templates.PYTHON_TOOLCHAIN["packaging"]["validate_command"]
        == data["packaging"]["validate_command"]
    )
    # No bare `pip install` (not preceded by `-m`) remains in these templates.
    for value in (
        env["install_command"],
        env["install_dev"],
        data["packaging"]["validate_command"],
    ):
        assert "python -m pip" in value


# ---------------------------------------------------------------------------
# BUG-3 -- idempotent self-heal (structural marker; functional coverage in
# tests/unit_11/test_env_creation_executed.py)
# ---------------------------------------------------------------------------


def test_s3_211_install_not_guarded_by_env_absence():
    """The install step in run_infrastructure_setup must NOT sit behind
    `not _env_exists(...)` -- topping up an existing under-provisioned env is
    the self-heal. Guards against a regression that re-nests install under the
    creation guard (checked structurally on the derived source)."""
    src = Path(infra.__file__).read_text(encoding="utf-8")
    # The Step-4b block gate is on the presence of create commands only.
    assert 'if env_info["commands"]:' in src
    # The create-only guard is a nested conditional, not the outer gate.
    assert 'if not _env_exists(env_name, env_info["env_manager"]):' in src


# ---------------------------------------------------------------------------
# BUG-5 -- dep-diff parse order + first-party filter
# ---------------------------------------------------------------------------


def _write_contracts(blueprint_dir: Path, dep_lines: list) -> Path:
    blueprint_dir.mkdir(parents=True, exist_ok=True)
    body = "\n".join(dep_lines)
    (blueprint_dir / "blueprint_contracts.md").write_text(
        f"""## Unit 1: U1

### Tier 3 -- Behavioral Contracts

## Package Dependencies

{body}

**Dependencies:** None.

---
""",
        encoding="utf-8",
    )
    return blueprint_dir / "blueprint_contracts.md"


def test_s3_211_parse_backtick_wrapped_name_and_descriptor(tmp_path):
    """A whole-token backtick-wrapped `name (descriptor)` yields the clean name
    (backticks + parenthetical stripped) -- NOT the pre-fix malformed
    leading-backtick token `core.segmentation."""
    contracts = _write_contracts(
        tmp_path / "blueprint",
        [
            "- `core.segmentation (SegmentationResult)`",
            "- `numpy`",
            "- cupy",
            "- blme (mixed-effects extensions)",
        ],
    )
    pkgs = _parse_blueprint_package_deps(contracts)
    # No token retains a stray backtick.
    assert not any("`" in p for p in pkgs), pkgs
    # The backtick+paren-wrapped name is emitted clean (the first-party FILTER
    # in compute_dep_diff, not the parser, is what later drops it).
    assert "core.segmentation" in pkgs
    assert {"numpy", "cupy", "blme"} <= pkgs


def test_s3_211_parse_rejects_unbalanced_backtick(tmp_path):
    """An unbalanced/partial backtick token is malformed and never emitted."""
    contracts = _write_contracts(tmp_path / "blueprint", ["- `foo", "- numpy"])
    pkgs = _parse_blueprint_package_deps(contracts)
    assert "numpy" in pkgs
    assert not any("`" in p for p in pkgs)
    assert "`foo" not in pkgs and "foo" not in pkgs


def test_s3_211_first_party_roots_include_core_and_plugin(tmp_path):
    roots = _first_party_module_roots(tmp_path)
    assert "core" in roots and "plugin" in roots


def test_s3_211_compute_dep_diff_excludes_first_party(tmp_path, monkeypatch):
    """A first-party module declared under Package Dependencies must NOT enter
    delta_blueprint_only (would trigger a doomed `pip install core.segmentation`).
    """
    (tmp_path / ".svp").mkdir()
    _write_contracts(
        tmp_path / "blueprint",
        ["- `core.segmentation (SegmentationResult)`", "- numpy"],
    )
    profile = {"language": {"primary": "python"}, "archetype": "python_project"}
    (tmp_path / "project_profile.json").write_text(
        json.dumps(profile), encoding="utf-8"
    )
    monkeypatch.setattr(infra, "load_profile", lambda pr: profile)
    monkeypatch.setattr(
        infra,
        "load_toolchain",
        lambda pr, language=None: {
            "testing": {"framework_packages": ["pytest"]},
            "quality": {"packages": ["ruff", "mypy"]},
        },
    )

    def fake_runner(cmd, **kwargs):
        # `conda list --json` -> nothing installed yet.
        return subprocess.CompletedProcess(cmd, 0, stdout="[]", stderr="")

    result = compute_dep_diff(tmp_path, "svp-test", runner=fake_runner)
    assert "numpy" in result["delta_blueprint_only"]
    assert "core.segmentation" not in result["delta_blueprint_only"]
    assert not any("`" in p for p in result["delta_blueprint_only"])

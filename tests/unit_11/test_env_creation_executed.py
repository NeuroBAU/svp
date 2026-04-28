"""Tests for Bug S3-137: run_infrastructure_setup executes env creation.

Step 4b (environment creation and package installation) must actually
invoke subprocess.run on the commands built in Step 1 when the env is
absent, and skip them when conda env list shows the env already exists.

These tests rely on the autouse `mock_infrastructure_subprocess` fixture
in tests/unit_11/conftest.py, which monkeypatches
infrastructure_setup.subprocess.run to a no-op MagicMock. Tests inspect
the mock's call_args_list to verify subprocess was called with the
expected command strings.
"""

import json
import subprocess

from infrastructure_setup import run_infrastructure_setup


def _write_minimal_blueprint(blueprint_dir):
    blueprint_dir.mkdir(parents=True, exist_ok=True)
    (blueprint_dir / "blueprint_contracts.md").write_text(
        "## Unit 1: First\n\n"
        "### Tier 2 — Signatures\n\n"
        "```python\n"
        "import json\n"
        "def f(): ...\n"
        "```\n\n"
        "## Unit 2: Second\n\n"
        "### Tier 2 — Signatures\n\n"
        "```python\n"
        "import requests\n"
        "def g(): ...\n"
        "```\n"
    )
    (blueprint_dir / "blueprint_prose.md").write_text("")


def _minimal_profile():
    return {
        "language": {"primary": "python"},
        "archetype": "python_project",
    }


def _minimal_toolchain():
    return {
        "environment": {
            "create": "conda create -n {env_name} python={python_version} -y",
            "install": "conda run -n {env_name} pip install {packages}",
        },
        "language": {"version_constraint": ">=3.11"},
        "quality": {},
    }


def _minimal_registry():
    return {
        "python": {
            "environment_manager": "conda",
            "file_extension": ".py",
            "toolchain_file": "python_conda_pytest.json",
            "import_syntax": "import {module}",
        }
    }


def _seed_state(project_root):
    svp = project_root / ".svp"
    svp.mkdir(parents=True, exist_ok=True)
    (svp / "pipeline_state.json").write_text(json.dumps({"total_units": 0}))


def test_env_creation_fires_when_env_absent(
    tmp_path, mock_infrastructure_subprocess
):
    """conda create + pip install fire when _env_exists returns False."""
    blueprint_dir = tmp_path / "blueprint"
    _write_minimal_blueprint(blueprint_dir)
    _seed_state(tmp_path)

    # Default mock: empty stdout → _env_exists returns False.
    run_infrastructure_setup(
        project_root=tmp_path,
        profile=_minimal_profile(),
        toolchain=_minimal_toolchain(),
        language_registry=_minimal_registry(),
        blueprint_dir=blueprint_dir,
    )

    call_cmds = [c.args[0] for c in mock_infrastructure_subprocess.call_args_list]
    # _env_exists check
    assert any(cmd[:3] == ["conda", "env", "list"] for cmd in call_cmds), (
        f"Expected 'conda env list' among calls; got {call_cmds}"
    )
    # env creation
    assert any(
        cmd[:2] == ["conda", "create"] and "-n" in cmd for cmd in call_cmds
    ), f"Expected 'conda create -n ...' among calls; got {call_cmds}"
    # package install
    assert any(
        "pip" in cmd and "install" in cmd for cmd in call_cmds
    ), f"Expected a 'pip install' call; got {call_cmds}"


def test_env_creation_skipped_when_env_already_exists(
    tmp_path, mock_infrastructure_subprocess
):
    """When conda env list reports env present, no create / install fires."""
    blueprint_dir = tmp_path / "blueprint"
    _write_minimal_blueprint(blueprint_dir)
    _seed_state(tmp_path)

    env_name = f"svp-{tmp_path.name}"
    conda_list_output = (
        "# conda environments:\n"
        "#\n"
        "base                  *  /x/conda\n"
        f"{env_name}                    /x/conda/envs/{env_name}\n"
    )

    def side_effect(args, **kwargs):
        if args[:3] == ["conda", "env", "list"]:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=conda_list_output, stderr=""
            )
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="", stderr=""
        )

    mock_infrastructure_subprocess.side_effect = side_effect

    run_infrastructure_setup(
        project_root=tmp_path,
        profile=_minimal_profile(),
        toolchain=_minimal_toolchain(),
        language_registry=_minimal_registry(),
        blueprint_dir=blueprint_dir,
    )

    call_cmds = [c.args[0] for c in mock_infrastructure_subprocess.call_args_list]
    # _env_exists check fired
    assert any(cmd[:3] == ["conda", "env", "list"] for cmd in call_cmds)
    # But no create
    assert not any(cmd[:2] == ["conda", "create"] for cmd in call_cmds), (
        f"Expected NO 'conda create' — env was reported present; got {call_cmds}"
    )
    # And no install
    assert not any("pip" in cmd and "install" in cmd for cmd in call_cmds), (
        f"Expected NO 'pip install' — env was reported present; got {call_cmds}"
    )


def test_install_command_includes_third_party_modules(
    tmp_path, mock_infrastructure_subprocess
):
    """Install list includes runtime deps extracted from blueprint imports."""
    blueprint_dir = tmp_path / "blueprint"
    _write_minimal_blueprint(blueprint_dir)  # Unit 2 imports `requests`
    _seed_state(tmp_path)

    run_infrastructure_setup(
        project_root=tmp_path,
        profile=_minimal_profile(),
        toolchain=_minimal_toolchain(),
        language_registry=_minimal_registry(),
        blueprint_dir=blueprint_dir,
    )

    call_cmds = [c.args[0] for c in mock_infrastructure_subprocess.call_args_list]
    install_calls = [
        cmd for cmd in call_cmds if "pip" in cmd and "install" in cmd
    ]
    assert install_calls, "Expected at least one 'pip install' call"
    install_str = " ".join(install_calls[0])
    # `requests` is third-party and should be in the install list;
    # `json` is stdlib and should NOT be.
    assert "requests" in install_str, (
        f"Expected 'requests' in install command; got: {install_str}"
    )
    assert " json " not in install_str, (
        f"Did not expect stdlib 'json' in install command; got: {install_str}"
    )


# ---------------------------------------------------------------------------
# Bug S3-160: env creation must be paired with mechanical verification.
# ---------------------------------------------------------------------------


def _r_profile_conda():
    return {
        "language": {"primary": "r"},
        "archetype": "r_project",
        "delivery": {
            "r": {
                "environment_recommendation": "conda",
                "dependency_format": "environment.yml",
                "source_layout": "package",
                "entry_points": False,
            }
        },
    }


def _r_registry_conda():
    return {
        "r": {
            "environment_manager": "conda",
            "file_extension": ".R",
            "source_dir": "R",
            "test_dir": "tests/testthat",
            "test_file_pattern": "test-*.R",
            "toolchain_file": "r_conda_testthat.json",
            "bridge_libraries": {},
            "default_delivery": {
                "environment_recommendation": "conda",
            },
        }
    }


def _materialize_r_toolchain(project_root):
    """Write a minimal pipeline toolchain.json that has verify_commands."""
    data = {
        "environment": {
            "tool": "conda",
            "run_prefix": "conda run -n {env_name}",
            "create_command": (
                "conda create -n {env_name} -c conda-forge r-base -y"
            ),
            "install_command": (
                "conda install -n {env_name} -c conda-forge {packages} -y"
            ),
            "verify_commands": [
                "{run_prefix} R --version",
                "{run_prefix} Rscript -e 'library(testthat); cat(\"OK\")'",
            ],
        },
        "language": {"version_constraint": ">=4.3"},
        "quality": {},
    }
    (project_root / "toolchain.json").write_text(json.dumps(data, indent=2))


def test_r_conda_env_creation_invokes_verify_and_sets_status_ready(
    tmp_path, mock_infrastructure_subprocess, monkeypatch
):
    """Bug S3-160: R conda branch calls verify_toolchain_ready and sets READY."""
    import infrastructure_setup
    from pipeline_state import load_state

    blueprint_dir = tmp_path / "blueprint"
    _write_minimal_blueprint(blueprint_dir)
    _seed_state(tmp_path)
    _materialize_r_toolchain(tmp_path)

    verify_calls = []

    def fake_verify(project_root, env_name, **kwargs):
        verify_calls.append((project_root, env_name))
        return (True, [])

    monkeypatch.setattr(
        infrastructure_setup, "verify_toolchain_ready", fake_verify
    )

    run_infrastructure_setup(
        project_root=tmp_path,
        profile=_r_profile_conda(),
        toolchain=_r_profile_conda(),
        language_registry=_r_registry_conda(),
        blueprint_dir=blueprint_dir,
    )

    # verify_toolchain_ready was called exactly once with our project root.
    assert len(verify_calls) == 1
    assert verify_calls[0][0] == tmp_path

    state = load_state(tmp_path)
    assert state.toolchain_status == "READY"


def test_r_conda_env_creation_verify_failure_propagates_status_not_ready(
    tmp_path, mock_infrastructure_subprocess, monkeypatch
):
    """Bug S3-160: verify failure -> NOT_READY persisted AND RuntimeError raised."""
    import pytest as _pytest

    import infrastructure_setup
    from pipeline_state import load_state

    blueprint_dir = tmp_path / "blueprint"
    _write_minimal_blueprint(blueprint_dir)
    _seed_state(tmp_path)
    _materialize_r_toolchain(tmp_path)

    def fake_verify(project_root, env_name, **kwargs):
        return (False, ["verify command failed (returncode=1): R --version"])

    monkeypatch.setattr(
        infrastructure_setup, "verify_toolchain_ready", fake_verify
    )

    with _pytest.raises(RuntimeError, match="Toolchain verification failed"):
        run_infrastructure_setup(
            project_root=tmp_path,
            profile=_r_profile_conda(),
            toolchain=_r_profile_conda(),
            language_registry=_r_registry_conda(),
            blueprint_dir=blueprint_dir,
        )

    state = load_state(tmp_path)
    assert state.toolchain_status == "NOT_READY"


def test_python_conda_env_creation_also_verifies(
    tmp_path, mock_infrastructure_subprocess, monkeypatch
):
    """Bug S3-160 parity: Python conda branch also fires verify_toolchain_ready."""
    import infrastructure_setup
    from pipeline_state import load_state

    blueprint_dir = tmp_path / "blueprint"
    _write_minimal_blueprint(blueprint_dir)
    _seed_state(tmp_path)
    # Materialize a python-shaped pipeline toolchain.json with verify_commands.
    (tmp_path / "toolchain.json").write_text(
        json.dumps(
            {
                "environment": {
                    "tool": "conda",
                    "run_prefix": "conda run -n {env_name}",
                    "verify_commands": ["{run_prefix} python --version"],
                },
                "language": {"version_constraint": ">=3.11"},
                "quality": {},
            }
        )
    )

    verify_calls = []

    def fake_verify(project_root, env_name, **kwargs):
        verify_calls.append((project_root, env_name))
        return (True, [])

    monkeypatch.setattr(
        infrastructure_setup, "verify_toolchain_ready", fake_verify
    )

    run_infrastructure_setup(
        project_root=tmp_path,
        profile=_minimal_profile(),
        toolchain=_minimal_toolchain(),
        language_registry=_minimal_registry(),
        blueprint_dir=blueprint_dir,
    )

    assert len(verify_calls) == 1
    state = load_state(tmp_path)
    assert state.toolchain_status == "READY"


# ---------------------------------------------------------------------------
# Bug S3-176: provision_only mode (Stage-0 provisioning).
#
# When provision_only=True, run_infrastructure_setup MUST run only the
# blueprint-independent prefix (env-create + toolchain verification) and
# return early. Blueprint-dependent steps (directory scaffolding,
# helper-svp.R templated copy, DAG validation, total_units derivation,
# regression test adaptation, build log creation) MUST be skipped because
# the blueprint does not yet exist at Stage-0 close.
# ---------------------------------------------------------------------------


def test_run_infrastructure_setup_provision_only_runs_env_create_and_verify_only(
    tmp_path, mock_infrastructure_subprocess, monkeypatch
):
    """provision_only=True runs env-create + verify but skips blueprint-
    dependent steps (no helper-svp.R, no directory scaffolding, no build_log)."""
    import infrastructure_setup

    # No blueprint directory authored — provision_only must not need it.
    blueprint_dir = tmp_path / "blueprint"
    _seed_state(tmp_path)
    # Materialize a python toolchain.json with verify_commands.
    (tmp_path / "toolchain.json").write_text(
        json.dumps(
            {
                "environment": {
                    "tool": "conda",
                    "run_prefix": "conda run -n {env_name}",
                    "verify_commands": ["{run_prefix} python --version"],
                },
                "language": {"version_constraint": ">=3.11"},
                "quality": {},
            }
        )
    )
    monkeypatch.setattr(
        infrastructure_setup,
        "verify_toolchain_ready",
        lambda *a, **k: (True, []),
    )

    run_infrastructure_setup(
        project_root=tmp_path,
        profile=_minimal_profile(),
        toolchain=_minimal_toolchain(),
        language_registry=_minimal_registry(),
        blueprint_dir=blueprint_dir,
        provision_only=True,
    )

    # Env-create fired (Step 4b).
    call_cmds = [c.args[0] for c in mock_infrastructure_subprocess.call_args_list]
    assert any(cmd[:2] == ["conda", "create"] for cmd in call_cmds), (
        f"Expected 'conda create' to fire in provision_only mode; got {call_cmds}"
    )
    # Blueprint-dependent artifacts NOT created.
    assert not (tmp_path / "src").exists(), (
        "src/ directory must NOT be scaffolded in provision_only mode "
        "(blueprint not yet authored)."
    )
    assert not (tmp_path / "tests" / "testthat" / "helper-svp.R").exists()
    # build_log.jsonl is part of Step 9 (skipped).
    assert not (tmp_path / ".svp" / "build_log.jsonl").exists()


def test_run_infrastructure_setup_provision_only_writes_toolchain_status_ready_on_success(
    tmp_path, mock_infrastructure_subprocess, monkeypatch
):
    """provision_only=True with successful verify writes
    state.toolchain_status='READY' to pipeline_state.json."""
    import infrastructure_setup
    from pipeline_state import load_state

    blueprint_dir = tmp_path / "blueprint"
    _seed_state(tmp_path)
    (tmp_path / "toolchain.json").write_text(
        json.dumps(
            {
                "environment": {
                    "tool": "conda",
                    "run_prefix": "conda run -n {env_name}",
                    "verify_commands": ["{run_prefix} python --version"],
                },
                "language": {"version_constraint": ">=3.11"},
                "quality": {},
            }
        )
    )
    monkeypatch.setattr(
        infrastructure_setup,
        "verify_toolchain_ready",
        lambda *a, **k: (True, []),
    )

    run_infrastructure_setup(
        project_root=tmp_path,
        profile=_minimal_profile(),
        toolchain=_minimal_toolchain(),
        language_registry=_minimal_registry(),
        blueprint_dir=blueprint_dir,
        provision_only=True,
    )

    state = load_state(tmp_path)
    assert state.toolchain_status == "READY"


def test_run_infrastructure_setup_provision_only_writes_toolchain_status_not_ready_on_failure(
    tmp_path, mock_infrastructure_subprocess, monkeypatch
):
    """provision_only=True with failing verify raises RuntimeError AND
    persists state.toolchain_status='NOT_READY'."""
    import pytest as _pytest

    import infrastructure_setup
    from pipeline_state import load_state

    blueprint_dir = tmp_path / "blueprint"
    _seed_state(tmp_path)
    (tmp_path / "toolchain.json").write_text(
        json.dumps(
            {
                "environment": {
                    "tool": "conda",
                    "run_prefix": "conda run -n {env_name}",
                    "verify_commands": ["{run_prefix} python --version"],
                },
                "language": {"version_constraint": ">=3.11"},
                "quality": {},
            }
        )
    )
    monkeypatch.setattr(
        infrastructure_setup,
        "verify_toolchain_ready",
        lambda *a, **k: (False, ["verify failed: python --version"]),
    )

    with _pytest.raises(RuntimeError, match="Toolchain verification failed"):
        run_infrastructure_setup(
            project_root=tmp_path,
            profile=_minimal_profile(),
            toolchain=_minimal_toolchain(),
            language_registry=_minimal_registry(),
            blueprint_dir=blueprint_dir,
            provision_only=True,
        )

    state = load_state(tmp_path)
    assert state.toolchain_status == "NOT_READY"

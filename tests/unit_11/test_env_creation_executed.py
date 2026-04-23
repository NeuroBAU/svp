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

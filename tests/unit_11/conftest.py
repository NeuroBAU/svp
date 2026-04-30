"""Conftest for Unit 11 tests — Bug S3-137.

run_infrastructure_setup now executes subprocess.run for conda env
creation and package installation (Step 4b). To keep unit tests hermetic
— no actual conda invocation, no pollution of the host environment — we
autouse-mock subprocess.run at the infrastructure_setup module level.

Tests that want to inspect subprocess calls can request the fixture by
name (`mock_infrastructure_subprocess`) and read `.call_args_list`, or
override `side_effect` to simulate specific conda output (e.g., the env
already exists).
"""

import subprocess
from unittest.mock import MagicMock

import pytest

import infrastructure_setup


@pytest.fixture(autouse=True)
def mock_infrastructure_subprocess(monkeypatch):
    """Replace subprocess.run in infrastructure_setup with a no-op mock.

    Default return: a CompletedProcess with returncode=0 and empty stdout.
    With empty stdout, `_env_exists` returns False, so env creation +
    install path fires during run_infrastructure_setup (and is captured
    harmlessly by the mock).

    Bug S3-200 / cycle I-3: the four production subprocess sites in Unit 11
    (`_env_exists`, regression-adapt, `_list_installed_conda_packages`,
    `install_dep_delta` conda install) drop `text=True` and decode bytes
    on the parent. The fixture mock therefore returns bytes for stdout +
    stderr to match the post-I-3 production shape. Tests that override
    `side_effect` are responsible for returning bytes too.
    """
    mock = MagicMock()
    mock.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=b"", stderr=b""
    )
    monkeypatch.setattr(infrastructure_setup.subprocess, "run", mock)
    return mock

"""Regression test for Bug S3-48 + S3-101: R test source path resolution."""
from pathlib import Path
import inspect


def test_unit_11_generates_helper_svp_r_for_r_projects():
    """S3-48: Infrastructure setup must mention helper-svp.R for R projects."""
    from infrastructure_setup import run_infrastructure_setup
    source = inspect.getsource(run_infrastructure_setup)
    assert "helper-svp.R" in source or "helper_svp" in source, (
        "Infrastructure setup must create helper-svp.R for R projects"
    )


def test_test_agent_definition_mentions_svp_source():
    """S3-48: TEST_AGENT_DEFINITION must mention svp_source for R tests."""
    from construction_agents import TEST_AGENT_DEFINITION
    assert "svp_source" in TEST_AGENT_DEFINITION, (
        "Test agent definition must mention svp_source() for R projects"
    )


def test_helper_svp_r_uses_test_path_navigation():
    """S3-101: helper-svp.R template must use testthat::test_path() navigation."""
    from infrastructure_setup import run_infrastructure_setup
    source = inspect.getsource(run_infrastructure_setup)
    assert "testthat::test_path()" in source, (
        "helper-svp.R must use testthat::test_path() for project root navigation, "
        "not file.path('R', ...) which resolves relative to CWD"
    )


def test_helper_svp_r_does_not_use_bare_r_path():
    """S3-101: helper-svp.R template must NOT use file.path('R', unit_file)."""
    from infrastructure_setup import run_infrastructure_setup
    source = inspect.getsource(run_infrastructure_setup)
    assert 'file.path("R"' not in source, (
        "helper-svp.R must not use file.path('R', ...) — "
        "use testthat::test_path() navigation instead"
    )

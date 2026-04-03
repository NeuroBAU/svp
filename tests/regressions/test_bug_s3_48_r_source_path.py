"""Regression test for Bug S3-48: R test source path resolution."""
from pathlib import Path


def test_unit_11_generates_helper_svp_r_for_r_projects():
    """S3-48: Infrastructure setup must mention helper-svp.R for R projects."""
    import inspect
    from src.unit_11.stub import run_infrastructure_setup
    source = inspect.getsource(run_infrastructure_setup)
    assert "helper-svp.R" in source or "helper_svp" in source, (
        "Infrastructure setup must create helper-svp.R for R projects"
    )


def test_test_agent_definition_mentions_svp_source():
    """S3-48: TEST_AGENT_DEFINITION must mention svp_source for R tests."""
    from src.unit_20.stub import TEST_AGENT_DEFINITION
    assert "svp_source" in TEST_AGENT_DEFINITION, (
        "Test agent definition must mention svp_source() for R projects"
    )

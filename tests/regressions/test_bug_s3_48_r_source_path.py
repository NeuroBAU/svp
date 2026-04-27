"""Regression test for Bug S3-48 + S3-101 + S3-161: R test source path resolution.

S3-48 originally introduced a placeholder `svp_source()` helper. S3-101 patched
its path resolution to use `testthat::test_path()`. S3-161 superseded BOTH by
replacing the helper with a namespace-walk approach: `devtools::load_all(
export_all = TRUE)` + walk `asNamespace(pkg)` exposing internal symbols to
`globalenv()`. The svp_source() function is no longer generated; tests no longer
need it because internal symbols are visible by name.

These regression tests are retained (renamed via reassertion) to pin the
new contract. Keeping the file under its original S3-48 name preserves git
history.
"""
from pathlib import Path
import inspect


def test_unit_11_generates_helper_svp_r_for_r_projects():
    """S3-48 (still required): Infrastructure setup must template helper-svp.R for R projects."""
    from infrastructure_setup import run_infrastructure_setup
    source = inspect.getsource(run_infrastructure_setup)
    assert "helper-svp.R" in source or "helper_svp" in source, (
        "Infrastructure setup must create helper-svp.R for R projects"
    )


def test_test_agent_definition_describes_r_internal_symbol_visibility():
    """S3-161 (supersedes S3-48): TEST_AGENT_DEFINITION must describe how R tests access internal symbols.

    Previously asserted on the literal token `svp_source`. With S3-161 the
    helper exposes every internal symbol via globalenv(), so tests just call
    them by name — no svp_source() wrapper. The agent definition must explain
    this so the test agent does not invent stale calls to svp_source().
    """
    from construction_agents import TEST_AGENT_DEFINITION
    # Either form is acceptable: legacy svp_source mention OR the new
    # globalenv/load_all/namespace-walk explanation.
    assert (
        "svp_source" in TEST_AGENT_DEFINITION
        or "load_all" in TEST_AGENT_DEFINITION
        or "globalenv" in TEST_AGENT_DEFINITION
        or "internal symbols" in TEST_AGENT_DEFINITION
    ), (
        "Test agent definition must describe how R tests access package "
        "internal symbols (either via legacy svp_source() OR via the "
        "S3-161 globalenv() namespace-walk helper)"
    )


def test_helper_svp_r_uses_namespace_walk():
    """S3-161 (supersedes S3-101): helper-svp.R template must use namespace-walk semantics.

    Previously asserted `testthat::test_path()` navigation. With S3-161 the
    helper does not navigate file paths at all — it walks the package namespace
    and assigns internal symbols into globalenv(). The signal tokens are
    `asNamespace`, `load_all`, and `globalenv`.
    """
    from infrastructure_setup import run_infrastructure_setup
    source = inspect.getsource(run_infrastructure_setup)
    assert "asNamespace" in source, (
        "helper-svp.R must walk the package namespace via asNamespace(pkg) "
        "(S3-161 supersedes S3-101's testthat::test_path() approach)"
    )
    assert "globalenv" in source, (
        "helper-svp.R must expose internal symbols to globalenv()"
    )
    assert "load_all" in source, (
        "helper-svp.R must call devtools::load_all(export_all = TRUE) when "
        "devtools is available"
    )


def test_helper_svp_r_does_not_use_bare_r_path():
    """S3-101 (still required): helper-svp.R template must NOT use file.path('R', unit_file).

    The forbidden pattern remains forbidden under S3-161 — the new helper
    doesn't navigate file paths at all, so the assertion still holds.
    """
    from infrastructure_setup import run_infrastructure_setup
    source = inspect.getsource(run_infrastructure_setup)
    assert 'file.path("R"' not in source, (
        "helper-svp.R must not use file.path('R', ...) — "
        "use namespace-walk via asNamespace(pkg) instead (S3-161)"
    )

"""Regression test for Bug S3-102: Oracle task prompt must embed test project artifacts."""
import inspect


def test_prepare_oracle_embeds_oracle_manifest():
    """S3-102: _prepare_oracle_agent must read oracle_manifest.json from test project."""
    from prepare_task import _prepare_oracle_agent
    source = inspect.getsource(_prepare_oracle_agent)
    assert "oracle_manifest.json" in source, (
        "_prepare_oracle_agent must embed oracle_manifest.json from test project"
    )


def test_prepare_oracle_embeds_stakeholder_spec():
    """S3-102: _prepare_oracle_agent must read test project stakeholder_spec.md."""
    from prepare_task import _prepare_oracle_agent
    source = inspect.getsource(_prepare_oracle_agent)
    assert "stakeholder_spec.md" in source, (
        "_prepare_oracle_agent must embed test project stakeholder_spec.md"
    )


def test_prepare_oracle_embeds_blueprint_contracts():
    """S3-102: _prepare_oracle_agent must read test project blueprint_contracts.md."""
    from prepare_task import _prepare_oracle_agent
    source = inspect.getsource(_prepare_oracle_agent)
    assert "blueprint_contracts.md" in source, (
        "_prepare_oracle_agent must embed test project blueprint_contracts.md"
    )


def test_prepare_oracle_handles_fmode_docs_path():
    """S3-102: _prepare_oracle_agent must handle F-mode by reading from docs/."""
    from prepare_task import _prepare_oracle_agent
    source = inspect.getsource(_prepare_oracle_agent)
    assert '"docs"' in source or "'docs'" in source, (
        "_prepare_oracle_agent must read F-mode artifacts from docs/ directory"
    )


def test_prepare_oracle_embeds_in_both_phases():
    """S3-102: Artifacts must be embedded in both dry_run and green_run phases."""
    from prepare_task import _prepare_oracle_agent
    source = inspect.getsource(_prepare_oracle_agent)
    # Count occurrences of artifact embedding — should appear twice (dry_run + green_run)
    count = source.count("oracle_manifest.json")
    assert count >= 2, (
        f"oracle_manifest.json appears {count} time(s) in _prepare_oracle_agent; "
        "expected >= 2 (dry_run + green_run)"
    )
